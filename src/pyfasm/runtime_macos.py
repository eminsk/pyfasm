"""
Native Apple macOS x86-64 Mach-O Runtime for PyFASM.
Outputs standalone Mach-O 64-bit executable using direct Darwin BSD kernel syscalls.
No libc, no external dynamic linker required.
"""
from __future__ import annotations


def get_macos_runtime_header() -> str:
    """Returns the FASM Mach-O 64-bit executable header and load commands."""
    return """format binary as 'macho'
use64

mach_header:
    dd 0xFEEDFACF           ; magic: MH_MAGIC_64
    dd 0x01000007           ; cputype: CPU_TYPE_X86_64
    dd 0x80000003           ; cpusubtype: CPU_SUBTYPE_LIB64 | CPU_SUBTYPE_I386_ALL
    dd 0x00000002           ; filetype: MH_EXECUTE
    dd 2                    ; ncmds: 2 commands (LC_SEGMENT_64 + LC_UNIXTHREAD)
    dd sizeof_cmds          ; sizeofcmds
    dd 0x00200001           ; flags: MH_NOUNDEFS | MH_PIE
    dd 0                    ; reserved

commands_start:
lc_segment_text:
    dd 0x19                 ; cmd: LC_SEGMENT_64
    dd 72 + 80              ; cmdsize: 72 + 80
    db '__TEXT', 0,0,0,0,0,0,0,0,0,0 ; segname (16 bytes)
    dq 0x100000000          ; vmaddr
    dq 0x10000              ; vmsize (64KB)
    dq 0                    ; fileoff
    dq file_size            ; filesize
    dd 7                    ; maxprot: rwx
    dd 5                    ; initprot: r-x
    dd 1                    ; nsects: 1
    dd 0                    ; flags

sect_text:
    db '__text', 0,0,0,0,0,0,0,0,0,0 ; sectname (16 bytes)
    db '__TEXT', 0,0,0,0,0,0,0,0,0,0 ; segname (16 bytes)
    dq 0x100000000 + code_start ; addr
    dq code_size            ; size
    dd code_start           ; offset
    dd 4                    ; align (2^4 = 16)
    dd 0                    ; reloff
    dd 0                    ; nreloc
    dd 0x80000400           ; flags: S_REGULAR | S_ATTR_SOME_INSTRUCTIONS | S_ATTR_PURE_INSTRUCTIONS
    dd 0                    ; reserved1
    dd 0                    ; reserved2
    dd 0                    ; reserved3

lc_unixthread:
    dd 0x5                  ; cmd: LC_UNIXTHREAD
    dd 16 + 168             ; cmdsize: 184
    dd 4                    ; flavor: x86_THREAD_STATE64
    dd 42                   ; count: 42 (168 / 4 dwords)
    dq 0,0,0,0,0,0,0,0      ; rax, rbx, rcx, rdx, rdi, rsi, rbp, rsp
    dq 0,0,0,0,0,0,0,0      ; r8, r9, r10, r11, r12, r13, r14, r15
    dq 0x100000000 + _pyfasm_entry_point ; rip (Entry Point)
    dq 0                    ; rflags
    dq 0,0                  ; cs, fs, gs

sizeof_cmds = $ - commands_start

align 16
code_start = $
"""


def get_macos_runtime_data() -> str:
    """Returns macOS runtime data structures."""
    return """
align 8
    crlf_str        db 10, 0
    minus_str       db '-', 0
    dot_str         db '.', 0
    flt_1m          dq 1000000.0
    flt_zero        dq 0.0
"""


def get_macos_runtime_code() -> str:
    """Returns native Darwin BSD syscall routines."""
    return """
_pyfasm_init_io:
    ret

_pyfasm_print_char:
    ; RCX = character code (in CL)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 16
    mov     byte [rsp], cl
    mov     rax, 0x2000004          ; Darwin sys_write
    mov     rdi, 1                  ; stdout
    mov     rsi, rsp
    mov     rdx, 1
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_str:
    ; RCX = pointer to null-terminated string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi

    mov     rsi, rcx
    test    rsi, rsi
    jz      .done_print_str

    ; Calculate length
    xor     eax, eax
    mov     rdi, rsi
    mov     rcx, -1
    repne   scasb
    not     rcx
    dec     rcx
    mov     rdx, rcx                ; rdx = length

    test    rdx, rdx
    jz      .done_print_str

    ; Darwin sys_write(stdout=1, buf=rsi, len=rdx)
    mov     rax, 0x2000004          ; Darwin sys_write
    mov     rdi, 1                  ; stdout
    syscall

.done_print_str:
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_newline:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 16
    mov     byte [rsp], 10          ; LF newline
    mov     rax, 0x2000004          ; Darwin sys_write
    mov     rdi, 1                  ; stdout
    mov     rsi, rsp                ; buffer
    mov     rdx, 1                  ; length
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_len:
    ; RCX = pointer to string
    push    rdi
    mov     rdi, rcx
    xor     eax, eax
    mov     rcx, -1
    repne   scasb
    not     rcx
    dec     rcx
    mov     rax, rcx
    pop     rdi
    ret

_pyfasm_print_int:
    ; RCX = 64-bit integer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48

    mov     rax, rcx
    lea     rdi, [rsp + 32]
    mov     byte [rdi], 0           ; null terminator
    mov     rbx, 10
    mov     r8, 0                   ; sign flag

    test    rax, rax
    jns     .pos_int
    neg     rax
    mov     r8, 1

.pos_int:
.conv_loop:
    xor     rdx, rdx
    div     rbx
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    test    rax, rax
    jnz     .conv_loop

    test    r8, r8
    jz      .write_int
    dec     rdi
    mov     byte [rdi], '-'

.write_int:
    lea     rdx, [rsp + 32]
    sub     rdx, rdi
    mov     rsi, rdi
    mov     rax, 0x2000004          ; Darwin sys_write
    mov     rdi, 1                  ; stdout
    syscall

    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16

    xorps   xmm1, xmm1
    ucomisd xmm0, xmm1
    jae     .flt_pos
    ; Negative
    movsd   [rsp + 32], xmm0
    mov     byte [rsp], '-'
    mov     rax, 0x2000004
    mov     rdi, 1
    mov     rsi, rsp
    mov     rdx, 1
    syscall
    movsd   xmm0, [rsp + 32]
    xorps   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1

.flt_pos:
    movsd   [rsp + 32], xmm0
    cvttsd2si rax, xmm0
    mov     [rsp + 40], rax
    mov     rcx, rax
    call    _pyfasm_print_int

    ; Dot
    mov     byte [rsp], '.'
    mov     rax, 0x2000004
    mov     rdi, 1
    mov     rsi, rsp
    mov     rdx, 1
    syscall

    ; Fraction (6 decimals)
    movsd   xmm0, [rsp + 32]
    cvtsi2sd xmm2, [rsp + 40]
    subsd   xmm0, xmm2
    mulsd   xmm0, [flt_1m]
    cvttsd2si rax, xmm0
    mov     rcx, rax
    call    _pyfasm_print_int

    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_alloc_memory:
    ; RCX = bytes -> Darwin sys_mmap (0x20000C5)
    push    rbp
    mov     rbp, rsp
    mov     rsi, rcx                ; length
    xor     rdi, rdi                ; addr = 0
    mov     rdx, 3                  ; PROT_READ | PROT_WRITE
    mov     r10, 0x1002             ; MAP_PRIVATE | MAP_ANON
    mov     r8, -1                  ; fd = -1
    xor     r9, r9                  ; offset = 0
    mov     rax, 0x20000C5          ; Darwin sys_mmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_free_memory:
    ; RCX = ptr -> Darwin sys_munmap (0x2000049)
    push    rbp
    mov     rbp, rsp
    mov     rdi, rcx
    mov     rsi, 4096
    mov     rax, 0x2000049          ; Darwin sys_munmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_atomic_add:
    lock add qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_atomic_sub:
    lock sub qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_get_tick_count:
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     rcx, 2500000
    xor     rdx, rdx
    div     rcx
    ret

_pyfasm_sleep_ms:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    mov     rax, rcx
    xor     rdx, rdx
    mov     rbx, 1000
    div     rbx
    mov     [rsp], rax              ; tv_sec
    imul    rdx, 1000000
    mov     [rsp + 8], rdx          ; tv_nsec
    mov     rdi, rsp
    xor     rsi, rsi
    mov     rax, 0x20000EB          ; Darwin sys_nanosleep
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

code_size = $ - code_start
file_size = $
"""
