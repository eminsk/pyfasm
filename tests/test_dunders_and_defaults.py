import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_dunders_and_defaults(tmp_path: Path):
    source = """
# 1. Functions with default arguments & keyword arguments
def compute_fee(amount, tax=10, discount=2):
    return amount + tax - discount

def configure_server(host="localhost", port=8080):
    return port

# 2. Vector with __add__, __sub__, __eq__, and __str__
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __str__(self):
        return f"Vector({self.x}, {self.y})"

# 3. Custom collection with __len__, __getitem__, __setitem__, __contains__
class MyArray:
    def __init__(self, cap):
        self.cap = cap
        self.item0 = 0
        self.item1 = 0
        self.item2 = 0

    def __len__(self):
        return self.cap

    def __getitem__(self, idx):
        if idx == 0:
            return self.item0
        if idx == 1:
            return self.item1
        return self.item2

    def __setitem__(self, idx, val):
        if idx == 0:
            self.item0 = val
        elif idx == 1:
            self.item1 = val
        else:
            self.item2 = val

    def __contains__(self, val):
        if self.item0 == val:
            return True
        if self.item1 == val:
            return True
        if self.item2 == val:
            return True
        return False

def main() -> int:
    # 1. Test default and keyword arguments
    print("--- Default & Keyword Args ---")
    print("Fee 1:", compute_fee(100))
    print("Fee 2:", compute_fee(100, 20))
    print("Fee 3:", compute_fee(100, 20, 5))
    print("Fee KW:", compute_fee(100, discount=5))
    print("Port KW:", configure_server(port=9000))

    # 2. Test operator overloading (__add__, __sub__, __eq__, __str__)
    print("--- Operator Overloading ---")
    v1 = Vector(10, 20)
    v2 = Vector(3, 5)
    v3 = v1 + v2
    print("V3 x:", v3.x)
    print("V3 y:", v3.y)

    v4 = v1 - v2
    print("V4 x:", v4.x)
    print("V4 y:", v4.y)

    v_eq1 = Vector(10, 20)
    v_eq2 = Vector(10, 20)
    v_diff = Vector(10, 25)
    print("Eq True:", v1 == v_eq2)
    print("Eq False:", v1 == v_diff)
    print("Ne True:", v1 != v_diff)
    print("Ne False:", v1 != v_eq2)

    print("Str v1:", str(v1))
    print("Print v3:", v3)

    # 3. Test container dunders (__len__, __getitem__, __setitem__, __contains__)
    print("--- Container Dunders ---")
    arr = MyArray(3)
    print("Len arr:", len(arr))

    arr[0] = 111
    arr[1] = 222
    arr[2] = 333
    print("Arr[0]:", arr[0])
    print("Arr[1]:", arr[1])
    print("Arr[2]:", arr[2])

    print("In 222:", 222 in arr)
    print("In 999:", 999 in arr)
    print("NotIn 999:", 999 not in arr)
    print("NotIn 222:", 222 not in arr)

    return 0
"""
    src_file = tmp_path / "dunders_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "dunders_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0, f"Execution failed with code {res.returncode}:\n{res.stderr}"
    out = res.stdout

    # Verify default & keyword arguments
    assert "Fee 1: 108" in out      # 100 + 10 - 2
    assert "Fee 2: 118" in out      # 100 + 20 - 2
    assert "Fee 3: 115" in out      # 100 + 20 - 5
    assert "Fee KW: 105" in out     # 100 + 10 - 5
    assert "Port KW: 9000" in out

    # Verify operator overloading
    assert "V3 x: 13" in out
    assert "V3 y: 25" in out
    assert "V4 x: 7" in out
    assert "V4 y: 15" in out
    assert "Eq True: 1" in out
    assert "Eq False: 0" in out
    assert "Ne True: 1" in out
    assert "Ne False: 0" in out
    assert "Str v1: Vector(10, 20)" in out
    assert "Print v3: Vector(13, 25)" in out

    # Verify container dunders
    assert "Len arr: 3" in out
    assert "Arr[0]: 111" in out
    assert "Arr[1]: 222" in out
    assert "Arr[2]: 333" in out
    assert "In 222: 1" in out
    assert "In 999: 0" in out
    assert "NotIn 999: 1" in out
    assert "NotIn 222: 0" in out
