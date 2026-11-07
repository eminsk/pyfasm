"""
Tests for Native Tkinter and Canvas FASM Codegen & Assembly.
Verifies that pure Python Tkinter code compiles directly into native Win32/GDI
assembly and PE64 machine code without Python VM, Tcl/Tk DLLs, or external interpreters.
"""
import sys
import ast
import tempfile
from pathlib import Path
import pytest
from pyfasm.ast_parser import AstAnalyzer
from pyfasm.codegen_x64 import X64CodeGen
from pyfasm.compiler import PyFasmCompiler

if sys.platform != "win32":
    pytest.skip("Win64 native tests require Windows environment", allow_module_level=True)


def test_tkinter_widgets_and_config_asm_generation():
    """Verify Button, Label, Checkbutton, configure(text=...), and messagebox emit native FASM."""
    code = '''
import tkinter as tk
from tkinter import messagebox

class CounterApp:
    def __init__(self, root):
        self.root = root
        self.count = 0
        self.lbl = tk.Label(root, text="Count: 0")
        self.btn = tk.Button(root, text="+1", command=self.increment)
        self.chk = tk.Checkbutton(root, text="Enable auto-reset")

    def increment(self):
        self.count = self.count + 1
        self.lbl.configure(text="Count: updated")
        messagebox.showinfo("Status", "Counter incremented")

root = tk.Tk()
app = CounterApp(root)
root.mainloop()
'''
    analyzer = AstAnalyzer()
    mod = analyzer.parse_source(code)
    codegen = X64CodeGen(mod, target="win64")
    asm = codegen.generate()

    # Verify native Win32 FASM calls
    assert "_pyfasm_create_label" in asm
    assert "_pyfasm_create_button" in asm
    assert "_pyfasm_create_checkbox" in asm
    assert "_pyfasm_set_text" in asm
    assert "_pyfasm_message_box" in asm
    assert "_pyfasm_run_window_loop" in asm
    assert "CreateWindowExW" in asm
    assert "MessageBoxW" in asm


def test_tkinter_canvas_drawing_primitives_asm_generation():
    """Verify Canvas create_line, create_rectangle, create_oval, create_text emit native GDI FASM."""
    code = '''
import tkinter as tk

class CanvasArtApp:
    def __init__(self, root):
        self.root = root
        self.cvs = tk.Canvas(root, width=500, height=400)
        self.cvs.create_line(10, 10, 200, 50)
        self.cvs.create_rectangle(20, 20, 150, 100)
        self.cvs.create_oval(180, 20, 280, 100)
        self.cvs.create_text(100, 150, text="Native FASM Drawing")

root = tk.Tk()
app = CanvasArtApp(root)
root.mainloop()
'''
    analyzer = AstAnalyzer()
    mod = analyzer.parse_source(code)
    codegen = X64CodeGen(mod, target="win64")
    asm = codegen.generate()

    assert "_pyfasm_canvas_create_line" in asm
    assert "_pyfasm_canvas_create_rectangle" in asm
    assert "_pyfasm_canvas_create_oval" in asm
    assert "_pyfasm_canvas_create_text" in asm
    assert "MoveToEx" in asm
    assert "LineTo" in asm
    assert "Rectangle" in asm
    assert "Ellipse" in asm
    assert "TextOutW" in asm
    assert "GetDC" in asm
    assert "ReleaseDC" in asm


def test_tkinter_native_binary_assembly():
    """Verify complete end-to-end compilation through FASM.EXE producing a valid native PE64 executable."""
    code = '''
import tkinter as tk

class MinimalApp:
    def __init__(self, root):
        self.root = root
        self.lbl = tk.Label(root, text="FASM Native Window")
        self.btn = tk.Button(root, text="Action", command=self.on_click)

    def on_click(self):
        self.lbl.configure(text="Action Performed")

root = tk.Tk()
app = MinimalApp(root)
'''
    compiler = PyFasmCompiler()
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_file = Path(tmp_dir) / "app.py"
        exe_file = Path(tmp_dir) / "app.exe"
        src_file.write_text(code, encoding="utf-8")

        success, out_bin, log = compiler.compile_file(str(src_file), output_binary=str(exe_file))
        assert success, f"Compilation failed with log: {log}"
        assert exe_file.exists(), "Output executable was not created"
        assert exe_file.stat().st_size > 1000, "Executable is too small"


def test_tkinter_canvas_end_to_end_assembly():
    """Verify Canvas drawing primitives compile end-to-end through FASM.EXE into PE64 binary."""
    code = '''
import tkinter as tk

class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.cvs = tk.Canvas(root, width=400, height=300)
        self.cvs.create_line(0, 0, 100, 100)
        self.cvs.create_rectangle(10, 10, 50, 50)
        self.cvs.create_oval(60, 60, 120, 120)
        self.cvs.create_text(50, 50, text="Hello FASM")

root = tk.Tk()
app = DrawingApp(root)
'''
    compiler = PyFasmCompiler()
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_file = Path(tmp_dir) / "drawing_app.py"
        exe_file = Path(tmp_dir) / "drawing_app.exe"
        src_file.write_text(code, encoding="utf-8")

        success, out_bin, log = compiler.compile_file(str(src_file), output_binary=str(exe_file))
        assert success, f"Canvas compilation failed with log: {log}"
        assert exe_file.exists(), "Canvas output executable was not created"
        assert exe_file.stat().st_size > 1000, "Executable is too small"
