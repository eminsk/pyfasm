from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
import pytest

from pyfasm import (
    CompilerDiagnostic,
    DiagnosticReport,
    PyFasmCompileError,
    PyFasmCompiler,
)
from pyfasm.diagnostics import format_fasm_error

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_e1001_syntax_error_in_entry_and_imported_module(tmp_path: Path):
    bad_entry = tmp_path / "bad_entry.py"
    bad_entry.write_text("def calc(x)\n    return x + 1\n", encoding="utf-8")
    out_exe = tmp_path / "bad_entry.exe"

    compiler = PyFasmCompiler()
    ok, _, log = compiler.compile_file(str(bad_entry), output_binary=str(out_exe), keep_asm=False)
    assert not ok
    assert not out_exe.exists()
    assert "error[E1001]" in log
    assert "bad_entry.py:1:" in log
    assert "def calc(x)" in log
    assert "^" in log

    with pytest.raises(PyFasmCompileError) as exc_info:
        compiler.compile_source_to_asm("def broken(:\n    pass\n")
    assert "error[E1001]" in str(exc_info.value)
    assert any(d.code == "E1001" for d in exc_info.value.diagnostics)

    # Syntax error in imported module must also abort compilation cleanly
    proj = tmp_path / "multi_bad"
    proj.mkdir()
    (proj / "broken_helper.py").write_text("def f(x):\n    return (\n", encoding="utf-8")
    main_py = proj / "main.py"
    main_py.write_text("import broken_helper\ndef main() -> int:\n    return 0\n", encoding="utf-8")
    ok2, _, log2 = compiler.compile_file(str(main_py), keep_asm=False)
    assert not ok2
    assert "error[E1001]" in log2
    assert "broken_helper.py" in log2


def test_e1002_e1003_input_and_target_errors(tmp_path: Path):
    compiler = PyFasmCompiler()

    ok_missing, _, log_missing = compiler.compile_file(str(tmp_path / "does_not_exist.py"))
    assert not ok_missing
    assert "error[E1002]" in log_missing

    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    ok_empty, _, log_empty = compiler.compile_file(str(empty_dir))
    assert not ok_empty
    assert "error[E1002]" in log_empty

    valid_src = tmp_path / "ok.py"
    valid_src.write_text("def main() -> int:\n    return 0\n", encoding="utf-8")
    ok_tgt, _, log_tgt = compiler.compile_file(str(valid_src), target="riscv64")
    assert not ok_tgt
    assert "error[E1003]" in log_tgt
    assert "win64" in log_tgt

    with pytest.raises(PyFasmCompileError) as exc_info:
        compiler.compile_source_to_asm("def main() -> int:\n    return 0\n", target="mips64")
    assert "error[E1003]" in str(exc_info.value)


def test_e2001_e2002_e2003_unsupported_constructs(tmp_path: Path):
    compiler = PyFasmCompiler()

    async_file = tmp_path / "async_mod.py"
    async_file.write_text("async def fetch():\n    return 1\n", encoding="utf-8")
    ok, report = compiler.check_file(str(async_file))
    assert not ok
    assert any(d.code == "E2001" for d in report.errors)
    assert "error[E2001]" in report.format_all()
    assert "spawn_thread" in report.format_all()

    meta_file = tmp_path / "meta_mod.py"
    meta_file.write_text(
        "class Meta(type):\n    pass\n\nclass Custom(metaclass=Meta):\n    pass\n",
        encoding="utf-8",
    )
    ok_m, rep_m = compiler.check_file(str(meta_file))
    assert not ok_m
    assert any(d.code == "E2002" for d in rep_m.errors)
    assert "error[E2002]" in rep_m.format_all()

    nonlocal_file = tmp_path / "nonlocal_mod.py"
    nonlocal_file.write_text(
        "def outer() -> int:\n"
        "    x = 1\n"
        "    def inner() -> int:\n"
        "        nonlocal x\n"
        "        x = 2\n"
        "        return x\n"
        "    return inner()\n",
        encoding="utf-8",
    )
    ok_n, rep_n = compiler.check_file(str(nonlocal_file))
    assert not ok_n
    assert any(d.code == "E2003" for d in rep_n.errors)
    assert "error[E2003]" in rep_n.format_all()


def test_warnings_and_strict_mode_promotion(tmp_path: Path):
    src = tmp_path / "warn_mod.py"
    src.write_text(
        "import pandas as pd\n\n"
        "class CustomCtx:\n"
        "    def __getattr__(self, name: str) -> int:\n"
        "        return 1\n\n"
        "def use_it(c: CustomCtx) -> int:\n"
        "    with c:\n"
        "        pass\n"
        "    return missing_external(1)\n",
        encoding="utf-8",
    )
    compiler = PyFasmCompiler()

    ok_default, rep_default = compiler.check_file(str(src), target="win64", strict=False)
    assert ok_default
    assert isinstance(rep_default, DiagnosticReport)
    assert all(isinstance(d, CompilerDiagnostic) for d in rep_default.items)
    warn_codes = {d.code for d in rep_default.warnings}
    assert {"W2004", "W2005", "W2006", "W3001"}.issubset(warn_codes)
    formatted_warn = rep_default.format_all()
    assert "warning[W2005]" in formatted_warn
    assert "warning[W3001]" in formatted_warn

    ok_strict, rep_strict = compiler.check_file(str(src), target="win64", strict=True)
    assert not ok_strict
    err_codes = {d.code for d in rep_strict.errors}
    assert {"E2004", "E2005", "E2006", "E3001"}.issubset(err_codes)

    ok_compile_strict, _, log_strict = compiler.compile_file(
        str(src), target="win64", keep_asm=False, strict=True
    )
    assert not ok_compile_strict
    assert "error[E3001]" in log_strict

    with pytest.raises(PyFasmCompileError) as exc_info:
        compiler.compile_source_to_asm(
            "def main() -> int:\n    return unknown_fn(5)\n", strict=True
        )
    assert "error[E3001]" in str(exc_info.value)


def test_e4001_and_e4002_fasm_error_formatting():
    raw_fasm_log = (
        "flat assembler  version 1.73.36  (16384 kilobytes memory, x64)\n"
        "functions.inc [42]:\n"
        "    call broken_external\n"
        "error: undefined symbol 'broken_external'.\n"
    )
    d1 = format_fasm_error(raw_fasm_log, asm_path="main.asm")
    assert d1.code == "E4001"
    assert d1.severity == "error"
    assert d1.file_path == "functions.inc"
    assert d1.lineno == 42
    rendered1 = d1.format()
    assert "error[E4001]" in rendered1
    assert "functions.inc:42" in rendered1
    assert "call broken_external" in rendered1

    d2 = format_fasm_error("Execution failed: [Errno 2] No such file or directory")
    assert d2.code == "E4002"
    assert "PYFASM_FASM_PATH" in (d2.hint or "")


def test_cli_check_and_compile_strict(tmp_path: Path):
    clean = tmp_path / "clean.py"
    clean.write_text("def main() -> int:\n    return 0\n", encoding="utf-8")
    res_ok = subprocess.run(
        [sys.executable, "-m", "pyfasm64", "check", str(clean)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert res_ok.returncode == 0
    assert "[PyFASM OK]" in res_ok.stdout

    warn_src = tmp_path / "with_warn.py"
    warn_src.write_text("def main() -> int:\n    return absent_helper(1)\n", encoding="utf-8")
    res_warn = subprocess.run(
        [sys.executable, "-m", "pyfasm64", "check", str(warn_src)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert res_warn.returncode == 0
    assert "warning[W3001]" in res_warn.stderr

    res_strict = subprocess.run(
        [sys.executable, "-m", "pyfasm64", "check", str(warn_src), "--strict"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert res_strict.returncode == 1
    assert "error[E3001]" in res_strict.stderr

    bad_src = tmp_path / "syntax_bad.py"
    bad_src.write_text("def main()\n    return 0\n", encoding="utf-8")
    res_bad = subprocess.run(
        [sys.executable, "-m", "pyfasm64", "check", str(bad_src)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert res_bad.returncode == 1
    assert "error[E1001]" in res_bad.stderr


def test_documentation_suite_complete_and_linked():
    docs_dir = REPO_ROOT / "docs"
    expected_docs = [
        "INDEX.md",
        "GETTING_STARTED.md",
        "LANGUAGE_REFERENCE.md",
        "CLI_AND_API.md",
        "ERRORS.md",
        "ARCHITECTURE.md",
        "GUIDE_RU.md",
    ]
    for doc_name in expected_docs:
        doc_path = docs_dir / doc_name
        assert doc_path.is_file(), f"Missing documentation file: {doc_path}"
        assert doc_path.stat().st_size > 1000, f"Documentation file too small: {doc_path}"

    doc_link_re = re.compile(r"https://github\.com/eminsk/pyfasm/blob/main/(docs/[A-Za-z0-9_.-]+\.md)")
    for readme_name in ("README.md", "README_RU.md"):
        text = (REPO_ROOT / readme_name).read_text(encoding="utf-8")
        links = set(doc_link_re.findall(text))
        assert len(links) >= 7, f"Expected full docs links in {readme_name}, got {links}"
        for rel_doc in links:
            assert (REPO_ROOT / rel_doc).is_file(), f"Broken doc link {rel_doc} in {readme_name}"

    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"/docs"' in pyproject_text
