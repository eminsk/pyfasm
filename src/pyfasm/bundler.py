"""
Project Bundler for PyFASM.
Packages complex Python applications into native standalone launcher executables
for Windows (PE64), Linux (ELF64), and Apple macOS (Mach-O 64) with smart virtual
environment and No-GIL runtime detection.
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
    """Builds high-performance native launchers using FASM for complex Python projects across Windows, Linux, and macOS."""

    def __init__(self, fasm_runner: Optional[FasmRunner] = None):
        self.fasm_runner = fasm_runner or FasmRunner()

    def generate_launcher_asm(
        self,
        entry_script: str,
        is_gui: bool = True,
        app_title: str = "PyFASM Application",
        target: str = "win64",
    ) -> str:
        """
        Generates clean FASM x64 assembly for a native process launcher across target platforms.
        Supported targets: 'win64', 'linux', 'macos' / 'apple'.
        """
        target_norm = target.lower()
        proj_dir_path = Path(entry_script).parent
        script_posix = str(entry_script).replace("\\", "/")
        proj_dir_posix = str(proj_dir_path).replace("\\", "/")

        # Check if project uses free-threaded Python build
        is_freethreaded = False
        pyver_file = proj_dir_path / ".python-version"
        if pyver_file.exists():
            try:
                content = pyver_file.read_text(encoding="utf-8").lower()
                if "freethreaded" in content or "t-windows" in content or "t-linux" in content:
                    is_freethreaded = True
            except Exception:
                pass

        gil_arg = "-X gil=0 " if is_freethreaded else ""

        # Linux ELF64 Launcher
        if target_norm == "linux":
            return f"""; ============================================================
; PyFASM Native Project Launcher (Linux ELF64 Syscall Engine)
; ============================================================
format ELF64 executable 3
entry start

segment readable writeable
    work_dir        db '{proj_dir_posix}', 0
    py_path         db '/usr/bin/env', 0
    py_arg0         db 'python3', 0
    py_arg1         db '{script_posix}', 0
    align 8
    argv            dq py_arg0, py_arg1, 0
    env_unbuf       db 'PYTHONUNBUFFERED=1', 0
    align 8
    envp            dq env_unbuf, 0

segment readable executable
start:
    ; sys_chdir (rax=80, rdi=work_dir)
    mov     rax, 80
    lea     rdi, [work_dir]
    syscall

    ; sys_execve (rax=59, rdi=py_path, rsi=argv, rdx=envp)
    mov     rax, 59
    lea     rdi, [py_path]
    lea     rsi, [argv]
    lea     rdx, [envp]
    syscall

    ; Fallback: exit(1) if execve fails
    mov     rax, 60
    mov     rdi, 1
    syscall
"""

        # Apple macOS Mach-O 64 Launcher
        if target_norm in ("macos", "apple"):
            return f"""; ============================================================
; PyFASM Native Project Launcher (Apple macOS Mach-O 64 Engine)
; ============================================================
format binary as 'macho'
use64

mach_header:
    dd 0xFEEDFACF           ; magic: MH_MAGIC_64
    dd 0x01000007           ; cputype: CPU_TYPE_X86_64
    dd 0x80000003           ; cpusubtype
    dd 0x00000002           ; filetype: MH_EXECUTE
    dd 2                    ; ncmds
    dd sizeof_cmds          ; sizeofcmds
    dd 0x00200001           ; flags: MH_NOUNDEFS | MH_PIE
    dd 0                    ; reserved

commands_start:
lc_segment_text:
    dd 0x19                 ; cmd: LC_SEGMENT_64
    dd 72 + 80              ; cmdsize
    db '__TEXT', 0,0,0,0,0,0,0,0,0,0 ; segname
    dq 0x100000000          ; vmaddr
    dq 0x10000              ; vmsize
    dq 0                    ; fileoff
    dq file_size            ; filesize
    dd 7                    ; maxprot
    dd 5                    ; initprot
    dd 1                    ; nsects
    dd 0                    ; flags

sect_text:
    db '__text', 0,0,0,0,0,0,0,0,0,0 ; sectname
    db '__TEXT', 0,0,0,0,0,0,0,0,0,0 ; segname
    dq 0x100000000 + code_start ; addr
    dq code_size            ; size
    dd code_start           ; offset
    dd 4                    ; align
    dd 0                    ; reloff
    dd 0                    ; nreloc
    dd 0x80000400           ; flags
    dd 0                    ; reserved1
    dd 0                    ; reserved2
    dd 0                    ; reserved3

lc_unixthread:
    dd 0x5                  ; cmd: LC_UNIXTHREAD
    dd 16 + 168             ; cmdsize
    dd 4                    ; flavor: x86_THREAD_STATE64
    dd 42                   ; count
    dq 0,0,0,0,0,0,0,0      ; registers
    dq 0,0,0,0,0,0,0,0
    dq 0x100000000 + start  ; rip
    dq 0                    ; rflags

sizeof_cmds = $ - commands_start

align 16
code_start = $ - mach_header

work_dir        db '{proj_dir_posix}', 0
py_path         db '/usr/bin/env', 0
py_arg0         db 'python3', 0
py_arg1         db '{script_posix}', 0
align 8
argv            dq py_arg0, py_arg1, 0
env_unbuf       db 'PYTHONUNBUFFERED=1', 0
align 8
envp            dq env_unbuf, 0

start:
    ; sys_chdir (rax=0x200000C, rdi=work_dir)
    mov     rax, 0x200000C
    lea     rdi, [work_dir]
    syscall

    ; sys_execve (rax=0x200003B, rdi=py_path, rsi=argv, rdx=envp)
    mov     rax, 0x200003B
    lea     rdi, [py_path]
    lea     rsi, [argv]
    lea     rdx, [envp]
    syscall

    ; sys_exit (rax=0x2000001, rdi=1)
    mov     rax, 0x2000001
    mov     rdi, 1
    syscall

code_size = $ - code_start
file_size = $ - mach_header
"""

        # Windows PE64 Launcher (Default)
        subsystem = "GUI 5.0" if is_gui else "console 5.0"
        script_escaped = entry_script.replace("\\", "\\\\")
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

        has_venv = bool(venv_escaped)

        return f"""; ============================================================
; PyFASM Native Project Bootstrapper & Launcher (Windows PE64)
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
        is_gui: bool = True,
        target: str = "win64",
    ) -> Tuple[bool, str, str]:
        """
        Bundles a project into a standalone launcher executable for the specified target.
        Supported targets: 'win64', 'linux', 'macos' / 'apple'.
        Returns (success: bool, output_binary_path: str, log_message: str).
        """
        proj_path = Path(project_dir).resolve()
        if not proj_path.exists():
            return False, "", f"Project directory not found: {project_dir}"

        # Detect entry script if not provided
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

        # Determine target and output extension
        target_norm = target.lower()
        if not output_exe:
            if target_norm == "linux":
                ext = ".elf"
            elif target_norm in ("macos", "apple"):
                ext = ".macho"
            else:
                ext = ".exe"
            out_bin = proj_path / f"{proj_path.name}{ext}"
        else:
            out_bin = Path(output_exe).resolve()
            if out_bin.suffix.lower() == ".elf":
                target_norm = "linux"
            elif out_bin.suffix.lower() == ".macho":
                target_norm = "macos"

        asm_content = self.generate_launcher_asm(
            entry_script=str(entry_path),
            is_gui=is_gui,
            app_title=proj_path.name,
            target=target_norm,
        )

        asm_file = out_bin.with_suffix(".asm")
        success, log = self.fasm_runner.assemble(
            asm_content=asm_content,
            output_binary=str(out_bin),
            asm_file_path=str(asm_file),
            keep_asm=True
        )

        if success and os.path.exists(out_bin):
            try:
                os.chmod(out_bin, 0o755)
            except Exception:
                pass
            if sys.platform == 'darwin':
                try:
                    import subprocess
                    subprocess.run(['codesign', '-s', '-', '-f', str(out_bin)], capture_output=True)
                except Exception:
                    pass

        return success, str(out_bin), log
