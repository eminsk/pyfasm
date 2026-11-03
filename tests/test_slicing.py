"""
Unit tests for slicing expressions in PyFASM:
s[start:end], s[start:], s[:end], s[::-1], and list slicing.
"""
import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_string_and_list_slicing(tmp_path: Path):
    source = """
def main() -> int:
    s = "Hello World"
    # Reverse string [::-1]
    rev = s[::-1]
    print("Reversed:", rev)

    # Substring [0:5] -> "Hello"
    sub1 = s[0:5]
    print("Sub1:", sub1)

    # Suffix [6:] -> "World"
    sub2 = s[6:]
    print("Sub2:", sub2)

    # Negative slice [-5:] -> "World"
    sub3 = s[-5:]
    print("Sub3:", sub3)

    # List slicing
    numbers = [10, 20, 30, 40, 50]
    rev_nums = numbers[::-1]
    print("Rev list len:", len(rev_nums))
    print("Rev list 0:", rev_nums[0])
    print("Rev list 4:", rev_nums[4])

    sub_nums = numbers[1:4] # [20, 30, 40]
    print("Sub list len:", len(sub_nums))
    print("Sub list 0:", sub_nums[0])
    print("Sub list 2:", sub_nums[2])
    return 0
"""
    src_file = tmp_path / "slice_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "slice_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Reversed: dlroW olleH" in res.stdout
    assert "Sub1: Hello" in res.stdout
    assert "Sub2: World" in res.stdout
    assert "Sub3: World" in res.stdout
    assert "Rev list len: 5" in res.stdout
    assert "Rev list 0: 50" in res.stdout
    assert "Rev list 4: 10" in res.stdout
    assert "Sub list len: 3" in res.stdout
    assert "Sub list 0: 20" in res.stdout
    assert "Sub list 2: 40" in res.stdout
