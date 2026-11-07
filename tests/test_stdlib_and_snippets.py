import sys
import subprocess
import tempfile
from pathlib import Path
import pytest
from pyfasm import PyFasmCompiler

if sys.platform != "win32":
    pytest.skip("Win64 native tests require Windows environment", allow_module_level=True)


def test_user_solution_min_operations():
    """Verifies the competitive programming snippet with class-level lambda, bisect, enumerate, zip, walrus, and bit shifts."""
    code = """
from bisect import bisect

class Solution:
    minOperations = lambda self, nums, locked, k: (
        (t >> 32) + (t & 0xFFFFFFFF)
        if (
            t := sum(
                ((l and not idx == i == x - 1) << 32) + i - idx
                for s in [[]]
                for i, (x, l) in enumerate(zip(nums, locked))
                if not s.insert(idx := bisect(s, x), x)
            )
        )
        >> 32
        <= k
        else -1
    )

if __name__ == "__main__":
    solver = Solution()
    assert solver.minOperations([2, 1, 3, 4], [0, 1, 0, 1], 1) == 2
    assert solver.minOperations([3, 1, 2], [1, 0, 1], 2) == 4
    assert solver.minOperations([2, 3, 1], [1, 0, 0], 0) == -1
    assert solver.minOperations([3, 2, 1], [0, 1, 0], 0) == -1
    assert solver.minOperations([3, 2, 1], [0, 1, 0], 1) == 4
    assert solver.minOperations([1, 2, 3, 4], [1, 1, 1, 1], 0) == 0
    print("SUCCESS_USER_SOLUTION")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "solution.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error ({res.returncode}): {res.stderr}"
        assert "SUCCESS_USER_SOLUTION" in res.stdout


def test_zip_and_enumerate():
    """Verifies built-in zip and enumerate."""
    code = """
nums = [10, 20, 30]
letters = [100, 200, 300]
res_zip = []
for a, b in zip(nums, letters):
    res_zip.append(a + b)

assert res_zip[0] == 110
assert res_zip[1] == 220
assert res_zip[2] == 330

res_enum = []
for idx, val in enumerate(nums, 5):
    res_enum.append(idx * 1000 + val)

assert res_enum[0] == 5010
assert res_enum[1] == 6020
assert res_enum[2] == 7030
print("SUCCESS_ZIP_ENUM")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "zip_enum.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_ZIP_ENUM" in res.stdout


def test_bisect_left_and_right():
    """Verifies bisect_right and bisect_left algorithms."""
    code = """
from bisect import bisect_left, bisect_right

arr = [1, 2, 4, 4, 4, 7, 9]
assert bisect_left(arr, 4) == 2
assert bisect_right(arr, 4) == 5
assert bisect_left(arr, 0) == 0
assert bisect_right(arr, 10) == 7
print("SUCCESS_BISECT")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "bisect_test.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_BISECT" in res.stdout


def test_heapq_min_heap():
    """Verifies heapq heappush and heappop conforming to min-heap invariant."""
    code = """
from heapq import heappush, heappop

heap = []
heappush(heap, 40)
heappush(heap, 10)
heappush(heap, 30)
heappush(heap, 5)
heappush(heap, 20)

assert heappop(heap) == 5
assert heappop(heap) == 10
assert heappop(heap) == 20
assert heappop(heap) == 30
assert heappop(heap) == 40
print("SUCCESS_HEAPQ")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "heap_test.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_HEAPQ" in res.stdout


def test_nested_unpacking_and_chained_compare():
    """Verifies nested tuple destructuring and chained comparison."""
    code = """
data = [(1, (2, 3)), (10, (20, 30))]
total = 0
for a, (b, c) in data:
    total = total + a + b + c

assert total == 66

x = 10
assert 5 < x < 15
assert 1 <= 1 == 1 < 2
print("SUCCESS_NESTED_CHAIN")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "chain_test.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_NESTED_CHAIN" in res.stdout


def test_math_gcd_lcm_isqrt_factorial():
    """Verifies math functions: gcd, lcm, isqrt, factorial in pure x64 assembly."""
    code = """
import math
from math import gcd, lcm, isqrt, factorial

assert gcd(48, 18) == 6
assert math.gcd(100, 25) == 25
assert gcd(0, 5) == 5
assert gcd(7, 13) == 1

assert lcm(4, 6) == 12
assert math.lcm(10, 15) == 30

assert isqrt(0) == 0
assert isqrt(1) == 1
assert isqrt(4) == 2
assert isqrt(15) == 3
assert isqrt(16) == 4
assert math.isqrt(100) == 10
assert math.isqrt(143) == 11
assert math.isqrt(144) == 12

assert factorial(0) == 1
assert factorial(1) == 1
assert factorial(5) == 120
assert math.factorial(6) == 720
print("SUCCESS_MATH_STDLIB")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "math_stdlib.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_MATH_STDLIB" in res.stdout


def test_itertools_and_functools():
    """Verifies itertools (chain, accumulate) and functools (reduce)."""
    code = """
import itertools
from itertools import chain, accumulate
import functools
from functools import reduce

# chain
c = chain([1, 2, 3], [4, 5])
assert c[0] == 1
assert c[1] == 2
assert c[2] == 3
assert c[3] == 4
assert c[4] == 5

# accumulate
acc = accumulate([1, 2, 3, 4, 5])
assert acc[0] == 1
assert acc[1] == 3
assert acc[2] == 6
assert acc[3] == 10
assert acc[4] == 15

# reduce
def add(a, b):
    return a + b

def mult(a, b):
    return a * b

assert reduce(add, [1, 2, 3, 4]) == 10
assert reduce(mult, [1, 2, 3, 4], 10) == 240
print("SUCCESS_ITERTOOLS_FUNCTOOLS")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "iter_functools.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_ITERTOOLS_FUNCTOOLS" in res.stdout


def test_user_solution_minimum_max_value():
    """Verifies competitive programming snippet with class-level lambda, generator expression, walrus, pow(0.5), next(gen, default), bit shifts, and assert."""
    code = """
class Solution:
    minimumMaxValue = lambda self, n, index, value: (
        -1
        if value < 2
        or value
        - (
            p := (
                next(
                    (
                        d
                        for d in range(3, int(value**0.5) + 1, 2)
                        if not value % d
                    ),
                    value,
                )
                if value & 1
                else 2
            )
        )
        < (index << 1)
        else value + (p + ((n - 2 - index) << 1) if index < n - 1 else 0)
    )

if __name__ == "__main__":
    solver = Solution()
    test_cases = [
        (4, 2, 8, 10),
        (2, 1, 3, -1),
        (2, 0, 3, 6),
        (2, 0, 1, -1),
        (3, 2, 6, 6),
        (4, 3, 9, 9),
        (5, 3, 9, 12),
    ]
    count = 0
    for n_val, idx_val, val, expected in test_cases:
        result = solver.minimumMaxValue(n_val, idx_val, val)
        assert result == expected
        print("All test cases passed successfully.")
        count = count + 1

    print("All test cases passed successfully.")
    assert count == 7
    print("SUCCESS_USER_MINIMUM_MAX_VALUE")
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "user_min_max.py"
        src.write_text(code, encoding="utf-8")
        compiler = PyFasmCompiler()
        ok, exe, log = compiler.compile_file(str(src))
        assert ok, f"Compilation failed: {log}"
        res = subprocess.run([exe], capture_output=True, text=True, timeout=10)
        assert res.returncode == 0, f"Runtime error: {res.stderr}"
        assert "SUCCESS_USER_MINIMUM_MAX_VALUE" in res.stdout
        lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip() == "All test cases passed successfully."]
        assert len(lines) == 8, f"Expected 8 prints of success message, got {len(lines)}"

