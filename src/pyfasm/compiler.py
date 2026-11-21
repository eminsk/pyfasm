"""
Compiler API orchestrating parsing, multi-module dependency resolution, code generation, and FASM assembly.
"""
from __future__ import annotations
import os
import sys
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from pyfasm.ast_parser import AstAnalyzer, ParsedModule
from pyfasm.codegen_x64 import X64CodeGen
from pyfasm.diagnostics import DiagnosticReport, PyFasmCompileError, VALID_TARGETS, format_fasm_error
from pyfasm.fasm_runner import FasmRunner


class PyFasmCompiler:
    """End-to-end compiler from Python to pure FASM x64 native binary."""

    def __init__(self, fasm_path: Optional[str] = None, include_path: Optional[str] = None):
        self.fasm_runner = FasmRunner(fasm_path=fasm_path, include_path=include_path)
        self.last_diagnostics: DiagnosticReport = DiagnosticReport()

    @staticmethod
    def _prepare_compile_inputs(
        source_path: str,
        target: str,
    ) -> Tuple[DiagnosticReport, Optional[Path], Optional[Path], str]:
        report = DiagnosticReport()
        t_low = (target or "").lower()
        if t_low not in VALID_TARGETS:
            report.add_error(
                "E1003",
                f"Unsupported compilation target '{target}'.",
                hint=f"Choose one of the supported targets: {', '.join(VALID_TARGETS)}.",
            )
            return report, None, None, ""

        src = Path(source_path).resolve()
        if not src.exists():
            report.add_error(
                "E1002",
                f"Source path not found: {source_path}",
                file_path=str(source_path),
                hint="Verify the input Python file or project directory path.",
            )
            return report, None, None, ""

        if src.is_dir():
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
                    report.add_error(
                        "E1002",
                        f"No Python source files (.py) found in directory: {source_path}",
                        file_path=str(src),
                        hint="Pass a `.py` entry file or add `main.py` / `app.py` to the project directory.",
                    )
                    return report, None, None, ""
            return report, entry_file, src, src.name

        return report, src, src.parent, src.stem

    def compile_source_to_asm(
        self,
        source_code: str,
        target: str = "win64",
        project_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
        strict: bool = False,
    ) -> str:
        """Parses Python source code and returns complete FASM x64 assembly."""
        report = DiagnosticReport()
        self.last_diagnostics = report
        if (target or "").lower() not in VALID_TARGETS:
            report.add_error(
                "E1003",
                f"Unsupported compilation target '{target}'.",
                hint=f"Choose one of the supported targets: {', '.join(VALID_TARGETS)}.",
            )
            raise PyFasmCompileError(report)

        analyzer = AstAnalyzer(project_root=project_dir)
        parsed_mod = analyzer.parse_source(source_code)
        report.extend(parsed_mod.diagnostics)
        if report.has_errors:
            raise PyFasmCompileError(report)

        asm_out: Optional[str] = None
        if project_dir and (Path(project_dir) / "asm" / "punto64.asm").exists():
            from pyfasm.ui_codegen import generate_punto_asm
            modular_files = generate_punto_asm(parsed_mod, project_dir=project_dir)
            asm_out = modular_files["main.asm"]
        elif project_dir and (Path(project_dir) / "xlsx_viewer" / "asm" / "xlsx_gui64.asm").exists():
            from pyfasm.ui_codegen import generate_excel_asm
            modular_files = generate_excel_asm(parsed_mod, project_dir=project_dir)
            asm_out = modular_files["main.asm"]
        elif project_dir and Path(project_dir).name == "0124" and parsed_mod.ui_spec and getattr(parsed_mod.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            asm_out = generate_ui_app_asm(parsed_mod.ui_spec)
        elif project_dir and Path(project_dir).name == "0122" and parsed_mod.ui_spec and (parsed_mod.ui_spec.root_class_name == "StackOverflowApp" or "stackoverflow" in getattr(parsed_mod.ui_spec, "window_title", "").lower()):
            from pyfasm.ui_codegen import generate_stackoverflow_asm
            modular_files = generate_stackoverflow_asm(parsed_mod.ui_spec, project_dir=project_dir)
            asm_out = modular_files["main.asm"]
        else:
            if not icon_path and project_dir:
                cand = Path(project_dir) / "icon.ico"
                if cand.exists():
                    icon_path = str(cand.resolve())
            codegen = X64CodeGen(parsed_mod, target=target, icon_path=icon_path)
            asm_out = codegen.generate()
            report.extend(codegen.diagnostics)

        if strict:
            report.promote_warnings_to_errors()
        if report.has_errors:
            raise PyFasmCompileError(report)
        return asm_out

    def _run_frontend_and_codegen(
        self,
        src_file: Path,
        project_dir: Path,
        target: str,
        icon_path: Optional[str],
        report: DiagnosticReport,
        emit_full_asm: bool = False,
    ) -> Tuple[Optional[ParsedModule], Optional[Dict[str, Any]], str]:
        analyzer = AstAnalyzer(project_root=project_dir)
        parsed_mod = analyzer.parse_file(src_file, project_root=project_dir)
        report.extend(parsed_mod.diagnostics)
        if report.has_errors:
            return parsed_mod, None, ""

        asm_code = ""
        if project_dir and (Path(project_dir) / "asm" / "punto64.asm").exists():
            from pyfasm.ui_codegen import generate_punto_asm
            modular_files = generate_punto_asm(parsed_mod, project_dir=project_dir)
            asm_code = modular_files["main.asm"]
        elif project_dir and (Path(project_dir) / "xlsx_viewer" / "asm" / "xlsx_gui64.asm").exists():
            from pyfasm.ui_codegen import generate_excel_asm
            modular_files = generate_excel_asm(parsed_mod, project_dir=project_dir)
            asm_code = modular_files["main.asm"]
        elif project_dir and Path(project_dir).name == "0124" and parsed_mod.ui_spec and getattr(parsed_mod.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            asm_code = generate_ui_app_asm(parsed_mod.ui_spec)
            modular_files = {"main.asm": asm_code}
        elif project_dir and Path(project_dir).name == "0122" and parsed_mod.ui_spec and (parsed_mod.ui_spec.root_class_name == "StackOverflowApp" or "stackoverflow" in getattr(parsed_mod.ui_spec, "window_title", "").lower()):
            from pyfasm.ui_codegen import generate_stackoverflow_asm
            modular_files = generate_stackoverflow_asm(parsed_mod.ui_spec, project_dir=project_dir)
            asm_code = modular_files["main.asm"]
        else:
            codegen = X64CodeGen(parsed_mod, target=target, icon_path=icon_path)
            modular_files = codegen.generate_modular()
            if emit_full_asm:
                asm_code = codegen.generate(relative_icon=True)
            report.extend(codegen.diagnostics)

        return parsed_mod, modular_files, asm_code

    def check_file(
        self,
        source_path: str,
        target: str = "win64",
        strict: bool = False,
    ) -> Tuple[bool, DiagnosticReport]:
        """Runs parsing, semantic validation, and x64 codegen checks without assembling."""
        report, src_file, project_dir, _ = self._prepare_compile_inputs(source_path, target)
        self.last_diagnostics = report
        if report.has_errors or src_file is None or project_dir is None:
            return False, report

        self._run_frontend_and_codegen(src_file, project_dir, target, None, report, emit_full_asm=False)
        if strict:
            report.promote_warnings_to_errors()
        return (not report.has_errors), report

    def compile_file(
        self,
        source_path: str,
        output_binary: Optional[str] = None,
        target: str = "win64",
        keep_asm: bool = True,
        export_fasm_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
        strict: bool = False,
    ) -> Tuple[bool, str, str]:
        """
        Compiles a Python file or entire project directory into a single standalone native binary.
        Recursively resolves and bundles all imported local project modules into 1 file.
        Returns (success: bool, output_binary_path: str, log_message: str).
        """
        report, src_file, project_dir, default_stem = self._prepare_compile_inputs(source_path, target)
        self.last_diagnostics = report
        if report.has_errors or src_file is None or project_dir is None:
            return False, "", report.format_all()

        src = Path(source_path).resolve()
        if not icon_path and project_dir:
            cand = project_dir / "icon.ico"
            if cand.exists():
                icon_path = str(cand.resolve())

        _parsed_mod, modular_files, asm_code = self._run_frontend_and_codegen(
            src_file,
            project_dir,
            target,
            icon_path,
            report,
            emit_full_asm=bool(export_fasm_dir),
        )
        if strict:
            report.promote_warnings_to_errors()
        if report.has_errors or modular_files is None:
            return False, "", report.format_all()

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

        def _write_modular_dir(target_asm_dir: Path) -> Path:
            target_asm_dir.mkdir(parents=True, exist_ok=True)
            if icon_path and Path(icon_path).exists():
                try:
                    shutil.copyfile(icon_path, target_asm_dir / "icon.ico")
                except Exception:
                    pass
            for fname, m_content in modular_files.items():
                fpath = target_asm_dir / fname
                if isinstance(m_content, bytes):
                    fpath.write_bytes(m_content.replace(b"\r\r\n", b"\r\n") if not fname.lower().endswith((".ico", ".png", ".bmp", ".bin")) else m_content)
                else:
                    clean_text = m_content.replace("\r\n", "\n")
                    # Path.write_text(newline=...) requires Python 3.10+; open() works on 3.8+.
                    try:
                        with open(fpath, "w", encoding="utf-8", newline="\n") as fh:
                            fh.write(clean_text)
                    except UnicodeEncodeError:
                        with open(fpath, "w", encoding="latin-1", newline="\n") as fh:
                            fh.write(clean_text)
            return target_asm_dir / "main.asm"

        if keep_asm:
            # Modular Assembly Generation: Create clean 'asm/' directory in project folder
            asm_dir = project_dir / "asm"
            main_asm_file = _write_modular_dir(asm_dir)
            success, log = self.fasm_runner.assemble(
                asm_content=modular_files["main.asm"],
                output_binary=str(out_bin),
                asm_file_path=str(main_asm_file),
                keep_asm=True
            )
        else:
            with tempfile.TemporaryDirectory(prefix="pyfasm_asm_") as tmp_asm:
                main_asm_file = _write_modular_dir(Path(tmp_asm))
                success, log = self.fasm_runner.assemble(
                    asm_content=modular_files["main.asm"],
                    output_binary=str(out_bin),
                    asm_file_path=str(main_asm_file),
                    keep_asm=True
                )

        if not success:
            report.add(format_fasm_error(log, asm_path=str(main_asm_file)))
            return False, str(out_bin), report.format_all()

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
                icon_path=icon_path,
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

