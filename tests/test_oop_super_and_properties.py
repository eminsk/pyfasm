import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_oop_super_and_properties(tmp_path: Path):
    source = """
class Base:
    def __init__(self, x):
        self.x = x

    def calc(self, m):
        return self.x * m

    def identify(self):
        return "I am Base"

class Sub(Base):
    def __init__(self, x, y):
        super().__init__(x)
        self.y = y

    def calc(self, m):
        return super().calc(m) + self.y

class GrandSub(Sub):
    # Inherits __init__(x, y) and calc(m) from Sub
    def bonus(self):
        return self.x + self.y + 100

class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, val):
        self._radius = val

    @property
    def diameter(self):
        return self._radius * 2

def main() -> int:
    # 1. Base and Sub with super().__init__ and super().calc
    print("--- OOP Super & Inheritance ---")
    b = Base(10)
    print("Base calc:", b.calc(3))
    print("Base identify:", b.identify())

    s = Sub(10, 5)
    print("Sub x:", s.x)
    print("Sub y:", s.y)
    print("Sub calc:", s.calc(3))
    # Sub inherits identify from Base directly
    print("Sub identify:", s.identify())

    # 2. Multi-level inheritance GrandSub
    g = GrandSub(20, 7)
    print("GrandSub calc:", g.calc(2))
    print("GrandSub bonus:", g.bonus())
    print("GrandSub identify:", g.identify())

    # 3. @property and @prop.setter
    print("--- Properties ---")
    c = Circle(5)
    print("Circle radius:", c.radius)
    print("Circle diameter:", c.diameter)

    c.radius = 12
    print("Circle new radius:", c.radius)
    print("Circle new diameter:", c.diameter)

    c.radius += 8
    print("Circle aug radius:", c.radius)
    print("Circle aug diameter:", c.diameter)

    # 4. String formatting with .format(...) and %
    print("--- String Formatting ---")
    msg1 = "Hello, {}! Code: {}".format("PyFASM", 100)
    print("Msg1:", msg1)

    msg2 = "{0} + {1} = {2}".format(10, 20, 30)
    print("Msg2:", msg2)

    msg3 = "User: %s, Score: %d" % ("Alice", 95)
    print("Msg3:", msg3)

    return 0
"""
    src_file = tmp_path / "oop_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "oop_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0, f"Execution failed with code {res.returncode}:\n{res.stderr}"
    out = res.stdout

    # Verify Base and Sub
    assert "Base calc: 30" in out
    assert "Base identify: I am Base" in out
    assert "Sub x: 10" in out
    assert "Sub y: 5" in out
    assert "Sub calc: 35" in out
    assert "Sub identify: I am Base" in out

    # Verify GrandSub
    assert "GrandSub calc: 47" in out
    assert "GrandSub bonus: 127" in out
    assert "GrandSub identify: I am Base" in out

    # Verify Properties
    assert "Circle radius: 5" in out
    assert "Circle diameter: 10" in out
    assert "Circle new radius: 12" in out
    assert "Circle new diameter: 24" in out
    assert "Circle aug radius: 20" in out
    assert "Circle aug diameter: 40" in out

    # Verify String Formatting
    assert "Msg1: Hello, PyFASM! Code: 100" in out
    assert "Msg2: 10 + 20 = 30" in out
    assert "Msg3: User: Alice, Score: 95" in out
