import sys
import subprocess
from pathlib import Path
import pytest
from pyfasm.compiler import PyFasmCompiler


@pytest.mark.skipif(sys.platform != "win32", reason="Native Win32 CreateThread multithreading execution test")
def test_end_to_end_multithreading_no_gil(tmp_path: Path):
    source = """
def worker(counter_ptr: int) -> int:
    for i in range(10000):
        atomic_add(counter_ptr, 1)
    return 0

def main() -> int:
    # Allocate 64 bytes for shared counter
    shared_mem = alloc_memory(64)
    shared_mem[0] = 0

    # Spawn 4 native OS worker threads (No GIL, true CPU parallelism)
    t1 = spawn_thread(worker, shared_mem)
    t2 = spawn_thread(worker, shared_mem)
    t3 = spawn_thread(worker, shared_mem)
    t4 = spawn_thread(worker, shared_mem)

    # Wait for all threads to complete
    wait_thread(t1)
    wait_thread(t2)
    wait_thread(t3)
    wait_thread(t4)

    total = shared_mem[0]
    print(total)
    free_memory(shared_mem)
    return 0
"""
    src_file = tmp_path / "test_threads.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "test_threads.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")

    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    res = subprocess.run([bin_path], capture_output=True, text=True)
    assert res.returncode == 0
    # 4 threads * 10,000 = 40,000
    assert "40000" in res.stdout.strip()
