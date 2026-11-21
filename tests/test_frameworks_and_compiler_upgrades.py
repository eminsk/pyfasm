from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from pyfasm.compiler import PyFasmCompiler


def _compile_strict_win64(
    tmp_path: Path, code: str, name: str
) -> tuple[str, Path, PyFasmCompiler]:
    src = tmp_path / f"{name}.py"
    exe = tmp_path / f"{name}.exe"
    src.write_text(code, encoding="utf-8")

    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(code, target="win64", strict=True)
    assert not compiler.last_diagnostics.errors, compiler.last_diagnostics.render()
    assert not compiler.last_diagnostics.warnings, compiler.last_diagnostics.render()

    if sys.platform == "win32":
        ok, out_exe, log = compiler.compile_file(
            str(src), output_binary=str(exe), target="win64", strict=True
        )
        assert ok, f"Win64 FASM build failed:\n{log}"
        assert Path(out_exe).exists()
        return asm, Path(out_exe), compiler
    return asm, exe, compiler


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_compiler_recursive_nested_fib_and_closures_strict_win64(tmp_path: Path):
    code = """
def fib(n: int) -> int:
    def _fib(k: int) -> tuple:
        if k == 0:
            return (0, 1)
        a, b = _fib(k >> 1)
        c = a * (2 * b - a)
        d = a * a + b * b
        if k & 1:
            return (d, c + d)
        return (c, d)
    res, _ = _fib(n)
    return res

def parity_sum(limit: int) -> int:
    def is_even(n: int) -> int:
        if n == 0:
            return 1
        return is_odd(n - 1)
    def is_odd(n: int) -> int:
        if n == 0:
            return 0
        return is_even(n - 1)
    total = 0
    for i in range(limit + 1):
        if is_even(i):
            total += i
    return total

def closure_chain_sum(step: int, n: int) -> int:
    def rec(k: int) -> int:
        if k <= 0:
            return 0
        return k * step + rec(k - 1)
    return rec(n)

def scale_float(x: int) -> float:
    return x * 1.5

def main() -> int:
    print(fib(0), fib(1), fib(10), fib(20))
    print(parity_sum(10))
    print(closure_chain_sum(3, 4))
    fn = scale_float
    val = fn(5)
    print(f"{val:.2f}")
    return 0
"""
    asm, exe, _ = _compile_strict_win64(tmp_path, code, "recursive_nested")
    assert "_fib" in asm

    if sys.platform == "win32":
        res = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=10)
        assert res.returncode == 0, res.stderr
        lines = [line.strip() for line in res.stdout.strip().splitlines()]
        assert lines == [
            "0 1 55 6765",
            "30",
            "30",
            "7.50",
        ]


def test_compiler_reflected_dunders_abs_and_fstring_formats_strict_win64(tmp_path: Path):
    code = """
class Box:
    def __init__(self, v: int):
        self.v = v

    def __abs__(self) -> int:
        return -self.v if self.v < 0 else self.v

    def __radd__(self, other: int) -> int:
        return other + self.v

    def __rsub__(self, other: int) -> int:
        return other - self.v

    def __rmul__(self, other: int) -> int:
        return other * self.v

    def __rtruediv__(self, other: int) -> float:
        return float(other) / self.v

    def __rfloordiv__(self, other: int) -> int:
        return other // self.v

    def __rmod__(self, other: int) -> int:
        return other % self.v

def main() -> int:
    b = Box(5)
    nb = Box(-12)
    print(abs(nb))
    print(10 + b, 20 - b, 3 * b, 23 // b, 23 % b)
    q = 15 / Box(4)
    print(f"{q:.2f}")
    name = "Мир"
    pi = 3.14159
    neg = -42
    print(f"{name!r}")
    print(f"{pi:.2f} {pi:.0f} {3.5:6.2f}")
    print(f"{255:x} {255:X} {42:04x} {5:04b} {63:o} {7:05d} {neg:05d}")
    return 0
"""
    _asm, exe, _ = _compile_strict_win64(tmp_path, code, "dunders_fstrings")
    if sys.platform == "win32":
        res = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=10)
        assert res.returncode == 0, res.stderr
        lines = res.stdout.splitlines()
        assert lines[0] == "12"
        assert lines[1] == "15 15 15 4 3"
        assert lines[2] == "3.75"
        assert lines[3] == "'Мир'"
        assert lines[4] == "3.14 3   3.50"
        assert lines[5] == "ff FF 002a 0101 77 00007 -0042"


def test_gui_tkinter_and_customtkinter_strict_win64(tmp_path: Path):
    code = """
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

def main() -> int:
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.title("PyFASM CTk App")
    root.geometry("640x480")

    sv = tk.StringVar("init")
    lbl = ctk.CTkLabel(root, text="Ready")
    entry = ctk.CTkEntry(root, placeholder_text="Type here")

    def on_click():
        sv.set(entry.get())
        lbl.configure(text=sv.get())
        messagebox.showinfo("Info", sv.get())

    btn = ctk.CTkButton(root, text="Run", command=on_click)
    chk = ctk.CTkCheckBox(root, text="Enable")
    cvs = tk.Canvas(root, width=300, height=200)
    cvs.create_rectangle(10, 10, 80, 60, fill="#ff0000")
    cvs.create_oval(90, 10, 140, 60, fill="blue")
    cvs.create_line(0, 0, 50, 50, fill="green")
    cvs.create_text(20, 100, text="OK", fill="white")
    cvs.delete("all")
    btn.pack()
    chk.pack()
    lbl.pack()
    entry.pack()
    if False:
        root.mainloop()
    root.destroy()
    return 0
"""
    asm, _exe, _ = _compile_strict_win64(tmp_path, code, "tk_ctk_gui")
    assert "_pyfasm_create_button" in asm
    assert "_pyfasm_create_checkbox" in asm
    assert "_pyfasm_stringvar_create" in asm
    assert "_pyfasm_canvas_set_color" in asm
    assert "_pyfasm_canvas_clear" in asm
    assert "_pyfasm_resize_window" in asm
    assert "_pyfasm_destroy_window" in asm


@pytest.mark.parametrize(
    ("pkg", "exec_call"),
    [
        ("PyQt5.QtWidgets", "app.exec_()"),
        ("PyQt6.QtWidgets", "app.exec()"),
        ("PySide6.QtWidgets", "app.exec()"),
    ],
)
def test_gui_qt5_qt6_pyside6_strict_win64(tmp_path: Path, pkg: str, exec_call: str):
    code = f"""
import sys
from {pkg} import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QListWidget,
    QMessageBox,
)

def main() -> int:
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("PyFASM Qt App")
    win.resize(520, 380)

    central = QWidget()
    layout = QVBoxLayout()
    lbl = QLabel("Hello Qt")
    edit = QLineEdit("initial")
    chk = QCheckBox("Agree")
    lst = QListWidget()
    btn = QPushButton("Submit")

    def on_submit():
        txt = edit.text()
        lbl.setText(txt)
        lst.addItem(txt)
        if chk.isChecked():
            QMessageBox.information(win, "Qt", txt)

    btn.clicked.connect(on_submit)
    chk.setChecked(True)
    layout.addWidget(lbl)
    layout.addWidget(edit)
    layout.addWidget(chk)
    layout.addWidget(lst)
    layout.addWidget(btn)
    central.setLayout(layout)
    win.setCentralWidget(central)
    win.show()
    if False:
        {exec_call}
    win.close()
    return 0
"""
    safe_pkg = pkg.split(".")[0].lower()
    asm, _exe, _ = _compile_strict_win64(tmp_path, code, f"qt_{safe_pkg}")
    assert "_pyfasm_register_control_callback" in asm
    assert "_pyfasm_show_window" in asm
    assert "_pyfasm_resize_window" in asm
    assert "_pyfasm_checkbox_get" in asm
    assert "_pyfasm_checkbox_set" in asm
    assert "_pyfasm_listbox_add" in asm


def test_gui_flet_strict_win64(tmp_path: Path):
    code = """
import flet as ft

def main(page: ft.Page):
    page.title = "PyFASM Flet App"
    status = ft.Text(value="Ready")
    inp = ft.TextField(label="Input")
    chk = ft.Checkbox(label="Enabled", value=True)

    def on_go(e):
        if chk.value:
            status.value = inp.value
        else:
            status.value = "Disabled"
        page.update()

    btn = ft.ElevatedButton(text="Go", on_click=on_go)
    page.add(ft.Column([status, inp, chk, btn]))
    page.update()

if False:
    ft.app(target=main)
"""
    asm, _exe, _ = _compile_strict_win64(tmp_path, code, "flet_gui")
    assert "_pyfasm_set_window_title" in asm
    assert "_pyfasm_create_label" in asm
    assert "_pyfasm_create_edit" in asm
    assert "_pyfasm_create_checkbox" in asm
    assert "_pyfasm_create_button" in asm
    assert "_pyfasm_unified_get" in asm
    assert "_pyfasm_unified_set" in asm
    assert "_pyfasm_checkbox_get" in asm
    assert "_pyfasm_checkbox_set" in asm


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_pygame_live_execution_strict_win64(tmp_path: Path):
    code = """
import pygame

def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((320, 240))
    pygame.display.set_caption("PyFASM Pygame Test")
    clock = pygame.time.Clock()
    r1 = pygame.Rect(10, 20, 40, 30)
    r2 = pygame.Rect(30, 35, 20, 20)
    r3 = pygame.Rect(200, 200, 10, 10)
    font = pygame.font.SysFont("Arial", 16)
    label = font.render("OK", True, (255, 255, 255))

    hit12 = 1 if r1.colliderect(r2) else 0
    hit13 = 1 if r1.colliderect(r3) else 0
    pt_hit = 1 if r1.collidepoint(25, 30) else 0
    print(r1.right, r1.bottom, hit12, hit13, pt_hit)
    print(pygame.QUIT, pygame.KEYDOWN, pygame.K_SPACE)

    for _i in range(3):
        events = pygame.event.get()
        keys = pygame.key.get_pressed()
        pos = pygame.mouse.get_pos()
        screen.fill((10, 20, 30))
        pygame.draw.rect(screen, (255, 0, 0), r1)
        pygame.draw.circle(screen, (0, 255, 0), (100, 100), 20)
        pygame.draw.line(screen, (0, 0, 255), (0, 0), (50, 50), 2)
        screen.blit(label, (10, 10))
        pygame.display.flip()
        clock.tick(120)

    pygame.quit()
    print("PYGAME_OK")
    return 0
"""
    _asm, exe, _ = _compile_strict_win64(tmp_path, code, "pygame_live")
    res = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert res.returncode == 0, res.stderr
    lines = [line.strip() for line in res.stdout.strip().splitlines()]
    assert lines[0] == "50 50 1 0 1"
    assert lines[1] == "256 768 32"
    assert lines[-1] == "PYGAME_OK"


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_fastapi_uvicorn_live_http_server_strict_win64(tmp_path: Path):
    port = _free_local_port()
    code = f"""
from fastapi import FastAPI, APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse
import uvicorn

app = FastAPI(title="PyFASM API")
router = APIRouter(prefix="/api")

@app.get("/health")
def health() -> dict:
    return {{"status": "ok"}}

@app.get("/sum/{{a}}/{{b}}")
def add_nums(a: int, b: int) -> dict:
    return {{"sum": a + b}}

@app.get("/greet/{{name}}")
async def greet(name: str, prefix: str = "Hi") -> dict:
    return {{"msg": f"{{prefix}} {{name}}"}}

@app.post("/echo")
def echo(body: str) -> dict:
    return {{"echo": body}}

@router.get("/info")
def router_info() -> dict:
    return {{"items": [1, 2, 3], "nested": {{"ok": "yes"}}, "count": 3}}

@app.get("/flag")
def flag() -> bool:
    return True

@app.get("/page")
def html_page():
    return HTMLResponse("<h1>PyFASM</h1>")

@app.get("/text")
def plain_text():
    return PlainTextResponse("pong")

app.include_router(router)

def main() -> int:
    uvicorn.run(app, host="127.0.0.1", port={port})
    return 0
"""
    _asm, exe, _ = _compile_strict_win64(tmp_path, code, "fastapi_live")
    proc = subprocess.Popen(
        [str(exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        ready = False
        for _ in range(60):
            if proc.poll() is not None:
                out, err = proc.communicate()
                pytest.fail(
                    f"FastAPI server exited early ({proc.returncode}):\n{out.decode(errors='replace')}\n{err.decode(errors='replace')}"
                )
            try:
                with urllib.request.urlopen(f"{base_url}/health", timeout=0.5) as resp:
                    if resp.status == 200:
                        assert json.loads(resp.read().decode("utf-8")) == {"status": "ok"}
                        ready = True
                        break
            except Exception:
                time.sleep(0.1)
        assert ready, "Compiled FastAPI server did not start listening in time"

        with urllib.request.urlopen(f"{base_url}/sum/19/23", timeout=2) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) == {"sum": 42}

        with urllib.request.urlopen(
            f"{base_url}/greet/%D0%9C%D0%B8%D1%80?prefix=%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82",
            timeout=2,
        ) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) == {"msg": "Привет Мир"}

        req = urllib.request.Request(
            f"{base_url}/echo",
            data="Тест PyFASM".encode("utf-8"),
            method="POST",
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) == {"echo": "Тест PyFASM"}

        with urllib.request.urlopen(f"{base_url}/api/info", timeout=2) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) == {
                "items": [1, 2, 3],
                "nested": {"ok": "yes"},
                "count": 3,
            }

        with urllib.request.urlopen(f"{base_url}/flag", timeout=2) as resp:
            assert resp.status == 200
            assert json.loads(resp.read().decode("utf-8")) is True

        with urllib.request.urlopen(f"{base_url}/page", timeout=2) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            assert resp.read().decode("utf-8") == "<h1>PyFASM</h1>"

        with urllib.request.urlopen(f"{base_url}/text", timeout=2) as resp:
            assert resp.status == 200
            assert "text/plain" in resp.headers.get("Content-Type", "")
            assert resp.read().decode("utf-8") == "pong"

        with urllib.request.urlopen(f"{base_url}/openapi.json", timeout=2) as resp:
            assert resp.status == 200
            schema = json.loads(resp.read().decode("utf-8"))
            assert "/health" in schema.get("paths", {})
            assert "/sum/{a}/{b}" in schema.get("paths", {})

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{base_url}/does-not-exist", timeout=2)
        assert exc_info.value.code == 404
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def test_customtkinter_canvas_no_template_hijack_and_flet_controls(tmp_path: Path):
    """Verify CustomTkinter and Flet code compiles authentically without falling back to hardcoded quadratic solver template."""
    code = """
import customtkinter as ctk

class MyDrawingStudio(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("My Unique Studio")
        self.geometry("800x600")
        f = ctk.CTkFont(family="Consolas", size=14, weight="bold")
        lbl = ctk.CTkLabel(self, text="Real Studio Label", font=f)
        btn = ctk.CTkButton(self, text="Custom Action", font=f)
        ent = ctk.CTkEntry(self, font=f)
        ent.delete(0, "end")
        ent.insert(0, "42")
        vals = [10, 5, 20, 1]
        lo = min(vals)
        hi = max(vals)
        print("STUDIO_LOADED", lo, hi)

def main() -> int:
    app = MyDrawingStudio()
    return 0
"""
    asm, exe, _ = _compile_strict_win64(tmp_path, code, "ctk_studio_real")
    assert "a  ·  коэффициент при x²" not in asm
    assert "_pyfasm_h_btn_solve" not in asm
    assert "Real Studio Label" in asm
    assert "My Unique Studio" in asm
    if sys.platform == "win32":
        res = subprocess.run([str(exe)], capture_output=True, text=True, encoding="utf-8", timeout=10)
        assert res.returncode == 0, res.stderr
        assert "STUDIO_LOADED 1 20" in res.stdout


def test_flet_advanced_controls_and_events_strict_win64(tmp_path: Path):
    """Verify advanced Flet controls (Card, Container, TextField, clean, window properties) compile cleanly in strict mode."""
    code = """
import flet as ft

def page_handler(page) -> int:
    page.title = "Flet Modern App"
    page.window_width = 800
    page.window_height = 600
    txt = ft.Text("Hello Flet")
    inp = ft.TextField(value="Input Text")
    btn = ft.ElevatedButton("Submit")
    card = ft.Card(content=ft.Container(content=txt))
    page.add(card, inp, btn)
    page.clean()
    page.update()
    print("FLET_STUDIO_OK")
    return 0

def main() -> int:
    ft.app(target=page_handler)
    return 0
"""
    asm, _exe, _ = _compile_strict_win64(tmp_path, code, "flet_advanced")
    assert "Flet Modern App" in asm
    assert "Hello Flet" in asm

