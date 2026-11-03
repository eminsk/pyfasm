import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_generators_and_yield(tmp_path: Path):
    source = """
def simple_gen():
    yield 100
    yield 200
    yield 300

def count_up(n: int):
    i = 1
    while i <= n:
        yield i * 10
        i += 1

def fib_gen(count: int):
    a = 0
    b = 1
    c = 0
    while c < count:
        yield a
        nxt = a + b
        a = b
        b = nxt
        c += 1

def main() -> int:
    # 1. Sequential yields with next()
    g = simple_gen()
    print("Next 1:", next(g))
    print("Next 2:", next(g))
    print("Next 3:", next(g))

    # 2. While loop generator with arguments
    g2 = count_up(4)
    print("Count 1:", next(g2))
    print("Count 2:", next(g2))
    print("Count 3:", next(g2))
    print("Count 4:", next(g2))

    # 3. Iteration over generator in for loop
    total = 0
    for x in count_up(5):
        total += x
    print("Total from count_up(5):", total)

    # 4. Fibonacci generator
    fib_sum = 0
    for f in fib_gen(7):
        fib_sum += f
    print("Fib sum 7:", fib_sum)

    return 0
"""
    src_file = tmp_path / "gen_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "gen_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Next 1: 100" in res.stdout
    assert "Next 2: 200" in res.stdout
    assert "Next 3: 300" in res.stdout
    assert "Count 1: 10" in res.stdout
    assert "Count 2: 20" in res.stdout
    assert "Count 3: 30" in res.stdout
    assert "Count 4: 40" in res.stdout
    assert "Total from count_up(5): 150" in res.stdout
    assert "Fib sum 7: 20" in res.stdout
