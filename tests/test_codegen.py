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
