format PE64 console 5.0
entry _pyfasm_entry_point

include 'win64a.inc'


section '.data' data readable writeable
    hStdOut         dq 0
    hStdIn          dq 0
    bytesWritten    dq 0
    bytesRead       dq 0
    crlf_str        db 13, 10, 0
    minus_str       db '-', 0
    dot_str         db '.', 0
    flt_1m          dq 1000000.0
    flt_zero        dq 0.0

    _str_lit_1 db 67, 111, 109, 112, 117, 116, 105, 110, 103, 32, 70, 105, 98, 111, 110, 97, 99, 99, 105, 32, 115, 101, 113, 117, 101, 110, 99, 101, 32, 117, 112, 32, 116, 111, 32, 78, 32, 61, 32, 52, 48, 32, 105, 110, 32, 110, 97, 116, 105, 118, 101, 32, 120, 54, 52, 46, 46, 46, 10, 0
    _str_lit_2 db 70, 105, 98, 40, 52, 48, 41, 32, 61, 32, 0
    _str_lit_3 db 69, 108, 97, 112, 115, 101, 100, 32, 116, 105, 109, 101, 32, 40, 109, 115, 41, 58, 32, 0

section '.text' code readable executable

_pyfasm_entry_point:
    push rbp
    mov rbp, rsp
    sub rsp, 32                      ; shadow/local frame
    and rsp, -16                     ; 16-byte stack alignment
    call _pyfasm_init_io             ; initialize runtime I/O
    call main                        ; execute user main()
    mov ecx, eax                     ; exit code in ecx (Windows)
    mov edi, eax                     ; exit code in edi (Linux/macOS)
    call [ExitProcess]

; ============================================================
; Function: fib
; ============================================================
fib:
_02_fibonacci_fib:
    push rbp
    mov rbp, rsp
    sub rsp, 80                      ; frame + shadow space
    mov [rbp - 8], rcx               ; arg n
    mov rax, [rbp - 8]               ; load n
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    cmp rax, r11
    setle al
    movzx rax, al
    test rax, rax
    jz ._if_else_1
    mov rax, [rbp - 8]               ; load n
    jmp .epilog_fib
    jmp ._if_end_2
._if_else_1:
._if_end_2:
    mov rax, 0
    mov [rbp - 16], rax              ; assign a
    mov rax, 1
    mov [rbp - 24], rax              ; assign b
    mov rax, 2
    mov [rbp - 32], rax              ; init for i
._for_start_3:
    mov rax, [rbp - 32]
    push rax
    mov rax, [rbp - 8]               ; load n
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    add rax, r11
    mov r11, rax
    pop rax
    cmp rax, r11
    jge ._for_end_5
    mov rax, [rbp - 16]              ; load a
    push rax
    mov rax, [rbp - 24]              ; load b
    mov r11, rax
    pop rax
    add rax, r11
    mov [rbp - 40], rax              ; assign c
    mov rax, [rbp - 24]              ; load b
    mov [rbp - 16], rax              ; assign a
    mov rax, [rbp - 40]              ; load c
    mov [rbp - 24], rax              ; assign b
._for_step_4:
    inc qword [rbp - 32]
    jmp ._for_start_3
._for_end_5:
    mov rax, [rbp - 24]              ; load b
    jmp .epilog_fib
.epilog_fib:
    mov rsp, rbp
    pop rbp
    ret

; ============================================================
; Function: main
; ============================================================
main:
_02_fibonacci_main:
    push rbp
    mov rbp, rsp
    sub rsp, 64                      ; frame + shadow space
    lea rax, [_str_lit_1]
    mov rcx, rax
    call _pyfasm_print_str
    call _pyfasm_get_tick_count
    mov [rbp - 8], rax               ; assign t0
    mov rax, 40
    push rax
    pop rcx
    sub rsp, 32                      ; shadow space for callee
    call fib
    add rsp, 32                      ; restore shadow space
    mov [rbp - 16], rax              ; assign ans
    call _pyfasm_get_tick_count
    mov [rbp - 24], rax              ; assign t1
    lea rax, [_str_lit_2]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 16]              ; load ans
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    call _pyfasm_print_newline
    lea rax, [_str_lit_3]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 24]              ; load t1
    push rax
    mov rax, [rbp - 8]               ; load t0
    mov r11, rax
    pop rax
    sub rax, r11
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    call _pyfasm_print_newline
    mov rax, 0
    jmp .epilog_main
.epilog_main:
    mov rsp, rbp
    pop rbp
    ret


section '.text' code readable executable

_pyfasm_init_io:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, -11                ; STD_OUTPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdOut], rax
    mov     ecx, -10                ; STD_INPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdIn], rax
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
    sub     rsp, 48
    and     rsp, -16

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
    mov     rbx, rcx                ; string length in rbx
    test    rbx, rbx
    jz      .done_print_str

    ; WriteFile(hStdOut, rsi, rbx, &bytesWritten, NULL)
    mov     rcx, [hStdOut]
    mov     rdx, rsi
    mov     r8, rbx
    lea     r9, [rsp + 32]
    mov     qword [rsp + 32], 0
    sub     rsp, 16                 ; 5th parameter on stack
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    add     rsp, 16

.done_print_str:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_print_newline:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    lea     rcx, [crlf_str]
    call    _pyfasm_print_str
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_char:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    mov     byte [rsp + 40], cl
    lea     rdx, [rsp + 40]
    mov     rcx, [hStdOut]
    mov     r8, 1
    lea     r9, [rsp + 32]
    mov     qword [rsp + 32], 0
    sub     rsp, 16
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    add     rsp, 16
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

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    ucomisd xmm0, [flt_zero]
    jae     .flt_pos
    movsd   [rsp + 32], xmm0
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    movsd   xmm0, [rsp + 32]
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.flt_pos:
    cvttsd2si rax, xmm0
    mov     [rsp + 40], rax
    mov     rcx, rax
    call    _pyfasm_print_int
    lea     rcx, [dot_str]
    call    _pyfasm_print_str

    cvtsi2sd xmm1, [rsp + 40]
    subsd   xmm0, xmm1
    mulsd   xmm0, [flt_1m]
    cvttsd2si rax, xmm0
    test    rax, rax
    jns     .frac_ok
    neg     rax
.frac_ok:
    mov     rcx, rax
    call    _pyfasm_print_int

    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_file_write:
    ; RCX = filename, RDX = content string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 64
    and     rsp, -16
    mov     rsi, rdx
    mov     rdx, 40000000h          ; GENERIC_WRITE
    xor     r8d, r8d                ; share = 0
    xor     r9d, r9d                ; security = NULL
    mov     qword [rsp + 32], 2      ; CREATE_ALWAYS
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0      ; template = NULL
    call    [CreateFileA]
    cmp     rax, -1
    je      .err_write
    mov     rbx, rax

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     r8, rax
    mov     rcx, rbx
    mov     rdx, rsi
    lea     r9, [bytesWritten]
    sub     rsp, 16
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    add     rsp, 16

    mov     rcx, rbx
    call    [CloseHandle]
    mov     rax, 1
    jmp     .done_write
.err_write:
    xor     eax, eax
.done_write:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_print_int:
    ; RCX = signed 64-bit integer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16

    mov     rax, rcx
    test    rax, rax
    jns     .positive

    ; Negative number
    push    rax
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    pop     rax
    neg     rax

.positive:
    lea     rdi, [rbp - 48]         ; end of temporary digit buffer
    mov     byte [rdi], 0           ; null-terminator
    mov     rbx, 10

.digit_loop:
    xor     rdx, rdx
    div     rbx                     ; rax = quotient, rdx = remainder
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    test    rax, rax
    jnz     .digit_loop

    ; Print digits string
    mov     rcx, rdi
    call    _pyfasm_print_str

    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_get_tick_count:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    [GetTickCount64]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_sleep_ms:
    ; RCX = milliseconds
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    [Sleep]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_alloc_memory:
    ; RCX = bytes to allocate
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     rdx, rcx                ; dwSize = bytes
    xor     ecx, ecx                ; lpAddress = NULL
    mov     r8d, 3000h              ; MEM_COMMIT | MEM_RESERVE
    mov     r9d, 04h                ; PAGE_READWRITE
    call    [VirtualAlloc]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_free_memory:
    ; RCX = pointer to memory
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    xor     edx, edx                ; dwSize = 0 (MUST be 0 for MEM_RELEASE)
    mov     r8d, 8000h              ; MEM_RELEASE
    call    [VirtualFree]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_spawn_thread:
    ; RCX = thread function pointer, RDX = parameter
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48                 ; 32 bytes shadow + 16 bytes for 5th and 6th args
    and     rsp, -16
    mov     r8, rcx                 ; lpStartAddress = target function
    mov     r9, rdx                 ; lpParameter = param
    xor     ecx, ecx                ; lpThreadAttributes = NULL
    xor     edx, edx                ; dwStackSize = 0
    mov     qword [rsp + 32], 0     ; dwCreationFlags = 0
    mov     qword [rsp + 40], 0     ; lpThreadId = NULL
    call    [CreateThread]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_wait_thread:
    ; RCX = thread handle
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    mov     rdx, -1                 ; INFINITE
    call    [WaitForSingleObject]
    mov     rcx, rbx
    call    [CloseHandle]
    lea     rsp, [rbp - 8]
    pop     rbx
    pop     rbp
    ret

_pyfasm_atomic_add:
    ; RCX = pointer to qword, RDX = value to add
    lock add qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_atomic_sub:
    ; RCX = pointer to qword, RDX = value to subtract
    lock sub qword [rcx], rdx
    mov     rax, [rcx]
    ret


section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL'

    import kernel32, \
           GetStdHandle, 'GetStdHandle', \
           WriteFile, 'WriteFile', \
           ReadFile, 'ReadFile', \
           CreateFileA, 'CreateFileA', \
           GetTickCount64, 'GetTickCount64', \
           Sleep, 'Sleep', \
           VirtualAlloc, 'VirtualAlloc', \
           VirtualFree, 'VirtualFree', \
           CreateThread, 'CreateThread', \
           WaitForSingleObject, 'WaitForSingleObject', \
           CloseHandle, 'CloseHandle', \
           ExitProcess, 'ExitProcess'
