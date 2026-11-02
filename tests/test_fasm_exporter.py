"""
Unit tests for PyFASM FasmExporter: verifying exported FASM sources,
include headers, build scripts, and end-to-end compilation from exported folders.
"""
import os
import subprocess
import sys
from pathlib import Path
import pytest
from pyfasm.compiler import PyFasmCompiler
from pyfasm.bundler import ProjectBundler
from pyfasm.fasm_exporter import FasmExporter


def test_fasm_exporter_pure_compile(tmp_path: Path):
    source = """
def multiply(x: int, y: int) -> int:
    return x * y

def main() -> int:
    print(multiply(7, 8))
    return 0
"""
    src_file = tmp_path / "math_app.py"
    src_file.write_text(source, encoding="utf-8")
    fasm_dir = tmp_path / "FASM"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(
        source_path=str(src_file),
        target="win64",
        export_fasm_dir=str(fasm_dir),
    )

    assert success is True, f"Compilation failed: {log}"
    assert fasm_dir.exists()
    assert (fasm_dir / "math_app.asm").exists()
    assert (fasm_dir / "build.bat").exists()
    assert (fasm_dir / "build.sh").exists()
    assert (fasm_dir / "README.md").exists()
    assert (fasm_dir / "INCLUDE").exists()
    assert (fasm_dir / "INCLUDE" / "WIN64A.INC").exists()

    # Verify that the exported directory can be compiled with FASM independently
    if os.name == "nt":
        fasm_bin = fasm_dir / "FASM.EXE"
        if not fasm_bin.exists():
            fasm_bin = fasm_dir / "fasm.exe"
        if fasm_bin.exists():
            rebuilt_exe = fasm_dir / "math_app_rebuilt.exe"
            env = os.environ.copy()
            env["INCLUDE"] = str(fasm_dir / "INCLUDE")
            res = subprocess.run([str(fasm_bin), str(fasm_dir / "math_app.asm"), str(rebuilt_exe)], env=env, capture_output=True, text=True)
            assert res.returncode == 0, f"Rebuild failed:\n{res.stdout}"
            assert rebuilt_exe.exists()

            run_res = subprocess.run([str(rebuilt_exe)], capture_output=True, text=True)
            assert "56" in run_res.stdout


def test_fasm_exporter_project_bundle(tmp_path: Path):
    proj_dir = tmp_path / "my_bundled_tool"
    proj_dir.mkdir()
    main_file = proj_dir / "main.py"
    main_file.write_text("print('Bundled tool from exported FASM!')\n", encoding="utf-8")
    fasm_dir = proj_dir / "FASM"

    bundler = ProjectBundler()
    success, out_bin, log = bundler.bundle(
        project_dir=str(proj_dir),
        entry_script=str(main_file),
        target="win64",
        onefile=True,
        export_fasm_dir=str(fasm_dir),
    )

    assert success is True, f"Bundler failed: {log}"
    assert fasm_dir.exists()
    assert (fasm_dir / f"{proj_dir.name}.asm").exists()
    assert (fasm_dir / f"{proj_dir.name}.zip").exists()
    assert (fasm_dir / "build.bat").exists()
    assert (fasm_dir / "build.sh").exists()
    assert (fasm_dir / "INCLUDE").exists()

    bat_content = (fasm_dir / "build.bat").read_text(encoding="ascii")
    assert f"{proj_dir.name}.asm" in bat_content
    assert f"{proj_dir.name}.zip" in bat_content


def test_cli_docs(capsys):
    from pyfasm.cli import main
    import sys

    # Test English docs
    sys.argv = ["pyfasm", "docs"]
    res = main()
    assert res == 0
    captured = capsys.readouterr()
    assert "PyFASM64: Universal Python-to-Pure FASM" in captured.out
    assert "What's New in v0.1.14" in captured.out

    # Test Russian docs
    sys.argv = ["pyfasm", "docs", "--ru"]
    res_ru = main()
    assert res_ru == 0
    captured_ru = capsys.readouterr()
    assert "PyFASM64: Универсальный нативный компилятор Python" in captured_ru.out
    assert "Что нового в v0.1.14" in captured_ru.out


def test_fasm_modern_sdk_includes_bundled():
    from pyfasm.fasm_runner import FasmRunner
    runner = FasmRunner()
    inc = Path(runner.include_path)
    assert inc.exists() and inc.is_dir()
    has_win64 = (inc / "WIN64A.INC").exists() or (inc / "win64a.inc").exists()
    assert has_win64, f"WIN64A.INC not found in {inc}"
