import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_lambdas_and_first_class_functions(tmp_path: Path):
    source = """
def square(x: int) -> int:
    return x * x

def cube(x: int) -> int:
    return x * x * x

def apply_op(fn, val: int) -> int:
    return fn(val)

def apply_binary(fn, a: int, b: int) -> int:
    return fn(a, b)

def main() -> int:
    # 1. Direct function pointer assignment & call
    my_fn = square
    print("Square 7:", my_fn(7))
    my_fn = cube
    print("Cube 4:", my_fn(4))

    # 2. Passing named functions as arguments (High-Order Functions)
    print("Apply square to 9:", apply_op(square, 9))
    print("Apply cube to 3:", apply_op(cube, 3))

    # 3. Lambda expressions (Lambda Lifting)
    double_fn = lambda x: x * 2
    print("Double 21:", double_fn(21))

    add_fn = lambda a, b: a + b
    mul_fn = lambda a, b: a * b
    print("Apply add lambda:", apply_binary(add_fn, 15, 25))
    print("Apply mul lambda:", apply_binary(mul_fn, 6, 7))

    # 4. Immediate lambda invocation
    diff = (lambda a, b: a - b)(100, 30)
    print("Immediate lambda diff:", diff)

    # 5. List of function pointers
    func_list = [square, cube]
    print("Func list [0](5):", func_list[0](5))
    print("Func list [1](5):", func_list[1](5))

    # 6. map() and filter() built-in higher order functions
    items = [1, 2, 3, 4, 5]
    doubled = map(lambda x: x * 10, items)
    print("Map len:", len(doubled))
    print("Map[0]:", doubled[0])
    print("Map[4]:", doubled[4])

    evens = filter(lambda x: x % 2 == 0, items)
    print("Filter len:", len(evens))
    print("Filter[0]:", evens[0])
    print("Filter[1]:", evens[1])

    return 0
"""
    src_file = tmp_path / "lambdas_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "lambdas_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Square 7: 49" in res.stdout
    assert "Cube 4: 64" in res.stdout
    assert "Apply square to 9: 81" in res.stdout
    assert "Apply cube to 3: 27" in res.stdout
    assert "Double 21: 42" in res.stdout
    assert "Apply add lambda: 40" in res.stdout
    assert "Apply mul lambda: 42" in res.stdout
    assert "Immediate lambda diff: 70" in res.stdout
    assert "Func list [0](5): 25" in res.stdout
    assert "Func list [1](5): 125" in res.stdout
    assert "Map len: 5" in res.stdout
    assert "Map[0]: 10" in res.stdout
    assert "Map[4]: 50" in res.stdout
    assert "Filter len: 2" in res.stdout
    assert "Filter[0]: 2" in res.stdout
    assert "Filter[1]: 4" in res.stdout
