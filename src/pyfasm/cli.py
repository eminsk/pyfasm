"""
Command-Line Interface (CLI) for PyFASM compiler.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pyfasm",
        description="PyFASM: Ahead-of-Time (AOT) Python to Pure FASM x64 Native Compiler & Bundler (Zero-GIL)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: compile
    p_compile = subparsers.add_parser("compile", help="Compile a Python file or project directory to a single native x64 binary")
    p_compile.add_argument("source", help="Path to input Python source file (.py) or project directory")
    p_compile.add_argument("-o", "--output", help="Path to output binary (.exe, .dll, .elf, .macho, or .bin)")
    p_compile.add_argument("--target", default="win64", help="Target OS platform (win64, dll, linux, macos, apple)")
    p_compile.add_argument("--run", action="store_true", help="Execute binary immediately after successful build (win64 only)")
    p_compile.add_argument("--no-asm", action="store_true", help="Do not keep intermediate .asm file")
    p_compile.add_argument("--export-fasm", "-f", nargs="?", const="FASM", default=None, help="Export complete self-contained compilable FASM source directory with build scripts (default: FASM)")

    # Subcommand: emit-asm
    p_asm = subparsers.add_parser("emit-asm", help="Output generated FASM x64 assembly to stdout or file")
    p_asm.add_argument("source", help="Path to input Python source file (.py) or project directory")
    p_asm.add_argument("-o", "--output", help="Path to output .asm file")
    p_asm.add_argument("--target", default="win64", help="Target OS platform (win64, dll, linux, macos, apple)")

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

    args = parser.parse_args()
    compiler = PyFasmCompiler()

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
        )

        if not success:
            print(f"[PyFASM ERROR] Project bundling failed:\n{log}", file=sys.stderr)
            return 1

        print(f"[PyFASM SUCCESS] Project bundled into native executable: {out_bin}")
        return 0

    if args.command == "compile":
        success, out_bin, log = compiler.compile_file(
            source_path=args.source,
            output_binary=args.output,
            target=args.target,
            keep_asm=not args.no_asm,
            export_fasm_dir=args.export_fasm,
        )

        if not success:
            print(f"[PyFASM ERROR] Compilation failed:\n{log}", file=sys.stderr)
            return 1

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
        src = Path(args.source).resolve()
        if not src.exists():
            print(f"[PyFASM ERROR] File not found: {args.source}", file=sys.stderr)
            return 1

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
                entry_file = py_files[0] if py_files else None
            project_dir = src
            src_file = entry_file
        else:
            project_dir = src.parent
            src_file = src

        from pyfasm.ast_parser import AstAnalyzer
        from pyfasm.codegen_x64 import X64CodeGen

        analyzer = AstAnalyzer(project_root=project_dir)
        parsed_mod = analyzer.parse_file(src_file, project_root=project_dir)
        codegen = X64CodeGen(parsed_mod, target=args.target)
        asm_code = codegen.generate()

        if args.output:
            out_asm = Path(args.output).resolve()
            out_asm.write_text(asm_code, encoding="utf-8")
            print(f"[PyFASM] Assembly written to: {out_asm}")
        else:
            print(asm_code)

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
