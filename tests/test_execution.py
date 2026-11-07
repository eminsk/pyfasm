from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple
import pytest
from pyfasm.compiler import PyFasmCompiler


def get_host_target() -> Tuple[str, str]:
    if sys.platform.startswith("linux"):
        return "linux", ".elf"
    elif sys.platform == "darwin":
        return "macos", ".macho"
    else:
        return "win64", ".exe"


def test_end_to_end_math_and_print(tmp_path: Path):
    source = """
def calc(a: int, b: int) -> int:
    return (a + b) * 3 - 5

def main() -> int:
    ans = calc(10, 20)
    print(ans)
    return 0
"""
    target, ext = get_host_target()
    src_file = tmp_path / "test_math.py"
    src_file.write_text(source, encoding="utf-8")
    out_bin = tmp_path / f"test_math{ext}"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_bin), target=target)

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    if sys.platform != "darwin":
        if os.name != "nt":
            os.chmod(bin_path, 0o755)
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
    target, ext = get_host_target()
    src_file = tmp_path / "test_fib.py"
    src_file.write_text(source, encoding="utf-8")
    out_bin = tmp_path / f"test_fib{ext}"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_bin), target=target)

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    if sys.platform != "darwin":
        if os.name != "nt":
            os.chmod(bin_path, 0o755)
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
    target, ext = get_host_target()
    src_file = tmp_path / "test_mem.py"
    src_file.write_text(source, encoding="utf-8")
    out_bin = tmp_path / f"test_mem{ext}"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_bin), target=target)

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    if sys.platform != "darwin":
        if os.name != "nt":
            os.chmod(bin_path, 0o755)
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


def test_end_to_end_float_and_strlen(tmp_path: Path):
    source = """
def main() -> int:
    msg: str = "PyFASM is ultra fast!"
    length = len(msg)
    print(length)

    pi = 3.141592
    print_float(pi)
    return 0
"""
    target, ext = get_host_target()
    src_file = tmp_path / "test_float.py"
    src_file.write_text(source, encoding="utf-8")
    out_bin = tmp_path / f"test_float{ext}"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_bin), target=target)

    assert success, f"Compilation failed:\n{log}"
    assert Path(bin_path).exists()

    if sys.platform != "darwin":
        if os.name != "nt":
            os.chmod(bin_path, 0o755)
        res = subprocess.run([bin_path], capture_output=True, text=True)
        assert res.returncode == 0
        # len("PyFASM is ultra fast!") = 21
        assert "21" in res.stdout
        # 3.141592
        assert "3." in res.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DLL ctypes test requires Win32")
def test_end_to_end_dll_compilation_and_ctypes(tmp_path: Path):
    source = """
def compute_kernel(x: int, y: int) -> int:
    return (x * 3) + (y * 7)

def get_magic_number() -> int:
    return 777
"""
    src_file = tmp_path / "math_kernel.py"
    src_file.write_text(source, encoding="utf-8")
    out_dll = tmp_path / "math_kernel.dll"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_dll), target="dll")

    assert success, f"DLL compilation failed:\n{log}"
    assert Path(bin_path).exists()

    # Load with ctypes and test
    import ctypes
    lib = ctypes.CDLL(str(bin_path))

    lib.compute_kernel.argtypes = [ctypes.c_int64, ctypes.c_int64]
    lib.compute_kernel.restype = ctypes.c_int64
    res1 = lib.compute_kernel(10, 20)
    # 10*3 + 20*7 = 30 + 140 = 170
    assert res1 == 170

    lib.get_magic_number.restype = ctypes.c_int64
    res2 = lib.get_magic_number()
    assert res2 == 777

    # Unload DLL to prevent address base lock in Windows process memory
    ctypes.windll.kernel32.FreeLibrary(lib._handle)


def test_bundler_creates_native_launcher(tmp_path: Path):
    target, ext = get_host_target()
    proj_dir = tmp_path / "mock_project"
    proj_dir.mkdir()
    entry_file = proj_dir / "main.py"
    entry_file.write_text("print('Hello from bundled app')", encoding="utf-8")

    out_bin = proj_dir / f"app_launcher{ext}"

    from pyfasm.bundler import ProjectBundler
    compiler = PyFasmCompiler()
    bundler = ProjectBundler(compiler.fasm_runner)
    success, bin_path, log = bundler.bundle(str(proj_dir), str(entry_file), str(out_bin), is_gui=False, target=target)

    assert success, f"Bundler failed:\n{log}"
    assert Path(bin_path).exists()
    assert Path(bin_path).stat().st_size > 0


def test_bundler_creates_linux_launcher(tmp_path: Path):
    proj_dir = tmp_path / "mock_linux_proj"
    proj_dir.mkdir()
    entry_file = proj_dir / "main.py"
    entry_file.write_text("print('Hello Linux App')", encoding="utf-8")

    out_elf = proj_dir / "app_launcher.elf"

    from pyfasm.bundler import ProjectBundler
    compiler = PyFasmCompiler()
    bundler = ProjectBundler(compiler.fasm_runner)
    success, bin_path, log = bundler.bundle(str(proj_dir), str(entry_file), str(out_elf), target="linux")

    assert success, f"Bundler failed:\n{log}"
    assert Path(bin_path).exists()
    content = Path(bin_path).read_bytes()
    assert content[:4] == b"\x7fELF", "Expected valid ELF header"


def test_bundler_creates_macos_launcher(tmp_path: Path):
    proj_dir = tmp_path / "mock_mac_proj"
    proj_dir.mkdir()
    entry_file = proj_dir / "main.py"
    entry_file.write_text("print('Hello Mac App')", encoding="utf-8")

    out_macho = proj_dir / "app_launcher.macho"

    from pyfasm.bundler import ProjectBundler
    compiler = PyFasmCompiler()
    bundler = ProjectBundler(compiler.fasm_runner)
    success, bin_path, log = bundler.bundle(str(proj_dir), str(entry_file), str(out_macho), target="macos")

    assert success, f"Bundler failed:\n{log}"
    assert Path(bin_path).exists()
    content = Path(bin_path).read_bytes()
    assert content[:4] == b"\xcf\xfa\xed\xfe", "Expected valid Mach-O 64-bit header"


def test_compile_linux_elf64(tmp_path: Path):
    source = """
def main() -> int:
    print_str("Hello from Linux ELF64!")
    print_newline()
    return 0
"""
    src_file = tmp_path / "hello_linux.py"
    src_file.write_text(source, encoding="utf-8")
    out_elf = tmp_path / "hello_linux.elf"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_elf), target="linux")

    assert success, f"Linux ELF compilation failed:\n{log}"
    assert Path(bin_path).exists()
    content = Path(bin_path).read_bytes()
    # Check ELF magic: \x7fELF
    assert content[:4] == b"\x7fELF", "Missing standard ELF header magic"
    # Check 64-bit class
    assert content[4] == 2, "Expected 64-bit ELF executable"


def test_compile_macos_macho64(tmp_path: Path):
    source = """
def main() -> int:
    print_str("Hello from Apple macOS Mach-O!")
    print_newline()
    return 0
"""
    src_file = tmp_path / "hello_mac.py"
    src_file.write_text(source, encoding="utf-8")
    out_macho = tmp_path / "hello_mac.macho"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_macho), target="macos")

    assert success, f"macOS Mach-O compilation failed:\n{log}"
    assert Path(bin_path).exists()
    content = Path(bin_path).read_bytes()
    # Check Mach-O 64-bit magic: 0xFEEDFACF (little endian: \xcf\xfa\xed\xfe)
    assert content[:4] == b"\xcf\xfa\xed\xfe", "Missing Mach-O 64-bit header magic"


def test_end_to_end_multimodule_single_file_compilation(tmp_path: Path):
    target, ext = get_host_target()
    proj = tmp_path / "multi_mod_app"
    proj.mkdir()

    # Module 1: math_lib.py
    (proj / "math_lib.py").write_text("""
def multiply(a: int, b: int) -> int:
    return a * b

def add_bonus(x: int) -> int:
    return x + 15
""", encoding="utf-8")

    # Module 2: helpers.py
    (proj / "helpers.py").write_text("""
import math_lib

def compute_total(base: int, factor: int) -> int:
    m = math_lib.multiply(base, factor)
    return math_lib.add_bonus(m)
""", encoding="utf-8")

    # Entry module: main.py
    (proj / "main.py").write_text("""
import helpers

def main() -> int:
    # (10 * 3) + 15 = 45
    ans = helpers.compute_total(10, 3)
    print(ans)
    return 0
""", encoding="utf-8")

    out_bin = proj / f"bundled_app{ext}"
    compiler = PyFasmCompiler()

    # Compile the entire project directory into a SINGLE standalone binary
    success, bin_path, log = compiler.compile_file(str(proj), str(out_bin), target=target)
    assert success, f"Multi-module compilation failed:\n{log}"
    assert Path(bin_path).exists()

    # Execute binary and verify output
    if sys.platform != "darwin":
        if os.name != "nt":
            os.chmod(bin_path, 0o755)
        res = subprocess.run([bin_path], capture_output=True, text=True)
        assert res.returncode == 0
        assert "45" in res.stdout.strip()


def test_multimodule_compilation_from_entry_file(tmp_path: Path):
    target, ext = get_host_target()
    proj = tmp_path / "entry_app"
    proj.mkdir()

    (proj / "core_utils.py").write_text("""
def calculate_area(w: int, h: int) -> int:
    return w * h
""", encoding="utf-8")

    main_py = proj / "main.py"
    main_py.write_text("""
from core_utils import calculate_area

def main() -> int:
    area = calculate_area(7, 8)
    print(area)
    return 0
""", encoding="utf-8")

    out_bin = proj / f"area_tool{ext}"
    compiler = PyFasmCompiler()

    # Compile passing main.py — it automatically resolves core_utils into 1 binary
    success, bin_path, log = compiler.compile_file(str(main_py), str(out_bin), target=target)
    assert success, f"Compilation failed:\n{log}"
    assert Path(bin_path).exists()

    if sys.platform != "darwin":
        if os.name != "nt":
            os.chmod(bin_path, 0o755)
        res = subprocess.run([bin_path], capture_output=True, text=True)
        assert res.returncode == 0
        assert "56" in res.stdout.strip()

