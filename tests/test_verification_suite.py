import subprocess
import tempfile
from pathlib import Path
import pytest
from pyfasm.compiler import PyFasmCompiler


def run_pyfasm_code(code: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "prog.py"
        exe = Path(tmp) / "prog.exe"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, out_exe, err = compiler.compile_file(str(src), output_binary=str(exe))
        assert ok, f"Compilation failed: {err}"
        proc = subprocess.run([out_exe], capture_output=True, text=True, timeout=10)
        return proc


def test_verification_arguments_0_to_20():
    """Verification Property 1: Pass from 0 to 20 arguments across registers and stack."""
    code = """
def f0() -> int:
    return 42

def f4(a: int, b: int, c: int, d: int) -> int:
    return a * 1000 + b * 100 + c * 10 + d

def f6(a: int, b: int, c: int, d: int, e: int, f: int) -> int:
    return a + b + c + d + e + f

def f12(a: int, b: int, c: int, d: int, e: int, f: int, g: int, h: int, i: int, j: int, k: int, l: int) -> int:
    return a + b + c + d + e + f + g + h + i + j + k + l

def f20(a1: int, a2: int, a3: int, a4: int, a5: int, a6: int, a7: int, a8: int, a9: int, a10: int,
        a11: int, a12: int, a13: int, a14: int, a15: int, a16: int, a17: int, a18: int, a19: int, a20: int) -> int:
    return (a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 +
            a11 + a12 + a13 + a14 + a15 + a16 + a17 + a18 + a19 + a20)

def main():
    print(f0())
    print(f4(1, 2, 3, 4))
    print(f6(10, 20, 30, 40, 50, 60))
    print(f12(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12))
    print(f20(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20))
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "42"
    assert lines[1] == "1234"
    assert lines[2] == "210"
    assert lines[3] == "78"  # sum 1..12 = 78
    assert lines[4] == "210"  # sum 1..20 = 210


def test_verification_deep_recursion_stack_alignment():
    """Verification Property 2: Recursion and deep call stack (16-byte alignment check)."""
    code = """
def fact(n: int) -> int:
    if n <= 1:
        return 1
    return n * fact(n - 1)

def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

def countdown(n: int) -> int:
    if n == 0:
        return 0
    return countdown(n - 1)

def main():
    print(fact(6))
    print(fib(10))
    print(countdown(500))
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "720"
    assert lines[1] == "55"
    assert lines[2] == "0"


def test_verification_integer_boundaries():
    """Verification Property 4: Integer boundary values around 65535, 65536, and negatives."""
    code = """
def main():
    a = 65535
    b = 65536
    c = 65537
    d = 100000
    neg = -12345
    print(a)
    print(b)
    print(c)
    print(d)
    print(neg)
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "65535"
    assert lines[1] == "65536"
    assert lines[2] == "65537"
    assert lines[3] == "100000"
    assert lines[4] == "-12345"


def test_verification_signed_arithmetic_combinations():
    """Verification Property 3: Signed and negative arithmetic & comparisons."""
    code = """
def main():
    a = -10
    b = 3
    div_res = a // b
    mul_res = a * b
    sub_res = a - b
    print(mul_res)
    print(sub_res)
    if a < b:
        print("lt_ok")
    if a <= -10:
        print("le_ok")
    if b > a:
        print("gt_ok")
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "-30"
    assert lines[1] == "-13"
    assert lines[2] == "lt_ok"
    assert lines[3] == "le_ok"
    assert lines[4] == "gt_ok"
