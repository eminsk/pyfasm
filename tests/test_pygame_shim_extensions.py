"""Regression tests for the extended pygame shim: transform.rotozoom/scale2x,
Surface.get_at/set_at/subsurface and extra pygame.mixer call shapes."""

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
    pygame.quit()
    return 0
"""


def test_rotozoom_emits_transform_call():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_transform_scale" in asm


def test_scale2x_emits_transform_call():
    asm = compile_asm(APP)
    assert "call _pyfasm_pg_transform_scale" in asm
    assert "mov qword [rsp + 40], 2" in asm


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


def test_runtime_defines_all_emitted_symbols():
    from pyfasm.runtime_win64_pygame import WIN64_PYGAME_RUNTIME_CODE

    asm = compile_asm(APP)
    for sym in ("_pyfasm_pg_get_at", "_pyfasm_pg_set_at", "_pyfasm_pg_subsurface",
                "_pyfasm_pg_mouse_set_pos", "_pyfasm_pg_mouse_set_visible",
                "_pyfasm_pg_key_set_repeat"):
        assert sym in asm, f"codegen emitted {sym}"
        assert f"{sym}:" in WIN64_PYGAME_RUNTIME_CODE, f"runtime missing {sym}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
