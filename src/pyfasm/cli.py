"""
Command-Line Interface (CLI) for PyFASM compiler.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple
from pyfasm import __version__
from pyfasm.compiler import PyFasmCompiler


def _format_markdown_table(table_lines: List[str]) -> List[str]:
    """Formats markdown table into aligned terminal box drawing table."""
    rows: List[List[str]] = []
    for line in table_lines:
        line_clean = line.strip().strip("|")
        cells = [c.strip() for c in line_clean.split("|")]
        # Skip separator line (| :--- | :--- |)
        if all(re.match(r"^:?-+:?$", c) for c in cells if c):
            continue
        clean_cells = []
        for c in cells:
            c = re.sub(r"\*\*([^*]+)\*\*", r"\1", c)
            c = re.sub(r"`([^`]+)`", r"\1", c)
            c = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", c)
            clean_cells.append(c)
        rows.append(clean_cells)
    if not rows:
        return table_lines

    num_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < num_cols:
            r.append("")

    col_widths = [max(len(r[i]) for r in rows) for i in range(num_cols)]
    col_widths = [max(w, 3) for w in col_widths]

    top = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    sep = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    bot = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"

    out = [top]
    for idx, r in enumerate(rows):
        row_str = "│" + "│".join(f" {r[i]:<{col_widths[i]}} " for i in range(num_cols)) + "│"
        out.append(row_str)
        if idx == 0 and len(rows) > 1:
            out.append(sep)
    out.append(bot)
    return out


def format_markdown_for_terminal(text: str, is_tty: bool = False) -> str:
    """Renders raw Markdown into clean, readable terminal text."""
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    n = len(lines)

    in_code_block = False
    code_block_lang = ""
    table_lines: List[str] = []

    def flush_table():
        nonlocal table_lines
        if table_lines:
            formatted = _format_markdown_table(table_lines)
            out.extend(formatted)
            table_lines = []

    bold = "\033[1m" if is_tty else ""
    cyan = "\033[36m" if is_tty else ""
    yellow = "\033[33m" if is_tty else ""
    green = "\033[32m" if is_tty else ""
    dim = "\033[2m" if is_tty else ""
    reset = "\033[0m" if is_tty else ""

    while i < n:
        raw_line = lines[i]
        line = raw_line.rstrip()

        # Handle code blocks
        if line.startswith("```"):
            if not in_code_block:
                flush_table()
                in_code_block = True
                code_block_lang = line[3:].strip()
                tag = f" [{code_block_lang}] " if code_block_lang else " "
                out.append(f"  {dim}┌──{tag}{'─' * max(2, 60 - len(tag))}{reset}")
            else:
                in_code_block = False
                out.append(f"  {dim}└──{'─' * 60}{reset}")
            i += 1
            continue

        if in_code_block:
            out.append(f"  {dim}│{reset}  {green}{line}{reset}")
            i += 1
            continue

        # Handle markdown tables
        if line.startswith("|") and line.endswith("|"):
            table_lines.append(line)
            i += 1
            continue
        else:
            flush_table()

        # Skip shields.io / web badge lines
        if line.startswith("[![") or "img.shields.io" in line:
            i += 1
            continue

        # Skip language switcher lines (e.g. > 🌐 Language / Язык: ...)
        if line.startswith("> 🌐 **Language") or line.startswith("> 🌐 **Язык"):
            i += 1
            continue

        # H1
        if line.startswith("# "):
            title = line[2:].strip()
            border = "═" * min(80, max(60, len(title) + 4))
            out.append("")
            out.append(f"{cyan}{border}{reset}")
            out.append(f"{bold}{cyan}  {title}{reset}")
            out.append(f"{cyan}{border}{reset}")
            out.append("")
            i += 1
            continue

        # H2
        if line.startswith("## "):
            title = line[3:].strip()
            border_len = max(2, 76 - len(title))
            out.append("")
            out.append(f"{bold}{cyan}── {title} {'─' * border_len}{reset}")
            out.append("")
            i += 1
            continue

        # H3
        if line.startswith("### "):
            title = line[4:].strip()
            out.append("")
            out.append(f"{bold}{yellow}▶ {title}{reset}")
            i += 1
            continue

        # Horizontal rule ---
        if re.match(r"^[-*_]{3,}$", line.strip()):
            out.append(f"{dim}{'─' * 80}{reset}")
            i += 1
            continue

        # Blockquote >
        if line.startswith("> "):
            quote_text = line[2:].strip()
            quote_text = re.sub(r"\*\*([^*]+)\*\*", rf"{bold}\1{reset}", quote_text)
            out.append(f"  {cyan}│{reset} {quote_text}")
            i += 1
            continue

        # Bullet list
        if re.match(r"^\s*[\*\-]\s+", line):
            indent_m = re.match(r"^(\s*)[\*\-]\s+(.*)$", line)
            if indent_m:
                ind, body = indent_m.group(1), indent_m.group(2)
                body = re.sub(r"\*\*([^*]+)\*\*", rf"{bold}\1{reset}", body)
                body = re.sub(r"`([^`]+)`", rf"{green}\1{reset}", body)
                body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", body)
                out.append(f"{ind}  • {body}")
                i += 1
                continue

        # Clean links and bold in prose
        cleaned = line
        cleaned = re.sub(r"\*\*([^*]+)\*\*", rf"{bold}\1{reset}", cleaned)
        cleaned = re.sub(r"`([^`]+)`", rf"{green}\1{reset}", cleaned)
        cleaned = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", cleaned)

        out.append(cleaned)
        i += 1

    flush_table()
    return "\n".join(out)


def main() -> int:
    invoked = Path(sys.argv[0]).stem.lower() if sys.argv else "pyfasm64"
    prog_name = "pyfasm" if invoked == "pyfasm" else "pyfasm64"
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="PyFASM64: Ahead-of-Time (AOT) Python to Pure FASM x64 Native Compiler & Bundler (Zero-GIL)"
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__} (Host Python: {sys.version.split()[0]})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: compile
    p_compile = subparsers.add_parser("compile", help="Compile a Python file or project directory to a single native x64 binary")
    p_compile.add_argument("source", help="Path to input Python source file (.py) or project directory")
    p_compile.add_argument("--python-version", "--py-ver", default=None, help="Target Python language version (default: auto-detected host version, e.g. 3.14, 3.15)")
    p_compile.add_argument("-o", "--output", help="Path to output binary (.exe, .dll, .elf, .macho, or .bin)")
    p_compile.add_argument("--target", default="win64", help="Target OS platform (win64, dll, linux, macos, apple, myos)")
    p_compile.add_argument("--gui", "--windowed", "-w", action="store_true", help="Compile as a Win32 GUI windowed subsystem executable (suppress console window)")
    p_compile.add_argument("--console", "-c", action="store_true", help="Compile with console subsystem (standard I/O enabled)")
    p_compile.add_argument("--optimize", "-O", action="store_true", help="Enable assembly peephole optimizations")
    p_compile.add_argument("--verbose", "-v", action="store_true", help="Enable verbose compilation diagnostics")
    p_compile.add_argument("--run", action="store_true", help="Execute compiled binary immediately after successful build")
    p_compile.add_argument("--no-asm", action="store_true", help="Do not keep intermediate .asm file")
    p_compile.add_argument("--export-fasm", "-f", nargs="?", const="FASM", default=None, help="Export complete self-contained compilable FASM source directory with build scripts (default: FASM)")
    p_compile.add_argument("--icon", default=None, help="Path to .ico icon file for PE resources, window, and taskbar")
    p_compile.add_argument("--strict", action="store_true", help="Treat compiler warnings (external imports, unsupported dunders, unresolved symbols) as errors")

    # Subcommand: check
    p_check = subparsers.add_parser("check", help="Validate Python compatibility and report errors/warnings without assembling")
    p_check.add_argument("source", help="Path to input Python source file (.py) or project directory")
    p_check.add_argument("--python-version", "--py-ver", default=None, help="Target Python language version (default: auto-detected host version)")
    p_check.add_argument("--target", default="win64", help="Target OS platform (win64, dll, linux, macos, apple, myos)")
    p_check.add_argument("--gui", "--windowed", "-w", action="store_true", help="Validate under GUI windowed subsystem")
    p_check.add_argument("--strict", action="store_true", help="Treat warnings as errors (non-zero exit code)")
    p_check.add_argument("--verbose", "-v", action="store_true", help="Enable verbose diagnostics")

    # Subcommand: emit-asm
    p_asm = subparsers.add_parser("emit-asm", help="Output generated FASM x64 assembly to stdout or file")
    p_asm.add_argument("source", help="Path to input Python source file (.py) or project directory")
    p_asm.add_argument("--python-version", "--py-ver", default=None, help="Target Python language version (default: auto-detected host version)")
    p_asm.add_argument("-o", "--output", help="Path to output .asm file")
    p_asm.add_argument("--target", default="win64", help="Target OS platform (win64, dll, linux, macos, apple, myos)")
    p_asm.add_argument("--gui", "--windowed", "-w", action="store_true", help="Target GUI windowed application structure")
    p_asm.add_argument("--console", "-c", action="store_true", help="Target console application structure")
    p_asm.add_argument("--icon", default=None, help="Path to .ico icon file for PE resources")
    p_asm.add_argument("--strict", action="store_true", help="Treat compiler warnings as errors")
    p_asm.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    # Subcommand: bundle
    p_bundle = subparsers.add_parser("bundle", help="Bundle a full Python project into a native x64 monolithic executable")
    p_bundle.add_argument("project_dir", help="Path to Python project directory")
    p_bundle.add_argument("-e", "--entry", help="Path to main entry script (default: auto-detected)")
    p_bundle.add_argument("-o", "--output", help="Path to output executable (.exe, .elf, .macho)")
    p_bundle.add_argument("--console", action="store_true", help="Build console launcher instead of GUI (shows stdout/stderr)")
    p_bundle.add_argument("--target", choices=["win64", "linux", "macos", "apple"], default="win64", help="Target OS platform for launcher (win64, linux, macos)")
    p_bundle.add_argument("--include-bin", action="append", default=[], help="Path to external binary or tool to include inside the bundle (e.g. ffmpeg.exe, mpv-2.dll)")
    p_bundle.add_argument("--include-venv", action="store_true", help="Pack project .venv environment into the bundle for offline standalone portability")
    p_bundle.add_argument("--dir-mode", action="store_true", help="Build directory-wrapper launcher instead of monolithic single-file")
    p_bundle.add_argument("--export-fasm", "-f", nargs="?", const="FASM", default=None, help="Export complete self-contained compilable FASM source directory with build scripts (default: FASM)")
    p_bundle.add_argument("--icon", default=None, help="Path to .ico icon file for PE resources, window, and taskbar")


    # Subcommand: clean
    p_clean = subparsers.add_parser("clean", help="Clean compiler cache, intermediate ASM files, and unpacked application caches")
    p_clean.add_argument("path", nargs="?", default=".", help="Project directory to clean (default: current directory)")
    p_clean.add_argument("--all", "-a", action="store_true", help="Clean all caches including global unpacked apps in %%LOCALAPPDATA%%/pyfasm")
    p_clean.add_argument("--apps", action="store_true", help="Clean only global unpacked standalone application caches")
    p_clean.add_argument("--dry-run", "-n", action="store_true", help="Show files to be deleted without removing them")

    # Subcommand: docs
    p_docs = subparsers.add_parser("docs", help="View PyFASM documentation (English by default, Russian via --ru)")
    p_docs.add_argument("--ru", "--russian", action="store_true", help="Display Russian documentation instead of English")
    p_docs.add_argument("--open", action="store_true", help="Open documentation file in default markdown viewer or editor")

    args = parser.parse_args()

    if args.command == "docs":
        doc_filename = "README_RU.md" if args.ru else "README.md"
        cand_dirs = [
            Path(__file__).resolve().parent,
            Path(__file__).resolve().parents[2],
            Path.cwd(),
        ]
        doc_path = None
        for d in cand_dirs:
            target = d / doc_filename
            if target.exists():
                doc_path = target
                break

        if not doc_path:
            for d in cand_dirs:
                target = d / "README.md"
                if target.exists():
                    doc_path = target
                    break

        if not doc_path:
            print(f"[PyFASM ERROR] Documentation file {doc_filename} not found.", file=sys.stderr)
            return 1

        if args.open:
            import os
            try:
                if os.name == "nt":
                    os.startfile(str(doc_path))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(doc_path)])
                else:
                    subprocess.run(["xdg-open", str(doc_path)])
                print(f"[PyFASM] Opened documentation: {doc_path}")
                return 0
            except Exception as e:
                print(f"[PyFASM ERROR] Failed to open {doc_path}: {e}", file=sys.stderr)
                return 1

        content = doc_path.read_text(encoding="utf-8")
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        formatted = format_markdown_for_terminal(content, is_tty=is_tty)
        print(formatted)
        return 0

    py_ver_opt = getattr(args, "python_version", None)
    compiler = PyFasmCompiler(py_version=py_ver_opt)

    if args.command == "clean":
        files_count, bytes_freed, items = PyFasmCompiler.clean_cache(
            project_dir=args.path,
            clean_apps=args.apps,
            clean_all=args.all,
            dry_run=args.dry_run,
        )
        mb = bytes_freed / (1024 * 1024)
        action_word = "Would remove" if args.dry_run else "Cleaned"
        print(f"[PyFASM] {action_word} {len(items)} target location(s) ({files_count} files, {mb:.2f} MB freed).")
        for item in items[:10]:
            print(f"  - {item}")
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more targets.")
        return 0

    if args.command == "bundle":
        from pyfasm.bundler import ProjectBundler
        bundler = ProjectBundler(compiler.fasm_runner)
        success, out_bin, log = bundler.bundle(
            project_dir=args.project_dir,
            entry_script=args.entry,
            output_exe=args.output,
            is_gui=not args.console,
            target=args.target,
            onefile=not args.dir_mode,
            include_bins=args.include_bin,
            include_venv=args.include_venv,
            export_fasm_dir=args.export_fasm,
            icon_path=args.icon,
        )

        if not success:
            print(f"[PyFASM ERROR] Project bundling failed:\n{log}", file=sys.stderr)
            return 1

        print(f"[PyFASM SUCCESS] Project bundled into native executable: {out_bin}")
        return 0

    gui_opt = True if getattr(args, "gui", False) else (False if getattr(args, "console", False) else None)

    if args.command == "check":
        ok, report = compiler.check_file(
            source_path=args.source,
            target=args.target,
            strict=args.strict,
            gui=gui_opt,
        )
        if report.items:
            print(report.format_all(), file=sys.stderr)
        if not ok:
            return 1
        if not report.items:
            print(f"[PyFASM OK] No issues found in: {args.source}")
        return 0

    if args.command == "compile":
        success, out_bin, log = compiler.compile_file(
            source_path=args.source,
            output_binary=args.output,
            target=args.target,
            keep_asm=not args.no_asm,
            export_fasm_dir=args.export_fasm,
            icon_path=args.icon,
            strict=args.strict,
            gui=gui_opt,
        )

        if not success:
            if log.lstrip().startswith(("error[", "warning[")):
                print(log, file=sys.stderr)
            else:
                print(f"[PyFASM ERROR] Compilation failed:\n{log}", file=sys.stderr)
            return 1

        if compiler.last_diagnostics.warnings:
            print(compiler.last_diagnostics.format_all(), file=sys.stderr)

        print(f"[PyFASM SUCCESS] Binary compiled: {out_bin}")
        if log:
            print(f"FASM log: {log}")

        if args.run:
            print(f"\n--- Running {out_bin} ---")
            res = subprocess.run([out_bin])
            print(f"--- Process exited with code {res.returncode} ---")
            return res.returncode

        return 0

    elif args.command == "emit-asm":
        report, src_file, project_dir, _ = compiler._prepare_compile_inputs(args.source, args.target)
        if report.has_errors or src_file is None or project_dir is None:
            print(report.format_all(), file=sys.stderr)
            return 1

        from pyfasm.ast_parser import AstAnalyzer
        from pyfasm.codegen_x64 import X64CodeGen

        analyzer = AstAnalyzer(
            project_root=project_dir,
            py_version=compiler.py_version,
            py_micro=compiler.py_micro,
        )
        parsed_mod = analyzer.parse_file(src_file, project_root=project_dir)
        if gui_opt is True:
            parsed_mod.is_gui_app = True
            parsed_mod.is_modern_gui = True
        elif gui_opt is False:
            parsed_mod.is_gui_app = False
        report.extend(parsed_mod.diagnostics)
        if report.has_errors:
            print(report.format_all(), file=sys.stderr)
            return 1

        codegen = X64CodeGen(
            parsed_mod,
            target=args.target,
            icon_path=args.icon,
            py_version=compiler.py_version,
            py_micro=compiler.py_micro,
        )
        asm_code = codegen.generate()
        report.extend(codegen.diagnostics)
        if args.strict:
            report.promote_warnings_to_errors()
        if report.items:
            print(report.format_all(), file=sys.stderr)
        if report.has_errors:
            return 1

        if args.output:
            out_asm = Path(args.output).resolve()
            with open(out_asm, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(asm_code)
            print(f"[PyFASM] Assembly written to: {out_asm}")
        else:
            print(asm_code)

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
