"""
Project Bundler for PyFASM.
Packages complex Python applications (including CustomTkinter, requests, yt-dlp)
into a native Windows x64 launcher executable with free-threading and disabled GIL.
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
        Generates clean FASM x64 assembly for a native process launcher
        that sets PYTHON_GIL=0 and runs the entry point seamlessly.
        """
        subsystem = "GUI 5.0" if is_gui else "console 5.0"

        # Escape entry_script for assembly
        script_escaped = entry_script.replace("\\", "\\\\")

        return f"""; ============================================================
; PyFASM Native Project Bootstrapper & Free-Threaded Launcher
; ============================================================
format PE64 {subsystem}
entry start

include 'win64a.inc'

section '.data' data readable writeable
    env_gil_name    db 'PYTHON_GIL', 0
    env_gil_val     db '0', 0
    env_unbuf_name  db 'PYTHONUNBUFFERED', 0
    env_unbuf_val   db '1', 0

    uv_cmd          db 'uv run python -X gil=0 "{script_escaped}"', 0
    python_cmd      db 'python -X gil=0 "{script_escaped}"', 0

    startup_info    STARTUPINFO
    process_info    PROCESS_INFORMATION

section '.text' code readable executable

start:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16

    ; Set PYTHON_GIL = 0 (Free-threading / No GIL)
    lea     rcx, [env_gil_name]
    lea     rdx, [env_gil_val]
    call    [SetEnvironmentVariableA]

    ; Set PYTHONUNBUFFERED = 1
    lea     rcx, [env_unbuf_name]
    lea     rdx, [env_unbuf_val]
    call    [SetEnvironmentVariableA]

    ; Zero startup_info
    lea     rdi, [startup_info]
    mov     rcx, sizeof.STARTUPINFO
    xor     al, al
    rep     stosb
    mov     [startup_info.cb], sizeof.STARTUPINFO

    ; Hide console window if GUI
    mov     [startup_info.dwFlags], 1 ; STARTF_USESHOWWINDOW
    mov     [startup_info.wShowWindow], {'0' if is_gui else '1'} ; SW_HIDE or SW_SHOWNORMAL

    ; Try CreateProcess with uv run python
    xor     ecx, ecx
    lea     rdx, [uv_cmd]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0 ; bInheritHandles
    mov     qword [rsp + 40], {'08000000h' if is_gui else '0'} ; CREATE_NO_WINDOW
    mov     qword [rsp + 48], 0 ; lpEnvironment
    mov     qword [rsp + 56], 0 ; lpCurrentDirectory
    lea     rax, [startup_info]
    mov     [rsp + 64], rax
    lea     rax, [process_info]
    mov     [rsp + 72], rax

    sub     rsp, 32
    call    [CreateProcessA]
    add     rsp, 32

    test    rax, rax
    jnz     .wait_proc

    ; Fallback: Try with standard python
    xor     ecx, ecx
    lea     rdx, [python_cmd]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], {'08000000h' if is_gui else '0'}
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    lea     rax, [startup_info]
    mov     [rsp + 64], rax
    lea     rax, [process_info]
    mov     [rsp + 72], rax

    sub     rsp, 32
    call    [CreateProcessA]
    add     rsp, 32

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

        # Detect entry script if not provided
        if not entry_script:
            candidates = [
                "application_startup.py",
                "app_core.py",
                "main.py",
                "app.py",
                "main_app.py",
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
