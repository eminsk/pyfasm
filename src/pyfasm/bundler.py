"""
Project Bundler for PyFASM.
Packages complex Python applications, media tools (ffmpeg, mpv), and libraries
into a single monolithic standalone executable across Windows (PE64), Linux (ELF64),
and Apple macOS (Mach-O 64).
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional, Tuple, List
from pyfasm.fasm_runner import FasmRunner


class ProjectBundler:
    """Builds high-performance native monolithic launchers using FASM across Windows, Linux, and macOS."""

    def __init__(self, fasm_runner: Optional[FasmRunner] = None):
        self.fasm_runner = fasm_runner or FasmRunner()

    def generate_launcher_asm(
        self,
        entry_script: str,
        is_gui: bool = False,
        app_title: str = "PyFASM Application",
        target: str = "win64",
        onefile: bool = True,
    ) -> str:
        """
        Generates FASM x64 assembly for a monolithic single-file or directory launcher.
        Supported targets: 'win64', 'linux', 'macos' / 'apple'.
        """
        target_norm = target.lower()
        proj_dir_path = Path(entry_script).parent
        script_posix = str(entry_script).replace("\\", "/")
        proj_dir_posix = str(proj_dir_path).replace("\\", "/")
        entry_rel = Path(entry_script).name
        app_name_safe = "".join(c if c.isalnum() else "_" for c in app_title)

        # Check if project uses free-threaded (No-GIL) Python build
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

        # ---------------------------------------------------------------------
        # Linux ELF64 Launcher
        # ---------------------------------------------------------------------
        if target_norm == "linux":
            if onefile:
                sh_cmd = (
                    f'APP_DIR="$HOME/.cache/pyfasm/{app_name_safe}"; '
                    f'if [ ! -f "$APP_DIR/.stamp" ]; then '
                    f'mkdir -p "$APP_DIR" && tar -xf "$0" -C "$APP_DIR" 2>/dev/null && touch "$APP_DIR/.stamp"; fi; '
                    f'export PATH="$APP_DIR:$PATH"; cd "$APP_DIR"; exec python3 {gil_arg}"{entry_rel}"'
                )
            else:
                sh_cmd = f'cd "{proj_dir_posix}"; exec python3 {gil_arg}"{script_posix}"'

            return f"""; ============================================================
; PyFASM Native Monolithic Project Launcher (Linux ELF64)
; ============================================================
format ELF64 executable 3
entry start

segment readable writeable
    sh_path         db '/bin/sh', 0
    sh_arg0         db 'sh', 0
    sh_arg1         db '-c', 0
    sh_cmd          db '{sh_cmd}', 0
    align 8
    argv            dq sh_arg0, sh_arg1, sh_cmd, 0
    env_unbuf       db 'PYTHONUNBUFFERED=1', 0
    align 8
    envp            dq env_unbuf, 0

segment readable executable
start:
    ; sys_execve (rax=59, rdi=sh_path, rsi=argv, rdx=envp)
    mov     rax, 59
    lea     rdi, [sh_path]
    lea     rsi, [argv]
    lea     rdx, [envp]
    syscall

    ; Fallback: exit(1)
    mov     rax, 60
    mov     rdi, 1
    syscall
"""

        # ---------------------------------------------------------------------
        # Apple macOS Mach-O 64 Launcher
        # ---------------------------------------------------------------------
        if target_norm in ("macos", "apple"):
            if onefile:
                sh_cmd = (
                    f'APP_DIR="$HOME/Library/Caches/pyfasm/{app_name_safe}"; '
                    f'if [ ! -f "$APP_DIR/.stamp" ]; then '
                    f'mkdir -p "$APP_DIR" && tar -xf "$0" -C "$APP_DIR" 2>/dev/null && touch "$APP_DIR/.stamp"; fi; '
                    f'export PATH="$APP_DIR:$PATH"; cd "$APP_DIR"; exec python3 {gil_arg}"{entry_rel}"'
                )
            else:
                sh_cmd = f'cd "{proj_dir_posix}"; exec python3 {gil_arg}"{script_posix}"'

            return f"""; ============================================================
; PyFASM Native Monolithic Project Launcher (Apple macOS Mach-O 64)
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
    db '__TEXT', 0,0,0,0,0,0,0,0,0,0
    dq 0x100000000
    dq 0x10000
    dq 0
    dq file_size
    dd 7
    dd 5
    dd 1
    dd 0

sect_text:
    db '__text', 0,0,0,0,0,0,0,0,0,0
    db '__TEXT', 0,0,0,0,0,0,0,0,0,0
    dq 0x100000000 + code_start
    dq code_size
    dd code_start
    dd 4
    dd 0
    dd 0
    dd 0x80000400
    dd 0
    dd 0
    dd 0

lc_unixthread:
    dd 0x5                  ; cmd: LC_UNIXTHREAD
    dd 16 + 168             ; cmdsize
    dd 4                    ; flavor: x86_THREAD_STATE64
    dd 42                   ; count
    dq 0,0,0,0,0,0,0,0
    dq 0,0,0,0,0,0,0,0
    dq 0x100000000 + start
    dq 0

sizeof_cmds = $ - commands_start

align 16
code_start = $ - mach_header

sh_path         db '/bin/sh', 0
sh_arg0         db 'sh', 0
sh_arg1         db '-c', 0
sh_cmd          db '{sh_cmd}', 0
align 8
argv            dq sh_arg0, sh_arg1, sh_cmd, 0
env_unbuf       db 'PYTHONUNBUFFERED=1', 0
align 8
envp            dq env_unbuf, 0

start:
    ; Darwin sys_execve (rax=0x200003B)
    mov     rax, 0x200003B
    lea     rdi, [sh_path]
    lea     rsi, [argv]
    lea     rdx, [envp]
    syscall

    ; Fallback sys_exit(1)
    mov     rax, 0x2000001
    mov     rdi, 1
    syscall

code_size = $ - code_start
file_size = $ - mach_header
"""

        # ---------------------------------------------------------------------
        # Windows PE64 Monolithic Launcher (Default)
        # ---------------------------------------------------------------------
        subsystem = "GUI 5.0" if is_gui else "console 5.0"

        if onefile:
            return f"""; ============================================================
; PyFASM Native Monolithic Single-File Launcher (Windows PE64)
; ============================================================
format PE64 {subsystem}
entry start

include 'win64a.inc'

section '.data' data readable writeable
    env_unbuf_name  db 'PYTHONUNBUFFERED', 0
    env_unbuf_val   db '1', 0

    cmd_prefix      db 'cmd.exe /c if not exist "%LOCALAPPDATA%\\pyfasm\\apps\\{app_name_safe}\\.stamp" (mkdir "%LOCALAPPDATA%\\pyfasm\\apps\\{app_name_safe}" & tar -xf "', 0
    cmd_mid         db '" -C "%LOCALAPPDATA%\\pyfasm\\apps\\{app_name_safe}" & echo 1 > "%LOCALAPPDATA%\\pyfasm\\apps\\{app_name_safe}\\.stamp") & set "PATH=%LOCALAPPDATA%\\pyfasm\\apps\\{app_name_safe};%PATH%" & cd /d "%LOCALAPPDATA%\\pyfasm\\apps\\{app_name_safe}" & python {gil_arg}"{entry_rel}"', 0

    sz_self_exe     rb 1024
    sz_full_cmd     rb 4096

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

    ; Get path to own executable
    xor     ecx, ecx
    lea     rdx, [sz_self_exe]
    mov     r8d, 1024
    call    [GetModuleFileNameA]

    ; Build full command line: cmd_prefix + sz_self_exe + cmd_mid
    lea     rdi, [sz_full_cmd]
    lea     rsi, [cmd_prefix]
.copy_prefix:
    lodsb
    test    al, al
    jz      .done_prefix
    stosb
    jmp     .copy_prefix
.done_prefix:

    lea     rsi, [sz_self_exe]
.copy_exe:
    lodsb
    test    al, al
    jz      .done_exe
    stosb
    jmp     .copy_exe
.done_exe:

    lea     rsi, [cmd_mid]
.copy_mid:
    lodsb
    stosb
    test    al, al
    jnz     .copy_mid

    ; Initialize startup_info
    lea     rcx, [startup_info]
    call    [GetStartupInfoA]

    ; Launch command
    xor     ecx, ecx
    lea     rdx, [sz_full_cmd]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0 ; bInheritHandles
    mov     qword [rsp + 40], 0 ; dwCreationFlags
    mov     qword [rsp + 48], 0 ; lpEnvironment
    mov     qword [rsp + 56], 0 ; lpCurrentDirectory
    lea     rax, [startup_info]
    mov     [rsp + 64], rax     ; lpStartupInfo
    lea     rax, [process_info]
    mov     [rsp + 72], rax     ; lpProcessInformation

    call    [CreateProcessA]
    test    rax, rax
    jz      .exit_err

    ; Wait for process to finish
    mov     rcx, [process_info.hProcess]
    mov     rdx, -1             ; INFINITE
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
           GetModuleFileNameA, 'GetModuleFileNameA', \\
           GetStartupInfoA, 'GetStartupInfoA', \\
           CreateProcessA, 'CreateProcessA', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           ExitProcess, 'ExitProcess'
"""
        else:
            # Directory wrapper mode
            script_escaped = entry_script.replace("\\", "\\\\")
            proj_dir = str(proj_dir_path).replace("\\", "\\\\")
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
    python_cmd      db 'python {gil_arg}"{script_escaped}"', 0

    startup_info    STARTUPINFO
    process_info    PROCESS_INFORMATION

section '.text' code readable executable

start:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 96
    and     rsp, -16

    lea     rcx, [env_unbuf_name]
    lea     rdx, [env_unbuf_val]
    call    [SetEnvironmentVariableA]

    lea     rcx, [startup_info]
    call    [GetStartupInfoA]

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
    test    rax, rax
    jz      .exit_err

    mov     rcx, [process_info.hProcess]
    mov     rdx, -1
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
        is_gui: bool = False,
        target: str = "win64",
        onefile: bool = True,
        include_bins: Optional[List[str]] = None,
    ) -> Tuple[bool, str, str]:
        """
        Bundles a project, its dependencies, and tools (ffmpeg, mpv) into a single monolithic standalone executable.
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
                "application_startup.py",
                "app_core.py",
                "app.py",
                "bot.py",
                "run.py",
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

        # Generate Launcher Assembly
        asm_content = self.generate_launcher_asm(
            entry_script=str(entry_path),
            is_gui=is_gui,
            app_title=proj_path.name,
            target=target_norm,
            onefile=onefile,
        )

        asm_file = out_bin.with_suffix(".asm")
        success, log = self.fasm_runner.assemble(
            asm_content=asm_content,
            output_binary=str(out_bin),
            asm_file_path=str(asm_file),
            keep_asm=True
        )

        if not success or not out_bin.exists():
            return False, "", log

        # If onefile: package project files, tools (ffmpeg, mpv), and configs into appended payload
        if onefile:
            payload_path = out_bin.with_suffix(".zip")
            with zipfile.ZipFile(payload_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. Add all .py files and configs
                skip_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".vscode"}
                skip_exts = {".mp4", ".mkv", ".avi", ".webm", ".ts", ".iso", ".zip", ".tar", ".gz", ".log", ".tmp"}

                # Gather files
                for root, dirs, files in os.walk(proj_path):
                    dirs[:] = [d for d in dirs if d not in skip_dirs]
                    for f in files:
                        p = Path(root) / f
                        if p.suffix.lower() in skip_exts:
                            continue
                        # Skip huge json info dumps if any
                        if f.endswith(".info.json") and p.stat().st_size > 500_000:
                            continue
                        # Skip own output binary
                        if p.resolve() == out_bin.resolve() or p.resolve() == payload_path.resolve():
                            continue
                        rel_path = p.relative_to(proj_path)
                        zf.write(p, arcname=str(rel_path))

                # 2. Add explicitly requested or discovered binary tools (e.g. ffmpeg.exe, mpv-2.dll)
                if include_bins:
                    for b_path in include_bins:
                        bp = Path(b_path).resolve()
                        if bp.exists():
                            zf.write(bp, arcname=bp.name)

            # Append zip payload directly to the executable
            payload_data = payload_path.read_bytes()
            with open(out_bin, "ab") as f_out:
                f_out.write(payload_data)

            # Clean up intermediate zip
            try:
                payload_path.unlink()
            except Exception:
                pass

        # Set permissions and code sign
        try:
            os.chmod(out_bin, 0o755)
        except Exception:
            pass

        if sys.platform == "darwin":
            try:
                subprocess.run(["codesign", "-s", "-", "-f", str(out_bin)], capture_output=True)
            except Exception:
                pass

        return True, str(out_bin), log
