import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_list_comprehension_range_and_filtering(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Simple range comprehension: squares
    squares = [x * x for x in range(6)]
    print("Squares len:", len(squares))
    print("Squares:", squares[0], squares[1], squares[2], squares[3], squares[4], squares[5])

    # 2. Filtered range comprehension: even numbers
    evens = [x for x in range(10) if x % 2 == 0]
    print("Evens len:", len(evens))
    print("Evens:", evens[0], evens[1], evens[2], evens[3], evens[4])

    return 0
"""
    src_file = tmp_path / "list_comp1.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "list_comp1.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Squares len: 6" in res.stdout
    assert "Squares: 0 1 4 9 16 25" in res.stdout
    assert "Evens len: 5" in res.stdout
    assert "Evens: 0 2 4 6 8" in res.stdout


def test_list_comprehension_over_container(tmp_path: Path):
    source = """
def main() -> int:
    nums = [10, 15, 20, 25, 30]
    # Filter and double elements > 15
    filtered = [x * 2 for x in nums if x > 15]
    print("Filtered len:", len(filtered))
    print("Filtered:", filtered[0], filtered[1], filtered[2])
    return 0
"""
    src_file = tmp_path / "list_comp2.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "list_comp2.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Filtered len: 3" in res.stdout
    assert "Filtered: 40 50 60" in res.stdout
