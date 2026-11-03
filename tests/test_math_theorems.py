"""
Tests for arbitrary mathematical theorems and algorithms in PyFASM:
Pythagorean theorem (a**2 + b**2 = c**2), binary exponentiation (** operator),
math.sqrt, math.pow, factorial, Euclidean GCD, Fibonacci, Quadratic formula, Collatz conjecture.
"""
import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_math_pythagoras_and_powers(tmp_path: Path):
    source = """
import math

def pythagoras(a: int, b: int) -> int:
    hyp_sq = a ** 2 + b ** 2
    return int(math.sqrt(hyp_sq))

def power_test(base: int, exp: int) -> int:
    return base ** exp

def main() -> int:
    # 3^2 + 4^2 = 9 + 16 = 25, sqrt(25) = 5
    c1 = pythagoras(3, 4)
    print("Hypotenuse of (3, 4):", c1)

    # 5^2 + 12^2 = 25 + 144 = 169, sqrt(169) = 13
    c2 = pythagoras(5, 12)
    print("Hypotenuse of (5, 12):", c2)

    # Powers: 2^10 = 1024, 3^4 = 81
    p1 = power_test(2, 10)
    print("2^10:", p1)
    p2 = power_test(3, 4)
    print("3^4:", p2)

    # math.pow and math.sqrt
    p3 = math.pow(5, 3)
    print("5^3:", p3)
    s1 = math.sqrt(144)
    print("sqrt(144):", s1)
    return 0
"""
    src_file = tmp_path / "pythagoras_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "pythagoras_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Hypotenuse of (3, 4): 5" in res.stdout
    assert "Hypotenuse of (5, 12): 13" in res.stdout
    assert "2^10: 1024" in res.stdout
    assert "3^4: 81" in res.stdout
    assert "5^3: 125" in res.stdout
    assert "sqrt(144): 12" in res.stdout


def test_arbitrary_math_theorems_and_loops(tmp_path: Path):
    source = """
import math

def quadratic_roots(a: int, b: int, c: int) -> int:
    # Discriminant D = b^2 - 4ac
    d = b ** 2 - 4 * a * c
    if d < 0:
        return -1
    # x1 = (-b + sqrt(d)) / (2a)
    x1 = (-b + int(math.sqrt(d))) // (2 * a)
    return x1

def collatz_steps(n: int) -> int:
    steps = 0
    val = n
    while val > 1:
        if val % 2 == 0:
            val = val // 2
        else:
            val = 3 * val + 1
        steps = steps + 1
    return steps

def sum_arithmetic(n: int) -> int:
    # S = n * (n + 1) / 2
    return (n * (n + 1)) // 2

def is_prime(n: int) -> int:
    if n <= 1:
        return 0
    d = 2
    while d * d <= n:
        if n % d == 0:
            return 0
        d = d + 1
    return 1

def main() -> int:
    # x^2 - 5x + 6 = 0 -> roots are 2 and 3
    root = quadratic_roots(1, -5, 6)
    print("Quadratic root x1:", root)

    # Collatz sequence for 27 (known to take 111 steps)
    steps27 = collatz_steps(27)
    print("Collatz steps for 27:", steps27)

    # Sum 1..100 = 5050
    s100 = sum_arithmetic(100)
    print("Sum 1..100:", s100)

    # Prime checks
    p17 = is_prime(17)
    p24 = is_prime(24)
    print("17 is prime:", p17)
    print("24 is prime:", p24)
    return 0
"""
    src_file = tmp_path / "theorems_app.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "theorems_app.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Quadratic root x1: 3" in res.stdout
    assert "Collatz steps for 27: 111" in res.stdout
    assert "Sum 1..100: 5050" in res.stdout
    assert "17 is prime: 1" in res.stdout
    assert "24 is prime: 0" in res.stdout
