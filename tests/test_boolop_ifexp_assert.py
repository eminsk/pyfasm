import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_boolop_short_circuit_and_ifexp(tmp_path: Path):
    source = """
def main() -> int:
    x = 15
    y = 5

    # 1. Test AND with both true
    both_true = 0
    if x > 10 and y < 10:
        both_true = 1

    # 2. Test AND with first false (short-circuit)
    one_false = 0
    if x < 10 and y < 10:
        one_false = 1

    # 3. Test OR with first true (short-circuit)
    first_or = 0
    if x > 10 or y > 100:
        first_or = 1

    # 4. Test Ternary IfExp
    status = 999 if x > 20 else 777

    print("Booleans:", both_true, one_false, first_or)
    print("Ternary:", status)
    return 0
"""
    src_file = tmp_path / "bool_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "bool_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Booleans: 1 0 1" in res.stdout
    assert "Ternary: 777" in res.stdout


def test_assert_namedexpr_and_delete(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Test assert passing
    x = 42
    assert x == 42
    print("Assert 1 passed")

    # 2. Test assert failing caught in try/except
    assert_failed_caught = 0
    try:
        assert x == 999
    except:
        assert_failed_caught = 1
        print("Caught AssertionError cleanly!")

    # 3. Test walrus operator (NamedExpr)
    val = (n := 123) * 2
    print("Walrus n:", n)
    print("Walrus val:", val)

    # 4. Test del
    target_del = 555
    del target_del
    print("Del target:", target_del)

    return 0
"""
    src_file = tmp_path / "assert_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "assert_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Assert 1 passed" in res.stdout
    assert "Caught AssertionError cleanly!" in res.stdout
    assert "Walrus n: 123" in res.stdout
    assert "Walrus val: 246" in res.stdout
    assert "Del target: 0" in res.stdout
