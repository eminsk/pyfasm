"""
PyFASM: Free-Threaded (No-GIL) Python to Pure FASM x64 Native Compiler.
"""
__version__ = "0.1.23"

from pyfasm.compiler import PyFasmCompiler
from pyfasm.bundler import ProjectBundler
from pyfasm.fasm_exporter import FasmExporter
from pyfasm.optimizer import PeepholeOptimizer, optimize_fasm_code
from pyfasm.cli import main

__all__ = ["PyFasmCompiler", "ProjectBundler", "FasmExporter", "PeepholeOptimizer", "optimize_fasm_code", "main"]
