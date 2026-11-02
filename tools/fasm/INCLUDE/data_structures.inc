; ==============================================================================
; FASM Modern SDK - High-Performance Data Structures & Strings (x86-64)
; File: include/data_structures.inc
; Python-like Dictionary, Dynamic List, and Fast String Operations
; ==============================================================================

proc FasmStrHash uses rcx rdx, pStr
        ; RCX = null-terminated string
        ; Returns RAX = 64-bit FNV-1a hash
        mov     rax, 0CBF29CE484222325h
        mov     rdx, 100000001B3h
        test    rcx, rcx
        jz      .h_ret
.h_loop:
        movzx   r8d, byte [rcx]
        test    r8b, r8b
        jz      .h_done
        xor     rax, r8
        imul    rax, rdx
        inc     rcx
        jmp     .h_loop
.h_done:
        test    rax, rax
        jnz     .h_ret
        mov     rax, 1
.h_ret:
        ret
endp


proc FasmStrCmp uses rcx rdx, pStr1, pStr2
        ; RCX = str1, RDX = str2
        ; Returns RAX = 1 if equal, 0 if not equal
        test    rcx, rcx
        jz      .c_null1
        test    rdx, rdx
        jz      .c_ne
        cmp     rcx, rdx
        je      .c_eq
.c_loop:
        mov     al, [rcx]
        mov     ah, [rdx]
        cmp     al, ah
        jne     .c_ne
        test    al, al
        jz      .c_eq
        inc     rcx
        inc     rdx
        jmp     .c_loop
.c_null1:
        test    rdx, rdx
        jz      .c_eq
.c_ne:
        xor     eax, eax
        ret
.c_eq:
        mov     eax, 1
        ret
endp


proc FasmStrLen uses rdi, pStr
        ; RCX = pStr
        ; Returns RAX = string length in bytes
        mov     rdi, rcx
        xor     eax, eax
        test    rdi, rdi
        jz      .sl_zero
        mov     rcx, -1
        repne   scasb
        not     rcx
        dec     rcx
        mov     rax, rcx
        ret
.sl_zero:
        xor     rax, rax
        ret
endp


proc FasmDictCreate uses rbx rdi, initialCap
        ; RCX = initial capacity (power of 2, default 16)
        ; Returns RAX = dict pointer
        test    rcx, rcx
        jnz     @f
        mov     rcx, 16
@@:
        mov     rbx, rcx
        ; Total bytes = 16 (header) + cap * 24
        lea     rax, [rbx + rbx * 2]
        shl     rax, 3
        add     rax, 16
        invoke  VirtualAlloc, 0, rax, 1000h or 2000h, 4 ; MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE
        mov     [rax], rbx             ; capacity
        mov     qword [rax + 8], 0     ; count = 0
        ; Zero out entries
        lea     rdi, [rax + 16]
        lea     rcx, [rbx + rbx * 2]
        shl     rcx, 1
        push    rax
        xor     eax, eax
        rep     stosq
        pop     rax
        ret
endp


proc FasmDictSet uses rbx rsi rdi r12 r13 r14, pDict, pKey, val
        ; RCX = pDict, RDX = pKey, R8 = val
        test    rcx, rcx
        jz      .ds_err
        mov     rbx, rcx
        mov     rsi, rdx
        mov     r12, r8

        mov     rcx, rsi
        call    FasmStrHash
        mov     r13, rax               ; hash

        mov     r14, [rbx]             ; capacity
        dec     r14                    ; mask
        and     rax, r14               ; slot
        mov     rdi, rax

.ds_probe:
        lea     rax, [rdi + rdi * 2]
        shl     rax, 3
        lea     rcx, [rbx + 16 + rax]

        mov     rax, [rcx]
        test    rax, rax
        jz      .ds_empty

        cmp     rax, r13
        jne     .ds_next

        push    rcx
        mov     rcx, [rcx + 8]
        mov     rdx, rsi
        call    FasmStrCmp
        pop     rcx
        test    eax, eax
        jnz     .ds_update

.ds_next:
        inc     rdi
        and     rdi, r14
        jmp     .ds_probe

.ds_empty:
        mov     [rcx], r13
        mov     [rcx + 8], rsi
        mov     [rcx + 16], r12
        inc     qword [rbx + 8]
        jmp     .ds_done

.ds_update:
        mov     [rcx + 16], r12

.ds_done:
        mov     rax, rbx
        ret
.ds_err:
        xor     rax, rax
        ret
endp


proc FasmDictGet uses rbx rsi rdi r12 r13 r14, pDict, pKey, defaultVal
        ; RCX = pDict, RDX = pKey, R8 = defaultVal
        test    rcx, rcx
        jz      .dg_def
        mov     rbx, rcx
        mov     rsi, rdx
        mov     r12, r8

        mov     rcx, rsi
        call    FasmStrHash
        mov     r13, rax

        mov     r14, [rbx]
        test    r14, r14
        jz      .dg_def
        dec     r14
        and     rax, r14
        mov     rdi, rax

        xor     r11, r11
.dg_probe:
        cmp     r11, [rbx]
        jge     .dg_def

        lea     rax, [rdi + rdi * 2]
        shl     rax, 3
        lea     rcx, [rbx + 16 + rax]

        mov     rax, [rcx]
        test    rax, rax
        jz      .dg_def

        cmp     rax, r13
        jne     .dg_next

        push    rcx
        push    r11
        mov     rcx, [rcx + 8]
        mov     rdx, rsi
        call    FasmStrCmp
        pop     r11
        pop     rcx
        test    eax, eax
        jnz     .dg_found

.dg_next:
        inc     rdi
        and     rdi, r14
        inc     r11
        jmp     .dg_probe

.dg_found:
        mov     rax, [rcx + 16]
        ret

.dg_def:
        mov     rax, r12
        ret
endp
