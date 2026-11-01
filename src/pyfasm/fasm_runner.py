"""
FASM execution wrapper for PyFASM compiler.
Locates FASM assembler and executes assembly jobs.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


class FasmRunner:
    """Manages discovery and invocation of Flat Assembler (FASM)."""

    DEFAULT_SEARCH_PATHS = [
        r"C:\FASM\FASM.EXE",
        r"C:\asm\FASM.EXE",
        r"C:\Program Files\FASM\fasm.exe",
        "/usr/bin/fasm",
        "/usr/local/bin/fasm",
    ]

    def __init__(self, fasm_path: Optional[str] = None, include_path: Optional[str] = None):
        self.fasm_path = self._locate_fasm(fasm_path)
        self.include_path = self._locate_include(include_path)

    def _locate_fasm(self, explicit_path: Optional[str]) -> str:
        if explicit_path and os.path.exists(explicit_path):
            return str(Path(explicit_path).resolve())

        # Check bundled repository tools/fasm
        repo_tools_dir = Path(__file__).resolve().parents[2] / "tools" / "fasm"
        if os.name == "nt":
            cand = repo_tools_dir / "FASM.EXE"
            if cand.exists():
                return str(cand.resolve())
        elif sys.platform == "darwin":
            for bin_name in ("fasm.darwin", "fasm"):
                cand = repo_tools_dir / bin_name
                if cand.exists():
                    try:
                        os.chmod(cand, 0o755)
                    except Exception:
                        pass
                    return str(cand.resolve())
        else:
            for bin_name in ("fasm.x64", "fasm"):
                cand = repo_tools_dir / bin_name
                if cand.exists():
                    try:
                        os.chmod(cand, 0o755)
                    except Exception:
                        pass
                    return str(cand.resolve())

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
        for cand_name in ("fasm.exe", "FASM.EXE", "fasm", "fasm.x64", "fasm.darwin"):
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
        elif sys.platform == "darwin":
            url = "https://raw.githubusercontent.com/STLVNUB/fasm-osx/master/fasm"
            dest = target_dir / "fasm"
            req = urllib.request.Request(url, headers={"User-Agent": "pyfasm"})
            with open(dest, "wb") as f:
                f.write(urllib.request.urlopen(req).read())
            try:
                os.chmod(dest, 0o755)
            except Exception:
                pass
            return str(dest.resolve())
        else:
            url = "https://flatassembler.net/fasm-1.73.32.tgz"
            tgz_dest = target_dir / "fasm.tgz"
            urllib.request.urlretrieve(url, tgz_dest)
            with tarfile.open(tgz_dest, "r:gz") as tf:
                tf.extractall(target_dir)
            for cand in target_dir.rglob("fasm.x64"):
                if cand.is_file():
                    try:
                        os.chmod(cand, 0o755)
                    except Exception:
                        pass
                    return str(cand.resolve())
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
            inc_path = Path(explicit_include).resolve()
        else:
            # Check adjacent to fasm_path
            fasm_dir = Path(self.fasm_path).parent
            candidate = fasm_dir / "INCLUDE"
            if candidate.exists() and candidate.is_dir():
                inc_path = candidate.resolve()
            else:
                # Check bundled tools/fasm/INCLUDE
                bundled_inc = Path(__file__).resolve().parents[2] / "tools" / "fasm" / "INCLUDE"
                if bundled_inc.exists() and bundled_inc.is_dir():
                    inc_path = bundled_inc.resolve()
                else:
                    inc_path = fasm_dir.resolve()

        if os.name != "nt" and inc_path.exists() and inc_path.is_dir():
            self._ensure_case_folded_include(inc_path)

        return str(inc_path)

    @staticmethod
    def _ensure_case_folded_include(base_inc: Path) -> None:
        """Creates symlinks for case-insensitive include resolution on case-sensitive filesystems (Linux)."""
        try:
            for root, dirs, files in os.walk(base_inc):
                r_path = Path(root)
                for d in list(dirs):
                    low_d = d.lower()
                    if low_d != d:
                        target = r_path / low_d
                        if not target.exists():
                            try:
                                os.symlink(d, target)
                            except Exception:
                                pass
                for f in files:
                    low_f = f.lower()
                    if low_f != f:
                        target = r_path / low_f
                        if not target.exists():
                            try:
                                os.symlink(f, target)
                            except Exception:
                                pass
        except Exception:
            pass

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
            if res.returncode != 0 and sys.platform == "darwin" and shutil.which("arch"):
                arch_res = subprocess.run(
                    ["arch", "-x86_64", self.fasm_path, str(asm_path), str(out_bin)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False
                )
                if arch_res.returncode == 0:
                    res = arch_res

            success = (res.returncode == 0) and out_bin.exists()
            log = res.stdout.strip()
            if not keep_asm and asm_file_path is None:
                try:
                    asm_path.unlink()
                except OSError:
                    pass
            return success, log
        except Exception as e:
            if sys.platform == "darwin" and shutil.which("arch"):
                try:
                    arch_res = subprocess.run(
                        ["arch", "-x86_64", self.fasm_path, str(asm_path), str(out_bin)],
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        check=False
                    )
                    success = (arch_res.returncode == 0) and out_bin.exists()
                    return success, arch_res.stdout.strip()
                except Exception:
                    pass
            return False, f"Execution failed: {e}"
