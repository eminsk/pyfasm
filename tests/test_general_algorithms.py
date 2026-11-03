import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_for_in_container_and_subscript_augassign(tmp_path: Path):
    source = """
def main() -> int:
    nums = [10, 20, 30, 40, 50]
    total = 0
    for x in nums:
        total = total + x
    print("Sum of elements:", total)

    # Test loop with break
    b_sum = 0
    for x in nums:
        if x > 30:
            break
        b_sum = b_sum + x
    print("Break sum:", b_sum)

    # Test loop with continue
    c_sum = 0
    for x in nums:
        if x == 30:
            continue
        c_sum = c_sum + x
    print("Continue sum:", c_sum)

    # Test subscript AugAssign: arr[i] += delta
    counts = [0, 0, 0, 0, 0]
    counts[0] += 5
    counts[1] += 12
    counts[4] += 99
    print("Counts:", counts[0], counts[1], counts[4])
    return 0
"""
    src_file = tmp_path / "for_container.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "for_container.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Sum of elements: 150" in res.stdout
    assert "Break sum: 60" in res.stdout
    assert "Continue sum: 120" in res.stdout
    assert "Counts: 5 12 99" in res.stdout


def test_bubble_sort_and_binary_search(tmp_path: Path):
    source = """
def main() -> int:
    # Bubble sort
    arr = [64, 34, 25, 12, 22, 11, 90]
    n = len(arr)
    i = 0
    while i < n - 1:
        j = 0
        while j < n - i - 1:
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
            j = j + 1
        i = i + 1

    print("Sorted:", arr[0], arr[1], arr[2], arr[3], arr[4], arr[5], arr[6])

    # Binary search for 25
    target = 25
    low = 0
    high = n - 1
    found_idx = -1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            found_idx = mid
            break
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    print("Found target 25 at index:", found_idx)
    return 0
"""
    src_file = tmp_path / "sort_search.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "sort_search.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Sorted: 11 12 22 25 34 64 90" in res.stdout
    assert "Found target 25 at index: 3" in res.stdout


def test_string_methods_and_transforms(tmp_path: Path):
    source = """
def main() -> int:
    s = "FlatAssembler"
    is_flat = s.startswith("Flat")
    is_py = s.startswith("Python")
    has_asm = s.endswith("Assembler")
    has_c = s.endswith("C")

    print("Starts with Flat:", is_flat)
    print("Starts with Python:", is_py)
    print("Ends with Assembler:", has_asm)
    print("Ends with C:", has_c)

    up = s.upper()
    print("Upper:", up)
    low = s.lower()
    print("Lower:", low)
    return 0
"""
    src_file = tmp_path / "str_methods.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "str_methods.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Starts with Flat: 1" in res.stdout
    assert "Starts with Python: 0" in res.stdout
    assert "Ends with Assembler: 1" in res.stdout
    assert "Ends with C: 0" in res.stdout
    assert "Upper: FLATASSEMBLER" in res.stdout
    assert "Lower: flatassembler" in res.stdout
