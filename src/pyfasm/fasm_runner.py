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
        r"C:\proekts\fasm-modern-sdk\bin\fasm.exe",
        r"D:\proekts\asm\fasm-modern-sdk\bin\fasm.exe",
        r"C:\asm\hdd\FASM.EXE",
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

        # 1. Check package bundled bin (e.g. site-packages/pyfasm/bin)
        pkg_bin_dir = Path(__file__).resolve().parent / "bin"
        if pkg_bin_dir.exists() and pkg_bin_dir.is_dir():
            if os.name == "nt":
                for cand_name in ("fasm.exe", "FASM.EXE"):
                    cand = pkg_bin_dir / cand_name
                    if cand.exists():
                        return str(cand.resolve())
            elif sys.platform == "darwin":
                for cand_name in ("fasm.darwin", "fasm"):
                    cand = pkg_bin_dir / cand_name
                    if cand.exists():
                        try:
                            os.chmod(cand, 0o755)
                        except Exception:
                            pass
                        return str(cand.resolve())
            else:
                for cand_name in ("fasm.x64", "fasm"):
                    cand = pkg_bin_dir / cand_name
                    if cand.exists():
                        try:
                            os.chmod(cand, 0o755)
                        except Exception:
                            pass
                        return str(cand.resolve())

        # 2. Check bundled repository tools/fasm
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

        # Check fasm-modern-sdk paths
        sdk_candidates = [
            Path("C:/proekts/fasm-modern-sdk/bin"),
            Path("D:/proekts/asm/fasm-modern-sdk/bin"),
            Path.home() / "fasm-modern-sdk" / "bin",
        ]
        for sdk_bin in sdk_candidates:
            if sdk_bin.exists():
                target_exe = "fasm.exe" if os.name == "nt" else ("fasm.darwin" if sys.platform == "darwin" else "fasm.x64")
                cand = sdk_bin / target_exe
                if cand.exists():
                    return str(cand.resolve())
                cand_plain = sdk_bin / "fasm"
                if cand_plain.exists():
                    return str(cand_plain.resolve())

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
        # Download modern FASM SDK from official repository: https://github.com/eminsk/fasm-modern-sdk
        sdk_version = "v1.73.36"
        base_url = f"https://github.com/eminsk/fasm-modern-sdk/releases/download/{sdk_version}"

        if os.name == "nt":
            url = f"{base_url}/fasm-modern-sdk-windows-x64.zip"
            zip_dest = target_dir / "fasm-modern-sdk-windows.zip"
            try:
                urllib.request.urlretrieve(url, zip_dest)
                with zipfile.ZipFile(zip_dest, "r") as zf:
                    zf.extractall(target_dir)
            except Exception:
                url_fb = "https://flatassembler.net/fasmw17332.zip"
                urllib.request.urlretrieve(url_fb, zip_dest)
                with zipfile.ZipFile(zip_dest, "r") as zf:
                    zf.extractall(target_dir)

            for cand in target_dir.rglob("fasm.exe"):
                return str(cand.resolve())
            for cand in target_dir.rglob("FASM.EXE"):
                return str(cand.resolve())

        elif sys.platform == "darwin":
            url = f"{base_url}/fasm-modern-sdk-macos-x64.tar.gz"
            tgz_dest = target_dir / "fasm-modern-sdk-macos.tar.gz"
            try:
                urllib.request.urlretrieve(url, tgz_dest)
                with tarfile.open(tgz_dest, "r:gz") as tf:
                    tf.extractall(target_dir)
            except Exception:
                url_fb = "https://raw.githubusercontent.com/STLVNUB/fasm-osx/master/fasm"
                dest = target_dir / "fasm"
                req = urllib.request.Request(url_fb, headers={"User-Agent": "pyfasm"})
                with open(dest, "wb") as f:
                    f.write(urllib.request.urlopen(req).read())
                try:
                    os.chmod(dest, 0o755)
                except Exception:
                    pass
                return str(dest.resolve())

            for cand in target_dir.rglob("fasm.darwin"):
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

        else:
            url = f"{base_url}/fasm-modern-sdk-linux-x64.tar.gz"
            tgz_dest = target_dir / "fasm-modern-sdk-linux.tar.gz"
            try:
                urllib.request.urlretrieve(url, tgz_dest)
                with tarfile.open(tgz_dest, "r:gz") as tf:
                    tf.extractall(target_dir)
            except Exception:
                url_fb = "https://flatassembler.net/fasm-1.73.32.tgz"
                urllib.request.urlretrieve(url_fb, tgz_dest)
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

        raise FileNotFoundError("Could not download FASM Modern SDK from eminsk/fasm-modern-sdk")

    def _locate_include(self, explicit_include: Optional[str]) -> str:
        if explicit_include and os.path.exists(explicit_include):
            inc_path = Path(explicit_include).resolve()
        else:
            fasm_dir = Path(self.fasm_path).parent
            pkg_inc = Path(__file__).resolve().parent / "include"
            repo_inc = Path(__file__).resolve().parents[2] / "tools" / "fasm" / "INCLUDE"
            candidates = [
                pkg_inc,
                fasm_dir / "INCLUDE",
                fasm_dir / "include",
                fasm_dir.parent / "include",
                fasm_dir.parent / "include" / "core",
                repo_inc,
                Path("C:/proekts/fasm-modern-sdk/include"),
                Path("D:/proekts/asm/fasm-modern-sdk/include"),
                Path.cwd() / "asm" / "INCLUDE",
                Path.home() / ".pyfasm" / "fasm" / "INCLUDE",
                fasm_dir,
            ]
            inc_path = None
            for cand in candidates:
                if cand.exists() and cand.is_dir():
                    if (cand / "WIN64A.INC").exists() or (cand / "win64a.inc").exists():
                        inc_path = cand.resolve()
                        break
                    elif (cand / "core" / "WIN64A.INC").exists() or (cand / "core" / "win64a.inc").exists():
                        inc_path = (cand / "core").resolve()
                        break
            if not inc_path:
                for cand in candidates:
                    if cand.exists() and cand.is_dir():
                        inc_path = cand.resolve()
                        break
            if not inc_path:
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
                cwd=str(asm_path.parent),
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
