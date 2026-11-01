"""
Native MyOS 10 x64 Runtime for PyFASM.
Outputs flat binary or ELF64 compatible with MyOS kernel execution.
"""
from __future__ import annotations


def get_myos_runtime_header() -> str:
    """Returns the FASM header for MyOS binary."""
    return """format binary as 'bin'
use64
org 0x1000000   ; Default MyOS userspace program base
jmp _pyfasm_entry_point
"""


def get_myos_runtime_data() -> str:
    return """
align 8
crlf_str        db 13, 10, 0
minus_str       db '-', 0
"""


def get_myos_runtime_code() -> str:
    """Returns native MyOS routines: Serial port I/O & VGA framebuffer output."""
    return """
_pyfasm_init_io:
    ; COM1 Serial Port Init (0x3F8) for debugging in QEMU / MyOS
    mov     dx, 03F9h
    xor     al, al
    out     dx, al
    mov     dx, 03FBh
    mov     al, 80h
    out     dx, al
    mov     dx, 03F8h
    mov     al, 03h
    out     dx, al
    mov     dx, 03F9h
    xor     al, al
    out     dx, al
    mov     dx, 03FBh
    mov     al, 03h
    out     dx, al
    ret

_pyfasm_print_char:
    ; AL = character
    mov     ah, al
    mov     dx, 03FDh
.wait_tx:
    in      al, dx
    test    al, 20h
    jz      .wait_tx
    mov     dx, 03F8h
    mov     al, ah
    out     dx, al
    ret

_pyfasm_print_str:
    ; RSI or RDI/RCX = pointer to string
    push    rsi
    mov     rsi, rcx
.loop_str:
    lodsb
    test    al, al
    jz      .done_str
    call    _pyfasm_print_char
    jmp     .loop_str
.done_str:
    pop     rsi
    ret

_pyfasm_print_newline:
    push    rax
    mov     al, 13
    call    _pyfasm_print_char
    mov     al, 10
    call    _pyfasm_print_char
    pop     rax
    ret

_pyfasm_print_int:
    ; RCX = signed integer
    push    rbx
    push    rdx
    push    rdi
    sub     rsp, 32
    mov     rax, rcx
    test    rax, rax
    jns     .pos
    push    rax
    mov     al, '-'
    call    _pyfasm_print_char
    pop     rax
    neg     rax
.pos:
    lea     rdi, [rsp + 24]
    mov     byte [rdi], 0
    mov     rbx, 10
.digits:
    xor     rdx, rdx
    div     rbx
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    test    rax, rax
    jnz     .digits

    mov     rcx, rdi
    call    _pyfasm_print_str
    add     rsp, 32
    pop     rdi
    pop     rdx
    pop     rbx
    ret

_pyfasm_get_tick_count:
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    ret

_pyfasm_sleep_ms:
    ; Simple delay loop using TSC
    push    rcx
    push    rbx
    mov     rbx, rcx
    imul    rbx, 2000000 ; Approx cycles per ms
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    add     rbx, rax
.spin:
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    cmp     rax, rbx
    jb      .spin
    pop     rbx
    pop     rcx
    ret

_pyfasm_atomic_add:
    lock add qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_atomic_sub:
    lock sub qword [rcx], rdx
    mov     rax, [rcx]
    ret
"""
