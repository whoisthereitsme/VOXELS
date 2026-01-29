from __future__ import annotations

import atexit
import sys
import threading
from pathlib import Path
from typing import TextIO, Optional, Callable


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


class Output:
    def __init__(
        self,
        root: Path | None = None,
        out_file: Path | None = None,
        *,
        overwrite: bool = True,
        include_stderr: bool = True,
        add_marker_on_start: bool = True,
        marker_prefix: str = "### CAPTURE START ###",
        append_to_bundle: bool = False,
        bundle_file: Path | None = None,
        auto_end_on_exit: bool = True,
        auto_end_on_exception: bool = True,
        write_file: bool = True,
    ) -> None:
        self.root: Path = (root if root is not None else Path.cwd()).resolve()
        self.out_file: Path = out_file if out_file is not None else (Path("bundle") / "output.txt")
        if not self.out_file.is_absolute():
            self.out_file = (self.root / self.out_file).resolve()

        self.overwrite = bool(overwrite)
        self.include_stderr = bool(include_stderr)
        self.add_marker_on_start = bool(add_marker_on_start)
        self.marker_prefix = str(marker_prefix)

        # kept for compatibility; not used by Bundle flow
        self.append_to_bundle = bool(append_to_bundle)
        self.bundle_path: Path = (bundle_file if bundle_file is not None else (self.out_file.parent / "bundle.txt"))
        if not self.bundle_path.is_absolute():
            self.bundle_path = (self.root / self.bundle_path).resolve()

        self.write_file = bool(write_file)

        self._lock = threading.Lock()
        self._buf_out: list[str] = []
        self._buf_err: list[str] = []

        self._orig_stdout: Optional[TextIO] = None
        self._orig_stderr: Optional[TextIO] = None

        self._ended = False
        self._orig_excepthook: Optional[Callable] = None

        self.start()

        if auto_end_on_exit:
            atexit.register(self.end)

        if auto_end_on_exception:
            self._install_excepthook()

    def _install_excepthook(self) -> None:
        self._orig_excepthook = sys.excepthook

        def hooked(exctype, value, tb) -> None:
            if self._orig_excepthook is not None:
                self._orig_excepthook(exctype, value, tb)
            self.end()

        sys.excepthook = hooked  # type: ignore[assignment]

    def start(self) -> None:
        if self.write_file:
            self.out_file.parent.mkdir(parents=True, exist_ok=True)

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        sys.stdout = _Tee(self._orig_stdout, self._buf_out, self._lock)  # type: ignore[assignment]
        if self.include_stderr:
            sys.stderr = _Tee(self._orig_stderr, self._buf_err, self._lock)  # type: ignore[assignment]

        if self.add_marker_on_start:
            print(f"{self.marker_prefix} root={self.root.as_posix()}")

    def end(self) -> Path:
        if self._ended:
            return self.out_file
        self._ended = True

        # Restore streams first
        if self._orig_stdout is not None:
            sys.stdout = self._orig_stdout  # type: ignore[assignment]
        if self.include_stderr and self._orig_stderr is not None:
            sys.stderr = self._orig_stderr  # type: ignore[assignment]

        # Restore excepthook
        if self._orig_excepthook is not None:
            sys.excepthook = self._orig_excepthook  # type: ignore[assignment]

        with self._lock:
            out_text = "".join(self._buf_out)
            err_text = "".join(self._buf_err)

        combined = out_text
        if self.include_stderr and err_text:
            if combined and not combined.endswith("\n"):
                combined += "\n"
            combined += err_text

        if self.add_marker_on_start:
            marker_line = f"{self.marker_prefix} root={self.root.as_posix()}"
            combined = self._keep_after_marker(combined, marker_line)

        header = (
            "### PROGRAM OUTPUT (CAPTURED IN-PROCESS) ###\n"
            f"Root: {self.root}\n"
            "### OUTPUT START ###\n\n"
        )
        footer = "\n### OUTPUT END ###\n"
        payload = header + combined + footer

        if self.write_file:
            if self.overwrite and self.out_file.exists():
                self.out_file.unlink()
            self.out_file.write_text(payload, encoding="utf-8")

        return self.out_file

    @staticmethod
    def _keep_after_marker(text: str, marker_line: str) -> str:
        idx = text.rfind(marker_line)
        if idx == -1:
            return text
        nl = text.find("\n", idx)
        if nl == -1:
            return ""
        return text[nl + 1 :]


if __name__ == "__main__":
    out = Output(root=Path.cwd(), out_file=Path("bundle") / "output.txt", write_file=True)
    print("This is a test of Output capture.")
    print("This line goes to stdout.")
    print("This line goes to stderr.", file=sys.stderr)
    out_path = out.end()
    print(f"Wrote captured output to: {out_path}")
