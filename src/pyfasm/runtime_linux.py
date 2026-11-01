"""
Native Linux x86-64 ELF64 Runtime for PyFASM.
Outputs standard Linux ELF64 executable using direct Linux kernel syscalls.
No libc, no external dependencies required.
"""
from __future__ import annotations


def get_linux_runtime_header() -> str:
    """Returns the FASM ELF64 executable header."""
    return """format ELF64 executable 3
entry _pyfasm_entry_point

segment readable executable
"""


def get_linux_runtime_data() -> str:
    """Returns Linux runtime data structures."""
    return """
segment readable writeable
    crlf_str        db 10, 0
    minus_str       db '-', 0
    dot_str         db '.', 0
    flt_1m          dq 1000000.0
    flt_zero        dq 0.0
    linux_time_sec  dq 0
    linux_time_nsec dq 0
"""


def get_linux_runtime_code() -> str:
    """Returns native Linux syscall routines (System V AMD64 ABI)."""
    return """
segment readable executable

_pyfasm_init_io:
    ret

_pyfasm_print_char:
    ; RCX = character code (in CL)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 16
    mov     byte [rsp], cl
    mov     rax, 1                  ; sys_write
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

    ; sys_write(stdout=1, buf=rsi, len=rdx)
    mov     rax, 1                  ; sys_write
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
    mov     rax, 1                  ; sys_write
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
    ; Length = (rsp + 32) - rdi
    lea     rdx, [rsp + 32]
    sub     rdx, rdi
    mov     rsi, rdi
    mov     rax, 1                  ; sys_write
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
    mov     rax, 1
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

    ; Print dot
    mov     byte [rsp], '.'
    mov     rax, 1
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
    ; RCX = bytes to allocate -> sys_mmap
    push    rbp
    mov     rbp, rsp
    mov     rsi, rcx                ; length
    xor     rdi, rdi                ; addr = 0
    mov     rdx, 3                  ; PROT_READ | PROT_WRITE
    mov     r10, 0x22               ; MAP_PRIVATE | MAP_ANONYMOUS
    mov     r8, -1                  ; fd = -1
    xor     r9, r9                  ; offset = 0
    mov     rax, 9                  ; sys_mmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_free_memory:
    ; RCX = ptr
    push    rbp
    mov     rbp, rsp
    mov     rdi, rcx
    mov     rsi, 4096               ; munmap default page
    mov     rax, 11                 ; sys_munmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_atomic_add:
    ; RCX = pointer to int64, RDX = value to add
    lock add qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_atomic_sub:
    ; RCX = pointer to int64, RDX = value to subtract
    lock sub qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_get_tick_count:
    ; High-resolution timestamp via RDTSC scaled to ms
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    ; Divide by typical 2.5 GHz (approx 2,500,000 cycles/ms)
    mov     rcx, 2500000
    xor     rdx, rdx
    div     rcx
    ret

_pyfasm_sleep_ms:
    ; RCX = milliseconds -> sys_nanosleep
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32

    ; sec = ms / 1000
    mov     rax, rcx
    xor     rdx, rdx
    mov     rbx, 1000
    div     rbx
    mov     [rsp], rax              ; tv_sec
    ; nsec = rem * 1000000
    imul    rdx, 1000000
    mov     [rsp + 8], rdx          ; tv_nsec

    mov     rdi, rsp
    xor     rsi, rsi
    mov     rax, 35                 ; sys_nanosleep
    syscall

    mov     rsp, rbp
    pop     rbp
    ret
"""
