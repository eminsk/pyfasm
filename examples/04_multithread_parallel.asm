format PE64 console 5.0
entry _pyfasm_entry_point

include 'win64a.inc'


section '.data' data readable writeable
    hStdOut         dq 0
    hStdIn          dq 0
    bytesWritten    dq 0
    crlf_str        db 13, 10, 0
    minus_str       db '-', 0

    _str_lit_1 db 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 10, 0
    _str_lit_2 db 32, 32, 80, 121, 70, 65, 83, 77, 32, 84, 114, 117, 101, 32, 77, 117, 108, 116, 105, 45, 84, 104, 114, 101, 97, 100, 105, 110, 103, 32, 66, 101, 110, 99, 104, 109, 97, 114, 107, 32, 40, 78, 111, 45, 71, 73, 76, 41, 10, 0
    _str_lit_3 db 83, 112, 97, 119, 110, 105, 110, 103, 32, 56, 32, 110, 97, 116, 105, 118, 101, 32, 79, 83, 32, 116, 104, 114, 101, 97, 100, 115, 32, 97, 99, 114, 111, 115, 115, 32, 67, 80, 85, 32, 99, 111, 114, 101, 115, 46, 46, 46, 10, 0
    _str_lit_4 db 69, 120, 112, 101, 99, 116, 101, 100, 32, 99, 111, 117, 110, 116, 58, 32, 50, 48, 48, 48, 48, 48, 48, 32, 40, 56, 32, 120, 32, 50, 53, 48, 44, 48, 48, 48, 41, 10, 0
    _str_lit_5 db 65, 99, 116, 117, 97, 108, 32, 99, 111, 117, 110, 116, 58, 32, 32, 32, 0
    _str_lit_6 db 69, 108, 97, 112, 115, 101, 100, 32, 116, 105, 109, 101, 32, 40, 109, 115, 41, 58, 32, 0

section '.text' code readable executable

_pyfasm_entry_point:
    sub rsp, 40                      ; shadow space for Windows x64 ABI
    call _pyfasm_init_io             ; initialize runtime I/O
    call main                        ; execute user main()
    mov ecx, eax                     ; exit code
    call [ExitProcess]

; ============================================================
; Function: worker
; ============================================================
worker:
    push rbp
    mov rbp, rsp
    sub rsp, 64                      ; frame + shadow space
    mov [rbp - 8], rcx               ; arg counter_ptr
    xor eax, eax
    mov [rbp - 16], rax              ; init for i
._for_start_1:
    mov rax, [rbp - 16]
    push rax
    mov rax, 250000
    mov r11, rax
    pop rax
    cmp rax, r11
    jge ._for_end_3
    mov rax, 1
    push rax
    mov rax, [rbp - 8]               ; load counter_ptr
    mov rcx, rax
    pop rdx
    call _pyfasm_atomic_add
._for_step_2:
    inc qword [rbp - 16]
    jmp ._for_start_1
._for_end_3:
    mov rax, 0
    jmp .epilog_worker
.epilog_worker:
    mov rsp, rbp
    pop rbp
    ret

; ============================================================
; Function: main
; ============================================================
main:
    push rbp
    mov rbp, rsp
    sub rsp, 144                     ; frame + shadow space
    lea rax, [_str_lit_1]
    mov rcx, rax
    call _pyfasm_print_str
    lea rax, [_str_lit_2]
    mov rcx, rax
    call _pyfasm_print_str
    lea rax, [_str_lit_1]
    mov rcx, rax
    call _pyfasm_print_str
    lea rax, [_str_lit_3]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, 64
    mov rcx, rax
    call _pyfasm_alloc_memory
    mov [rbp - 8], rax               ; assign counter
    mov rax, 0
    push rax                         ; save value to assign
    mov rax, 0
    push rax                         ; save index
    mov rax, [rbp - 8]               ; load counter
    mov r8, rax                      ; array base pointer
    pop r11                          ; index
    pop rax                          ; value
    mov [r8 + r11 * 8], rax          ; store arr[idx] = val
    call _pyfasm_get_tick_count
    mov [rbp - 16], rax              ; assign t0
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 24], rax              ; assign t1
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 32], rax              ; assign t2
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 40], rax              ; assign t3
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 48], rax              ; assign t4
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 56], rax              ; assign t5
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 64], rax              ; assign t6
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 72], rax              ; assign t7
    mov rax, [rbp - 8]               ; load counter
    push rax
    lea rax, [worker]                ; address of worker
    mov rcx, rax
    pop rdx
    call _pyfasm_spawn_thread
    mov [rbp - 80], rax              ; assign t8
    mov rax, [rbp - 24]              ; load t1
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 32]              ; load t2
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 40]              ; load t3
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 48]              ; load t4
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 56]              ; load t5
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 64]              ; load t6
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 72]              ; load t7
    mov rcx, rax
    call _pyfasm_wait_thread
    mov rax, [rbp - 80]              ; load t8
    mov rcx, rax
    call _pyfasm_wait_thread
    call _pyfasm_get_tick_count
    mov [rbp - 88], rax              ; assign t1_end
    mov rax, [rbp - 8]               ; load counter
    push rax
    mov rax, 0
    mov r11, rax
    pop rax
    mov rax, [rax + r11 * 8]         ; load arr[idx]
    mov [rbp - 96], rax              ; assign total
    lea rax, [_str_lit_4]
    mov rcx, rax
    call _pyfasm_print_str
    lea rax, [_str_lit_5]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 96]              ; load total
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    call _pyfasm_print_newline
    lea rax, [_str_lit_6]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, [rbp - 88]              ; load t1_end
    push rax
    mov rax, [rbp - 16]              ; load t0
    mov r11, rax
    pop rax
    sub rax, r11
    mov rcx, rax
    call _pyfasm_print_int
    call _pyfasm_print_newline
    call _pyfasm_print_newline
    mov rax, [rbp - 8]               ; load counter
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
