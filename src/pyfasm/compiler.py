"""
Compiler API orchestrating parsing, code generation, and FASM assembly.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Tuple, Optional
from pyfasm.ast_parser import AstAnalyzer, ParsedModule
from pyfasm.codegen_x64 import X64CodeGen
from pyfasm.fasm_runner import FasmRunner


class PyFasmCompiler:
    """End-to-end compiler from Python to pure FASM x64 native binary."""

    def __init__(self, fasm_path: Optional[str] = None, include_path: Optional[str] = None):
        self.fasm_runner = FasmRunner(fasm_path=fasm_path, include_path=include_path)

    def compile_source_to_asm(self, source_code: str, target: str = "win64") -> str:
        """Parses Python source code and returns complete FASM x64 assembly."""
        analyzer = AstAnalyzer()
        parsed_mod = analyzer.parse_source(source_code)
        codegen = X64CodeGen(parsed_mod, target=target)
        return codegen.generate()

    def compile_file(
        self,
        source_path: str,
        output_binary: Optional[str] = None,
        target: str = "win64",
        keep_asm: bool = True
    ) -> Tuple[bool, str, str]:
        """
        Compiles a Python file to native binary.
        Returns (success: bool, output_binary_path: str, log_message: str).
        """
        src = Path(source_path).resolve()
        if not src.exists():
            return False, "", f"Source file not found: {source_path}"

        source_code = src.read_text(encoding="utf-8")
        asm_code = self.compile_source_to_asm(source_code, target=target)

        if not output_binary:
            if target == "win64":
                out_bin = src.with_suffix(".exe")
            else:
                out_bin = src.with_suffix(".bin")
        else:
            out_bin = Path(output_binary).resolve()

        asm_file = out_bin.with_suffix(".asm")
        success, log = self.fasm_runner.assemble(
            asm_content=asm_code,
            output_binary=str(out_bin),
            asm_file_path=str(asm_file) if keep_asm else None,
            keep_asm=keep_asm
        )

        return success, str(out_bin), log
