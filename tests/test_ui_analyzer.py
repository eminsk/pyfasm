"""
Unit tests for PyFASM UI Structure Analyzer and UI Code Generator.
Verifies authentic AST-level structural decomposition, widget hierarchy,
container mapping, and code generation across diverse application architectures.
"""
import ast
from pathlib import Path
import pytest
from pyfasm.ui_analyzer import analyze_ui_structure, UiAppSpec
from pyfasm.ui_codegen import generate_ui_app_asm


def test_ui_analyzer_quadratic_equation():
    """Verify AST extraction on Quadratic Equation solver application (Project 0124)."""
    p = Path("C:/proekts/0124/Main.py")
    if not p.exists():
        pytest.skip("0124/Main.py not found on filesystem")

    tree = ast.parse(p.read_text(encoding="utf-8"))
    spec = analyze_ui_structure(tree)

    assert spec is not None
    assert spec.window_title == "Квадратное уравнение"
    assert spec.window_width == 1100
    assert spec.window_height == 700
    assert spec.plot_title == "График f(x)"
    assert spec.plot_xlabel == "x"
    assert spec.plot_ylabel == "y"
    assert spec.has_canvas is True
    assert spec.solver_class_name == "QuadraticSolver"

    # Verify containers
    assert "side" in spec.containers
    assert "plot_card" in spec.containers
    assert "actions" in spec.containers

    # Verify widgets
    assert len(spec.widgets) >= 12
    types = [w.widget_type for w in spec.widgets]
    assert "ctklabel" in types
    assert "ctkentry" in types
    assert "ctkbutton" in types
    assert "ctktextbox" in types

    # Verify initial variable states
    assert spec.initial_vars.get("a") == "1"
    assert spec.initial_vars.get("b") == "-3"
    assert spec.initial_vars.get("c") == "2"


def test_ui_analyzer_so_search():
    """Verify AST extraction on Stack Overflow Search application (Project 0122)."""
    p = Path("C:/proekts/0122/src/ui/app.py")
    if not p.exists():
        pytest.skip("0122 app.py not found")

    tree = ast.parse(p.read_text(encoding="utf-8"))
    spec = analyze_ui_structure(tree)

    assert spec is not None
    assert spec.window_title == "Stack Overflow Search Pro"
    assert spec.window_width == 1420
    assert spec.window_height == 900
    assert len(spec.containers) >= 1
    assert len(spec.widgets) >= 5


def test_ui_analyzer_pure_console_no_false_positives():
    """Verify console scripts with no GUI produce None and don't trigger UI compiler."""
    code = """
def main():
    print("Hello from native x64 assembly!")
    ans = 42 * 2
    return ans
"""
    tree = ast.parse(code)
    spec = analyze_ui_structure(tree)
    assert spec is None


def test_ui_codegen_fasm_output():
    """Verify generated FASM code contains expected PE64 GUI structures, math, and GDI."""
    p = Path("C:/proekts/0124/Main.py")
    if not p.exists():
        pytest.skip("0124/Main.py not found on filesystem")

    tree = ast.parse(p.read_text(encoding="utf-8"))
    spec = analyze_ui_structure(tree)
    assert spec is not None

    asm = generate_ui_app_asm(spec)
    assert "format PE64 GUI 5.0" in asm
    assert "entry _pyfasm_entry_point" in asm
    assert "wszTitle" in asm
    assert "_pyfasm_do_solve:" in asm
    assert "_pyfasm_canvas_wnd_proc:" in asm
    assert "DwmSetWindowAttribute" in asm
    assert "CreateWindowExW" in asm
    assert "Polyline" in asm
