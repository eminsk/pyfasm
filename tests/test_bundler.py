"""
Unit tests for PyFASM ProjectBundler.
"""
import os
import sys
import tempfile
import zipfile
from pathlib import Path
import pytest
from pyfasm.bundler import ProjectBundler


def test_generate_launcher_asm_win64():
    bundler = ProjectBundler()
    asm = bundler.generate_launcher_asm(
        entry_script="C:/fake/app/main.py",
        is_gui=False,
        app_title="TestApp",
        target="win64",
        onefile=True,
    )
    assert "format PE64 console 5.0" in asm
    assert "TestApp" in asm
    assert "run.bat" in asm


def test_generate_launcher_asm_win64_gui():
    bundler = ProjectBundler()
    asm = bundler.generate_launcher_asm(
        entry_script="C:/fake/app/main.py",
        is_gui=True,
        app_title="TestGuiApp",
        target="win64",
        onefile=True,
    )
    assert "format PE64 GUI 5.0" in asm
    assert "STARTF_USESHOWWINDOW" in asm
    assert "SW_HIDE" in asm
    assert "TestGuiApp" in asm


def test_generate_launcher_asm_linux():
    bundler = ProjectBundler()
    asm = bundler.generate_launcher_asm(
        entry_script="/home/user/app/main.py",
        is_gui=False,
        app_title="TestLinuxApp",
        target="linux",
        onefile=True,
    )
    assert "format ELF64 executable 3" in asm
    assert "TestLinuxApp" in asm
    assert "run.sh" in asm


def test_generate_launcher_asm_macos():
    bundler = ProjectBundler()
    asm = bundler.generate_launcher_asm(
        entry_script="/Users/user/app/main.py",
        is_gui=False,
        app_title="TestMacApp",
        target="macos",
        onefile=True,
    )
    assert "MH_MAGIC_64" in asm
    assert "TestMacApp" in asm


def test_bundle_minimal_project(tmp_path):
    proj_dir = tmp_path / "my_test_app"
    proj_dir.mkdir()
    main_file = proj_dir / "main.py"
    main_file.write_text("print('Bundler Test Success!')\n", encoding="utf-8")

    if sys.platform.startswith("linux"):
        target, ext = "linux", ".elf"
    elif sys.platform == "darwin":
        target, ext = "macos", ".macho"
    else:
        target, ext = "win64", ".exe"

    bundler = ProjectBundler()
    out_bin = tmp_path / f"my_test_app{ext}"
    success, out_path, log = bundler.bundle(
        project_dir=str(proj_dir),
        entry_script=str(main_file),
        output_exe=str(out_bin),
        is_gui=False,
        target=target,
        onefile=True,
    )
    assert success is True, f"Bundler failed for {target}:\n{log}"
    assert Path(out_path).exists()
    assert Path(out_path).stat().st_size > 0


def test_bundle_cross_platform_win64(tmp_path):
    proj_dir = tmp_path / "my_cross_win_app"
    proj_dir.mkdir()
    main_file = proj_dir / "main.py"
    main_file.write_text("print('Bundler Cross Win64 Success!')\n", encoding="utf-8")

    bundler = ProjectBundler()
    out_exe = tmp_path / "my_cross_win_app.exe"
    success, out_path, log = bundler.bundle(
        project_dir=str(proj_dir),
        entry_script=str(main_file),
        output_exe=str(out_exe),
        is_gui=False,
        target="win64",
        onefile=True,
    )
    assert success is True, f"Cross-compilation for win64 failed:\n{log}"
    assert Path(out_path).exists()
    assert Path(out_path).stat().st_size > 0


def test_bundle_runner_portability(tmp_path):
    """Verify run.bat and run.sh have zero hardcoded developer machine paths."""
    proj_dir = tmp_path / "my_portable_app"
    proj_dir.mkdir()
    # Mock a fake developer .venv to ensure bundler doesn't leak its path
    venv_dir = proj_dir / ".venv" / "Scripts"
    venv_dir.mkdir(parents=True)
    (venv_dir / "python.exe").write_text("", encoding="utf-8")

    main_file = proj_dir / "main.py"
    main_file.write_text("print('Portable!')\n", encoding="utf-8")

    bundler = ProjectBundler()
    out_exe = tmp_path / "my_portable_app.exe"
    success, out_path, log = bundler.bundle(
        project_dir=str(proj_dir),
        entry_script=str(main_file),
        output_exe=str(out_exe),
        is_gui=False,
        target="win64",
        onefile=True,
    )
    assert success is True

    # Check payload archive directly in the bundled binary
    with zipfile.ZipFile(str(out_path), "r") as zf:
        run_bat = zf.read("run.bat").decode("utf-8")
        run_sh = zf.read("run.sh").decode("utf-8")

        # Must not contain absolute project directory or developer machine path
        assert str(proj_dir) not in run_bat
        assert str(proj_dir) not in run_sh
        assert "C:\\proekts" not in run_bat
        assert "/proekts" not in run_sh

        # Must use relative or standard portable paths
        assert "%~dp0" in run_bat
        assert "$DIR" in run_sh
