format PE64 console 5.0
entry _pyfasm_entry_point

include 'win64a.inc'


section '.data' data readable writeable
    hStdOut         dq 0
    hStdIn          dq 0
    bytesWritten    dq 0
    crlf_str        db 13, 10, 0
    minus_str       db '-', 0

    _str_lit_1 db 83, 105, 101, 118, 101, 32, 111, 102, 32, 69, 114, 97, 116, 111, 115, 116, 104, 101, 110, 101, 115, 32, 117, 112, 32, 116, 111, 32, 0
    _str_lit_2 db 32, 105, 110, 32, 110, 97, 116, 105, 118, 101, 32, 120, 54, 52, 32, 109, 101, 109, 111, 114, 121, 32, 98, 117, 102, 102, 101, 114, 46, 46, 46, 10, 0
    _str_lit_3 db 84, 111, 116, 97, 108, 32, 112, 114, 105, 109, 101, 32, 110, 117, 109, 98, 101, 114, 115, 32, 102, 111, 117, 110, 100, 58, 32, 0
    _str_lit_4 db 67, 111, 109, 112, 117, 116, 97, 116, 105, 111, 110, 32, 116, 105, 109, 101, 32, 40, 109, 115, 41, 58, 32, 0

section '.text' code readable executable

_pyfasm_entry_point:
    sub rsp, 40                      ; shadow space for Windows x64 ABI
    call _pyfasm_init_io             ; initialize runtime I/O
    call main                        ; execute user main()
    mov ecx, eax                     ; exit code
    call [ExitProcess]

; ============================================================
; Function: main
; ============================================================
main:
    push rbp
    mov rbp, rsp
    sub rsp, 112                     ; frame + shadow space
    mov rax, 100000
    mov [rbp - 8], rax               ; assign limit
    lea rax, [_str_lit_1]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 8]               ; load limit
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    lea rax, [_str_lit_2]
    mov rcx, rax
    call _pyfasm_print_str
    call _pyfasm_get_tick_count
    mov [rbp - 16], rax              ; assign t0
    mov rax, [rbp - 8]               ; load limit
    push rax
    mov rax, 8
    mov r11, rax
    pop rax
    imul rax, r11
    mov rcx, rax
    call _pyfasm_alloc_memory
    mov [rbp - 24], rax              ; assign sieve
    xor eax, eax
    mov [rbp - 32], rax              ; init for i
._for_start_1:
    mov rax, [rbp - 32]
    push rax
    mov rax, [rbp - 8]               ; load limit
    mov r11, rax
    pop rax
    cmp rax, r11
    jge ._for_end_3
    mov rax, 1
    push rax                         ; save value to assign
    mov rax, [rbp - 32]              ; load i
    push rax                         ; save index
    mov rax, [rbp - 24]              ; load sieve
    mov r8, rax                      ; array base pointer
    pop r11                          ; index
    pop rax                          ; value
    mov [r8 + r11 * 8], rax          ; store arr[idx] = val
._for_step_2:
    inc qword [rbp - 32]
    jmp ._for_start_1
._for_end_3:
    mov rax, 0
    push rax                         ; save value to assign
    mov rax, 0
    push rax                         ; save index
    mov rax, [rbp - 24]              ; load sieve
    mov r8, rax                      ; array base pointer
    pop r11                          ; index
    pop rax                          ; value
    mov [r8 + r11 * 8], rax          ; store arr[idx] = val
    mov rax, 0
    push rax                         ; save value to assign
    mov rax, 1
    push rax                         ; save index
    mov rax, [rbp - 24]              ; load sieve
    mov r8, rax                      ; array base pointer
    pop r11                          ; index
    pop rax                          ; value
    mov [r8 + r11 * 8], rax          ; store arr[idx] = val
    mov rax, 2
    mov [rbp - 40], rax              ; assign p
._while_start_4:
    mov rax, [rbp - 40]              ; load p
    push rax
    mov rax, [rbp - 40]              ; load p
    mov r11, rax
    pop rax
    imul rax, r11
    push rax
    mov rax, [rbp - 8]               ; load limit
    mov r11, rax
    pop rax
    cmp rax, r11
    setl al
    movzx rax, al
    test rax, rax
    jz ._while_end_5
    mov rax, [rbp - 24]              ; load sieve
    push rax
    mov rax, [rbp - 40]              ; load p
    mov r11, rax
    pop rax
    mov rax, [rax + r11 * 8]         ; load arr[idx]
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    cmp rax, r11
    sete al
    movzx rax, al
    test rax, rax
    jz ._if_else_6
    mov rax, [rbp - 40]              ; load p
    push rax
    mov rax, [rbp - 40]              ; load p
    mov r11, rax
    pop rax
    imul rax, r11
    mov [rbp - 64], rax              ; assign multiple
._while_start_8:
    mov rax, [rbp - 64]              ; load multiple
    push rax
    mov rax, [rbp - 8]               ; load limit
    mov r11, rax
    pop rax
    cmp rax, r11
    setl al
    movzx rax, al
    test rax, rax
    jz ._while_end_9
    mov rax, 0
    push rax                         ; save value to assign
    mov rax, [rbp - 64]              ; load multiple
    push rax                         ; save index
    mov rax, [rbp - 24]              ; load sieve
    mov r8, rax                      ; array base pointer
    pop r11                          ; index
    pop rax                          ; value
    mov [r8 + r11 * 8], rax          ; store arr[idx] = val
    mov rax, [rbp - 64]              ; load multiple
    push rax
    mov rax, [rbp - 40]              ; load p
    mov r11, rax
    pop rax
    add rax, r11
    mov [rbp - 64], rax              ; assign multiple
    jmp ._while_start_8
._while_end_9:
    jmp ._if_end_7
._if_else_6:
._if_end_7:
    mov rax, [rbp - 40]              ; load p
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    add rax, r11
    mov [rbp - 40], rax              ; assign p
    jmp ._while_start_4
._while_end_5:
    mov rax, 0
    mov [rbp - 48], rax              ; assign primes_count
    xor eax, eax
    mov [rbp - 32], rax              ; init for i
._for_start_10:
    mov rax, [rbp - 32]
    push rax
    mov rax, [rbp - 8]               ; load limit
    mov r11, rax
    pop rax
    cmp rax, r11
    jge ._for_end_12
    mov rax, [rbp - 24]              ; load sieve
    push rax
    mov rax, [rbp - 32]              ; load i
    mov r11, rax
    pop rax
    mov rax, [rax + r11 * 8]         ; load arr[idx]
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    cmp rax, r11
    sete al
    movzx rax, al
    test rax, rax
    jz ._if_else_13
    mov rax, [rbp - 48]              ; load primes_count
    push rax
    mov rax, 1
    mov r11, rax
    pop rax
    add rax, r11
    mov [rbp - 48], rax              ; assign primes_count
    jmp ._if_end_14
._if_else_13:
._if_end_14:
._for_step_11:
    inc qword [rbp - 32]
    jmp ._for_start_10
._for_end_12:
    call _pyfasm_get_tick_count
    mov [rbp - 56], rax              ; assign t1
    lea rax, [_str_lit_3]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 48]              ; load primes_count
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    call _pyfasm_print_newline
    lea rax, [_str_lit_4]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 56]              ; load t1
    push rax
    mov rax, [rbp - 16]              ; load t0
    mov r11, rax
    pop rax
    sub rax, r11
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    call _pyfasm_print_newline
    mov rax, [rbp - 24]              ; load sieve
    mov rcx, rax
    call _pyfasm_free_memory
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
           GetTickCount64, 'GetTickCount64', \
           Sleep, 'Sleep', \
           VirtualAlloc, 'VirtualAlloc', \
           VirtualFree, 'VirtualFree', \
           CreateThread, 'CreateThread', \
           WaitForSingleObject, 'WaitForSingleObject', \
           CloseHandle, 'CloseHandle', \
           ExitProcess, 'ExitProcess'
