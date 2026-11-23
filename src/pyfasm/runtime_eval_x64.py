# -*- coding: utf-8 -*-
"""
Portable Pure x86-64 Runtime Expression Evaluator (`eval`) for PyFASM.
Shared across Win64 (Console + GUI), Linux, macOS, and MyOS via runtime_core_x64.py.
Evaluates dynamic string expressions returned by `input()` or constructed at runtime,
supporting arithmetic, comparisons, boolean logic, bitwise ops, strings, constants,
and math/conversion built-ins using typed (RAX=value, RDX=type_tag) pairs.
Type tags: 0 = int64, 1 = IEEE-754 float64, 2 = UTF-8 cstr ptr, 3 = bool, 4 = None.
"""
from __future__ import annotations


def get_eval_x64_data() -> str:
    return r"""
    align 8
    _pyfasm_eval_last_type  dq 0
    _pyfasm_eval_e          dq 4005BF0A8B145769h ; 2.718281828459045
    _pyfasm_eval_tau        dq 401921FB54442D18h ; 6.283185307179586
    _pyfasm_eval_str_true   db 'True', 0
    _pyfasm_eval_str_false  db 'False', 0
    _pyfasm_eval_str_none   db 'None', 0
    _pyfasm_eval_str_nan    db 'nan', 0
    _pyfasm_eval_str_inf    db 'inf', 0
    _pyfasm_eval_str_ninf   db '-inf', 0
    _pyfasm_eval_str_neg0   db '-0.0', 0
    _pyfasm_eval_str_empty  db 0
    _pyfasm_eval_kw_or      db 'or', 0
    _pyfasm_eval_kw_and     db 'and', 0
    _pyfasm_eval_kw_not     db 'not', 0
    _pyfasm_eval_kw_true    db 'True', 0
    _pyfasm_eval_kw_false   db 'False', 0
    _pyfasm_eval_kw_none    db 'None', 0
    _pyfasm_eval_kw_math    db 'math', 0
    _pyfasm_eval_kw_pi      db 'pi', 0
    _pyfasm_eval_kw_e       db 'e', 0
    _pyfasm_eval_kw_tau     db 'tau', 0
    _pyfasm_eval_kw_inf     db 'inf', 0
    _pyfasm_eval_kw_nan     db 'nan', 0
    _pyfasm_eval_kw_abs     db 'abs', 0
    _pyfasm_eval_kw_int     db 'int', 0
    _pyfasm_eval_kw_float   db 'float', 0
    _pyfasm_eval_kw_str     db 'str', 0
    _pyfasm_eval_kw_bool    db 'bool', 0
    _pyfasm_eval_kw_len     db 'len', 0
    _pyfasm_eval_kw_round   db 'round', 0
    _pyfasm_eval_kw_pow     db 'pow', 0
    _pyfasm_eval_kw_min     db 'min', 0
    _pyfasm_eval_kw_max     db 'max', 0
    _pyfasm_eval_kw_sqrt    db 'sqrt', 0
    _pyfasm_eval_kw_sin     db 'sin', 0
    _pyfasm_eval_kw_cos     db 'cos', 0
    _pyfasm_eval_kw_tan     db 'tan', 0
    _pyfasm_eval_kw_exp     db 'exp', 0
    _pyfasm_eval_kw_log     db 'log', 0
    _pyfasm_eval_kw_log10   db 'log10', 0
    _pyfasm_eval_kw_floor   db 'floor', 0
    _pyfasm_eval_kw_ceil    db 'ceil', 0
    _pyfasm_eval_kw_atan2   db 'atan2', 0
"""


def get_eval_x64_code() -> str:
    return r"""
; ============================================================
; Portable Native Expression Evaluator (`eval`)
; ============================================================

_pyfasm_eval:
    ; RCX = expr UTF-8 string ptr -> RAX = result, [_pyfasm_eval_last_type] = tag (0..4)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 40
    and     rsp, -16

    mov     qword [_pyfasm_eval_last_type], 0
    test    rcx, rcx
    jz      .ev_top_empty
    cmp     rcx, 65536
    jb      .ev_top_empty
    cmp     byte [rcx], 0
    je      .ev_top_empty

    mov     rsi, rcx
    call    _pyfasm_ev_expr
    mov     [_pyfasm_eval_last_type], rdx
    jmp     .ev_top_done

.ev_top_empty:
    xor     eax, eax
    mov     qword [_pyfasm_eval_last_type], 4

.ev_top_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_eval_float_to_clean_str:
    ; RCX = IEEE-754 float64 bits -> RAX = cleaned decimal UTF-8 cstr ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rax, rbx
    mov     rdx, [_pyfasm_flt_inf]
    cmp     rax, rdx
    jb      .evfc_finite
    ja      .evfc_nan
    bt      rbx, 63
    jc      .evfc_ninf
    lea     rax, [_pyfasm_eval_str_inf]
    jmp     .evfc_done
.evfc_ninf:
    lea     rax, [_pyfasm_eval_str_ninf]
    jmp     .evfc_done
.evfc_nan:
    lea     rax, [_pyfasm_eval_str_nan]
    jmp     .evfc_done

.evfc_finite:
    mov     rcx, rbx
    call    _pyfasm_float_to_str
    mov     rbx, rax                ; formatted buffer pointer
    test    rbx, rbx
    jz      .evfc_done

    ; Fix double minus ('--...') if ever produced on edge negative inputs
    cmp     byte [rbx], '-'
    jne     .evfc_find_dot
    cmp     byte [rbx + 1], '-'
    jne     .evfc_find_dot
    inc     rbx

.evfc_find_dot:
    mov     rsi, rbx
    xor     edi, edi                ; edi = dot pointer
.evfc_scan:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .evfc_at_end
    cmp     al, '.'
    jne     .evfc_next
    mov     rdi, rsi
.evfc_next:
    inc     rsi
    jmp     .evfc_scan

.evfc_at_end:
    test    rdi, rdi
    jz      .evfc_ret
    ; rsi points to null terminator; trim trailing '0' back toward dot+1
    dec     rsi
.evfc_trim:
    lea     rax, [rdi + 1]
    cmp     rsi, rax
    jbe     .evfc_ret
    cmp     byte [rsi], '0'
    jne     .evfc_ret
    mov     byte [rsi], 0
    dec     rsi
    jmp     .evfc_trim

.evfc_ret:
    mov     rax, rbx
.evfc_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_eval_print_clean_float:
    ; RCX = IEEE-754 float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_eval_float_to_clean_str
    mov     rcx, rax
    call    _pyfasm_print_str
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_eval_value:
    ; RCX = val, RDX = type_tag (0=int, 1=f64, 2=str, 3=bool, 4=None)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16

    cmp     edx, 1
    je      .evp_flt
    cmp     edx, 2
    je      .evp_str
    cmp     edx, 3
    je      .evp_bool
    cmp     edx, 4
    je      .evp_none
    call    _pyfasm_print_int
    jmp     .evp_done
.evp_flt:
    call    _pyfasm_eval_print_clean_float
    jmp     .evp_done
.evp_str:
    call    _pyfasm_print_str
    jmp     .evp_done
.evp_bool:
    test    rcx, rcx
    jz      .evp_bfalse
    lea     rcx, [_pyfasm_eval_str_true]
    call    _pyfasm_print_str
    jmp     .evp_done
.evp_bfalse:
    lea     rcx, [_pyfasm_eval_str_false]
    call    _pyfasm_print_str
    jmp     .evp_done
.evp_none:
    lea     rcx, [_pyfasm_eval_str_none]
    call    _pyfasm_print_str
.evp_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_eval_to_int:
    ; RCX = val, RDX = type_tag -> RAX = int64
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    cmp     edx, 1
    je      .evti_flt
    cmp     edx, 2
    je      .evti_str
    cmp     edx, 4
    je      .evti_zero
    mov     rax, rcx
    jmp     .evti_done
.evti_flt:
    movq    xmm0, rcx
    cvttsd2si rax, xmm0
    jmp     .evti_done
.evti_str:
    call    _pyfasm_str_to_int
    jmp     .evti_done
.evti_zero:
    xor     eax, eax
.evti_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_eval_to_float:
    ; RCX = val, RDX = type_tag -> RAX = IEEE-754 f64 bits
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    cmp     edx, 1
    je      .evtf_same
    cmp     edx, 2
    je      .evtf_str
    cmp     edx, 4
    je      .evtf_zero
    cvtsi2sd xmm0, rcx
    movq    rax, xmm0
    jmp     .evtf_done
.evtf_same:
    mov     rax, rcx
    jmp     .evtf_done
.evtf_zero:
    xor     eax, eax
    jmp     .evtf_done
.evtf_str:
    ; Reuse internal parser on the string content
    push    rsi
    mov     rsi, rcx
    call    _pyfasm_ev_skip_ws
    xor     ebx, ebx
    cmp     byte [rsi], '-'
    jne     .evtf_splus
    mov     ebx, 1
    inc     rsi
    jmp     .evtf_snum
.evtf_splus:
    cmp     byte [rsi], '+'
    jne     .evtf_snum
    inc     rsi
.evtf_snum:
    call    _pyfasm_ev_parse_number
    cmp     edx, 1
    je      .evtf_sneg
    cvtsi2sd xmm0, rax
    movq    rax, xmm0
.evtf_sneg:
    test    ebx, ebx
    jz      .evtf_sret
    mov     rcx, [_pyfasm_flt_sign_mask]
    xor     rax, rcx
.evtf_sret:
    pop     rsi
.evtf_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_eval_to_str:
    ; RCX = val, RDX = type_tag -> RAX = UTF-8 cstr ptr
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    cmp     edx, 1
    je      .evts_flt
    cmp     edx, 2
    je      .evts_str
    cmp     edx, 3
    je      .evts_bool
    cmp     edx, 4
    je      .evts_none
    call    _pyfasm_int_to_str
    jmp     .evts_done
.evts_flt:
    call    _pyfasm_eval_float_to_clean_str
    jmp     .evts_done
.evts_str:
    mov     rax, rcx
    jmp     .evts_done
.evts_bool:
    test    rcx, rcx
    jz      .evts_bf
    lea     rax, [_pyfasm_eval_str_true]
    jmp     .evts_done
.evts_bf:
    lea     rax, [_pyfasm_eval_str_false]
    jmp     .evts_done
.evts_none:
    lea     rax, [_pyfasm_eval_str_none]
.evts_done:
    mov     rsp, rbp
    pop     rbp
    ret

; --- Internal Lexer / Helpers (cursor in RSI) ---

_pyfasm_ev_skip_ws:
    movzx   eax, byte [rsi]
    cmp     al, ' '
    je      .evsw_adv
    cmp     al, 9
    je      .evsw_adv
    cmp     al, 13
    je      .evsw_adv
    cmp     al, 10
    je      .evsw_adv
    ret
.evsw_adv:
    inc     rsi
    jmp     _pyfasm_ev_skip_ws

_pyfasm_ev_is_ident_char:
    ; AL = char -> EDX = 1 if [A-Za-z0-9_], else 0 (preserves AL)
    cmp     al, '_'
    je      .evic_yes
    cmp     al, '0'
    jb      .evic_no
    cmp     al, '9'
    jbe     .evic_yes
    cmp     al, 'A'
    jb      .evic_no
    cmp     al, 'Z'
    jbe     .evic_yes
    cmp     al, 'a'
    jb      .evic_no
    cmp     al, 'z'
    jbe     .evic_yes
.evic_no:
    xor     edx, edx
    ret
.evic_yes:
    mov     edx, 1
    ret

_pyfasm_ev_match_kw:
    ; RCX = kw_cstr, RSI = cursor -> EAX = 1 & advances RSI if exact keyword match
    xor     r8d, r8d
.evmk_lp:
    movzx   eax, byte [rcx + r8]
    test    al, al
    jz      .evmk_end
    cmp     al, byte [rsi + r8]
    jne     .evmk_no
    inc     r8
    jmp     .evmk_lp
.evmk_end:
    movzx   eax, byte [rsi + r8]
    call    _pyfasm_ev_is_ident_char
    test    edx, edx
    jnz     .evmk_no
    add     rsi, r8
    mov     eax, 1
    ret
.evmk_no:
    xor     eax, eax
    ret

_pyfasm_ev_str_eq:
    ; RCX = s1, RDX = s2 -> EAX = 1 if equal else 0
.evseq_lp:
    movzx   eax, byte [rcx]
    cmp     al, byte [rdx]
    jne     .evseq_no
    test    al, al
    jz      .evseq_yes
    inc     rcx
    inc     rdx
    jmp     .evseq_lp
.evseq_yes:
    mov     eax, 1
    ret
.evseq_no:
    xor     eax, eax
    ret

_pyfasm_ev_str_cmp:
    ; RCX = s1, RDX = s2 -> EAX = -1 (<), 0 (==), +1 (>)
.evsc_lp:
    movzx   eax, byte [rcx]
    movzx   r8d, byte [rdx]
    cmp     eax, r8d
    jb      .evsc_lt
    ja      .evsc_gt
    test    eax, eax
    jz      .evsc_eq
    inc     rcx
    inc     rdx
    jmp     .evsc_lp
.evsc_lt:
    mov     eax, -1
    ret
.evsc_gt:
    mov     eax, 1
    ret
.evsc_eq:
    xor     eax, eax
    ret

_pyfasm_ev_to_truthy:
    ; RCX = val, RDX = tag -> EAX = 0 or 1
    cmp     edx, 1
    je      .evtt_flt
    cmp     edx, 2
    je      .evtt_str
    cmp     edx, 4
    je      .evtt_false
    xor     eax, eax
    test    rcx, rcx
    setne   al
    ret
.evtt_flt:
    movq    xmm0, rcx
    xorpd   xmm1, xmm1
    ucomisd xmm0, xmm1
    jp      .evtt_true
    jne     .evtt_true
    xor     eax, eax
    ret
.evtt_str:
    test    rcx, rcx
    jz      .evtt_false
    cmp     byte [rcx], 0
    je      .evtt_false
.evtt_true:
    mov     eax, 1
    ret
.evtt_false:
    xor     eax, eax
    ret

_pyfasm_ev_to_f64_reg:
    ; RAX = val, EDX = tag -> XMM0 = double
    cmp     edx, 1
    je      .evtf0_flt
    cvtsi2sd xmm0, rax
    ret
.evtf0_flt:
    movq    xmm0, rax
    ret

; --- Recursive Descent Parser ---

_pyfasm_ev_expr:
_pyfasm_ev_or:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    call    _pyfasm_ev_and
    mov     rbx, rax
    mov     r12, rdx
.evor_lp:
    call    _pyfasm_ev_skip_ws
    lea     rcx, [_pyfasm_eval_kw_or]
    call    _pyfasm_ev_match_kw
    test    eax, eax
    jz      .evor_done
    call    _pyfasm_ev_and
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rcx, rbx
    mov     rdx, r12
    call    _pyfasm_ev_to_truthy
    test    eax, eax
    jnz     .evor_lp
    mov     rbx, r13
    mov     r12, [rsp + 32]
    jmp     .evor_lp
.evor_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_and:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    call    _pyfasm_ev_not
    mov     rbx, rax
    mov     r12, rdx
.evand_lp:
    call    _pyfasm_ev_skip_ws
    lea     rcx, [_pyfasm_eval_kw_and]
    call    _pyfasm_ev_match_kw
    test    eax, eax
    jz      .evand_done
    call    _pyfasm_ev_not
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rcx, rbx
    mov     rdx, r12
    call    _pyfasm_ev_to_truthy
    test    eax, eax
    jz      .evand_lp
    mov     rbx, r13
    mov     r12, [rsp + 32]
    jmp     .evand_lp
.evand_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_not:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_ev_skip_ws
    lea     rcx, [_pyfasm_eval_kw_not]
    call    _pyfasm_ev_match_kw
    test    eax, eax
    jz      .evnot_cmp
    call    _pyfasm_ev_not
    mov     rcx, rax
    call    _pyfasm_ev_to_truthy
    xor     eax, 1
    mov     edx, 3
    jmp     .evnot_done
.evnot_cmp:
    call    _pyfasm_ev_cmp
.evnot_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_cmp:
    ; op codes: 1='==', 2='!=', 3='<=', 4='>=', 5='<', 6='>'
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    call    _pyfasm_ev_bitor
    mov     rbx, rax
    mov     r12, rdx
    xor     r14d, r14d              ; r14 = matched any comparison
    mov     r15d, 1                 ; r15 = chained bool result
.evcmp_lp:
    call    _pyfasm_ev_skip_ws
    xor     r13d, r13d
    mov     al, byte [rsi]
    mov     ah, byte [rsi + 1]
    cmp     al, '='
    jne     .evcmp_c1
    cmp     ah, '='
    jne     .evcmp_done
    mov     r13d, 1
    add     rsi, 2
    jmp     .evcmp_rhs
.evcmp_c1:
    cmp     al, '!'
    jne     .evcmp_c2
    cmp     ah, '='
    jne     .evcmp_done
    mov     r13d, 2
    add     rsi, 2
    jmp     .evcmp_rhs
.evcmp_c2:
    cmp     al, '<'
    jne     .evcmp_c3
    cmp     ah, '='
    jne     .evcmp_lt
    mov     r13d, 3
    add     rsi, 2
    jmp     .evcmp_rhs
.evcmp_lt:
    mov     r13d, 5
    inc     rsi
    jmp     .evcmp_rhs
.evcmp_c3:
    cmp     al, '>'
    jne     .evcmp_done
    cmp     ah, '='
    jne     .evcmp_gt
    mov     r13d, 4
    add     rsi, 2
    jmp     .evcmp_rhs
.evcmp_gt:
    mov     r13d, 6
    inc     rsi

.evcmp_rhs:
    mov     r14d, 1
    call    _pyfasm_ev_bitor
    mov     [rsp + 32], rax         ; rhs val
    mov     [rsp + 40], rdx         ; rhs tag

    ; Check None or string comparisons
    cmp     r12d, 4
    je      .evcmp_none
    cmp     dword [rsp + 40], 4
    je      .evcmp_none
    cmp     r12d, 2
    je      .evcmp_str
    cmp     dword [rsp + 40], 2
    je      .evcmp_diff_type

    ; Numeric comparison (int/bool/f64)
    cmp     r12d, 1
    je      .evcmp_f64
    cmp     dword [rsp + 40], 1
    je      .evcmp_f64

    ; Both integer-compatible (int/bool)
    mov     rcx, [rsp + 32]
    xor     eax, eax
    cmp     r13d, 1
    je      .evci_eq
    cmp     r13d, 2
    je      .evci_ne
    cmp     r13d, 3
    je      .evci_le
    cmp     r13d, 4
    je      .evci_ge
    cmp     r13d, 5
    je      .evci_lt
    cmp     rbx, rcx
    setg    al
    jmp     .evcmp_comb
.evci_eq:
    cmp     rbx, rcx
    sete    al
    jmp     .evcmp_comb
.evci_ne:
    cmp     rbx, rcx
    setne   al
    jmp     .evcmp_comb
.evci_le:
    cmp     rbx, rcx
    setle   al
    jmp     .evcmp_comb
.evci_ge:
    cmp     rbx, rcx
    setge   al
    jmp     .evcmp_comb
.evci_lt:
    cmp     rbx, rcx
    setl    al
    jmp     .evcmp_comb

.evcmp_f64:
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0
    mov     rax, [rsp + 32]
    mov     edx, dword [rsp + 40]
    call    _pyfasm_ev_to_f64_reg
    ; xmm1 = lhs, xmm0 = rhs -> dispatch before ucomisd so EFLAGS stay intact
    xor     eax, eax
    cmp     r13d, 1
    je      .evcf_eq
    cmp     r13d, 2
    je      .evcf_ne
    cmp     r13d, 3
    je      .evcf_le
    cmp     r13d, 4
    je      .evcf_ge
    cmp     r13d, 5
    je      .evcf_lt
    ucomisd xmm1, xmm0
    jp      .evcf_nan_false
    seta    al
    jmp     .evcmp_comb
.evcf_eq:
    ucomisd xmm1, xmm0
    jp      .evcf_nan_false
    sete    al
    jmp     .evcmp_comb
.evcf_ne:
    ucomisd xmm1, xmm0
    jp      .evcf_nan_true
    setne   al
    jmp     .evcmp_comb
.evcf_le:
    ucomisd xmm1, xmm0
    jp      .evcf_nan_false
    setbe   al
    jmp     .evcmp_comb
.evcf_ge:
    ucomisd xmm1, xmm0
    jp      .evcf_nan_false
    setae   al
    jmp     .evcmp_comb
.evcf_lt:
    ucomisd xmm1, xmm0
    jp      .evcf_nan_false
    setb    al
    jmp     .evcmp_comb
.evcf_nan_true:
    mov     eax, 1
    jmp     .evcmp_comb
.evcf_nan_false:
    xor     eax, eax
    jmp     .evcmp_comb

.evcmp_str:
    cmp     dword [rsp + 40], 2
    jne     .evcmp_diff_type
    mov     rcx, rbx
    mov     rdx, [rsp + 32]
    call    _pyfasm_ev_str_cmp
    mov     ecx, eax
    xor     eax, eax
    cmp     r13d, 1
    je      .evcs_eq
    cmp     r13d, 2
    je      .evcs_ne
    cmp     r13d, 3
    je      .evcs_le
    cmp     r13d, 4
    je      .evcs_ge
    cmp     r13d, 5
    je      .evcs_lt
    test    ecx, ecx
    setg    al
    jmp     .evcmp_comb
.evcs_eq:
    test    ecx, ecx
    sete    al
    jmp     .evcmp_comb
.evcs_ne:
    test    ecx, ecx
    setne   al
    jmp     .evcmp_comb
.evcs_le:
    test    ecx, ecx
    setle   al
    jmp     .evcmp_comb
.evcs_ge:
    test    ecx, ecx
    setge   al
    jmp     .evcmp_comb
.evcs_lt:
    test    ecx, ecx
    setl    al
    jmp     .evcmp_comb

.evcmp_none:
    xor     eax, eax
    cmp     r12d, 4
    jne     .evcmp_diff_type
    cmp     dword [rsp + 40], 4
    jne     .evcmp_diff_type
    cmp     r13d, 1
    sete    al
    jmp     .evcmp_comb

.evcmp_diff_type:
    xor     eax, eax
    cmp     r13d, 2
    sete    al

.evcmp_comb:
    and     r15d, eax
    mov     rbx, [rsp + 32]
    mov     r12, [rsp + 40]
    jmp     .evcmp_lp

.evcmp_done:
    test    r14d, r14d
    jz      .evcmp_pass
    mov     eax, r15d
    mov     edx, 3
    jmp     .evcmp_ret
.evcmp_pass:
    mov     rax, rbx
    mov     rdx, r12
.evcmp_ret:
    lea     rsp, [rbp - 40]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_bitor:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_ev_bitxor
    mov     rbx, rax
    mov     r12, rdx
.evbo_lp:
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], '|'
    jne     .evbo_done
    inc     rsi
    call    _pyfasm_ev_bitxor
    or      rbx, rax
    xor     r12d, r12d
    jmp     .evbo_lp
.evbo_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_bitxor:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_ev_bitand
    mov     rbx, rax
    mov     r12, rdx
.evbx_lp:
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], '^'
    jne     .evbx_done
    inc     rsi
    call    _pyfasm_ev_bitand
    xor     rbx, rax
    xor     r12d, r12d
    jmp     .evbx_lp
.evbx_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_bitand:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_ev_shift
    mov     rbx, rax
    mov     r12, rdx
.evba_lp:
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], '&'
    jne     .evba_done
    inc     rsi
    call    _pyfasm_ev_shift
    and     rbx, rax
    xor     r12d, r12d
    jmp     .evba_lp
.evba_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_shift:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16
    call    _pyfasm_ev_add
    mov     rbx, rax
    mov     r12, rdx
.evsh_lp:
    call    _pyfasm_ev_skip_ws
    mov     al, byte [rsi]
    cmp     al, '<'
    jne     .evsh_r
    cmp     byte [rsi + 1], '<'
    jne     .evsh_done
    add     rsi, 2
    call    _pyfasm_ev_add
    mov     rcx, rax
    shl     rbx, cl
    xor     r12d, r12d
    jmp     .evsh_lp
.evsh_r:
    cmp     al, '>'
    jne     .evsh_done
    cmp     byte [rsi + 1], '>'
    jne     .evsh_done
    add     rsi, 2
    call    _pyfasm_ev_add
    mov     rcx, rax
    sar     rbx, cl
    xor     r12d, r12d
    jmp     .evsh_lp
.evsh_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_add:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    call    _pyfasm_ev_mul
    mov     rbx, rax
    mov     r12, rdx
.evadd_lp:
    call    _pyfasm_ev_skip_ws
    mov     al, byte [rsi]
    cmp     al, '+'
    je      .evadd_plus
    cmp     al, '-'
    je      .evadd_minus
    jmp     .evadd_done

.evadd_plus:
    inc     rsi
    call    _pyfasm_ev_mul
    cmp     r12d, 2
    jne     .evadd_pnum
    cmp     edx, 2
    jne     .evadd_lp
    mov     rcx, rbx
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     rbx, rax
    mov     r12d, 2
    jmp     .evadd_lp
.evadd_pnum:
    cmp     r12d, 1
    je      .evadd_pflt
    cmp     edx, 1
    je      .evadd_pflt
    add     rbx, rax
    xor     r12d, r12d
    jmp     .evadd_lp
.evadd_pflt:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    addsd   xmm1, xmm0
    movq    rbx, xmm1
    mov     r12d, 1
    jmp     .evadd_lp

.evadd_minus:
    inc     rsi
    call    _pyfasm_ev_mul
    cmp     r12d, 1
    je      .evadd_mflt
    cmp     edx, 1
    je      .evadd_mflt
    sub     rbx, rax
    xor     r12d, r12d
    jmp     .evadd_lp
.evadd_mflt:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    subsd   xmm1, xmm0
    movq    rbx, xmm1
    mov     r12d, 1
    jmp     .evadd_lp

.evadd_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_str_repeat:
    ; RCX = str_ptr, RDX = count -> RAX = newly allocated str_ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16

    mov     rbx, rcx                ; s
    mov     r12, rdx                ; count
    cmp     r12, 0
    jg      .evsr_len
    lea     rax, [_pyfasm_eval_str_empty]
    jmp     .evsr_done
.evsr_len:
    mov     rcx, rbx
    call    _pyfasm_str_len
    mov     rsi, rax                ; item_len
    imul    rax, r12
    inc     rax
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax                ; dst
    push    rax
.evsr_outer:
    test    r12, r12
    jz      .evsr_end
    mov     rcx, rsi
    push    rsi
    mov     rsi, rbx
    rep     movsb
    pop     rsi
    dec     r12
    jmp     .evsr_outer
.evsr_end:
    mov     byte [rdi], 0
    pop     rax
.evsr_done:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_mul:
    ; op: 1='*', 2='//', 3='/', 4='%'
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    call    _pyfasm_ev_unary
    mov     rbx, rax
    mov     r12, rdx
.evmul_lp:
    call    _pyfasm_ev_skip_ws
    mov     al, byte [rsi]
    cmp     al, '*'
    jne     .evmul_chk_div
    cmp     byte [rsi + 1], '*'
    je      .evmul_done             ; leave ** cleanly? pow already bound tighter!
    inc     rsi
    mov     r13d, 1
    jmp     .evmul_rhs
.evmul_chk_div:
    cmp     al, '/'
    jne     .evmul_chk_mod
    cmp     byte [rsi + 1], '/'
    jne     .evmul_truediv
    add     rsi, 2
    mov     r13d, 2
    jmp     .evmul_rhs
.evmul_truediv:
    inc     rsi
    mov     r13d, 3
    jmp     .evmul_rhs
.evmul_chk_mod:
    cmp     al, '%'
    jne     .evmul_done
    inc     rsi
    mov     r13d, 4

.evmul_rhs:
    call    _pyfasm_ev_unary
    cmp     r13d, 1
    je      .evmul_do_star
    cmp     r13d, 3
    je      .evmul_do_tdiv
    cmp     r13d, 2
    je      .evmul_do_fdiv

    ; % modulo
    cmp     r12d, 1
    je      .evmul_fmod
    cmp     edx, 1
    je      .evmul_fmod
    test    rax, rax
    jz      .evmul_divzero
    mov     rcx, rax
    mov     rax, rbx
    cqo
    idiv    rcx                     ; RDX = rem
    test    rdx, rdx
    jz      .evmul_mod_ok
    mov     rax, rdx
    xor     rax, rcx
    jns     .evmul_mod_ok
    add     rdx, rcx
.evmul_mod_ok:
    mov     rbx, rdx
    xor     r12d, r12d
    jmp     .evmul_lp

.evmul_fmod:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm2, xmm0              ; lhs
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm3, xmm0              ; rhs
    movsd   xmm0, xmm2
    divsd   xmm0, xmm3
    movq    rcx, xmm0
    sub     rsp, 48
    movsd   [rsp + 32], xmm2
    movsd   [rsp + 40], xmm3
    call    _pyfasm_math_floor_f64
    movsd   xmm2, [rsp + 32]
    movsd   xmm3, [rsp + 40]
    add     rsp, 48
    movq    xmm0, rax
    mulsd   xmm0, xmm3
    subsd   xmm2, xmm0
    movq    rbx, xmm2
    mov     r12d, 1
    jmp     .evmul_lp

.evmul_do_fdiv:
    cmp     r12d, 1
    je      .evmul_ffdiv
    cmp     edx, 1
    je      .evmul_ffdiv
    test    rax, rax
    jz      .evmul_divzero
    mov     rcx, rax
    mov     rax, rbx
    cqo
    idiv    rcx                     ; RAX = q, RDX = rem
    test    rdx, rdx
    jz      .evmul_fd_ok
    mov     r8, rdx
    xor     r8, rcx
    jns     .evmul_fd_ok
    dec     rax
.evmul_fd_ok:
    mov     rbx, rax
    xor     r12d, r12d
    jmp     .evmul_lp

.evmul_ffdiv:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    divsd   xmm1, xmm0
    movq    rcx, xmm1
    call    _pyfasm_math_floor_f64
    mov     rbx, rax
    mov     r12d, 1
    jmp     .evmul_lp

.evmul_divzero:
    xor     ebx, ebx
    xor     r12d, r12d
    jmp     .evmul_lp

.evmul_do_tdiv:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    divsd   xmm1, xmm0
    movq    rbx, xmm1
    mov     r12d, 1
    jmp     .evmul_lp

.evmul_do_star:
    cmp     r12d, 2
    jne     .evmul_chk_rstr
    mov     rcx, rbx
    mov     rdx, rax
    call    _pyfasm_ev_str_repeat
    mov     rbx, rax
    mov     r12d, 2
    jmp     .evmul_lp
.evmul_chk_rstr:
    cmp     edx, 2
    jne     .evmul_mnum
    mov     rcx, rax
    mov     rdx, rbx
    call    _pyfasm_ev_str_repeat
    mov     rbx, rax
    mov     r12d, 2
    jmp     .evmul_lp
.evmul_mnum:
    cmp     r12d, 1
    je      .evmul_mflt
    cmp     edx, 1
    je      .evmul_mflt
    imul    rbx, rax
    xor     r12d, r12d
    jmp     .evmul_lp
.evmul_mflt:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    mulsd   xmm1, xmm0
    movq    rbx, xmm1
    mov     r12d, 1
    jmp     .evmul_lp

.evmul_done:
    mov     rax, rbx
    mov     rdx, r12
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_unary:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_ev_skip_ws
    mov     al, byte [rsi]
    cmp     al, '+'
    jne     .evu_neg
    inc     rsi
    call    _pyfasm_ev_unary
    jmp     .evu_done
.evu_neg:
    cmp     al, '-'
    jne     .evu_inv
    inc     rsi
    call    _pyfasm_ev_unary
    cmp     edx, 1
    je      .evu_fneg
    neg     rax
    xor     edx, edx
    jmp     .evu_done
.evu_fneg:
    mov     rcx, [_pyfasm_flt_sign_mask]
    xor     rax, rcx
    jmp     .evu_done
.evu_inv:
    cmp     al, '~'
    jne     .evu_pow
    inc     rsi
    call    _pyfasm_ev_unary
    not     rax
    xor     edx, edx
    jmp     .evu_done
.evu_pow:
    call    _pyfasm_ev_pow
.evu_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_pow:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    call    _pyfasm_ev_atom
    mov     rbx, rax
    mov     r12, rdx
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], '*'
    jne     .evpw_ret
    cmp     byte [rsi + 1], '*'
    jne     .evpw_ret
    add     rsi, 2
    call    _pyfasm_ev_unary
    cmp     r12d, 1
    je      .evpw_flt
    cmp     edx, 1
    je      .evpw_flt
    cmp     rax, 0
    jl      .evpw_flt
    ; Integer non-negative exponentiation
    mov     rcx, rax
    mov     rax, 1
    mov     r8, rbx
.evpw_ilp:
    test    rcx, rcx
    jz      .evpw_iok
    test    rcx, 1
    jz      .evpw_isq
    imul    rax, r8
.evpw_isq:
    imul    r8, r8
    shr     rcx, 1
    jmp     .evpw_ilp
.evpw_iok:
    xor     edx, edx
    jmp     .evpw_exit

.evpw_flt:
    mov     r13, rax
    mov     [rsp + 32], rdx
    mov     rax, rbx
    mov     edx, r12d
    call    _pyfasm_ev_to_f64_reg
    movq    rbx, xmm0               ; x_f64
    mov     rax, r13
    mov     edx, dword [rsp + 32]
    call    _pyfasm_ev_to_f64_reg
    movq    rdx, xmm0               ; y_f64
    mov     rcx, rbx
    call    _pyfasm_math_pow_f64
    mov     edx, 1
    jmp     .evpw_exit

.evpw_ret:
    mov     rax, rbx
    mov     rdx, r12
.evpw_exit:
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_parse_string:
    ; RSI points to opening quote (' or ") -> RAX = str_ptr, EDX = 2
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    push    r12
    push    r13
    sub     rsp, 32
    and     rsp, -16

    movzx   r12d, byte [rsi]        ; quote char
    inc     rsi
    mov     r13, rsi                ; save start for pass 1 length scan
    xor     ebx, ebx
.evps_scan:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .evps_alloc
    cmp     al, r12b
    je      .evps_alloc
    inc     rsi
    cmp     al, '\'
    jne     .evps_inc
    cmp     byte [rsi], 0
    je      .evps_alloc
    inc     rsi
.evps_inc:
    inc     ebx
    jmp     .evps_scan

.evps_alloc:
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax
    mov     rsi, r13
.evps_copy:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .evps_end
    cmp     al, r12b
    je      .evps_close
    inc     rsi
    cmp     al, '\'
    jne     .evps_store
    movzx   ecx, byte [rsi]
    test    cl, cl
    jz      .evps_end
    inc     rsi
    cmp     cl, 'n'
    jne     .evps_et
    mov     al, 10
    jmp     .evps_store
.evps_et:
    cmp     cl, 't'
    jne     .evps_er
    mov     al, 9
    jmp     .evps_store
.evps_er:
    cmp     cl, 'r'
    jne     .evps_ec
    mov     al, 13
    jmp     .evps_store
.evps_ec:
    mov     al, cl
.evps_store:
    mov     byte [rdi], al
    inc     rdi
    jmp     .evps_copy
.evps_close:
    inc     rsi
.evps_end:
    mov     byte [rdi], 0
    pop     rax
    mov     edx, 2
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_parse_number:
    ; RSI cursor at digit or '.' -> RAX = val (int64 or f64), EDX = 0 or 1
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    xor     ebx, ebx                ; int accumulator
    xorpd   xmm0, xmm0              ; float accumulator
    xor     r12d, r12d              ; r12d = is_float

    cmp     byte [rsi], '0'
    jne     .evpn_dec
    movzx   eax, byte [rsi + 1]
    or      al, 32
    cmp     al, 'x'
    je      .evpn_hex
    cmp     al, 'b'
    je      .evpn_bin
    cmp     al, 'o'
    je      .evpn_oct
    jmp     .evpn_dec

.evpn_hex:
    add     rsi, 2
.evpn_hlp:
    movzx   eax, byte [rsi]
    cmp     al, '_'
    je      .evpn_hnx
    cmp     al, '0'
    jb      .evpn_int_ret
    cmp     al, '9'
    jbe     .evpn_hd
    or      al, 32
    cmp     al, 'a'
    jb      .evpn_int_ret
    cmp     al, 'f'
    ja      .evpn_int_ret
    sub     eax, ('a' - 10)
    jmp     .evpn_hadd
.evpn_hd:
    sub     eax, '0'
.evpn_hadd:
    shl     rbx, 4
    add     rbx, rax
.evpn_hnx:
    inc     rsi
    jmp     .evpn_hlp

.evpn_bin:
    add     rsi, 2
.evpn_blp:
    movzx   eax, byte [rsi]
    cmp     al, '_'
    je      .evpn_bnx
    cmp     al, '0'
    jb      .evpn_int_ret
    cmp     al, '1'
    ja      .evpn_int_ret
    sub     eax, '0'
    shl     rbx, 1
    add     rbx, rax
.evpn_bnx:
    inc     rsi
    jmp     .evpn_blp

.evpn_oct:
    add     rsi, 2
.evpn_olp:
    movzx   eax, byte [rsi]
    cmp     al, '_'
    je      .evpn_onx
    cmp     al, '0'
    jb      .evpn_int_ret
    cmp     al, '7'
    ja      .evpn_int_ret
    sub     eax, '0'
    shl     rbx, 3
    add     rbx, rax
.evpn_onx:
    inc     rsi
    jmp     .evpn_olp

.evpn_dec:
    movsd   xmm2, [_pyfasm_flt_ten]
.evpn_dlp:
    movzx   eax, byte [rsi]
    cmp     al, '_'
    je      .evpn_dnx
    cmp     al, '0'
    jb      .evpn_chk_dot
    cmp     al, '9'
    ja      .evpn_chk_dot
    sub     eax, '0'
    imul    rbx, 10
    add     rbx, rax
    mulsd   xmm0, xmm2
    cvtsi2sd xmm1, eax
    addsd   xmm0, xmm1
.evpn_dnx:
    inc     rsi
    jmp     .evpn_dlp

.evpn_chk_dot:
    cmp     byte [rsi], '.'
    jne     .evpn_chk_exp
    mov     r12d, 1
    inc     rsi
    movsd   xmm3, [_pyfasm_flt_ten]
.evpn_flp:
    movzx   eax, byte [rsi]
    cmp     al, '_'
    je      .evpn_fnx
    cmp     al, '0'
    jb      .evpn_chk_exp
    cmp     al, '9'
    ja      .evpn_chk_exp
    sub     eax, '0'
    cvtsi2sd xmm1, eax
    divsd   xmm1, xmm3
    addsd   xmm0, xmm1
    mulsd   xmm3, xmm2
.evpn_fnx:
    inc     rsi
    jmp     .evpn_flp

.evpn_chk_exp:
    movzx   eax, byte [rsi]
    or      al, 32
    cmp     al, 'e'
    jne     .evpn_finish
    mov     r12d, 1
    inc     rsi
    xor     r13d, r13d              ; exp sign (0=+, 1=-)
    cmp     byte [rsi], '-'
    jne     .evpn_ep
    mov     r13d, 1
    inc     rsi
    jmp     .evpn_edig
.evpn_ep:
    cmp     byte [rsi], '+'
    jne     .evpn_edig
    inc     rsi
.evpn_edig:
    xor     ecx, ecx
.evpn_elp:
    movzx   eax, byte [rsi]
    cmp     al, '0'
    jb      .evpn_escale
    cmp     al, '9'
    ja      .evpn_escale
    sub     eax, '0'
    imul    ecx, 10
    add     ecx, eax
    inc     rsi
    jmp     .evpn_elp
.evpn_escale:
    movsd   xmm2, [_pyfasm_flt_ten]
.evpn_eslp:
    test    ecx, ecx
    jz      .evpn_finish
    test    r13d, r13d
    jnz     .evpn_ediv
    mulsd   xmm0, xmm2
    jmp     .evpn_edec
.evpn_ediv:
    divsd   xmm0, xmm2
.evpn_edec:
    dec     ecx
    jmp     .evpn_eslp

.evpn_finish:
    test    r12d, r12d
    jz      .evpn_int_ret
    movq    rax, xmm0
    mov     edx, 1
    jmp     .evpn_ret
.evpn_int_ret:
    mov     rax, rbx
    xor     edx, edx
.evpn_ret:
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ev_atom:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    push    r12
    push    r13
    push    r14
    ; [rsp+32..95]: ident buf (64B), [rsp+96..223]: up to 8 args * 16B (val, tag)
    sub     rsp, 240
    and     rsp, -16

    call    _pyfasm_ev_skip_ws
    movzx   eax, byte [rsi]
    test    al, al
    jz      .eva_zero

    cmp     al, '('
    jne     .eva_chk_str
    inc     rsi
    call    _pyfasm_ev_expr
    push    rax
    push    rdx
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], ')'
    jne     .eva_paren_done
    inc     rsi
.eva_paren_done:
    pop     rdx
    pop     rax
    jmp     .eva_ret

.eva_chk_str:
    cmp     al, 39                  ; '\''
    je      .eva_str
    cmp     al, '"'
    jne     .eva_chk_num
.eva_str:
    call    _pyfasm_ev_parse_string
    jmp     .eva_ret

.eva_chk_num:
    cmp     al, '.'
    je      .eva_num
    cmp     al, '0'
    jb      .eva_chk_ident
    cmp     al, '9'
    ja      .eva_chk_ident
.eva_num:
    call    _pyfasm_ev_parse_number
    jmp     .eva_ret

.eva_chk_ident:
    cmp     al, '_'
    je      .eva_ident
    mov     ecx, eax
    or      cl, 32
    cmp     cl, 'a'
    jb      .eva_zero
    cmp     cl, 'z'
    ja      .eva_zero

.eva_ident:
    lea     r12, [rsp + 32]         ; ident buffer
    xor     ebx, ebx
.eva_id_lp:
    movzx   eax, byte [rsi]
    call    _pyfasm_ev_is_ident_char
    test    edx, edx
    jz      .eva_id_end
    cmp     ebx, 62
    jge     .eva_id_skip
    mov     byte [r12 + rbx], al
    inc     ebx
.eva_id_skip:
    inc     rsi
    jmp     .eva_id_lp
.eva_id_end:
    mov     byte [r12 + rbx], 0

    ; Allow optional `math.` prefix
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_math]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_chk_consts
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], '.'
    jne     .eva_chk_consts
    inc     rsi
    call    _pyfasm_ev_skip_ws
    xor     ebx, ebx
.eva_mid_lp:
    movzx   eax, byte [rsi]
    call    _pyfasm_ev_is_ident_char
    test    edx, edx
    jz      .eva_mid_end
    cmp     ebx, 62
    jge     .eva_mid_skip
    mov     byte [r12 + rbx], al
    inc     ebx
.eva_mid_skip:
    inc     rsi
    jmp     .eva_mid_lp
.eva_mid_end:
    mov     byte [r12 + rbx], 0

.eva_chk_consts:
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], '('
    je      .eva_func_call

    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_true]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_false
    mov     eax, 1
    mov     edx, 3
    jmp     .eva_ret
.eva_c_false:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_false]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_none
    xor     eax, eax
    mov     edx, 3
    jmp     .eva_ret
.eva_c_none:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_none]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_pi
    xor     eax, eax
    mov     edx, 4
    jmp     .eva_ret
.eva_c_pi:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_pi]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_e
    mov     rax, [_pyfasm_flt_pi]
    mov     edx, 1
    jmp     .eva_ret
.eva_c_e:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_e]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_tau
    mov     rax, [_pyfasm_eval_e]
    mov     edx, 1
    jmp     .eva_ret
.eva_c_tau:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_tau]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_inf
    mov     rax, [_pyfasm_eval_tau]
    mov     edx, 1
    jmp     .eva_ret
.eva_c_inf:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_inf]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_c_nan
    mov     rax, [_pyfasm_flt_inf]
    mov     edx, 1
    jmp     .eva_ret
.eva_c_nan:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_nan]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_zero
    mov     rax, [_pyfasm_flt_nan]
    mov     edx, 1
    jmp     .eva_ret

.eva_func_call:
    inc     rsi                     ; consume '('
    xor     r13d, r13d              ; r13 = argc
    lea     r14, [rsp + 96]         ; args array: 8 slots of (val, tag)
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], ')'
    je      .eva_args_done
.eva_arg_lp:
    call    _pyfasm_ev_expr
    cmp     r13d, 8
    jge     .eva_arg_next
    mov     rcx, r13
    shl     rcx, 4
    mov     [r14 + rcx + 0], rax
    mov     [r14 + rcx + 8], rdx
    inc     r13d
.eva_arg_next:
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], ','
    jne     .eva_args_done
    inc     rsi
    call    _pyfasm_ev_skip_ws
    cmp     byte [rsi], ')'
    jne     .eva_arg_lp
.eva_args_done:
    cmp     byte [rsi], ')'
    jne     .eva_dispatch
    inc     rsi

.eva_dispatch:
    ; abs(x)
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_abs]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_int
    test    r13d, r13d
    jz      .eva_zero
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    cmp     edx, 1
    je      .evf_abs_f
    test    rax, rax
    jns     .evf_abs_id
    neg     rax
.evf_abs_id:
    xor     edx, edx
    jmp     .eva_ret
.evf_abs_f:
    and     rax, qword [_pyfasm_flt_abs_mask]
    mov     edx, 1
    jmp     .eva_ret

.evf_int:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_int]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_float
    test    r13d, r13d
    jz      .eva_zero
    mov     rcx, [r14 + 0]
    mov     rdx, [r14 + 8]
    call    _pyfasm_eval_to_int
    xor     edx, edx
    jmp     .eva_ret

.evf_float:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_float]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_str
    xor     eax, eax
    mov     edx, 1
    test    r13d, r13d
    jz      .eva_ret
    mov     rcx, [r14 + 0]
    mov     rdx, [r14 + 8]
    call    _pyfasm_eval_to_float
    mov     edx, 1
    jmp     .eva_ret

.evf_str:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_str]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_bool
    test    r13d, r13d
    jnz     .evf_str_arg
    lea     rax, [_pyfasm_eval_str_empty]
    mov     edx, 2
    jmp     .eva_ret
.evf_str_arg:
    mov     rcx, [r14 + 0]
    mov     rdx, [r14 + 8]
    call    _pyfasm_eval_to_str
    mov     edx, 2
    jmp     .eva_ret

.evf_bool:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_bool]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_len
    xor     eax, eax
    mov     edx, 3
    test    r13d, r13d
    jz      .eva_ret
    mov     rcx, [r14 + 0]
    mov     rdx, [r14 + 8]
    call    _pyfasm_ev_to_truthy
    mov     edx, 3
    jmp     .eva_ret

.evf_len:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_len]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_round
    test    r13d, r13d
    jz      .eva_zero
    cmp     dword [r14 + 8], 2
    jne     .eva_zero
    mov     rcx, [r14 + 0]
    call    _pyfasm_str_len
    xor     edx, edx
    jmp     .eva_ret

.evf_round:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_round]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_pow
    test    r13d, r13d
    jz      .eva_zero
    cmp     r13d, 1
    ja      .evf_round_nd
    cmp     dword [r14 + 8], 1
    jne     .evf_round_i1
    mov     rcx, [r14 + 0]
    mov     [rsp + 224], rcx
    fninit
    fld     qword [rsp + 224]
    frndint
    fistp   qword [rsp + 224]
    mov     rax, [rsp + 224]
    xor     edx, edx
    jmp     .eva_ret
.evf_round_i1:
    mov     rax, [r14 + 0]
    xor     edx, edx
    jmp     .eva_ret
.evf_round_nd:
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, [_pyfasm_flt_one]
    movsd   xmm2, [_pyfasm_flt_ten]
    mov     rcx, [r14 + 16]
    cmp     rcx, 0
    jl      .evf_rnd_neg
.evf_rnd_p:
    test    rcx, rcx
    jz      .evf_rnd_app
    mulsd   xmm1, xmm2
    dec     rcx
    jmp     .evf_rnd_p
.evf_rnd_neg:
    neg     rcx
.evf_rnd_nlp:
    test    rcx, rcx
    jz      .evf_rnd_app
    divsd   xmm1, xmm2
    dec     rcx
    jmp     .evf_rnd_nlp
.evf_rnd_app:
    mulsd   xmm0, xmm1
    movq    qword [rsp + 224], xmm0
    movq    qword [rsp + 232], xmm1
    fninit
    fld     qword [rsp + 224]
    frndint
    fdiv    qword [rsp + 232]
    fstp    qword [rsp + 224]
    mov     rax, [rsp + 224]
    mov     edx, 1
    jmp     .eva_ret

.evf_pow:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_pow]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_minmax
    cmp     r13d, 2
    jl      .eva_zero
    cmp     dword [r14 + 8], 1
    je      .evf_pow_f
    cmp     dword [r14 + 24], 1
    je      .evf_pow_f
    mov     rcx, [r14 + 16]
    cmp     rcx, 0
    jl      .evf_pow_f
    mov     r8, [r14 + 0]
    mov     rax, 1
.evf_pow_ilp:
    test    rcx, rcx
    jz      .evf_pow_modchk
    test    rcx, 1
    jz      .evf_pow_isq
    imul    rax, r8
.evf_pow_isq:
    imul    r8, r8
    shr     rcx, 1
    jmp     .evf_pow_ilp
.evf_pow_modchk:
    cmp     r13d, 3
    jl      .evf_pow_iret
    mov     rcx, [r14 + 32]
    test    rcx, rcx
    jz      .eva_zero
    cqo
    idiv    rcx
    mov     rax, rdx
.evf_pow_iret:
    xor     edx, edx
    jmp     .eva_ret
.evf_pow_f:
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    movq    rbx, xmm0
    mov     rax, [r14 + 16]
    mov     edx, dword [r14 + 24]
    call    _pyfasm_ev_to_f64_reg
    movq    rdx, xmm0
    mov     rcx, rbx
    call    _pyfasm_math_pow_f64
    mov     edx, 1
    jmp     .eva_ret

.evf_minmax:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_min]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_chk_max
    xor     edi, edi                ; edi = 0 (min)
    jmp     .evf_mm_run
.evf_chk_max:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_max]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_sqrt
    mov     edi, 1                  ; edi = 1 (max)

.evf_mm_run:
    test    r13d, r13d
    jz      .eva_zero
    mov     rbx, [r14 + 0]
    mov     rdx, [r14 + 8]          ; rdx-safe? Save tag in [rsp+224]!
    mov     [rsp + 224], rdx
    mov     ecx, 1
.evf_mm_lp:
    cmp     ecx, r13d
    jge     .evf_mm_done
    mov     r8, rcx
    shl     r8, 4
    mov     r9, [r14 + r8 + 0]      ; cand val
    mov     r10, [r14 + r8 + 8]     ; cand tag
    cmp     qword [rsp + 224], 1
    je      .evf_mm_flt
    cmp     r10d, 1
    je      .evf_mm_flt
    cmp     edi, 0
    jne     .evf_mm_imax
    cmp     r9, rbx
    jge     .evf_mm_nx
    mov     rbx, r9
    mov     [rsp + 224], r10
    jmp     .evf_mm_nx
.evf_mm_imax:
    cmp     r9, rbx
    jle     .evf_mm_nx
    mov     rbx, r9
    mov     [rsp + 224], r10
    jmp     .evf_mm_nx
.evf_mm_flt:
    mov     rax, rbx
    mov     edx, dword [rsp + 224]
    call    _pyfasm_ev_to_f64_reg
    movsd   xmm1, xmm0              ; best
    mov     rax, r9
    mov     edx, r10d
    call    _pyfasm_ev_to_f64_reg   ; xmm0 = cand
    cmp     edi, 0
    jne     .evf_mm_fmax
    ucomisd xmm0, xmm1
    jae     .evf_mm_nx
    movq    rbx, xmm0
    mov     qword [rsp + 224], 1
    jmp     .evf_mm_nx
.evf_mm_fmax:
    ucomisd xmm0, xmm1
    jbe     .evf_mm_nx
    movq    rbx, xmm0
    mov     qword [rsp + 224], 1
.evf_mm_nx:
    inc     ecx
    jmp     .evf_mm_lp
.evf_mm_done:
    mov     rax, rbx
    mov     rdx, [rsp + 224]
    jmp     .eva_ret

.evf_sqrt:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_sqrt]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_sin
    test    r13d, r13d
    jz      .eva_zero
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    sqrtsd  xmm0, xmm0
    movq    rax, xmm0
    mov     edx, 1
    jmp     .eva_ret

.evf_sin:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_sin]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_cos
    lea     rbx, [_pyfasm_math_sin]
    jmp     .evf_call_f64_1

.evf_cos:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_cos]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_tan
    lea     rbx, [_pyfasm_math_cos]
    jmp     .evf_call_f64_1

.evf_tan:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_tan]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_exp
    lea     rbx, [_pyfasm_math_tan]
    jmp     .evf_call_f64_1

.evf_exp:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_exp]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_log
    lea     rbx, [_pyfasm_math_exp]
    jmp     .evf_call_f64_1

.evf_log:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_log]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_log10
    lea     rbx, [_pyfasm_math_log]
    jmp     .evf_call_f64_1

.evf_log10:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_log10]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_floor
    lea     rbx, [_pyfasm_math_log10]
    jmp     .evf_call_f64_1

.evf_floor:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_floor]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_ceil
    test    r13d, r13d
    jz      .eva_zero
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    movq    rcx, xmm0
    call    _pyfasm_math_floor_f64
    movq    xmm0, rax
    cvttsd2si rax, xmm0
    xor     edx, edx
    jmp     .eva_ret

.evf_ceil:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_ceil]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .evf_atan2
    test    r13d, r13d
    jz      .eva_zero
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    movq    rcx, xmm0
    call    _pyfasm_math_ceil_f64
    movq    xmm0, rax
    cvttsd2si rax, xmm0
    xor     edx, edx
    jmp     .eva_ret

.evf_atan2:
    mov     rcx, r12
    lea     rdx, [_pyfasm_eval_kw_atan2]
    call    _pyfasm_ev_str_eq
    test    eax, eax
    jz      .eva_zero
    cmp     r13d, 2
    jl      .eva_zero
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    movq    rbx, xmm0
    mov     rax, [r14 + 16]
    mov     edx, dword [r14 + 24]
    call    _pyfasm_ev_to_f64_reg
    movq    rdx, xmm0
    mov     rcx, rbx
    call    _pyfasm_math_atan2
    mov     edx, 1
    jmp     .eva_ret

.evf_call_f64_1:
    test    r13d, r13d
    jz      .eva_zero
    mov     rax, [r14 + 0]
    mov     edx, dword [r14 + 8]
    call    _pyfasm_ev_to_f64_reg
    movq    rcx, xmm0
    call    rbx
    mov     edx, 1
    jmp     .eva_ret

.eva_zero:
    xor     eax, eax
    xor     edx, edx
.eva_ret:
    lea     rsp, [rbp - 40]
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
"""
