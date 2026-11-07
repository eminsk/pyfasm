"""
Unit tests for bug fixes in PyFASM v0.1.23:
1. Division by zero outside try block (no #DE crash).
2. Float arithmetic (+, -, *, /) and unary minus.
3. Float comparisons (<, >, <=, >=, ==, !=) including negative numbers.
4. String equality & inequality comparison by value.
5. Negative list indexing (read and write).
6. String indexing (read single char).
"""
import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_division_by_zero_safety(tmp_path: Path):
    source = """
def main() -> int:
    a = 10
    b = 0
    c = a // b
    print("Safe div result:", c)
    d = a % b
    print("Safe mod result:", d)
    return 0
"""
    src_file = tmp_path / "div_zero_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "div_zero_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Safe div result: 0" in res.stdout
    assert "Safe mod result: 0" in res.stdout


def test_float_arithmetic_and_comparisons(tmp_path: Path):
    source = """
def main() -> int:
    f1: float = 2.5
    f2: float = 1.5
    f_add = f1 + f2
    print("Float add:", f_add)

    f_sub = f1 - f2
    print("Float sub:", f_sub)

    f_mul = f1 * 2.0
    print("Float mul:", f_mul)

    f_div = 10.0 / 4.0
    print("Float div:", f_div)

    # Float comparisons with negative values
    neg1: float = -1.0
    neg2: float = -2.0
    if neg2 < neg1:
        print("Cmp neg ok: -2.0 < -1.0")
    if neg1 > neg2:
        print("Cmp neg ok: -1.0 > -2.0")

    if f1 > f2:
        print("Cmp pos ok: 2.5 > 1.5")
    return 0
"""
    src_file = tmp_path / "float_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "float_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Float add: 4.0" in res.stdout
    assert "Float sub: 1.0" in res.stdout
    assert "Float mul: 5.0" in res.stdout
    assert "Float div: 2.500000" in res.stdout
    assert "Cmp neg ok: -2.0 < -1.0" in res.stdout
    assert "Cmp neg ok: -1.0 > -2.0" in res.stdout
    assert "Cmp pos ok: 2.5 > 1.5" in res.stdout


def test_string_comparisons_and_indexing(tmp_path: Path):
    source = """
def main() -> int:
    s1 = "foo" + "bar"
    s2 = "foobar"
    if s1 == s2:
        print("String eq: MATCH")
    else:
        print("String eq: FAIL")

    if s1 != "other":
        print("String neq: MATCH")

    # Single char indexing
    greeting = "Hello"
    first = greeting[0]
    second = greeting[1]
    last = greeting[4]
    print("Char 0:", first)
    print("Char 1:", second)
    print("Char 4:", last)
    return 0
"""
    src_file = tmp_path / "str_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "str_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "String eq: MATCH" in res.stdout
    assert "String neq: MATCH" in res.stdout
    assert "Char 0: H" in res.stdout
    assert "Char 1: e" in res.stdout
    assert "Char 4: o" in res.stdout


def test_negative_list_indexing(tmp_path: Path):
    source = """
def main() -> int:
    nums = [100, 200, 300, 400]
    last_item = nums[-1]
    prev_item = nums[-2]
    print("Last item:", last_item)
    print("Prev item:", prev_item)

    # Assign to negative index
    nums[-1] = 999
    new_last = nums[-1]
    print("Updated last:", new_last)
    return 0
"""
    src_file = tmp_path / "list_neg_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "list_neg_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Last item: 400" in res.stdout
    assert "Prev item: 300" in res.stdout
    assert "Updated last: 999" in res.stdout
