"""
Structured compiler diagnostics and rustc/clang-style error reporting for PyFASM64.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

VALID_TARGETS: Tuple[str, ...] = ("win64", "dll", "linux", "macos", "apple", "myos")

UNSUPPORTED_DUNDERS: Set[str] = {
    "__del__",
    "__getattr__",
    "__getattribute__",
    "__setattr__",
    "__delattr__",
    "__hash__",
    "__format__",
}

SUPPORTED_DUNDERS_SUMMARY: str = (
    "__init__, __new__, __add__..__xor__, __iadd__..__ixor__, __neg__, __pos__, __invert__, "
    "__eq__..__ge__, __len__, __getitem__, __setitem__, __contains__, __str__, __repr__, "
    "__bool__, __call__, __iter__, __next__, __enter__, __exit__"
)

NATIVELY_SUPPORTED_OR_ADAPTED_MODULES: Set[str] = {
    "math",
    "json",
    "bisect",
    "heapq",
    "itertools",
    "functools",
    "re",
    "os",
    "sys",
    "time",
    "typing",
    "dataclasses",
    "collections",
    "ctypes",
    "pathlib",
    "struct",
    "random",
    "string",
    "copy",
    "enum",
    "abc",
    "operator",
    "io",
    "unittest",
    "pytest",
    "__future__",
    "numpy",
    "requests",
    "bs4",
    "darkdetect",
    "tkinter",
    "customtkinter",
    "pystray",
    "pil",
    "pillow",
    "nanogemm",
    "pyfasm",
    "pyfasm64",
}

KNOWN_UNSUPPORTED_EXTERNAL_MODULES: Set[str] = {
    "asyncio",
    "pandas",
    "torch",
    "tensorflow",
    "scipy",
    "matplotlib",
    "sklearn",
    "cv2",
    "sqlite3",
    "sqlalchemy",
    "fastapi",
    "flask",
    "django",
    "aiohttp",
    "httpx",
    "playwright",
    "selenium",
    "cryptography",
    "pydantic",
    "multiprocessing",
    "concurrent",
    "subprocess",
    "socket",
    "ssl",
    "urllib",
    "http",
    "logging",
    "decimal",
    "datetime",
    "fractions",
}

_FASM_LOC_RE = re.compile(r"^(.+?)\s+\[(\d+)\]:\s*$")
_FASM_ERR_RE = re.compile(r"^\s*error:\s*(.+?)\s*$", re.IGNORECASE)


def extract_source_line(
    file_path: Optional[str] = None,
    lineno: Optional[int] = None,
    source_files: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Extracts a single 1-based source line from cache or disk."""
    if lineno is None or lineno < 1:
        return None
    if source_files and file_path and file_path in source_files:
        lines = source_files[file_path].splitlines()
        if lineno <= len(lines):
            return lines[lineno - 1]
    if file_path and file_path not in ("<source>", "<string>"):
        try:
            p = Path(file_path)
            if p.is_file():
                lines = p.read_text(encoding="utf-8-sig", errors="replace").splitlines()
                if lineno <= len(lines):
                    return lines[lineno - 1]
        except OSError:
            pass
    return None


@dataclass
class CompilerDiagnostic:
    """Single structured compiler diagnostic with source location and hint."""

    severity: str
    code: str
    message: str
    file_path: Optional[str] = None
    lineno: Optional[int] = None
    col_offset: Optional[int] = None
    end_col_offset: Optional[int] = None
    source_line: Optional[str] = None
    hint: Optional[str] = None

    def format(self) -> str:
        """Renders the diagnostic in rustc/clang style."""
        lines: List[str] = [f"{self.severity}[{self.code}]: {self.message}"]

        loc_parts: List[str] = []
        if self.file_path:
            loc_parts.append(self.file_path)
            if self.lineno is not None:
                loc_parts.append(str(self.lineno))
                if self.col_offset is not None:
                    loc_parts.append(str(self.col_offset))

        src_line = self.source_line
        if src_line is None and self.file_path and self.lineno is not None:
            src_line = extract_source_line(self.file_path, self.lineno)

        gutter_width = len(str(self.lineno)) if self.lineno is not None else 1
        gutter = " " * gutter_width

        if loc_parts:
            lines.append(f"{gutter}--> {':'.join(loc_parts)}")

        if src_line is not None and self.lineno is not None:
            display_line = src_line.rstrip("\r\n")
            lines.append(f"{gutter} |")
            lines.append(f"{self.lineno} | {display_line}")
            if self.col_offset is not None and self.col_offset >= 1:
                pad_len = min(max(0, self.col_offset - 1), len(display_line))
                pad = " " * pad_len
                if self.end_col_offset is not None and self.end_col_offset > self.col_offset:
                    span = min(self.end_col_offset - self.col_offset, max(1, len(display_line) - pad_len))
                else:
                    span = 1
                lines.append(f"{gutter} | {pad}{'^' * max(1, span)}")

        if self.hint:
            lines.append(f"{gutter} = hint: {self.hint}")

        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format()


@dataclass
class DiagnosticReport:
    """Deduplicated collection of compiler errors, warnings, and notes."""

    items: List[CompilerDiagnostic] = field(default_factory=list)
    _seen: Set[Tuple[str, str, Optional[str], Optional[int], str]] = field(
        default_factory=set, init=False, repr=False
    )

    def add(self, diag: CompilerDiagnostic) -> None:
        key = (diag.severity, diag.code, diag.file_path, diag.lineno, diag.message)
        if key not in self._seen:
            self._seen.add(key)
            self.items.append(diag)

    def add_error(
        self,
        code: str,
        message: str,
        file_path: Optional[str] = None,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        end_col_offset: Optional[int] = None,
        source_line: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.add(
            CompilerDiagnostic(
                severity="error",
                code=code,
                message=message,
                file_path=file_path,
                lineno=lineno,
                col_offset=col_offset,
                end_col_offset=end_col_offset,
                source_line=source_line,
                hint=hint,
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        file_path: Optional[str] = None,
        lineno: Optional[int] = None,
        col_offset: Optional[int] = None,
        end_col_offset: Optional[int] = None,
        source_line: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.add(
            CompilerDiagnostic(
                severity="warning",
                code=code,
                message=message,
                file_path=file_path,
                lineno=lineno,
                col_offset=col_offset,
                end_col_offset=end_col_offset,
                source_line=source_line,
                hint=hint,
            )
        )

    def add_note(
        self,
        code: str,
        message: str,
        file_path: Optional[str] = None,
        lineno: Optional[int] = None,
        hint: Optional[str] = None,
    ) -> None:
        self.add(
            CompilerDiagnostic(
                severity="note",
                code=code,
                message=message,
                file_path=file_path,
                lineno=lineno,
                hint=hint,
            )
        )

    def extend(self, diags: Iterable[CompilerDiagnostic]) -> None:
        for d in diags:
            self.add(d)

    def promote_warnings_to_errors(self, codes: Optional[Set[str]] = None) -> None:
        """Promotes matching warnings to errors (Wxxxx -> Exxxx) for --strict mode."""
        promoted: List[CompilerDiagnostic] = []
        self._seen.clear()
        for d in self.items:
            if d.severity == "warning" and (codes is None or d.code in codes):
                new_code = "E" + d.code[1:] if d.code.startswith("W") else d.code
                d = replace(d, severity="error", code=new_code)
            key = (d.severity, d.code, d.file_path, d.lineno, d.message)
            if key not in self._seen:
                self._seen.add(key)
                promoted.append(d)
        self.items = promoted

    @property
    def errors(self) -> List[CompilerDiagnostic]:
        return [d for d in self.items if d.severity == "error"]

    @property
    def warnings(self) -> List[CompilerDiagnostic]:
        return [d for d in self.items if d.severity == "warning"]

    @property
    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self.items)

    @property
    def has_warnings(self) -> bool:
        return any(d.severity == "warning" for d in self.items)

    def format_all(self, include_summary: bool = True) -> str:
        if not self.items:
            return ""
        rendered = "\n\n".join(d.format() for d in self.items)
        if not include_summary:
            return rendered
        n_err = len(self.errors)
        n_warn = len(self.warnings)
        if n_err > 0:
            return f"{rendered}\n\ncompilation failed: {n_err} error(s), {n_warn} warning(s)"
        if n_warn > 0:
            return f"{rendered}\n\ncompilation finished with {n_warn} warning(s)"
        return rendered


class PyFasmCompileError(Exception):
    """Raised when AOT compilation fails with structured compiler diagnostics."""

    def __init__(self, report: DiagnosticReport):
        self.report: DiagnosticReport = report
        self.diagnostics: List[CompilerDiagnostic] = list(report.items)
        super().__init__(report.format_all())


def from_syntax_error(
    exc: SyntaxError,
    file_path: Optional[str] = None,
    source_text: Optional[str] = None,
) -> CompilerDiagnostic:
    """Converts a Python SyntaxError into an E1001 CompilerDiagnostic."""
    path = file_path or getattr(exc, "filename", None) or "<source>"
    lineno = getattr(exc, "lineno", None)
    offset = getattr(exc, "offset", None)
    end_offset = getattr(exc, "end_offset", None)

    src_line: Optional[str] = None
    if source_text is not None and lineno is not None and lineno >= 1:
        lines = source_text.splitlines()
        if lineno <= len(lines):
            src_line = lines[lineno - 1]
    elif getattr(exc, "text", None):
        src_line = str(exc.text).rstrip("\r\n")

    msg = getattr(exc, "msg", None) or str(exc)
    return CompilerDiagnostic(
        severity="error",
        code="E1001",
        message=f"Python syntax error: {msg}",
        file_path=path,
        lineno=lineno,
        col_offset=offset if (isinstance(offset, int) and offset >= 1) else None,
        end_col_offset=end_offset if (isinstance(end_offset, int) and end_offset >= 1) else None,
        source_line=src_line,
        hint="Fix the Python syntax error before compiling with PyFASM64.",
    )


def format_fasm_error(raw_log: str, asm_path: Optional[str] = None) -> CompilerDiagnostic:
    """Parses FASM assembler logs into an actionable E4001/E4002 diagnostic."""
    raw = (raw_log or "").strip()
    if raw.startswith("Execution failed:") or not raw:
        return CompilerDiagnostic(
            severity="error",
            code="E4002",
            message=raw or "FASM assembler binary could not be executed or produced no output.",
            file_path=asm_path,
            hint=(
                "Verify the FASM binary is executable and accessible, or set the "
                "`PYFASM_FASM_PATH` and `PYFASM_INCLUDE_PATH` environment variables."
            ),
        )

    parsed_file: Optional[str] = asm_path
    parsed_line: Optional[int] = None
    offending_stmt: Optional[str] = None
    err_reason: Optional[str] = None

    log_lines = raw.splitlines()
    for idx, line in enumerate(log_lines):
        m_loc = _FASM_LOC_RE.match(line.strip())
        if m_loc:
            parsed_file = m_loc.group(1).strip()
            try:
                parsed_line = int(m_loc.group(2))
            except ValueError:
                parsed_line = None
            if idx + 1 < len(log_lines):
                cand_stmt = log_lines[idx + 1].rstrip()
                if not _FASM_ERR_RE.match(cand_stmt) and not cand_stmt.startswith("processed:"):
                    offending_stmt = cand_stmt.lstrip()
        m_err = _FASM_ERR_RE.match(line)
        if m_err:
            err_reason = m_err.group(1).strip()

    reason_text = err_reason or raw
    low = reason_text.lower()
    if "undefined symbol" in low:
        hint = (
            "An external function or variable symbol has no assembly definition. "
            "Check imports/spelling or run `pyfasm64 check --strict` to locate the Python origin."
        )
    elif "error reading file" in low or "file not found" in low:
        hint = (
            "FASM could not open a referenced include or resource file. "
            "Check `PYFASM_INCLUDE_PATH` / asset paths and ensure files exist."
        )
    elif "invalid operand" in low or "illegal instruction" in low or "invalid expression" in low:
        hint = (
            "Invalid x86-64 operand or syntax emitted in assembly. "
            "Run `pyfasm64 emit-asm` to inspect the generated FASM source around the reported line."
        )
    elif "out of memory" in low:
        hint = "FASM ran out of assembler memory while assembling large data or unrolled sections."
    else:
        hint = "Inspect the generated `.asm` file around the reported line or run `pyfasm64 check --strict`."

    message = f"FASM assembly error: {reason_text}\nFASM output:\n{raw}"
    return CompilerDiagnostic(
        severity="error",
        code="E4001",
        message=message,
        file_path=parsed_file,
        lineno=parsed_line,
        source_line=offending_stmt,
        hint=hint,
    )
