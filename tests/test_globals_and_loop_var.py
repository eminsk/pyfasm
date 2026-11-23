"""
Regression tests for module-level state shared with functions:
1. Module globals read from functions when the script has no user main().
2. list.append / dict item assignment on a global container inside a function.
3. The loop variable of `for i in range(...)` keeps the last yielded value.
"""
import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def _compile_and_run(tmp_path: Path, name: str, source: str) -> str:
    src_file = tmp_path / f"{name}.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / f"{name}.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    return res.stdout


def test_module_globals_read_from_functions_without_main(tmp_path: Path):
    source = """
items = {"1": "apple", "2": "pear"}
nums = [1, 2, 3]
count = 5
name = "zed"
def f():
    return len(items)
def h():
    return len(nums)
def k():
    return count + 1
def m():
    return name
print(f(), h(), k(), m())
"""
    out = _compile_and_run(tmp_path, "globals_no_main", source)
    assert "2 3 6 zed" in out


def test_global_container_mutation_inside_function(tmp_path: Path):
    source = """
names = ["a"]
d = {}
def show():
    print(len(names), len(d))
def main():
    show()
    names.append("b")
    d["k"] = 1
    show()
main()
"""
    out = _compile_and_run(tmp_path, "global_append", source)
    assert out.split() == ["1", "0", "2", "1"]


def test_range_loop_variable_after_loop(tmp_path: Path):
    source = """
for i in range(3):
    pass
print(i)
def main():
    for j in range(4):
        pass
    print(j)
    k = 0
    for k in range(2, 10, 3):
        pass
    print(k)
main()
"""
    out = _compile_and_run(tmp_path, "range_loop_var", source)
    assert out.split() == ["2", "3", "8"]


def test_list_remove_and_reverse(tmp_path: Path):
    source = """
def main():
    nums = [5, 1, 9, 3]
    nums.remove(9)
    words = ["pear", "apple", "kiwi"]
    words.remove("apple")
    print(nums, words)
    nums.reverse()
    print(nums)
main()
"""
    out = _compile_and_run(tmp_path, "list_remove", source)
    lines = out.strip().splitlines()
    assert lines[0] == "[5, 1, 3] ['pear', 'kiwi']"
    assert lines[1] == "[3, 1, 5]"


def test_sorted_strings_dict_keys_and_reverse(tmp_path: Path):
    source = """
def main():
    nums = [5, 1, 3]
    print(sorted(["b", "a", "c"]), sorted(nums), sorted(nums, reverse=True))
    ws = ["pear", "apple", "kiwi", "Apple"]
    ws.sort()
    print(ws)
    d = {"2": "x", "1": "y", "3": "z"}
    print(sorted(d.keys()), sorted(d))
main()
"""
    out = _compile_and_run(tmp_path, "sorted_str", source)
    lines = out.strip().splitlines()
    assert lines[0] == "['a', 'b', 'c'] [1, 3, 5] [5, 3, 1]"
    assert lines[1] == "['Apple', 'apple', 'kiwi', 'pear']"
    assert lines[2] == "['1', '2', '3'] ['1', '2', '3']"
