"""
Native Win64 Data-Driven Matplotlib Engine for PyFASM.
Renders Figures, Subplots, Lines, Scatter, Bars, Histograms, H/VLines,
Fill-Between, Text, Gridlines, Spines, Axis Ticks, and Legend via GDI
double-buffering, plus 24-bit DIB BMP export for savefig().
"""

WIN64_MPL_RUNTIME_DATA = r"""
    ; --- Native Data-Driven Matplotlib Engine State ---
    _pyfasm_mpl_cur_fig         dq 0
    _pyfasm_mpl_cur_ax          dq 0
    _pyfasm_mpl_tab10           dd 00B4771Fh, 000E7FFFh, 002CA02Ch, 002827D6h, 00BD6794h, 004B568Ch, 00C277E3h, 007F7F7Fh, 0022BCBDh, 00CFBE17h
    _pyfasm_mpl_f_zero          dq 0.0
    _pyfasm_mpl_f_one           dq 1.0
    _pyfasm_mpl_f_half          dq 0.5
    _pyfasm_mpl_f_tiny          dq 1.0e-9
    _pyfasm_mpl_f_pad           dq 0.05
    _pyfasm_mpl_f_big           dq 1.0e300
    _pyfasm_mpl_f_nbig          dq -1.0e300
    _pyfasm_mpl_f_four          dq 4.0
    _pyfasm_mpl_wbuf            rw 512
    _pyfasm_mpl_bmp_hdr         rb 54
"""

WIN64_MPL_RUNTIME_CODE = r"""
; ============================================================================
; Matplotlib Native Data-Driven Engine (Win64 GDI + DIB BMP)
; Struct layouts:
;   PYFMFIG! (96 bytes):
;     +0: magic, +8: width_px, +16: height_px, +24: dpi, +32: bg_bgr(u32),
;     +40: axes_arr_ptr, +48: axes_count, +56: axes_cap, +64: suptitle_ptr,
;     +72: canvas_hwnd, +80: fg_bgr(u32)
;   PYFMAXS! (208 bytes):
;     +0: magic, +8: fig_ptr, +16: nrows, +24: ncols, +32: index(1-based),
;     +40: bg_bgr(u32), +48: fg_bgr(u32), +56: spine_bgr(u32),
;     +64: grid_on(u32), +68: grid_bgr(u32), +72: legend_on(u32),
;     +80: title_ptr, +88: xlabel_ptr, +96: ylabel_ptr,
;     +104: has_xlim(u32), +108: has_ylim(u32),
;     +112: xmin(f64), +120: xmax(f64), +128: ymin(f64), +136: ymax(f64),
;     +144: art_arr_ptr, +152: art_count, +160: art_cap, +168: color_cycle_idx
;   PYFMART! (72 bytes):
;     +0: magic, +8: kind(1=line,2=scatter,3=bar,4=hline,5=vline,6=fill,7=text,8=hist),
;     +16: x_arr_ptr or x_f64, +24: y_arr_ptr or y_f64,
;     +32: aux_ptr (y2_arr or text_str), +40: color_bgr(u32),
;     +44: lw_or_size(u32), +48: style_flags(u32), +56: label_ptr
; ============================================================================

_pyfasm_mpl_val_to_f64:
    ; RAX = tagged-less int48 or f64 bits -> XMM0 = float64, EAX = 1 if finite else 0
    mov     rcx, rax
    sar     rcx, 48
    test    rcx, rcx
    jz      .mvf_int
    cmp     rcx, -1
    je      .mvf_int
    mov     rdx, 7FF0000000000000h
    mov     rcx, rax
    and     rcx, rdx
    cmp     rcx, rdx
    je      .mvf_nan
    movq    xmm0, rax
    mov     eax, 1
    ret
.mvf_int:
    cvtsi2sd xmm0, rax
    mov     eax, 1
    ret
.mvf_nan:
    pxor    xmm0, xmm0
    xor     eax, eax
    ret

_pyfasm_mpl_str_eq_ci:
    ; RCX = s1 (UTF-8), RDX = s2 (ASCII lower) -> EAX = 1 if equal else 0
    test    rcx, rcx
    jz      .mseq_no
    test    rdx, rdx
    jz      .mseq_no
.mseq_loop:
    movzx   eax, byte [rcx]
    cmp     al, 'A'
    jb      .mseq_lo
    cmp     al, 'Z'
    ja      .mseq_lo
    add     al, 32
.mseq_lo:
    movzx   r8d, byte [rdx]
    cmp     al, r8b
    jne     .mseq_no
    test    al, al
    jz      .mseq_yes
    inc     rcx
    inc     rdx
    jmp     .mseq_loop
.mseq_yes:
    mov     eax, 1
    ret
.mseq_no:
    xor     eax, eax
    ret

_pyfasm_mpl_hex_nibble:
    ; AL = ASCII char -> EAX = 0..15 or -1
    cmp     al, '0'
    jb      .mhn_bad
    cmp     al, '9'
    ja      .mhn_af
    sub     al, '0'
    movzx   eax, al
    ret
.mhn_af:
    cmp     al, 'A'
    jb      .mhn_lo
    cmp     al, 'F'
    ja      .mhn_lo
    sub     al, 'A' - 10
    movzx   eax, al
    ret
.mhn_lo:
    cmp     al, 'a'
    jb      .mhn_bad
    cmp     al, 'f'
    ja      .mhn_bad
    sub     al, 'a' - 10
    movzx   eax, al
    ret
.mhn_bad:
    mov     eax, -1
    ret

_pyfasm_mpl_parse_color:
    ; RCX = str_ptr_or_0, RDX = cycle_idx -> EAX = 0x00BBGGRR
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx

    cmp     rbx, 10000h
    jb      .mpc_cycle

    movzx   eax, byte [rbx]
    cmp     al, '#'
    jne     .mpc_named

    ; Check #RGB vs #RRGGBB
    xor     ecx, ecx
.mpc_len:
    cmp     byte [rbx + 1 + rcx], 0
    je      .mpc_got_len
    inc     ecx
    cmp     ecx, 8
    jb      .mpc_len
.mpc_got_len:
    cmp     ecx, 6
    jb      .mpc_short_hex
    ; #RRGGBB -> 00BBGGRR
    mov     al, byte [rbx + 1]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    shl     eax, 4
    mov     r8d, eax
    mov     al, byte [rbx + 2]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    or      r8d, eax            ; R
    mov     al, byte [rbx + 3]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    shl     eax, 4
    mov     r9d, eax
    mov     al, byte [rbx + 4]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    or      r9d, eax            ; G
    mov     al, byte [rbx + 5]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    shl     eax, 4
    mov     r10d, eax
    mov     al, byte [rbx + 6]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    or      r10d, eax           ; B
    shl     r10d, 16
    shl     r9d, 8
    mov     eax, r10d
    or      eax, r9d
    or      eax, r8d
    jmp     .mpc_done

.mpc_short_hex:
    cmp     ecx, 3
    jne     .mpc_cycle
    mov     al, byte [rbx + 1]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    imul    r8d, eax, 17
    mov     al, byte [rbx + 2]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    imul    r9d, eax, 17
    mov     al, byte [rbx + 3]
    call    _pyfasm_mpl_hex_nibble
    cmp     eax, 0
    jl      .mpc_cycle
    imul    r10d, eax, 17
    shl     r10d, 16
    shl     r9d, 8
    mov     eax, r10d
    or      eax, r9d
    or      eax, r8d
    jmp     .mpc_done

.mpc_named:
    ; Single-char matplotlib codes
    cmp     byte [rbx + 1], 0
    jne     .mpc_words
    movzx   eax, byte [rbx]
    cmp     al, 'r'
    je      .c_red
    cmp     al, 'g'
    je      .c_green
    cmp     al, 'b'
    je      .c_blue
    cmp     al, 'c'
    je      .c_cyan
    cmp     al, 'm'
    je      .c_mag
    cmp     al, 'y'
    je      .c_yellow
    cmp     al, 'k'
    je      .c_black
    cmp     al, 'w'
    je      .c_white
    jmp     .mpc_cycle

.mpc_words:
    mov     rcx, rbx
    lea     rdx, [.s_red]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_red
    mov     rcx, rbx
    lea     rdx, [.s_blue]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_blue
    mov     rcx, rbx
    lea     rdx, [.s_green]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_green
    mov     rcx, rbx
    lea     rdx, [.s_cyan]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_cyan
    mov     rcx, rbx
    lea     rdx, [.s_magenta]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_mag
    mov     rcx, rbx
    lea     rdx, [.s_yellow]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_yellow
    mov     rcx, rbx
    lea     rdx, [.s_black]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_black
    mov     rcx, rbx
    lea     rdx, [.s_white]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_white
    mov     rcx, rbx
    lea     rdx, [.s_orange]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_orange
    mov     rcx, rbx
    lea     rdx, [.s_purple]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_purple
    mov     rcx, rbx
    lea     rdx, [.s_gray]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_gray
    mov     rcx, rbx
    lea     rdx, [.s_grey]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .c_gray
    jmp     .mpc_cycle

.c_red:     mov eax, 00241CD6h
            jmp .mpc_done
.c_green:   mov eax, 002CA02Ch
            jmp .mpc_done
.c_blue:    mov eax, 00B4771Fh
            jmp .mpc_done
.c_cyan:    mov eax, 00CFBE17h
            jmp .mpc_done
.c_mag:     mov eax, 00BF00BFh
            jmp .mpc_done
.c_yellow:  mov eax, 0000D7FFh
            jmp .mpc_done
.c_black:   mov eax, 00111111h
            jmp .mpc_done
.c_white:   mov eax, 00FFFFFFh
            jmp .mpc_done
.c_orange:  mov eax, 000E7FFFh
            jmp .mpc_done
.c_purple:  mov eax, 00BD6794h
            jmp .mpc_done
.c_gray:    mov eax, 00808080h
            jmp .mpc_done

.mpc_cycle:
    mov     rax, rsi
    cqo
    mov     ecx, 10
    idiv    rcx
    test    rdx, rdx
    jge     .mpc_idx_ok
    add     rdx, 10
.mpc_idx_ok:
    mov     eax, dword [_pyfasm_mpl_tab10 + rdx * 4]
.mpc_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

.s_red      db 'red', 0
.s_blue     db 'blue', 0
.s_green    db 'green', 0
.s_cyan     db 'cyan', 0
.s_magenta  db 'magenta', 0
.s_yellow   db 'yellow', 0
.s_black    db 'black', 0
.s_white    db 'white', 0
.s_orange   db 'orange', 0
.s_purple   db 'purple', 0
.s_gray     db 'gray', 0
.s_grey     db 'grey', 0

_pyfasm_mpl_make_range_x:
    ; RCX = count -> RAX = newly allocated [count, 0.0, 1.0, ...] list
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jg      .mrx_ok
    mov     ebx, 1
.mrx_ok:
    lea     rcx, [rbx + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     [rax], rbx
    xor     esi, esi
.mrx_lp:
    cmp     rsi, rbx
    jge     .mrx_done
    cvtsi2sd xmm0, rsi
    movq    rdx, xmm0
    mov     [rax + 8 + rsi * 8], rdx
    inc     rsi
    jmp     .mrx_lp
.mrx_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_figure_new:
    ; RCX = width_px (0->640), RDX = height_px (0->480), R8 = dpi (0->100), R9 = bg_str_or_0 -> RAX = PYFMFIG!
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9

    test    rbx, rbx
    jg      .mfn_w
    mov     ebx, 640
.mfn_w:
    test    rsi, rsi
    jg      .mfn_h
    mov     esi, 480
.mfn_h:
    test    rdi, rdi
    jg      .mfn_d
    mov     edi, 100
.mfn_d:
    mov     ecx, 96
    call    _pyfasm_alloc
    mov     r8, 5059464D46494721h ; 'PYFMFIG!'
    mov     [rax + 0], r8
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     [rax + 24], rdi
    mov     dword [rax + 32], 00FFFFFFh
    mov     qword [rax + 48], 0
    mov     qword [rax + 56], 16
    mov     qword [rax + 64], 0
    mov     qword [rax + 72], 0
    mov     dword [rax + 80], 00111111h
    mov     rbx, rax

    test    r12, r12
    jz      .mfn_arr
    mov     rcx, r12
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     dword [rbx + 32], eax
.mfn_arr:
    mov     ecx, 128
    call    _pyfasm_alloc
    mov     [rbx + 40], rax
    mov     [_pyfasm_mpl_cur_fig], rbx
    mov     rax, rbx
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_gcf:
    ; -> RAX = current PYFMFIG! (creates default if 0)
    mov     rax, [_pyfasm_mpl_cur_fig]
    test    rax, rax
    jz      .mgcf_new
    ret
.mgcf_new:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    xor     ecx, ecx
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_mpl_figure_new
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_fig_add_subplot:
    ; RCX = fig_or_0, RDX = nrows(0->1), R8 = ncols(0->1), R9 = index(0->1) -> RAX = PYFMAXS!
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16

    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    test    rbx, rbx
    jnz     .mas_fig
    call    _pyfasm_mpl_gcf
    mov     rbx, rax
.mas_fig:
    cmp     rsi, 0
    jg      .mas_r
    mov     esi, 1
.mas_r:
    cmp     rdi, 0
    jg      .mas_c
    mov     edi, 1
.mas_c:
    cmp     r12, 0
    jg      .mas_i
    mov     r12d, 1
.mas_i:
    ; Reuse matching subplot if already registered
    mov     rcx, [rbx + 48]
    xor     edx, edx
.mas_find:
    cmp     rdx, rcx
    jge     .mas_alloc
    mov     rax, [rbx + 40]
    mov     rax, [rax + rdx * 8]
    cmp     [rax + 16], rsi
    jne     .mas_next
    cmp     [rax + 24], rdi
    jne     .mas_next
    cmp     [rax + 32], r12
    jne     .mas_next
    mov     [_pyfasm_mpl_cur_ax], rax
    jmp     .mas_done
.mas_next:
    inc     rdx
    jmp     .mas_find

.mas_alloc:
    mov     ecx, 208
    call    _pyfasm_alloc
    mov     r8, 5059464D41585321h ; 'PYFMAXS!'
    mov     [rax + 0], r8
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     [rax + 24], rdi
    mov     [rax + 32], r12
    mov     dword [rax + 40], 00FFFFFFh
    mov     dword [rax + 48], 00111111h
    mov     dword [rax + 56], 00333333h
    mov     dword [rax + 64], 0
    mov     dword [rax + 68], 00DCDCDCh
    mov     dword [rax + 72], 0
    mov     qword [rax + 80], 0
    mov     qword [rax + 88], 0
    mov     qword [rax + 96], 0
    mov     qword [rax + 104], 0
    mov     qword [rax + 144], 0
    mov     qword [rax + 152], 0
    mov     qword [rax + 160], 64
    mov     qword [rax + 168], 0
    mov     rsi, rax
    mov     ecx, 512
    call    _pyfasm_alloc
    mov     [rsi + 144], rax

    mov     rcx, [rbx + 48]
    cmp     rcx, [rbx + 56]
    jge     .mas_ret_new
    inc     qword [rbx + 48]
    mov     rdx, [rbx + 40]
    mov     [rdx + rcx * 8], rsi
.mas_ret_new:
    mov     [_pyfasm_mpl_cur_fig], rbx
    mov     [_pyfasm_mpl_cur_ax], rsi
    mov     rax, rsi
.mas_done:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_gca:
    ; -> RAX = current PYFMAXS!
    mov     rax, [_pyfasm_mpl_cur_ax]
    test    rax, rax
    jz      .mgca_new
    ret
.mgca_new:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 1
    mov     r9d, 1
    call    _pyfasm_mpl_fig_add_subplot
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_plt_subplots:
    ; RCX = nrows, RDX = ncols, R8 = width_px, R9 = height_px -> RAX = [2, fig_ptr, ax_or_grid]
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

    cmp     rcx, 0
    jg      .mps_nr
    mov     ecx, 1
.mps_nr:
    cmp     rdx, 0
    jg      .mps_nc
    mov     edx, 1
.mps_nc:
    mov     r12, rcx            ; nrows
    mov     r13, rdx            ; ncols
    mov     rcx, r8
    mov     rdx, r9
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_mpl_figure_new
    mov     r14, rax            ; fig

    mov     rax, r12
    imul    rax, r13
    cmp     rax, 1
    jne     .mps_grid
    ; 1x1 -> (fig, ax)
    mov     rcx, r14
    mov     edx, 1
    mov     r8d, 1
    mov     r9d, 1
    call    _pyfasm_mpl_fig_add_subplot
    mov     r15, rax
    jmp     .mps_pack

.mps_grid:
    cmp     r12, 1
    je      .mps_1d
    cmp     r13, 1
    je      .mps_1d
    ; 2D list of rows
    lea     rcx, [r12 + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     r15, rax
    mov     [r15], r12
    xor     ebx, ebx
    mov     esi, 1
.mps_r_lp:
    cmp     rbx, r12
    jge     .mps_pack
    lea     rcx, [r13 + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rdi], r13
    mov     [r15 + 8 + rbx * 8], rdi
    xor     eax, eax
    mov     [rsp + 32], rax
.mps_c_lp:
    mov     rax, [rsp + 32]
    cmp     rax, r13
    jge     .mps_r_next
    mov     rcx, r14
    mov     rdx, r12
    mov     r8, r13
    mov     r9, rsi
    call    _pyfasm_mpl_fig_add_subplot
    mov     rdx, [rsp + 32]
    mov     [rdi + 8 + rdx * 8], rax
    inc     rsi
    inc     qword [rsp + 32]
    jmp     .mps_c_lp
.mps_r_next:
    inc     rbx
    jmp     .mps_r_lp

.mps_1d:
    mov     rdi, r12
    imul    rdi, r13
    lea     rcx, [rdi + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     r15, rax
    mov     [r15], rdi
    xor     ebx, ebx
.mps_1d_lp:
    cmp     rbx, rdi
    jge     .mps_pack
    mov     rcx, r14
    mov     rdx, r12
    mov     r8, r13
    lea     r9, [rbx + 1]
    call    _pyfasm_mpl_fig_add_subplot
    mov     [r15 + 8 + rbx * 8], rax
    inc     rbx
    jmp     .mps_1d_lp

.mps_pack:
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     [rax + 8], r14
    mov     [rax + 16], r15
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

_pyfasm_mpl_resolve_ax:
    ; RCX = ax_or_0 -> RAX = PYFMAXS!
    test    rcx, rcx
    jz      _pyfasm_mpl_gca
    mov     r10, 5059464D41585321h
    cmp     [rcx], r10
    jne     _pyfasm_mpl_gca
    mov     rax, rcx
    ret

_pyfasm_mpl_add_artist:
    ; RCX = ax, RDX = art_ptr
    test    rcx, rcx
    jz      .maa_d
    mov     rax, [rcx + 152]
    cmp     rax, [rcx + 160]
    jge     .maa_d
    inc     qword [rcx + 152]
    mov     r8, [rcx + 144]
    mov     [r8 + rax * 8], rdx
.maa_d:
    ret

_pyfasm_mpl_invalidate_ax:
    ; RCX = ax
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .mia_d
    mov     rax, [rcx + 8]
    test    rax, rax
    jz      .mia_d
    mov     rcx, [rax + 72]
    test    rcx, rcx
    jz      .mia_d
    xor     edx, edx
    xor     r8d, r8d
    call    [InvalidateRect]
.mia_d:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_fig_clear:
    ; RCX = fig_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .mfc_have
    call    _pyfasm_mpl_gcf
    mov     rcx, rax
.mfc_have:
    mov     rbx, rcx
    mov     qword [rbx + 48], 0
    mov     qword [_pyfasm_mpl_cur_ax], 0
    mov     rcx, [rbx + 72]
    test    rcx, rcx
    jz      .mfc_d
    xor     edx, edx
    xor     r8d, r8d
    call    [InvalidateRect]
.mfc_d:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_clear:
    ; RCX = ax_or_fig_or_listbox_or_0
    test    rcx, rcx
    jz      .mac_gca
    mov     rax, 5059464D41585321h ; 'PYFMAXS!'
    cmp     [rcx], rax
    je      .mac_ax
    mov     rax, 5059464D46494721h ; 'PYFMFIG!'
    cmp     [rcx], rax
    je      _pyfasm_mpl_fig_clear
    jmp     _pyfasm_listbox_clear
.mac_gca:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_mpl_gca
    mov     rcx, rax
    mov     rsp, rbp
    pop     rbp
.mac_ax:
    mov     qword [rcx + 152], 0
    mov     qword [rcx + 168], 0
    mov     qword [rcx + 104], 0
    jmp     _pyfasm_mpl_invalidate_ax

_pyfasm_mpl_fig_suptitle:
    ; RCX = fig_or_0, RDX = title_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    test    rcx, rcx
    jnz     .mfst_have
    call    _pyfasm_mpl_gcf
    mov     rcx, rax
.mfst_have:
    mov     [rcx + 64], rbx
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_plot:
    ; RCX=ax_or_0, RDX=x_arr_or_0, R8=y_arr, R9=color_str_or_0, [rbp+48]=lw, [rbp+56]=style_flags, [rbp+64]=label_str_or_0
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

    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax

    test    rdi, rdi
    jz      .map_done
    test    rsi, rsi
    jnz     .map_have_x
    mov     rcx, [rdi]
    call    _pyfasm_mpl_make_range_x
    mov     rsi, rax
.map_have_x:
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h ; 'PYFMART!'
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 1
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     qword [r13 + 32], 0
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [r13 + 40], eax
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .map_lw
    mov     eax, 2
.map_lw:
    mov     dword [r13 + 44], eax
    mov     eax, dword [rbp + 56]
    mov     dword [r13 + 48], eax
    mov     rax, [rbp + 64]
    mov     [r13 + 56], rax

    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
.map_done:
    mov     rax, r13
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

_pyfasm_mpl_axes_scatter:
    ; RCX=ax_or_0, RDX=x_arr, R8=y_arr, R9=color_str_or_0, [rbp+48]=size_px, [rbp+56]=label_str_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    test    rsi, rsi
    jz      .masc_d
    test    rdi, rdi
    jz      .masc_d
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 2
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     qword [r13 + 32], 0
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [r13 + 40], eax
    mov     rax, [rbp + 48]
    cmp     rax, 2
    jge     .masc_sz
    mov     eax, 6
.masc_sz:
    mov     dword [r13 + 44], eax
    mov     dword [r13 + 48], 0
    mov     rax, [rbp + 56]
    mov     [r13 + 56], rax
    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
.masc_d:
    mov     rax, r13
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_bar:
    ; RCX=ax_or_0, RDX=x_arr, R8=height_arr, R9=color_str_or_0, [rbp+48]=label_str_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    test    rdi, rdi
    jz      .mab_d
    test    rsi, rsi
    jnz     .mab_xok
    mov     rcx, [rdi]
    call    _pyfasm_mpl_make_range_x
    mov     rsi, rax
.mab_xok:
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 3
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     qword [r13 + 32], 0
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [r13 + 40], eax
    mov     dword [r13 + 44], 1
    mov     dword [r13 + 48], 0
    mov     rax, [rbp + 48]
    mov     [r13 + 56], rax
    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
.mab_d:
    mov     rax, r13
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_hist:
    ; RCX=ax_or_0, RDX=data_arr, R8=bins_int, R9=color_str_or_0, [rbp+48]=label_str_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    test    rsi, rsi
    jz      .mah_done
    mov     r14, [rsi]
    cmp     r14, 0
    jle     .mah_done

    cmp     rdi, 1
    jge     .mah_bins_ok
    mov     edi, 10
.mah_bins_ok:
    cmp     rdi, 256
    jle     .mah_bins_cap
    mov     edi, 256
.mah_bins_cap:
    movsd   xmm1, qword [_pyfasm_mpl_f_big]
    movsd   xmm2, qword [_pyfasm_mpl_f_nbig]
    xor     r15d, r15d
.mah_minmax:
    cmp     r15, r14
    jge     .mah_got_mm
    mov     rax, [rsi + 8 + r15 * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mah_mm_next
    minsd   xmm1, xmm0
    maxsd   xmm2, xmm0
.mah_mm_next:
    inc     r15
    jmp     .mah_minmax

.mah_got_mm:
    movsd   xmm3, xmm2
    subsd   xmm3, xmm1
    ucomisd xmm3, qword [_pyfasm_mpl_f_tiny]
    ja      .mah_span_ok
    addsd   xmm2, qword [_pyfasm_mpl_f_half]
    subsd   xmm1, qword [_pyfasm_mpl_f_half]
    movsd   xmm3, xmm2
    subsd   xmm3, xmm1
.mah_span_ok:
    movsd   qword [rsp + 32], xmm1
    movsd   qword [rsp + 40], xmm3

    lea     rcx, [rdi + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     r13, rax            ; centers_arr
    mov     [r13], rdi

    lea     rcx, [rdi + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     [rsp + 48], rax     ; counts_arr (zeroed by _pyfasm_alloc or zero loop)
    mov     [rax], rdi
    xor     ecx, ecx
.mah_z:
    cmp     rcx, rdi
    jge     .mah_fill
    mov     qword [rax + 8 + rcx * 8], 0
    inc     rcx
    jmp     .mah_z

.mah_fill:
    mov     r8, [rsp + 48]      ; counts_arr
    cvtsi2sd xmm4, rdi
    movsd   xmm1, qword [rsp + 32]
    movsd   xmm3, qword [rsp + 40]
    xor     r15d, r15d
.mah_bin_lp:
    cmp     r15, r14
    jge     .mah_centers
    mov     rax, [rsi + 8 + r15 * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mah_bin_next
    subsd   xmm0, xmm1
    divsd   xmm0, xmm3
    mulsd   xmm0, xmm4
    cvttsd2si ecx, xmm0
    cmp     ecx, 0
    jge     .mah_c_lo
    xor     ecx, ecx
.mah_c_lo:
    cmp     rcx, rdi
    jl      .mah_c_hi
    lea     rcx, [rdi - 1]
.mah_c_hi:
    inc     qword [r8 + 8 + rcx * 8]
.mah_bin_next:
    inc     r15
    jmp     .mah_bin_lp

.mah_centers:
    mov     r8, [rsp + 48]
    cvtsi2sd xmm4, rdi
    movsd   xmm3, qword [rsp + 40]
    divsd   xmm3, xmm4          ; bin_w
    movsd   xmm1, qword [rsp + 32]
    xor     ecx, ecx
.mah_cent_lp:
    cmp     rcx, rdi
    jge     .mah_art
    cvtsi2sd xmm0, rcx
    addsd   xmm0, qword [_pyfasm_mpl_f_half]
    mulsd   xmm0, xmm3
    addsd   xmm0, xmm1
    movq    rdx, xmm0
    mov     [r13 + 8 + rcx * 8], rdx
    ; Convert integer bin count -> float64
    cvtsi2sd xmm5, qword [r8 + 8 + rcx * 8]
    movq    rdx, xmm5
    mov     [r8 + 8 + rcx * 8], rdx
    inc     rcx
    jmp     .mah_cent_lp

.mah_art:
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     rsi, rax
    mov     rax, 5059464D41525421h
    mov     [rsi + 0], rax
    mov     qword [rsi + 8], 8
    mov     [rsi + 16], r13
    mov     rax, [rsp + 48]
    mov     [rsi + 24], rax
    mov     qword [rsi + 32], 0
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [rsi + 40], eax
    mov     dword [rsi + 44], 1
    mov     dword [rsi + 48], 0
    mov     rax, [rbp + 48]
    mov     [rsi + 56], rax
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
    mov     rax, rsi
.mah_done:
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

_pyfasm_mpl_axes_hline:
    ; RCX=ax_or_0, RDX=y_val, R8=color_or_0, R9=style_flags, [rbp+48]=label
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rax, rsi
    call    _pyfasm_mpl_val_to_f64
    movq    rsi, xmm0
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r8, 5059464D41525421h
    mov     [rax + 0], r8
    mov     qword [rax + 8], 4
    mov     qword [rax + 16], 0
    mov     [rax + 24], rsi
    mov     qword [rax + 32], 0
    mov     rsi, rax
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, rdi
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [rsi + 40], eax
    mov     dword [rsi + 44], 1
    mov     dword [rsi + 48], r12d
    mov     rax, [rbp + 48]
    mov     [rsi + 56], rax
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
    mov     rax, rsi
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_vline:
    ; RCX=ax_or_0, RDX=x_val, R8=color_or_0, R9=style_flags, [rbp+48]=label
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rax, rsi
    call    _pyfasm_mpl_val_to_f64
    movq    rsi, xmm0
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r8, 5059464D41525421h
    mov     [rax + 0], r8
    mov     qword [rax + 8], 5
    mov     [rax + 16], rsi
    mov     qword [rax + 24], 0
    mov     qword [rax + 32], 0
    mov     rsi, rax
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, rdi
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [rsi + 40], eax
    mov     dword [rsi + 44], 1
    mov     dword [rsi + 48], r12d
    mov     rax, [rbp + 48]
    mov     [rsi + 56], rax
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
    mov     rax, rsi
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_fill_between:
    ; RCX=ax_or_0, RDX=x_arr, R8=y1_arr, R9=y2_arr_or_0, [rbp+48]=color_or_0, [rbp+56]=label
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    test    rsi, rsi
    jz      .mafb_d
    test    rdi, rdi
    jz      .mafb_d
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 6
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     [r13 + 32], r12
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, [rbp + 48]
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    ; Lighten fill color toward white 60% so curves remain legible
    mov     ecx, eax
    and     ecx, 0FFh
    mov     edx, eax
    shr     edx, 8
    and     edx, 0FFh
    mov     r8d, eax
    shr     r8d, 16
    and     r8d, 0FFh
    add     ecx, 380
    shr     ecx, 2
    add     edx, 380
    shr     edx, 2
    add     r8d, 380
    shr     r8d, 2
    shl     r8d, 16
    shl     edx, 8
    or      ecx, edx
    or      ecx, r8d
    mov     dword [r13 + 40], ecx
    mov     dword [r13 + 44], 1
    mov     dword [r13 + 48], 0
    mov     rax, [rbp + 56]
    mov     [r13 + 56], rax
    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
.mafb_d:
    mov     rax, r13
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_text:
    ; RCX=ax_or_0, RDX=x_val, R8=y_val, R9=text_str, [rbp+48]=color_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rax, rsi
    call    _pyfasm_mpl_val_to_f64
    movq    rsi, xmm0
    mov     rax, rdi
    call    _pyfasm_mpl_val_to_f64
    movq    rdi, xmm0
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r8, 5059464D41525421h
    mov     [rax + 0], r8
    mov     qword [rax + 8], 7
    mov     [rax + 16], rsi
    mov     [rax + 24], rdi
    mov     [rax + 32], r12
    mov     rsi, rax
    mov     rcx, [rbp + 48]
    test    rcx, rcx
    jnz     .mat_col
    mov     eax, dword [rbx + 48]
    jmp     .mat_scol
.mat_col:
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
.mat_scol:
    mov     dword [rsi + 40], eax
    mov     dword [rsi + 44], 12
    mov     dword [rsi + 48], 0
    mov     qword [rsi + 56], 0
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_mpl_add_artist
    mov     rcx, rbx
    call    _pyfasm_mpl_invalidate_ax
    mov     rax, rsi
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_title:
    ; RCX = ax_or_0, RDX = title_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    call    _pyfasm_mpl_resolve_ax
    mov     [rax + 80], rbx
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_xlabel:
    ; RCX = ax_or_0, RDX = xlabel_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    call    _pyfasm_mpl_resolve_ax
    mov     [rax + 88], rbx
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_ylabel:
    ; RCX = ax_or_0, RDX = ylabel_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    call    _pyfasm_mpl_resolve_ax
    mov     [rax + 96], rbx
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_xlim:
    ; RCX = ax_or_0, RDX = xmin, R8 = xmax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rax, rsi
    call    _pyfasm_mpl_val_to_f64
    movsd   qword [rbx + 112], xmm0
    mov     rax, rdi
    call    _pyfasm_mpl_val_to_f64
    movsd   qword [rbx + 120], xmm0
    mov     dword [rbx + 104], 1
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_ylim:
    ; RCX = ax_or_0, RDX = ymin, R8 = ymax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rax, rsi
    call    _pyfasm_mpl_val_to_f64
    movsd   qword [rbx + 128], xmm0
    mov     rax, rdi
    call    _pyfasm_mpl_val_to_f64
    movsd   qword [rbx + 136], xmm0
    mov     dword [rbx + 108], 1
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_set_facecolor:
    ; RCX = fig_or_ax_or_0, RDX = color_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rcx, rdx
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     esi, eax
    test    rbx, rbx
    jz      .msfc_ax
    mov     rax, 5059464D46494721h
    cmp     [rbx], rax
    jne     .msfc_ax
    mov     dword [rbx + 32], esi
    jmp     .msfc_done
.msfc_ax:
    mov     rcx, rbx
    call    _pyfasm_mpl_resolve_ax
    mov     dword [rax + 40], esi
.msfc_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_grid:
    ; RCX = ax_or_0, RDX = visible(0/1), R8 = color_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     dword [rbx + 64], esi
    test    rdi, rdi
    jz      .mag_d
    mov     rcx, rdi
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     dword [rbx + 68], eax
.mag_d:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_legend:
    ; RCX = ax_or_0
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_mpl_resolve_ax
    mov     dword [rax + 72], 1
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_fgcolor:
    ; RCX = ax_or_0, RDX = color_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rcx, rsi
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     dword [rbx + 48], eax
    mov     rcx, [rbx + 8]
    test    rcx, rcx
    jz      .msfg_d
    mov     dword [rcx + 80], eax
.msfg_d:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_set_spine_color:
    ; RCX = ax_or_0, RDX = color_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    call    _pyfasm_mpl_resolve_ax
    mov     rbx, rax
    mov     rcx, rsi
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     dword [rbx + 56], eax
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_canvas_attach:
    ; RCX = fig_ptr, RDX = canvas_hwnd -> RAX = canvas_hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jnz     .mca_f
    call    _pyfasm_mpl_gcf
    mov     rbx, rax
.mca_f:
    mov     [rbx + 72], rsi
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .mca_d
    shl     rax, 6
    mov     qword [_pyfasm_widget_aux + rax + 48], rbx
.mca_d:
    mov     rax, rsi
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_canvas_widget:
    ; RCX = canvas_hwnd -> RAX = canvas_hwnd
    mov     rax, rcx
    ret

_pyfasm_mpl_canvas_draw:
    ; RCX = canvas_hwnd_or_fig_or_0
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .mcd_fig
    mov     rax, 5059464D46494721h
    cmp     [rcx], rax
    je      .mcd_have_fig
    jmp     .mcd_inv
.mcd_fig:
    call    _pyfasm_mpl_gcf
    mov     rcx, rax
.mcd_have_fig:
    mov     rcx, [rcx + 72]
.mcd_inv:
    test    rcx, rcx
    jz      .mcd_d
    xor     edx, edx
    xor     r8d, r8d
    call    [InvalidateRect]
.mcd_d:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_plt_show:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 64
    and     rsp, -16
    call    _pyfasm_mpl_gcf
    mov     rbx, rax
    mov     rcx, [rbx + 72]
    test    rcx, rcx
    jnz     .mpsh_loop
    ; Standalone plt.show() -> create host window + canvas
    call    _pyfasm_ensure_window
    mov     rcx, [_pyfasm_h_wnd]
    mov     rdx, [rbx + 8]      ; fig width
    mov     r8, [rbx + 16]      ; fig height
    call    _pyfasm_create_canvas
    mov     rsi, rax
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_mpl_canvas_attach
    mov     rcx, rsi
    xor     edx, edx
    mov     r8d, 3
    mov     r9d, 1
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    call    _pyfasm_widget_set_pack
    mov     rcx, [_pyfasm_h_wnd]
    call    _pyfasm_apply_layout
.mpsh_loop:
    call    _pyfasm_run_window_loop
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_draw_text_utf8:
    ; RCX = hdc, RDX = x, R8 = y, R9 = utf8_ptr -> EAX = wide_len
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     esi, edx
    mov     edi, r8d
    test    r9, r9
    jz      .mdtu_zero
    mov     rcx, r9
    lea     rdx, [_pyfasm_mpl_wbuf]
    mov     r8d, 510
    call    _pyfasm_utf8_to_wide
    cmp     eax, 1
    jle     .mdtu_zero
    dec     eax                 ; exclude trailing NUL
    mov     ecx, eax
    mov     [rsp + 32], rcx     ; len
    lea     r9, [_pyfasm_mpl_wbuf]
    mov     rcx, rbx
    mov     edx, esi
    mov     r8d, edi
    call    [TextOutW]
    jmp     .mdtu_done
.mdtu_zero:
    xor     eax, eax
.mdtu_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_map_x:
    ; XMM0 = data_x, RAX = px0, RDX = pw, [R8] = xmin, [R8+8] = xmax -> EAX = pixel_x
    movsd   xmm1, qword [r8]
    movsd   xmm2, qword [r8 + 8]
    subsd   xmm2, xmm1
    ucomisd xmm2, qword [_pyfasm_mpl_f_tiny]
    ja      .mmx_ok
    movsd   xmm2, qword [_pyfasm_mpl_f_one]
.mmx_ok:
    subsd   xmm0, xmm1
    divsd   xmm0, xmm2
    cvtsi2sd xmm3, rdx
    mulsd   xmm0, xmm3
    cvttsd2si ecx, xmm0
    add     eax, ecx
    ret

_pyfasm_mpl_map_y:
    ; XMM0 = data_y, RAX = py1(bottom), RDX = ph, [R8] = ymin, [R8+8] = ymax -> EAX = pixel_y
    movsd   xmm1, qword [r8]
    movsd   xmm2, qword [r8 + 8]
    subsd   xmm2, xmm1
    ucomisd xmm2, qword [_pyfasm_mpl_f_tiny]
    ja      .mmy_ok
    movsd   xmm2, qword [_pyfasm_mpl_f_one]
.mmy_ok:
    subsd   xmm0, xmm1
    divsd   xmm0, xmm2
    cvtsi2sd xmm3, rdx
    mulsd   xmm0, xmm3
    cvttsd2si ecx, xmm0
    sub     eax, ecx
    ret

_pyfasm_mpl_render_axes:
    ; RCX = ax_ptr, RDX = hdc, R8 = fig_w, R9 = fig_h, [rbp+48] = top_offset
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 288
    and     rsp, -16
    movdqu  [rsp + 256], xmm6
    movdqu  [rsp + 272], xmm7

    ; Stack locals (RSP stays constant throughout!):
    ; [rsp+64]  .. [rsp+79]  = RECT (px0, py0, px1, py1)
    ; [rsp+80]  = sub_x0, [rsp+88] = sub_y0, [rsp+96] = sub_w, [rsp+104] = sub_h
    ; [rsp+112] = xmin(f64), [rsp+120] = xmax(f64), [rsp+128] = ymin(f64), [rsp+136] = ymax(f64)
    ; [rsp+144] = pw, [rsp+152] = ph
    ; [rsp+160..191] = Polygon points (4 x 8B) / scratch POINTs
    ; [rsp+192..279] = fixed GDI & loop scratch slots (no push/pop inside body!)

    mov     r12, rcx            ; ax_ptr
    mov     r13, rdx            ; hdc
    mov     r14, r8             ; fig_w
    mov     r15, r9             ; fig_h

    mov     rcx, [rbp + 48]     ; top_offset
    sub     r15, rcx            ; avail_h
    cmp     r15, 60
    jge     .mra_h_ok
    mov     r15d, 60
.mra_h_ok:
    mov     rax, [r12 + 32]     ; 1-based index
    dec     rax
    cqo
    mov     r8, [r12 + 24]      ; ncols
    cmp     r8, 1
    jge     .mra_nc_ok
    mov     r8d, 1
.mra_nc_ok:
    idiv    r8                  ; rax = row, rdx = col
    mov     rbx, rax            ; row
    mov     rsi, rdx            ; col

    mov     rax, r14
    cqo
    idiv    r8
    mov     [rsp + 96], rax     ; cell_w
    imul    rsi, rax
    mov     [rsp + 80], rsi     ; sub_x0

    mov     rax, r15
    cqo
    mov     r9, [r12 + 16]      ; nrows
    cmp     r9, 1
    jge     .mra_nr_ok
    mov     r9d, 1
.mra_nr_ok:
    idiv    r9
    mov     [rsp + 104], rax    ; cell_h
    imul    rbx, rax
    add     rbx, [rbp + 48]
    mov     [rsp + 88], rbx     ; sub_y0

    ; Plot rect: px0=sub_x0+62, py0=sub_y0+28, px1=sub_x0+cell_w-18, py1=sub_y0+cell_h-38
    mov     eax, dword [rsp + 80]
    add     eax, 62
    mov     dword [rsp + 64], eax
    mov     eax, dword [rsp + 88]
    add     eax, 28
    mov     dword [rsp + 68], eax
    mov     eax, dword [rsp + 80]
    add     eax, dword [rsp + 96]
    sub     eax, 18
    mov     ecx, dword [rsp + 64]
    add     ecx, 20
    cmp     eax, ecx
    jge     .mra_px1_ok
    mov     eax, ecx
.mra_px1_ok:
    mov     dword [rsp + 72], eax
    sub     eax, dword [rsp + 64]
    mov     [rsp + 144], rax    ; pw

    mov     eax, dword [rsp + 88]
    add     eax, dword [rsp + 104]
    sub     eax, 38
    mov     ecx, dword [rsp + 68]
    add     ecx, 20
    cmp     eax, ecx
    jge     .mra_py1_ok
    mov     eax, ecx
.mra_py1_ok:
    mov     dword [rsp + 76], eax
    sub     eax, dword [rsp + 68]
    mov     [rsp + 152], rax    ; ph

    ; Fill axes background
    mov     ecx, dword [r12 + 40]
    call    [CreateSolidBrush]
    mov     rbx, rax
    mov     rcx, r13
    lea     rdx, [rsp + 64]
    mov     r8, rbx
    call    [FillRect]
    mov     rcx, rbx
    call    [DeleteObject]

    ; Compute data range (dminx..dmaxx, dminy..dmaxy)
    movsd   xmm4, qword [_pyfasm_mpl_f_big]
    movsd   xmm5, qword [_pyfasm_mpl_f_nbig]
    movsd   xmm6, xmm4
    movsd   xmm7, xmm5

    mov     r14, [r12 + 152]    ; art_count
    xor     r15d, r15d
.mra_scale_art:
    cmp     r15, r14
    jge     .mra_scale_fin
    mov     rax, [r12 + 144]
    mov     rbx, [rax + r15 * 8]
    mov     rcx, [rbx + 8]      ; kind
    cmp     rcx, 4
    je      .mra_sc_hline
    cmp     rcx, 5
    je      .mra_sc_vline
    cmp     rcx, 7
    je      .mra_sc_text

    ; Array artists (1,2,3,6,8)
    mov     rsi, [rbx + 16]     ; x_arr
    mov     rdi, [rbx + 24]     ; y_arr
    test    rsi, rsi
    jz      .mra_sc_next
    test    rdi, rdi
    jz      .mra_sc_next
    mov     r8, [rsi]
    mov     r9, [rdi]
    cmp     r8, r9
    jle     .mra_sc_len
    mov     r8, r9
.mra_sc_len:
    ; Bar / Hist baseline y = 0
    cmp     rcx, 3
    je      .mra_sc_zero
    cmp     rcx, 8
    jne     .mra_sc_pts
.mra_sc_zero:
    pxor    xmm0, xmm0
    minsd   xmm6, xmm0
    maxsd   xmm7, xmm0
.mra_sc_pts:
    xor     r9d, r9d
.mra_sc_pt_lp:
    cmp     r9, r8
    jge     .mra_sc_chk_y2
    mov     rax, [rsi + 8 + r9 * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mra_sc_pt_nx
    movsd   xmm1, xmm0
    mov     rax, [rdi + 8 + r9 * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mra_sc_pt_nx
    minsd   xmm4, xmm1
    maxsd   xmm5, xmm1
    minsd   xmm6, xmm0
    maxsd   xmm7, xmm0
.mra_sc_pt_nx:
    inc     r9
    jmp     .mra_sc_pt_lp

.mra_sc_chk_y2:
    cmp     qword [rbx + 8], 6
    jne     .mra_sc_next
    mov     rdi, [rbx + 32]
    test    rdi, rdi
    jz      .mra_sc_next
    mov     r8, [rdi]
    xor     r9d, r9d
.mra_sc_y2_lp:
    cmp     r9, r8
    jge     .mra_sc_next
    mov     rax, [rdi + 8 + r9 * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mra_sc_y2_nx
    minsd   xmm6, xmm0
    maxsd   xmm7, xmm0
.mra_sc_y2_nx:
    inc     r9
    jmp     .mra_sc_y2_lp

.mra_sc_hline:
    movq    xmm0, qword [rbx + 24]
    minsd   xmm6, xmm0
    maxsd   xmm7, xmm0
    jmp     .mra_sc_next
.mra_sc_vline:
    movq    xmm0, qword [rbx + 16]
    minsd   xmm4, xmm0
    maxsd   xmm5, xmm0
    jmp     .mra_sc_next
.mra_sc_text:
    movq    xmm0, qword [rbx + 16]
    minsd   xmm4, xmm0
    maxsd   xmm5, xmm0
    movq    xmm0, qword [rbx + 24]
    minsd   xmm6, xmm0
    maxsd   xmm7, xmm0
.mra_sc_next:
    inc     r15
    jmp     .mra_scale_art

.mra_scale_fin:
    ucomisd xmm5, xmm4
    jae     .mra_x_have
    pxor    xmm4, xmm4
    movsd   xmm5, qword [_pyfasm_mpl_f_one]
.mra_x_have:
    ucomisd xmm7, xmm6
    jae     .mra_y_have
    pxor    xmm6, xmm6
    movsd   xmm7, qword [_pyfasm_mpl_f_one]
.mra_y_have:
    movsd   xmm0, xmm5
    subsd   xmm0, xmm4
    ucomisd xmm0, qword [_pyfasm_mpl_f_tiny]
    ja      .mra_x_pad
    subsd   xmm4, qword [_pyfasm_mpl_f_half]
    addsd   xmm5, qword [_pyfasm_mpl_f_half]
    jmp     .mra_x_chk_over
.mra_x_pad:
    mulsd   xmm0, qword [_pyfasm_mpl_f_pad]
    subsd   xmm4, xmm0
    addsd   xmm5, xmm0
.mra_x_chk_over:
    cmp     dword [r12 + 104], 0
    je      .mra_store_x
    movsd   xmm4, qword [r12 + 112]
    movsd   xmm5, qword [r12 + 120]
.mra_store_x:
    movsd   qword [rsp + 112], xmm4
    movsd   qword [rsp + 120], xmm5

    movsd   xmm0, xmm7
    subsd   xmm0, xmm6
    ucomisd xmm0, qword [_pyfasm_mpl_f_tiny]
    ja      .mra_y_pad
    subsd   xmm6, qword [_pyfasm_mpl_f_half]
    addsd   xmm7, qword [_pyfasm_mpl_f_half]
    jmp     .mra_y_chk_over
.mra_y_pad:
    mulsd   xmm0, qword [_pyfasm_mpl_f_pad]
    subsd   xmm6, xmm0
    addsd   xmm7, xmm0
.mra_y_chk_over:
    cmp     dword [r12 + 108], 0
    je      .mra_store_y
    movsd   xmm6, qword [r12 + 128]
    movsd   xmm7, qword [r12 + 136]
.mra_store_y:
    movsd   qword [rsp + 128], xmm6
    movsd   qword [rsp + 136], xmm7

    ; Configure text rendering
    mov     rcx, r13
    mov     edx, 1
    call    [SetBkMode]
    mov     rcx, r13
    mov     edx, dword [r12 + 48]
    call    [SetTextColor]
    mov     ecx, 17             ; DEFAULT_GUI_FONT
    call    [GetStockObject]
    mov     rcx, r13
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 192], rax    ; save old font

    ; Draw 5x5 gridlines if grid_on
    cmp     dword [r12 + 64], 0
    je      .mra_draw_artists
    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, dword [r12 + 68]
    call    [CreatePen]
    mov     rbx, rax
    mov     rcx, r13
    mov     rdx, rbx
    call    [SelectObject]
    mov     rsi, rax
    xor     r14d, r14d
.mra_grid_lp:
    cmp     r14d, 5
    jge     .mra_grid_end
    ; Vertical grid line
    mov     eax, [rsp + 144]
    imul    eax, r14d
    cdq
    mov     ecx, 4
    idiv    ecx
    add     eax, dword [rsp + 64]
    mov     edi, eax
    mov     rcx, r13
    mov     edx, edi
    mov     r8d, dword [rsp + 68]
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r13
    mov     edx, edi
    mov     r8d, dword [rsp + 76]
    call    [LineTo]
    ; Horizontal grid line
    mov     eax, [rsp + 152]
    imul    eax, r14d
    cdq
    mov     ecx, 4
    idiv    ecx
    mov     edi, dword [rsp + 76]
    sub     edi, eax
    mov     rcx, r13
    mov     edx, dword [rsp + 64]
    mov     r8d, edi
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r13
    mov     edx, dword [rsp + 72]
    mov     r8d, edi
    call    [LineTo]
    inc     r14d
    jmp     .mra_grid_lp
.mra_grid_end:
    mov     rcx, r13
    mov     rdx, rsi
    call    [SelectObject]
    mov     rcx, rbx
    call    [DeleteObject]

.mra_draw_artists:
    ; Clip region inside plot rect using SaveDC / IntersectClipRect would be nice; clamp pixels instead cleanly
    mov     r14, [r12 + 152]
    xor     r15d, r15d
.mra_art_lp:
    cmp     r15, r14
    jge     .mra_draw_spines
    mov     rax, [r12 + 144]
    mov     rbx, [rax + r15 * 8]
    mov     rax, [rbx + 8]      ; kind
    cmp     rax, 1
    je      .mra_art_line
    cmp     rax, 2
    je      .mra_art_scatter
    cmp     rax, 3
    je      .mra_art_bar
    cmp     rax, 8
    je      .mra_art_bar
    cmp     rax, 4
    je      .mra_art_hline
    cmp     rax, 5
    je      .mra_art_vline
    cmp     rax, 6
    je      .mra_art_fill
    cmp     rax, 7
    je      .mra_art_text
    jmp     .mra_art_nx

.mra_art_line:
    mov     rsi, [rbx + 16]
    mov     rdi, [rbx + 24]
    mov     rcx, [rsi]
    mov     rdx, [rdi]
    cmp     rcx, rdx
    jle     .mral_cnt
    mov     rcx, rdx
.mral_cnt:
    cmp     rcx, 1
    jl      .mra_art_nx
    mov     [rsp + 200], rcx    ; n
    mov     ecx, dword [rbx + 48]
    and     ecx, 3              ; PS_SOLID=0, PS_DASH=1, PS_DOT=2
    mov     edx, dword [rbx + 44]
    test    ecx, ecx
    jz      .mral_pen
    mov     edx, 1              ; GDI dashed pens require width 1
.mral_pen:
    mov     r8d, dword [rbx + 40]
    call    [CreatePen]
    mov     [rsp + 208], rax    ; hpen
    mov     rcx, r13
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 216], rax    ; old_pen

    mov     dword [rsp + 224], 0 ; have_prev = 0
    xor     ecx, ecx
    mov     [rsp + 232], rcx    ; i = 0
.mral_lp:
    mov     rcx, [rsp + 232]
    cmp     rcx, [rsp + 200]
    jge     .mral_markers
    mov     rax, [rsi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mral_break
    movsd   qword [rsp + 160], xmm0
    mov     rcx, [rsp + 232]
    mov     rax, [rdi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mral_break
    movsd   qword [rsp + 168], xmm0

    movsd   xmm0, qword [rsp + 160]
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     dword [rsp + 176], eax
    movsd   xmm0, qword [rsp + 168]
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 180], eax

    cmp     dword [rsp + 224], 0
    jne     .mral_lineto
    mov     rcx, r13
    mov     edx, dword [rsp + 176]
    mov     r8d, dword [rsp + 180]
    xor     r9d, r9d
    call    [MoveToEx]
    mov     dword [rsp + 224], 1
    jmp     .mral_next
.mral_lineto:
    mov     rcx, r13
    mov     edx, dword [rsp + 176]
    mov     r8d, dword [rsp + 180]
    call    [LineTo]
    jmp     .mral_next
.mral_break:
    mov     dword [rsp + 224], 0
.mral_next:
    inc     qword [rsp + 232]
    jmp     .mral_lp

.mral_markers:
    mov     rcx, r13
    mov     rdx, [rsp + 216]
    call    [SelectObject]
    mov     rcx, [rsp + 208]
    call    [DeleteObject]
    test    dword [rbx + 48], 4
    jz      .mra_art_nx
    ; Fall through to also draw point markers if style_flags & 4
.mra_art_scatter:
    mov     rsi, [rbx + 16]
    mov     rdi, [rbx + 24]
    mov     rcx, [rsi]
    mov     rdx, [rdi]
    cmp     rcx, rdx
    jle     .mas_cnt
    mov     rcx, rdx
.mas_cnt:
    mov     [rsp + 200], rcx
    mov     ecx, dword [rbx + 40]
    call    [CreateSolidBrush]
    mov     [rsp + 208], rax
    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, dword [rbx + 40]
    call    [CreatePen]
    mov     [rsp + 216], rax
    mov     rcx, r13
    mov     rdx, [rsp + 208]
    call    [SelectObject]
    mov     [rsp + 224], rax
    mov     rcx, r13
    mov     rdx, [rsp + 216]
    call    [SelectObject]
    mov     [rsp + 232], rax
    xor     ecx, ecx
    mov     [rsp + 184], rcx
.mas_lp:
    mov     rcx, [rsp + 184]
    cmp     rcx, [rsp + 200]
    jge     .mas_end
    mov     rax, [rsi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mas_nx
    movsd   qword [rsp + 160], xmm0
    mov     rcx, [rsp + 184]
    mov     rax, [rdi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mas_nx
    movsd   qword [rsp + 168], xmm0
    movsd   xmm0, qword [rsp + 160]
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     dword [rsp + 176], eax
    movsd   xmm0, qword [rsp + 168]
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 180], eax
    mov     eax, dword [rsp + 176]
    mov     ecx, dword [rbx + 44]
    shr     ecx, 1
    cmp     ecx, 3
    jge     .mas_rad
    mov     ecx, 3
.mas_rad:
    mov     edx, eax
    sub     edx, ecx            ; left
    mov     r8d, dword [rsp + 180]
    sub     r8d, ecx            ; top
    mov     r9d, eax
    add     r9d, ecx            ; right
    mov     eax, dword [rsp + 180]
    add     eax, ecx            ; bottom
    mov     [rsp + 32], eax
    mov     rcx, r13
    call    [Ellipse]
.mas_nx:
    inc     qword [rsp + 184]
    jmp     .mas_lp
.mas_end:
    mov     rcx, r13
    mov     rdx, [rsp + 224]
    call    [SelectObject]
    mov     rcx, r13
    mov     rdx, [rsp + 232]
    call    [SelectObject]
    mov     rcx, [rsp + 208]
    call    [DeleteObject]
    mov     rcx, [rsp + 216]
    call    [DeleteObject]
    jmp     .mra_art_nx

.mra_art_bar:
    mov     rsi, [rbx + 16]
    mov     rdi, [rbx + 24]
    mov     rcx, [rsi]
    mov     rdx, [rdi]
    cmp     rcx, rdx
    jle     .mab_cnt
    mov     rcx, rdx
.mab_cnt:
    cmp     rcx, 1
    jl      .mra_art_nx
    mov     [rsp + 200], rcx
    ; Half bar width = max(2, pw / (2 * n + 2))
    mov     rax, [rsp + 144]
    lea     r8, [rcx * 2 + 2]
    cqo
    idiv    r8
    cmp     eax, 2
    jge     .mab_bw
    mov     eax, 2
.mab_bw:
    mov     [rsp + 208], rax    ; half_w
    ; Baseline py_zero clamped to [py0, py1]
    pxor    xmm0, xmm0
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    cmp     eax, dword [rsp + 68]
    jge     .mab_z1
    mov     eax, dword [rsp + 68]
.mab_z1:
    cmp     eax, dword [rsp + 76]
    jle     .mab_z2
    mov     eax, dword [rsp + 76]
.mab_z2:
    mov     [rsp + 216], rax    ; py_zero

    mov     ecx, dword [rbx + 40]
    call    [CreateSolidBrush]
    mov     [rsp + 224], rax
    xor     ecx, ecx
    mov     edx, 1
    xor     r8d, r8d
    call    [CreatePen]
    mov     [rsp + 232], rax
    mov     rcx, r13
    mov     rdx, [rsp + 224]
    call    [SelectObject]
    mov     [rsp + 240], rax    ; old_brush
    mov     rcx, r13
    mov     rdx, [rsp + 232]
    call    [SelectObject]
    mov     [rsp + 248], rax    ; old_pen
    xor     ecx, ecx
    mov     [rsp + 184], rcx
.mab_lp:
    mov     rcx, [rsp + 184]
    cmp     rcx, [rsp + 200]
    jge     .mab_end
    mov     rax, [rsi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mab_nx
    movsd   qword [rsp + 160], xmm0
    mov     rcx, [rsp + 184]
    mov     rax, [rdi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    test    eax, eax
    jz      .mab_nx
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 176], eax ; py_top
    movsd   xmm0, qword [rsp + 160]
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     edx, eax
    sub     edx, dword [rsp + 208] ; left
    mov     r9d, eax
    add     r9d, dword [rsp + 208] ; right
    mov     r8d, dword [rsp + 176]
    mov     eax, dword [rsp + 216]
    cmp     r8d, eax
    jle     .mab_ord
    xchg    r8d, eax
.mab_ord:
    mov     [rsp + 32], eax
    mov     rcx, r13
    call    [Rectangle]
.mab_nx:
    inc     qword [rsp + 184]
    jmp     .mab_lp
.mab_end:
    mov     rcx, r13
    mov     rdx, [rsp + 248]
    call    [SelectObject]
    mov     rcx, r13
    mov     rdx, [rsp + 240]
    call    [SelectObject]
    mov     rcx, [rsp + 224]
    call    [DeleteObject]
    mov     rcx, [rsp + 232]
    call    [DeleteObject]
    jmp     .mra_art_nx

.mra_art_hline:
    movq    xmm0, qword [rbx + 24]
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     esi, eax
    mov     ecx, dword [rbx + 48]
    and     ecx, 3
    mov     edx, 1
    mov     r8d, dword [rbx + 40]
    call    [CreatePen]
    mov     rdi, rax
    mov     rcx, r13
    mov     rdx, rdi
    call    [SelectObject]
    mov     [rsp + 240], rax
    mov     rcx, r13
    mov     edx, dword [rsp + 64]
    mov     r8d, esi
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r13
    mov     edx, dword [rsp + 72]
    mov     r8d, esi
    call    [LineTo]
    mov     rcx, r13
    mov     rdx, [rsp + 240]
    call    [SelectObject]
    mov     rcx, rdi
    call    [DeleteObject]
    jmp     .mra_art_nx

.mra_art_vline:
    movq    xmm0, qword [rbx + 16]
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     esi, eax
    mov     ecx, dword [rbx + 48]
    and     ecx, 3
    mov     edx, 1
    mov     r8d, dword [rbx + 40]
    call    [CreatePen]
    mov     rdi, rax
    mov     rcx, r13
    mov     rdx, rdi
    call    [SelectObject]
    mov     [rsp + 240], rax
    mov     rcx, r13
    mov     edx, esi
    mov     r8d, dword [rsp + 68]
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r13
    mov     edx, esi
    mov     r8d, dword [rsp + 76]
    call    [LineTo]
    mov     rcx, r13
    mov     rdx, [rsp + 240]
    call    [SelectObject]
    mov     rcx, rdi
    call    [DeleteObject]
    jmp     .mra_art_nx

.mra_art_fill:
    mov     rsi, [rbx + 16]
    mov     rdi, [rbx + 24]
    mov     rcx, [rsi]
    mov     rdx, [rdi]
    cmp     rcx, rdx
    jle     .mafb_c
    mov     rcx, rdx
.mafb_c:
    cmp     rcx, 2
    jl      .mra_art_nx
    mov     [rsp + 200], rcx
    mov     ecx, dword [rbx + 40]
    call    [CreateSolidBrush]
    mov     [rsp + 208], rax
    mov     ecx, 8              ; NULL_PEN
    call    [GetStockObject]
    mov     rcx, r13
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 240], rax
    mov     rcx, r13
    mov     rdx, [rsp + 208]
    call    [SelectObject]
    mov     [rsp + 248], rax
    mov     qword [rsp + 216], 0
.mafb_quad:
    mov     rcx, [rsp + 216]
    lea     rdx, [rcx + 1]
    cmp     rdx, [rsp + 200]
    jge     .mafb_end
    mov     rax, [rsi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     dword [rsp + 160], eax ; p0.x
    mov     dword [rsp + 184], eax ; p3.x
    mov     rcx, [rsp + 216]
    mov     rax, [rsi + 16 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     dword [rsp + 168], eax ; p1.x
    mov     dword [rsp + 176], eax ; p2.x
    ; y1[i], y1[i+1]
    mov     rcx, [rsp + 216]
    mov     rax, [rdi + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 164], eax ; p0.y
    mov     rcx, [rsp + 216]
    mov     rax, [rdi + 16 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 172], eax ; p1.y
    ; y2 or 0.0
    mov     r9, [rbx + 32]
    test    r9, r9
    jz      .mafb_y2_zero
    mov     rcx, [rsp + 216]
    mov     rax, [r9 + 8 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    jmp     .mafb_y2_p3
.mafb_y2_zero:
    pxor    xmm0, xmm0
.mafb_y2_p3:
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 188], eax ; p3.y
    mov     r9, [rbx + 32]
    test    r9, r9
    jz      .mafb_y2_zero2
    mov     rcx, [rsp + 216]
    mov     rax, [r9 + 16 + rcx * 8]
    call    _pyfasm_mpl_val_to_f64
    jmp     .mafb_y2_p2
.mafb_y2_zero2:
    pxor    xmm0, xmm0
.mafb_y2_p2:
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     dword [rsp + 180], eax ; p2.y

    mov     rcx, r13
    lea     rdx, [rsp + 160]
    mov     r8d, 4
    call    [Polygon]
    inc     qword [rsp + 216]
    jmp     .mafb_quad
.mafb_end:
    mov     rcx, r13
    mov     rdx, [rsp + 248]
    call    [SelectObject]
    mov     rcx, r13
    mov     rdx, [rsp + 240]
    call    [SelectObject]
    mov     rcx, [rsp + 208]
    call    [DeleteObject]
    jmp     .mra_art_nx

.mra_art_text:
    movq    xmm0, qword [rbx + 16]
    mov     eax, dword [rsp + 64]
    mov     rdx, [rsp + 144]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     esi, eax
    movq    xmm0, qword [rbx + 24]
    mov     eax, dword [rsp + 76]
    mov     rdx, [rsp + 152]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     edi, eax
    mov     rcx, r13
    mov     edx, dword [rbx + 40]
    call    [SetTextColor]
    mov     rcx, r13
    mov     edx, esi
    mov     r8d, edi
    mov     r9, [rbx + 32]
    call    _pyfasm_mpl_draw_text_utf8
    mov     rcx, r13
    mov     edx, dword [r12 + 48]
    call    [SetTextColor]

.mra_art_nx:
    inc     r15
    jmp     .mra_art_lp

.mra_draw_spines:
    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, dword [r12 + 56]
    call    [CreatePen]
    mov     rbx, rax
    mov     ecx, 5              ; NULL_BRUSH
    call    [GetStockObject]
    mov     rcx, r13
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 240], rax
    mov     rcx, r13
    mov     rdx, rbx
    call    [SelectObject]
    mov     [rsp + 248], rax
    mov     rcx, r13
    mov     edx, dword [rsp + 64]
    mov     r8d, dword [rsp + 68]
    mov     r9d, dword [rsp + 72]
    mov     eax, dword [rsp + 76]
    mov     [rsp + 32], eax
    call    [Rectangle]
    mov     rcx, r13
    mov     rdx, [rsp + 248]
    call    [SelectObject]
    mov     rcx, r13
    mov     rdx, [rsp + 240]
    call    [SelectObject]
    mov     rcx, rbx
    call    [DeleteObject]

    ; Draw X & Y tick labels (5 ticks)
    xor     r14d, r14d
.mra_ticks:
    cmp     r14d, 5
    jge     .mra_labels
    cvtsi2sd xmm0, r14d
    divsd   xmm0, qword [_pyfasm_mpl_f_four]
    ; X tick
    movsd   xmm1, qword [rsp + 120]
    subsd   xmm1, qword [rsp + 112]
    mulsd   xmm1, xmm0
    addsd   xmm1, qword [rsp + 112]
    movq    rcx, xmm1
    call    _pyfasm_float_to_str
    mov     r9, rax
    mov     eax, [rsp + 144]
    imul    eax, r14d
    cdq
    mov     ecx, 4
    idiv    ecx
    add     eax, dword [rsp + 64]
    sub     eax, 10
    mov     edx, eax
    mov     r8d, dword [rsp + 76]
    add     r8d, 4
    mov     rcx, r13
    call    _pyfasm_mpl_draw_text_utf8
    ; Y tick
    cvtsi2sd xmm0, r14d
    divsd   xmm0, qword [_pyfasm_mpl_f_four]
    movsd   xmm1, qword [rsp + 136]
    subsd   xmm1, qword [rsp + 128]
    mulsd   xmm1, xmm0
    addsd   xmm1, qword [rsp + 128]
    movq    rcx, xmm1
    call    _pyfasm_float_to_str
    mov     r9, rax
    mov     eax, [rsp + 152]
    imul    eax, r14d
    cdq
    mov     ecx, 4
    idiv    ecx
    mov     r8d, dword [rsp + 76]
    sub     r8d, eax
    sub     r8d, 7
    mov     edx, dword [rsp + 64]
    sub     edx, 48
    mov     rcx, r13
    call    _pyfasm_mpl_draw_text_utf8
    inc     r14d
    jmp     .mra_ticks

.mra_labels:
    ; Title
    mov     r9, [r12 + 80]
    test    r9, r9
    jz      .mra_xlabel
    mov     edx, dword [rsp + 64]
    mov     eax, dword [rsp + 144]
    shr     eax, 2
    add     edx, eax
    mov     r8d, dword [rsp + 68]
    sub     r8d, 20
    mov     rcx, r13
    call    _pyfasm_mpl_draw_text_utf8
.mra_xlabel:
    mov     r9, [r12 + 88]
    test    r9, r9
    jz      .mra_ylabel
    mov     edx, dword [rsp + 64]
    mov     eax, dword [rsp + 144]
    shr     eax, 1
    add     edx, eax
    sub     edx, 24
    mov     r8d, dword [rsp + 76]
    add     r8d, 20
    mov     rcx, r13
    call    _pyfasm_mpl_draw_text_utf8
.mra_ylabel:
    mov     r9, [r12 + 96]
    test    r9, r9
    jz      .mra_legend
    mov     edx, dword [rsp + 80]
    add     edx, 4
    mov     r8d, dword [rsp + 68]
    sub     r8d, 2
    mov     rcx, r13
    call    _pyfasm_mpl_draw_text_utf8

.mra_legend:
    cmp     dword [r12 + 72], 0
    je      .mra_fin
    mov     esi, dword [rsp + 68]
    add     esi, 10             ; legend y
    mov     r14, [r12 + 152]
    xor     r15d, r15d
.mra_leg_lp:
    cmp     r15, r14
    jge     .mra_fin
    mov     rax, [r12 + 144]
    mov     rbx, [rax + r15 * 8]
    mov     r9, [rbx + 56]
    test    r9, r9
    jz      .mra_leg_nx
    mov     edi, dword [rsp + 72]
    sub     edi, 120
    ; Swatch
    xor     ecx, ecx
    mov     edx, 3
    mov     r8d, dword [rbx + 40]
    call    [CreatePen]
    mov     [rsp + 240], rax
    mov     rcx, r13
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 248], rax
    mov     rcx, r13
    mov     edx, edi
    lea     r8d, [esi + 7]
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r13
    lea     edx, [edi + 18]
    lea     r8d, [esi + 7]
    call    [LineTo]
    mov     rcx, r13
    mov     rdx, [rsp + 248]
    call    [SelectObject]
    mov     rcx, [rsp + 240]
    call    [DeleteObject]
    mov     rcx, r13
    lea     edx, [edi + 24]
    mov     r8d, esi
    mov     r9, [rbx + 56]
    call    _pyfasm_mpl_draw_text_utf8
    add     esi, 18
.mra_leg_nx:
    inc     r15
    jmp     .mra_leg_lp

.mra_fin:
    mov     rcx, r13
    mov     rdx, [rsp + 192]
    call    [SelectObject]
    movdqu  xmm6, [rsp + 256]
    movdqu  xmm7, [rsp + 272]
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

_pyfasm_mpl_render_to_dc:
    ; RCX = fig_ptr, RDX = hdc, R8 = w_px, R9 = h_px
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 64
    and     rsp, -16

    mov     rbx, rcx            ; fig_ptr
    mov     rsi, rdx            ; hdc
    mov     rdi, r8             ; w
    mov     r12, r9             ; h

    mov     dword [rsp + 48], 0
    mov     dword [rsp + 52], 0
    mov     dword [rsp + 56], edi
    mov     dword [rsp + 60], r12d
    mov     ecx, dword [rbx + 32]
    call    [CreateSolidBrush]
    mov     r13, rax
    mov     rcx, rsi
    lea     rdx, [rsp + 48]
    mov     r8, r13
    call    [FillRect]
    mov     rcx, r13
    call    [DeleteObject]

    ; Draw suptitle if present
    xor     r13d, r13d          ; top_offset
    mov     r9, [rbx + 64]
    test    r9, r9
    jz      .mrtd_axes
    mov     rcx, rsi
    mov     edx, 1
    call    [SetBkMode]
    mov     rcx, rsi
    mov     edx, dword [rbx + 80]
    call    [SetTextColor]
    mov     rcx, rsi
    mov     eax, edi
    shr     eax, 2
    mov     edx, eax
    mov     r8d, 6
    mov     r9, [rbx + 64]
    call    _pyfasm_mpl_draw_text_utf8
    mov     r13d, 26

.mrtd_axes:
    mov     r14, [rbx + 48]     ; axes_count
    xor     eax, eax
    mov     [rsp + 40], rax
.mrtd_lp:
    mov     rax, [rsp + 40]
    cmp     rax, r14
    jge     .mrtd_done
    mov     rcx, [rbx + 40]
    mov     rcx, [rcx + rax * 8]
    mov     rdx, rsi
    mov     r8, rdi
    mov     r9, r12
    mov     [rsp + 32], r13
    call    _pyfasm_mpl_render_axes
    inc     qword [rsp + 40]
    jmp     .mrtd_lp

.mrtd_done:
    xor     eax, eax
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

_pyfasm_mpl_paint_hwnd:
    ; RCX = canvas_hwnd, RDX = hdc, R8 = fig_ptr
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

    mov     rbx, rcx            ; hwnd
    mov     rsi, rdx            ; hdc
    mov     rdi, r8             ; fig_ptr
    test    rbx, rbx
    jz      .mpph_done
    test    rsi, rsi
    jz      .mpph_done
    test    rdi, rdi
    jz      .mpph_done

    lea     rdx, [rsp + 32]     ; RECT (16B)
    call    [GetClientRect]
    mov     r12d, dword [rsp + 40] ; w
    mov     r13d, dword [rsp + 44] ; h
    cmp     r12d, 4
    jl      .mpph_done
    cmp     r13d, 4
    jl      .mpph_done

    mov     rcx, rsi
    call    [CreateCompatibleDC]
    mov     r14, rax
    test    r14, r14
    jz      .mpph_direct

    mov     rcx, rsi
    mov     edx, r12d
    mov     r8d, r13d
    call    [CreateCompatibleBitmap]
    push    rax
    mov     rcx, r14
    mov     rdx, rax
    call    [SelectObject]
    push    rax

    mov     rcx, rdi
    mov     rdx, r14
    mov     r8d, r12d
    mov     r9d, r13d
    call    _pyfasm_mpl_render_to_dc

    mov     rcx, rsi
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, r12d
    sub     rsp, 48
    mov     dword [rsp + 32], r13d
    mov     [rsp + 40], r14
    mov     dword [rsp + 48], 0
    mov     dword [rsp + 56], 0
    mov     dword [rsp + 64], 00CC0020h ; SRCCOPY
    call    [BitBlt]
    add     rsp, 48

    pop     rdx
    mov     rcx, r14
    call    [SelectObject]
    pop     rcx
    call    [DeleteObject]
    mov     rcx, r14
    call    [DeleteDC]
    jmp     .mpph_done

.mpph_direct:
    mov     rcx, rdi
    mov     rdx, rsi
    mov     r8d, r12d
    mov     r9d, r13d
    call    _pyfasm_mpl_render_to_dc

.mpph_done:
    xor     eax, eax
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

_pyfasm_mpl_fig_savefig:
    ; RCX = fig_or_0, RDX = utf8_path_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 144
    and     rsp, -16

    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jnz     .mfs_f
    call    _pyfasm_mpl_gcf
    mov     rbx, rax
.mfs_f:
    test    rsi, rsi
    jz      .mfs_done
    mov     rdi, [rbx + 8]      ; W
    mov     r12, [rbx + 16]     ; H
    cmp     rdi, 16
    jge     .mfs_wok
    mov     edi, 640
.mfs_wok:
    cmp     r12, 16
    jge     .mfs_hok
    mov     r12d, 480
.mfs_hok:
    ; row_stride = ((W * 3 + 3) & ~3)
    lea     eax, [edi * 3 + 3]
    and     eax, -4
    imul    r13d, eax, 1
    imul    r13, r12            ; pixel_bytes

    ; Zero 40-byte BITMAPINFOHEADER at [rsp+64..103]
    xor     ecx, ecx
.mfs_zbmi:
    mov     qword [rsp + 64 + rcx], 0
    add     ecx, 8
    cmp     ecx, 48
    jl      .mfs_zbmi
    mov     dword [rsp + 64], 40
    mov     dword [rsp + 68], edi
    mov     dword [rsp + 72], r12d
    mov     word [rsp + 76], 1
    mov     word [rsp + 78], 24
    mov     dword [rsp + 84], r13d

    xor     ecx, ecx
    call    [CreateCompatibleDC]
    mov     r14, rax
    test    r14, r14
    jz      .mfs_done

    mov     rcx, r14
    lea     rdx, [rsp + 64]
    xor     r8d, r8d
    lea     r9, [rsp + 112]     ; ppvBits
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    call    [CreateDIBSection]
    mov     r15, rax
    test    r15, r15
    jz      .mfs_deldc

    mov     rcx, r14
    mov     rdx, r15
    call    [SelectObject]
    mov     [rsp + 120], rax    ; old_bmp

    mov     rcx, rbx
    mov     rdx, r14
    mov     r8, rdi
    mov     r9, r12
    call    _pyfasm_mpl_render_to_dc

    ; Populate 54-byte BMP file+info header
    xor     ecx, ecx
.mfs_zhdr:
    mov     byte [_pyfasm_mpl_bmp_hdr + rcx], 0
    inc     ecx
    cmp     ecx, 54
    jl      .mfs_zhdr
    mov     word [_pyfasm_mpl_bmp_hdr + 0], 4D42h
    lea     eax, [r13d + 54]
    mov     dword [_pyfasm_mpl_bmp_hdr + 2], eax
    mov     dword [_pyfasm_mpl_bmp_hdr + 10], 54
    mov     dword [_pyfasm_mpl_bmp_hdr + 14], 40
    mov     dword [_pyfasm_mpl_bmp_hdr + 18], edi
    mov     dword [_pyfasm_mpl_bmp_hdr + 22], r12d
    mov     word [_pyfasm_mpl_bmp_hdr + 26], 1
    mov     word [_pyfasm_mpl_bmp_hdr + 28], 24
    mov     dword [_pyfasm_mpl_bmp_hdr + 34], r13d

    mov     rcx, rsi
    mov     edx, 40000000h      ; GENERIC_WRITE
    xor     r8d, r8d
    xor     r9d, r9d
    mov     dword [rsp + 32], 2 ; CREATE_ALWAYS
    mov     dword [rsp + 40], 80h
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    cmp     rax, -1
    je      .mfs_cleanup
    mov     rbx, rax

    mov     rcx, rbx
    lea     rdx, [_pyfasm_mpl_bmp_hdr]
    mov     r8d, 54
    lea     r9, [rsp + 128]
    mov     qword [rsp + 32], 0
    call    [WriteFile]

    mov     rcx, rbx
    mov     rdx, [rsp + 112]
    mov     r8d, r13d
    lea     r9, [rsp + 128]
    mov     qword [rsp + 32], 0
    call    [WriteFile]

    mov     rcx, rbx
    call    [CloseHandle]

.mfs_cleanup:
    mov     rcx, r14
    mov     rdx, [rsp + 120]
    call    [SelectObject]
    mov     rcx, r15
    call    [DeleteObject]
.mfs_deldc:
    mov     rcx, r14
    call    [DeleteDC]
.mfs_done:
    xor     eax, eax
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
"""
