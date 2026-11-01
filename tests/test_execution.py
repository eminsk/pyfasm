import subprocess
from pathlib import Path
import pytest
from pyfasm.compiler import PyFasmCompiler


def test_end_to_end_math_and_print(tmp_path: Path):
    source = """
def calc(a: int, b: int) -> int:
    return (a + b) * 3 - 5

def main() -> int:
    ans = calc(10, 20)
    print(ans)
    return 0
"""
    src_file = tmp_path / "test_math.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "test_math.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    # Execute binary and verify stdout
    res = subprocess.run([bin_path], capture_output=True, text=True)
    assert res.returncode == 0
    # (10 + 20) * 3 - 5 = 85
    assert "85" in res.stdout.strip()


def test_end_to_end_fibonacci_loop(tmp_path: Path):
    source = """
def fib(n: int) -> int:
    if n <= 1:
        return n
    a = 0
    b = 1
    for i in range(2, n + 1):
        c = a + b
        a = b
        b = c
    return b

def main() -> int:
    f10 = fib(10)
    print(f10)
    return 0
"""
    src_file = tmp_path / "test_fib.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "test_fib.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    res = subprocess.run([bin_path], capture_output=True, text=True)
    assert res.returncode == 0
    # fib(10) = 55
    assert "55" in res.stdout.strip()


def test_end_to_end_memory_allocation(tmp_path: Path):
    source = """
def main() -> int:
    buf = alloc_memory(64)
    buf[0] = 123
    buf[1] = 456
    buf[2] = buf[0] + buf[1]
    print(buf[2])
    free_memory(buf)
    return 0
"""
    src_file = tmp_path / "test_mem.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "test_mem.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    res = subprocess.run([bin_path], capture_output=True, text=True)
    assert res.returncode == 0
    # 123 + 456 = 579
    assert "579" in res.stdout.strip()


def test_end_to_end_myos_compilation(tmp_path: Path):
    source = """
def main() -> int:
    print_str("MyOS Native 64-bit Binary")
    return 0
"""
    src_file = tmp_path / "test_myos.py"
    src_file.write_text(source, encoding="utf-8")
    out_bin = tmp_path / "test_myos.bin"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_bin), target="myos")

    assert success, f"MyOS compilation failed:\n{log}"
    assert Path(bin_path).exists()
    assert Path(bin_path).stat().st_size > 0

