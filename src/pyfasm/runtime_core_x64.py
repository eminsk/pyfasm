# -*- coding: utf-8 -*-
"""
Portable x86-64 Core Runtime for PyFASM (Shared across Win64, Linux, macOS, MyOS).
Implements authentic IEEE-754 math, complex arithmetic, vectorized 1D/2D NumPy ops,
generator draining, dynamic attribute lookup, string strip(chars), and e/E/f/g formatting.
All functions strictly adhere to the Microsoft x64 ABI (RCX, RDX, R8, R9) and stack alignment rules.
"""


from .runtime_eval_x64 import get_eval_x64_code, get_eval_x64_data


def get_core_x64_data() -> str:
    return r"""
    align 8
    _pyfasm_cmplx_tag       dq 505946434D504C58h
    _pyfasm_flt_half        dq 3FE0000000000000h ; 0.5
    _pyfasm_flt_one         dq 3FF0000000000000h ; 1.0
    _pyfasm_flt_neg_one     dq 0BFF0000000000000h ; -1.0
    _pyfasm_flt_two         dq 4000000000000000h ; 2.0
    _pyfasm_flt_ten         dq 4024000000000000h ; 10.0
    _pyfasm_flt_inf         dq 7FF0000000000000h ; +inf
    _pyfasm_flt_ninf        dq 0FFF0000000000000h ; -inf
    _pyfasm_flt_nan         dq 7FF8000000000000h ; NaN
    _pyfasm_flt_abs_mask    dq 7FFFFFFFFFFFFFFFh
    _pyfasm_flt_sign_mask   dq 8000000000000000h
    _pyfasm_flt_pi          dq 400921FB54442D18h
    _pyfasm_flt_two_pi      dq 401921FB54442D18h
    _pyfasm_flt_exp_max     dq 40862E42FEFA39EFh ; ~709.7827
    _pyfasm_flt_exp_min     dq 0C0874910D52D3051h ; ~-745.1332
    _pyfasm_flt_1e_9        dq 3E112E0BE826D695h ; 1e-9
    _pyfasm_flt_1e15        dq 430C6BF526340000h ; 1e15
    _pyfasm_rand_state      dq 0
    _pyfasm_str_j           db 'j', 0
    _pyfasm_str_plus        db '+', 0
    _pyfasm_str_real_key    db 'real', 0
    _pyfasm_str_imag_key    db 'imag', 0
    _pyfasm_str_inf_lo      db 'inf', 0
    _pyfasm_str_ninf_lo     db '-inf', 0
    _pyfasm_str_nan_lo      db 'nan', 0
    _pyfasm_str_inf_up      db 'INF', 0
    _pyfasm_str_ninf_up     db '-INF', 0
    _pyfasm_str_nan_up      db 'NAN', 0
    align 8
    _pyfasm_attr_table_ptr  dq 0
    _pyfasm_dyn_attrs_head  dq 0
""" + get_eval_x64_data()


def get_core_x64_code() -> str:
    return r"""
; ============================================================
; Generator Draining & Slice Assignment
; ============================================================
_pyfasm_gen_to_list:
    ; RCX = gen_ptr -> RAX = newly allocated heap list of yielded elements
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .gtl_empty
    cmp     rcx, 65536
    jb      .gtl_empty

    ; If pointer looks like an already-materialized list rather than a gen frame,
    ; distinguish: generated gen frame has step_fn code ptr at [rcx+8] & done flag 0/1 at [rcx+16].
    mov     r12, rcx                ; r12 = gen_ptr
    mov     r13, 64                 ; r13 = temp buffer capacity (elements)
    xor     r14d, r14d              ; r14 = element count
    mov     rcx, 512                ; 64 * 8 bytes
    call    _pyfasm_alloc
    mov     r15, rax                ; r15 = temp buffer

.gtl_loop:
    cmp     qword [r12 + 16], 1
    je      .gtl_build
    mov     rcx, r12
    call    _pyfasm_gen_next
    cmp     qword [r12 + 16], 1
    je      .gtl_build
    mov     rbx, rax                ; yielded item

    cmp     r14, r13
    jl      .gtl_store
    ; Grow buffer: new_cap = r13 * 2
    lea     rcx, [r13 * 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     rsi, r15
    mov     rcx, r14
    rep     movsq
    mov     r15, rax
    shl     r13, 1

.gtl_store:
    mov     [r15 + r14 * 8], rbx
    inc     r14
    jmp     .gtl_loop

.gtl_build:
    mov     rcx, r14
    cmp     rcx, 16
    jge     .gtl_alloc_list
    mov     ecx, 16
.gtl_alloc_list:
    call    _pyfasm_list_create
    mov     [rax], r14
    lea     rdi, [rax + 8]
    mov     rsi, r15
    mov     rcx, r14
    rep     movsq
    jmp     .gtl_done

.gtl_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create

.gtl_done:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_slice_assign:
    ; RCX = dest_list, RDX = src_list -> RAX = dest_list (in-place arr[:] = src)
    test    rcx, rcx
    jz      .lsa_ret_rcx
    cmp     rcx, 65536
    jb      .lsa_ret_rcx
    test    rdx, rdx
    jz      .lsa_zero
    cmp     rdx, 65536
    jb      .lsa_zero
    mov     r8, [rdx]
    test    r8, r8
    jl      .lsa_zero
    mov     [rcx], r8
    xor     r9d, r9d
.lsa_cp:
    cmp     r9, r8
    jge     .lsa_ret_rcx
    mov     r10, [rdx + r9 * 8 + 8]
    mov     [rcx + r9 * 8 + 8], r10
    inc     r9
    jmp     .lsa_cp
.lsa_zero:
    mov     qword [rcx], 0
.lsa_ret_rcx:
    mov     rax, rcx
    ret

; ============================================================
; Complex Number Engine (24-byte struct: [0]=tag, [8]=re, [16]=im)
; ============================================================
_pyfasm_is_complex:
    ; RCX = value -> RAX = 1 if PYFCMPLX pointer, else 0
    cmp     rcx, 65536
    jb      .ic_no
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .ic_no
    mov     rax, [_pyfasm_cmplx_tag]
    cmp     qword [rcx], rax
    sete    al
    movzx   eax, al
    ret
.ic_no:
    xor     eax, eax
    ret

_pyfasm_complex_new:
    ; RCX = re_f64 bits, RDX = im_f64 bits -> RAX = PYFCMPLX pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     r12, rdx
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     rcx, [_pyfasm_cmplx_tag]
    mov     [rax], rcx
    mov     [rax + 8], rbx
    mov     [rax + 16], r12
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_real:
    ; RCX = complex ptr or float64/int -> RAX = float64 bits
    cmp     rcx, 65536
    jb      .cr_small_int
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .cr_already_f64
    mov     rax, [_pyfasm_cmplx_tag]
    cmp     qword [rcx], rax
    jne     .cr_zero
    mov     rax, [rcx + 8]
    ret
.cr_small_int:
    cvtsi2sd xmm0, rcx
    movq    rax, xmm0
    ret
.cr_already_f64:
    mov     rax, rcx
    ret
.cr_zero:
    xor     eax, eax
    ret

_pyfasm_complex_imag:
    ; RCX = complex ptr or float64/int -> RAX = float64 bits
    cmp     rcx, 65536
    jb      .ci_zero
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .ci_zero
    mov     rax, [_pyfasm_cmplx_tag]
    cmp     qword [rcx], rax
    jne     .ci_zero
    mov     rax, [rcx + 16]
    ret
.ci_zero:
    xor     eax, eax
    ret

_pyfasm_unpack_complex_pair:
    ; Internal leaf helper: RCX = val -> XMM0 = re, XMM1 = im
    ; Clobbers RAX, R8, XMM0, XMM1
    cmp     rcx, 65536
    jb      .ucp_int
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .ucp_f64
    mov     rax, [_pyfasm_cmplx_tag]
    cmp     qword [rcx], rax
    jne     .ucp_zero
    movq    xmm0, [rcx + 8]
    movq    xmm1, [rcx + 16]
    ret
.ucp_int:
    cvtsi2sd xmm0, rcx
    xorpd   xmm1, xmm1
    ret
.ucp_f64:
    movq    xmm0, rcx
    xorpd   xmm1, xmm1
    ret
.ucp_zero:
    xorpd   xmm0, xmm0
    xorpd   xmm1, xmm1
    ret

_pyfasm_complex_neg:
    ; RCX = complex -> RAX = new negated PYFCMPLX
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_unpack_complex_pair
    xorpd   xmm2, xmm2
    subsd   xmm2, xmm0
    xorpd   xmm3, xmm3
    subsd   xmm3, xmm1
    movq    rcx, xmm2
    movq    rdx, xmm3
    call    _pyfasm_complex_new
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_abs:
    ; RCX = complex -> RAX = |z| as float64 bits
    call    _pyfasm_unpack_complex_pair
    mulsd   xmm0, xmm0
    mulsd   xmm1, xmm1
    addsd   xmm0, xmm1
    sqrtsd  xmm0, xmm0
    movq    rax, xmm0
    ret

_pyfasm_complex_add:
    ; RCX = a, RDX = b -> RAX = PYFCMPLX
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    call    _pyfasm_unpack_complex_pair
    movsd   [rsp + 32], xmm0
    movsd   [rsp + 40], xmm1
    mov     rcx, rdx
    call    _pyfasm_unpack_complex_pair
    addsd   xmm0, [rsp + 32]
    addsd   xmm1, [rsp + 40]
    movq    rcx, xmm0
    movq    rdx, xmm1
    call    _pyfasm_complex_new
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_sub:
    ; RCX = a, RDX = b -> RAX = PYFCMPLX
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    call    _pyfasm_unpack_complex_pair
    movsd   [rsp + 32], xmm0
    movsd   [rsp + 40], xmm1
    mov     rcx, rdx
    call    _pyfasm_unpack_complex_pair
    movsd   xmm2, [rsp + 32]
    movsd   xmm3, [rsp + 40]
    subsd   xmm2, xmm0
    subsd   xmm3, xmm1
    movq    rcx, xmm2
    movq    rdx, xmm3
    call    _pyfasm_complex_new
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_mul:
    ; RCX = a+bi, RDX = c+di -> RAX = PYFCMPLX (ac-bd, ad+bc)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    call    _pyfasm_unpack_complex_pair
    movsd   [rsp + 32], xmm0        ; a
    movsd   [rsp + 40], xmm1        ; b
    mov     rcx, rdx
    call    _pyfasm_unpack_complex_pair ; xmm0=c, xmm1=d
    movsd   xmm2, [rsp + 32]        ; a
    movsd   xmm3, [rsp + 40]        ; b
    movsd   xmm4, xmm2
    mulsd   xmm4, xmm0              ; ac
    movsd   xmm5, xmm3
    mulsd   xmm5, xmm1              ; bd
    subsd   xmm4, xmm5              ; ac - bd
    mulsd   xmm2, xmm1              ; ad
    mulsd   xmm3, xmm0              ; bc
    addsd   xmm2, xmm3              ; ad + bc
    movq    rcx, xmm4
    movq    rdx, xmm2
    call    _pyfasm_complex_new
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_div:
    ; RCX = a+bi, RDX = c+di -> RAX = PYFCMPLX
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    call    _pyfasm_unpack_complex_pair
    movsd   [rsp + 32], xmm0        ; a
    movsd   [rsp + 40], xmm1        ; b
    mov     rcx, rdx
    call    _pyfasm_unpack_complex_pair ; xmm0=c, xmm1=d
    movsd   xmm2, xmm0
    mulsd   xmm2, xmm0              ; c^2
    movsd   xmm3, xmm1
    mulsd   xmm3, xmm1              ; d^2
    addsd   xmm2, xmm3              ; denom = c^2 + d^2
    movsd   xmm4, [rsp + 32]        ; a
    movsd   xmm5, [rsp + 40]        ; b
    movsd   xmm3, xmm4
    mulsd   xmm3, xmm0              ; ac
    movsd   [rsp + 32], xmm3
    movsd   xmm3, xmm5
    mulsd   xmm3, xmm1              ; bd
    addsd   xmm3, [rsp + 32]        ; ac + bd
    divsd   xmm3, xmm2              ; real part
    mulsd   xmm5, xmm0              ; bc
    mulsd   xmm4, xmm1              ; ad
    subsd   xmm5, xmm4              ; bc - ad
    divsd   xmm5, xmm2              ; imag part
    movq    rcx, xmm3
    movq    rdx, xmm5
    call    _pyfasm_complex_new
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_sqrt:
    ; RCX = complex or real/int -> RAX = PYFCMPLX sqrt(z)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    call    _pyfasm_unpack_complex_pair ; xmm0 = x, xmm1 = y
    movsd   xmm2, xmm0
    mulsd   xmm2, xmm2
    movsd   xmm3, xmm1
    mulsd   xmm3, xmm3
    addsd   xmm2, xmm3
    sqrtsd  xmm2, xmm2              ; xmm2 = r = hypot(x, y)
    xorpd   xmm3, xmm3
    ucomisd xmm2, xmm3
    jne     .csq_nonzero
    xor     ecx, ecx
    xor     edx, edx
    call    _pyfasm_complex_new
    jmp     .csq_done
.csq_nonzero:
    movsd   xmm4, [_pyfasm_flt_half]
    movsd   xmm5, [_pyfasm_flt_two]
    ucomisd xmm0, xmm3
    jb      .csq_neg_x
    ; x >= 0: u = sqrt((r + x) * 0.5), v = y / (2 * u)
    addsd   xmm2, xmm0
    mulsd   xmm2, xmm4
    sqrtsd  xmm2, xmm2              ; u
    mulsd   xmm5, xmm2              ; 2u
    divsd   xmm1, xmm5              ; v = y / (2u)
    movq    rcx, xmm2
    movq    rdx, xmm1
    call    _pyfasm_complex_new
    jmp     .csq_done
.csq_neg_x:
    ; x < 0: v_mag = sqrt((r - x) * 0.5), u = |y| / (2*v_mag), v = (y >= 0 ? v_mag : -v_mag)
    subsd   xmm2, xmm0
    mulsd   xmm2, xmm4
    sqrtsd  xmm2, xmm2              ; v_mag
    movsd   xmm4, xmm1
    movq    rax, xmm4
    and     rax, [_pyfasm_flt_abs_mask]
    movq    xmm4, rax               ; |y|
    mulsd   xmm5, xmm2              ; 2 * v_mag
    divsd   xmm4, xmm5              ; u = |y| / (2*v_mag)
    ucomisd xmm1, xmm3
    jae     .csq_v_pos
    xorpd   xmm0, xmm0
    subsd   xmm0, xmm2
    movaps  xmm2, xmm0
.csq_v_pos:
    movq    rcx, xmm4
    movq    rdx, xmm2
    call    _pyfasm_complex_new
.csq_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_complex_to_str:
    ; RCX = PYFCMPLX ptr -> RAX = heap str "(re+imj)"
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    call    _pyfasm_is_complex
    test    eax, eax
    jz      .cts_fallback
    mov     rcx, [rbx + 8]
    call    _pyfasm_float_to_str
    mov     rsi, rax                ; real str
    lea     rcx, [lparen_str]
    mov     rdx, rsi
    call    _pyfasm_str_concat
    mov     rsi, rax
    mov     rax, [rbx + 16]
    test    rax, rax
    js      .cts_neg_im
    mov     rcx, rsi
    lea     rdx, [_pyfasm_str_plus]
    call    _pyfasm_str_concat
    mov     rsi, rax
.cts_neg_im:
    mov     rcx, [rbx + 16]
    call    _pyfasm_float_to_str
    mov     rcx, rsi
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     rcx, rax
    lea     rdx, [_pyfasm_str_j]
    call    _pyfasm_str_concat
    mov     rcx, rax
    lea     rdx, [rparen_str]
    call    _pyfasm_str_concat
    jmp     .cts_ret
.cts_fallback:
    mov     rcx, rbx
    call    _pyfasm_float_to_str
.cts_ret:
    lea     rsp, [rbp - 24]
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; IEEE-754 Math Functions (Pure x86-64 / x87 FPU)
; ============================================================
_pyfasm_math_isnan:
    ; RCX = float64 bits -> RAX = 1 if NaN else 0
    mov     rax, 7FFFFFFFFFFFFFFFh
    and     rcx, rax
    mov     rdx, 7FF0000000000000h
    cmp     rcx, rdx
    seta    al
    movzx   eax, al
    ret

_pyfasm_math_isinf:
    ; RCX = float64 bits -> RAX = 1 if +/-inf else 0
    mov     rax, 7FFFFFFFFFFFFFFFh
    and     rcx, rax
    mov     rdx, 7FF0000000000000h
    cmp     rcx, rdx
    sete    al
    movzx   eax, al
    ret

_pyfasm_math_isfinite:
    ; RCX = float64 bits -> RAX = 1 if finite else 0
    mov     rax, 7FFFFFFFFFFFFFFFh
    and     rcx, rax
    mov     rdx, 7FF0000000000000h
    cmp     rcx, rdx
    setb    al
    movzx   eax, al
    ret

_pyfasm_math_isclose:
    ; RCX = a_f64, RDX = b_f64, R8 = rel_tol_f64, R9 = abs_tol_f64 -> RAX = 0/1
    movq    xmm0, rcx
    movq    xmm1, rdx
    ucomisd xmm0, xmm1
    jp      .mic_false              ; either operand is NaN
    je      .mic_true               ; exact equality (incl +/-inf == +/-inf)
    ; Check infinities: if either is inf and they were not equal -> False
    mov     rax, [_pyfasm_flt_abs_mask]
    mov     r10, rcx
    and     r10, rax
    cmp     r10, [_pyfasm_flt_inf]
    jae     .mic_false
    mov     r10, rdx
    and     r10, rax
    cmp     r10, [_pyfasm_flt_inf]
    jae     .mic_false
    ; |a - b|
    movq    xmm2, rax
    movsd   xmm3, xmm0
    subsd   xmm3, xmm1
    andpd   xmm3, xmm2              ; |a - b|
    andpd   xmm0, xmm2              ; |a|
    andpd   xmm1, xmm2              ; |b|
    maxsd   xmm0, xmm1              ; max(|a|, |b|)
    movq    xmm4, r8
    mulsd   xmm0, xmm4              ; rel_tol * max(|a|, |b|)
    movq    xmm5, r9
    maxsd   xmm0, xmm5              ; max(rel_tol * max, abs_tol)
    ucomisd xmm3, xmm0
    ja      .mic_false
.mic_true:
    mov     eax, 1
    ret
.mic_false:
    xor     eax, eax
    ret

_pyfasm_min_f64:
    ; RCX = a_f64, RDX = b_f64 -> RAX = min(a, b) bits
    movq    xmm0, rcx
    movq    xmm1, rdx
    minsd   xmm0, xmm1
    movq    rax, xmm0
    ret

_pyfasm_max_f64:
    ; RCX = a_f64, RDX = b_f64 -> RAX = max(a, b) bits
    movq    xmm0, rcx
    movq    xmm1, rdx
    maxsd   xmm0, xmm1
    movq    rax, xmm0
    ret

_pyfasm_math_sin:
    ; RCX = float64 bits -> RAX = sin(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rax, rcx
    cmp     rax, [_pyfasm_flt_inf]
    jae     .msin_nan
    fninit
    fld     qword [_pyfasm_flt_two_pi]
    fld     qword [rsp + 8]
.msin_rem:
    fprem
    fnstsw  ax
    test    ax, 0400h
    jnz     .msin_rem
    fstp    st1
    fsin
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.msin_nan:
    mov     rax, [_pyfasm_flt_nan]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_cos:
    ; RCX = float64 bits -> RAX = cos(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rax, rcx
    cmp     rax, [_pyfasm_flt_inf]
    jae     .mcos_nan
    fninit
    fld     qword [_pyfasm_flt_two_pi]
    fld     qword [rsp + 8]
.mcos_rem:
    fprem
    fnstsw  ax
    test    ax, 0400h
    jnz     .mcos_rem
    fstp    st1
    fcos
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.mcos_nan:
    mov     rax, [_pyfasm_flt_nan]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_tan:
    ; RCX = float64 bits -> RAX = tan(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rax, rcx
    cmp     rax, [_pyfasm_flt_inf]
    jae     .mtan_nan
    fninit
    fld     qword [_pyfasm_flt_two_pi]
    fld     qword [rsp + 8]
.mtan_rem:
    fprem
    fnstsw  ax
    test    ax, 0400h
    jnz     .mtan_rem
    fstp    st1
    fptan
    fstp    st0                     ; pop 1.0 pushed by fptan
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.mtan_nan:
    mov     rax, [_pyfasm_flt_nan]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_atan2:
    ; RCX = y_f64, RDX = x_f64 -> RAX = atan2(y, x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    mov     [rsp + 16], rdx
    fninit
    fld     qword [rsp + 8]         ; y
    fld     qword [rsp + 16]        ; x
    fpatan
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_hypot:
    ; RCX = x_f64, RDX = y_f64 -> RAX = sqrt(x*x + y*y)
    movq    xmm0, rcx
    movq    xmm1, rdx
    mulsd   xmm0, xmm0
    mulsd   xmm1, xmm1
    addsd   xmm0, xmm1
    sqrtsd  xmm0, xmm0
    movq    rax, xmm0
    ret

_pyfasm_math_exp:
    ; RCX = x_f64 -> RAX = e^x float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    movq    xmm0, rcx
    ucomisd xmm0, xmm0
    jp      .mexp_nan
    ucomisd xmm0, [_pyfasm_flt_exp_max]
    ja      .mexp_inf
    ucomisd xmm0, [_pyfasm_flt_exp_min]
    jb      .mexp_zero
    fninit
    fldl2e
    fld     qword [rsp + 8]
    fmulp   st1, st0
    fld     st0
    frndint
    fsub    st1, st0
    fxch    st1
    f2xm1
    fld1
    faddp   st1, st0
    fscale
    fstp    st1
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.mexp_inf:
    mov     rax, [_pyfasm_flt_inf]
    mov     rsp, rbp
    pop     rbp
    ret
.mexp_zero:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret
.mexp_nan:
    mov     rax, [_pyfasm_flt_nan]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_log:
    ; RCX = x_f64 -> RAX = ln(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    movq    xmm0, rcx
    ucomisd xmm0, xmm0
    jp      .mlog_nan
    xorpd   xmm1, xmm1
    ucomisd xmm0, xmm1
    je      .mlog_ninf
    jb      .mlog_nan
    fninit
    fldln2
    fld     qword [rsp + 8]
    fyl2x
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.mlog_ninf:
    mov     rax, [_pyfasm_flt_ninf]
    mov     rsp, rbp
    pop     rbp
    ret
.mlog_nan:
    mov     rax, [_pyfasm_flt_nan]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_log10:
    ; RCX = x_f64 -> RAX = log10(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    movq    xmm0, rcx
    ucomisd xmm0, xmm0
    jp      .ml10_nan
    xorpd   xmm1, xmm1
    ucomisd xmm0, xmm1
    je      .ml10_ninf
    jb      .ml10_nan
    fninit
    fldlg2
    fld     qword [rsp + 8]
    fyl2x
    fstp    qword [rsp + 8]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.ml10_ninf:
    mov     rax, [_pyfasm_flt_ninf]
    mov     rsp, rbp
    pop     rbp
    ret
.ml10_nan:
    mov     rax, [_pyfasm_flt_nan]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_floor_f64:
    ; RCX = x_f64 -> RAX = floor(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    fninit
    fnstcw  word [rsp + 16]
    movzx   eax, word [rsp + 16]
    and     eax, 0F3FFh
    or      eax, 0400h              ; round down (-inf)
    mov     word [rsp + 18], ax
    fldcw   word [rsp + 18]
    fld     qword [rsp + 8]
    frndint
    fstp    qword [rsp + 8]
    fldcw   word [rsp + 16]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_ceil_f64:
    ; RCX = x_f64 -> RAX = ceil(x) float64 bits
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [rsp + 8], rcx
    fninit
    fnstcw  word [rsp + 16]
    movzx   eax, word [rsp + 16]
    and     eax, 0F3FFh
    or      eax, 0800h              ; round up (+inf)
    mov     word [rsp + 18], ax
    fldcw   word [rsp + 18]
    fld     qword [rsp + 8]
    frndint
    fstp    qword [rsp + 8]
    fldcw   word [rsp + 16]
    mov     rax, [rsp + 8]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_math_pow_f64:
    ; RCX = x_f64, RDX = y_f64 -> RAX = x**y float64 bits
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 64
    and     rsp, -16

    mov     rbx, rcx                ; x
    mov     r12, rdx                ; y
    movq    xmm0, rbx
    movq    xmm1, r12
    xorpd   xmm2, xmm2

    ; y == 0.0 -> 1.0
    ucomisd xmm1, xmm2
    jp      .mpow_nan
    jne     .mpow_chk_xnan
    mov     rax, [_pyfasm_flt_one]
    jmp     .mpow_done

.mpow_chk_xnan:
    ucomisd xmm0, xmm0
    jp      .mpow_nan

    ; x == 0.0
    ucomisd xmm0, xmm2
    jne     .mpow_chk_sign
    ucomisd xmm1, xmm2
    ja      .mpow_zero
    mov     rax, [_pyfasm_flt_inf]
    jmp     .mpow_done

.mpow_chk_sign:
    ; Check negative base: if x < 0, check if y is integer
    ucomisd xmm0, xmm2
    ja      .mpow_pos
    ; Check y is finite integer
    mov     rcx, r12
    call    _pyfasm_math_floor_f64
    movq    xmm3, rax
    movq    xmm1, r12
    ucomisd xmm1, xmm3
    jne     .mpow_nan               ; non-integer power of negative base -> NaN
    cvttsd2si rax, xmm1
    and     rax, 1
    mov     [rsp + 32], rax         ; parity: 1 if odd else 0
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rbx, rax                ; |x|
    mov     [rsp + 40], rbx
    mov     [rsp + 48], r12
    fninit
    fld     qword [rsp + 48]        ; y
    fld     qword [rsp + 40]        ; |x|
    fyl2x
    fld     st0
    frndint
    fsub    st1, st0
    fxch    st1
    f2xm1
    fld1
    faddp   st1, st0
    fscale
    fstp    st1
    fstp    qword [rsp + 40]
    mov     rax, [rsp + 40]
    cmp     qword [rsp + 32], 0
    jz      .mpow_done
    mov     rdx, [_pyfasm_flt_sign_mask]
    xor     rax, rdx
    jmp     .mpow_done

.mpow_pos:
    mov     [rsp + 40], rbx
    mov     [rsp + 48], r12
    fninit
    fld     qword [rsp + 48]        ; y
    fld     qword [rsp + 40]        ; x
    fyl2x                           ; st0 = y * log2(x)
    fld     st0
    frndint
    fsub    st1, st0
    fxch    st1
    f2xm1
    fld1
    faddp   st1, st0
    fscale
    fstp    st1
    fstp    qword [rsp + 40]
    mov     rax, [rsp + 40]
    jmp     .mpow_done

.mpow_zero:
    xor     eax, eax
    jmp     .mpow_done
.mpow_nan:
    mov     rax, [_pyfasm_flt_nan]
.mpow_done:
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; Real 1D/2D Vectorized NumPy Operations (lists of IEEE-754 float64 bits)
; ============================================================
_pyfasm_np_linspace:
    ; RCX = start_f64, RDX = stop_f64, R8 = num_i64 -> RAX = list_ptr of float64s
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    mov     r12, rcx                ; start_f64
    mov     r13, rdx                ; stop_f64
    mov     r14, r8                 ; num
    cmp     r14, 0
    jle     .npl_empty

    mov     rcx, r14
    call    _pyfasm_list_create
    mov     r15, rax
    mov     [r15], r14
    cmp     r14, 1
    jne     .npl_multi
    mov     [r15 + 8], r12
    mov     rax, r15
    jmp     .npl_done

.npl_multi:
    movq    xmm0, r12               ; start
    movq    xmm1, r13               ; stop
    subsd   xmm1, xmm0              ; span = stop - start
    lea     rax, [r14 - 1]
    cvtsi2sd xmm2, rax
    divsd   xmm1, xmm2              ; step = span / (num - 1)
    movsd   [rsp + 32], xmm0
    movsd   [rsp + 40], xmm1

    xor     ebx, ebx
    lea     rsi, [r14 - 1]
.npl_loop:
    cmp     rbx, rsi
    jge     .npl_last
    cvtsi2sd xmm3, rbx
    mulsd   xmm3, [rsp + 40]
    addsd   xmm3, [rsp + 32]
    movq    rax, xmm3
    mov     [r15 + rbx * 8 + 8], rax
    inc     rbx
    jmp     .npl_loop

.npl_last:
    mov     [r15 + rsi * 8 + 8], r13
    mov     rax, r15
    jmp     .npl_done

.npl_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
.npl_done:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_arange:
    ; RCX = start_f64, RDX = stop_f64, R8 = step_f64 -> RAX = list_ptr of float64s
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    mov     r12, rcx                ; start
    mov     r13, rdx                ; stop
    mov     r14, r8                 ; step

    movq    xmm0, r12
    movq    xmm1, r13
    movq    xmm2, r14
    xorpd   xmm3, xmm3
    ucomisd xmm2, xmm3
    je      .npa_empty

    subsd   xmm1, xmm0              ; span = stop - start
    divsd   xmm1, xmm2              ; ratio
    ucomisd xmm1, xmm3
    jbe     .npa_empty

    movq    rcx, xmm1
    call    _pyfasm_math_ceil_f64
    movq    xmm4, rax
    cvttsd2si rbx, xmm4             ; count
    cmp     rbx, 0
    jle     .npa_empty
    cmp     rbx, 1048576
    jle     .npa_cnt_ok
    mov     rbx, 1048576
.npa_cnt_ok:
    mov     rcx, rbx
    call    _pyfasm_list_create
    mov     r15, rax
    mov     [r15], rbx

    movq    xmm0, r12
    movq    xmm2, r14
    movsd   [rsp + 32], xmm0
    movsd   [rsp + 40], xmm2
    xor     esi, esi
.npa_loop:
    cmp     rsi, rbx
    jge     .npa_ret
    cvtsi2sd xmm3, rsi
    mulsd   xmm3, [rsp + 40]
    addsd   xmm3, [rsp + 32]
    movq    rax, xmm3
    mov     [r15 + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npa_loop

.npa_ret:
    mov     rax, r15
    jmp     .npa_done
.npa_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
.npa_done:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_empty:
    ; RCX = length (int64) -> RAX = zeroed float64 list of exact length RCX
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    cmp     rbx, 0
    jg      .npe_alloc
    xor     ecx, ecx
    call    _pyfasm_list_create
    jmp     .npe_done
.npe_alloc:
    mov     rcx, rbx
    call    _pyfasm_list_create
    mov     [rax], rbx
    lea     rdi, [rax + 8]
    mov     rcx, rbx
    mov     rdx, rax
    xor     eax, eax
    rep     stosq
    mov     rax, rdx
.npe_done:
    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_min_f64:
    ; RCX = list_ptr of float64 -> RAX = min float64 bits
    test    rcx, rcx
    jz      .npmin_zero
    cmp     rcx, 65536
    jb      .npmin_zero
    mov     r8, [rcx]
    test    r8, r8
    jle     .npmin_zero
    movq    xmm0, [rcx + 8]
    mov     r9, 1
.npmin_loop:
    cmp     r9, r8
    jge     .npmin_done
    minsd   xmm0, [rcx + r9 * 8 + 8]
    inc     r9
    jmp     .npmin_loop
.npmin_done:
    movq    rax, xmm0
    ret
.npmin_zero:
    xor     eax, eax
    ret

_pyfasm_np_max_f64:
    ; RCX = list_ptr of float64 -> RAX = max float64 bits
    test    rcx, rcx
    jz      .npmax_zero
    cmp     rcx, 65536
    jb      .npmax_zero
    mov     r8, [rcx]
    test    r8, r8
    jle     .npmax_zero
    movq    xmm0, [rcx + 8]
    mov     r9, 1
.npmax_loop:
    cmp     r9, r8
    jge     .npmax_done
    maxsd   xmm0, [rcx + r9 * 8 + 8]
    inc     r9
    jmp     .npmax_loop
.npmax_done:
    movq    rax, xmm0
    ret
.npmax_zero:
    xor     eax, eax
    ret

_pyfasm_np_ptp_f64:
    ; RCX = list_ptr of float64 -> RAX = max - min float64 bits
    test    rcx, rcx
    jz      .npptp_zero
    cmp     rcx, 65536
    jb      .npptp_zero
    mov     r8, [rcx]
    test    r8, r8
    jle     .npptp_zero
    movq    xmm0, [rcx + 8]         ; min
    movq    xmm1, [rcx + 8]         ; max
    mov     r9, 1
.npptp_loop:
    cmp     r9, r8
    jge     .npptp_done
    movq    xmm2, [rcx + r9 * 8 + 8]
    minsd   xmm0, xmm2
    maxsd   xmm1, xmm2
    inc     r9
    jmp     .npptp_loop
.npptp_done:
    subsd   xmm1, xmm0
    movq    rax, xmm1
    ret
.npptp_zero:
    xor     eax, eax
    ret

_pyfasm_np_sum_f64:
    ; RCX = list_ptr of float64 -> RAX = sum float64 bits
    xorpd   xmm0, xmm0
    test    rcx, rcx
    jz      .npsum_done
    cmp     rcx, 65536
    jb      .npsum_done
    mov     r8, [rcx]
    xor     r9d, r9d
.npsum_loop:
    cmp     r9, r8
    jge     .npsum_done
    addsd   xmm0, [rcx + r9 * 8 + 8]
    inc     r9
    jmp     .npsum_loop
.npsum_done:
    movq    rax, xmm0
    ret

_pyfasm_np_mean_f64:
    ; RCX = list_ptr of float64 -> RAX = mean float64 bits
    test    rcx, rcx
    jz      .npmean_zero
    cmp     rcx, 65536
    jb      .npmean_zero
    mov     r8, [rcx]
    test    r8, r8
    jle     .npmean_zero
    xorpd   xmm0, xmm0
    xor     r9d, r9d
.npmean_loop:
    cmp     r9, r8
    jge     .npmean_div
    addsd   xmm0, [rcx + r9 * 8 + 8]
    inc     r9
    jmp     .npmean_loop
.npmean_div:
    cvtsi2sd xmm1, r8
    divsd   xmm0, xmm1
    movq    rax, xmm0
    ret
.npmean_zero:
    xor     eax, eax
    ret

_pyfasm_np_sign_scalar_f64:
    ; Internal leaf helper: RAX = f64_bits -> RAX = sign float64 (-1.0, 0.0, 1.0)
    movq    xmm0, rax
    xorpd   xmm1, xmm1
    ucomisd xmm0, xmm1
    jp      .nps_zero
    ja      .nps_pos
    jb      .nps_neg
.nps_zero:
    xor     eax, eax
    ret
.nps_pos:
    mov     rax, [_pyfasm_flt_one]
    ret
.nps_neg:
    mov     rax, [_pyfasm_flt_neg_one]
    ret

_pyfasm_np_sign_f64:
    ; RCX = float64 scalar OR list_ptr of float64s -> RAX = sign scalar or array
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    cmp     rcx, 65536
    jb      .npsg_scalar
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .npsg_scalar

    ; Valid heap pointer -> vector sign
    mov     r12, rcx
    mov     r13, [r12]
    test    r13, r13
    jle     .npsg_empty_list
    mov     rcx, r13
    call    _pyfasm_list_create
    mov     [rax], r13
    xor     ebx, ebx
    mov     rdx, rax
.npsg_loop:
    cmp     rbx, r13
    jge     .npsg_list_done
    mov     rax, [r12 + rbx * 8 + 8]
    call    _pyfasm_np_sign_scalar_f64
    mov     [rdx + rbx * 8 + 8], rax
    inc     rbx
    jmp     .npsg_loop
.npsg_list_done:
    mov     rax, rdx
    jmp     .npsg_done

.npsg_empty_list:
    xor     ecx, ecx
    call    _pyfasm_list_create
    jmp     .npsg_done

.npsg_scalar:
    mov     rax, rcx
    call    _pyfasm_np_sign_scalar_f64

.npsg_done:
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_vec_op:
    ; RCX = lhs (arr or f64), RDX = rhs (arr or f64), R8 = op (0:+,1:-,2:*,3:/,4:**), R9 = flags (1:lhs_arr, 2:rhs_arr)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    mov     r12, rcx                ; lhs
    mov     r13, rdx                ; rhs
    mov     r14, r8                 ; op_code
    mov     r15, r9                 ; flags

    ; Determine output length n in rbx
    xor     ebx, ebx
    test    r15, 1
    jz      .npvo_chk_rhs
    cmp     r12, 65536
    jb      .npvo_chk_rhs
    mov     rbx, [r12]
.npvo_chk_rhs:
    test    r15, 2
    jz      .npvo_got_len
    cmp     r13, 65536
    jb      .npvo_got_len
    mov     rax, [r13]
    test    rbx, rbx
    jz      .npvo_use_rlen
    cmp     rbx, 1
    je      .npvo_use_rlen
    cmp     rax, 1
    je      .npvo_got_len
    cmp     rax, rbx
    jge     .npvo_got_len
.npvo_use_rlen:
    mov     rbx, rax
.npvo_got_len:
    test    rbx, rbx
    jle     .npvo_empty
    mov     rcx, rbx
    call    _pyfasm_list_create
    mov     [rax], rbx
    mov     [rsp + 32], rax         ; res_list ptr
    xor     esi, esi                ; i = 0

.npvo_loop:
    cmp     rsi, rbx
    jge     .npvo_finish

    ; Load lhs[i] into rcx (or scalar)
    test    r15, 1
    jz      .npvo_lhs_scalar
    mov     rax, [r12]
    test    rax, rax
    jle     .npvo_lhs_zero
    cmp     rax, 1
    jne     .npvo_lhs_idx
    mov     rcx, [r12 + 8]
    jmp     .npvo_rhs_load
.npvo_lhs_idx:
    mov     rcx, [r12 + rsi * 8 + 8]
    jmp     .npvo_rhs_load
.npvo_lhs_zero:
    xor     ecx, ecx
    jmp     .npvo_rhs_load
.npvo_lhs_scalar:
    mov     rcx, r12

.npvo_rhs_load:
    test    r15, 2
    jz      .npvo_rhs_scalar
    mov     rax, [r13]
    test    rax, rax
    jle     .npvo_rhs_zero
    cmp     rax, 1
    jne     .npvo_rhs_idx
    mov     rdx, [r13 + 8]
    jmp     .npvo_exec
.npvo_rhs_idx:
    mov     rdx, [r13 + rsi * 8 + 8]
    jmp     .npvo_exec
.npvo_rhs_zero:
    xor     edx, edx
    jmp     .npvo_exec
.npvo_rhs_scalar:
    mov     rdx, r13

.npvo_exec:
    movq    xmm0, rcx
    movq    xmm1, rdx
    cmp     r14, 0
    je      .npvo_add
    cmp     r14, 1
    je      .npvo_sub
    cmp     r14, 2
    je      .npvo_mul
    cmp     r14, 3
    je      .npvo_div
    ; op == 4: pow
    call    _pyfasm_math_pow_f64
    jmp     .npvo_store
.npvo_add:
    addsd   xmm0, xmm1
    movq    rax, xmm0
    jmp     .npvo_store
.npvo_sub:
    subsd   xmm0, xmm1
    movq    rax, xmm0
    jmp     .npvo_store
.npvo_mul:
    mulsd   xmm0, xmm1
    movq    rax, xmm0
    jmp     .npvo_store
.npvo_div:
    divsd   xmm0, xmm1
    movq    rax, xmm0
.npvo_store:
    mov     rdi, [rsp + 32]
    mov     [rdi + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npvo_loop

.npvo_finish:
    mov     rax, [rsp + 32]
    jmp     .npvo_done
.npvo_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
.npvo_done:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_ufunc_scalar:
    ; RCX = val_f64, RDX = uid (0:sqrt,1:sin,2:cos,3:tan,4:exp,5:log,6:abs,7:isfinite,8:isnan,9:floor,10:ceil,11:log10)
    cmp     rdx, 0
    je      .nus_sqrt
    cmp     rdx, 1
    je      _pyfasm_math_sin
    cmp     rdx, 2
    je      _pyfasm_math_cos
    cmp     rdx, 3
    je      _pyfasm_math_tan
    cmp     rdx, 4
    je      _pyfasm_math_exp
    cmp     rdx, 5
    je      _pyfasm_math_log
    cmp     rdx, 6
    je      .nus_abs
    cmp     rdx, 7
    je      _pyfasm_math_isfinite
    cmp     rdx, 8
    je      _pyfasm_math_isnan
    cmp     rdx, 9
    je      _pyfasm_math_floor_f64
    cmp     rdx, 10
    je      _pyfasm_math_ceil_f64
    cmp     rdx, 11
    je      _pyfasm_math_log10
    mov     rax, rcx
    ret
.nus_sqrt:
    movq    xmm0, rcx
    sqrtsd  xmm0, xmm0
    movq    rax, xmm0
    ret
.nus_abs:
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rax, rcx
    ret

_pyfasm_np_vec_ufunc:
    ; RCX = list_ptr or f64 scalar, RDX = ufunc_id -> RAX = new list or scalar
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    push    r14
    sub     rsp, 40
    and     rsp, -16

    mov     r12, rcx
    mov     r13, rdx
    cmp     r12, 65536
    jb      .npu_scalar
    mov     rax, 00007FFFFFFFFFFFh
    cmp     r12, rax
    ja      .npu_scalar

    mov     r14, [r12]
    test    r14, r14
    jle     .npu_empty
    mov     rcx, r14
    call    _pyfasm_list_create
    mov     [rax], r14
    mov     rbx, rax
    xor     esi, esi
.npu_loop:
    cmp     rsi, r14
    jge     .npu_list_ret
    mov     rcx, [r12 + rsi * 8 + 8]
    mov     rdx, r13
    call    _pyfasm_np_ufunc_scalar
    mov     [rbx + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npu_loop
.npu_list_ret:
    mov     rax, rbx
    jmp     .npu_done
.npu_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    jmp     .npu_done
.npu_scalar:
    mov     rcx, r12
    mov     rdx, r13
    call    _pyfasm_np_ufunc_scalar
.npu_done:
    lea     rsp, [rbp - 40]
    pop     r14
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_column_stack:
    ; RCX = tuple/list of 1D arrays -> RAX = 2D list [[arr0[i], arr1[i], ...], ...]
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .npcs_empty
    mov     r12, rcx                ; seq of cols
    mov     r13, [r12]              ; K = num cols
    test    r13, r13
    jle     .npcs_empty
    mov     rax, [r12 + 8]          ; col 0
    test    rax, rax
    jz      .npcs_empty
    mov     r14, [rax]              ; N = num rows
    test    r14, r14
    jle     .npcs_empty

    mov     rcx, r14
    call    _pyfasm_list_create
    mov     [rax], r14
    mov     r15, rax                ; outer result list
    xor     ebx, ebx                ; row i = 0

.npcs_row_loop:
    cmp     rbx, r14
    jge     .npcs_done_ok
    mov     rcx, r13
    call    _pyfasm_list_create
    mov     [rax], r13
    mov     rdi, rax
    xor     esi, esi                ; col j = 0
.npcs_col_loop:
    cmp     rsi, r13
    jge     .npcs_store_row
    mov     rax, [r12 + rsi * 8 + 8]
    xor     ecx, ecx
    test    rax, rax
    jz      .npcs_store_cell
    cmp     rbx, [rax]
    jge     .npcs_store_cell
    mov     rcx, [rax + rbx * 8 + 8]
.npcs_store_cell:
    mov     [rdi + rsi * 8 + 8], rcx
    inc     rsi
    jmp     .npcs_col_loop
.npcs_store_row:
    mov     [r15 + rbx * 8 + 8], rdi
    inc     rbx
    jmp     .npcs_row_loop

.npcs_done_ok:
    mov     rax, r15
    jmp     .npcs_ret
.npcs_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
.npcs_ret:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_all:
    ; RCX = list_ptr or bool -> RAX = 1 if all non-zero else 0
    cmp     rcx, 65536
    jb      .npa_bool
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .npa_bool
    mov     r8, [rcx]
    mov     r9, 7FFFFFFFFFFFFFFFh
    xor     r10d, r10d
.npa_loop:
    cmp     r10, r8
    jge     .npa_true
    mov     rax, [rcx + r10 * 8 + 8]
    test    rax, r9
    jz      .npa_false
    inc     r10
    jmp     .npa_loop
.npa_bool:
    mov     rax, 7FFFFFFFFFFFFFFFh
    test    rcx, rax
    setnz   al
    movzx   eax, al
    ret
.npa_true:
    mov     eax, 1
    ret
.npa_false:
    xor     eax, eax
    ret

_pyfasm_np_any:
    ; RCX = list_ptr or bool -> RAX = 1 if any non-zero else 0
    cmp     rcx, 65536
    jb      .npan_bool
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .npan_bool
    mov     r8, [rcx]
    mov     r9, 7FFFFFFFFFFFFFFFh
    xor     r10d, r10d
.npan_loop:
    cmp     r10, r8
    jge     .npan_false
    mov     rax, [rcx + r10 * 8 + 8]
    test    rax, r9
    jnz     .npan_true
    inc     r10
    jmp     .npan_loop
.npan_bool:
    mov     rax, 7FFFFFFFFFFFFFFFh
    test    rcx, rax
    setnz   al
    movzx   eax, al
    ret
.npan_true:
    mov     eax, 1
    ret
.npan_false:
    xor     eax, eax
    ret

_pyfasm_np_all_finite:
    ; RCX = list_ptr -> RAX = 1 if every float element is finite else 0
    test    rcx, rcx
    jz      .npaf_true
    cmp     rcx, 65536
    jb      .npaf_scalar
    mov     rax, 00007FFFFFFFFFFFh
    cmp     rcx, rax
    ja      .npaf_scalar
    mov     r8, [rcx]
    mov     r9, 7FFFFFFFFFFFFFFFh
    mov     r11, 7FF0000000000000h
    xor     r10d, r10d
.npaf_loop:
    cmp     r10, r8
    jge     .npaf_true
    mov     rax, [rcx + r10 * 8 + 8]
    and     rax, r9
    cmp     rax, r11
    jae     .npaf_false
    inc     r10
    jmp     .npaf_loop
.npaf_scalar:
    jmp     _pyfasm_math_isfinite
.npaf_true:
    mov     eax, 1
    ret
.npaf_false:
    xor     eax, eax
    ret

; ============================================================
; Dynamic Attributes: getattr / hasattr / setattr
; Table entry format (24 bytes): [class_id (qword), name_str_ptr (qword), offset (qword)]
; ============================================================
_pyfasm_attr_lookup_entry:
    ; Internal helper: RCX = obj, RDX = attr_name_str -> RAX = offset (>= 0) or -1 if not found
    ; Uses R12..R15 safely via standard frame
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 48
    and     rsp, -16

    mov     r12, rcx                ; obj
    mov     r13, rdx                ; attr_name_str
    cmp     r12, 65536
    jb      .ale_not_found
    mov     rax, 00007FFFFFFFFFFFh
    cmp     r12, rax
    ja      .ale_not_found
    test    r13, r13
    jz      .ale_not_found

    ; Determine class_id if PYFCLSTG present at [obj + 2032]
    mov     r14, -1                 ; default cid = -1 (untagged)
    mov     rax, 505946434C535447h  ; "PYFCLSTG"
    cmp     [r12 + 2032], rax
    jne     .ale_scan
    mov     r14, [r12 + 2040]

.ale_scan:
    mov     rbx, [_pyfasm_attr_table_ptr]
    test    rbx, rbx
    jz      .ale_not_found

    ; Pass 1: exact class_id match (if r14 >= 0)
    cmp     r14, 0
    jl      .ale_pass2
    mov     rsi, rbx
.ale_p1_loop:
    mov     rdi, [rsi + 8]          ; name ptr
    test    rdi, rdi
    jz      .ale_pass2
    cmp     [rsi], r14
    jne     .ale_p1_next
    mov     rcx, rdi
    mov     rdx, r13
    call    _pyfasm_str_cmp
    test    eax, eax
    jz      .ale_p1_next
    mov     rax, [rsi + 16]         ; byte offset
    jmp     .ale_done
.ale_p1_next:
    add     rsi, 24
    jmp     .ale_p1_loop

.ale_pass2:
    ; If class_id was known (r14 > 0), do not bleed unrelated classes' attributes!
    cmp     r14, 0
    jg      .ale_not_found
    mov     rsi, rbx
.ale_p2_loop:
    mov     rdi, [rsi + 8]
    test    rdi, rdi
    jz      .ale_not_found
    cmp     qword [rsi], -1
    jne     .ale_p2_next
    mov     rcx, rdi
    mov     rdx, r13
    call    _pyfasm_str_cmp
    test    eax, eax
    jz      .ale_p2_next
    mov     rax, [rsi + 16]
    jmp     .ale_done
.ale_p2_next:
    add     rsi, 24
    jmp     .ale_p2_loop

.ale_not_found:
    mov     rax, -1
.ale_done:
    lea     rsp, [rbp - 48]
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_getattr:
    ; RCX = obj, RDX = attr_name_str, R8 = default_val -> RAX = value
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 48
    and     rsp, -16

    mov     r12, rcx                ; obj
    mov     r13, rdx                ; name
    mov     r14, r8                 ; default

    ; 1. Check PYFCMPLX ("real" / "imag")
    mov     rcx, r12
    call    _pyfasm_is_complex
    test    eax, eax
    jz      .ga_chk_dyn
    ; Check "real"
    mov     rcx, r13
    lea     rdx, [_pyfasm_str_real_key]
    call    _pyfasm_str_cmp
    test    eax, eax
    jz      .ga_chk_imag
    mov     rax, [r12 + 8]
    jmp     .ga_done
.ga_chk_imag:
    mov     rcx, r13
    lea     rdx, [_pyfasm_str_imag_key]
    call    _pyfasm_str_cmp
    test    eax, eax
    jz      .ga_chk_dyn
    mov     rax, [r12 + 16]
    jmp     .ga_done

.ga_chk_dyn:
    ; 2. Walk dynamic setattr linked list: [next (8), obj (8), name_str (8), val (8)]
    mov     rbx, [_pyfasm_dyn_attrs_head]
.ga_dyn_loop:
    test    rbx, rbx
    jz      .ga_chk_table
    cmp     [rbx + 8], r12
    jne     .ga_dyn_next
    mov     rcx, [rbx + 16]
    mov     rdx, r13
    call    _pyfasm_str_cmp
    test    eax, eax
    jz      .ga_dyn_next
    mov     rax, [rbx + 24]
    jmp     .ga_done
.ga_dyn_next:
    mov     rbx, [rbx]
    jmp     .ga_dyn_loop

.ga_chk_table:
    ; 3. Static attribute table lookup
    mov     rcx, r12
    mov     rdx, r13
    call    _pyfasm_attr_lookup_entry
    cmp     rax, 0
    jl      .ga_default
    mov     rax, [r12 + rax]
    jmp     .ga_done

.ga_default:
    mov     rax, r14

.ga_done:
    lea     rsp, [rbp - 48]
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_hasattr:
    ; RCX = obj, RDX = attr_name_str -> RAX = 1 if present else 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    mov     r12, rcx
    mov     r13, rdx

    ; Check PYFCMPLX
    mov     rcx, r12
    call    _pyfasm_is_complex
    test    eax, eax
    jz      .ha_dyn
    mov     rcx, r13
    lea     rdx, [_pyfasm_str_real_key]
    call    _pyfasm_str_cmp
    test    eax, eax
    jnz     .ha_true
    mov     rcx, r13
    lea     rdx, [_pyfasm_str_imag_key]
    call    _pyfasm_str_cmp
    test    eax, eax
    jnz     .ha_true

.ha_dyn:
    mov     rbx, [_pyfasm_dyn_attrs_head]
.ha_dyn_loop:
    test    rbx, rbx
    jz      .ha_tbl
    cmp     [rbx + 8], r12
    jne     .ha_dyn_next
    mov     rcx, [rbx + 16]
    mov     rdx, r13
    call    _pyfasm_str_cmp
    test    eax, eax
    jnz     .ha_true
.ha_dyn_next:
    mov     rbx, [rbx]
    jmp     .ha_dyn_loop

.ha_tbl:
    mov     rcx, r12
    mov     rdx, r13
    call    _pyfasm_attr_lookup_entry
    cmp     rax, 0
    jge     .ha_true
    xor     eax, eax
    jmp     .ha_done
.ha_true:
    mov     eax, 1
.ha_done:
    lea     rsp, [rbp - 24]
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_setattr:
    ; RCX = obj, RDX = attr_name_str, R8 = val -> RAX = 0 (None)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 48
    and     rsp, -16

    mov     r12, rcx
    mov     r13, rdx
    mov     r14, r8

    ; Update static offset directly if declared in table
    call    _pyfasm_attr_lookup_entry
    cmp     rax, 0
    jl      .sa_dyn
    mov     [r12 + rax], r14
    xor     eax, eax
    jmp     .sa_done

.sa_dyn:
    mov     rbx, [_pyfasm_dyn_attrs_head]
.sa_loop:
    test    rbx, rbx
    jz      .sa_alloc
    cmp     [rbx + 8], r12
    jne     .sa_next
    mov     rcx, [rbx + 16]
    mov     rdx, r13
    call    _pyfasm_str_cmp
    test    eax, eax
    jz      .sa_next
    mov     [rbx + 24], r14
    xor     eax, eax
    jmp     .sa_done
.sa_next:
    mov     rbx, [rbx]
    jmp     .sa_loop

.sa_alloc:
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     rcx, [_pyfasm_dyn_attrs_head]
    mov     [rax], rcx
    mov     [rax + 8], r12
    mov     [rax + 16], r13
    mov     [rax + 24], r14
    mov     [_pyfasm_dyn_attrs_head], rax
    xor     eax, eax

.sa_done:
    lea     rsp, [rbp - 32]
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; String Strip with Optional Chars (strip / lstrip / rstrip)
; ============================================================
_pyfasm_byte_in_chars:
    ; Internal leaf: AL = byte, RDX = chars_str (or 0 for whitespace) -> CF = 1 if match
    test    rdx, rdx
    jz      .bic_ws
    mov     r9, rdx
.bic_loop:
    mov     cl, [r9]
    test    cl, cl
    jz      .bic_no
    cmp     al, cl
    je      .bic_yes
    inc     r9
    jmp     .bic_loop
.bic_ws:
    cmp     al, ' '
    je      .bic_yes
    cmp     al, 9
    jb      .bic_no
    cmp     al, 13
    jbe     .bic_yes
.bic_no:
    clc
    ret
.bic_yes:
    stc
    ret

_pyfasm_str_strip_chars:
    ; RCX = target str, RDX = chars str (or 0 for whitespace), R8 = mode (0:both, 1:left, 2:right)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16

    mov     rsi, rcx
    mov     r12, rdx                ; chars
    mov     r13, r8                 ; mode
    test    rsi, rsi
    jz      .ssc_empty

    ; Find end (rdi -> last char index or end)
    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax                ; total byte len
    test    rbx, rbx
    jz      .ssc_empty
    lea     rdi, [rsi + rbx - 1]    ; rdi = pointer to last byte

    cmp     r13, 2                  ; rstrip only?
    je      .ssc_right
.ssc_left_loop:
    cmp     rsi, rdi
    ja      .ssc_empty
    mov     al, [rsi]
    mov     rdx, r12
    call    _pyfasm_byte_in_chars
    jnc     .ssc_right
    inc     rsi
    jmp     .ssc_left_loop

.ssc_right:
    cmp     r13, 1                  ; lstrip only?
    je      .ssc_copy
.ssc_right_loop:
    cmp     rdi, rsi
    jb      .ssc_empty
    mov     al, [rdi]
    mov     rdx, r12
    call    _pyfasm_byte_in_chars
    jnc     .ssc_copy
    dec     rdi
    jmp     .ssc_right_loop

.ssc_copy:
    cmp     rdi, rsi
    jb      .ssc_empty
    mov     rbx, rdi
    sub     rbx, rsi
    inc     rbx
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     r12, rax
    mov     rcx, rbx
    rep     movsb
    mov     byte [rdi], 0
    mov     rax, r12
    jmp     .ssc_done

.ssc_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0

.ssc_done:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; General Float Formatter (f, F, e, E, g, G)
; RCX = float64 bits, RDX = precision (-1 for default), R8 = format char ('f','F','e','E','g','G')
; ============================================================
_pyfasm_float_to_str_fmt:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 192
    and     rsp, -16

    mov     r12, rcx                ; raw float64 bits
    mov     r13, rdx                ; precision (-1 = default 6)
    mov     r14, r8                 ; fmt char ('f','F','e','E','g','G')

    cmp     r13, 0
    jge     .ffmt_p_cap
    mov     r13, 6
.ffmt_p_cap:
    cmp     r13, 15
    jle     .ffmt_p_ok
    mov     r13, 15
.ffmt_p_ok:

    ; Check uppercase vs lowercase for inf/nan/exp letter
    mov     byte [rsp + 160], 'e'
    cmp     r14, 'E'
    je      .ffmt_upper
    cmp     r14, 'G'
    je      .ffmt_upper
    cmp     r14, 'F'
    je      .ffmt_upper
    jmp     .ffmt_chk_special
.ffmt_upper:
    mov     byte [rsp + 160], 'E'

.ffmt_chk_special:
    mov     rax, [_pyfasm_flt_abs_mask]
    and     rax, r12
    cmp     rax, [_pyfasm_flt_inf]
    ja      .ffmt_nan
    jb      .ffmt_finite
    ; Infinite
    bt      r12, 63
    jc      .ffmt_ninf
    cmp     byte [rsp + 160], 'E'
    je      .ffmt_pinf_up
    lea     rax, [_pyfasm_str_inf_lo]
    jmp     .ffmt_done
.ffmt_pinf_up:
    lea     rax, [_pyfasm_str_inf_up]
    jmp     .ffmt_done
.ffmt_ninf:
    cmp     byte [rsp + 160], 'E'
    je      .ffmt_ninf_up
    lea     rax, [_pyfasm_str_ninf_lo]
    jmp     .ffmt_done
.ffmt_ninf_up:
    lea     rax, [_pyfasm_str_ninf_up]
    jmp     .ffmt_done
.ffmt_nan:
    cmp     byte [rsp + 160], 'E'
    je      .ffmt_nan_up
    lea     rax, [_pyfasm_str_nan_lo]
    jmp     .ffmt_done
.ffmt_nan_up:
    lea     rax, [_pyfasm_str_nan_up]
    jmp     .ffmt_done

.ffmt_finite:
    mov     ecx, 128
    call    _pyfasm_alloc
    mov     r15, rax                ; r15 = output base
    mov     rdi, rax                ; rdi = write cursor

    ; Extract sign and take |x|
    xor     ebx, ebx                ; ebx = neg flag
    bt      r12, 63
    jnc     .ffmt_abs_ok
    mov     ebx, 1
    mov     byte [rdi], '-'
    inc     rdi
    mov     rax, [_pyfasm_flt_abs_mask]
    and     r12, rax
.ffmt_abs_ok:
    movq    xmm0, r12               ; xmm0 = |x| >= 0

    ; Dispatch 'e'/'E' or 'g'/'G' or large 'f'/'F'
    cmp     r14, 'e'
    je      .ffmt_sci
    cmp     r14, 'E'
    je      .ffmt_sci
    cmp     r14, 'g'
    je      .ffmt_gen
    cmp     r14, 'G'
    je      .ffmt_gen

    ; Fixed 'f'/'F' format
    ucomisd xmm0, [_pyfasm_flt_1e15]
    jae     .ffmt_sci               ; avoid 64-bit integer overflow for huge fixed numbers
    mov     rcx, r13
    mov     rdx, rdi
    call    _pyfasm_ffmt_emit_fixed_pos
    mov     rdi, rax
    mov     byte [rdi], 0
    mov     rax, r15
    jmp     .ffmt_done

.ffmt_gen:
    ; Python 'g'/'G': sig_digits P = max(1, r13)
    cmp     r13, 1
    jge     .ffmt_g_pok
    mov     r13, 1
.ffmt_g_pok:
    xor     esi, esi                ; exp10 = 0
    xorpd   xmm1, xmm1
    ucomisd xmm0, xmm1
    je      .ffmt_g_fixed_zero
    ; Normalize xmm0 into [1.0, 10.0) to compute exp10
    call    _pyfasm_ffmt_norm10     ; returns xmm0 = mant in [1,10), rax = exp10
    mov     rsi, rax
    ; Round to r13 significant digits: frac_digits = r13 - 1
    lea     rcx, [r13 - 1]
    movsd   xmm4, [_pyfasm_flt_ten]
    movsd   xmm5, [_pyfasm_flt_one]
    mov     rax, rcx
.ffmt_g_pow:
    test    rax, rax
    jz      .ffmt_g_chk_ovf
    mulsd   xmm5, xmm4
    dec     rax
    jmp     .ffmt_g_pow
.ffmt_g_chk_ovf:
    movsd   xmm1, xmm0
    mulsd   xmm1, xmm5
    addsd   xmm1, [_pyfasm_flt_half]
    cvttsd2si rbx, xmm1             ; rounded integer with r13 digits
    ; Compute 10^r13 limit
    mov     rax, 1
    mov     rcx, r13
.ffmt_g_lim:
    test    rcx, rcx
    jz      .ffmt_g_lim_done
    imul    rax, 10
    dec     rcx
    jmp     .ffmt_g_lim
.ffmt_g_lim_done:
    cmp     rbx, rax
    jl      .ffmt_g_choose
    inc     rsi                     ; carry increased exponent (e.g. 9.999 -> 1.000e+1)
.ffmt_g_choose:
    ; Python rule: fixed if -4 <= exp10 < P (r13), else scientific
    cmp     rsi, -4
    jl      .ffmt_sci_normed
    cmp     rsi, r13
    jge     .ffmt_sci_normed
    ; Fixed with prec = P - 1 - exp10 (using un-normalized |x| in r12!)
    movq    xmm0, r12
    mov     rcx, r13
    dec     rcx
    sub     rcx, rsi
    cmp     rcx, 0
    jge     .ffmt_g_fok
    xor     ecx, ecx
.ffmt_g_fok:
    mov     rbx, rcx                ; save frac_digits
    mov     rdx, rdi
    call    _pyfasm_ffmt_emit_fixed_pos
    mov     rdi, rax
    ; Trim trailing zeros after decimal point for 'g'
    test    rbx, rbx
    jz      .ffmt_g_term
    mov     rcx, rdi
    call    _pyfasm_ffmt_trim_dot_zeros
    mov     rdi, rax
.ffmt_g_term:
    mov     byte [rdi], 0
    mov     rax, r15
    jmp     .ffmt_done

.ffmt_g_fixed_zero:
    mov     byte [rdi], '0'
    inc     rdi
    mov     byte [rdi], 0
    mov     rax, r15
    jmp     .ffmt_done

.ffmt_sci:
    ; Normalize xmm0 -> mant in [1,10), rsi = exp10; frac_digits = r13
    xor     esi, esi
    xorpd   xmm1, xmm1
    ucomisd xmm0, xmm1
    je      .ffmt_sci_emit
    call    _pyfasm_ffmt_norm10
    mov     rsi, rax
.ffmt_sci_emit:
    mov     rcx, r13                ; frac digits
    xor     ebx, ebx                ; do_trim = 0
    jmp     .ffmt_sci_core

.ffmt_sci_normed:
    ; Entered from 'g' (re-normalize from r12 to keep full mantissa precision)
    movq    xmm0, r12
    call    _pyfasm_ffmt_norm10
    mov     rsi, rax
    lea     rcx, [r13 - 1]          ; frac_digits = P - 1
    mov     ebx, 1                  ; do_trim = 1 (strip trailing zeros before 'e')

.ffmt_sci_core:
    ; xmm0 = mant in [1, 10) or 0.0, rsi = exp10, rcx = frac_digits, ebx = trim_zeros
    mov     [rsp + 40], rcx
    mov     [rsp + 48], rbx
    movsd   xmm4, [_pyfasm_flt_ten]
    movsd   xmm5, [_pyfasm_flt_one]
    mov     rax, rcx
.ffmt_sc_pow:
    test    rax, rax
    jz      .ffmt_sc_rnd
    mulsd   xmm5, xmm4
    dec     rax
    jmp     .ffmt_sc_pow
.ffmt_sc_rnd:
    mulsd   xmm0, xmm5
    addsd   xmm0, [_pyfasm_flt_half]
    cvttsd2si rbx, xmm0             ; rbx = integer mantissa with (frac+1) digits
    ; Check overflow (mant >= 10^(frac+1))
    mov     rax, 10
    mov     rcx, [rsp + 40]
.ffmt_sc_lim:
    test    rcx, rcx
    jz      .ffmt_sc_ovf_chk
    imul    rax, 10
    dec     rcx
    jmp     .ffmt_sc_lim
.ffmt_sc_ovf_chk:
    cmp     rbx, rax
    jl      .ffmt_sc_digits
    ; Divide rbx by 10, increment rsi (unless x == 0)
    mov     rax, rbx
    xor     edx, edx
    mov     rcx, 10
    div     rcx
    mov     rbx, rax
    inc     rsi
.ffmt_sc_digits:
    ; Extract (frac + 1) digits backwards into [rsp + 96 ..]
    mov     rcx, [rsp + 40]
    inc     rcx                     ; total digits >= 1
    lea     r8, [rsp + 140]
    mov     rax, rbx
    mov     r9, 10
.ffmt_sc_dloop:
    xor     edx, edx
    div     r9
    add     dl, '0'
    dec     r8
    mov     [r8], dl
    dec     rcx
    jnz     .ffmt_sc_dloop
    ; Write first digit
    mov     al, [r8]
    mov     [rdi], al
    inc     rdi
    inc     r8
    mov     rcx, [rsp + 40]
    test    rcx, rcx
    jz      .ffmt_sc_exp
    mov     byte [rdi], '.'
    inc     rdi
.ffmt_sc_floop:
    mov     al, [r8]
    mov     [rdi], al
    inc     rdi
    inc     r8
    dec     rcx
    jnz     .ffmt_sc_floop
    cmp     qword [rsp + 48], 0
    je      .ffmt_sc_exp
    mov     rcx, rdi
    call    _pyfasm_ffmt_trim_dot_zeros
    mov     rdi, rax
.ffmt_sc_exp:
    mov     al, [rsp + 160]
    mov     [rdi], al
    inc     rdi
    cmp     rsi, 0
    jge     .ffmt_sc_epos
    mov     byte [rdi], '-'
    inc     rdi
    neg     rsi
    jmp     .ffmt_sc_edig
.ffmt_sc_epos:
    mov     byte [rdi], '+'
    inc     rdi
.ffmt_sc_edig:
    cmp     rsi, 100
    jl      .ffmt_sc_e2
    mov     rax, rsi
    xor     edx, edx
    mov     rcx, 100
    div     rcx
    add     al, '0'
    mov     [rdi], al
    inc     rdi
    mov     rsi, rdx
.ffmt_sc_e2:
    mov     rax, rsi
    xor     edx, edx
    mov     rcx, 10
    div     rcx
    add     al, '0'
    mov     [rdi], al
    inc     rdi
    add     dl, '0'
    mov     [rdi], dl
    inc     rdi
    mov     byte [rdi], 0
    mov     rax, r15

.ffmt_done:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

; --- Helper subroutines for _pyfasm_float_to_str_fmt ---
_pyfasm_ffmt_norm10:
    ; XMM0 = |x| > 0 -> XMM0 in [1.0, 10.0), RAX = exp10
    xor     eax, eax
    movsd   xmm4, [_pyfasm_flt_ten]
    movsd   xmm5, [_pyfasm_flt_one]
.fn_big:
    ucomisd xmm0, xmm4
    jb      .fn_small
    divsd   xmm0, xmm4
    inc     rax
    cmp     rax, 350
    jl      .fn_big
    ret
.fn_small:
    ucomisd xmm0, xmm5
    jae     .fn_ok
    mulsd   xmm0, xmm4
    dec     rax
    cmp     rax, -350
    jg      .fn_small
.fn_ok:
    ret

_pyfasm_ffmt_trim_dot_zeros:
    ; RCX = write cursor end -> RAX = trimmed cursor end (trims trailing '0' and optional '.')
.ftdz_loop:
    dec     rcx
    cmp     byte [rcx], '0'
    je      .ftdz_loop
    cmp     byte [rcx], '.'
    je      .ftdz_end
    inc     rcx
.ftdz_end:
    mov     rax, rcx
    ret

_pyfasm_ffmt_emit_fixed_pos:
    ; XMM0 = |x| (< 1e15), RCX = frac_digits (0..15), RDX = write cursor -> RAX = updated cursor
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 96
    and     rsp, -16

    mov     rsi, rcx                ; rsi = frac_digits
    mov     rdi, rdx                ; rdi = write cursor
    movsd   xmm4, [_pyfasm_flt_ten]
    movsd   xmm5, [_pyfasm_flt_one]
    mov     rax, rsi
.fef_pow:
    test    rax, rax
    jz      .fef_calc
    mulsd   xmm5, xmm4
    dec     rax
    jmp     .fef_pow
.fef_calc:
    mulsd   xmm0, xmm5
    addsd   xmm0, [_pyfasm_flt_half]
    cvttsd2si rax, xmm0             ; scaled integer
    xor     ebx, ebx                ; ebx = total digits count
    lea     r9, [rsp + 80]          ; backwards buffer at [rsp+40..80]
    mov     r10, 10
    mov     rcx, rsi                ; frac digit loop counter
.fef_frac_ext:
    test    rcx, rcx
    jz      .fef_int_start
    xor     edx, edx
    div     r10
    add     dl, '0'
    dec     r9
    mov     [r9], dl
    inc     ebx
    dec     rcx
    jmp     .fef_frac_ext
.fef_int_start:
    test    rax, rax
    jnz     .fef_int_loop
    dec     r9
    mov     byte [r9], '0'
    inc     ebx
    jmp     .fef_emit
.fef_int_loop:
    test    rax, rax
    jz      .fef_emit
    xor     edx, edx
    div     r10
    add     dl, '0'
    dec     r9
    mov     [r9], dl
    inc     ebx
    jmp     .fef_int_loop
.fef_emit:
    ; Write integer digits = ebx - esi
    mov     eax, ebx
    sub     eax, esi
.fef_wint:
    mov     dl, [r9]
    mov     [rdi], dl
    inc     rdi
    inc     r9
    dec     eax
    jnz     .fef_wint
    test    esi, esi
    jz      .fef_done
    mov     byte [rdi], '.'
    inc     rdi
    mov     rcx, rsi
.fef_wfrac:
    mov     dl, [r9]
    mov     [rdi], dl
    inc     rdi
    inc     r9
    dec     rcx
    jnz     .fef_wfrac
.fef_done:
    mov     rax, rdi
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; String ordering, string-list sort, list reverse and remove
; ============================================================
_pyfasm_str_order:
    ; RCX = str a, RDX = str b -> RAX = -1 / 0 / 1 (byte-wise, equals code point order for UTF-8)
    cmp     rcx, 65536
    jb      .so_a_null
    cmp     rdx, 65536
    jb      .so_gt
.so_loop:
    movzx   eax, byte [rcx]
    movzx   r10d, byte [rdx]
    cmp     eax, r10d
    jb      .so_lt
    ja      .so_gt
    test    eax, eax
    jz      .so_eq
    inc     rcx
    inc     rdx
    jmp     .so_loop
.so_a_null:
    cmp     rdx, 65536
    jb      .so_eq
.so_lt:
    mov     rax, -1
    ret
.so_gt:
    mov     eax, 1
    ret
.so_eq:
    xor     eax, eax
    ret

_pyfasm_list_sort_str:
    ; RCX = list of str pointers, sorted in place (stable insertion sort) -> RAX = list
    test    rcx, rcx
    jnz     .lss_start
    xor     eax, eax
    ret
.lss_start:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    mov     rdi, rcx
    mov     r12, [rdi]              ; r12 = len
    mov     rsi, 1                  ; rsi = i
.lss_outer:
    cmp     rsi, r12
    jge     .lss_done
    mov     r13, [rdi + rsi * 8 + 8] ; r13 = key
    mov     rbx, rsi                ; rbx = j
.lss_inner:
    test    rbx, rbx
    jz      .lss_place
    mov     rcx, [rdi + rbx * 8]    ; item[j - 1]
    mov     rdx, r13
    call    _pyfasm_str_order
    cmp     rax, 0
    jle     .lss_place
    mov     rax, [rdi + rbx * 8]
    mov     [rdi + rbx * 8 + 8], rax
    dec     rbx
    jmp     .lss_inner
.lss_place:
    mov     [rdi + rbx * 8 + 8], r13
    inc     rsi
    jmp     .lss_outer
.lss_done:
    mov     rax, rdi
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret

_pyfasm_list_reverse:
    ; RCX = list pointer, reversed in place -> RAX = list
    mov     rax, rcx
    test    rcx, rcx
    jz      .lrv_ret
    mov     r10, [rcx]
    lea     rdx, [rcx + 8]          ; left
    lea     r10, [rcx + r10 * 8]    ; right = last item
.lrv_loop:
    cmp     rdx, r10
    jae     .lrv_ret
    mov     r8, [rdx]
    mov     r9, [r10]
    mov     [rdx], r9
    mov     [r10], r8
    add     rdx, 8
    sub     r10, 8
    jmp     .lrv_loop
.lrv_ret:
    ret

_pyfasm_list_remove:
    ; RCX = list pointer, RDX = value -> removes first equal item, RAX = 1 if removed
    xor     eax, eax
    test    rcx, rcx
    jz      .lrm_ret
    mov     r10, [rcx]              ; len
    xor     r11, r11                ; index
.lrm_find:
    cmp     r11, r10
    jge     .lrm_ret
    cmp     [rcx + r11 * 8 + 8], rdx
    je      .lrm_shift
    inc     r11
    jmp     .lrm_find
.lrm_shift:
    inc     r11
    cmp     r11, r10
    jge     .lrm_shrink
    mov     r8, [rcx + r11 * 8 + 8]
    mov     [rcx + r11 * 8], r8
    jmp     .lrm_shift
.lrm_shrink:
    dec     qword [rcx]
    mov     eax, 1
.lrm_ret:
    ret

_pyfasm_list_remove_str:
    ; RCX = list of str pointers, RDX = str -> removes first equal string, RAX = 1 if removed
    test    rcx, rcx
    jnz     .lrs_start
    xor     eax, eax
    ret
.lrs_start:
    push    rbx
    push    rsi
    push    rdi
    mov     rdi, rcx
    mov     rsi, rdx
    xor     rbx, rbx
.lrs_find:
    cmp     rbx, [rdi]
    jge     .lrs_none
    mov     rcx, [rdi + rbx * 8 + 8]
    cmp     rcx, rsi
    je      .lrs_hit
    mov     rdx, rsi
    call    _pyfasm_str_order
    test    rax, rax
    jz      .lrs_hit
    inc     rbx
    jmp     .lrs_find
.lrs_hit:
    mov     rcx, rdi
    mov     rdx, [rdi + rbx * 8 + 8]
    call    _pyfasm_list_remove
    jmp     .lrs_ret
.lrs_none:
    xor     eax, eax
.lrs_ret:
    pop     rdi
    pop     rsi
    pop     rbx
    ret
""" + get_eval_x64_code()
