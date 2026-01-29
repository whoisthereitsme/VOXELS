from __future__ import annotations
import atexit
import sys
import threading
import time
from pathlib import Path
from typing import Iterable, Optional, Set, TextIO, Callable


from .github import GitHub


# ============================================================
# Bundle builder with integrated output capture (no output.txt, no HTML)
# ============================================================

class Bundle:
    class _Tee(TextIO):
        def __init__(self, original: TextIO, buffer: list[str], lock: threading.Lock) -> None:
            self._original = original
            self._buffer = buffer
            self._lock = lock

            

        def write(self, s: str) -> int:
            n = self._original.write(s)
            with self._lock:
                self._buffer.append(s)
            return n

        def flush(self) -> None:
            self._original.flush()

        def isatty(self) -> bool:
            return getattr(self._original, "isatty", lambda: False)()

        @property
        def encoding(self):
            return getattr(self._original, "encoding", "utf-8")

    def __init__(
        self,
        *,
        root: Path | None = None,
        out: Path | None = None,
        exts: Set[str] | None = None,
        dirs: Set[str] | None = None,
        skip: Set[str] | None = None,
        max_bytes: int = 2_000_000,
        overwrite: bool = True,
        include_stderr: bool = True,
        marker_prefix: str = "### CAPTURE START ###",
        auto_end_on_exit: bool = True,
        auto_end_on_exception: bool = True,
    ) -> None:
        self.root = (root if root is not None else Path.cwd()).resolve()
        self.out = (out if out is not None else (self.root / "bundle" / "bundle.txt")).resolve()

        self.exts = exts if exts is not None else {
            ".py", ".pyi", ".txt", ".md", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".bat", ".ps1", ".sh",
        }
        self.dirs = dirs if dirs is not None else {
            ".git", ".hg", ".svn", ".idea", ".vscode",
            "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
            ".venv", "venv", "env",
            "node_modules", "dist", "build",
            "atlas", "_old", "__OLD",
        }
        self.skip = skip if skip is not None else {".DS_Store", "Thumbs.db"}
        self.max_bytes = int(max_bytes)
        self.overwrite = bool(overwrite)

        self.include_stderr = bool(include_stderr)
        self.marker_prefix = str(marker_prefix)

        self._lock = threading.Lock()
        self._buf_out: list[str] = []
        self._buf_err: list[str] = []

        self._orig_stdout: Optional[TextIO] = None
        self._orig_stderr: Optional[TextIO] = None
        self._orig_excepthook: Optional[Callable] = None
        self._ended = False

        self.start_capture()

        if auto_end_on_exit:
            atexit.register(self.stop_capture_and_write_bundle)

        if auto_end_on_exception:
            self._install_excepthook()

        self.github = GitHub

    def __enter__(self) -> "Bundle":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop_capture_and_write_bundle()
        self.github()
        return False

    def _install_excepthook(self) -> None:
        self._orig_excepthook = sys.excepthook

        def hooked(exctype, value, tb) -> None:
            if self._orig_excepthook is not None:
                self._orig_excepthook(exctype, value, tb)
            self.stop_capture_and_write_bundle()

        sys.excepthook = hooked  # type: ignore[assignment]

    def start_capture(self) -> None:
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        sys.stdout = self._Tee(self._orig_stdout, self._buf_out, self._lock)  # type: ignore[assignment]
        if self.include_stderr:
            sys.stderr = self._Tee(self._orig_stderr, self._buf_err, self._lock)  # type: ignore[assignment]

        print(f"{self.marker_prefix} root={self.root.as_posix()}")

    def stop_capture_and_write_bundle(self) -> Path:
        captured = self._end_capture_get_text()
        return self.write_bundle_txt(captured_output=captured)

    def _end_capture_get_text(self) -> str:
        if self._ended:
            with self._lock:
                out_text = "".join(self._buf_out)
                err_text = "".join(self._buf_err)
            return self._combine_streams(out_text, err_text)

        self._ended = True

        if self._orig_stdout is not None:
            sys.stdout = self._orig_stdout  # type: ignore[assignment]
        if self.include_stderr and self._orig_stderr is not None:
            sys.stderr = self._orig_stderr  # type: ignore[assignment]

        if self._orig_excepthook is not None:
            sys.excepthook = self._orig_excepthook  # type: ignore[assignment]

        with self._lock:
            out_text = "".join(self._buf_out)
            err_text = "".join(self._buf_err)

        combined = self._combine_streams(out_text, err_text)

        marker_line = f"{self.marker_prefix} root={self.root.as_posix()}"
        combined = self._keep_after_marker(combined, marker_line)
        return combined

    def _combine_streams(self, out_text: str, err_text: str) -> str:
        combined = out_text
        if self.include_stderr and err_text:
            if combined and not combined.endswith("\n"):
                combined += "\n"
            combined += err_text
        return combined

    @staticmethod
    def _keep_after_marker(text: str, marker_line: str) -> str:
        idx = text.rfind(marker_line)
        if idx == -1:
            return text
        nl = text.find("\n", idx)
        if nl == -1:
            return ""
        return text[nl + 1 :]

    def write_bundle_txt(self, *, captured_output: str) -> Path:
        self.out.parent.mkdir(parents=True, exist_ok=True)
        if self.overwrite and self.out.exists():
            self.out.unlink()

        generated_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        files = sorted(self._iter_files(self.root), key=lambda p: str(p.relative_to(self.root)).lower())

        lines: list[str] = []
        lines.append(f"#Time when generated: {generated_at}\n\n")
        lines.append("### PROJECT BUNDLE ###\n")
        lines.append(f"Root: {self.root}\n")
        lines.append(f"Files included: {len(files)}\n\n")

        for i, p in enumerate(files, start=1):
            rel = p.relative_to(self.root).as_posix()

            lines.append("\n" + "#" * 80 + "\n")
            lines.append(f"# FILE {i}/{len(files)}: {rel} (START)\n")
            lines.append("#" * 80 + "\n\n")

            content = self._safe_read_text_lossy(p)
            if content and not content.endswith("\n"):
                content += "\n"
            lines.append(content)

            lines.append("\n" + "#" * 80 + "\n")
            lines.append(f"# FILE {i}/{len(files)}: {rel} (END)\n")
            lines.append("#" * 80 + "\n\n")

        if captured_output.strip():
            lines.append("\n" + "################################################################################\n")
            lines.append("### CAPTURED OUTPUT (STDOUT/STDERR) ###\n")
            lines.append("################################################################################\n\n")
            lines.append(captured_output if captured_output.endswith("\n") else captured_output + "\n")
            lines.append("\n################################################################################\n")
            lines.append("### END OF CAPTURED OUTPUT ###\n")
            lines.append("################################################################################\n")

        final_text = "".join(lines)
        if not final_text.endswith("\n"):
            final_text += "\n"

        total_lines = final_text.count("\n")
        final_text += f"# Total lines in bundle: {total_lines}\n"
        final_text += f"# Total files in bundle: {len(files)}\n"
        final_text += f"# Generated at the time: {time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}\n"
        final_text += "--- END OF FILE ---\n"

        self.out.write_text(final_text, encoding="utf-8")
        return self.out

    def _iter_files(self, root: Path) -> Iterable[Path]:
        for p in root.rglob("*"):
            if p.is_dir():
                continue

            parts = set(p.parts)
            if any(d in parts for d in self.dirs):
                continue
            if p.name in self.skip:
                continue
            if p.suffix.lower() not in self.exts:
                continue

            try:
                if p.stat().st_size > self.max_bytes:
                    continue
            except OSError:
                continue

            yield p

    @staticmethod
    def _safe_read_text_lossy(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"<<ERROR READING FILE: {e}>>\n"





