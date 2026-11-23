"""Regression tests for the extended pygame shim: transform.rotozoom/scale2x,
Surface.get_at/set_at/subsurface and extra pygame.mixer call shapes."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pyfasm.compiler import PyFasmCompiler


def compile_asm(source: str) -> str:
    return PyFasmCompiler().compile_source_to_asm(source, target="win64")


APP = """
import pygame

def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((320, 240))
    r1 = pygame.Rect(5, 6, 7, 8)
    area = r1.colliderect(pygame.Rect(6, 7, 10, 10))
    img = pygame.image.load("test.png")
    img2 = pygame.transform.scale(img, (64, 64))
    img3 = pygame.transform.rotozoom(img2, 45, 1.5)
    img4 = pygame.transform.scale2x(img2)
    c = img2.get_at((3, 4))
    pygame.Surface.set_at(img2, (1, 2), (255, 0, 0))
    part = img2.subsurface(pygame.Rect(0, 0, 16, 16))
    pygame.mixer.init()
    snd = pygame.mixer.Sound("beep.wav")
    pygame.mixer.Sound.play(snd)
    pygame.mixer.Channel(0).set_volume(0.5)
    pygame.mixer.stop()
    pygame.mouse.set_visible(False)
    pygame.mouse.set_pos((10, 20))
    pygame.key.set_repeat(10, 20)
    pygame.event.pump()
    pygame.event.clear()
    pygame.event.set_blocked(pygame.MOUSEMOTION)
    pygame.event.post(pygame.event.Event(pygame.USEREVENT))
    pygame.event.wait()
    pygame.key.set_mods(pygame.KMOD_SHIFT)
    pygame.mouse.get_rel()
    pygame.font.get_fonts()
    pygame.transform.rotate(img2, 90)
    pygame.time.get_ticks()
    pygame.quit()
    return 0
"""


def test_rotozoom_emits_transform_call():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_transform_rotozoom" in asm


def test_scale2x_emits_transform_call():
    asm = compile_asm(APP)
    assert "mov rax, 4000000000000000h" in asm


def test_get_at_set_at_emit_pixel_calls():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_get_at" in asm
    assert "call _pyfasm_pg_set_at" in asm


def test_subsurface_emits_subsurface_call():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_subsurface" in asm


def test_mixer_variants_route_to_noop():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_mixer_noop" in asm


def test_mouse_set_visible_and_set_pos_emit_calls():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_mouse_set_visible" in asm
    assert "call _pyfasm_pg_mouse_set_pos" in asm


def test_key_set_repeat_emits_call():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_key_set_repeat" in asm


def test_event_helpers_routed():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_pump_messages" in asm
    assert "call _pyfasm_pg_event_post" in asm
    assert "call _pyfasm_pg_event_wait" in asm
    assert "pygame constant USEREVENT" in asm
    assert "pygame constant MOUSEMOTION" in asm
    assert "pygame constant KMOD_SHIFT" in asm


def test_transform_rotate_emits_call():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_transform_rotozoom" in asm


def test_time_get_ticks_and_font_list():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_get_ticks" in asm


def test_no_pygame_attribute_fallbacks_left():
    asm = compile_asm(APP)
    assert "safe fallback for module/class attribute" not in asm


def test_runtime_defines_all_emitted_symbols():
    from pyfasm.runtime_win64_pygame import WIN64_PYGAME_RUNTIME_CODE

    asm = compile_asm(APP)
    for sym in ("_pyfasm_pg_get_at", "_pyfasm_pg_set_at", "_pyfasm_pg_subsurface",
                "_pyfasm_pg_mouse_set_pos", "_pyfasm_pg_mouse_set_visible",
                "_pyfasm_pg_key_set_repeat", "_pyfasm_pg_transform_rotozoom",
                "_pyfasm_pg_event_post", "_pyfasm_pg_event_wait",
                "_pyfasm_pg_mouse_get_rel"):
        assert sym in asm, f"codegen emitted {sym}"
        assert f"{sym}:" in WIN64_PYGAME_RUNTIME_CODE, f"runtime missing {sym}"



BEHAVIOUR_APP = """
import pygame

def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((64, 48))
    surf = pygame.Surface((10, 8))
    surf.fill((0, 0, 0))
    surf.set_at((2, 3), (200, 100, 50))
    c = surf.get_at((2, 3))
    print(c[0], c[1], c[2], c[3])
    pygame.Surface.set_at(surf, (4, 1), (9, 8, 7))
    d = surf.get_at((4, 1))
    print(d[0], d[1], d[2])
    part = surf.subsurface(pygame.Rect(2, 1, 4, 3))
    print(part.get_width(), part.get_height())
    e = part.get_at((0, 2))
    print(e[0], e[1], e[2])
    r = pygame.transform.rotate(surf, 90)
    print(r.get_width(), r.get_height())
    z = pygame.transform.rotozoom(surf, 0, 2)
    print(z.get_width(), z.get_height())
    x2 = pygame.transform.scale2x(surf)
    print(x2.get_width(), x2.get_height())
    ev = pygame.event.Event(pygame.USEREVENT)
    print(ev.type)
    pygame.event.post(ev)
    n = 0
    for g in pygame.event.get():
        if g.type == pygame.USEREVENT:
            n += 1
    print(n)
    pygame.event.post(pygame.event.Event(pygame.USEREVENT))
    w = pygame.event.wait()
    print(w.type)
    pygame.quit()
    print("PYGAME_SHIM_OK")
    return 0
"""


def test_pygame_shim_behaviour_win64(tmp_path: Path):
    src = tmp_path / "pg_shim.py"
    exe = tmp_path / "pg_shim.exe"
    src.write_text(BEHAVIOUR_APP, encoding="utf-8")
    compiler = PyFasmCompiler()
    ok, out_exe, log = compiler.compile_file(str(src), output_binary=str(exe), target="win64")
    assert ok, f"Win64 FASM build failed:\n{log}"
    if sys.platform != "win32" and not (shutil.which("wine") or shutil.which("wine64")):
        pytest.skip("Running the Win64 binary requires Windows or Wine")
    res = subprocess.run([str(out_exe)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert res.returncode == 0, res.stderr
    lines = [line.strip() for line in res.stdout.strip().splitlines()]
    assert lines == [
        "200 100 50 255",
        "9 8 7",
        "4 3",
        "200 100 50",
        "8 10",
        "20 16",
        "20 16",
        "24",
        "1",
        "24",
        "PYGAME_SHIM_OK",
    ]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
