format binary as 'bin'
use64
org 0x1000000   ; Default MyOS userspace program base
jmp _pyfasm_entry_point


align 8
crlf_str        db 13, 10, 0
minus_str       db '-', 0

    _str_lit_1 db 72, 101, 108, 108, 111, 32, 102, 114, 111, 109, 32, 80, 121, 70, 65, 83, 77, 58, 32, 80, 117, 114, 101, 32, 78, 97, 116, 105, 118, 101, 32, 120, 54, 52, 32, 65, 115, 115, 101, 109, 98, 108, 121, 32, 119, 105, 116, 104, 111, 117, 116, 32, 71, 73, 76, 33, 10, 0
    _str_lit_2 db 67, 111, 109, 112, 117, 116, 105, 110, 103, 32, 98, 97, 115, 105, 99, 32, 97, 114, 105, 116, 104, 109, 101, 116, 105, 99, 58, 32, 40, 49, 48, 48, 32, 42, 32, 50, 53, 41, 32, 47, 32, 53, 32, 43, 32, 52, 50, 32, 61, 32, 0

align 16

_pyfasm_entry_point:
    sub rsp, 40                      ; shadow space for Windows x64 ABI
    call _pyfasm_init_io             ; initialize runtime I/O
    call main                        ; execute user main()
    mov ecx, eax                     ; exit code
    ret

; ============================================================
; Function: main
; ============================================================
main:
    push rbp
    mov rbp, rsp
    sub rsp, 48                      ; frame + shadow space
    lea rax, [_str_lit_1]
    mov rcx, rax
    call _pyfasm_print_str
    lea rax, [_str_lit_2]
    mov rcx, rax
    call _pyfasm_print_str
    mov rax, 100
    push rax
    mov rax, 25
    mov r11, rax
    pop rax
    imul rax, r11
    push rax
    mov rax, 5
    mov r11, rax
    pop rax
    cqo
    idiv r11
    push rax
    mov rax, 42
    mov r11, rax
    pop rax
    add rax, r11
    mov [rbp - 8], rax               ; assign ans
    mov rax, [rbp - 8]               ; load ans
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
