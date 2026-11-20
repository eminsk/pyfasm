"""
PyFASM64: Free-Threaded (No-GIL) Python to Pure FASM x64 Native Compiler & Bundler.
"""
from pyfasm import (
    __version__,
    PyFasmCompiler,
    ProjectBundler,
    FasmExporter,
    PeepholeOptimizer,
    optimize_fasm_code,
    main,
)

__all__ = [
    "__version__",
    "PyFasmCompiler",
    "ProjectBundler",
    "FasmExporter",
    "PeepholeOptimizer",
    "optimize_fasm_code",
    "main",
]
