import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_tuple_unpacking_and_swap(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Parallel assignment & swap
    a, b = 10, 20
    print("Initial:", a, b)
    a, b = b, a
    print("Swapped:", a, b)

    # 2. Dynamic tuple unpacking
    point = (100, 200, 300)
    x, y, z = point
    print("Point:", x, y, z)

    return 0
"""
    src_file = tmp_path / "unpack_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "unpack_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Initial: 10 20" in res.stdout
    assert "Swapped: 20 10" in res.stdout
    assert "Point: 100 200 300" in res.stdout


def test_dict_comprehension_and_filtering(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Range dict comprehension
    d = {x: x * 10 for x in range(5)}
    print("Dict len:", len(d))
    print("D[0]:", d[0])
    print("D[3]:", d[3])
    print("D[4]:", d[4])

    # 2. Filtered dict comprehension: even squares
    evens = {x: x * x for x in range(8) if x % 2 == 0}
    print("Evens len:", len(evens))
    print("Evens[2]:", evens[2])
    print("Evens[6]:", evens[6])

    # 3. Dict comprehension over list
    items = [5, 9, 13]
    squares_map = {k: k * k for k in items}
    print("Squares_map[5]:", squares_map[5])
    print("Squares_map[9]:", squares_map[9])
    print("Squares_map[13]:", squares_map[13])

    return 0
"""
    src_file = tmp_path / "dictcomp_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "dictcomp_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Dict len: 5" in res.stdout
    assert "D[0]: 0" in res.stdout
    assert "D[3]: 30" in res.stdout
    assert "D[4]: 40" in res.stdout
    assert "Evens len: 4" in res.stdout
    assert "Evens[2]: 4" in res.stdout
    assert "Evens[6]: 36" in res.stdout
    assert "Squares_map[5]: 25" in res.stdout
    assert "Squares_map[9]: 81" in res.stdout
    assert "Squares_map[13]: 169" in res.stdout
