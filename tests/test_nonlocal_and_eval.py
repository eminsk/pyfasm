"""Tests for native nonlocal cell bindings, eval runtime, and print(eval(input()))."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pyfasm.compiler import PyFasmCompiler


def _compile_and_run(tmp_path: Path, name: str, source: str, input_text: str = "") -> str:
    src_file = tmp_path / f"{name}.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / f"{name}.exe"

    compiler = PyFasmCompiler()
    ok, _, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"

    res = subprocess.run(
        [str(out_exe)],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert res.returncode == 0, f"Process crashed with returncode {res.returncode}:\n{res.stderr}"
    return res.stdout.strip()


def test_nonlocal_cell_mutation_and_nested_scope(tmp_path: Path):
    source = """
def game() -> int:
    high_score = 0
    def set_score(s: int) -> None:
        nonlocal high_score
        if s > high_score:
            high_score = s
    def add_bonus(b: int) -> int:
        nonlocal high_score
        high_score = high_score + b
        return high_score

    set_score(100)
    add_bonus(25)
    return high_score

def main() -> int:
    score = game()
    print("SCORE:", score)
    return 0
"""
    out = _compile_and_run(tmp_path, "nonlocal_score", source)
    assert out == "SCORE: 125"


def test_eval_basic_arithmetic_and_precedence(tmp_path: Path):
    source = """
def main() -> int:
    a = eval("2 + 3 * 4")
    b = eval("(2 + 3) * 4")
    c = eval("100 / 4")
    d = eval("2 ** 5")
    print(a, b, c, d)
    return 0
"""
    out = _compile_and_run(tmp_path, "eval_arith", source)
    assert out == "14 20 25.0 32"


def test_eval_strings_bools_and_comparisons(tmp_path: Path):
    source = """
def main() -> int:
    s = eval("'hello ' + 'world'")
    b1: bool = eval("True and not False")
    b2: bool = eval("5 > 3 and 10 <= 20")
    print(s, b1, b2)
    return 0
"""
    out = _compile_and_run(tmp_path, "eval_str_bool", source)
    assert out == "hello world True True"


def test_eval_math_builtins_and_functions(tmp_path: Path):
    source = """
def main() -> int:
    v_abs = eval("abs(-42)")
    v_sqrt = eval("math.sqrt(49)")
    v_max = eval("max(10, 50, 30)")
    v_min = eval("min(10, 50, 30)")
    print(v_abs, v_sqrt, v_max, v_min)
    return 0
"""
    out = _compile_and_run(tmp_path, "eval_builtins", source)
    assert out == "42 7.0 50 10"


def test_print_eval_input_pipeline(tmp_path: Path):
    source = """
def main() -> int:
    print(eval(input()))
    return 0
"""
    for expr, expected in [
        ("3 + 7 * 2", "17"),
        ("10 * 10", "100"),
        ("abs(-15) + 5", "20"),
    ]:
        out = _compile_and_run(tmp_path, f"eval_input_{expected}", source, input_text=expr + "\n")
        assert out == expected


@pytest.mark.parametrize("target", ["win64", "linux", "macos", "myos"])
def test_cross_target_nonlocal_and_eval_strict(tmp_path: Path, target: str):
    source = """
def calculate() -> int:
    x = 10
    def modify() -> None:
        nonlocal x
        x = x + 5
    modify()
    return x

def main() -> int:
    v = calculate()
    res = eval("v * 2")
    print(res)
    return 0
"""
    src = tmp_path / f"test_{target}.py"
    src.write_text(source, encoding="utf-8")
    ext = ".exe" if target == "win64" else (".bin" if target == "myos" else "")
    out_bin = tmp_path / f"test_{target}{ext}"

    compiler = PyFasmCompiler()
    ok, _, log = compiler.compile_file(str(src), str(out_bin), target=target)
    assert ok is True, f"Compilation to target {target} failed:\n{log}"
    assert out_bin.exists()
