import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_try_except_zero_division_and_finally(tmp_path: Path):
    source = """
def main() -> int:
    caught = 0
    finally_ran = 0
    try:
        x = 0
        y = 100 // x
        print("Should not reach here:", y)
    except:
        caught = 1
        print("Caught division by zero!")
    finally:
        finally_ran = 1
        print("Finally executed!")

    print("Status:", caught, finally_ran)
    return 0
"""
    src_file = tmp_path / "try_test1.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "try_test1.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Caught division by zero!" in res.stdout
    assert "Finally executed!" in res.stdout
    assert "Status: 1 1" in res.stdout


def test_try_except_user_raise_and_orelse(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Test raise
    raise_caught = 0
    try:
        raise
    except:
        raise_caught = 1
        print("Caught explicit raise!")

    # 2. Test successful try with orelse
    orelse_ran = 0
    try:
        val = 42 * 2
    except:
        print("Should not catch")
    else:
        orelse_ran = 1
        print("Else block executed:", val)

    print("Summary:", raise_caught, orelse_ran)
    return 0
"""
    src_file = tmp_path / "try_test2.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "try_test2.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Caught explicit raise!" in res.stdout
    assert "Else block executed: 84" in res.stdout
    assert "Summary: 1 1" in res.stdout
