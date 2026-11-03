import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_sets_and_operations(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Set literal and length
    s = {10, 20, 30}
    print("Initial set len:", len(s))

    # 2. Add elements
    s.add(40)
    s.add(20)  # duplicate should not increase size
    print("After adds len:", len(s))

    # 3. Membership test (in / not in)
    if 20 in s:
        print("20 is in set: YES")
    if 99 not in s:
        print("99 not in set: YES")

    # 4. Remove element
    s.remove(20)
    print("After remove len:", len(s))
    if 20 not in s:
        print("20 was removed: YES")

    # 5. Set comprehension
    evens = {x * 2 for x in range(6) if x > 0}
    print("Evens set len:", len(evens))
    if 4 in evens:
        print("4 in evens: YES")
    if 10 in evens:
        print("10 in evens: YES")

    # 6. Iteration over set
    total = 0
    test_set = {5, 15, 25}
    for item in test_set:
        total += item
    print("Sum of test_set:", total)

    return 0
"""
    src_file = tmp_path / "sets_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "sets_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Initial set len: 3" in res.stdout
    assert "After adds len: 4" in res.stdout
    assert "20 is in set: YES" in res.stdout
    assert "99 not in set: YES" in res.stdout
    assert "After remove len: 3" in res.stdout
    assert "20 was removed: YES" in res.stdout
    assert "Evens set len: 5" in res.stdout
    assert "4 in evens: YES" in res.stdout
    assert "10 in evens: YES" in res.stdout
    assert "Sum of test_set: 45" in res.stdout


def test_starred_unpacking_and_list_containment(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Head, *tail
    nums = [10, 20, 30, 40]
    head, *tail = nums
    print("Head:", head)
    print("Tail len:", len(tail))
    print("Tail[0]:", tail[0])
    print("Tail[2]:", tail[2])

    # 2. *init, last
    *init, last = nums
    print("Init len:", len(init))
    print("Init[0]:", init[0])
    print("Init[1]:", init[1])
    print("Last:", last)

    # 3. First, *mid, last
    first, *mid, end_val = [100, 200, 300, 400]
    print("First:", first)
    print("Mid len:", len(mid))
    print("Mid[0]:", mid[0])
    print("Mid[1]:", mid[1])
    print("End val:", end_val)

    # 4. List pop and containment
    arr = [1, 2, 3, 4]
    popped = arr.pop()
    print("Popped:", popped)
    print("Arr len after pop:", len(arr))
    if 3 in arr:
        print("3 in arr: YES")
    if 4 not in arr:
        print("4 not in arr: YES")

    return 0
"""
    src_file = tmp_path / "starred_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "starred_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Head: 10" in res.stdout
    assert "Tail len: 3" in res.stdout
    assert "Tail[0]: 20" in res.stdout
    assert "Tail[2]: 40" in res.stdout
    assert "Init len: 3" in res.stdout
    assert "Init[0]: 10" in res.stdout
    assert "Init[1]: 20" in res.stdout
    assert "Last: 40" in res.stdout
    assert "First: 100" in res.stdout
    assert "Mid len: 2" in res.stdout
    assert "Mid[0]: 200" in res.stdout
    assert "Mid[1]: 300" in res.stdout
    assert "End val: 400" in res.stdout
    assert "Popped: 4" in res.stdout
    assert "Arr len after pop: 3" in res.stdout
    assert "3 in arr: YES" in res.stdout
    assert "4 not in arr: YES" in res.stdout


def test_match_case_and_globals(tmp_path: Path):
    source = """
counter = 100

def modify_global(delta: int) -> None:
    global counter
    counter += delta

def describe_number(val: int) -> int:
    match val:
        case 1:
            return 111
        case 2 | 3:
            return 222
        case x if x > 50:
            return 888
        case _:
            return 999

def main() -> int:
    # 1. Global variable modification
    print("Initial counter:", counter)
    modify_global(50)
    print("Updated counter:", counter)

    # 2. Pattern matching
    print("Match 1:", describe_number(1))
    print("Match 2:", describe_number(2))
    print("Match 3:", describe_number(3))
    print("Match 75:", describe_number(75))
    print("Match 10:", describe_number(10))

    return 0
"""
    src_file = tmp_path / "match_global_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "match_global_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Initial counter: 100" in res.stdout
    assert "Updated counter: 150" in res.stdout
    assert "Match 1: 111" in res.stdout
    assert "Match 2: 222" in res.stdout
    assert "Match 3: 222" in res.stdout
    assert "Match 75: 888" in res.stdout
    assert "Match 10: 999" in res.stdout
