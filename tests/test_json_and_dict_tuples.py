import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_native_json_parser_execution(tmp_path: Path):
    source = """
import json

def main() -> int:
    raw = '{"name": "PyFASM", "version": 1, "active": true, "tags": ["native", "fast"], "extra": {"arch": "x64"}}'
    data = json.loads(raw)
    
    # Int and string access
    print("Name:", data.get("name", "Unknown"))
    print("Version:", data.get("version", 0))
    print("Default test:", data.get("missing", 999))
    
    # List inside dict
    tags = data.get("tags")
    print("Tags count:", len(tags))
    print("Tag 0:", tags[0])
    print("Tag 1:", tags[1])
    
    # Nested dict
    extra = data.get("extra")
    print("Arch:", extra.get("arch"))
    
    # Tuple key dictionary indexing (e.g. for Excel cell matrices)
    matrix = {}
    matrix[(10, 20)] = 555
    print("Matrix cell (10, 20):", matrix[(10, 20)])
    
    return 0
"""
    src_file = tmp_path / "test_json.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "test_json.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Name: PyFASM" in res.stdout
    assert "Version: 1" in res.stdout
    assert "Default test: 999" in res.stdout
    assert "Tags count: 2" in res.stdout
    assert "Tag 0: native" in res.stdout
    assert "Tag 1: fast" in res.stdout
    assert "Arch: x64" in res.stdout
    assert "Matrix cell (10, 20): 555" in res.stdout
