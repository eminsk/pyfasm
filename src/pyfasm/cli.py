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
        description="PyFASM: Free-Threaded (No-GIL) Python to Pure FASM x64 Native Compiler"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: compile
    p_compile = subparsers.add_parser("compile", help="Compile a Python file to native x64 executable")
    p_compile.add_argument("source", help="Path to input Python source file (.py)")
    p_compile.add_argument("-o", "--output", help="Path to output binary (.exe or .bin)")
    p_compile.add_argument("--target", choices=["win64", "myos"], default="win64", help="Target OS platform")
    p_compile.add_argument("--run", action="store_true", help="Execute binary immediately after successful build")
    p_compile.add_argument("--no-asm", action="store_true", help="Do not keep intermediate .asm file")

    # Subcommand: emit-asm
    p_asm = subparsers.add_parser("emit-asm", help="Output generated FASM x64 assembly to stdout or file")
    p_asm.add_argument("source", help="Path to input Python source file (.py)")
    p_asm.add_argument("-o", "--output", help="Path to output .asm file")
    p_asm.add_argument("--target", choices=["win64", "myos"], default="win64", help="Target OS platform")

    args = parser.parse_args()
    compiler = PyFasmCompiler()

    if args.command == "compile":
        success, out_bin, log = compiler.compile_file(
            source_path=args.source,
            output_binary=args.output,
            target=args.target,
            keep_asm=not args.no_asm
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

        source_code = src.read_text(encoding="utf-8")
        asm_code = compiler.compile_source_to_asm(source_code, target=args.target)

        if args.output:
            out_asm = Path(args.output).resolve()
            out_asm.write_text(asm_code, encoding="ascii")
            print(f"[PyFASM] Assembly written to: {out_asm}")
        else:
            print(asm_code)

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
