; ==============================================================================
; FASM Modern SDK - Zero-Allocation JSON Parser Engine (x86-64)
; File: include/json_fast.inc
; High-performance JSON key/value extractor with zero external dependencies.
; ==============================================================================

proc JsonGetStr uses rbx rsi rdi r12 r13, pJson, pKey, pOutBuf, maxLen
        ; RCX = pJson (null-terminated UTF-8/ASCII JSON string)
        ; RDX = pKey (e.g. "title", "quota_remaining")
        ; R8  = pOutBuf (destination buffer)
        ; R9  = maxLen (buffer capacity)
        ; Returns RAX = bytes copied (0 if not found)
        mov     rsi, rcx
        mov     rbx, rdx
        mov     rdi, r8
        mov     r12, r9

        test    rsi, rsi
        jz      .not_found
        test    rbx, rbx
        jz      .not_found
        test    rdi, rdi
        jz      .not_found
        test    r12, r12
        jz      .not_found

        ; Calculate key length
        mov     rcx, rbx
        xor     eax, eax
        push    rdi
        mov     rdi, rbx
        mov     rcx, -1
        repne   scasb
        not     rcx
        dec     rcx
        pop     rdi
        mov     r13, rcx                ; r13 = keyLen
        test    r13, r13
        jz      .not_found

.scan_key:
        mov     al, [rsi]
        test    al, al
        jz      .not_found

        ; Look for opening quote of key
        cmp     al, '"'
        jne     .next_char

        ; Compare key
        inc     rsi
        push    rsi
        push    rbx
        mov     rcx, r13
.cmp_k:
        mov     al, [rsi]
        mov     ah, [rbx]
        cmp     al, ah
        jne     .key_mismatch
        inc     rsi
        inc     rbx
        dec     rcx
        jnz     .cmp_k

        ; Key matched! Next char must be quote
        cmp     byte [rsi], '"'
        jne     .key_mismatch

        ; Match confirmed
        pop     rbx
        pop     rax                     ; discard saved rsi
        inc     rsi                     ; skip closing quote

        ; Find colon ':'
.find_colon:
        mov     al, [rsi]
        test    al, al
        jz      .not_found
        inc     rsi
        cmp     al, ':'
        jne     .find_colon

        ; Skip whitespace until value
.find_val_quote:
        mov     al, [rsi]
        test    al, al
        jz      .not_found
        cmp     al, '"'
        je      .found_val_start
        inc     rsi
        jmp     .find_val_quote

.found_val_start:
        inc     rsi                     ; skip opening quote
        xor     ecx, ecx                ; byte count

.copy_loop:
        mov     al, [rsi]
        test    al, al
        jz      .terminate
        cmp     al, '"'
        je      .terminate
        cmp     rcx, r12
        jae     .terminate

        ; Check escape sequence
        cmp     al, '\'
        jne     .store_byte
        inc     rsi
        mov     al, [rsi]
        test    al, al
        jz      .terminate
        cmp     al, '"'
        je      .store_byte
        cmp     al, '\'
        je      .store_byte
        cmp     al, 'n'
        jne     .store_byte
        mov     al, 10

.store_byte:
        mov     [rdi + rcx], al
        inc     rcx
        inc     rsi
        jmp     .copy_loop

.terminate:
        mov     byte [rdi + rcx], 0
        mov     rax, rcx
        ret

.key_mismatch:
        pop     rbx
        pop     rsi

.next_char:
        inc     rsi
        jmp     .scan_key

.not_found:
        test    rdi, rdi
        jz      @f
        mov     byte [rdi], 0
@@:
        xor     eax, eax
        ret
endp


proc JsonGetInt uses rbx rsi rdi r12, pJson, pKey, defaultVal
        ; RCX = pJson, RDX = pKey, R8 = defaultVal
        ; Returns RAX = 64-bit signed integer value
        mov     rsi, rcx
        mov     rbx, rdx
        mov     r12, r8

        test    rsi, rsi
        jz      .ji_default
        test    rbx, rbx
        jz      .ji_default

        ; Calculate key length
        push    rdi
        mov     rdi, rbx
        xor     eax, eax
        mov     rcx, -1
        repne   scasb
        not     rcx
        dec     rcx
        pop     rdi
        mov     r8, rcx                 ; r8 = keyLen
        test    r8, r8
        jz      .ji_default

.ji_scan:
        mov     al, [rsi]
        test    al, al
        jz      .ji_default

        cmp     al, '"'
        jne     .ji_next

        inc     rsi
        push    rsi
        push    rbx
        mov     rcx, r8
.ji_cmp:
        mov     al, [rsi]
        mov     ah, [rbx]
        cmp     al, ah
        jne     .ji_mismatch
        inc     rsi
        inc     rbx
        dec     rcx
        jnz     .ji_cmp

        cmp     byte [rsi], '"'
        jne     .ji_mismatch

        pop     rbx
        pop     rax
        inc     rsi

.ji_colon:
        mov     al, [rsi]
        test    al, al
        jz      .ji_default
        inc     rsi
        cmp     al, ':'
        jne     .ji_colon

.ji_skip_spaces:
        mov     al, [rsi]
        test    al, al
        jz      .ji_default
        cmp     al, ' '
        je      .ji_adv_space
        cmp     al, 9
        je      .ji_adv_space
        cmp     al, 13
        je      .ji_adv_space
        cmp     al, 10
        je      .ji_adv_space
        jmp     .ji_parse_num
.ji_adv_space:
        inc     rsi
        jmp     .ji_skip_spaces

.ji_parse_num:
        xor     r9, r9                  ; sign (0=pos, 1=neg)
        cmp     byte [rsi], '-'
        jne     .ji_digits
        mov     r9, 1
        inc     rsi

.ji_digits:
        xor     rax, rax
.ji_loop:
        movzx   ecx, byte [rsi]
        cmp     cl, '0'
        jb      .ji_done
        cmp     cl, '9'
        ja      .ji_done
        sub     cl, '0'
        imul    rax, 10
        add     rax, rcx
        inc     rsi
        jmp     .ji_loop

.ji_done:
        test    r9, r9
        jz      .ji_ret
        neg     rax
.ji_ret:
        ret

.ji_mismatch:
        pop     rbx
        pop     rsi

.ji_next:
        inc     rsi
        jmp     .ji_scan

.ji_default:
        mov     rax, r12
        ret
endp
