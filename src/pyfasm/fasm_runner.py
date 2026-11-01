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
        r"C:\FASM\FASM.EXE",
        r"C:\asm\FASM.EXE",
        r"C:\Program Files\FASM\fasm.exe",
    ]

    def __init__(self, fasm_path: Optional[str] = None, include_path: Optional[str] = None):
        self.fasm_path = self._locate_fasm(fasm_path)
        self.include_path = self._locate_include(include_path)

    def _locate_fasm(self, explicit_path: Optional[str]) -> str:
        if explicit_path and os.path.exists(explicit_path):
            return str(Path(explicit_path).resolve())

        # Check bundled repository tools/fasm
        repo_tools = Path(__file__).resolve().parents[2] / "tools" / "fasm" / ("FASM.EXE" if os.name == "nt" else "fasm")
        if repo_tools.exists():
            return str(repo_tools.resolve())

        # Check system PATH
        path_which = shutil.which("fasm") or shutil.which("fasm.exe")
        if path_which:
            return str(Path(path_which).resolve())

        # Check default paths
        for p in self.DEFAULT_SEARCH_PATHS:
            if os.path.exists(p):
                return str(Path(p).resolve())

        # Check user cache ~/.pyfasm/fasm
        user_fasm_dir = Path.home() / ".pyfasm" / "fasm"
        for cand_name in ("fasm.exe", "FASM.EXE", "fasm"):
            cand = user_fasm_dir / cand_name
            if cand.exists():
                return str(cand.resolve())

        # Auto-download on demand if not found
        try:
            return self._auto_download_fasm(user_fasm_dir)
        except Exception:
            pass

        raise FileNotFoundError(
            "FASM executable not found! Please install FASM or specify its path."
        )

    def _auto_download_fasm(self, target_dir: Path) -> str:
        import urllib.request
        import zipfile
        import tarfile

        target_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            url = "https://flatassembler.net/fasmw17332.zip"
            zip_dest = target_dir / "fasmw.zip"
            urllib.request.urlretrieve(url, zip_dest)
            with zipfile.ZipFile(zip_dest, "r") as zf:
                zf.extractall(target_dir)
            for cand in target_dir.rglob("fasm.exe"):
                return str(cand.resolve())
            for cand in target_dir.rglob("FASM.EXE"):
                return str(cand.resolve())
        else:
            url = "https://flatassembler.net/fasm-1.73.32.tgz"
            tgz_dest = target_dir / "fasm.tgz"
            urllib.request.urlretrieve(url, tgz_dest)
            with tarfile.open(tgz_dest, "r:gz") as tf:
                tf.extractall(target_dir)
            for cand in target_dir.rglob("fasm"):
                if cand.is_file():
                    try:
                        os.chmod(cand, 0o755)
                    except Exception:
                        pass
                    return str(cand.resolve())
        raise FileNotFoundError("Could not auto-download FASM")

    def _locate_include(self, explicit_include: Optional[str]) -> str:
        if explicit_include and os.path.exists(explicit_include):
            return str(Path(explicit_include).resolve())

        # Check adjacent to fasm_path
        fasm_dir = Path(self.fasm_path).parent
        candidate = fasm_dir / "INCLUDE"
        if candidate.exists() and candidate.is_dir():
            return str(candidate.resolve())

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
