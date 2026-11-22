"""Comprehensive cross-target and native execution tests for PyFASM64 universal libraries."""

import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from pyfasm.compiler import PyFasmCompiler


_EXT_BY_TARGET = {
    "win64": ".exe",
    "linux": ".elf",
    "macos": ".macho",
    "myos": ".bin",
}


def _compile_and_run_win64(tmp_path: Path, name: str, source: str) -> tuple[subprocess.CompletedProcess, Path]:
    src = tmp_path / f"{name}.py"
    out = tmp_path / f"{name}.exe"
    src.write_text(source, encoding="utf-8")
    comp = PyFasmCompiler()
    ok, bin_path, log = comp.compile_file(str(src), str(out), target="win64", strict=True, keep_asm=False)
    assert ok, f"Compilation failed for {name}:\n{log}"
    assert bin_path and Path(bin_path).exists() and Path(bin_path).stat().st_size > 0
    if sys.platform != "win32":
        pytest.skip("Native win64 execution test requires Windows host")
    proc = subprocess.run(
        [str(bin_path)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc, tmp_path


def _read_bmp_info(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    assert len(data) > 54
    assert data[:2] == b"BM"
    width, height = struct.unpack_from("<ii", data, 18)
    return width, abs(height), data[54:]


def test_pure_python_numpy_math_complex_execution(tmp_path: Path) -> None:
    code = '''
import math
import numpy as np

class Box:
    def __init__(self, x):
        self.x = x

def main():
    t = tuple(i * 2 for i in range(4))
    a = [10, 20]
    starred_list = [5, *a, 30]
    starred_tuple = (*t, 99)

    mn = min(3.5, 1.25, 4.8)
    mx = max(-2.5, 2.75, 0.5)

    z = complex(3.0, 4.0)
    z_abs = abs(z)
    z_re = z.real
    z_im = z.imag

    m_sin = math.sin(0.5)
    m_cos = math.cos(0.5)
    m_sqrt = math.sqrt(9.0)
    m_atan2 = math.atan2(1.0, 1.0)
    m_log = math.log(math.e)
    m_exp = math.exp(1.0)

    arr = np.linspace(0.0, 1.0, 5)
    sarr = np.sin(arr)
    mat = np.zeros((2, 3))
    mat[0] = [1.0, 2.0, 3.0]
    mat[1, 1] = 7.5

    b = Box(11)
    has_x = hasattr(b, "x")
    setattr(b, "y", 22)
    got_x = getattr(b, "x")
    got_y = getattr(b, "y")

    cleaned = "xyhello worldyx".strip("xy ")
    sci = f"{0.00125:.3e}"
    gen = f"{12.3456789:.8g}"

    fns = []
    for k in range(3):
        fns.append(lambda v=k: v * 10)
    lam_res = [f() for f in fns]

    print("TUP", t[0], t[1], t[2], t[3])
    print("STAR", starred_list[0], starred_list[2], starred_tuple[4])
    print("MINMAX", mn, mx)
    print("CPLX", z_abs, z_re, z_im)
    print("MATH", round(m_sin * m_sin + m_cos * m_cos, 6), m_sqrt, round(m_atan2 * 4.0, 5), round(m_log, 6), round(m_exp, 5))
    print("NP", len(arr), round(float(arr[2]), 4), round(float(sarr[4]), 5), mat[0, 2], mat[1, 1])
    print("ATTR", 1 if has_x else 0, got_x, got_y)
    print("STR", cleaned, sci, gen)
    print("LAM", lam_res[0], lam_res[1], lam_res[2])

main()
'''
    proc, _ = _compile_and_run_win64(tmp_path, "pure_python_full", code)
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
    joined = "\n".join(lines)
    assert "TUP 0 2 4 6" in joined
    assert "STAR 5 20 99" in joined
    assert re.search(r"MINMAX 1\.250* 2\.750*", joined), joined
    assert re.search(r"CPLX 5(\.0+)? 3(\.0+)? 4(\.0+)?", joined), joined
    assert re.search(r"MATH 1(\.0+)? 3(\.0+)? 3\.141590* 1(\.0+)? 2\.718280*", joined), joined
    assert re.search(r"NP 5 0\.50+ 0\.841470* 3(\.0+)? 7\.50*", joined), joined
    assert "ATTR 1 11 22" in joined
    assert "STR hello world" in joined
    assert "1.250e-03" in joined
    assert "12.345679" in joined
    assert "LAM 0 10 20" in joined


def test_matplotlib_native_data_driven_savefig(tmp_path: Path) -> None:
    code = '''
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

x = np.linspace(0.0, 6.28, 32)
y1 = np.sin(x)
y2 = np.cos(x)

fig1, ax1 = plt.subplots(figsize=(6.4, 4.8), dpi=100)
fig1.patch.set_facecolor("#ffffff")
ax1.plot(x, y1, color="#1f77b4", label="sin")
ax1.scatter([0.0, 3.14, 6.28], [0.0, 0.0, 0.0], color="#ff7f0e")
ax1.axhline(0.0, color="#444444")
ax1.axvline(3.14, color="#888888")
ax1.set_title("Wave A")
ax1.set_xlabel("rad")
ax1.set_ylabel("amp")
ax1.set_xlim(0.0, 6.28)
ax1.set_ylim(-1.2, 1.2)
ax1.grid(True)
ax1.legend()
fig1.savefig("plot_a.bmp")

fig2, ax2 = plt.subplots(figsize=(6.4, 4.8), dpi=100)
ax2.plot(x, y2, color="#d62728", label="cos")
ax2.bar([1.0, 2.0, 3.0], [0.4, 0.9, 0.2], color="#2ca02c")
ax2.set_title("Wave B")
fig2.savefig("plot_b.bmp")

fig3 = Figure(figsize=(4.0, 3.0), dpi=100)
ax3 = fig3.add_subplot(111)
ax3.hist([0.1, 0.2, 0.25, 0.6, 0.65, 0.9], bins=4, color="#9467bd")
fig3.savefig("plot_hist.bmp")
'''
    proc, out_dir = _compile_and_run_win64(tmp_path, "mpl_savefig_test", code)
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"

    pa = out_dir / "plot_a.bmp"
    pb = out_dir / "plot_b.bmp"
    ph = out_dir / "plot_hist.bmp"
    assert pa.exists() and pb.exists() and ph.exists()

    wa, ha, pixa = _read_bmp_info(pa)
    wb, hb, pixb = _read_bmp_info(pb)
    wh, hh, pixh = _read_bmp_info(ph)
    assert (wa, ha) == (640, 480)
    assert (wb, hb) == (640, 480)
    assert (wh, hh) == (400, 300)
    assert len(set(pixa)) > 1
    assert len(set(pixb)) > 1
    assert len(set(pixh)) > 1
    assert pa.read_bytes() != pb.read_bytes()


def test_pygame_offscreen_surface_drawing_and_io(tmp_path: Path) -> None:
    code = '''
import pygame

pygame.init()
surf = pygame.Surface((200, 120))
surf.fill(pygame.Color(240, 240, 240))

r = pygame.Rect(10, 10, 40, 30)
r_moved = r.move(20, 15)
r_copy = r.copy()
r_copy.move_ip(5, 5)
r_inf = r.inflate(10, 10)
bound = pygame.Rect(0, 0, 200, 120)
r_clamp = pygame.Rect(180, 100, 40, 30)
r_clamp.clamp_ip(bound)
hit = r.collidelist([pygame.Rect(100, 100, 10, 10), pygame.Rect(20, 20, 20, 20)])

pygame.draw.rect(surf, (220, 40, 40), r, 0)
pygame.draw.rect(surf, (20, 20, 200), r_moved, 2)
pygame.draw.circle(surf, (20, 180, 40), (100, 60), 25, 2)
pygame.draw.ellipse(surf, (200, 120, 20), pygame.Rect(130, 10, 50, 30))
pygame.draw.polygon(surf, (150, 40, 190), [(20, 90), (45, 70), (70, 95)])
pygame.draw.lines(surf, (10, 140, 160), False, [(90, 95), (120, 80), (150, 105)], 2)
pygame.draw.arc(surf, (80, 80, 80), pygame.Rect(150, 60, 40, 40), 0.0, 3.14, 2)

font = pygame.font.SysFont("Arial", 16)
txt = font.render("OK", True, (10, 10, 10))
surf.blit(txt, (85, 8))

grp = pygame.sprite.Group()
scaled = pygame.transform.scale(surf, (100, 60))
flipped = pygame.transform.flip(scaled, True, False)

pygame.image.save(surf, "pg_main.bmp")
pygame.image.save(flipped, "pg_flip.bmp")
loaded = pygame.image.load("pg_main.bmp")

cx, cy = r.center
tlx, tly = r_moved.topleft
print("PG", surf.get_width(), surf.get_height(), r_inf.width, cx, cy, tlx, tly, hit, loaded.get_width(), r_clamp.x)
pygame.quit()
'''
    proc, out_dir = _compile_and_run_win64(tmp_path, "pygame_offscreen_test", code)
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    assert "PG 200 120 50 30 25 30 25 1 200 160" in proc.stdout

    pm = out_dir / "pg_main.bmp"
    pf = out_dir / "pg_flip.bmp"
    assert pm.exists() and pf.exists()
    wm, hm, pixm = _read_bmp_info(pm)
    wf, hf, pixf = _read_bmp_info(pf)
    assert (wm, hm) == (200, 120)
    assert (wf, hf) == (100, 60)
    assert len(set(pixm)) > 5
    assert len(set(pixf)) > 5


_FRAMEWORK_SAMPLES = {
    "tkinter": '''
import tkinter as tk
from tkinter import ttk
root = tk.Tk()
root.title("Tk")
var = tk.StringVar(value="v")
ttk.Label(root, textvariable=var).pack()
tk.Entry(root).pack()
tk.Button(root, text="Go").pack()
root.update()
''',
    "customtkinter": '''
import customtkinter as ctk
app = ctk.CTk()
app.title("CTk")
frm = ctk.CTkFrame(app)
frm.pack(fill="both", expand=True)
ctk.CTkLabel(frm, text="Hi").pack()
ctk.CTkSlider(frm, from_=0, to=10).pack()
''',
    "pyqt5": '''
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton
import sys
app = QApplication(sys.argv)
w = QMainWindow()
c = QWidget()
l = QVBoxLayout(c)
l.addWidget(QLabel("Qt5"))
l.addWidget(QPushButton("OK"))
w.setCentralWidget(c)
w.show()
''',
    "pyqt6": '''
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QComboBox, QSpinBox, QProgressBar
from PyQt6.QtCore import QTimer
import sys
app = QApplication(sys.argv)
w = QMainWindow()
c = QWidget()
l = QVBoxLayout(c)
l.addWidget(QLabel("Qt6"))
cb = QComboBox()
cb.addItem("A")
l.addWidget(cb)
sp = QSpinBox()
sp.setValue(5)
l.addWidget(sp)
pb = QProgressBar()
pb.setValue(50)
l.addWidget(pb)
w.setCentralWidget(c)
t = QTimer()
w.show()
''',
    "pyside6": '''
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
import sys
app = QApplication(sys.argv)
w = QWidget()
l = QVBoxLayout(w)
l.addWidget(QLabel("PySide6"))
l.addWidget(QPushButton("Run"))
w.show()
''',
    "pygame": '''
import pygame
pygame.init()
s = pygame.display.set_mode((160, 120))
s.fill((10, 20, 30))
pygame.draw.rect(s, (255, 0, 0), pygame.Rect(5, 5, 20, 20))
pygame.display.flip()
pygame.quit()
''',
    "matplotlib": '''
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
ax.plot([1.0, 2.0, 3.0], [2.0, 4.0, 1.0], color="#1f77b4")
ax.grid(True)
fig.savefig("out.bmp")
''',
}


@pytest.mark.parametrize("target", ["win64", "linux", "macos", "myos"])
@pytest.mark.parametrize("framework", list(_FRAMEWORK_SAMPLES.keys()))
def test_cross_target_strict_all_gui_frameworks(tmp_path: Path, target: str, framework: str) -> None:
    src = tmp_path / f"{framework}.py"
    out = tmp_path / f"{framework}_{target}{_EXT_BY_TARGET[target]}"
    src.write_text(_FRAMEWORK_SAMPLES[framework], encoding="utf-8")

    comp = PyFasmCompiler()
    ok, bin_path, log = comp.compile_file(str(src), str(out), target=target, strict=True, keep_asm=False)
    assert ok, f"Strict compile failed ({framework}, {target}):\n{log}"
    assert bin_path and Path(bin_path).exists() and Path(bin_path).stat().st_size > 0


def test_zero_hardcoded_templates_regression() -> None:
    src_dir = Path(__file__).resolve().parent.parent / "src" / "pyfasm"
    forbidden = ("StackOverflow", "SO_ITEMS", "2*x^2 - 4*x - 6")
    for py_file in sorted(src_dir.glob("*.py")):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            assert token not in text, f"Found forbidden hardcoded template token {token!r} in {py_file.name}"
