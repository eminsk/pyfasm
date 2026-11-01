"""
PyFASM: Free-Threaded (No-GIL) Python to Pure FASM x64 Native Compiler.
"""
from pyfasm.compiler import PyFasmCompiler
from pyfasm.cli import main

__all__ = ["PyFasmCompiler", "main"]
