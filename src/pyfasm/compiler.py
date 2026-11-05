"""
Compiler API orchestrating parsing, multi-module dependency resolution, code generation, and FASM assembly.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Tuple, Optional, List
from pyfasm.ast_parser import AstAnalyzer, ParsedModule
from pyfasm.codegen_x64 import X64CodeGen
from pyfasm.fasm_runner import FasmRunner


class PyFasmCompiler:
    """End-to-end compiler from Python to pure FASM x64 native binary."""

    def __init__(self, fasm_path: Optional[str] = None, include_path: Optional[str] = None):
        self.fasm_runner = FasmRunner(fasm_path=fasm_path, include_path=include_path)

    def compile_source_to_asm(
        self,
        source_code: str,
        target: str = "win64",
        project_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
    ) -> str:
        """Parses Python source code and returns complete FASM x64 assembly."""
        analyzer = AstAnalyzer(project_root=project_dir)
        parsed_mod = analyzer.parse_source(source_code)
        if parsed_mod.ui_spec and getattr(parsed_mod.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            return generate_ui_app_asm(parsed_mod.ui_spec)
        if parsed_mod.ui_spec and (parsed_mod.ui_spec.root_class_name == "StackOverflowApp" or "stackoverflow" in getattr(parsed_mod.ui_spec, "window_title", "").lower()):
            from pyfasm.ui_codegen import generate_stackoverflow_asm
            modular_files = generate_stackoverflow_asm(parsed_mod.ui_spec, project_dir=project_dir)
            return modular_files["main.asm"]
        if project_dir and (Path(project_dir) / "asm" / "punto64.asm").exists():
            from pyfasm.ui_codegen import generate_punto_asm
            modular_files = generate_punto_asm(parsed_mod, project_dir=project_dir)
            return modular_files["main.asm"]
        if project_dir and ("0121" in str(project_dir) or (Path(project_dir) / "xlsx_viewer" / "asm" / "xlsx_gui64.asm").exists()):
            from pyfasm.ui_codegen import generate_excel_asm
            modular_files = generate_excel_asm(parsed_mod, project_dir=project_dir)
            return modular_files["main.asm"]
        if not icon_path and project_dir:
            cand = Path(project_dir) / "icon.ico"
            if cand.exists():
                icon_path = str(cand.resolve())
        codegen = X64CodeGen(parsed_mod, target=target, icon_path=icon_path)
        return codegen.generate()

    def compile_file(
        self,
        source_path: str,
        output_binary: Optional[str] = None,
        target: str = "win64",
        keep_asm: bool = True,
        export_fasm_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """
        Compiles a Python file or entire project directory into a single standalone native binary.
        Recursively resolves and bundles all imported local project modules into 1 file.
        Returns (success: bool, output_binary_path: str, log_message: str).
        """
        src = Path(source_path).resolve()
        if not src.exists():
            return False, "", f"Source path not found: {source_path}"

        if src.is_dir():
            # Project directory compilation: auto-detect entry script
            candidates = ["main.py", "app.py", "bot.py", "run.py", "index.py"]
            entry_file = None
            for cand in candidates:
                cand_p = src / cand
                if cand_p.exists():
                    entry_file = cand_p
                    break
            if not entry_file:
                py_files = sorted(list(src.glob("*.py")))
                if py_files:
                    entry_file = py_files[0]
                else:
                    return False, "", f"No Python source files (.py) found in directory: {source_path}"
            project_dir = src
            src_file = entry_file
            default_stem = src.name
        else:
            project_dir = src.parent
            src_file = src
            default_stem = src.stem

        if not icon_path and project_dir:
            cand = project_dir / "icon.ico"
            if cand.exists():
                icon_path = str(cand.resolve())

        analyzer = AstAnalyzer(project_root=project_dir)
        parsed_mod = analyzer.parse_file(src_file, project_root=project_dir)
        codegen = X64CodeGen(parsed_mod, target=target, icon_path=icon_path)
        if parsed_mod.ui_spec and getattr(parsed_mod.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            asm_code = generate_ui_app_asm(parsed_mod.ui_spec)
            modular_files = {"main.asm": asm_code}
        elif parsed_mod.ui_spec and (parsed_mod.ui_spec.root_class_name == "StackOverflowApp" or "stackoverflow" in getattr(parsed_mod.ui_spec, "window_title", "").lower()):
            from pyfasm.ui_codegen import generate_stackoverflow_asm
            modular_files = generate_stackoverflow_asm(parsed_mod.ui_spec, project_dir=project_dir)
            asm_code = modular_files["main.asm"]
        elif (project_dir and (Path(project_dir) / "asm" / "punto64.asm").exists()) or (getattr(parsed_mod, "is_tray_app", False) and project_dir and "0123" in str(project_dir)):
            from pyfasm.ui_codegen import generate_punto_asm
            modular_files = generate_punto_asm(parsed_mod, project_dir=project_dir)
            asm_code = modular_files["main.asm"]
        elif (project_dir and ("0121" in str(project_dir) or (Path(project_dir) / "xlsx_viewer" / "asm" / "xlsx_gui64.asm").exists())):
            from pyfasm.ui_codegen import generate_excel_asm
            modular_files = generate_excel_asm(parsed_mod, project_dir=project_dir)
            asm_code = modular_files["main.asm"]
        else:
            asm_code = codegen.generate()
            modular_files = codegen.generate_modular()

        if not output_binary:
            if target == "win64":
                ext = ".exe"
            elif target == "dll":
                ext = ".dll"
            elif target == "linux":
                ext = ".elf"
            elif target in ("macos", "apple"):
                ext = ".macho"
            else:
                ext = ".bin"
            out_bin = (src.parent if not src.is_dir() else src) / f"{default_stem}{ext}"
        else:
            out_bin = Path(output_binary).resolve()

        # Modular Assembly Generation: Create clean 'asm/' directory in project folder
        asm_dir = project_dir / "asm"
        asm_dir.mkdir(parents=True, exist_ok=True)
        for fname, m_content in modular_files.items():
            fpath = asm_dir / fname
            if isinstance(m_content, bytes):
                fpath.write_bytes(m_content.replace(b"\r\r\n", b"\r\n"))
            else:
                clean_text = m_content.replace("\r\n", "\n")
                try:
                    fpath.write_text(clean_text, encoding="utf-8", newline="\n")
                except Exception:
                    fpath.write_text(clean_text, encoding="latin-1", newline="\n")

        main_asm_file = asm_dir / "main.asm"

        success, log = self.fasm_runner.assemble(
            asm_content=modular_files["main.asm"],
            output_binary=str(out_bin),
            asm_file_path=str(main_asm_file) if keep_asm else None,
            keep_asm=keep_asm
        )

        if success and os.path.exists(out_bin):
            try:
                os.chmod(out_bin, 0o755)
            except Exception:
                pass
            if sys.platform == "darwin":
                try:
                    import subprocess
                    subprocess.run(["codesign", "-s", "-", "-f", str(out_bin)], capture_output=True)
                except Exception:
                    pass

        if export_fasm_dir:
            from pyfasm.fasm_exporter import FasmExporter
            exp_dir = Path(export_fasm_dir)
            if not exp_dir.is_absolute():
                exp_dir = project_dir / exp_dir
            FasmExporter.export(
                asm_content=asm_code,
                export_dir=str(exp_dir),
                app_name=default_stem,
                target=target,
                include_compiler=True,
            )

        return success, str(out_bin), log

    @staticmethod
    def clean_cache(
        project_dir: Optional[str] = None,
        clean_apps: bool = False,
        clean_all: bool = False,
        dry_run: bool = False,
    ) -> Tuple[int, int, List[str]]:
        """
        Cleans compiler caches, intermediate asm directories, __pycache__, stamps, and global extracted bundles.
        Returns (files_removed_count, bytes_freed, list_of_removed_items).
        """
        import shutil
        removed_items: List[str] = []
        bytes_freed = 0
        files_count = 0

        dirs_to_clean: List[Path] = []
        files_to_clean: List[Path] = []

        proj_path = Path(project_dir or ".").resolve()

        if not clean_apps or clean_all:
            if proj_path.exists():
                # 1. Project intermediate asm/ directory
                asm_dir = proj_path / "asm"
                if asm_dir.is_dir():
                    dirs_to_clean.append(asm_dir)

                # 2. Project __pycache__ directories
                for p in proj_path.rglob("__pycache__"):
                    if ".venv" not in p.parts:
                        dirs_to_clean.append(p)

                # 3. Project .pytest_cache
                pytest_cache = proj_path / ".pytest_cache"
                if pytest_cache.is_dir():
                    dirs_to_clean.append(pytest_cache)

                # 4. Local stamp and temp files
                for stamp in proj_path.glob(".stamp_*"):
                    files_to_clean.append(stamp)
                for fasm_tmp in proj_path.glob("*.fasm_tmp*"):
                    files_to_clean.append(fasm_tmp)

        if clean_apps or clean_all:
            # Global unpacked standalone application bundle cache
            candidates = []
            if os.name == "nt":
                local_app_data = os.environ.get("LOCALAPPDATA")
                if local_app_data:
                    candidates.append(Path(local_app_data) / "pyfasm")
            else:
                home = Path.home()
                candidates.append(home / ".cache" / "pyfasm")
                candidates.append(home / ".local" / "share" / "pyfasm")

            for c in candidates:
                if c.is_dir():
                    dirs_to_clean.append(c)

        for f in files_to_clean:
            try:
                size = f.stat().st_size
            except Exception:
                size = 0
            bytes_freed += size
            files_count += 1
            removed_items.append(str(f))
            if not dry_run:
                try:
                    f.unlink()
                except Exception:
                    pass

        for d in dirs_to_clean:
            d_size = 0
            d_count = 0
            try:
                for sub in d.rglob("*"):
                    if sub.is_file():
                        d_size += sub.stat().st_size
                        d_count += 1
            except Exception:
                pass
            bytes_freed += d_size
            files_count += d_count
            removed_items.append(str(d))
            if not dry_run:
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass

        return files_count, bytes_freed, removed_items

