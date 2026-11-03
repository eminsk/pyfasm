import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_yield_from_and_generator_expressions(tmp_path: Path):
    source = """
def sub_gen():
    yield 10
    yield 20

def delegating_gen():
    yield 1
    yield from sub_gen()
    yield 2
    yield from [30, 40]
    yield 3

def nested_loop_gen():
    for i in [1, 2]:
        for j in [10, 20]:
            yield i * j

def main() -> int:
    # 1. Delegating generator with yield from
    print("--- Yield From ---")
    for val in delegating_gen():
        print("Del:", val)

    # 2. Generator expressions with closure/free variable capture
    print("--- Generator Expressions ---")
    factor = 3
    g = (x * factor for x in [1, 2, 3, 4] if x > 1)
    print("GenExp next 1:", next(g))
    print("GenExp next 2:", next(g))
    print("GenExp next 3:", next(g))

    # 3. Built-in sum, any, all with generator expressions
    print("--- Builtins on GenExp ---")
    s_gen = sum(x * x for x in range(5))
    print("Sum GenExp:", s_gen)

    s_list = sum([10, 20, 30, 40])
    print("Sum List:", s_list)

    has_large = any(x > 50 for x in [10, 25, 60, 5])
    has_neg = any(x < 0 for x in [10, 25, 60, 5])
    print("Any True:", has_large)
    print("Any False:", has_neg)

    all_pos = all(x > 0 for x in [10, 25, 60, 5])
    all_even = all(x % 2 == 0 for x in [10, 25, 60, 5])
    print("All True:", all_pos)
    print("All False:", all_even)

    # 4. list(generator) conversion
    conv = list(x * 10 for x in [1, 2, 3])
    print("Conv len:", len(conv))
    print("Conv[0]:", conv[0])
    print("Conv[1]:", conv[1])
    print("Conv[2]:", conv[2])

    # 5. Tuple unpacking in for loop
    print("--- Tuple Unpack in For ---")
    pairs = [(1, 100), (2, 200), (3, 300)]
    sum_a = 0
    sum_b = 0
    for a, b in pairs:
        sum_a += a
        sum_b += b
    print("Sum A:", sum_a)
    print("Sum B:", sum_b)

    # 6. Yield inside nested for loops
    print("--- Nested For Yield ---")
    for n in nested_loop_gen():
        print("Nested:", n)

    return 0
"""
    src_file = tmp_path / "genexp_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "genexp_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    out = res.stdout

    # Verify Yield From
    assert "Del: 1" in out
    assert "Del: 10" in out
    assert "Del: 20" in out
    assert "Del: 2" in out
    assert "Del: 30" in out
    assert "Del: 40" in out
    assert "Del: 3" in out

    # Verify GenExp
    assert "GenExp next 1: 6" in out
    assert "GenExp next 2: 9" in out
    assert "GenExp next 3: 12" in out

    # Verify Builtins
    assert "Sum GenExp: 30" in out
    assert "Sum List: 100" in out
    assert "Any True: 1" in out
    assert "Any False: 0" in out
    assert "All True: 1" in out
    assert "All False: 0" in out

    # Verify list(gen)
    assert "Conv len: 3" in out
    assert "Conv[0]: 10" in out
    assert "Conv[1]: 20" in out
    assert "Conv[2]: 30" in out

    # Verify tuple unpack
    assert "Sum A: 6" in out
    assert "Sum B: 600" in out

    # Verify nested loop yield
    assert "Nested: 10" in out
    assert "Nested: 20" in out
    assert "Nested: 40" in out
