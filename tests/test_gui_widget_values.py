"""
Regression tests for values read back from native GUI widgets:
1. StringVar.get() / Entry.get() return text, at module level and through self.<field>.
2. Listbox.size() and QComboBox.count() return the number of items.
3. after(ms, root.destroy) and QTimer.singleShot(ms, app.quit) end the event loop.
4. A user-defined show() method is an ordinary call, not the event loop.

The programs open a real window, so on non-Windows hosts they need Wine and a display
(an existing DISPLAY or xvfb-run); without them the tests fail with a clear message
instead of passing over the check.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pyfasm.ast_parser import AstAnalyzer
from pyfasm.compiler import PyFasmCompiler
from pyfasm.types import TYPE_INT, TYPE_STR


def _gui_launcher() -> list:
    if sys.platform == "win32":
        return []
    wine = shutil.which("wine") or shutil.which("wine64")
    if not wine:
        if os.environ.get("PYFASM_REQUIRE_WINE") == "1":
            raise RuntimeError(
                "Wine is required to execute the compiled Windows GUI binary on "
                f"{sys.platform}. Install it (Debian/Ubuntu: 'sudo apt-get install wine wine64')."
            )
        pytest.skip(f"Running Windows GUI binary on {sys.platform} requires Wine (not installed)")
    if os.environ.get("DISPLAY"):
        return [wine]
    xvfb = shutil.which("xvfb-run")
    if not xvfb:
        if os.environ.get("PYFASM_REQUIRE_WINE") == "1":
            raise RuntimeError(
                "A display is required to open a native window: set DISPLAY or install "
                "xvfb (Debian/Ubuntu: 'sudo apt-get install xvfb')."
            )
        pytest.skip(
            f"A display or xvfb-run is required to run Windows GUI binary under Wine on {sys.platform}"
        )
    return [xvfb, "-a", wine]


def _compile_and_run_gui(tmp_path: Path, name: str, source: str) -> str:
    launcher = _gui_launcher()
    src_file = tmp_path / f"{name}.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / f"{name}.exe"

    ok, _, log = PyFasmCompiler().compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"

    res = subprocess.Popen(
        launcher + [str(out_exe)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )
    try:
        out, _ = res.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        res.kill()
        out, _ = res.communicate()
        pytest.fail(f"GUI program did not exit (event loop never ended). Output so far:\n{out}")
    assert res.returncode == 0, out
    return out


def test_widget_variables_keep_handle_type():
    source = """
import tkinter as tk
root = tk.Tk()
var = tk.StringVar(value="0")
e = tk.Entry(root)
e.insert(0, "hello")
s = var.get()
t = e.get()
print(s, t, len(t))
"""
    module = AstAnalyzer().parse_source(source)
    local_vars = module.functions["main"].local_vars

    def _type(name):
        return local_vars[name].var_type if name in local_vars else module.global_var_types[name]

    def _kind(name):
        return local_vars[name].widget_kind if name in local_vars else module.global_widget_kinds.get(name)

    assert _type("var") == TYPE_INT and _kind("var") == "strvar"
    assert _type("e") == TYPE_INT and _kind("e") == "entry"
    assert _type("s") == TYPE_STR
    assert _type("t") == TYPE_STR


def test_tkinter_stringvar_and_entry_get_return_text(tmp_path: Path):
    source = """
import tkinter as tk
root = tk.Tk()
var = tk.StringVar(value="0")
var.set("7")
e = tk.Entry(root)
e.pack()
e.insert(0, "hello")
print("A", var.get(), e.get())
s = var.get()
t = e.get()
print("B", s, t, len(t))
root.destroy()
print("DONE")
"""
    out = _compile_and_run_gui(tmp_path, "tk_get", source)
    assert "A 7 hello" in out
    assert "B 7 hello 5" in out
    assert "DONE" in out


def test_tkinter_widget_fields_and_user_show_method(tmp_path: Path):
    source = """
import tkinter as tk
class App:
    def __init__(self, root):
        self.root = root
        self.var = tk.StringVar(value="0")
        self.entry = tk.Entry(root)
        self.entry.pack()
        self.entry.insert(0, "hello")
    def show(self):
        self.var.set("9")
        print("IN", self.var.get(), self.entry.get())
root = tk.Tk()
app = App(root)
app.show()
print("OUT", app.var.get(), app.entry.get())
root.destroy()
print("DONE")
"""
    out = _compile_and_run_gui(tmp_path, "tk_fields", source)
    assert "IN 9 hello" in out
    assert "OUT 9 hello" in out
    assert "DONE" in out


def test_tkinter_listbox_size_and_after_destroy(tmp_path: Path):
    source = """
import tkinter as tk
root = tk.Tk()
lb = tk.Listbox(root)
lb.pack()
for name in ["a", "b", "c"]:
    lb.insert(tk.END, name)
print("LB", lb.size())
root.after(300, root.destroy)
root.mainloop()
print("DONE")
"""
    out = _compile_and_run_gui(tmp_path, "tk_listbox", source)
    assert "LB 3" in out
    assert "DONE" in out


def test_customtkinter_window_class_values_and_after_destroy(tmp_path: Path):
    source = """
import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CTk demo")
        self.clicks = 0
        self.label = ctk.CTkLabel(self, text="Clicks: 0")
        self.label.pack()
        self.entry = ctk.CTkEntry(self)
        self.entry.pack()
        self.button = ctk.CTkButton(self, text="Go", command=self.on_click)
        self.button.pack()

    def on_click(self):
        self.clicks += 1
        self.label.configure(text=f"Clicks: {self.clicks}")

app = App()
app.on_click()
app.on_click()
app.entry.insert(0, "bob")
print("CTK", app.clicks, app.label.cget("text"), app.entry.get())
app.after(300, app.destroy)
app.mainloop()
print("CTK_DONE")
"""
    out = _compile_and_run_gui(tmp_path, "ctk_values", source)
    assert "CTK 2 Clicks: 2 bob" in out
    assert "CTK_DONE" in out


@pytest.mark.parametrize("binding", ["PyQt5", "PyQt6"])
def test_qt_combobox_count_and_single_shot_quit(tmp_path: Path, binding: str):
    exec_call = "app.exec_()" if binding == "PyQt5" else "app.exec()"
    source = f"""
import sys
from {binding}.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox
from {binding}.QtCore import QTimer

class Win(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt demo")
        self.n = 0
        c = QWidget()
        lay = QVBoxLayout(c)
        self.label = QLabel("n=0")
        self.edit = QLineEdit()
        self.edit.setText("abc")
        self.cb = QComboBox()
        self.cb.addItems(["x", "y", "z"])
        lay.addWidget(self.label)
        lay.addWidget(self.edit)
        lay.addWidget(self.cb)
        self.setCentralWidget(c)

    def add(self):
        self.n += 1
        self.label.setText(f"n={{self.n}}")

app = QApplication(sys.argv)
w = Win()
w.show()
w.add()
w.add()
print("QT", w.n, w.label.text(), w.edit.text(), w.cb.count())
QTimer.singleShot(300, app.quit)
{exec_call}
print("QT_DONE")
"""
    out = _compile_and_run_gui(tmp_path, f"qt_values_{binding.lower()}", source)
    assert "QT 2 n=2 abc 3" in out
    assert "QT_DONE" in out
