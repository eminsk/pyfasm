import subprocess
import tempfile
from pathlib import Path
import pytest
from pyfasm import PyFasmCompiler


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
