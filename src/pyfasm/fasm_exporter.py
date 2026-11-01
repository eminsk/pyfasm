"""
FASM project exporter: exports generated FASM assembly, include headers,
compiler binaries, and 1-click build scripts (build.bat / build.sh)
into a self-contained folder (e.g. FASM/) ready for manual inspection, editing,
and re-compilation.
"""
from __future__ import annotations
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Union


class FasmExporter:
    """Exports self-contained, compilable FASM source directories."""

    @staticmethod
    def get_bundled_tools_dir() -> Path:
        return Path(__file__).resolve().parents[2] / "tools" / "fasm"

    @classmethod
    def export(
        cls,
        asm_content: str,
        export_dir: Union[str, Path],
        app_name: str = "app",
        target: str = "win64",
        payload_zip: Optional[Union[str, Path]] = None,
        include_compiler: bool = True,
    ) -> Path:
        """
        Exports a complete, self-contained FASM project into export_dir.

        Creates:
          - <app_name>.asm       (Generated assembly source code)
          - INCLUDE/             (FASM include files: win64a.inc, macros, equates)
          - FASM.EXE / fasm.x64  (Portable FASM assembler)
          - build.bat            (1-click compilation on Windows)
          - build.sh             (1-click compilation on Linux/macOS)
          - README.md            (Instructions for compiling and editing)
          - <app_name>.zip       (Optional payload archive if bundling)
        """
        out_dir = Path(export_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        target_norm = target.lower()
        if target_norm == "linux":
            out_ext = ".elf"
        elif target_norm in ("macos", "apple"):
            out_ext = ".macho"
        elif target_norm == "dll":
            out_ext = ".dll"
        else:
            out_ext = ".exe"

        # 1. Write the assembly source file
        asm_path = out_dir / f"{app_name}.asm"
        asm_path.write_text(asm_content, encoding="ascii", errors="replace")

        # 2. Copy include headers
        tools_dir = cls.get_bundled_tools_dir()
        inc_src = tools_dir / "INCLUDE"
        inc_dst = out_dir / "INCLUDE"
        if inc_src.exists() and inc_src.is_dir():
            if inc_dst.exists():
                try:
                    shutil.rmtree(inc_dst)
                except Exception:
                    pass
            if not inc_dst.exists():
                shutil.copytree(inc_src, inc_dst)

            # On Linux/macOS, ensure lowercase symlinks exist
            if os.name != "nt":
                try:
                    for root, dirs, files in os.walk(inc_dst):
                        r_path = Path(root)
                        for d in list(dirs):
                            if d.lower() != d and not (r_path / d.lower()).exists():
                                try:
                                    os.symlink(d, r_path / d.lower())
                                except Exception:
                                    pass
                        for f in files:
                            if f.lower() != f and not (r_path / f.lower()).exists():
                                try:
                                    os.symlink(f, r_path / f.lower())
                                except Exception:
                                    pass
                except Exception:
                    pass

        # 3. Copy compiler binaries if requested
        if include_compiler and tools_dir.exists():
            for bin_name in ("FASM.EXE", "fasm.exe", "fasm.x64", "fasm.darwin", "fasm"):
                src_bin = tools_dir / bin_name
                if src_bin.exists() and src_bin.is_file():
                    dst_bin = out_dir / bin_name
                    if not dst_bin.exists():
                        shutil.copy2(src_bin, dst_bin)
                    try:
                        os.chmod(dst_bin, 0o755)
                    except Exception:
                        pass

        # 4. Copy payload zip if present
        payload_name = f"{app_name}.zip"
        has_payload = False
        if payload_zip:
            p_zip = Path(payload_zip).resolve()
            if p_zip.exists():
                dst_zip = out_dir / payload_name
                try:
                    if p_zip != dst_zip:
                        shutil.copy2(p_zip, dst_zip)
                    has_payload = True
                except Exception:
                    has_payload = False

        # 5. Generate build.bat
        bat_lines = [
            "@echo off",
            "setlocal",
            'cd /d "%~dp0"',
            "echo ===================================================",
            f"echo   Compiling {app_name}.asm with FASM",
            "echo ===================================================",
            "",
            'set "INCLUDE=%~dp0INCLUDE"',
            "",
            'if exist "%~dp0FASM.EXE" (',
            '    set "FASM_EXE=%~dp0FASM.EXE"',
            ') else if exist "%~dp0fasm.exe" (',
            '    set "FASM_EXE=%~dp0fasm.exe"',
            ") else (",
            '    set "FASM_EXE=fasm"',
            ")",
            "",
            f'echo [*] Assembling {app_name}.asm to {app_name}{out_ext}...',
            f'"%FASM_EXE%" "%~dp0{app_name}.asm" "%~dp0{app_name}{out_ext}"',
            "if %ERRORLEVEL% neq 0 (",
            "    echo [!] FASM compilation failed with error code %ERRORLEVEL%",
            "    exit /b %ERRORLEVEL%",
            ")",
        ]
        if has_payload:
            bat_lines.extend([
                "",
                f'echo [*] Appending monolithic payload {payload_name}...',
                f'copy /b "%~dp0{app_name}{out_ext}" + "%~dp0{payload_name}" "%~dp0{app_name}{out_ext}" >nul',
            ])
        bat_lines.extend([
            "",
            f'echo [OK] Build successful: "%~dp0{app_name}{out_ext}"',
            "exit /b 0",
        ])
        (out_dir / "build.bat").write_text("\r\n".join(bat_lines) + "\r\n", encoding="ascii")

        # 6. Generate build.sh
        sh_lines = [
            "#!/bin/sh",
            "set -e",
            'DIR="$(cd "$(dirname "$0")" && pwd)"',
            'export INCLUDE="$DIR/INCLUDE"',
            'FASM_BIN="$DIR/fasm"',
            'if [ ! -f "$FASM_BIN" ]; then',
            '    if [ -f "$DIR/fasm.x64" ]; then',
            '        FASM_BIN="$DIR/fasm.x64"',
            '    elif [ -f "$DIR/fasm.darwin" ]; then',
            '        FASM_BIN="$DIR/fasm.darwin"',
            '    else',
            '        FASM_BIN="fasm"',
            '    fi',
            'fi',
            'chmod +x "$FASM_BIN" 2>/dev/null || true',
            f'echo "[*] Assembling {app_name}.asm to {app_name}{out_ext}..."',
            f'"$FASM_BIN" "$DIR/{app_name}.asm" "$DIR/{app_name}{out_ext}"',
        ]
        if has_payload:
            sh_lines.extend([
                f'echo "[*] Appending monolithic payload {payload_name}..."',
                f'cat "$DIR/{payload_name}" >> "$DIR/{app_name}{out_ext}"',
            ])
        sh_lines.extend([
            f'echo "[OK] Build successful: $DIR/{app_name}{out_ext}"',
        ])
        sh_file = out_dir / "build.sh"
        sh_file.write_text("\n".join(sh_lines) + "\n", encoding="ascii")
        try:
            os.chmod(sh_file, 0o755)
        except Exception:
            pass

        # 7. Write README.md
        payload_desc = f"- `{payload_name}`: Embedded monolithic project payload archive.\n" if has_payload else ""
        readme = f"""# {app_name} - FASM Source & Compilation Package

This folder contains the complete, standalone Flat Assembler (FASM) source code and build tools for **{app_name}**.

## Contents
- `{app_name}.asm`: The generated pure x86_64 assembly source file.
- `INCLUDE/`: Standard FASM macro, struct, and equates libraries (Win64 / ELF / Mach-O headers).
- `build.bat`: One-click build script for Windows (double-click or run from cmd).
- `build.sh`: One-click build script for Linux / macOS (`chmod +x build.sh && ./build.sh`).
{payload_desc}
## How to Recompile
- **On Windows**: Run `build.bat`
- **On Linux / macOS**: Run `./build.sh`

You can freely edit `{app_name}.asm`, optimize instructions, add assembly macros, and re-run the build script to produce a newly compiled binary.
"""
        (out_dir / "README.md").write_text(readme, encoding="utf-8")

        return out_dir
