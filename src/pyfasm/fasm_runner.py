"""
FASM execution wrapper for PyFASM compiler.
Locates FASM assembler and executes assembly jobs.
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class FasmRunner:
    """Manages discovery and invocation of Flat Assembler (FASM)."""

    DEFAULT_SEARCH_PATHS = [
        r"C:\proekts\FASM\FASM.EXE",
        r"C:\asm\hdd\FASM.EXE",
        r"C:\Program Files\FASM\fasm.exe",
    ]

    def __init__(self, fasm_path: Optional[str] = None, include_path: Optional[str] = None):
        self.fasm_path = self._locate_fasm(fasm_path)
        self.include_path = self._locate_include(include_path)

    def _locate_fasm(self, explicit_path: Optional[str]) -> str:
        if explicit_path and os.path.exists(explicit_path):
            return str(Path(explicit_path).resolve())

        # Check system PATH
        path_which = shutil.which("fasm") or shutil.which("fasm.exe")
        if path_which:
            return str(Path(path_which).resolve())

        # Check default paths
        for p in self.DEFAULT_SEARCH_PATHS:
            if os.path.exists(p):
                return str(Path(p).resolve())

        raise FileNotFoundError(
            "FASM executable not found! Please install FASM or specify its path."
        )

    def _locate_include(self, explicit_include: Optional[str]) -> str:
        if explicit_include and os.path.exists(explicit_include):
            return str(Path(explicit_include).resolve())

        # Check adjacent to fasm_path
        fasm_dir = Path(self.fasm_path).parent
        candidate = fasm_dir / "INCLUDE"
        if candidate.exists() and candidate.is_dir():
            return str(candidate.resolve())

        # Check C:\proekts\FASM\INCLUDE
        if os.path.exists(r"C:\proekts\FASM\INCLUDE"):
            return r"C:\proekts\FASM\INCLUDE"

        return str(fasm_dir.resolve())

    def assemble(
        self,
        asm_content: str,
        output_binary: str,
        asm_file_path: Optional[str] = None,
        keep_asm: bool = True
    ) -> Tuple[bool, str]:
        """
        Assembles asm_content into output_binary using FASM.
        Returns (success: bool, log_message: str).
        """
        out_bin = Path(output_binary).resolve()
        out_bin.parent.mkdir(parents=True, exist_ok=True)

        if asm_file_path:
            asm_path = Path(asm_file_path).resolve()
        else:
            asm_path = out_bin.with_suffix(".asm")

        asm_path.parent.mkdir(parents=True, exist_ok=True)
        asm_path.write_text(asm_content, encoding="ascii", errors="replace")

        env = os.environ.copy()
        env["INCLUDE"] = self.include_path

        cmd = [self.fasm_path, str(asm_path), str(out_bin)]

        try:
            res = subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )
            success = (res.returncode == 0) and out_bin.exists()
            log = res.stdout.strip()
            if not keep_asm and asm_file_path is None:
                try:
                    asm_path.unlink()
                except OSError:
                    pass
            return success, log
        except Exception as e:
            return False, f"Execution failed: {e}"
