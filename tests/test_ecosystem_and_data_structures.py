"""
Tests for PyFASM expanded ecosystem and advanced data structures:
- Native Dictionaries (FNV-1a hash map, dict.get, dict assignment, membership)
- Native Strings (lower, upper, startswith, endswith, strip, in, +, +=, f-strings)
- Ecosystem Adapters (darkdetect, requests, beautifulsoup4)
- Native Tuples and Lists
"""
import sys
import subprocess
from pathlib import Path
import pytest
from pyfasm.compiler import PyFasmCompiler


def test_dict_and_string_methods_codegen():
    source = """
def main() -> int:
    d = {"site": 42, "page": 1}
    d["page"] = 2
    val = d["site"]
    missing = d.get("absent", 999)
    has_site = "site" in d
    
    text = "  FastAPI Search  "
    stripped = text.strip()
    lowered = text.lower()
    uppered = text.upper()
    has_fast = "Fast" in text
    starts = text.startswith("  ")
    ends = text.endswith("  ")
    
    is_dark = darkdetect_isDark()
    theme_mode = darkdetect_theme()
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")
    
    assert "call _pyfasm_dict_create" in asm
    assert "call _pyfasm_dict_set" in asm
    assert "call _pyfasm_dict_get" in asm
    assert "call _pyfasm_dict_contains" in asm
    assert "call _pyfasm_str_strip" in asm
    assert "call _pyfasm_str_lower" in asm
    assert "call _pyfasm_str_upper" in asm
    assert "call _pyfasm_str_contains" in asm
    assert "call _pyfasm_str_startswith" in asm
    assert "call _pyfasm_str_endswith" in asm
    assert "call _pyfasm_is_dark_theme" in asm
    assert "call _pyfasm_darkdetect_theme" in asm


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_end_to_end_dict_execution(tmp_path: Path):
    source = """
def main() -> int:
    # 1. Create and populate dictionary
    params = {"page": 1, "size": 25}
    params["order"] = 777
    
    # 2. Lookup values
    p = params["page"]
    sz = params["size"]
    ord_val = params["order"]
    fallback = params.get("nonexistent", 888)
    
    print(p)
    print(sz)
    print(ord_val)
    print(fallback)
    return 0
"""
    src_file = tmp_path / "dict_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "dict_test.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert success, f"FASM compilation failed:\n{log}"
    assert Path(bin_path).exists()

    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert lines == ["1", "25", "777", "888"]


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_end_to_end_string_methods_execution(tmp_path: Path):
    source = """
def main() -> int:
    s = "hello"
    # String concatenation with +
    full = s + " world"
    print_str(full)
    
    # AugAssign +=
    greeting = "Hi"
    greeting += " there"
    print_str(greeting)
    
    # Membership 'in'
    if "world" in full:
        print(1)
    else:
        print(0)
        
    if "xyz" not in full:
        print(2)
    else:
        print(0)
    return 0
"""
    src_file = tmp_path / "str_methods_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "str_methods_test.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert success, f"FASM compilation failed:\n{log}"

    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert lines == ["hello world", "Hi there", "1", "2"]


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_end_to_end_fstring_execution(tmp_path: Path):
    source = """
def main() -> int:
    name = "StackOverflow"
    count = 42
    msg = f"Platform: {name}, Quota: {count}"
    print_str(msg)
    return 0
"""
    src_file = tmp_path / "fstr_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "fstr_test.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert success, f"FASM compilation failed:\n{log}"

    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    assert "Platform: StackOverflow, Quota: 42" in proc.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_end_to_end_tuples_execution(tmp_path: Path):
    source = """
def main() -> int:
    t = (100, 200, 300)
    print(t[0])
    print(t[1])
    print(t[2])
    print(len(t))
    return 0
"""
    src_file = tmp_path / "tuple_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "tuple_test.exe"

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert success, f"FASM compilation failed:\n{log}"

    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    lines = proc.stdout.strip().splitlines()
    assert lines == ["100", "200", "300", "3"]
