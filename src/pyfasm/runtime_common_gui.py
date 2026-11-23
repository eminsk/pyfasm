"""
Portable x86-64 Cross-Platform GUI, Qt, Matplotlib, Pygame & Ecosystem Runtime.
Shared by Linux (ELF64), Apple macOS (Mach-O), and MyOS 10 bare-metal targets.
Uses pure x86-64 instructions + OS-agnostic _pyfasm_print_* and _pyfasm_file_*
primitives with zero OS-specific dynamic library dependencies.
"""

COMMON_GUI_RUNTIME_DATA = r"""
    align 8
    _pyfasm_cmn_empty           db 0
    _pyfasm_cw_count            dq 0
    _pyfasm_cw_kinds            rq 256
    _pyfasm_cw_texts            rq 256
    _pyfasm_cw_hwnds            rq 256
    _pyfasm_cmn_dark            dq 1
    _pyfasm_cmn_theme_ptr       dq 0
    _pyfasm_cmn_http_resp       dq 200, _pyfasm_cmn_empty, 0, _pyfasm_cmn_empty

    _pyfasm_tui_top             db '+====================================================================+', 10, 0
    _pyfasm_tui_sep             db '+--------------------------------------------------------------------+', 10, 0
    _pyfasm_tui_win_pfx         db '| Window: ', 0
    _pyfasm_tui_row_pfx         db '|   ', 0
    _pyfasm_tui_tag_lbl         db '[Label] ', 0
    _pyfasm_tui_tag_edt         db '[Entry] ', 0
    _pyfasm_tui_tag_txt         db '[Textbox] ', 0
    _pyfasm_tui_tag_btn         db '[Button] ', 0
    _pyfasm_tui_tag_chk         db '[CheckBox] ', 0
    _pyfasm_tui_tag_lst         db '[ListBox] ', 0
    _pyfasm_tui_tag_cnv         db '[Canvas] ', 0
    _pyfasm_tui_tag_cmb         db '[ComboBox] ', 0
    _pyfasm_tui_tag_sld         db '[Slider] ', 0
    _pyfasm_tui_tag_prb         db '[Progress] ', 0
    _pyfasm_tui_widget_def      db '(widget)', 0
    _pyfasm_tui_axes_pfx        db '| [Axes] title=', 0
    _pyfasm_tui_artists_pfx     db ' | artists=', 0
    _pyfasm_tui_untitled        db '<untitled>', 0

    ; --- Portable Matplotlib State & Constants ---
    align 8
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
    _pyfasm_mpl_bmp_hdr         rb 54

    ; --- Portable Pygame Software Surface State ---
    align 8
    _pyfasm_pg_width            dq 800
    _pyfasm_pg_height           dq 600
    _pyfasm_pg_screen_surf      dq 0
    _pyfasm_pg_surf_cnt         dq 0
    _pyfasm_pg_surf_tbl         rq 256
    _pyfasm_pg_rc               rd 4
    _pyfasm_pg_ev_list          dq 0
    _pyfasm_pg_keys_arr         rq 260
    _pyfasm_pg_mouse_pos_arr    dq 2, 0, 0
    _pyfasm_pg_mouse_btns       dq 3, 0, 0, 0
    _pyfasm_pg_ticks            dq 0
"""

COMMON_GUI_RUNTIME_CODE = r"""
; ============================================================================
; Portable Widget Recorder, Dynamic TUI Renderer & 24-bit BMP Exporter
; ============================================================================

_pyfasm_common_record_widget:
    ; RCX = kind, RDX = text_ptr_or_0, R8 = hwnd
    mov     rax, [_pyfasm_cw_count]
    cmp     rax, 256
    jge     .crw_done
    mov     [_pyfasm_cw_kinds + rax * 8], rcx
    mov     [_pyfasm_cw_texts + rax * 8], rdx
    mov     [_pyfasm_cw_hwnds + rax * 8], r8
    inc     qword [_pyfasm_cw_count]
.crw_done:
    ret

_pyfasm_render_tui_window:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16

    lea     rcx, [_pyfasm_tui_top]
    call    _pyfasm_print_str
    lea     rcx, [_pyfasm_tui_win_pfx]
    call    _pyfasm_print_str
    lea     rcx, [_pyfasm_win_title]
    call    _pyfasm_print_str
    call    _pyfasm_print_newline
    lea     rcx, [_pyfasm_tui_sep]
    call    _pyfasm_print_str

    mov     rsi, [_pyfasm_cw_count]
    xor     ebx, ebx
.rtw_wloop:
    cmp     rbx, rsi
    jge     .rtw_mpl
    lea     rcx, [_pyfasm_tui_row_pfx]
    call    _pyfasm_print_str
    mov     rax, [_pyfasm_cw_kinds + rbx * 8]
    lea     rcx, [_pyfasm_tui_tag_lbl]
    cmp     rax, 1
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_edt]
    cmp     rax, 2
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_txt]
    cmp     rax, 3
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_btn]
    cmp     rax, 4
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_chk]
    cmp     rax, 5
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_lst]
    cmp     rax, 6
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_cnv]
    cmp     rax, 7
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_cmb]
    cmp     rax, 8
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_sld]
    cmp     rax, 9
    je      .rtw_ptag
    lea     rcx, [_pyfasm_tui_tag_prb]
.rtw_ptag:
    call    _pyfasm_print_str
    mov     rcx, [_pyfasm_cw_texts + rbx * 8]
    cmp     rcx, 4096
    jae     .rtw_ptxt
    lea     rcx, [_pyfasm_tui_widget_def]
.rtw_ptxt:
    call    _pyfasm_print_str
    call    _pyfasm_print_newline
    inc     rbx
    jmp     .rtw_wloop

.rtw_mpl:
    mov     r12, [_pyfasm_mpl_cur_fig]
    test    r12, r12
    jz      .rtw_end
    mov     rsi, [r12 + 48]
    xor     ebx, ebx
.rtw_aloop:
    cmp     rbx, rsi
    jge     .rtw_end
    mov     rax, [r12 + 40]
    mov     rdi, [rax + rbx * 8]
    lea     rcx, [_pyfasm_tui_axes_pfx]
    call    _pyfasm_print_str
    mov     rcx, [rdi + 80]
    cmp     rcx, 4096
    jae     .rtw_atitle
    lea     rcx, [_pyfasm_tui_untitled]
.rtw_atitle:
    call    _pyfasm_print_str
    lea     rcx, [_pyfasm_tui_artists_pfx]
    call    _pyfasm_print_str
    mov     rcx, [rdi + 152]
    call    _pyfasm_int_to_str
    mov     rcx, rax
    call    _pyfasm_print_str
    call    _pyfasm_print_newline
    inc     rbx
    jmp     .rtw_aloop

.rtw_end:
    lea     rcx, [_pyfasm_tui_top]
    call    _pyfasm_print_str
    xor     eax, eax
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_common_write_bmp24:
    ; RCX = path_cstr, RDX = width, R8 = height, R9 = pix_bgr_buf
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx                ; path
    mov     rsi, rdx                ; W
    mov     rdi, r8                 ; H
    mov     r12, r9                 ; pix
    test    rbx, rbx
    jz      .cwb_done
    test    r12, r12
    jz      .cwb_done
    cmp     rsi, 1
    jl      .cwb_done
    cmp     rdi, 1
    jl      .cwb_done

    lea     eax, [esi * 3 + 3]
    and     eax, -4
    imul    r13d, eax, 1
    imul    r13, rdi                ; pixel_bytes

    xor     ecx, ecx
.cwb_zh:
    mov     byte [_pyfasm_mpl_bmp_hdr + rcx], 0
    inc     ecx
    cmp     ecx, 54
    jl      .cwb_zh
    mov     word [_pyfasm_mpl_bmp_hdr + 0], 4D42h
    lea     eax, [r13d + 54]
    mov     dword [_pyfasm_mpl_bmp_hdr + 2], eax
    mov     dword [_pyfasm_mpl_bmp_hdr + 10], 54
    mov     dword [_pyfasm_mpl_bmp_hdr + 14], 40
    mov     dword [_pyfasm_mpl_bmp_hdr + 18], esi
    mov     dword [_pyfasm_mpl_bmp_hdr + 22], edi
    mov     word [_pyfasm_mpl_bmp_hdr + 26], 1
    mov     word [_pyfasm_mpl_bmp_hdr + 28], 24
    mov     dword [_pyfasm_mpl_bmp_hdr + 34], r13d

    mov     rcx, rbx
    lea     rdx, [.cwb_mode]
    call    _pyfasm_file_open
    cmp     rax, 0
    jl      .cwb_done
    mov     rbx, rax                ; fd
    mov     rcx, rbx
    lea     rdx, [_pyfasm_mpl_bmp_hdr]
    mov     r8d, 54
    call    _pyfasm_file_write_bytes
    mov     rcx, rbx
    mov     rdx, r12
    mov     r8, r13
    call    _pyfasm_file_write_bytes
    mov     rcx, rbx
    call    _pyfasm_file_close
.cwb_done:
    xor     eax, eax
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.cwb_mode db 'w', 0

; ============================================================================
; Portable Callback, Tk / CTk, Color, Theme & StringVar Helpers
; ============================================================================

_pyfasm_invoke_cb:
    ; RCX = cb_or_closure, RDX = arg1
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .icb_d
    cmp     rcx, 4096
    jb      .icb_d
    mov     r10, 505946434C4F5355h  ; 'PYFCLOSU'
    cmp     [rcx], r10
    jne     .icb_plain
    mov     rax, [rcx + 8]
    test    rax, rax
    jz      .icb_d
    call    rax
    jmp     .icb_d
.icb_plain:
    mov     rax, rcx
    mov     rcx, rdx
    call    rax
.icb_d:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_is_list:
    xor     eax, eax
    cmp     rcx, 65536
    jb      .isl_done
    mov     r10, [rcx]
    cmp     r10, 0
    jl      .isl_done
    cmp     r10, 10000000
    jg      .isl_done
    mov     eax, 1
.isl_done:
    ret

_pyfasm_combobox_add:
    xor     eax, eax
    ret

_pyfasm_create_combobox:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 900
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 8
    mov     rdx, 0
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_slider:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 1000
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 9
    xor     edx, edx
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_progressbar:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 1100
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 10
    xor     edx, edx
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_segmented:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 1200
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 4
    xor     edx, edx
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_font:
    mov     rax, 1
    ret

_pyfasm_widget_set_font:
_pyfasm_widget_configure:
_pyfasm_widget_set_colors:
_pyfasm_widget_bind:
_pyfasm_textbox_append:
_pyfasm_progressbar_set:
_pyfasm_grid_propagate:
_pyfasm_after:
_pyfasm_window_close_cb:
_pyfasm_stringvar_bind:
_pyfasm_stringvar_trace:
_pyfasm_fire_sv_traces:
_pyfasm_update_window:
_pyfasm_init_tray:
_pyfasm_run_tray_loop:
    xor     eax, eax
    ret

_pyfasm_tabview_add:
    jmp     _pyfasm_create_frame

_pyfasm_is_stringvar:
    xor     eax, eax
    cmp     rcx, 65536
    jb      .isv_d
    mov     r10, 5059465356415221h  ; 'PYFSVAR!'
    cmp     [rcx], r10
    jne     .isv_d
    mov     eax, 1
.isv_d:
    ret

_pyfasm_winfo_width:
    mov     rax, 800
    ret

_pyfasm_winfo_height:
    mov     rax, 600
    ret

_pyfasm_set_appearance_mode:
    test    rcx, rcx
    jz      .sam_d
    movzx   eax, byte [rcx]
    cmp     al, 'l'
    je      .sam_light
    cmp     al, 'L'
    je      .sam_light
    mov     qword [_pyfasm_cmn_dark], 1
    xor     eax, eax
    ret
.sam_light:
    mov     qword [_pyfasm_cmn_dark], 0
.sam_d:
    xor     eax, eax
    ret

_pyfasm_set_default_color_theme:
    mov     [_pyfasm_cmn_theme_ptr], rcx
    xor     eax, eax
    ret

_pyfasm_parse_hex_nibble:
    movzx   eax, cl
    cmp     al, '0'
    jb      .phn_b
    cmp     al, '9'
    ja      .phn_u
    sub     al, '0'
    ret
.phn_u:
    cmp     al, 'A'
    jb      .phn_l
    cmp     al, 'F'
    ja      .phn_l
    sub     al, 'A' - 10
    ret
.phn_l:
    cmp     al, 'a'
    jb      .phn_b
    cmp     al, 'f'
    ja      .phn_b
    sub     al, 'a' - 10
    ret
.phn_b:
    mov     eax, -1
    ret

_pyfasm_parse_color_one32:
_pyfasm_parse_color:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    or      eax, 01000000h
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_resolve_packed_color:
    mov     rax, rcx
    cmp     rax, 0
    je      .rpc_zero
    and     eax, 00FFFFFFh
    ret
.rpc_zero:
    xor     eax, eax
    ret

_pyfasm_filedialog_open:
_pyfasm_filedialog_save:
    lea     rax, [_pyfasm_cmn_empty]
    ret

_pyfasm_msgbox_info:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rdx, rdx
    jz      .mbi_c
    mov     rcx, rdx
.mbi_c:
    call    _pyfasm_print_str
    call    _pyfasm_print_newline
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================================
; Portable Qt Layouts & Timer Engine
; ============================================================================

_pyfasm_qt_create_widget:
    jmp     _pyfasm_create_frame

_pyfasm_qt_layout_new:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     ecx, 64
    call    _pyfasm_alloc
    mov     r8, 505946514C415921h   ; 'PYFQLAY!'
    mov     [rax + 0], r8
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     qword [rax + 24], 0
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_layout_add_widget:
_pyfasm_qt_layout_add_layout:
_pyfasm_qt_layout_set_margins:
_pyfasm_qt_layout_add_stretch:
_pyfasm_qt_widget_set_layout:
_pyfasm_qt_set_central_widget:
_pyfasm_qt_combobox_index:
_pyfasm_qt_combobox_set_index:
_pyfasm_qt_set_value:
_pyfasm_qt_get_value:
_pyfasm_qt_set_range:
    xor     eax, eax
    ret

_pyfasm_qt_tab_add:
    mov     rax, rdx
    ret

_pyfasm_qtimer_new:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     rdx, 5059465154494D52h  ; 'PYFQTIMR'
    mov     [rax + 0], rdx
    mov     qword [rax + 8], 0
    mov     qword [rax + 16], 100
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qtimer_connect:
    test    rcx, rcx
    jz      .pqtc_d
    mov     [rcx + 8], rdx
.pqtc_d:
    xor     eax, eax
    ret

_pyfasm_qtimer_start:
    test    rcx, rcx
    jz      .pqts_d
    test    rdx, rdx
    jle     .pqts_d
    mov     [rcx + 16], rdx
.pqts_d:
    xor     eax, eax
    ret

; ============================================================================
; Portable Matplotlib Data Model + Pure-x64 Software 24-bit BMP Rasterizer
; ============================================================================

_pyfasm_mpl_val_to_f64:
    mov     rcx, rax
    sar     rcx, 48
    test    rcx, rcx
    jz      .cmvf_int
    cmp     rcx, -1
    je      .cmvf_int
    mov     rdx, 7FF0000000000000h
    mov     rcx, rax
    and     rcx, rdx
    cmp     rcx, rdx
    je      .cmvf_nan
    movq    xmm0, rax
    mov     eax, 1
    ret
.cmvf_int:
    cvtsi2sd xmm0, rax
    mov     eax, 1
    ret
.cmvf_nan:
    pxor    xmm0, xmm0
    xor     eax, eax
    ret

_pyfasm_mpl_str_eq_ci:
    test    rcx, rcx
    jz      .cmseq_no
    test    rdx, rdx
    jz      .cmseq_no
.cmseq_loop:
    movzx   eax, byte [rcx]
    cmp     al, 'A'
    jb      .cmseq_lo
    cmp     al, 'Z'
    ja      .cmseq_lo
    add     al, 32
.cmseq_lo:
    movzx   r8d, byte [rdx]
    cmp     al, r8b
    jne     .cmseq_no
    test    al, al
    jz      .cmseq_yes
    inc     rcx
    inc     rdx
    jmp     .cmseq_loop
.cmseq_yes:
    mov     eax, 1
    ret
.cmseq_no:
    xor     eax, eax
    ret

_pyfasm_mpl_hex_nibble:
    cmp     al, '0'
    jb      .cmhn_bad
    cmp     al, '9'
    ja      .cmhn_af
    sub     al, '0'
    movzx   eax, al
    ret
.cmhn_af:
    cmp     al, 'A'
    jb      .cmhn_lo
    cmp     al, 'F'
    ja      .cmhn_lo
    sub     al, 'A' - 10
    movzx   eax, al
    ret
.cmhn_lo:
    cmp     al, 'a'
    jb      .cmhn_bad
    cmp     al, 'f'
    ja      .cmhn_bad
    sub     al, 'a' - 10
    movzx   eax, al
    ret
.cmhn_bad:
    mov     eax, -1
    ret

_pyfasm_mpl_parse_color:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    cmp     rbx, 10000h
    jb      .cmpc_cycle
    movzx   eax, byte [rbx]
    cmp     al, '#'
    jne     .cmpc_named
    xor     ecx, ecx
.cmpc_len:
    cmp     byte [rbx + 1 + rcx], 0
    je      .cmpc_glen
    inc     ecx
    cmp     ecx, 8
    jb      .cmpc_len
.cmpc_glen:
    cmp     ecx, 6
    jb      .cmpc_cycle
    mov     al, byte [rbx + 1]
    call    _pyfasm_mpl_hex_nibble
    shl     eax, 4
    mov     r8d, eax
    mov     al, byte [rbx + 2]
    call    _pyfasm_mpl_hex_nibble
    or      r8d, eax
    mov     al, byte [rbx + 3]
    call    _pyfasm_mpl_hex_nibble
    shl     eax, 4
    mov     r9d, eax
    mov     al, byte [rbx + 4]
    call    _pyfasm_mpl_hex_nibble
    or      r9d, eax
    mov     al, byte [rbx + 5]
    call    _pyfasm_mpl_hex_nibble
    shl     eax, 4
    mov     r10d, eax
    mov     al, byte [rbx + 6]
    call    _pyfasm_mpl_hex_nibble
    or      r10d, eax
    shl     r10d, 16
    shl     r9d, 8
    mov     eax, r10d
    or      eax, r9d
    or      eax, r8d
    jmp     .cmpc_done
.cmpc_named:
    cmp     byte [rbx + 1], 0
    jne     .cmpc_words
    movzx   eax, byte [rbx]
    cmp     al, 'r'
    je      .cc_r
    cmp     al, 'g'
    je      .cc_g
    cmp     al, 'b'
    je      .cc_b
    cmp     al, 'c'
    je      .cc_c
    cmp     al, 'm'
    je      .cc_m
    cmp     al, 'y'
    je      .cc_y
    cmp     al, 'k'
    je      .cc_k
    cmp     al, 'w'
    je      .cc_w
    jmp     .cmpc_cycle
.cmpc_words:
    mov     rcx, rbx
    lea     rdx, [.cs_red]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .cc_r
    mov     rcx, rbx
    lea     rdx, [.cs_blue]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .cc_b
    mov     rcx, rbx
    lea     rdx, [.cs_green]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .cc_g
    mov     rcx, rbx
    lea     rdx, [.cs_black]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .cc_k
    mov     rcx, rbx
    lea     rdx, [.cs_white]
    call    _pyfasm_mpl_str_eq_ci
    test    eax, eax
    jnz     .cc_w
    jmp     .cmpc_cycle
.cc_r: mov eax, 00241CD6h
       jmp .cmpc_done
.cc_g: mov eax, 002CA02Ch
       jmp .cmpc_done
.cc_b: mov eax, 00B4771Fh
       jmp .cmpc_done
.cc_c: mov eax, 00CFBE17h
       jmp .cmpc_done
.cc_m: mov eax, 00BF00BFh
       jmp .cmpc_done
.cc_y: mov eax, 0000D7FFh
       jmp .cmpc_done
.cc_k: mov eax, 00111111h
       jmp .cmpc_done
.cc_w: mov eax, 00FFFFFFh
       jmp .cmpc_done
.cmpc_cycle:
    mov     rax, rsi
    cqo
    mov     ecx, 10
    idiv    rcx
    test    rdx, rdx
    jge     .cmpc_ok
    add     rdx, 10
.cmpc_ok:
    mov     eax, dword [_pyfasm_mpl_tab10 + rdx * 4]
.cmpc_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.cs_red   db 'red', 0
.cs_blue  db 'blue', 0
.cs_green db 'green', 0
.cs_black db 'black', 0
.cs_white db 'white', 0

_pyfasm_mpl_make_range_x:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jg      .cmrx_ok
    mov     ebx, 1
.cmrx_ok:
    lea     rcx, [rbx + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     [rax], rbx
    xor     esi, esi
.cmrx_lp:
    cmp     rsi, rbx
    jge     .cmrx_d
    cvtsi2sd xmm0, rsi
    movq    rdx, xmm0
    mov     [rax + 8 + rsi * 8], rdx
    inc     rsi
    jmp     .cmrx_lp
.cmrx_d:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_figure_new:
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
    jg      .cmfn_w
    mov     ebx, 640
.cmfn_w:
    test    rsi, rsi
    jg      .cmfn_h
    mov     esi, 480
.cmfn_h:
    mov     ecx, 96
    call    _pyfasm_alloc
    mov     r8, 5059464D46494721h
    mov     [rax + 0], r8
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     [rax + 24], rdi
    mov     dword [rax + 32], 00FFFFFFh
    mov     qword [rax + 48], 0
    mov     qword [rax + 56], 16
    mov     qword [rax + 64], 0
    mov     qword [rax + 72], 0
    mov     rbx, rax
    test    r12, r12
    jz      .cmfn_arr
    mov     rcx, r12
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     dword [rbx + 32], eax
.cmfn_arr:
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
    mov     rax, [_pyfasm_mpl_cur_fig]
    test    rax, rax
    jnz     .cmgcf_r
    xor     ecx, ecx
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    jmp     _pyfasm_mpl_figure_new
.cmgcf_r:
    ret

_pyfasm_mpl_fig_add_subplot:
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
    jnz     .cmas_f
    call    _pyfasm_mpl_gcf
    mov     rbx, rax
.cmas_f:
    cmp     rsi, 0
    jg      .cmas_r
    mov     esi, 1
.cmas_r:
    cmp     rdi, 0
    jg      .cmas_c
    mov     edi, 1
.cmas_c:
    cmp     r12, 0
    jg      .cmas_i
    mov     r12d, 1
.cmas_i:
    mov     ecx, 208
    call    _pyfasm_alloc
    mov     r8, 5059464D41585321h
    mov     [rax + 0], r8
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     [rax + 24], rdi
    mov     [rax + 32], r12
    mov     dword [rax + 40], 00FFFFFFh
    mov     dword [rax + 48], 00111111h
    mov     dword [rax + 56], 00333333h
    mov     qword [rax + 104], 0
    mov     qword [rax + 152], 0
    mov     qword [rax + 160], 64
    mov     qword [rax + 168], 0
    mov     rsi, rax
    mov     ecx, 512
    call    _pyfasm_alloc
    mov     [rsi + 144], rax
    mov     rcx, [rbx + 48]
    cmp     rcx, [rbx + 56]
    jge     .cmas_ret
    inc     qword [rbx + 48]
    mov     rdx, [rbx + 40]
    mov     [rdx + rcx * 8], rsi
.cmas_ret:
    mov     [_pyfasm_mpl_cur_fig], rbx
    mov     [_pyfasm_mpl_cur_ax], rsi
    mov     rax, rsi
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_gca:
    mov     rax, [_pyfasm_mpl_cur_ax]
    test    rax, rax
    jnz     .cmgca_r
    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 1
    mov     r9d, 1
    jmp     _pyfasm_mpl_fig_add_subplot
.cmgca_r:
    ret

_pyfasm_mpl_plt_subplots:
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
    jg      .cmps_nr
    mov     ecx, 1
.cmps_nr:
    cmp     rdx, 0
    jg      .cmps_nc
    mov     edx, 1
.cmps_nc:
    mov     r12, rcx
    mov     r13, rdx
    mov     rcx, r8
    mov     rdx, r9
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_mpl_figure_new
    mov     r14, rax
    mov     rax, r12
    imul    rax, r13
    cmp     rax, 1
    jne     .cmps_multi
    mov     rcx, r14
    mov     edx, 1
    mov     r8d, 1
    mov     r9d, 1
    call    _pyfasm_mpl_fig_add_subplot
    mov     r15, rax
    jmp     .cmps_pack
.cmps_multi:
    mov     rdi, r12
    imul    rdi, r13
    lea     rcx, [rdi + 2]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     r15, rax
    mov     [r15], rdi
    xor     ebx, ebx
.cmps_lp:
    cmp     rbx, rdi
    jge     .cmps_pack
    mov     rcx, r14
    mov     rdx, r12
    mov     r8, r13
    lea     r9, [rbx + 1]
    call    _pyfasm_mpl_fig_add_subplot
    mov     [r15 + 8 + rbx * 8], rax
    inc     rbx
    jmp     .cmps_lp
.cmps_pack:
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
    test    rcx, rcx
    jz      _pyfasm_mpl_gca
    mov     r10, 5059464D41585321h
    cmp     [rcx], r10
    jne     _pyfasm_mpl_gca
    mov     rax, rcx
    ret

_pyfasm_mpl_add_artist:
    test    rcx, rcx
    jz      .cmaa_d
    mov     rax, [rcx + 152]
    cmp     rax, [rcx + 160]
    jge     .cmaa_d
    inc     qword [rcx + 152]
    mov     r8, [rcx + 144]
    mov     [r8 + rax * 8], rdx
.cmaa_d:
    ret

_pyfasm_mpl_invalidate_ax:
_pyfasm_mpl_canvas_draw:
_pyfasm_mpl_paint_hwnd:
_pyfasm_mpl_draw_text_utf8:
_pyfasm_mpl_render_axes:
_pyfasm_mpl_render_to_dc:
    xor     eax, eax
    ret

_pyfasm_mpl_fig_clear:
    test    rcx, rcx
    jz      .cmfc_gcf
    mov     qword [rcx + 48], 0
.cmfc_gcf:
    mov     qword [_pyfasm_mpl_cur_ax], 0
    xor     eax, eax
    ret

_pyfasm_mpl_axes_clear:
    test    rcx, rcx
    jz      _pyfasm_mpl_gca
    mov     rax, 5059464D41585321h
    cmp     [rcx], rax
    je      .cmac_ax
    mov     rax, 5059464D46494721h
    cmp     [rcx], rax
    je      _pyfasm_mpl_fig_clear
    jmp     _pyfasm_listbox_clear
.cmac_ax:
    mov     qword [rcx + 152], 0
    mov     qword [rcx + 168], 0
    mov     qword [rcx + 104], 0
    xor     eax, eax
    ret

_pyfasm_mpl_fig_suptitle:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    test    rcx, rcx
    jnz     .cmfst_h
    call    _pyfasm_mpl_gcf
    mov     rcx, rax
.cmfst_h:
    mov     [rcx + 64], rbx
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_mpl_axes_plot:
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
    jz      .cmap_d
    test    rsi, rsi
    jnz     .cmap_x
    mov     rcx, [rdi]
    call    _pyfasm_mpl_make_range_x
    mov     rsi, rax
.cmap_x:
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 1
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [r13 + 40], eax
    mov     dword [r13 + 44], 2
    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
.cmap_d:
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

_pyfasm_mpl_axes_scatter:
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
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 2
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [r13 + 40], eax
    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
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
_pyfasm_mpl_axes_hist:
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
    jnz     .cmab_ok
    mov     rdi, rsi
    mov     rcx, [rdi]
    call    _pyfasm_mpl_make_range_x
    mov     rsi, rax
.cmab_ok:
    mov     ecx, 72
    call    _pyfasm_alloc
    mov     r13, rax
    mov     r8, 5059464D41525421h
    mov     [r13 + 0], r8
    mov     qword [r13 + 8], 3
    mov     [r13 + 16], rsi
    mov     [r13 + 24], rdi
    mov     rax, [rbx + 168]
    inc     qword [rbx + 168]
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_mpl_parse_color
    mov     dword [r13 + 40], eax
    mov     rcx, rbx
    mov     rdx, r13
    call    _pyfasm_mpl_add_artist
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

_pyfasm_mpl_axes_hline:
_pyfasm_mpl_axes_vline:
_pyfasm_mpl_axes_fill_between:
_pyfasm_mpl_axes_text:
    xor     eax, eax
    ret

_pyfasm_mpl_axes_set_title:
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
_pyfasm_mpl_axes_set_ylim:
_pyfasm_mpl_set_facecolor:
_pyfasm_mpl_axes_grid:
_pyfasm_mpl_axes_legend:
_pyfasm_mpl_axes_set_fgcolor:
_pyfasm_mpl_axes_set_spine_color:
    xor     eax, eax
    ret

_pyfasm_mpl_canvas_attach:
    mov     rax, rdx
    ret

_pyfasm_mpl_canvas_widget:
    mov     rax, rcx
    ret

_pyfasm_mpl_plt_show:
    jmp     _pyfasm_run_window_loop

_pyfasm_mpl_map_x:
    movsd   xmm1, qword [r8]
    movsd   xmm2, qword [r8 + 8]
    subsd   xmm2, xmm1
    ucomisd xmm2, qword [_pyfasm_mpl_f_tiny]
    ja      .cmmx_ok
    movsd   xmm2, qword [_pyfasm_mpl_f_one]
.cmmx_ok:
    subsd   xmm0, xmm1
    divsd   xmm0, xmm2
    cvtsi2sd xmm3, rdx
    mulsd   xmm0, xmm3
    cvttsd2si ecx, xmm0
    add     eax, ecx
    ret

_pyfasm_mpl_map_y:
    movsd   xmm1, qword [r8]
    movsd   xmm2, qword [r8 + 8]
    subsd   xmm2, xmm1
    ucomisd xmm2, qword [_pyfasm_mpl_f_tiny]
    ja      .cmmy_ok
    movsd   xmm2, qword [_pyfasm_mpl_f_one]
.cmmy_ok:
    subsd   xmm0, xmm1
    divsd   xmm0, xmm2
    cvtsi2sd xmm3, rdx
    mulsd   xmm0, xmm3
    cvttsd2si ecx, xmm0
    add     eax, ecx
    ret

_pyfasm_mpl_sw_set_pixel:
    ; RAX = pix_buf, ECX = x, EDX = y, R8D = W, R9D = H, R10D = row_stride, R11D = bgr_color
    cmp     ecx, 0
    jl      .msp_d
    cmp     ecx, r8d
    jge     .msp_d
    cmp     edx, 0
    jl      .msp_d
    cmp     edx, r9d
    jge     .msp_d
    imul    edx, r10d
    imul    ecx, ecx, 3
    add     edx, ecx
    movsxd  rdx, edx
    mov     ecx, r11d
    mov     byte [rax + rdx + 2], cl ; R
    shr     ecx, 8
    mov     byte [rax + rdx + 1], cl ; G
    shr     ecx, 8
    mov     byte [rax + rdx + 0], cl ; B
.msp_d:
    ret

_pyfasm_mpl_sw_draw_line:
    ; [rsp args avoid]: RCX=pix, RDX=W, R8=H, R9=row_stride, [rbp+48]=x0, [rbp+56]=y0, [rbp+64]=x1, [rbp+72]=y1, [rbp+80]=bgr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    mov     rax, rcx
    mov     r10d, r9d               ; row_stride
    mov     r11d, dword [rbp + 80]  ; bgr
    mov     r12d, dword [rbp + 48]  ; x0
    mov     r13d, dword [rbp + 56]  ; y0
    mov     r14d, dword [rbp + 64]  ; x1
    mov     r15d, dword [rbp + 72]  ; y1
    ; Sample 256 interpolated steps along segment cleanly in pure x64
    xor     ebx, ebx
.msdl_lp:
    cmp     ebx, 256
    jg      .msdl_done
    mov     esi, r14d
    sub     esi, r12d
    imul    esi, ebx
    sar     esi, 8
    add     esi, r12d
    mov     edi, r15d
    sub     edi, r13d
    imul    edi, ebx
    sar     edi, 8
    add     edi, r13d
    mov     ecx, esi
    push    rdx
    mov     edx, edi
    ; r8d = W? wait RDX held W! Move W to stack/pass via r8=W, r9=H? Reload from regs safely:
    pop     rdx
    push    r8
    push    r9
    mov     r9d, r8d
    mov     r8d, edx
    mov     edx, edi
    call    _pyfasm_mpl_sw_set_pixel
    mov     edx, r8d
    pop     r9
    pop     r8
    inc     ebx
    jmp     .msdl_lp
.msdl_done:
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

_pyfasm_mpl_sw_fill_rect:
    ret

_pyfasm_mpl_fig_savefig:
    ; RCX = fig_or_0, RDX = path_cstr -> pure-x64 24-bit rasterized BMP
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
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jnz     .cmfs_f
    call    _pyfasm_mpl_gcf
    mov     rbx, rax
.cmfs_f:
    test    rsi, rsi
    jz      .cmfs_done
    mov     rdi, [rbx + 8]          ; W
    mov     r12, [rbx + 16]         ; H
    cmp     rdi, 16
    jge     .cmfs_wok
    mov     edi, 640
.cmfs_wok:
    cmp     r12, 16
    jge     .cmfs_hok
    mov     r12d, 480
.cmfs_hok:
    lea     eax, [edi * 3 + 3]
    and     eax, -4
    mov     r13d, eax               ; row_stride
    mov     rcx, r13
    imul    rcx, r12
    call    _pyfasm_alloc
    mov     r14, rax                ; pix_buf
    ; Fill background with 0xFF (white)
    mov     r8, r13
    imul    r8, r12
    xor     rcx, rcx
.cmfs_bg:
    cmp     rcx, r8
    jge     .cmfs_plot
    mov     byte [r14 + rcx], 0FFh
    inc     rcx
    jmp     .cmfs_bg

.cmfs_plot:
    cmp     qword [rbx + 48], 0
    jle     .cmfs_write
    mov     rax, [rbx + 40]
    mov     r15, [rax + 0]          ; first ax
    cmp     qword [r15 + 152], 0
    jle     .cmfs_write
    mov     rax, [r15 + 144]
    mov     rax, [rax + 0]          ; first artist
    mov     [rsp + 80], rax
    mov     r8, [rax + 16]          ; x_arr
    mov     r9, [rax + 24]          ; y_arr
    test    r8, r8
    jz      .cmfs_write
    test    r9, r9
    jz      .cmfs_write
    mov     [rsp + 88], r8
    mov     [rsp + 96], r9
    mov     rcx, [r8]
    cmp     rcx, [r9]
    jle     .cmfs_cnt
    mov     rcx, [r9]
.cmfs_cnt:
    cmp     rcx, 2
    jl      .cmfs_write
    mov     [rsp + 104], rcx

    ; Compute xmin..xmax, ymin..ymax
    movsd   xmm2, qword [_pyfasm_mpl_f_big]
    movsd   xmm3, qword [_pyfasm_mpl_f_nbig]
    movsd   xmm4, xmm2
    movsd   xmm5, xmm3
    xor     ecx, ecx
.cmfs_sc:
    cmp     rcx, [rsp + 104]
    jge     .cmfs_sc_d
    mov     r8, [rsp + 88]
    mov     rax, [r8 + 8 + rcx * 8]
    push    rcx
    call    _pyfasm_mpl_val_to_f64
    pop     rcx
    movsd   xmm1, xmm0
    mov     r9, [rsp + 96]
    mov     rax, [r9 + 8 + rcx * 8]
    push    rcx
    call    _pyfasm_mpl_val_to_f64
    pop     rcx
    minsd   xmm2, xmm1
    maxsd   xmm3, xmm1
    minsd   xmm4, xmm0
    maxsd   xmm5, xmm0
    inc     rcx
    jmp     .cmfs_sc
.cmfs_sc_d:
    movsd   qword [rsp + 112], xmm2
    movsd   qword [rsp + 120], xmm3
    movsd   qword [rsp + 128], xmm4
    movsd   qword [rsp + 136], xmm5

    ; Draw polyline segments across pix_buf
    xor     r15d, r15d
.cmfs_seg:
    lea     rax, [r15 + 1]
    cmp     rax, [rsp + 104]
    jge     .cmfs_write
    mov     r8, [rsp + 88]
    mov     rax, [r8 + 8 + r15 * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, 40
    lea     edx, [edi - 80]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     [rsp + 32], rax         ; arg5: x0
    mov     r9, [rsp + 96]
    mov     rax, [r9 + 8 + r15 * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, 40
    lea     edx, [r12d - 80]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     [rsp + 40], rax         ; arg6: y0
    mov     r8, [rsp + 88]
    mov     rax, [r8 + 16 + r15 * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, 40
    lea     edx, [edi - 80]
    lea     r8, [rsp + 112]
    call    _pyfasm_mpl_map_x
    mov     [rsp + 48], rax         ; arg7: x1
    mov     r9, [rsp + 96]
    mov     rax, [r9 + 16 + r15 * 8]
    call    _pyfasm_mpl_val_to_f64
    mov     eax, 40
    lea     edx, [r12d - 80]
    lea     r8, [rsp + 128]
    call    _pyfasm_mpl_map_y
    mov     [rsp + 56], rax         ; arg8: y1
    mov     rax, [rsp + 80]
    mov     eax, dword [rax + 40]   ; bgr color
    mov     [rsp + 64], rax         ; arg9: bgr
    mov     rcx, r14                ; pix
    mov     rdx, rdi                ; W
    mov     r8, r12                 ; H
    mov     r9, r13                 ; row_stride
    call    _pyfasm_mpl_sw_draw_line
    inc     r15
    jmp     .cmfs_seg

.cmfs_write:
    mov     rcx, rsi
    mov     rdx, rdi
    mov     r8, r12
    mov     r9, r14
    call    _pyfasm_common_write_bmp24
.cmfs_done:
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

; ============================================================================
; Portable Pygame Software Surface & Event Engine
; ============================================================================

_pyfasm_pg_unpack_color:
    cmp     rcx, 65536
    jb      .cpuc_int
    mov     rax, 5059465047434F4Ch
    cmp     [rcx], rax
    jne     .cpuc_seq
    mov     eax, dword [rcx + 8]
    ret
.cpuc_seq:
    mov     rax, [rcx]
    cmp     rax, 3
    jl      .cpuc_str
    cmp     rax, 16
    ja      .cpuc_str
    mov     r8d, dword [rcx + 8]
    mov     r9d, dword [rcx + 16]
    mov     r10d, dword [rcx + 24]
    and     r8d, 0FFh
    and     r9d, 0FFh
    and     r10d, 0FFh
    shl     r10d, 16
    shl     r9d, 8
    mov     eax, r8d
    or      eax, r9d
    or      eax, r10d
    ret
.cpuc_str:
    xor     edx, edx
    jmp     _pyfasm_mpl_parse_color
.cpuc_int:
    mov     eax, ecx
    mov     r8d, eax
    shr     r8d, 16
    and     r8d, 0FFh
    mov     r9d, eax
    and     r9d, 0000FF00h
    mov     r10d, eax
    and     r10d, 0FFh
    shl     r10d, 16
    mov     eax, r8d
    or      eax, r9d
    or      eax, r10d
    ret

_pyfasm_pg_unpack_rect:
    test    rcx, rcx
    jz      .cpur_z
    cmp     rcx, 65536
    jb      .cpur_z
    mov     rax, 5059465245435421h
    cmp     [rcx], rax
    je      .cpur_r
    cmp     qword [rcx], 4
    jl      .cpur_z
    mov     eax, dword [rcx + 8]
    mov     edx, dword [rcx + 16]
    mov     r8d, dword [rcx + 24]
    mov     r9d, dword [rcx + 32]
    jmp     .cpur_s
.cpur_r:
    mov     eax, dword [rcx + 48]
    mov     edx, dword [rcx + 56]
    mov     r8d, dword [rcx + 64]
    mov     r9d, dword [rcx + 72]
.cpur_s:
    mov     dword [_pyfasm_pg_rc], eax
    mov     dword [_pyfasm_pg_rc + 4], edx
    add     eax, r8d
    add     edx, r9d
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     dword [_pyfasm_pg_rc + 12], edx
    ret
.cpur_z:
    xor     eax, eax
    mov     dword [_pyfasm_pg_rc], eax
    mov     dword [_pyfasm_pg_rc + 4], eax
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     dword [_pyfasm_pg_rc + 12], eax
    ret

_pyfasm_pg_surface_new:
    ; RCX = w_or_tuple, RDX = h -> RAX = PYFPGSRF (64B: +0 magic, +8 w, +16 h, +24 row_stride, +32 pix_buf, +40 alpha)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, 100
    mov     rdi, 100
    cmp     rcx, 65536
    jb      .cpsn_d
    cmp     qword [rcx], 2
    jl      .cpsn_d
    mov     rsi, [rcx + 8]
    mov     rdi, [rcx + 16]
    jmp     .cpsn_chk
.cpsn_d:
    test    rcx, rcx
    jz      .cpsn_chk
    mov     rsi, rcx
    test    rdx, rdx
    jz      .cpsn_chk
    mov     rdi, rdx
.cpsn_chk:
    cmp     rsi, 1
    jge     .cpsn_w
    mov     esi, 1
.cpsn_w:
    cmp     rdi, 1
    jge     .cpsn_h
    mov     edi, 1
.cpsn_h:
    lea     eax, [esi * 3 + 3]
    and     eax, -4
    mov     r12d, eax               ; row_stride
    mov     ecx, 64
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     rax, 5059465047535246h
    mov     [rbx + 0], rax
    mov     [rbx + 8], rsi
    mov     [rbx + 16], rdi
    mov     [rbx + 24], r12
    mov     qword [rbx + 40], 255
    mov     rcx, r12
    imul    rcx, rdi
    call    _pyfasm_alloc
    mov     [rbx + 32], rax
    mov     rcx, [_pyfasm_pg_surf_cnt]
    cmp     rcx, 256
    jge     .cpsn_ret
    mov     [_pyfasm_pg_surf_tbl + rcx * 8], rbx
    inc     qword [_pyfasm_pg_surf_cnt]
.cpsn_ret:
    mov     rax, rbx
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_resolve_surf:
    mov     r9, [_pyfasm_pg_surf_cnt]
    xor     r10d, r10d
.cprs_lp:
    cmp     r10, r9
    jge     .cprs_scr
    cmp     rcx, [_pyfasm_pg_surf_tbl + r10 * 8]
    je      .cprs_ok
    inc     r10
    jmp     .cprs_lp
.cprs_scr:
    mov     rcx, [_pyfasm_pg_screen_surf]
    test    rcx, rcx
    jnz     .cprs_ok
    xor     eax, eax
    xor     edx, edx
    xor     r8d, r8d
    ret
.cprs_ok:
    mov     rax, rcx
    mov     rdx, [rcx + 8]
    mov     r8, [rcx + 16]
    ret

_pyfasm_pg_init:
_pyfasm_pg_quit:
_pyfasm_pg_set_caption:
_pyfasm_pg_flip:
_pyfasm_pg_pump_messages:
_pyfasm_pg_enqueue_ev:
_pyfasm_pg_vk_to_py:
_pyfasm_pg_wnd_proc:
_pyfasm_pg_surface_set_alpha:
_pyfasm_pg_draw_arc:
_pyfasm_pg_blit:
_pyfasm_pg_mixer_noop:
    xor     eax, eax
    ret

_pyfasm_pg_set_mode:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_pg_surface_new
    mov     [_pyfasm_pg_screen_surf], rax
    mov     rcx, [rax + 8]
    mov     [_pyfasm_pg_width], rcx
    mov     rcx, [rax + 16]
    mov     [_pyfasm_pg_height], rcx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_display_get_surface:
    mov     rax, [_pyfasm_pg_screen_surf]
    ret

_pyfasm_pg_surface_get_size:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_pg_resolve_surf
    mov     rbx, rdx
    mov     rsi, r8
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_surface_get_width:
    call    _pyfasm_pg_resolve_surf
    mov     rax, rdx
    ret

_pyfasm_pg_surface_get_height:
    call    _pyfasm_pg_resolve_surf
    mov     rax, r8
    ret

_pyfasm_pg_surface_get_rect:
    call    _pyfasm_pg_resolve_surf
    mov     r9, r8
    mov     r8, rdx
    xor     ecx, ecx
    xor     edx, edx
    jmp     _pyfasm_pg_rect_new

_pyfasm_pg_surface_copy:
    cmp     rcx, 65536
    jb      .cpsc_s
    mov     rax, 5059465245435421h
    cmp     [rcx], rax
    je      _pyfasm_pg_rect_copy
.cpsc_s:
    call    _pyfasm_pg_resolve_surf
    mov     rcx, rdx
    mov     rdx, r8
    jmp     _pyfasm_pg_surface_new

_pyfasm_pg_fill:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .cpf_d
    mov     rsi, rax
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     r8, [rsi + 16]
    imul    r8, [rsi + 24]
    mov     rdi, [rsi + 32]
    xor     rcx, rcx
.cpf_lp:
    cmp     rcx, r8
    jge     .cpf_d
    mov     byte [rdi + rcx], al
    inc     rcx
    jmp     .cpf_lp
.cpf_d:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_draw_rect:
_pyfasm_pg_draw_circle:
_pyfasm_pg_draw_ellipse:
_pyfasm_pg_draw_line:
_pyfasm_pg_draw_polygon:
_pyfasm_pg_draw_lines:
    xor     eax, eax
    ret

_pyfasm_pg_font_new:
    mov     rax, 1
    ret

_pyfasm_pg_font_render:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rcx, rdx
    call    _pyfasm_pg_unpack_color
    mov     esi, eax
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     rdx, 5059465047545854h
    mov     [rax], rdx
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     qword [rax + 24], 0
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_font_size:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rcx, rdx
    call    _pyfasm_str_len
    imul    rbx, rax, 8
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     [rax + 8], rbx
    mov     qword [rax + 16], 16
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_image_save:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .cpis_d
    mov     rcx, rbx
    mov     rdx, [rax + 8]
    mov     r8, [rax + 16]
    mov     r9, [rax + 32]
    call    _pyfasm_common_write_bmp24
.cpis_d:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_image_load:
    mov     ecx, 32
    mov     edx, 32
    jmp     _pyfasm_pg_surface_new

_pyfasm_pg_transform_scale:
    cmp     rdx, 65536
    jb      .cpts_d
    mov     rcx, [rdx + 8]
    mov     rdx, [rdx + 16]
    jmp     _pyfasm_pg_surface_new
.cpts_d:
    mov     rcx, rdx
    mov     rdx, r8
    jmp     _pyfasm_pg_surface_new

_pyfasm_pg_transform_flip:
    jmp     _pyfasm_pg_surface_copy

_pyfasm_pg_poll_events:
    mov     rax, [_pyfasm_pg_ev_list]
    test    rax, rax
    jnz     .cppe_r
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     [_pyfasm_pg_ev_list], rax
    mov     rsp, rbp
    pop     rbp
.cppe_r:
    ret

_pyfasm_pg_get_pressed:
    mov     qword [_pyfasm_pg_keys_arr], 256
    lea     rax, [_pyfasm_pg_keys_arr]
    ret

_pyfasm_pg_mouse_get_pos:
    lea     rax, [_pyfasm_pg_mouse_pos_arr]
    ret

_pyfasm_pg_mouse_get_pressed:
    lea     rax, [_pyfasm_pg_mouse_btns]
    ret

_pyfasm_pg_clock_tick:
_pyfasm_pg_delay:
    inc     qword [_pyfasm_pg_ticks]
    mov     eax, 16
    ret

_pyfasm_pg_get_ticks:
    mov     rax, [_pyfasm_pg_ticks]
    imul    rax, 16
    ret

_pyfasm_pg_rect_new:
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
    mov     ecx, 96
    call    _pyfasm_alloc
    mov     rcx, 5059465245435421h
    mov     [rax], rcx
    mov     [rax + 48], rbx
    mov     [rax + 56], rsi
    mov     [rax + 64], rdi
    mov     [rax + 72], r12
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_rect_colliderect:
    test    rcx, rcx
    jz      .cprc_no
    test    rdx, rdx
    jz      .cprc_no
    mov     r8, [rcx + 48]
    mov     r9, [rcx + 64]
    add     r9, r8
    mov     r10, [rdx + 48]
    mov     r11, [rdx + 64]
    add     r11, r10
    cmp     r9, r10
    jle     .cprc_no
    cmp     r8, r11
    jge     .cprc_no
    mov     r8, [rcx + 56]
    mov     r9, [rcx + 72]
    add     r9, r8
    mov     r10, [rdx + 56]
    mov     r11, [rdx + 72]
    add     r11, r10
    cmp     r9, r10
    jle     .cprc_no
    cmp     r8, r11
    jge     .cprc_no
    mov     eax, 1
    ret
.cprc_no:
    xor     eax, eax
    ret

_pyfasm_pg_rect_collidepoint:
    test    rcx, rcx
    jz      .cpcp_no
    cmp     rdx, 65536
    jb      .cpcp_xy
    mov     r8, [rdx + 16]
    mov     rdx, [rdx + 8]
.cpcp_xy:
    mov     r9, [rcx + 48]
    cmp     rdx, r9
    jl      .cpcp_no
    add     r9, [rcx + 64]
    cmp     rdx, r9
    jge     .cpcp_no
    mov     r9, [rcx + 56]
    cmp     r8, r9
    jl      .cpcp_no
    add     r9, [rcx + 72]
    cmp     r8, r9
    jge     .cpcp_no
    mov     eax, 1
    ret
.cpcp_no:
    xor     eax, eax
    ret

_pyfasm_pg_rect_move:
    test    rcx, rcx
    jz      .cprm_z
    mov     r9, [rcx + 72]
    mov     r10, [rcx + 64]
    mov     rax, [rcx + 48]
    add     rax, rdx
    mov     rdx, [rcx + 56]
    add     rdx, r8
    mov     rcx, rax
    mov     r8, r10
    jmp     _pyfasm_pg_rect_new
.cprm_z:
    xor     eax, eax
    ret

_pyfasm_pg_rect_move_ip:
    test    rcx, rcx
    jz      .cprmip_d
    add     [rcx + 48], rdx
    add     [rcx + 56], r8
.cprmip_d:
    xor     eax, eax
    ret

_pyfasm_pg_rect_inflate:
    test    rcx, rcx
    jz      .cpri_z
    mov     r10, rdx
    mov     r11, r8
    mov     rax, [rcx + 48]
    mov     r9, r10
    sar     r9, 1
    sub     rax, r9
    mov     r9, r11
    sar     r9, 1
    mov     rdx, [rcx + 56]
    sub     rdx, r9
    mov     r8, [rcx + 64]
    add     r8, r10
    mov     r9, [rcx + 72]
    add     r9, r11
    mov     rcx, rax
    jmp     _pyfasm_pg_rect_new
.cpri_z:
    xor     eax, eax
    ret

_pyfasm_pg_rect_copy:
    test    rcx, rcx
    jz      .cprcp_z
    mov     r9, [rcx + 72]
    mov     r8, [rcx + 64]
    mov     rdx, [rcx + 56]
    mov     rcx, [rcx + 48]
    jmp     _pyfasm_pg_rect_new
.cprcp_z:
    xor     eax, eax
    ret

_pyfasm_pg_rect_clamp_ip:
    test    rcx, rcx
    jz      .cprcl_d
    test    rdx, rdx
    jz      .cprcl_d
    mov     r8, [rcx + 48]
    mov     r9, [rdx + 48]
    cmp     r8, r9
    jge     .cprcl_x1
    mov     r8, r9
.cprcl_x1:
    mov     [rcx + 48], r8
.cprcl_d:
    xor     eax, eax
    ret

_pyfasm_pg_rect_collidelist:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .cprcli_no
    cmp     rdx, 65536
    jb      .cprcli_no
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, [rsi]
    mov     qword [rsp + 32], 0
.cprcli_lp:
    mov     rax, [rsp + 32]
    cmp     rax, rdi
    jge     .cprcli_no
    mov     rcx, rbx
    mov     rdx, [rsi + 8 + rax * 8]
    call    _pyfasm_pg_rect_colliderect
    test    rax, rax
    jnz     .cprcli_hit
    inc     qword [rsp + 32]
    jmp     .cprcli_lp
.cprcli_hit:
    mov     rax, [rsp + 32]
    jmp     .cprcli_d
.cprcli_no:
    mov     rax, -1
.cprcli_d:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_color_new:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    cmp     rcx, 65536
    jb      .cpcn_rgb
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     ebx, eax
    jmp     .cpcn_alloc
.cpcn_rgb:
    mov     ebx, ecx
    and     ebx, 0FFh
    and     edx, 0FFh
    shl     edx, 8
    and     r8d, 0FFh
    shl     r8d, 16
    or      ebx, edx
    or      ebx, r8d
.cpcn_alloc:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     rcx, 5059465047434F4Ch
    mov     [rax], rcx
    mov     [rax + 8], rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_group_new:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================================
; Portable Threading, HTTP, JSON & External Symbol Fallbacks
; ============================================================================

_pyfasm_spawn_thread:
    ; RCX = fn_ptr, RDX = arg1 -> synchronous portable invocation
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_invoke_cb
    mov     eax, 1
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_wait_thread:
_pyfasm_http_register_route:
_pyfasm_http_server_run:
_pyfasm_load_ext_symbol:
_pyfasm_json_copy_cstr:
_pyfasm_json_write_escaped_str:
_pyfasm_json_write_list:
_pyfasm_json_write_dict:
_pyfasm_json_write_auto:
    xor     eax, eax
    ret

_pyfasm_http_get:
    lea     rax, [_pyfasm_cmn_http_resp]
    ret

_pyfasm_url_decode_alloc:
    mov     rax, rcx
    ret
"""
