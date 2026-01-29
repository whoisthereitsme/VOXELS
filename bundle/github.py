import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Set

from credentials import *


# ============================================================
# GitHub publisher (single commit, whole project)
# ============================================================
@dataclass(frozen=True)
class FileJob:
    local_path: Path
    repo_path: str


class GitHub:
    def __init__(
        self,
        root: Path = Path.cwd(),
        verbose: bool = True,
        workers: int = 12,
        message: str = "Publish project snapshot",
        exts: Optional[Set[str]] = None,
        dirs: Optional[Set[str]] = None,
        files: Optional[Set[str]] = None,
        bytes: int = 2_000_000,
        binary: bool = True,
    ) -> None:
        self.owner = Environ.githublogin
        self.token = Environ.githubtoken
        self.repo = "VOXELS"
        self.branch = "main"
        self.root = root.resolve()
        
        self.verbose = verbose
        self.workers = workers
        self.message = message

        self.exts = exts
        self.dirs = dirs or {
            ".git", ".hg", ".svn",
            ".idea", ".vscode",
            "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
            ".venv", "venv", "env",
            "node_modules", "dist", "build",
            ".gradle", ".terraform",
            "atlas", "_old", "__OLD",
        }
        self.files = files or {".DS_Store", "Thumbs.db"}
        self.bytes = bytes
        self.binary = binary

        self.lock = threading.Lock()

        self.publish()

    def publish(self) -> None:
        t0 = time.perf_counter()
        if not self.token:
            raise SystemExit(
                f"Missing environment variable GITHUB_TOKEN.\n"
                f"Create a fine-grained PAT (Contents: read+write) for repo {self.owner}/{self.repo}."
            )

        if not self.root.exists() or not self.root.is_dir():
            raise SystemExit(f"root does not exist or is not a directory: {self.root}")

        jobs = self._build_jobs()
        self._log(f"[GITHUB] single-commit publish: {len(jobs)} files from {self.root} -> {self.owner}/{self.repo}@{self.branch}")

        head_commit_sha = self._get_branch_head_commit_sha(self.token)
        base_tree_sha = self._get_commit_tree_sha(self.token, head_commit_sha)

        path_to_blob_sha = self._create_blobs_parallel(self.token, jobs)
        new_tree_sha = self._create_tree(self.token, base_tree_sha, path_to_blob_sha)
        new_commit_sha = self._create_commit(self.token, new_tree_sha, head_commit_sha)
        self._update_branch_ref(self.token, new_commit_sha)

        dt = time.perf_counter() - t0
        self._log(f"[GITHUB] done: 1 commit, {len(jobs)} files, elapsed {dt:.2f}s. files/sec: {len(jobs)/dt:.1f}")

    # -----------------------------
    # File enumeration / filters
    # -----------------------------
    def _build_jobs(self) -> list[FileJob]:
        files = sorted(self._iter_project_files(self.root), key=lambda p: str(p).lower())
        return [FileJob(p, p.relative_to(self.root).as_posix()) for p in files]

    def _iter_project_files(self, root: Path) -> Iterable[Path]:
        for p in root.rglob("*"):
            if p.is_dir():
                continue

            parts = set(p.parts)
            if any(d in parts for d in self.dirs):
                continue
            if p.name in self.files:
                continue
            if self.exts is not None and p.suffix.lower() not in self.exts:
                continue

            try:
                if p.stat().st_size > self.bytes:
                    continue
            except OSError:
                continue

            if self.binary:
                try:
                    data = p.read_bytes()
                except OSError:
                    continue
                if self._looks_binary(data):
                    continue

            yield p

    @staticmethod
    def _looks_binary(data: bytes) -> bool:
        if b"\x00" in data:
            return True
        sample = data[:8192]
        if not sample:
            return False
        bad = 0
        for b in sample:
            if b in (9, 10, 13) or 32 <= b <= 126:
                continue
            bad += 1
        return (bad / len(sample)) > 0.20

    # -----------------------------
    # GitHub API core
    # -----------------------------
    def _api_request(self, method: str, url: str, token: str, body: Optional[dict] = None) -> dict:
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url=url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json; charset=utf-8")

        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API error {e.code} for {url}\n{raw}") from e

    def _get_branch_head_commit_sha(self, token: str) -> str:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/ref/heads/{self.branch}"
        j = self._api_request("GET", url, token)
        return j["object"]["sha"]

    def _get_commit_tree_sha(self, token: str, commit_sha: str) -> str:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/commits/{commit_sha}"
        j = self._api_request("GET", url, token)
        return j["tree"]["sha"]

    def _create_blob(self, token: str, content_bytes: bytes) -> str:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/blobs"
        body = {"content": base64.b64encode(content_bytes).decode("ascii"), "encoding": "base64"}
        j = self._api_request("POST", url, token, body=body)
        return j["sha"]

    def _create_blobs_parallel(self, token: str, jobs: list[FileJob]) -> dict[str, str]:
        out: dict[str, str] = {}
        lock = threading.Lock()

        def worker(job: FileJob) -> None:
            data = job.local_path.read_bytes()
            sha = self._create_blob(token, data)
            with lock:
                out[job.repo_path] = sha
            if self.verbose:
                self._log(f"    [blob] {job.repo_path}")

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = [ex.submit(worker, j) for j in jobs]
            for fut in as_completed(futures):
                fut.result()

        return out

    def _create_tree(self, token: str, base_tree_sha: str, path_to_blob_sha: dict[str, str]) -> str:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/trees"
        tree_entries = [
            {"path": path, "mode": "100644", "type": "blob", "sha": blob_sha}
            for path, blob_sha in path_to_blob_sha.items()
        ]
        body = {"base_tree": base_tree_sha, "tree": tree_entries}
        j = self._api_request("POST", url, token, body=body)
        return j["sha"]

    def _create_commit(self, token: str, tree_sha: str, parent_commit_sha: str) -> str:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/commits"
        body = {"message": self.message, "tree": tree_sha, "parents": [parent_commit_sha]}
        j = self._api_request("POST", url, token, body=body)
        return j["sha"]

    def _update_branch_ref(self, token: str, new_commit_sha: str) -> None:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/git/refs/heads/{self.branch}"
        body = {"sha": new_commit_sha, "force": False}
        self._api_request("PATCH", url, token, body=body)

    def _log(self, msg: str) -> None:
        with self.lock:
            print(msg)

