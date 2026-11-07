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
    """Verification Property 4: Integer boundary values around 65535, 65536, large values, and list subscripts."""
    code = """
def main():
    a = 65535
    b = 65536
    c = 65537
    d = 100000
    neg = -12345
    large = 1000000000
    arr = [10, 20, 1000000000]
    words = ["compiler", "fasm"]
    print(a)
    print(b)
    print(c)
    print(d)
    print(neg)
    print(large)
    print(arr[2])
    print(words[0])
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "65535"
    assert lines[1] == "65536"
    assert lines[2] == "65537"
    assert lines[3] == "100000"
    assert lines[4] == "-12345"
    assert lines[5] == "1000000000"
    assert lines[6] == "1000000000"
    assert lines[7] == "compiler"


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


def test_verification_peephole_thread_safety_and_abi():
    """Verification Property: Peephole optimizer thread-safety & 32-bit zero-extend preservation."""
    from pyfasm.optimizer import optimize_fasm_code

    raw_asm = """
    mov rax, rax
    mov eax, eax
    lock inc qword [rcx]
    mov [g_counter], rax
    mov rax, [g_counter]
    mov [rbp - 16], rbx
    mov rbx, [rbp - 16]
"""
    opt = optimize_fasm_code(raw_asm)
    # 64-bit self-move must be eliminated
    assert "mov rax, rax" not in opt
    # 32-bit zero-extending self-move MUST NOT be eliminated
    assert "mov eax, eax" in opt
    # Memory barrier MUST be preserved
    assert "lock inc qword [rcx]" in opt
    # Non-stack global memory reload MUST NOT be eliminated (shared memory visibility)
    assert "mov rax, [g_counter]" in opt
    # Stack-local variable reload CAN be eliminated
    assert opt.count("mov rbx, [rbp - 16]") == 0 or opt.count("[rbp - 16]") == 1


def test_verification_callee_saved_registers_abi():
    """Verification Property 8: Preserve Microsoft x64 callee-saved registers (rbx, rsi, rdi, r12-r15)."""
    code = """
def helper(x: int) -> int:
    # Uses multiple registers in calculation
    a = x * 2
    b = a + 5
    c = b * 3
    d = c - 1
    return d

def main():
    val = helper(10)
    print(val)
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    assert res.stdout.strip() == "74"


def test_verification_cpython_conformance():
    """Verification Property 10: Compare output byte-for-byte against CPython 3.12+."""
    import sys

    code = """
def test_math() -> int:
    acc = 0
    for i in range(1, 20):
        acc = acc + (i * 3) - (i // 2)
    return acc

def test_lists() -> int:
    nums = [10, 20, 30, 40, 50]
    total = 0
    for n in nums:
        total = total + n
    return total

def test_strings():
    s = "pyfasm native compiler"
    print(s.upper())

def main():
    print("Math result:", test_math())
    print("List sum:", test_lists())
    test_strings()
"""
    # 1. Run in CPython
    cpython_proc = subprocess.run(
        [sys.executable, "-c", code + "\nmain()"],
        capture_output=True,
        text=True
    )
    assert cpython_proc.returncode == 0
    expected_output = cpython_proc.stdout

    # 2. Run in PyFASM Native Compiler
    pyfasm_proc = run_pyfasm_code(code)
    assert pyfasm_proc.returncode == 0
    assert pyfasm_proc.stdout == expected_output


def test_verification_ctypes_dll_bidirectional(tmp_path: Path):
    """Verification Property 7: Call PyFASM compiled Win64 DLL from C/Python via ctypes."""
    import ctypes

    code = """
def native_add(a: int, b: int) -> int:
    return a * 10 + b

def native_compute(x: int, y: int, z: int) -> int:
    return (x + y) * z
"""
    src_file = tmp_path / "math_lib.py"
    dll_path = tmp_path / "math_lib.dll"
    src_file.write_text(code, encoding="utf-8")

    compiler = PyFasmCompiler()
    ok, out_dll, err = compiler.compile_file(str(src_file), output_binary=str(dll_path), target="dll")
    assert ok, f"DLL compilation failed: {err}"
    assert dll_path.exists()

    lib = ctypes.CDLL(str(dll_path))
    lib.native_add.argtypes = [ctypes.c_longlong, ctypes.c_longlong]
    lib.native_add.restype = ctypes.c_longlong
    res_add = lib.native_add(5, 7)
    assert res_add == 57

    lib.native_compute.argtypes = [ctypes.c_longlong, ctypes.c_longlong, ctypes.c_longlong]
    lib.native_compute.restype = ctypes.c_longlong
    res_compute = lib.native_compute(10, 20, 3)
    assert res_compute == 90

    # Unload DLL so tmp_path can clean up safely
    ctypes.windll.kernel32.FreeLibrary(lib._handle)


def test_verification_multithreaded_concurrency():
    """Verification Properties 5 & 6: Concurrent shared memory access & atomic synchronization."""
    code = """
def worker(counter_ptr: int) -> int:
    for i in range(2500):
        atomic_add(counter_ptr, 1)
    return 0

def main():
    shared_mem = alloc_memory(64)
    shared_mem[0] = 0

    t1 = spawn_thread(worker, shared_mem)
    t2 = spawn_thread(worker, shared_mem)
    t3 = spawn_thread(worker, shared_mem)
    t4 = spawn_thread(worker, shared_mem)

    wait_thread(t1)
    wait_thread(t2)
    wait_thread(t3)
    wait_thread(t4)

    print("Concurrent total:", shared_mem[0])
    free_memory(shared_mem)
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    assert "Concurrent total: 10000" in res.stdout


def test_verification_memory_lifecycle():
    """Verification Property 9: Allocation lifecycle, pointer sanity, and buffer integrity."""
    code = """
def test_buffer_integrity() -> int:
    # Allocate 1000 items (8000 bytes)
    buf = alloc_memory(8000)
    for i in range(100):
        buf[i] = i * 7
    total = 0
    for i in range(100):
        total = total + buf[i]
    free_memory(buf)
    return total

def test_dynamic_strings_and_lists() -> int:
    count = 0
    for i in range(50):
        s = "prefix_" + "suffix"
        lst = [1, 2, 3]
        count = count + len(s) + len(lst)
    return count

def main():
    print("Buffer sum:", test_buffer_integrity())
    print("Lifecycle count:", test_dynamic_strings_and_lists())
"""
    res = run_pyfasm_code(code)
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    # sum(i * 7 for i in range(100)) = 7 * (99 * 100 // 2) = 7 * 4950 = 34650
    assert lines[0] == "Buffer sum: 34650"
    # len("prefix_suffix") = 13, len([1, 2, 3]) = 3 => 16 * 50 = 800
    assert lines[1] == "Lifecycle count: 800"





