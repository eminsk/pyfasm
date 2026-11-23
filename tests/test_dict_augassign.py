import subprocess
from pathlib import Path

from pyfasm.compiler import PyFasmCompiler


def test_dict_key_augassign_execution(tmp_path: Path):
    source = """
def main() -> int:
    state = {"ticks": 1, "name": "a", "items": 10}
    state["ticks"] += 5
    state["ticks"] *= 2
    state["items"] -= 3
    state["name"] += "b"
    print("Ticks:", state["ticks"])
    print("Items:", state["items"])
    print("Name:", state["name"])
    return 0
"""
    src_file = tmp_path / "dict_aug.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "dict_aug.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Ticks: 12" in res.stdout
    assert "Items: 7" in res.stdout
    assert "Name: ab" in res.stdout
