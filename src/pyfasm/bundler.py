"""
Project Bundler for PyFASM.
Packages complex Python applications into a native Windows x64 launcher executable
with smart virtual environment and No-GIL runtime detection.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple
from pyfasm.fasm_runner import FasmRunner


class ProjectBundler:
    """Builds a high-performance native launcher using FASM for complex Python projects."""

    def __init__(self, fasm_runner: Optional[FasmRunner] = None):
        self.fasm_runner = fasm_runner or FasmRunner()

    def generate_launcher_asm(
        self,
        entry_script: str,
        is_gui: bool = True,
        app_title: str = "PyFASM Application"
    ) -> str:
        """
        Generates clean FASM x64 assembly for a native process launcher.
        """
        subsystem = "GUI 5.0" if is_gui else "console 5.0"

        # Escape paths for assembly
        script_escaped = entry_script.replace("\\", "\\\\")
        proj_dir_path = Path(entry_script).parent
        proj_dir = str(proj_dir_path).replace("\\", "\\\\")

        # Locate venv python
        venv_scripts = proj_dir_path / ".venv" / "Scripts"
        venv_py = venv_scripts / ("pythonw.exe" if is_gui else "python.exe")
        if not venv_py.exists():
            venv_py = venv_scripts / "python.exe"
        venv_escaped = str(venv_py).replace("\\", "\\\\") if venv_py.exists() else ""

        # Locate uv executable
        uv_path = shutil.which("uv")
        if not uv_path:
            local_bin = Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
            if local_bin.exists():
                uv_path = str(local_bin)
            else:
                uv_path = "uv"
        uv_escaped = str(uv_path).replace("\\", "\\\\")

        # Check if project uses free-threaded Python build
        is_freethreaded = False
        pyver_file = proj_dir_path / ".python-version"
        if pyver_file.exists():
            try:
                content = pyver_file.read_text(encoding="utf-8").lower()
                if "freethreaded" in content or "t-windows" in content:
                    is_freethreaded = True
            except Exception:
                pass

        gil_arg = "-X gil=0 " if is_freethreaded else ""

        has_venv = bool(venv_escaped)

        return f"""; ============================================================
; PyFASM Native Project Bootstrapper & Launcher
; ============================================================
format PE64 {subsystem}
entry start

include 'win64a.inc'

section '.data' data readable writeable
    env_unbuf_name  db 'PYTHONUNBUFFERED', 0
    env_unbuf_val   db '1', 0

    work_dir        db '{proj_dir}', 0
    venv_cmd        db '"{venv_escaped}" "{script_escaped}"', 0
    uv_cmd          db '"{uv_escaped}" run --project "{proj_dir}" python {gil_arg}"{script_escaped}"', 0
    python_cmd      db 'python {gil_arg}"{script_escaped}"', 0

    startup_info    STARTUPINFO
    process_info    PROCESS_INFORMATION

section '.text' code readable executable

start:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 96
    and     rsp, -16

    ; Set PYTHONUNBUFFERED = 1
    lea     rcx, [env_unbuf_name]
    lea     rdx, [env_unbuf_val]
    call    [SetEnvironmentVariableA]

    ; Initialize startup_info using system defaults
    lea     rcx, [startup_info]
    call    [GetStartupInfoA]

    ; Try venv Python directly if available
    {'''
    xor     ecx, ecx
    lea     rdx, [venv_cmd]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0 ; bInheritHandles
    mov     qword [rsp + 40], 0 ; dwCreationFlags
    mov     qword [rsp + 48], 0 ; lpEnvironment
    lea     rax, [work_dir]
    mov     [rsp + 56], rax     ; lpCurrentDirectory
    lea     rax, [startup_info]
    mov     [rsp + 64], rax     ; lpStartupInfo
    lea     rax, [process_info]
    mov     [rsp + 72], rax     ; lpProcessInformation

    call    [CreateProcessA]
    test    rax, rax
    jnz     .wait_proc
    ''' if has_venv else ''}

    ; Try CreateProcess with uv run --project
    xor     ecx, ecx
    lea     rdx, [uv_cmd]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0 ; bInheritHandles
    mov     qword [rsp + 40], 0 ; dwCreationFlags
    mov     qword [rsp + 48], 0 ; lpEnvironment
    lea     rax, [work_dir]
    mov     [rsp + 56], rax     ; lpCurrentDirectory
    lea     rax, [startup_info]
    mov     [rsp + 64], rax     ; lpStartupInfo
    lea     rax, [process_info]
    mov     [rsp + 72], rax     ; lpProcessInformation

    call    [CreateProcessA]

    test    rax, rax
    jnz     .wait_proc

    ; Fallback: Try with standard python
    xor     ecx, ecx
    lea     rdx, [python_cmd]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    lea     rax, [work_dir]
    mov     [rsp + 56], rax
    lea     rax, [startup_info]
    mov     [rsp + 64], rax
    lea     rax, [process_info]
    mov     [rsp + 72], rax

    call    [CreateProcessA]

.wait_proc:
    test    rax, rax
    jz      .exit_err

    ; Wait for process to finish
    mov     rcx, [process_info.hProcess]
    mov     rdx, -1 ; INFINITE
    call    [WaitForSingleObject]

    mov     rcx, [process_info.hProcess]
    call    [CloseHandle]
    mov     rcx, [process_info.hThread]
    call    [CloseHandle]

    xor     ecx, ecx
    call    [ExitProcess]

.exit_err:
    mov     ecx, 1
    call    [ExitProcess]

section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL'

    import kernel32, \\
           SetEnvironmentVariableA, 'SetEnvironmentVariableA', \\
           GetStartupInfoA, 'GetStartupInfoA', \\
           CreateProcessA, 'CreateProcessA', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           ExitProcess, 'ExitProcess'
"""

    def bundle(
        self,
        project_dir: str,
        entry_script: Optional[str] = None,
        output_exe: Optional[str] = None,
        is_gui: bool = True
    ) -> Tuple[bool, str, str]:
        """
        Bundles a project into a standalone launcher executable.
        Returns (success: bool, output_binary_path: str, log_message: str).
        """
        proj_path = Path(project_dir).resolve()
        if not proj_path.exists():
            return False, "", f"Project directory not found: {project_dir}"

        # Detect entry script if not provided (main.py has highest priority)
        if not entry_script:
            candidates = [
                "main.py",
                "app.py",
                "app_core.py",
                "main_app.py",
                "application_startup.py",
            ]
            for cand in candidates:
                cand_file = proj_path / cand
                if cand_file.exists():
                    entry_script = str(cand_file)
                    break

        if not entry_script or not Path(entry_script).exists():
            return False, "", f"Could not determine entry script in {project_dir}"

        entry_path = Path(entry_script).resolve()
        if not output_exe:
            out_bin = proj_path / f"{proj_path.name}.exe"
        else:
            out_bin = Path(output_exe).resolve()

        asm_content = self.generate_launcher_asm(
            entry_script=str(entry_path),
            is_gui=is_gui,
            app_title=proj_path.name
        )

        asm_file = out_bin.with_suffix(".asm")
        success, log = self.fasm_runner.assemble(
            asm_content=asm_content,
            output_binary=str(out_bin),
            asm_file_path=str(asm_file),
            keep_asm=True
        )

        return success, str(out_bin), log
