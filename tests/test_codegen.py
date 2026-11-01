import pytest
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
