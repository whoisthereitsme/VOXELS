from __future__ import annotations

import base64
import datetime as _dt
import html as _html
import os
import shutil
from pathlib import Path
from typing import Iterable, Set
from .github import GitHub
from .output import Output


class Bundle:
    __slots__ = (
        "root",
        "out_txt",
        "out_html",
        "include_exts",
        "skip_dirs",
        "skip_filenames",
        "max_bytes",
        "run_on_init",
        "overwrite",
        "output",
        "publish",
        "publish_dst_html",
        "publish_dst_txt",
        "write_txt_local",
        "write_output_txt_local",
        "publish_txt",
    )

    def __init__(
        self,
        *,
        root: Path | None = None,
        out_txt: Path | None = None,
        out_html: Path | None = None,
        include_exts: Set[str] | None = None,
        skip_dirs: Set[str] | None = None,
        skip_filenames: Set[str] | None = None,
        max_bytes: int = 2_000_000,
        run_on_init: bool = True,
        overwrite: bool = True,
        start_output_capture: bool = True,
        # local artifacts
        write_txt_local: bool = True,
        write_output_txt_local: bool = True,
        # publishing
        publish: bool = True,
        publish_txt: bool = True,
        publish_dst_html: Path | None = None,
        publish_dst_txt: Path | None = None,
    ) -> None:
        self.root = (root if root is not None else Path.cwd()).resolve()

        self.out_txt = out_txt if out_txt is not None else (Path("bundle") / "bundle.txt")
        if not self.out_txt.is_absolute():
            self.out_txt = (self.root / self.out_txt).resolve()

        self.out_html = out_html if out_html is not None else (Path("bundle") / "bundle.html")
        if not self.out_html.is_absolute():
            self.out_html = (self.root / self.out_html).resolve()

        self.include_exts = include_exts if include_exts is not None else {
            ".py", ".pyi", ".txt", ".md", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".bat", ".ps1", ".sh",
        }

        self.skip_dirs = skip_dirs if skip_dirs is not None else {
            ".git", ".hg", ".svn", ".idea", ".vscode",
            "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
            ".venv", "venv", "env",
            "node_modules", "dist", "build",
            "atlas", "bundle", "_old", "__OLD",
        }

        self.skip_filenames = skip_filenames if skip_filenames is not None else {".DS_Store"}

        self.max_bytes = int(max_bytes)
        self.run_on_init = bool(run_on_init)
        self.overwrite = bool(overwrite)

        self.write_txt_local = bool(write_txt_local)
        self.write_output_txt_local = bool(write_output_txt_local)

        self.publish = bool(publish)
        self.publish_txt = bool(publish_txt)

        self.publish_dst_html = publish_dst_html if publish_dst_html is not None else Path(
            r"P:\Public Folder\bundle.html"
        )
        self.publish_dst_txt = publish_dst_txt if publish_dst_txt is not None else Path(
            r"P:\Public Folder\bundle.txt"
        )

        self.output: Output | None = None
        if start_output_capture:
            # Output will write bundle/output.txt locally (optional), and we will read it back and
            # embed it into the HTML (and optionally into bundle.txt) deterministically.
            self.output = Output(
                root=self.root,
                out_file=(Path("bundle") / "output.txt"),
                overwrite=True,
                include_stderr=True,
                add_marker_on_start=True,
                marker_prefix="### CAPTURE START ###",
                append_to_bundle=False,     # we embed ourselves
                bundle_file=None,
                auto_end_on_exit=True,
                auto_end_on_exception=True,
                write_file=self.write_output_txt_local,
            )

        if self.run_on_init:
            self.run()

    # -----------------------------
    # Public API
    # -----------------------------

    def run(self) -> Path:
        """
        Builds the bundle content and writes:
          - bundle.html (always)
          - bundle.txt (optional, local)
        """
        self.out_html.parent.mkdir(parents=True, exist_ok=True)
        self.out_txt.parent.mkdir(parents=True, exist_ok=True)

        if self.overwrite:
            if self.out_html.exists():
                self.out_html.unlink()
            if self.write_txt_local and self.out_txt.exists():
                self.out_txt.unlink()

        t_generated = _dt.datetime.now().isoformat()
        bundle_text = self._bundle_project_text(self.root, t_generated)

        # Always write HTML (self-contained)
        html_doc = self._render_html_document(
            title="PROJECT BUNDLE",
            generated_at=t_generated,
            plain_text=bundle_text,
        )
        self.out_html.write_text(html_doc, encoding="utf-8")

        # Optionally write plain text locally
        if self.write_txt_local:
            self.out_txt.write_text(bundle_text, encoding="utf-8")

        return self.out_html

    def stop(self) -> None:
        captured_block = ""
        if self.output is not None:
            out_path = self.output.end()
            captured_block = self._safe_read_text_lossy(out_path)

        # Rebuild including captured output (so final HTML always includes runtime output)
        self._rebuild_with_captured_output(captured_block=captured_block)

        if self.publish:
            self._publish()

    # -----------------------------
    # Internals
    # -----------------------------

    def _rebuild_with_captured_output(self, *, captured_block: str) -> None:
        t_generated = _dt.datetime.now().isoformat()

        bundle_text = self._bundle_project_text(self.root, t_generated)

        if captured_block.strip():
            bundle_text = (
                bundle_text
                + "\n"
                + "################################################################################\n"
                + "### CAPTURED OUTPUT ###\n"
                + "################################################################################\n\n"
                + captured_block
                + ("" if captured_block.endswith("\n") else "\n")
                + "################################################################################\n"
                + "### END OF CAPTURED OUTPUT ###\n"
                + "################################################################################\n"
            )

        html_doc = self._render_html_document(
            title="PROJECT BUNDLE",
            generated_at=t_generated,
            plain_text=bundle_text,
        )
        self.out_html.write_text(html_doc, encoding="utf-8")

        if self.write_txt_local:
            self.out_txt.write_text(bundle_text, encoding="utf-8")

    def _publish(self) -> None:
        try:
            # TXT (optional)
            if self.publish_txt and self.write_txt_local and self.out_txt.exists():
                self.publish_dst_txt.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src=self.out_txt, dst=self.publish_dst_txt)
                print(f"[publish] OK: copied TXT bundle to pCloud: {self.publish_dst_txt}")
        except Exception as e:
            print(f"[publish] ERROR: could not publish bundle(s): {e!r}")
        GitHub()

    def _iter_files(self, root: Path) -> Iterable[Path]:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in self.skip_dirs]

            for name in filenames:
                if name in self.skip_filenames:
                    continue
                p = Path(dirpath) / name
                if p.suffix.lower() not in self.include_exts:
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

    def _bundle_project_text(self, root: Path, generated_at: str) -> str:
        files = sorted(self._iter_files(root), key=lambda p: str(p.relative_to(root)).lower())

        lines: list[str] = []
        lines.append(f"#Time when generated: {generated_at}\n\n")
        lines.append("### PROJECT BUNDLE ###\n")
        lines.append(f"Root: {root}\n")
        lines.append(f"Files included: {len(files)}\n\n")

        for i, p in enumerate(files, start=1):
            rel = p.relative_to(root).as_posix()

            lines.append("\n")
            lines.append("#" * 80 + "\n")
            lines.append(f"# FILE {i}/{len(files)}: {rel} (START)\n")
            lines.append("#" * 80 + "\n\n")

            content = self._safe_read_text_lossy(p)
            if content and not content.endswith("\n"):
                content += "\n"
            lines.append(content)

            lines.append("\n")
            lines.append("#" * 80 + "\n")
            lines.append(f"# FILE {i}/{len(files)}: {rel} (END)\n")
            lines.append("#" * 80 + "\n\n")

        final_text = "".join(lines)
        if not final_text.endswith("\n"):
            final_text += "\n"

        total_lines = final_text.count("\n")
        final_text += f"# Total lines in bundle: {total_lines}\n"
        final_text += f"# Total files in bundle: {len(files)}\n"
        final_text += f"# Generated at the time: {_dt.datetime.now().isoformat()}\n"
        final_text += "--- END OF FILE ---\n"
        return final_text

    @staticmethod
    def _render_html_document(*, title: str, generated_at: str, plain_text: str) -> str:
        """
        No interface: the page body is just the full bundle text rendered in <pre>.
        We also embed the exact same text base64-encoded in a <script> tag for completeness/debug,
        but the visible content is the escaped plain text (fast, immediate render).
        """
        # Visible payload: HTML-escaped inside <pre>
        escaped = _html.escape(plain_text, quote=False)

        # Optional embedded b64 (not used for rendering, but preserves exact bytes if needed)
        b64 = base64.b64encode(plain_text.encode("utf-8", errors="strict")).decode("ascii")

        return (
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"utf-8\" />\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
            f"  <title>{_html.escape(title)} — { _html.escape(generated_at) }</title>\n"
            "  <style>\n"
            "    html, body { margin: 0; padding: 0; }\n"
            "    body { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace; }\n"
            "    pre { margin: 0; padding: 12px; white-space: pre; overflow: auto; }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            f"<pre>{escaped}</pre>\n"
            "\n"
            f"<script id=\"bundle_b64\" type=\"text/plain\">{b64}</script>\n"
            "</body>\n"
            "</html>\n"
        )


if __name__ == "__main__":
    b = Bundle()
    try:
        # your program runs here...
        pass
    finally:
        b.stop()
