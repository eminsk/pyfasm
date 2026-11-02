import pytest
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_codegen_emits_valid_asm_structure():
    source = """
def main() -> int:
    x = 42
    print(x)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "format PE64 console 5.0" in asm
    assert "_pyfasm_entry_point:" in asm
    assert "main:" in asm
    assert "call _pyfasm_print_int" in asm
    assert "call [ExitProcess]" in asm


def test_codegen_linux_elf64_structure():
    source = """
def main() -> int:
    x = 100
    print(x)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="linux")

    assert "format ELF64 executable 3" in asm
    assert "segment readable executable" in asm
    assert "syscall" in asm
    assert "main:" in asm


def test_codegen_macos_macho64_structure():
    source = """
def main() -> int:
    x = 200
    print(x)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="macos")

    assert "format binary as 'macho'" in asm
    assert "MH_MAGIC_64" in asm or "0xFEEDFACF" in asm
    assert "LC_SEGMENT_64" in asm or "0x19" in asm
    assert "syscall" in asm
    assert "main:" in asm


def test_codegen_escapes_reserved_fasm_keywords(tmp_path: Path):
    source = """
def add(a: int, b: int) -> int:
    return a + b

def test(x: int) -> int:
    return x * 2

def main() -> int:
    s = add(10, 20)
    t = test(s)
    print(t)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "fn_add:" in asm
    assert "fn_test:" in asm
    assert "call fn_add" in asm
    assert "call fn_test" in asm

    # Verify that FASM compiles it without 'reserved word used as symbol'
    src_file = tmp_path / "reserved_app.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation with reserved keywords failed: {log}"


def test_codegen_emits_fallback_stubs_for_unresolved_symbols(tmp_path: Path):
    source = """
def main() -> int:
    p = Path('myfile.txt')
    print(123)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "call Path" in asm
    assert "Path:" in asm
    assert "fallback stub for external symbol 'Path'" in asm

    # Verify that FASM compiles the code with unresolved symbol stubs without error
    src_file = tmp_path / "stub_app.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation with external symbol stub failed: {log}"


def test_codegen_handles_numeric_prefix_and_invalid_symbols(tmp_path: Path):
    from pyfasm.codegen_x64 import safe_asm_label
    assert safe_asm_label("01_hello") == "_01_hello"
    assert safe_asm_label("123_calc") == "_123_calc"
    assert safe_asm_label("bad-symbol-name!") == "bad_symbol_name_"
    assert safe_asm_label("add") == "fn_add"

    source = """
def helper() -> int:
    return 777

def main() -> int:
    print(helper())
    return 0
"""
    src_file = tmp_path / "01_numeric_app.py"
    src_file.write_text(source, encoding="utf-8")
    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation of numeric-prefixed file failed: {log}"


def test_codegen_handles_boolean_constants_and_instruction_shadowing(tmp_path: Path):
    source = """
def main() -> int:
    flag = False
    flag_on = True
    s = str(123)
    if flag:
        return 1
    return 0
"""
    src_file = tmp_path / "bool_and_str.py"
    src_file.write_text(source, encoding="utf-8")
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")
    assert "mov rax, 0" in asm
    assert "mov rax, 1" in asm
    assert "call fn_str" in asm
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation failed: {log}"
