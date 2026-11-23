"""
Native Windows x64 Runtime for PyFASM.
Provides essential I/O, memory, threading, and atomic operations with strict x64 ABI alignment.
"""
from __future__ import annotations


def get_win64_runtime_header(is_dll: bool = False) -> str:
    """Returns the FASM PE64 header and inclusion directives."""
    if is_dll:
        return """format PE64 DLL
entry DllEntryPoint

include 'win64a.inc'
"""
    return """format PE64 console 5.0
entry _pyfasm_entry_point

include 'win64a.inc'
"""


def _get_win64_full_runtime_data() -> str:
    """Returns runtime data structures (buffers, handles, constants)."""
    return """
section '.data' data readable writeable
    hStdOut         dq 0
    hStdIn          dq 0
    bytesWritten    dq 0
    bytesRead       dq 0
    crlf_str        db 13, 10, 0
    minus_str       db '-', 0
    dot_str         db '.', 0
    none_str        db 'None', 0
    szNanoGemmISA   db 'AVX2+FMA (PyFASM NanoGEMM Native SIMD)', 0
    flt_1m          dq 1000000.0
    flt_ten         dq 10.0
    flt_zero        dq 0.0
    lbrack_str      db '[', 0
    rbrack_str      db ']', 0
    lbrace_str      db '{', 0
    rbrace_str      db '}', 0
    lparen_str      db '(', 0
    rparen_str      db ')', 0
    comma_str       db ',', 0
    comma_sp_str    db ', ', 0
    colon_sp_str    db ': ', 0
    squote_str      db 39, 0
    empty_set_str   db 'set()', 0
    align 8
    inp_buf         rb 4096
    align 8
    inp_wbuf        rw 2048
    align 4
    consoleMode     dd 0
    isStdOutConsole dd 0
    isStdInConsole  dd 0

    ; --- Native Win32 GUI Runtime Data ---
    _pyfasm_wnd_class   db 'PyFasmWindowClass', 0
    _pyfasm_wnd_title   db 'PyFasm Native Application', 0
    _pyfasm_wnd_title_ptr dq _pyfasm_wnd_title
    _pyfasm_h_wnd       dq 0
    _pyfasm_h_inst      dq 0
    _pyfasm_h_font      dq 0
    align 8
    _pyfasm_wc          rb 80 ; WNDCLASSEXA
    _pyfasm_msg         rb 48 ; MSG

    ; Win32 Window Control Classes
    szButtonClass       db 'BUTTON', 0
    szEditClass         db 'EDIT', 0
    szStaticClass       db 'STATIC', 0
    szListBoxClass      db 'LISTBOX', 0

    ; Registry / Dark Detect Data
    _pyfasm_reg_theme_key   db 'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize', 0
    _pyfasm_reg_theme_val   db 'AppsUseLightTheme', 0
    align 4
    _pyfasm_reg_val_data    dd 0
    _pyfasm_reg_val_size    dd 4

    ; WinINet HTTP Client & Response Data
    _pyfasm_http_agent      db 'PyFASM-Native/1.0', 0
    _pyfasm_http_ok_str     db 'OK', 0
    _pyfasm_http_err_str    db 'Error', 0
    align 4
    _pyfasm_http_read_bytes dd 0
    align 8
    _pyfasm_http_resp_obj   dq 0, 0, 0, 0 ; [status_code, text, json, reason]
    align 8
    _pyfasm_http_buf        rb 65536 ; 64KB HTTP response buffer
    align 8
    _pyfasm_http_url_buf    rb 2048  ; 2KB URL + query params buffer

    ; HTML entity stripping buffer
    align 8
    _pyfasm_strip_buf       rb 65536

    ; Theme Strings & Int Buffer
    szDarkStr               db 'Dark', 0
    szLightStr              db 'Light', 0
    align 8
    _pyfasm_int_buf         rb 32

    ; GUI Handles & State
    _pyfasm_last_gui_instance dq 0
    _pyfasm_last_edit_hwnd  dq 0
    _pyfasm_last_list_hwnd  dq 0
    _pyfasm_last_label_hwnd dq 0
    _pyfasm_last_btn_hwnd   dq 0
    _pyfasm_layout_curr_x   dq 30
    _pyfasm_layout_curr_y   dq 20
    _pyfasm_ctrl_count      dq 0

    ; Control Callback Table (up to 128 controls)
    align 8
    _pyfasm_ctrl_ids        rd 128
    align 8
    _pyfasm_ctrl_callbacks  rq 128
    align 8
    _pyfasm_ctrl_hwnds      rq 128
    align 8
    _pyfasm_canvas_color    dd 0FFFFFFFFh
    _pyfasm_canvas_color_pad dd 0

    ; Static Buffers
    align 8
    _pyfasm_edit_buf        rb 2048
    _pyfasm_status_buf      rb 2048

    ; --- Modern Unicode UTF-16 Win32 GUI Runtime Data ---
    align 8
    _pyfasm_wnd_class_w     du 'PyFasmWindowClassW', 0
    _pyfasm_tray_class_w    du 'PyFasmTrayClassW', 0
    _pyfasm_wnd_title_w     du 'PyFASM Application', 0
    _pyfasm_wnd_title_w_ptr dq _pyfasm_wnd_title_w

    szButtonClassW          du 'BUTTON', 0
    szEditClassW            du 'EDIT', 0
    szStaticClassW          du 'STATIC', 0
    szListBoxClassW         du 'LISTBOX', 0
    wszSegoeUI              du 'Segoe UI', 0
    wszConsolas             du 'Consolas', 0

    ; --- PyFASM Universal Geometry Engine & Layout SDK Data ---
    align 8
    _pyfasm_card_class_w    du 'PyFasmCardClassW', 0
    _pyfasm_canvas_class_w  du 'PyFasmCanvasClassW', 0
    _pyfasm_hbr_canvas      dq 0
    _pyfasm_hpen_card_border dq 0

    ; Layout Descriptors Table (capacity 256 widgets, 64 bytes per entry)
    align 16
    _pyfasm_layout_count    dq 0
    align 16
    _pyfasm_layout_table    rb 256 * 64

    ; Container Configuration Table (capacity 32 containers, 272 bytes per entry)
    align 16
    _pyfasm_container_cfg_count dq 0
    align 16
    _pyfasm_container_cfg_table rb 32 * 272

    ; Temporary geometry calculation buffers (32 cols, 32 rows)
    align 16
    _pyfasm_col_widths      rd 32
    _pyfasm_row_heights     rd 32
    _pyfasm_col_pos         rd 32
    _pyfasm_row_pos         rd 32
    align 16
    _pyfasm_layout_rc       rb 32

    ; Dark Theme GDI Brushes & Attributes
    align 8
    _pyfasm_dark_mode_val   dd 1
    _pyfasm_caption_color   dd 001A110Fh
    _pyfasm_caption_text_color dd 00FFFFFFh
    wszDarkModeExplorer     du 'DarkMode_Explorer', 0
    _pyfasm_hbr_bg          dq 0 ; #0f111a
    _pyfasm_hbr_card        dq 0 ; #1d1f2e
    _pyfasm_hbr_input       dq 0 ; #141620
    _pyfasm_hbr_orange      dq 0 ; #f48024
    _pyfasm_hbr_orange_press dq 0 ; #da670b
    _pyfasm_hbr_card_sel    dq 0 ; #141b26
    _pyfasm_hbr_green_pill  dq 0 ; #28a745
    _pyfasm_hpen_green_pill dq 0 ; #28a745
    _pyfasm_hpen_orange     dq 0
    _pyfasm_hpen_slate      dq 0
    align 8
    _pyfasm_card_text_buf   rw 512
    align 16
    _pyfasm_wide_buf        rw 1024
    align 8
    _pyfasm_rc_client       rd 4
    _pyfasm_h_font_ui       dq 0
    _pyfasm_h_font_bold     dq 0
    _pyfasm_h_font_mono     dq 0
    _pyfasm_h_font_title    dq 0
    _pyfasm_h_icon_big      dq 0
    _pyfasm_h_icon_small    dq 0
    wszIconFile             du 'icon.ico', 0
    wszTrayIconFile         du 'icon.ico', 0

    ; Universal GUI Widget Metadata, Auxiliary Styling, Bindings, Timers & Controls
    align 8
    _pyfasm_widget_aux      rb 256 * 64 ; [0:hbr, 8:fg_u32, 12:tc_u32, 16:fg_pq, 24:tc_pq, 32:hfont, 40:sv_ptr, 48:aux_ptr, 56:id|flags]
    _pyfasm_container_min_table rb 32 * 272 ; [0:hwnd, 8..135:col_minsize, 136..263:row_minsize]
    _pyfasm_sv_trace_cnt    dq 0
    _pyfasm_sv_traces       rb 64 * 24  ; [sv_ptr, cb_ptr, hwnd]
    _pyfasm_timer_cnt       dq 0
    _pyfasm_timers          rb 32 * 24  ; [id, hwnd, cb_ptr]
    _pyfasm_bind_cnt        dq 0
    _pyfasm_binds           rb 64 * 24  ; [hwnd, ev_code, cb_ptr]
    _pyfasm_seg_cnt         dq 0
    _pyfasm_segs            rb 16 * 128 ; segmented button descriptors
    _pyfasm_sv_updating     dd 0
    _pyfasm_combo_class_w   du 'COMBOBOX', 0
    _pyfasm_trackbar_class_w du 'msctls_trackbar32', 0
    _pyfasm_progress_class_w du 'msctls_progress32', 0
    _pyfasm_ofn_filter      du 'All Files (*.*)', 0, '*.*', 0, 0
    _pyfasm_fd_wide_buf     rw 520
    _pyfasm_fd_ofn_buf      rb 160
    _pyfasm_qt_layout_list_cnt dq 0
    _pyfasm_qt_pending_layouts rq 64
    _pyfasm_sz_dark_mode    db 'Dark', 0
    _pyfasm_sz_light_mode   db 'Light', 0
    _pyfasm_str_tag_return  db 'return', 0
    _pyfasm_str_tag_key     db 'key', 0
    _pyfasm_str_tag_btn1    db 'button-1', 0
    align 4
    _pyfasm_theme_bg        dd 001A110Fh ; #0f111a (dark) / #f8fafc (light)
    _pyfasm_theme_card      dd 002B241Eh ; #1e242b (dark) / #ffffff (light)
    _pyfasm_theme_input     dd 00241D18h ; #181d24 (dark) / #f1f5f9 (light)
    _pyfasm_theme_text      dd 00F0EAE4h ; #e4eaf0 (dark) / #0f172a (light)
    _pyfasm_theme_muted     dd 00A89988h ; #8899a8
    _pyfasm_theme_accent    dd 00A56A1Fh ; #1f6aa5
    _pyfasm_theme_accent_press dd 007B4814h ; #14487b
    _pyfasm_theme_sel       dd 005C4430h ; #30445c
    _pyfasm_theme_border    dd 00554133h ; #334155
    align 8
    _pyfasm_hbr_sel         dq 0
    _pyfasm_text_extent_sz  dd 0, 0
    _pyfasm_last_combo_hwnd dq 0
    _pyfasm_last_prog_hwnd  dq 0
    _pyfasm_last_slider_hwnd dq 0

    ; System Tray Data structures for Background Apps
    align 8
    _pyfasm_tray_hwnd       dq 0
    _pyfasm_tray_nid        rb 1024 ; NOTIFYICONDATAW (976 bytes on Win64)
    _pyfasm_tray_wc         rb 80   ; WNDCLASSEXW
    _pyfasm_tray_enabled    dd 1
    _pyfasm_tray_sound      dd 1
    align 8
    _pyfasm_cursor_pt       rq 2    ; POINT (x, y)
    wszTrayTipOn            du 'PyFASM App (Active: ON)', 0
    wszTrayTipOff           du 'PyFASM App (Active: OFF)', 0
    wszMenuAuto             du 'Auto-switch', 0
    wszMenuSound            du 'Sound notification', 0
    wszMenuHotkey           du 'Manual Switch: Pause/Break or F8', 0
    wszMenuExit             du 'Exit', 0
"""


def _get_win64_full_runtime_code() -> str:
    """Returns native assembly routines with strict 16-byte stack alignment."""
    return """
section '.text' code readable executable

_pyfasm_init_io:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, 65001              ; CP_UTF8
    call    [SetConsoleOutputCP]
    mov     ecx, 65001              ; CP_UTF8
    call    [SetConsoleCP]
    mov     ecx, -11                ; STD_OUTPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdOut], rax
    mov     rcx, rax
    lea     rdx, [consoleMode]
    call    [GetConsoleMode]
    mov     [isStdOutConsole], eax
    mov     ecx, -10                ; STD_INPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdIn], rax
    mov     rcx, rax
    lea     rdx, [consoleMode]
    call    [GetConsoleMode]
    mov     [isStdInConsole], eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_str:
    ; RCX = pointer to null-terminated UTF-8 string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .done_print_str

    ; Calculate UTF-8 byte length
    xor     eax, eax
    mov     rdi, rsi
    mov     rcx, -1
    repne   scasb
    not     rcx
    dec     rcx
    mov     rbx, rcx                ; byte length in rbx
    test    rbx, rbx
    jz      .done_print_str

    cmp     dword [isStdOutConsole], 0
    je      .print_str_file
    cmp     rbx, 32768
    ja      .print_str_file

    ; Query UTF-16 character count
    mov     ecx, 65001              ; CP_UTF8
    xor     edx, edx
    mov     r8, rsi
    mov     r9d, ebx
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    call    [MultiByteToWideChar]
    test    eax, eax
    jle     .print_str_file
    cmp     eax, 1024
    jg      .print_str_file

    mov     r12d, eax
    sub     rsp, 2112               ; shadow (32) + args (32) + 1024 wchars (2048), 16-byte aligned
    mov     ecx, 65001
    xor     edx, edx
    mov     r8, rsi
    mov     r9d, ebx
    lea     rax, [rsp + 64]
    mov     [rsp + 32], rax
    mov     [rsp + 40], r12
    call    [MultiByteToWideChar]
    test    eax, eax
    jle     .print_str_console_fail

    mov     rcx, [hStdOut]
    lea     rdx, [rsp + 64]
    mov     r8d, eax
    lea     r9, [rsp + 48]
    mov     dword [rsp + 48], 0
    mov     qword [rsp + 32], 0
    call    [WriteConsoleW]
    test    eax, eax
    jz      .print_str_console_fail
    add     rsp, 2112
    jmp     .done_print_str

.print_str_console_fail:
    add     rsp, 2112

.print_str_file:
    ; WriteFile(hStdOut, rsi, rbx, &bytesWritten, NULL)
    mov     rcx, [hStdOut]
    mov     rdx, rsi
    mov     r8, rbx
    lea     r9, [rsp + 48]
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 32], 0
    call    [WriteFile]

.done_print_str:
    lea     rsp, [rbp - 32]
    pop     r12
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
    test    rcx, rcx
    jz      .sl_zero
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
.sl_zero:
    xor     eax, eax
    ret

_pyfasm_utf8_len:
    ; RCX = pointer to null-terminated UTF-8 string -> RAX = codepoint count
    test    rcx, rcx
    jz      .ul_zero
    xor     eax, eax
.ul_loop:
    movzx   edx, byte [rcx]
    test    dl, dl
    jz      .ul_done
    and     dl, 0C0h
    cmp     dl, 80h
    je      .ul_cont
    inc     rax
.ul_cont:
    inc     rcx
    jmp     .ul_loop
.ul_zero:
    xor     eax, eax
.ul_done:
    ret

_pyfasm_utf8_getitem:
    ; RCX = str_ptr, RDX = signed codepoint index
    ; Returns RAX = heap-allocated 1-codepoint UTF-8 string (or "" if out of range)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     r12, rdx
    test    rsi, rsi
    jz      .ug_empty
    cmp     r12, 0
    jge     .ug_nonneg
    mov     rcx, rsi
    call    _pyfasm_utf8_len
    add     r12, rax
    cmp     r12, 0
    jl      .ug_empty

.ug_nonneg:
    xor     r13d, r13d
.ug_scan:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .ug_empty
    mov     edx, eax
    and     dl, 0C0h
    cmp     dl, 80h
    je      .ug_step_only
    cmp     r13, r12
    je      .ug_found
    inc     r13
.ug_step_only:
    inc     rsi
    jmp     .ug_scan

.ug_found:
    movzx   eax, byte [rsi]
    mov     rbx, 1
    cmp     al, 0C2h
    jb      .ug_alloc
    cmp     al, 0DFh
    jbe     .ug_len2
    cmp     al, 0EFh
    jbe     .ug_len3
    cmp     al, 0F4h
    jbe     .ug_len4
    jmp     .ug_alloc
.ug_len2:
    mov     rbx, 2
    jmp     .ug_clamp
.ug_len3:
    mov     rbx, 3
    jmp     .ug_clamp
.ug_len4:
    mov     rbx, 4
.ug_clamp:
    mov     r13, 1
.ug_chk:
    cmp     r13, rbx
    jae     .ug_alloc
    cmp     byte [rsi + r13], 0
    je      .ug_trunc
    inc     r13
    jmp     .ug_chk
.ug_trunc:
    mov     rbx, r13

.ug_alloc:
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ug_cp:
    cmp     rcx, rbx
    jae     .ug_nul
    mov     dl, byte [rsi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ug_cp
.ug_nul:
    mov     byte [rax + rbx], 0
    jmp     .ug_ret

.ug_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.ug_ret:
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    sub     rsp, 64
    and     rsp, -16
    ucomisd xmm0, [flt_zero]
    jae     .flt_pos
    movsd   [rbp - 24], xmm0
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    movsd   xmm0, [rbp - 24]
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.flt_pos:
    movsd   [rbp - 24], xmm0
    cvttsd2si rax, xmm0
    mov     [rbp - 32], rax
    mov     rcx, rax
    call    _pyfasm_print_int
    lea     rcx, [dot_str]
    call    _pyfasm_print_str

    movsd   xmm0, [rbp - 24]
    cvtsi2sd xmm1, qword [rbp - 32]
    subsd   xmm0, xmm1
    mulsd   xmm0, [flt_1m]
    mov     rax, 3FE0000000000000h
    movq    xmm1, rax
    addsd   xmm0, xmm1
    cvttsd2si rax, xmm0
    test    rax, rax
    jns     .frac_nonneg
    xor     eax, eax
.frac_nonneg:
    cmp     rax, 1000000
    jl      .frac_check_zero
    mov     rax, 999999
.frac_check_zero:
    test    rax, rax
    jnz     .frac_padded
    xor     ecx, ecx
    call    _pyfasm_print_int
    jmp     .flt_done
.frac_padded:
    lea     rdi, [rbp - 42]
    mov     byte [rdi], 0
    mov     rbx, 10
    mov     ecx, 6
.frac_digit_loop:
    xor     edx, edx
    div     rbx
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    dec     ecx
    jnz     .frac_digit_loop
    mov     rcx, rdi
    call    _pyfasm_print_str
.flt_done:
    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rbx
    pop     rbp
    ret

_pyfasm_float_to_str:
    ; RCX = IEEE-754 float64 bits -> RAX = heap-allocated string pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 96
    and     rsp, -16

    mov     [rbp - 40], rcx
    mov     ecx, 64
    call    _pyfasm_alloc
    mov     r12, rax
    mov     rdi, rax

    movq    xmm0, qword [rbp - 40]
    ucomisd xmm0, [flt_zero]
    jae     .fts_pos
    mov     byte [rdi], '-'
    inc     rdi
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.fts_pos:
    movsd   [rbp - 48], xmm0
    cvttsd2si rax, xmm0
    mov     [rbp - 56], rax

    lea     rsi, [rbp - 64]
    mov     byte [rsi], 0
    mov     rbx, 10
    test    rax, rax
    jnz     .fts_int_loop
    mov     byte [rdi], '0'
    inc     rdi
    jmp     .fts_dot
.fts_int_loop:
    test    rax, rax
    jz      .fts_int_copy
    xor     edx, edx
    div     rbx
    add     dl, '0'
    dec     rsi
    mov     [rsi], dl
    jmp     .fts_int_loop
.fts_int_copy:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .fts_dot
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .fts_int_copy

.fts_dot:
    mov     byte [rdi], '.'
    inc     rdi

    movsd   xmm0, [rbp - 48]
    cvtsi2sd xmm1, qword [rbp - 56]
    subsd   xmm0, xmm1
    mulsd   xmm0, [flt_1m]
    mov     rax, 3FE0000000000000h
    movq    xmm1, rax
    addsd   xmm0, xmm1
    cvttsd2si rax, xmm0
    test    rax, rax
    jns     .fts_frac_nonneg
    xor     eax, eax
.fts_frac_nonneg:
    cmp     rax, 1000000
    jl      .fts_frac_check_zero
    mov     rax, 999999
.fts_frac_check_zero:
    test    rax, rax
    jnz     .fts_frac_digits
    mov     byte [rdi], '0'
    inc     rdi
    jmp     .fts_done

.fts_frac_digits:
    mov     rbx, 10
    mov     ecx, 6
    lea     rsi, [rdi + 5]
.fts_frac_loop:
    xor     edx, edx
    div     rbx
    add     dl, '0'
    mov     [rsi], dl
    dec     rsi
    dec     ecx
    jnz     .fts_frac_loop
    add     rdi, 6

.fts_done:
    mov     byte [rdi], 0
    mov     rax, r12
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret


_pyfasm_file_open:
    ; RCX = filename string, RDX = mode string (e.g. "w", "r", "a", or 0)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx
    mov     rdi, rdx

    mov     ebx, 'r'
    test    rdi, rdi
    jz      .fo_mode_ready
    movzx   ebx, byte [rdi]
.fo_mode_ready:

    cmp     ebx, 'w'
    je      .fo_mode_write
    cmp     ebx, 'a'
    je      .fo_mode_append

    ; Mode 'r'
    mov     rcx, rsi
    mov     edx, 80000000h          ; GENERIC_READ
    mov     r8d, 1                  ; FILE_SHARE_READ
    xor     r9d, r9d
    mov     qword [rsp + 32], 3      ; OPEN_EXISTING
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    jmp     .fo_open_done

.fo_mode_write:
    mov     rcx, rsi
    mov     edx, 40000000h          ; GENERIC_WRITE
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 2      ; CREATE_ALWAYS
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    jmp     .fo_open_done

.fo_mode_append:
    mov     rcx, rsi
    mov     edx, 40000000h          ; GENERIC_WRITE
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 4      ; OPEN_ALWAYS
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    cmp     rax, -1
    je      .fo_open_done
    mov     rbx, rax
    mov     rcx, rax
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, 2                  ; FILE_END
    call    [SetFilePointer]
    mov     rax, rbx

.fo_open_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_file_write_data:
    ; RCX = file handle, RDX = content string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 64
    and     rsp, -16

    test    rcx, rcx
    jz      .err_f_write
    cmp     rcx, -1
    je      .err_f_write

    mov     rbx, rcx
    mov     rsi, rdx

    mov     rcx, rsi
    test    rcx, rcx
    jz      .zero_len_write
    call    _pyfasm_str_len
    mov     r8, rax
    jmp     .do_f_write
.zero_len_write:
    xor     r8d, r8d
.do_f_write:
    mov     rcx, rbx
    mov     rdx, rsi
    lea     r9, [rsp + 40]
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    jmp     .f_write_done

.err_f_write:
    xor     eax, eax
.f_write_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_file_read_all:
    ; RCX = file handle
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16

    test    rcx, rcx
    jz      .empty_f_read
    cmp     rcx, -1
    je      .empty_f_read

    mov     rbx, rcx

    mov     rcx, rbx
    xor     edx, edx
    call    [GetFileSize]
    cmp     eax, -1
    je      .empty_f_read
    test    eax, eax
    jz      .empty_f_read

    mov     esi, eax

    lea     ecx, [rsi + 1]
    call    _pyfasm_alloc
    test    rax, rax
    jz      .empty_f_read
    mov     rdi, rax

    mov     rcx, rbx
    mov     rdx, rdi
    mov     r8d, esi
    lea     r9, [rsp + 40]
    mov     qword [rsp + 32], 0
    call    [ReadFile]

    mov     eax, [rsp + 40]
    mov     byte [rdi + rax], 0
    mov     rax, rdi
    jmp     .f_read_done

.empty_f_read:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.f_read_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_file_close:
    ; RCX = file handle
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jz      .fc_close_done
    cmp     rcx, -1
    je      .fc_close_done

    call    [CloseHandle]
.fc_close_done:
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

_pyfasm_is_dark_theme:
    ; Checks Windows Registry for dark theme:
    ; HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize -> AppsUseLightTheme
    push    rbp
    mov     rbp, rsp
    sub     rsp, 80
    and     rsp, -16

    mov     ecx, 80000001h                 ; HKEY_CURRENT_USER
    movsxd  rcx, ecx
    lea     rdx, [_pyfasm_reg_theme_key]
    xor     r8d, r8d                       ; reserved = 0
    mov     r9d, 20019h                    ; KEY_READ
    lea     rax, [rbp - 8]                 ; phkResult
    mov     [rsp + 32], rax
    call    [RegOpenKeyExA]
    test    eax, eax
    jnz     .fallback_dark

    ; Query AppsUseLightTheme
    mov     rcx, [rbp - 8]                 ; hKey
    lea     rdx, [_pyfasm_reg_theme_val]
    xor     r8d, r8d                       ; lpReserved = NULL
    xor     r9d, r9d                       ; lpType = NULL
    mov     dword [_pyfasm_reg_val_size], 4
    lea     rax, [_pyfasm_reg_val_data]
    mov     [rsp + 32], rax                ; lpData
    lea     rax, [_pyfasm_reg_val_size]
    mov     [rsp + 40], rax                ; lpcbData
    call    [RegQueryValueExA]

    mov     [rbp - 16], rax
    mov     rcx, [rbp - 8]
    call    [RegCloseKey]
    mov     rax, [rbp - 16]

    test    eax, eax
    jnz     .fallback_dark

    mov     eax, [_pyfasm_reg_val_data]
    test    eax, eax
    setz    al                             ; 1 if AppsUseLightTheme == 0 (Dark)
    movzx   rax, al
    mov     rsp, rbp
    pop     rbp
    ret

.fallback_dark:
    mov     rax, 1                         ; Default to Dark theme
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_strip_html:
    ; RCX = pointer to input HTML string
    ; Returns RAX = pointer to stripped plain text string (_pyfasm_strip_buf)
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx

    mov     rsi, rcx
    lea     rdi, [_pyfasm_strip_buf]
    test    rsi, rsi
    jz      .done_empty

    xor     ebx, ebx                       ; ebx = in_tag flag (0 or 1)

.scan_loop:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .finish_scan

    cmp     al, '<'
    je      .enter_tag

    cmp     al, '>'
    je      .exit_tag

    test    ebx, ebx
    jnz     .skip_char                     ; inside <...>, skip byte

    ; Check for HTML entity &...;
    cmp     al, '&'
    je      .check_entity

    mov     [rdi], al
    inc     rdi
    inc     rsi
    jmp     .scan_loop

.enter_tag:
    mov     ebx, 1
    inc     rsi
    jmp     .scan_loop

.exit_tag:
    xor     ebx, ebx
    inc     rsi
    jmp     .scan_loop

.skip_char:
    inc     rsi
    jmp     .scan_loop

.check_entity:
    ; Check &quot; -> "
    cmp     dword [rsi + 1], 'quot'
    jne     .check_amp
    cmp     byte [rsi + 5], ';'
    jne     .check_amp
    mov     byte [rdi], '"'
    inc     rdi
    add     rsi, 6
    jmp     .scan_loop

.check_amp:
    cmp     dword [rsi + 1], 'amp;'
    jne     .check_lt
    mov     byte [rdi], '&'
    inc     rdi
    add     rsi, 5
    jmp     .scan_loop

.check_lt:
    cmp     word [rsi + 1], 'lt'
    jne     .check_gt
    cmp     byte [rsi + 3], ';'
    jne     .check_gt
    mov     byte [rdi], '<'
    inc     rdi
    add     rsi, 4
    jmp     .scan_loop

.check_gt:
    cmp     word [rsi + 1], 'gt'
    jne     .check_apos
    cmp     byte [rsi + 3], ';'
    jne     .check_apos
    mov     byte [rdi], '>'
    inc     rdi
    add     rsi, 4
    jmp     .scan_loop

.check_apos:
    cmp     dword [rsi + 1], '#39;'
    jne     .entity_default
    mov     byte [rdi], "'"
    inc     rdi
    add     rsi, 5
    jmp     .scan_loop

.entity_default:
    mov     [rdi], al
    inc     rdi
    inc     rsi
    jmp     .scan_loop

.finish_scan:
    mov     byte [rdi], 0
    lea     rax, [_pyfasm_strip_buf]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.done_empty:
    mov     byte [_pyfasm_strip_buf], 0
    lea     rax, [_pyfasm_strip_buf]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_http_get:
    ; RCX = pointer to URL string (e.g. "https://api.stackexchange.com/...")
    ; RDX = pointer to params dictionary (or 0)
    ; Returns RAX = pointer to _pyfasm_http_resp_obj
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx                       ; save URL in rsi
    mov     r12, rdx                       ; save params dict in r12

    ; Format URL with query parameters if params dict provided
    test    r12, r12
    jz      .use_direct_url

    ; Copy base URL to _pyfasm_http_url_buf
    lea     rdi, [_pyfasm_http_url_buf]
    mov     rcx, rsi
.copy_base_url:
    mov     al, [rcx]
    test    al, al
    jz      .base_url_copied
    mov     [rdi], al
    inc     rcx
    inc     rdi
    jmp     .copy_base_url
.base_url_copied:
    ; Check if dict has items
    mov     rax, [r12 + 8]                 ; count of items
    test    rax, rax
    jz      .url_finish
    ; Append '?'
    mov     byte [rdi], '?'
    inc     rdi

    ; Loop over dict slots: capacity = [r12]
    mov     r13, [r12]                     ; capacity
    lea     r14, [r12 + 16]                ; slot ptr
.dict_url_loop:
    test    r13, r13
    jz      .dict_url_done
    dec     r13
    mov     rax, [r14]                     ; slot hash
    test    rax, rax
    jz      .next_url_slot
    cmp     rax, -1
    je      .next_url_slot
    ; Non-empty slot: key = [r14 + 8], val = [r14 + 16]
    mov     rcx, [r14 + 8]                 ; key string
    test    rcx, rcx
    jz      .next_url_slot
.copy_key_loop:
    mov     al, [rcx]
    test    al, al
    jz      .key_copied
    mov     [rdi], al
    inc     rcx
    inc     rdi
    jmp     .copy_key_loop
.key_copied:
    mov     byte [rdi], '='
    inc     rdi
    ; Copy val: could be string (> 65536) or int
    mov     rcx, [r14 + 16]                ; val
    cmp     rcx, 65536
    jb      .copy_val_int
.copy_val_str:
    mov     al, [rcx]
    test    al, al
    jz      .val_copied
    mov     [rdi], al
    inc     rcx
    inc     rdi
    jmp     .copy_val_str
.copy_val_int:
    mov     rax, rcx
    push    r14
    push    r13
    mov     r8, rax
    test    r8, r8
    jns     .pos_val_int
    mov     byte [rdi], '-'
    inc     rdi
    neg     r8
.pos_val_int:
    mov     rax, r8
    mov     r9, 10
    lea     r10, [_pyfasm_int_buf + 30]
    mov     byte [r10], 0
.val_digit_loop:
    xor     edx, edx
    div     r9
    add     dl, '0'
    dec     r10
    mov     [r10], dl
    test    rax, rax
    jnz     .val_digit_loop
.copy_digits:
    mov     al, [r10]
    test    al, al
    jz      .digits_copied
    mov     [rdi], al
    inc     r10
    inc     rdi
    jmp     .copy_digits
.digits_copied:
    pop     r13
    pop     r14
.val_copied:
    mov     byte [rdi], '&'
    inc     rdi
.next_url_slot:
    add     r14, 24
    jmp     .dict_url_loop
.dict_url_done:
    cmp     byte [rdi - 1], '&'
    jne     .url_finish
    dec     rdi
.url_finish:
    mov     byte [rdi], 0
    lea     rsi, [_pyfasm_http_url_buf]
    jmp     .do_http_connect

.use_direct_url:
    ; rsi is already direct url

.do_http_connect:
    ; InternetOpenA
    lea     rcx, [_pyfasm_http_agent]
    mov     edx, 1                         ; INTERNET_OPEN_TYPE_DIRECT
    xor     r8, r8                         ; proxy = NULL
    xor     r9, r9                         ; proxy bypass = NULL
    mov     qword [rsp + 32], 0            ; flags = 0
    call    [InternetOpenA]
    test    rax, rax
    jz      .http_fail
    mov     rbx, rax                       ; rbx = hInternet

    ; InternetOpenUrlA
    mov     rcx, rbx
    mov     rdx, rsi                       ; lpszUrl
    xor     r8, r8                         ; headers = NULL
    xor     r9, r9                         ; headers length = 0
    mov     rax, 84000100h                 ; INTERNET_FLAG_RELOAD | INTERNET_FLAG_SECURE | INTERNET_FLAG_NO_CACHE_WRITE
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 0            ; dwContext = 0
    call    [InternetOpenUrlA]
    test    rax, rax
    jz      .http_close_session
    mov     rsi, rax                       ; rsi = hFile / hUrl

    ; InternetReadFile
    mov     rcx, rsi
    lea     rdx, [_pyfasm_http_buf]
    mov     r8d, 65535                    ; max bytes to read
    lea     r9, [_pyfasm_http_read_bytes]
    call    [InternetReadFile]

    ; Null-terminate response
    mov     eax, [_pyfasm_http_read_bytes]
    mov     byte [_pyfasm_http_buf + rax], 0

    ; Close hUrl
    mov     rcx, rsi
    call    [InternetCloseHandle]

    ; Close hInternet
    mov     rcx, rbx
    call    [InternetCloseHandle]

    ; Populate response object: [status_code, text, json, reason]
    mov     qword [_pyfasm_http_resp_obj], 200
    lea     rax, [_pyfasm_http_buf]
    mov     qword [_pyfasm_http_resp_obj + 8], rax
    mov     qword [_pyfasm_http_resp_obj + 16], 0
    lea     rax, [_pyfasm_http_ok_str]
    mov     qword [_pyfasm_http_resp_obj + 24], rax

    lea     rax, [_pyfasm_http_resp_obj]
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.http_close_session:
    mov     rcx, rbx
    call    [InternetCloseHandle]

.http_fail:
    mov     qword [_pyfasm_http_resp_obj], 0
    mov     byte [_pyfasm_http_buf], 0
    lea     rax, [_pyfasm_http_buf]
    mov     qword [_pyfasm_http_resp_obj + 8], rax
    mov     qword [_pyfasm_http_resp_obj + 16], 0
    lea     rax, [_pyfasm_http_err_str]
    mov     qword [_pyfasm_http_resp_obj + 24], rax

    lea     rax, [_pyfasm_http_resp_obj]
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; Native JSON Parser (Pure x86-64 recursive-descent)
; ============================================================
_pyfasm_json_skip_ws:
.jsw_loop:
    mov     al, [rsi]
    cmp     al, ' '
    je      .jsw_next
    cmp     al, 9                   ; \t
    je      .jsw_next
    cmp     al, 10                  ; \n
    je      .jsw_next
    cmp     al, 13                  ; \r
    je      .jsw_next
    ret
.jsw_next:
    inc     rsi
    jmp     .jsw_loop

_pyfasm_json_parse:
    ; RCX = pointer to JSON string
    ; Returns RAX = parsed dict, list, str, or int
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .jp_null
    mov     rsi, rcx
    call    _pyfasm_json_parse_val
    jmp     .jp_ret
.jp_null:
    xor     eax, eax
.jp_ret:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_json_parse_val:
    call    _pyfasm_json_skip_ws
    mov     al, [rsi]
    test    al, al
    jz      .jpv_zero
    cmp     al, '{'
    je      _pyfasm_json_parse_obj
    cmp     al, '['
    je      _pyfasm_json_parse_arr
    cmp     al, '"'
    je      _pyfasm_json_parse_str
    cmp     al, 't'
    je      .jpv_true
    cmp     al, 'T'
    je      .jpv_true
    cmp     al, 'f'
    je      .jpv_false
    cmp     al, 'F'
    je      .jpv_false
    cmp     al, 'n'
    je      .jpv_null
    cmp     al, 'N'
    je      .jpv_null
    cmp     al, '-'
    je      _pyfasm_json_parse_num
    cmp     al, '0'
    jb      .jpv_zero
    cmp     al, '9'
    jbe     _pyfasm_json_parse_num
.jpv_zero:
    xor     eax, eax
    ret
.jpv_true:
    add     rsi, 4                  ; skip 'true'
    mov     eax, 1
    ret
.jpv_false:
    add     rsi, 5                  ; skip 'false'
    xor     eax, eax
    ret
.jpv_null:
    add     rsi, 4                  ; skip 'null'
    xor     eax, eax
    ret

_pyfasm_json_parse_num:
    xor     rax, rax
    xor     r8d, r8d                ; sign = 0
    cmp     byte [rsi], '-'
    jne     .jpn_loop
    mov     r8d, 1                  ; negative
    inc     rsi
.jpn_loop:
    movzx   ecx, byte [rsi]
    cmp     cl, '0'
    jb      .jpn_done
    cmp     cl, '9'
    ja      .jpn_done
    sub     cl, '0'
    imul    rax, 10
    add     rax, rcx
    inc     rsi
    jmp     .jpn_loop
.jpn_done:
    test    r8d, r8d
    jz      .jpn_ret
    neg     rax
.jpn_ret:
    ret

_pyfasm_json_parse_str:
    ; Expects [rsi] == '"'
    inc     rsi
    mov     rdi, rsi                ; rdi = start
.jps_scan:
    mov     al, [rsi]
    test    al, al
    jz      .jps_copy
    cmp     al, '"'
    je      .jps_copy
    cmp     al, 92                  ; backslash '\'
    jne     .jps_next
    inc     rsi
    cmp     byte [rsi], 0
    je      .jps_copy
.jps_next:
    inc     rsi
    jmp     .jps_scan
.jps_copy:
    mov     rcx, rsi
    sub     rcx, rdi                ; rcx = length in bytes
    push    rcx
    push    rdi
    inc     rcx                     ; +1 for null terminator
    call    _pyfasm_alloc
    pop     rdi
    pop     rcx
    push    rax                     ; save allocated string ptr
    mov     rdx, rax                ; dest in rdx
.jps_unescape:
    cmp     rdi, rsi
    jge     .jps_finish
    mov     al, [rdi]
    cmp     al, 92                  ; backslash
    jne     .jps_put
    inc     rdi
    cmp     rdi, rsi
    jge     .jps_finish
    mov     al, [rdi]
    cmp     al, 'n'
    jne     .jps_chk_r
    mov     al, 10
    jmp     .jps_put
.jps_chk_r:
    cmp     al, 'r'
    jne     .jps_chk_t
    mov     al, 13
    jmp     .jps_put
.jps_chk_t:
    cmp     al, 't'
    jne     .jps_put
    mov     al, 9
.jps_put:
    mov     [rdx], al
    inc     rdx
    inc     rdi
    jmp     .jps_unescape
.jps_finish:
    mov     byte [rdx], 0
    cmp     byte [rsi], '"'
    jne     .jps_ret
    inc     rsi
.jps_ret:
    pop     rax
    ret

_pyfasm_json_parse_arr:
    ; Expects [rsi] == '['
    inc     rsi
    xor     ecx, ecx                ; default capacity
    call    _pyfasm_list_create
    push    rbx
    mov     rbx, rax                ; rbx = list ptr
.jpa_loop:
    call    _pyfasm_json_skip_ws
    mov     al, [rsi]
    test    al, al
    jz      .jpa_done
    cmp     al, ']'
    je      .jpa_done
    cmp     al, ','
    jne     .jpa_val
    inc     rsi
    call    _pyfasm_json_skip_ws
.jpa_val:
    cmp     byte [rsi], ']'
    je      .jpa_done
    call    _pyfasm_json_parse_val
    mov     rdx, rax                ; value in rdx
    mov     rcx, rbx                ; list in rcx
    call    _pyfasm_list_append
    jmp     .jpa_loop
.jpa_done:
    cmp     byte [rsi], ']'
    jne     .jpa_ret
    inc     rsi
.jpa_ret:
    mov     rax, rbx
    pop     rbx
    ret

_pyfasm_json_parse_obj:
    ; Expects [rsi] == '{'
    inc     rsi
    xor     ecx, ecx                ; default capacity (16)
    call    _pyfasm_dict_create
    push    rbx
    mov     rbx, rax                ; rbx = dict ptr
.jpo_loop:
    call    _pyfasm_json_skip_ws
    mov     al, [rsi]
    test    al, al
    jz      .jpo_done
    cmp     al, '}'
    je      .jpo_done
    cmp     al, ','
    jne     .jpo_key
    inc     rsi
    call    _pyfasm_json_skip_ws
.jpo_key:
    cmp     byte [rsi], '}'
    je      .jpo_done
    cmp     byte [rsi], '"'
    jne     .jpo_done               ; invalid key
    call    _pyfasm_json_parse_str
    push    rax                     ; save key on stack
    call    _pyfasm_json_skip_ws
    cmp     byte [rsi], ':'
    jne     .jpo_err
    inc     rsi                     ; skip ':'
    call    _pyfasm_json_parse_val
    mov     r8, rax                 ; value in r8
    pop     rdx                     ; key in rdx
    mov     rcx, rbx                ; dict in rcx
    call    _pyfasm_dict_set
    jmp     .jpo_loop
.jpo_err:
    pop     rax
.jpo_done:
    cmp     byte [rsi], '}'
    jne     .jpo_ret
    inc     rsi
.jpo_ret:
    mov     rax, rbx
    pop     rbx
    ret

_pyfasm_str_concat:
    ; RCX = str1, RDX = str2
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     rbx, rdx

    ; Calculate len(str1)
    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     [rsp + 32], rax                ; len1

    ; Calculate len(str2)
    mov     rcx, rbx
    call    _pyfasm_str_len
    mov     r8, rax                        ; len2

    ; Allocate len1 + len2 + 1 bytes
    mov     rax, [rsp + 32]
    add     rax, r8
    inc     rax                            ; +1 for null terminator
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax                       ; rdi = new buffer
    mov     [rsp + 40], rax                ; save return pointer

    test    rsi, rsi
    jz      .copy_s2_init
.copy_s1:
    mov     al, [rsi]
    test    al, al
    jz      .copy_s2_init
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .copy_s1

.copy_s2_init:
    test    rbx, rbx
    jz      .concat_null_term
.copy_s2:
    mov     al, [rbx]
    mov     [rdi], al
    test    al, al
    jz      .concat_done
    inc     rbx
    inc     rdi
    jmp     .copy_s2

.concat_null_term:
    mov     byte [rdi], 0
.concat_done:
    mov     rax, [rsp + 40]
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_join:
    ; RCX = sep_str, RDX = seq_ptr
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
    mov     rsi, rcx
    mov     rbx, rdx
    test    rbx, rbx
    jz      .join_empty
    mov     r12, [rbx]
    test    r12, r12
    jle     .join_empty

    mov     rcx, [rbx + 8]
    call    _pyfasm_auto_to_str
    mov     r15, rax
    mov     r13, 1
.join_loop:
    cmp     r13, r12
    jge     .join_done
    mov     rcx, r15
    mov     rdx, rsi
    call    _pyfasm_str_concat
    mov     r15, rax
    mov     rcx, [rbx + r13 * 8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .join_loop

.join_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    mov     r15, rax
.join_done:
    mov     rax, r15
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

_pyfasm_str_removeprefix:
    ; RCX = str, RDX = prefix
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    call    _pyfasm_str_startswith
    test    eax, eax
    jz      .rmp_ret_orig
    mov     rcx, rsi
    call    _pyfasm_str_len
    add     rbx, rax
.rmp_ret_orig:
    mov     rax, rbx
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_removesuffix:
    ; RCX = str, RDX = suffix
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    call    _pyfasm_str_endswith
    test    eax, eax
    jz      .rms_ret_orig
    mov     rcx, rbx
    call    _pyfasm_str_len
    mov     rdi, rax
    mov     rcx, rsi
    call    _pyfasm_str_len
    sub     rdi, rax
    lea     rcx, [rdi + 1]
    call    _pyfasm_alloc
    mov     rsi, rax
    mov     rcx, rdi
    mov     rdx, rbx
.rms_copy:
    test    rcx, rcx
    jz      .rms_done
    mov     al, [rdx]
    mov     [rsi], al
    inc     rdx
    inc     rsi
    dec     rcx
    jmp     .rms_copy
.rms_done:
    mov     byte [rsi], 0
    sub     rsi, rdi
    mov     rax, rsi
    jmp     .rms_ret
.rms_ret_orig:
    mov     rax, rbx
.rms_ret:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_replace:
    ; RCX = target, RDX = old_str, R8 = new_str
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
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
    test    rbx, rbx
    jz      .srep_ret_empty
    test    rsi, rsi
    jz      .srep_ret_orig

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     r12, rax
    test    r12, r12
    jz      .srep_ret_orig

    mov     rcx, rdi
    call    _pyfasm_str_len
    mov     r13, rax

    mov     ecx, 65536
    call    _pyfasm_alloc
    mov     r14, rax
    mov     r15, rax

.srep_loop:
    mov     al, [rbx]
    test    al, al
    jz      .srep_finish

    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_str_startswith
    test    eax, eax
    jz      .srep_copy_char

    mov     rcx, r13
    mov     rdx, rdi
.srep_copy_new:
    test    rcx, rcx
    jz      .srep_adv_old
    mov     al, [rdx]
    mov     [r15], al
    inc     rdx
    inc     r15
    dec     rcx
    jmp     .srep_copy_new
.srep_adv_old:
    add     rbx, r12
    jmp     .srep_loop

.srep_copy_char:
    mov     al, [rbx]
    mov     [r15], al
    inc     rbx
    inc     r15
    jmp     .srep_loop

.srep_finish:
    mov     byte [r15], 0
    mov     rax, r14
    jmp     .srep_ret
.srep_ret_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    jmp     .srep_ret
.srep_ret_orig:
    mov     rax, rbx
.srep_ret:
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

_pyfasm_str_cmp:
    ; RCX = key1, RDX = key2
    ; Returns RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .cmp_eq
    test    rcx, rcx
    jz      .cmp_ne
    js      .cmp_ne
    test    rdx, rdx
    jz      .cmp_ne
    js      .cmp_ne
    cmp     rcx, 65536
    jb      .cmp_ne
    cmp     rdx, 65536
    jb      .cmp_ne
.cmp_loop:
    mov     al, [rcx]
    mov     ah, [rdx]
    cmp     al, ah
    jne     .cmp_ne
    test    al, al
    jz      .cmp_eq
    inc     rcx
    inc     rdx
    jmp     .cmp_loop
.cmp_ne:
    xor     eax, eax
    ret
.cmp_eq:
    mov     eax, 1
    ret

_pyfasm_str_contains:
    ; RCX = haystack, RDX = needle
    ; Returns 1 if needle in haystack, 0 otherwise
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx

    mov     rsi, rcx
    mov     rbx, rdx
    test    rbx, rbx
    jz      .sc_found
    cmp     byte [rbx], 0
    jz      .sc_found
    test    rsi, rsi
    jz      .sc_not_found

.sc_outer:
    mov     al, [rsi]
    test    al, al
    jz      .sc_not_found

    mov     rdi, rsi
    mov     rdx, rbx
.sc_inner:
    mov     cl, [rdx]
    test    cl, cl
    jz      .sc_found
    cmp     cl, [rdi]
    jne     .sc_advance
    inc     rdi
    inc     rdx
    jmp     .sc_inner

.sc_advance:
    inc     rsi
    jmp     .sc_outer

.sc_found:
    mov     rax, 1
    jmp     .sc_ret

.sc_not_found:
    xor     rax, rax

.sc_ret:
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_lower:
    ; RCX = string
    ; Returns RAX = new lowercase string in heap
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .lower_empty

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax
    inc     rax
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax

.lower_loop:
    mov     al, [rsi]
    test    al, al
    jz      .lower_done
    cmp     al, 'A'
    jb      .lower_chk_utf8
    cmp     al, 'Z'
    ja      .lower_chk_utf8
    add     al, 32
    jmp     .lower_store
.lower_chk_utf8:
    cmp     al, 0D0h
    jne     .lower_store
    mov     dl, [rsi + 1]
    test    dl, dl
    jz      .lower_store
    cmp     dl, 81h
    jne     .lower_ru_ap
    ; Yo (D0 81) -> yo (D1 91)
    mov     byte [rdi], 0D1h
    mov     byte [rdi + 1], 91h
    add     rsi, 2
    add     rdi, 2
    jmp     .lower_loop
.lower_ru_ap:
    cmp     dl, 90h
    jb      .lower_store
    cmp     dl, 9Fh
    ja      .lower_ru_rya
    ; A..P (D0 90..9F) -> a..p (D0 B0..BF)
    add     dl, 20h
    mov     byte [rdi], 0D0h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .lower_loop
.lower_ru_rya:
    cmp     dl, 0A0h
    jb      .lower_store
    cmp     dl, 0AFh
    ja      .lower_store
    ; R..Ya (D0 A0..AF) -> r..ya (D1 80..8F)
    sub     dl, 20h
    mov     byte [rdi], 0D1h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .lower_loop
.lower_store:
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .lower_loop

.lower_done:
    mov     byte [rdi], 0
    pop     rax
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.lower_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_upper:
    ; RCX = string
    ; Returns RAX = new uppercase string in heap
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .upper_empty

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax
    inc     rax
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax

.upper_loop:
    mov     al, [rsi]
    test    al, al
    jz      .upper_done
    cmp     al, 'a'
    jb      .upper_chk_utf8
    cmp     al, 'z'
    ja      .upper_chk_utf8
    sub     al, 32
    jmp     .upper_store
.upper_chk_utf8:
    cmp     al, 0D0h
    je      .upper_d0
    cmp     al, 0D1h
    je      .upper_d1
    jmp     .upper_store
.upper_d0:
    mov     dl, [rsi + 1]
    test    dl, dl
    jz      .upper_store
    cmp     dl, 0B0h
    jb      .upper_store
    cmp     dl, 0BFh
    ja      .upper_store
    ; a..p (D0 B0..BF) -> A..P (D0 90..9F)
    sub     dl, 20h
    mov     byte [rdi], 0D0h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .upper_loop
.upper_d1:
    mov     dl, [rsi + 1]
    test    dl, dl
    jz      .upper_store
    cmp     dl, 91h
    jne     .upper_d1_rya
    ; yo (D1 91) -> Yo (D0 81)
    mov     byte [rdi], 0D0h
    mov     byte [rdi + 1], 81h
    add     rsi, 2
    add     rdi, 2
    jmp     .upper_loop
.upper_d1_rya:
    cmp     dl, 80h
    jb      .upper_store
    cmp     dl, 8Fh
    ja      .upper_store
    ; r..ya (D1 80..8F) -> R..Ya (D0 A0..AF)
    add     dl, 20h
    mov     byte [rdi], 0D0h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .upper_loop
.upper_store:
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .upper_loop

.upper_done:
    mov     byte [rdi], 0
    pop     rax
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.upper_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_startswith:
    ; RCX = str, RDX = prefix
    ; Returns RAX = 1 if starts with prefix, 0 otherwise
    test    rdx, rdx
    jz      .sw_true
    cmp     byte [rdx], 0
    jz      .sw_true
    test    rcx, rcx
    jz      .sw_false
.sw_loop:
    mov     al, [rdx]
    test    al, al
    jz      .sw_true
    cmp     al, [rcx]
    jne     .sw_false
    inc     rcx
    inc     rdx
    jmp     .sw_loop
.sw_true:
    mov     eax, 1
    ret
.sw_false:
    xor     eax, eax
    ret

_pyfasm_str_endswith:
    ; RCX = str, RDX = suffix
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    mov     rdi, rdx
    test    rdi, rdi
    jz      .ew_true
    cmp     byte [rdi], 0
    jz      .ew_true
    test    rsi, rsi
    jz      .ew_false

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax

    mov     rcx, rdi
    call    _pyfasm_str_len

    cmp     rbx, rax
    jl      .ew_false

    sub     rbx, rax
    add     rsi, rbx

    mov     rcx, rsi
    mov     rdx, rdi
    call    _pyfasm_str_cmp
    jmp     .ew_ret

.ew_true:
    mov     eax, 1
    jmp     .ew_ret

.ew_false:
    xor     eax, eax

.ew_ret:
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_strip:
    ; RCX = string
    ; Returns RAX = trimmed string in heap
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .strip_empty

.strip_leading:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .strip_empty
    cmp     al, 32
    ja      .strip_leading_done
    inc     rsi
    jmp     .strip_leading
.strip_leading_done:

    mov     rdi, rsi
.strip_find_end:
    cmp     byte [rdi], 0
    jz      .strip_found_end
    inc     rdi
    jmp     .strip_find_end
.strip_found_end:
    dec     rdi

.strip_trailing:
    cmp     rdi, rsi
    jb      .strip_empty
    movzx   eax, byte [rdi]
    cmp     al, 32
    ja      .strip_trailing_done
    dec     rdi
    jmp     .strip_trailing
.strip_trailing_done:

    mov     rbx, rdi
    sub     rbx, rsi
    inc     rbx

    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax

    mov     rcx, rbx
    rep     movsb
    mov     byte [rdi], 0

    pop     rax
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.strip_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_dict_create:
    ; RCX = initial capacity (0 = default 256; rounded up to power of 2, min 256)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rax, 256
    test    rcx, rcx
    jle     .cap_ok
    cmp     rcx, rax
    jbe     .cap_ok
.cap_pow2_loop:
    cmp     rax, 1048576
    jae     .cap_ok
    shl     rax, 1
    cmp     rax, rcx
    jb      .cap_pow2_loop
.cap_ok:
    mov     rbx, rax
    lea     rax, [rbx + rbx * 2]
    shl     rax, 3
    add     rax, 16
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], rbx
    mov     qword [rax + 8], 0
    lea     rdi, [rax + 16]
    lea     rcx, [rbx + rbx * 2]
    mov     rdx, rax
    xor     eax, eax
    rep     stosq
    mov     rax, rdx
    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_hash:
    ; RCX = null-terminated string or 64-bit integer
    ; Returns RAX = 64-bit FNV-1a hash (never 0 or -1)
    test    rcx, rcx
    jz      .hash_zero
    js      .hash_int
    cmp     rcx, 65536
    jb      .hash_int
    mov     rax, 0CBF29CE484222325h
    mov     rdx, 100000001B3h
.hash_loop:
    movzx   r8d, byte [rcx]
    test    r8b, r8b
    jz      .hash_done
    xor     rax, r8
    imul    rax, rdx
    inc     rcx
    jmp     .hash_loop
.hash_zero:
    mov     rax, 0CBF29CE484222325h
    ret
.hash_int:
    mov     rax, rcx
    mov     rdx, 100000001B3h
    imul    rax, rdx
    test    rax, rax
    jz      .hash_one
    cmp     rax, -1
    je      .hash_one
    ret
.hash_done:
    test    rax, rax
    jz      .hash_one
    cmp     rax, -1
    je      .hash_one
    ret
.hash_one:
    mov     rax, 1
    ret

_pyfasm_dict_set:
    ; RCX = dict_ptr, RDX = key_str, R8 = val
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dict_set_done
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    test    r14, r14
    jz      .dict_set_done
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
    mov     qword [rsp + 40], 0
.dict_probe:
    cmp     r11, [rbx]
    jge     .dict_use_tombstone_or_done

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dict_slot_empty

    cmp     rax, -1
    je      .dict_slot_tombstone

    cmp     rax, r13
    jne     .dict_next_slot

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dict_update_val

.dict_next_slot:
    inc     rdi
    and     rdi, r14
    inc     r11
    jmp     .dict_probe

.dict_slot_tombstone:
    cmp     qword [rsp + 40], 0
    jne     .dict_next_slot
    mov     [rsp + 40], rcx
    jmp     .dict_next_slot

.dict_use_tombstone_or_done:
    mov     rcx, [rsp + 40]
    test    rcx, rcx
    jz      .dict_set_done
    jmp     .dict_insert_at_rcx

.dict_slot_empty:
    mov     rax, [rsp + 40]
    test    rax, rax
    jz      .dict_insert_at_rcx
    mov     rcx, rax

.dict_insert_at_rcx:
    mov     [rcx], r13
    mov     [rcx + 8], rsi
    mov     [rcx + 16], r12
    inc     qword [rbx + 8]
    jmp     .dict_set_done

.dict_update_val:
    mov     [rcx + 16], r12

.dict_set_done:
    mov     rax, rbx
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

_pyfasm_dict_get:
    ; RCX = dict_ptr, RDX = key_str, R8 = default_val
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
    test    rcx, rcx
    jz      .dict_get_default
    mov     rbx, rcx
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    test    r14, r14
    jz      .dict_get_default
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
.dict_get_probe:
    cmp     r11, [rbx]
    jge     .dict_get_default

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dict_get_default

    cmp     rax, r13
    jne     .dict_get_next

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dict_get_found

.dict_get_next:
    inc     rdi
    and     rdi, r14
    inc     r11
    jmp     .dict_get_probe

.dict_get_found:
    mov     rax, [rcx + 16]
    jmp     .dict_get_ret

.dict_get_default:
    mov     rax, r12

.dict_get_ret:
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

; ============================================================
; Dictionary Tuple Key Support (FNV-1a tuple hashing & comparison)
; ============================================================
_pyfasm_tuple_hash:
    ; RCX = pointer to tuple [num_elts, elt0, elt1, ...]
    ; Returns RAX = 64-bit FNV-1a hash
    push    rbx
    push    rsi
    test    rcx, rcx
    jz      .th_zero
    mov     rsi, rcx
    mov     rbx, [rsi]             ; num_elts
    test    rbx, rbx
    jz      .th_zero
    mov     rax, 0CBF29CE484222325h
    mov     r10, 100000001B3h
.th_loop:
    add     rsi, 8
    mov     r8, [rsi]              ; current element
    xor     rax, r8
    imul    rax, r10
    dec     rbx
    jnz     .th_loop
    test    rax, rax
    jz      .th_one
    cmp     rax, -1
    jne     .th_ret
.th_one:
    mov     rax, 1
.th_ret:
    pop     rsi
    pop     rbx
    ret
.th_zero:
    mov     rax, 0CBF29CE484222325h
    pop     rsi
    pop     rbx
    ret

_pyfasm_tuple_cmp:
    ; RCX = tuple1, RDX = tuple2
    ; Returns RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .tc_eq
    test    rcx, rcx
    jz      .tc_ne
    test    rdx, rdx
    jz      .tc_ne
    mov     r8, [rcx]              ; len1
    cmp     r8, [rdx]              ; len2
    jne     .tc_ne
    test    r8, r8
    jz      .tc_eq
.tc_loop:
    add     rcx, 8
    add     rdx, 8
    mov     rax, [rcx]
    cmp     rax, [rdx]
    jne     .tc_ne
    dec     r8
    jnz     .tc_loop
.tc_eq:
    mov     eax, 1
    ret
.tc_ne:
    xor     eax, eax
    ret

_pyfasm_dict_set_tuple:
    ; RCX = dict_ptr, RDX = tuple_key_ptr, R8 = val
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dst_done
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_tuple_hash
    mov     r13, rax

    mov     r14, [rbx]             ; capacity
    test    r14, r14
    jz      .dst_done
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
    mov     qword [rsp + 40], 0
.dst_probe:
    cmp     r11, [rbx]
    jge     .dst_use_tombstone_or_done

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]             ; slot hash
    test    rax, rax
    jz      .dst_slot_empty

    cmp     rax, -1
    je      .dst_slot_tombstone

    cmp     rax, r13
    jne     .dst_next_slot

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]         ; existing tuple in slot
    mov     rdx, rsi               ; target tuple
    call    _pyfasm_tuple_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dst_update_val

.dst_next_slot:
    inc     rdi
    and     rdi, r14
    inc     r11
    jmp     .dst_probe

.dst_slot_tombstone:
    cmp     qword [rsp + 40], 0
    jne     .dst_next_slot
    mov     [rsp + 40], rcx
    jmp     .dst_next_slot

.dst_use_tombstone_or_done:
    mov     rcx, [rsp + 40]
    test    rcx, rcx
    jz      .dst_done
    jmp     .dst_insert_at_rcx

.dst_slot_empty:
    mov     rax, [rsp + 40]
    test    rax, rax
    jz      .dst_insert_at_rcx
    mov     rcx, rax

.dst_insert_at_rcx:
    mov     [rcx], r13
    mov     [rcx + 8], rsi
    mov     [rcx + 16], r12
    inc     qword [rbx + 8]
    jmp     .dst_done

.dst_update_val:
    mov     [rcx + 16], r12

.dst_done:
    mov     rax, rbx
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

_pyfasm_dict_get_tuple:
    ; RCX = dict_ptr, RDX = tuple_key_ptr, R8 = default_val
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
    test    rcx, rcx
    jz      .dgt_default
    mov     rbx, rcx
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_tuple_hash
    mov     r13, rax

    mov     r14, [rbx]             ; capacity
    test    r14, r14
    jz      .dgt_default
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11               ; probe counter
.dgt_probe:
    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dgt_default

    cmp     rax, r13
    jne     .dgt_next_slot

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_tuple_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dgt_found

.dgt_next_slot:
    inc     r11
    cmp     r11, [rbx]
    jge     .dgt_default
    inc     rdi
    and     rdi, r14
    jmp     .dgt_probe

.dgt_found:
    mov     rax, [rcx + 16]
    jmp     .dgt_ret

.dgt_default:
    mov     rax, r12

.dgt_ret:
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

_pyfasm_dict_contains:
    ; RCX = dict_ptr, RDX = key_str
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     r8, -999999999
    call    _pyfasm_dict_get
    cmp     rax, -999999999
    setne   al
    movzx   rax, al
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_dict_len:
    test    rcx, rcx
    jz      .dict_len_zero
    mov     rax, [rcx + 8]
    ret
.dict_len_zero:
    xor     eax, eax
    ret

_pyfasm_dict_remove:
    ; RCX = dict_ptr, RDX = key
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
    test    rcx, rcx
    jz      .rem_done
    mov     rbx, rcx
    mov     rsi, rdx

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
.rem_probe:
    cmp     r11, [rbx]
    jge     .rem_done

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .rem_done

    cmp     rax, r13
    jne     .rem_next

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jz      .rem_next

    ; Found: mark as tombstone (-1)
    mov     qword [rcx], -1
    mov     qword [rcx + 8], 0
    mov     qword [rcx + 16], 0
    dec     qword [rbx + 8]
    mov     eax, 1
    jmp     .rem_ret

.rem_next:
    inc     r11
    inc     rdi
    and     rdi, r14
    jmp     .rem_probe

.rem_done:
    xor     eax, eax
.rem_ret:
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

_pyfasm_dict_values:
    ; RCX = dict_ptr -> returns RAX = list of values
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dval_empty
    mov     rcx, [rbx + 8]
    call    _pyfasm_list_create
    mov     r12, rax
    mov     r13, [rbx]
    xor     r14, r14
.dval_loop:
    cmp     r14, r13
    jge     .dval_done
    lea     rax, [r14 + r14 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .dval_next
    cmp     rax, -1
    je      .dval_next
    mov     rcx, r12
    mov     rdx, [rsi + 16]
    call    _pyfasm_list_append
.dval_next:
    inc     r14
    jmp     .dval_loop
.dval_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     r12, rax
.dval_done:
    mov     rax, r12
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

_pyfasm_dict_keys:
    ; RCX = dict_ptr -> returns RAX = list of keys
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dkey_empty
    mov     rcx, [rbx + 8]
    call    _pyfasm_list_create
    mov     r12, rax
    mov     r13, [rbx]
    xor     r14, r14
.dkey_loop:
    cmp     r14, r13
    jge     .dkey_done
    lea     rax, [r14 + r14 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .dkey_next
    cmp     rax, -1
    je      .dkey_next
    mov     rcx, r12
    mov     rdx, [rsi + 8]
    call    _pyfasm_list_append
.dkey_next:
    inc     r14
    jmp     .dkey_loop
.dkey_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     r12, rax
.dkey_done:
    mov     rax, r12
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

_pyfasm_dict_items:
    ; RCX = dict_ptr -> returns RAX = list of (key, val) pairs
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .ditem_empty
    mov     rcx, [rbx + 8]
    call    _pyfasm_list_create
    mov     r12, rax
    mov     r13, [rbx]
    xor     r14, r14
.ditem_loop:
    cmp     r14, r13
    jge     .ditem_done
    lea     rax, [r14 + r14 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .ditem_next
    cmp     rax, -1
    je      .ditem_next
    mov     ecx, 2
    call    _pyfasm_list_create
    mov     rdi, rax
    mov     rcx, rdi
    mov     rdx, [rsi + 8]
    call    _pyfasm_list_append
    mov     rcx, rdi
    mov     rdx, [rsi + 16]
    call    _pyfasm_list_append
    mov     rcx, r12
    mov     rdx, rdi
    call    _pyfasm_list_append
.ditem_next:
    inc     r14
    jmp     .ditem_loop
.ditem_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     r12, rax
.ditem_done:
    mov     rax, r12
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

_pyfasm_set_create:
    jmp     _pyfasm_dict_create

_pyfasm_set_add:
    mov     r8, 1
    jmp     _pyfasm_dict_set

_pyfasm_set_contains:
    jmp     _pyfasm_dict_contains

_pyfasm_set_remove:
    jmp     _pyfasm_dict_remove

_pyfasm_set_len:
    jmp     _pyfasm_dict_len

_pyfasm_str_count:
    ; RCX = str (haystack), RDX = sub (needle, can be string pointer or single char)
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
    xor     r14, r14            ; count = 0
    test    rcx, rcx
    jz      .sc_done
    test    rdx, rdx
    jz      .sc_done
    mov     rsi, rcx            ; rsi = haystack
    mov     rdi, rdx            ; rdi = needle

    ; Check if needle is a pointer (>= 65536) or single char (< 65536)
    cmp     rdi, 65536
    jae     .sc_needle_is_str

    ; Needle is single char byte
    movzx   ebx, dil
    test    bl, bl
    jz      .sc_done
.sc_char_loop:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .sc_done
    cmp     al, bl
    jne     .sc_char_next
    inc     r14
.sc_char_next:
    inc     rsi
    jmp     .sc_char_loop

.sc_needle_is_str:
    ; Needle is a string pointer
    mov     rcx, rdi
    sub     rsp, 32
    call    _pyfasm_str_len
    add     rsp, 32
    mov     r12, rax            ; r12 = needle len
    test    r12, r12
    jz      .sc_done

    ; If needle len is 1, optimize to char loop
    cmp     r12, 1
    jne     .sc_str_loop
    movzx   ebx, byte [rdi]
    jmp     .sc_char_loop

.sc_str_loop:
    ; Needle len >= 2
    movzx   eax, byte [rsi]
    test    al, al
    jz      .sc_done
    ; Check if haystack[0..r12-1] matches needle[0..r12-1]
    xor     rcx, rcx
.sc_match_loop:
    cmp     rcx, r12
    jge     .sc_matched
    mov     al, [rsi + rcx]
    test    al, al
    jz      .sc_done            ; reached end of haystack
    cmp     al, [rdi + rcx]
    jne     .sc_no_match
    inc     rcx
    jmp     .sc_match_loop

.sc_matched:
    inc     r14
    add     rsi, r12            ; advance past non-overlapping match
    jmp     .sc_str_loop

.sc_no_match:
    inc     rsi
    jmp     .sc_str_loop

.sc_done:
    mov     rax, r14
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

_pyfasm_list_count:
    ; RCX = list_ptr, RDX = item
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16
    xor     r13, r13            ; count = 0
    test    rcx, rcx
    jz      .lc_done
    mov     rbx, rcx            ; list
    mov     rsi, rdx            ; item
    mov     rdi, [rbx]          ; length
    xor     r12, r12            ; index = 0
.lc_loop:
    cmp     r12, rdi
    jge     .lc_done
    mov     rax, [rbx + r12 * 8 + 8]
    cmp     rax, rsi
    je      .lc_inc
    ; If both are >= 65536, try str_cmp
    cmp     rsi, 65536
    jb      .lc_next
    cmp     rax, 65536
    jb      .lc_next
    mov     rcx, rax
    mov     rdx, rsi
    sub     rsp, 32
    call    _pyfasm_str_cmp
    add     rsp, 32
    test    eax, eax
    jz      .lc_next
.lc_inc:
    inc     r13
.lc_next:
    inc     r12
    jmp     .lc_loop
.lc_done:
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

_pyfasm_set_from_str:
    ; RCX = null-terminated string
    ; Returns RAX = list_ptr of unique 1-character strings
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 320            ; 256 bytes for visited table + 32 shadow space + alignment
    and     rsp, -16

    test    rcx, rcx
    jz      .sfs_empty

    mov     rsi, rcx            ; rsi = string ptr

    ; Zero-out 256-byte visited array on stack
    lea     rdi, [rsp + 32]
    mov     ecx, 32             ; 32 * 8 = 256 bytes
    xor     eax, eax
    rep stosq

    ; Allocate list for up to 256 elements: 256 * 8 + 16 = 2064 bytes
    mov     ecx, 2064
    sub     rsp, 32
    call    _pyfasm_alloc
    add     rsp, 32
    mov     rbx, rax            ; rbx = list_ptr
    mov     qword [rbx], 0      ; length = 0

.sfs_loop:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .sfs_done

    lea     rdi, [rsp + 32]
    cmp     byte [rdi + rax], 0
    jne     .sfs_next

    ; Mark as visited
    mov     byte [rdi + rax], 1

    ; Allocate 16-byte memory for 1-character string: [char, 0]
    mov     r14, rax
    mov     ecx, 16
    sub     rsp, 32
    call    _pyfasm_alloc
    add     rsp, 32
    mov     byte [rax], r14b
    mov     byte [rax + 1], 0

    ; Append to list
    mov     rcx, rbx            ; list
    mov     rdx, rax            ; item (1-char string)
    sub     rsp, 32
    call    _pyfasm_list_append
    add     rsp, 32

.sfs_next:
    inc     rsi
    jmp     .sfs_loop

.sfs_done:
    mov     rax, rbx
    jmp     .sfs_ret

.sfs_empty:
    mov     ecx, 16
    sub     rsp, 32
    call    _pyfasm_list_create
    add     rsp, 32
.sfs_ret:
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

_pyfasm_set_from_list:
    ; RCX = list_ptr [len, elt0, elt1, ...]
    ; Returns RAX = new list_ptr with unique elements
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .sfl_empty

    mov     rbx, rcx            ; rbx = source list
    mov     r12, [rbx]          ; length
    test    r12, r12
    jz      .sfl_empty

    ; Allocate new list
    lea     rcx, [r12 * 8 + 16]
    sub     rsp, 32
    call    _pyfasm_alloc
    add     rsp, 32
    mov     rdi, rax            ; rdi = new unique list
    mov     qword [rdi], 0      ; length = 0

    xor     r13, r13            ; src idx = 0
.sfl_loop:
    cmp     r13, r12
    jge     .sfl_done
    mov     rdx, [rbx + r13 * 8 + 8] ; candidate item
    mov     rcx, rdi            ; new list
    sub     rsp, 32
    call    _pyfasm_list_contains
    add     rsp, 32
    test    eax, eax
    jnz     .sfl_next           ; already in unique list

    ; Append to new list
    mov     rcx, rdi
    mov     rdx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    _pyfasm_list_append
    add     rsp, 32
.sfl_next:
    inc     r13
    jmp     .sfl_loop

.sfl_done:
    mov     rax, rdi
    jmp     .sfl_ret

.sfl_empty:
    mov     ecx, 16
    sub     rsp, 32
    call    _pyfasm_list_create
    add     rsp, 32
.sfl_ret:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_from_iterable:
    ; RCX = str or list
    test    rcx, rcx
    jz      .sfi_empty
    cmp     qword [rcx], 1000000
    ja      _pyfasm_set_from_str
    cmp     byte [rcx], 0
    je      .sfi_empty
    movzx   eax, byte [rcx]
    cmp     al, 32
    jb      _pyfasm_set_from_list
    cmp     al, 126
    ja      _pyfasm_set_from_list
    movzx   edx, byte [rcx + 1]
    test    dl, dl
    jz      _pyfasm_set_from_str
    cmp     dl, 32
    jb      _pyfasm_set_from_list
    cmp     dl, 126
    ja      _pyfasm_set_from_list
    jmp     _pyfasm_set_from_str

.sfi_empty:
    mov     ecx, 16
    jmp     _pyfasm_list_create

_pyfasm_list_contains:
    ; RCX = list_ptr, RDX = item
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .plc_not_found
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, [rbx]
    test    rdi, rdi
    jz      .plc_not_found
    xor     r12, r12
.plc_loop:
    cmp     r12, rdi
    jge     .plc_not_found
    mov     rax, [rbx + r12 * 8 + 8]
    cmp     rax, rsi
    je      .plc_found
    cmp     rsi, 65536
    jb      .plc_next
    cmp     rax, 65536
    jb      .plc_next
    mov     rcx, rax
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    test    eax, eax
    jnz     .plc_found
.plc_next:
    inc     r12
    jmp     .plc_loop
.plc_found:
    mov     eax, 1
    jmp     .plc_ret
.plc_not_found:
    xor     eax, eax
.plc_ret:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret


_pyfasm_random_choice:
    ; RCX = list pointer
    push    rbp
    mov     rbp, rsp
    test    rcx, rcx
    jz      .rc_null
    mov     r8, [rcx]
    test    r8, r8
    jz      .rc_null
    push    rcx
    rdtsc
    pop     rcx
    xor     edx, edx
    div     r8d
    mov     rax, [rcx + rdx * 8 + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.rc_null:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_pop:
    ; RCX = list_ptr
    test    rcx, rcx
    jz      .lp_empty
    mov     rdx, [rcx]
    test    rdx, rdx
    jz      .lp_empty
    mov     rax, [rcx + rdx * 8]
    dec     qword [rcx]
    ret
.lp_empty:
    xor     eax, eax
    ret

_pyfasm_map:
    ; RCX = seq_ptr, RDX = func_ptr
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
    test    rcx, rcx
    jz      .map_empty
    test    rdx, rdx
    jz      .map_empty
    mov     rbx, rcx     ; seq_ptr
    mov     rsi, rdx     ; func_ptr
    mov     r12, [rbx]   ; length
    lea     rcx, [r12 * 8 + 16]
    call    _pyfasm_alloc
    mov     rdi, rax     ; new list
    mov     [rdi], r12   ; new list length
    xor     r13, r13     ; idx = 0
.map_loop:
    cmp     r13, r12
    jge     .map_done
    mov     rax, 505946434C4F5355h
    cmp     qword [rsi], rax
    jne     .map_plain_call
    mov     rcx, rsi
    mov     rdx, [rbx + r13 * 8 + 8]
    mov     rax, [rsi + 8]
    sub     rsp, 32
    call    rax
    add     rsp, 32
    jmp     .map_store_elt
.map_plain_call:
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
.map_store_elt:
    mov     [rdi + r13 * 8 + 8], rax
    inc     r13
    jmp     .map_loop
.map_done:
    mov     rax, rdi
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
.map_empty:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
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

_pyfasm_filter:
    ; RCX = seq_ptr, RDX = func_ptr
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
    test    rcx, rcx
    jz      .filt_empty
    test    rdx, rdx
    jz      .filt_empty
    mov     rbx, rcx     ; seq_ptr
    mov     rsi, rdx     ; func_ptr
    mov     r12, [rbx]   ; length
    lea     rcx, [r12 * 8 + 16]
    call    _pyfasm_alloc
    mov     rdi, rax     ; new list
    xor     r13, r13     ; in_idx = 0
    xor     r14, r14     ; out_idx = 0
.filt_loop:
    cmp     r13, r12
    jge     .filt_done
    mov     rax, 505946434C4F5355h
    cmp     qword [rsi], rax
    jne     .filt_plain_call
    mov     rcx, rsi
    mov     rdx, [rbx + r13 * 8 + 8]
    mov     rax, [rsi + 8]
    sub     rsp, 32
    call    rax
    add     rsp, 32
    jmp     .filt_chk_res
.filt_plain_call:
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
.filt_chk_res:
    test    rax, rax
    jz      .filt_skip
    mov     rax, [rbx + r13 * 8 + 8]
    mov     [rdi + r14 * 8 + 8], rax
    inc     r14
.filt_skip:
    inc     r13
    jmp     .filt_loop
.filt_done:
    mov     [rdi], r14   ; stored filtered length
    mov     rax, rdi
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
.filt_empty:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
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

_pyfasm_gen_next:
    ; RCX = gen_ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    test    rcx, rcx
    jz      .gn_empty
    mov     rbx, rcx
    cmp     qword [rbx + 16], 1   ; done?
    je      .gn_empty
    mov     rax, [rbx + 8]        ; step function pointer
    mov     rcx, rbx
    call    rax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.gn_empty:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_create:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    test    ecx, ecx
    jnz     .plc_cap
    mov     ecx, 256
.plc_cap:
    shl     ecx, 3
    add     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_append:
    test    rcx, rcx
    jz      .la_ret
    mov     rax, [rcx]
    mov     [rcx + rax * 8 + 8], rdx
    inc     qword [rcx]
.la_ret:
    mov     rax, rcx
    ret

_pyfasm_list_extend:
    ; RCX = dest list pointer, RDX = src iterable/list pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    test    rcx, rcx
    jz      .le_ret
    test    rdx, rdx
    jz      .le_ret
    cmp     rdx, 65536
    jb      .le_ret
    mov     rsi, rcx
    mov     rdi, rdx
    mov     rbx, [rdi]              ; src len
    test    rbx, rbx
    jle     .le_ret
    xor     ecx, ecx                ; i = 0
.le_loop:
    cmp     rcx, rbx
    jge     .le_ret
    mov     rdx, [rdi + rcx * 8 + 8]
    mov     rax, [rsi]
    mov     [rsi + rax * 8 + 8], rdx
    inc     qword [rsi]
    inc     rcx
    jmp     .le_loop
.le_ret:
    mov     rax, rsi
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_insert:
    ; RCX = list pointer
    ; RDX = insertion index (signed 64-bit int)
    ; R8  = value to insert
    test    rcx, rcx
    jz      .pli_ret
    mov     rax, [rcx]              ; current length
    ; Clamp index: if rdx < 0: rdx = max(0, rdx + rax)
    test    rdx, rdx
    jge     .pli_check_high
    add     rdx, rax
    test    rdx, rdx
    jge     .pli_shift_prep
    xor     edx, edx
    jmp     .pli_shift_prep
.pli_check_high:
    cmp     rdx, rax
    jle     .pli_shift_prep
    mov     rdx, rax                ; clamp to current length
.pli_shift_prep:
    mov     r11, rax                ; r11 = current length
.pli_shift_loop:
    cmp     r11, rdx
    jle     .pli_do_insert
    mov     r10, [rcx + r11 * 8]    ; element at index r11 - 1
    mov     [rcx + (r11 + 1) * 8], r10 ; shift right by 1 slot
    dec     r11
    jmp     .pli_shift_loop
.pli_do_insert:
    mov     [rcx + (rdx + 1) * 8], r8
    inc     qword [rcx]             ; length++
.pli_ret:
    xor     eax, eax                ; list.insert returns None
    ret

bisect:
bisect_right:
_pyfasm_bisect:
_pyfasm_bisect_right:
    ; RCX = list pointer
    ; RDX = target value x
    test    rcx, rcx
    jnz     .bsr_start
    xor     eax, eax
    ret
.bsr_start:
    mov     r9, [rcx]               ; hi = len(arr)
.bsr_loop:
    cmp     r8, r9
    jge     .bsr_done
    mov     rax, r8
    add     rax, r9
    sar     rax, 1                  ; mid = (lo + hi) / 2
    mov     r10, [rcx + rax * 8 + 8] ; arr[mid]
    cmp     rdx, r10
    jl      .bsr_hi                 ; if x < arr[mid]: hi = mid
    lea     r8, [rax + 1]           ; else: lo = mid + 1
    jmp     .bsr_loop
.bsr_hi:
    mov     r9, rax
    jmp     .bsr_loop
.bsr_done:
    mov     rax, r8                 ; return lo
    ret

bisect_left:
_pyfasm_bisect_left:
    ; RCX = list pointer
    ; RDX = target value x
    test    rcx, rcx
    jnz     .bsl_start
    xor     eax, eax
    ret
.bsl_start:
    mov     r9, [rcx]               ; hi = len(arr)
.bsl_loop:
    cmp     r8, r9
    jge     .bsl_done
    mov     rax, r8
    add     rax, r9
    sar     rax, 1                  ; mid = (lo + hi) / 2
    mov     r10, [rcx + rax * 8 + 8] ; arr[mid]
    cmp     r10, rdx
    jl      .bsl_lo                 ; if arr[mid] < x: lo = mid + 1
    mov     r9, rax                 ; else: hi = mid
    jmp     .bsl_loop
.bsl_lo:
    lea     r8, [rax + 1]
    jmp     .bsl_loop
.bsl_done:
    mov     rax, r8                 ; return lo
    ret

_pyfasm_str_to_char_list:
    ; RCX = string pointer -> RAX = list of 1-character string pointers
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16
    mov     r12, rcx
    test    r12, r12
    jz      .s2l_empty
    mov     rcx, r12
    call    _pyfasm_str_len
    mov     r13, rax                ; r13 = length in bytes
    mov     rcx, r13
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = list pointer
    test    r13, r13
    jz      .s2l_done
    xor     r14, r14
.s2l_loop:
    cmp     r14, r13
    jge     .s2l_done
    movzx   eax, byte [r12 + r14]
    mov     r15d, 1                 ; default 1 byte
    cmp     al, 0C0h
    jb      .s2l_got_len
    cmp     al, 0E0h
    jb      .s2l_len2
    cmp     al, 0F0h
    jb      .s2l_len3
    mov     r15d, 4
    jmp     .s2l_got_len
.s2l_len2:
    mov     r15d, 2
    jmp     .s2l_got_len
.s2l_len3:
    mov     r15d, 3
.s2l_got_len:
    mov     ecx, 16
    call    _pyfasm_alloc
    lea     rsi, [r12 + r14]
    xor     ecx, ecx
.s2l_copy:
    cmp     ecx, r15d
    jge     .s2l_copied
    mov     r8b, byte [rsi + rcx]
    mov     byte [rax + rcx], r8b
    inc     ecx
    jmp     .s2l_copy
.s2l_copied:
    mov     byte [rax + rcx], 0     ; null terminator
    add     r14, r15
    mov     rcx, rbx
    mov     rdx, rax
    call    _pyfasm_list_append
    jmp     .s2l_loop
.s2l_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     rbx, rax
.s2l_done:
    mov     rax, rbx
    lea     rsp, [rbp - 48]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

zip:
_pyfasm_zip:
    ; RCX = list a (or str a), RDX = list b (or str b)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16
    mov     r12, rcx                ; r12 = list a
    mov     r13, rdx                ; r13 = list b
    test    r12, r12
    jz      .zip_a_ready
    mov     rcx, r12
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .zip_a_ready
    mov     rcx, r12
    call    _pyfasm_str_to_char_list
    mov     r12, rax
.zip_a_ready:
    test    r13, r13
    jz      .zip_b_ready
    mov     rcx, r13
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .zip_b_ready
    mov     rcx, r13
    call    _pyfasm_str_to_char_list
    mov     r13, rax
.zip_b_ready:
    xor     r14, r14                ; min_len = 0
    test    r12, r12
    jz      .zip_alloc_empty
    test    r13, r13
    jz      .zip_alloc_empty
    mov     rax, [r12]
    mov     rdx, [r13]
    cmp     rax, rdx
    cmovle  r14, rax
    cmovg   r14, rdx
.zip_alloc_empty:
    mov     rcx, r14
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = result list
    mov     [rbx], r14              ; store length
    test    r14, r14
    jz      .zip_ret

    xor     r15, r15                ; i = 0
.zip_loop:
    cmp     r15, r14
    jge     .zip_ret
    ; Allocate 2-tuple: 24 bytes
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     qword [rax], 2          ; tuple len = 2
    mov     rdx, [r12 + r15 * 8 + 8] ; a[i]
    mov     [rax + 8], rdx
    mov     rdx, [r13 + r15 * 8 + 8] ; b[i]
    mov     [rax + 16], rdx
    mov     [rbx + r15 * 8 + 8], rax ; store tuple in result list
    inc     r15
    jmp     .zip_loop

.zip_ret:
    mov     rax, rbx
    lea     rsp, [rbp - 40]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

enumerate:
_pyfasm_enumerate:
    ; RCX = list a (or str a), RDX = start index
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16
    mov     r12, rcx                ; r12 = list a
    mov     r13, rdx                ; r13 = start index
    test    r12, r12
    jz      .enum_ready
    mov     rcx, r12
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .enum_ready
    mov     rcx, r12
    call    _pyfasm_str_to_char_list
    mov     r12, rax
.enum_ready:
    xor     r14, r14                ; len = 0
    test    r12, r12
    jz      .enum_alloc_empty
    mov     r14, [r12]
.enum_alloc_empty:
    mov     rcx, r14
    call    _pyfasm_list_create
    mov     rbx, rax
    mov     [rbx], r14
    test    r14, r14
    jz      .enum_ret

    xor     r15, r15                ; i = 0
.enum_loop:
    cmp     r15, r14
    jge     .enum_ret
    ; Allocate 2-tuple: 24 bytes
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     rdx, r15
    add     rdx, r13                ; i + start
    mov     [rax + 8], rdx
    mov     rdx, [r12 + r15 * 8 + 8] ; item
    mov     [rax + 16], rdx
    mov     [rbx + r15 * 8 + 8], rax
    inc     r15
    jmp     .enum_loop

.enum_ret:
    mov     rax, rbx
    lea     rsp, [rbp - 40]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

heappush:
_pyfasm_heappush:
    ; RCX = heap list pointer, RDX = item
    test    rcx, rcx
    jz      .hp_ret
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    mov     rbx, rcx                ; rbx = heap
    mov     r12, rdx                ; r12 = item
    ; Append item to end
    mov     rcx, rbx
    mov     rdx, r12
    call    _pyfasm_list_append
    ; pos = len - 1
    mov     rax, [rbx]
    dec     rax                     ; rax = pos
.hp_siftup:
    test    rax, rax
    jle     .hp_done                ; while pos > 0
    mov     rdx, rax
    dec     rdx
    sar     rdx, 1                  ; parent = (pos - 1) / 2
    mov     r8, [rbx + rdx * 8 + 8] ; heap[parent]
    mov     r9, [rbx + rax * 8 + 8] ; heap[pos]
    cmp     r9, r8
    jge     .hp_done                ; if heap[pos] >= heap[parent]: done
    ; swap heap[pos] and heap[parent]
    mov     [rbx + rax * 8 + 8], r8
    mov     [rbx + rdx * 8 + 8], r9
    mov     rax, rdx                ; pos = parent
    jmp     .hp_siftup
.hp_done:
    add     rsp, 32
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
.hp_ret:
    xor     eax, eax
    ret

heappop:
_pyfasm_heappop:
    ; RCX = heap list pointer
    test    rcx, rcx
    jnz     .hpo_chk_len
    xor     eax, eax
    ret
.hpo_chk_len:
    mov     rax, [rcx]
    test    rax, rax
    jnz     .hpo_start
    xor     eax, eax
    ret
.hpo_start:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     rbx, rcx                ; rbx = heap
    mov     r12, [rbx + 8]          ; return item = heap[0]
    mov     rax, [rbx]
    dec     rax                     ; last_pos = len - 1
    mov     [rbx], rax              ; len--
    test    rax, rax
    jz      .hpo_done               ; if was 1 item, now 0
    ; move last item to root: heap[0] = heap[last_pos]
    mov     rdx, [rbx + (rax + 1) * 8]
    mov     [rbx + 8], rdx
    xor     r13, r13                ; pos = 0
    mov     r14, rax                ; count = len
.hpo_siftdown:
    mov     rax, r13
    shl     rax, 1
    inc     rax                     ; child = 2 * pos + 1
    cmp     rax, r14
    jge     .hpo_done               ; if child >= count: break
    mov     rdx, rax
    inc     rdx                     ; right = child + 1
    cmp     rdx, r14
    jge     .hpo_cmp_child
    mov     r8, [rbx + rax * 8 + 8] ; heap[child]
    mov     r9, [rbx + rdx * 8 + 8] ; heap[right]
    cmp     r9, r8
    cmovl   rax, rdx                ; if heap[right] < heap[child]: child = right
.hpo_cmp_child:
    mov     r8, [rbx + r13 * 8 + 8] ; heap[pos]
    mov     r9, [rbx + rax * 8 + 8] ; heap[child]
    cmp     r8, r9
    jle     .hpo_done               ; if heap[pos] <= heap[child]: break
    ; swap heap[pos] and heap[child]
    mov     [rbx + r13 * 8 + 8], r9
    mov     [rbx + rax * 8 + 8], r8
    mov     r13, rax                ; pos = child
    jmp     .hpo_siftdown
.hpo_done:
    mov     rax, r12                ; return popped root
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

heapreplace:
_pyfasm_heapreplace:
    ; RCX = heap list pointer, RDX = new item
    test    rcx, rcx
    jnz     .hpr_chk_len
    xor     eax, eax
    ret
.hpr_chk_len:
    mov     rax, [rcx]
    test    rax, rax
    jnz     .hpr_start
    xor     eax, eax
    ret
.hpr_start:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     rbx, rcx                ; rbx = heap
    mov     r12, [rbx + 8]          ; r12 = return old root
    mov     [rbx + 8], rdx          ; heap[0] = new_item
    xor     r13, r13                ; pos = 0
    mov     r14, [rbx]              ; count = len
.hpr_siftdown:
    mov     rax, r13
    shl     rax, 1
    inc     rax                     ; child = 2 * pos + 1
    cmp     rax, r14
    jge     .hpr_done               ; if child >= count: break
    mov     rdx, rax
    inc     rdx                     ; right = child + 1
    cmp     rdx, r14
    jge     .hpr_cmp_child
    mov     r8, [rbx + rax * 8 + 8] ; heap[child]
    mov     r9, [rbx + rdx * 8 + 8] ; heap[right]
    cmp     r9, r8
    cmovl   rax, rdx                ; if heap[right] < heap[child]: child = right
.hpr_cmp_child:
    mov     r8, [rbx + r13 * 8 + 8] ; heap[pos]
    mov     r9, [rbx + rax * 8 + 8] ; heap[child]
    cmp     r8, r9
    jle     .hpr_done               ; if heap[pos] <= heap[child]: break
    ; swap heap[pos] and heap[child]
    mov     [rbx + r13 * 8 + 8], r9
    mov     [rbx + rax * 8 + 8], r8
    mov     r13, rax                ; pos = child
    jmp     .hpr_siftdown
.hpr_done:
    mov     rax, r12                ; return old root
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

heapify:
_pyfasm_heapify:
    ; RCX = heap list pointer
    test    rcx, rcx
    jnz     .hpy_chk_len
    xor     eax, eax
    ret
.hpy_chk_len:
    mov     rax, [rcx]
    cmp     rax, 1
    jle     .hpy_ret_zero           ; if len <= 1: already a heap
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    mov     rbx, rcx                ; rbx = heap
    mov     r14, [rbx]              ; r14 = count = len
    mov     r15, r14
    shr     r15, 1
    dec     r15                     ; r15 = start_pos = (len / 2) - 1
.hpy_loop:
    test    r15, r15
    js      .hpy_done               ; while start_pos >= 0
    mov     r13, r15                ; pos = start_pos
.hpy_siftdown:
    mov     rax, r13
    shl     rax, 1
    inc     rax                     ; child = 2 * pos + 1
    cmp     rax, r14
    jge     .hpy_next               ; if child >= count: next start_pos
    mov     rdx, rax
    inc     rdx                     ; right = child + 1
    cmp     rdx, r14
    jge     .hpy_cmp_child
    mov     r8, [rbx + rax * 8 + 8] ; heap[child]
    mov     r9, [rbx + rdx * 8 + 8] ; heap[right]
    cmp     r9, r8
    cmovl   rax, rdx                ; if heap[right] < heap[child]: child = right
.hpy_cmp_child:
    mov     r8, [rbx + r13 * 8 + 8] ; heap[pos]
    mov     r9, [rbx + rax * 8 + 8] ; heap[child]
    cmp     r8, r9
    jle     .hpy_next               ; if heap[pos] <= heap[child]: next start_pos
    ; swap heap[pos] and heap[child]
    mov     [rbx + r13 * 8 + 8], r9
    mov     [rbx + rax * 8 + 8], r8
    mov     r13, rax                ; pos = child
    jmp     .hpy_siftdown
.hpy_next:
    dec     r15
    jmp     .hpy_loop
.hpy_done:
    add     rsp, 40
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
.hpy_ret_zero:
    xor     eax, eax                ; return None
    ret

sorted:
_pyfasm_sorted:
    ; RCX = list pointer
    test    rcx, rcx
    jnz     .srt_chk
    xor     eax, eax
    ret
.srt_chk:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    mov     rsi, rcx                ; rsi = src list
    mov     r12, [rsi]              ; r12 = len
    ; Allocate new list
    mov     rax, r12
    inc     rax
    shl     rax, 3                  ; (len + 1) * 8
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax                ; rdi = dst list
    mov     [rdi], r12              ; store len
    ; Copy elements
    xor     rcx, rcx
.srt_cp:
    cmp     rcx, r12
    jge     .srt_sort
    mov     rax, [rsi + rcx * 8 + 8]
    mov     [rdi + rcx * 8 + 8], rax
    inc     rcx
    jmp     .srt_cp
.srt_sort:
    cmp     r12, 2
    jl      .srt_done
    mov     rbx, 1                  ; i = 1
.srt_outer:
    cmp     rbx, r12
    jge     .srt_done
    mov     r13, [rdi + rbx * 8 + 8] ; key = dst[i]
    mov     rcx, rbx
    dec     rcx                     ; j = i - 1
.srt_inner:
    test    rcx, rcx
    js      .srt_place
    mov     rax, [rdi + rcx * 8 + 8] ; dst[j]
    mov     r8, rax
    mov     r9, r13
    cmp     r8, 65536
    jb      .srt_cmp_sc
    cmp     r9, 65536
    jb      .srt_cmp_sc
    mov     r10, [r8]
    cmp     r10, 1
    jle     .srt_cmp_1
    mov     r8, [r8 + 16]
    mov     r9, [r9 + 16]
    jmp     .srt_cmp_sc
.srt_cmp_1:
    mov     r8, [r8 + 8]
    mov     r9, [r9 + 8]
.srt_cmp_sc:
    cmp     r8, r9
    jle     .srt_place              ; if dst[j] <= key: break
    mov     [rdi + (rcx + 1) * 8 + 8], rax ; dst[j + 1] = dst[j]
    dec     rcx
    jmp     .srt_inner
.srt_place:
    mov     [rdi + (rcx + 1) * 8 + 8], r13 ; dst[j + 1] = key
    inc     rbx
    jmp     .srt_outer
.srt_done:
    mov     rax, rdi                ; return sorted list pointer
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

sort:
_pyfasm_list_sort:
    ; RCX = list pointer
    test    rcx, rcx
    jnz     .lsrt_start
    xor     eax, eax
    ret
.lsrt_start:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    mov     rdi, rcx
    mov     r12, [rdi]              ; r12 = len
    cmp     r12, 2
    jl      .lsrt_done
    mov     rbx, 1                  ; i = 1
.lsrt_outer:
    cmp     rbx, r12
    jge     .lsrt_done
    mov     r13, [rdi + rbx * 8 + 8] ; key = dst[i]
    mov     rcx, rbx
    dec     rcx                     ; j = i - 1
.lsrt_inner:
    test    rcx, rcx
    js      .lsrt_place
    mov     rax, [rdi + rcx * 8 + 8] ; dst[j]
    mov     r8, rax
    mov     r9, r13
    cmp     r8, 65536
    jb      .lsrt_cmp_sc
    cmp     r9, 65536
    jb      .lsrt_cmp_sc
    mov     r10, [r8]
    cmp     r10, 1
    jle     .lsrt_cmp_1
    mov     r8, [r8 + 16]
    mov     r9, [r9 + 16]
    jmp     .lsrt_cmp_sc
.lsrt_cmp_1:
    mov     r8, [r8 + 8]
    mov     r9, [r9 + 8]
.lsrt_cmp_sc:
    cmp     r8, r9
    jle     .lsrt_place              ; if dst[j] <= key: break
    mov     [rdi + (rcx + 1) * 8 + 8], rax ; dst[j + 1] = dst[j]
    dec     rcx
    jmp     .lsrt_inner
.lsrt_place:
    mov     [rdi + (rcx + 1) * 8 + 8], r13 ; dst[j + 1] = key
    inc     rbx
    jmp     .lsrt_outer
.lsrt_done:
    xor     eax, eax                ; sort() returns None (0)
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_eq:
    ; RCX = list 1, RDX = list 2
    ; Returns: RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .leq_ret1
    test    rcx, rcx
    jz      .leq_ret0
    test    rdx, rdx
    jz      .leq_ret0
    cmp     rcx, 65536
    jb      .leq_ret0
    cmp     rdx, 65536
    jb      .leq_ret0
    mov     rax, [rcx]              ; length of list 1
    cmp     rax, [rdx]              ; length of list 2
    jne     .leq_ret0
    test    rax, rax
    jz      .leq_ret1               ; both empty lists -> equal!
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    mov     rsi, rcx                ; list 1
    mov     rdi, rdx                ; list 2
    mov     r12, [rsi]              ; length
    xor     rbx, rbx                ; index = 0
.leq_elem_loop:
    cmp     rbx, r12
    jge     .leq_all_match
    mov     r13, [rsi + rbx * 8 + 8] ; list1[i]
    mov     r14, [rdi + rbx * 8 + 8] ; list2[i]
    cmp     r13, r14
    jne     .leq_elem_diff
    inc     rbx
    jmp     .leq_elem_loop
.leq_elem_diff:
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
.leq_ret0:
    xor     eax, eax
    ret
.leq_all_match:
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
.leq_ret1:
    mov     eax, 1
    ret

_pyfasm_list2d_eq:
    ; RCX = list 1, RDX = list 2
    ; Returns: RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .l2eq_ret1
    test    rcx, rcx
    jz      .l2eq_ret0
    test    rdx, rdx
    jz      .l2eq_ret0
    cmp     rcx, 65536
    jb      .l2eq_ret0
    cmp     rdx, 65536
    jb      .l2eq_ret0
    mov     rax, [rcx]              ; length of list 1
    cmp     rax, [rdx]              ; length of list 2
    jne     .l2eq_ret0
    test    rax, rax
    jz      .l2eq_ret1              ; both empty lists -> equal!
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 48
    mov     rsi, rcx                ; list 1
    mov     rdi, rdx                ; list 2
    mov     r12, [rsi]              ; length
    xor     rbx, rbx                ; index = 0
.l2eq_loop:
    cmp     rbx, r12
    jge     .l2eq_all_match
    mov     rcx, [rsi + rbx * 8 + 8] ; list1[i]
    mov     rdx, [rdi + rbx * 8 + 8] ; list2[i]
    call    _pyfasm_list_eq
    test    rax, rax
    jz      .l2eq_mismatch
    inc     rbx
    jmp     .l2eq_loop
.l2eq_mismatch:
    xor     eax, eax
    add     rsp, 48
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.l2eq_all_match:
    mov     eax, 1
    add     rsp, 48
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.l2eq_ret0:
    xor     eax, eax
    ret
.l2eq_ret1:
    mov     eax, 1
    ret

_pyfasm_list_repeat:
    ; RCX = list pointer
    ; RDX = count (signed 64-bit int)
    ; Returns: RAX = new list pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40

    mov     rsi, rcx                ; rsi = src_list
    mov     r12, rdx                ; r12 = count
    test    r12, r12
    jle     .lrep_empty
    test    rsi, rsi
    jz      .lrep_empty
    cmp     rsi, 65536
    jb      .lrep_empty

    mov     r13, [rsi]              ; r13 = src_len
    test    r13, r13
    jz      .lrep_empty

    ; total_len = src_len * count
    mov     rax, r13
    imul    rax, r12
    mov     r14, rax                ; r14 = total_len

    ; bytes = total_len * 8 + 16
    lea     rcx, [r14 * 8 + 16]
    call    _pyfasm_alloc
    mov     rdi, rax                ; rdi = new_list
    mov     [rdi], r14              ; store total_len

    ; Copy elements: outer loop = count, inner loop = src_len
    xor     rbx, rbx                ; dest_idx = 0
    xor     r15, r15                ; rep_i = 0
.lrep_outer:
    cmp     r15, r12
    jge     .lrep_done
    xor     r8, r8                  ; elem_j = 0
.lrep_inner:
    cmp     r8, r13
    jge     .lrep_inner_done
    mov     rax, [rsi + r8 * 8 + 8]
    mov     [rdi + rbx * 8 + 8], rax
    inc     rbx
    inc     r8
    jmp     .lrep_inner
.lrep_inner_done:
    inc     r15
    jmp     .lrep_outer

.lrep_empty:
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 0
    mov     rdi, rax

.lrep_done:
    mov     rax, rdi
    add     rsp, 40
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

_pyfasm_list_concat:
    ; RCX = list 1, RDX = list 2
    ; Returns: RAX = new concatenated list
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40

    mov     rsi, rcx                ; list 1
    mov     rdi, rdx                ; list 2
    xor     r12, r12                ; len 1 = 0
    xor     r13, r13                ; len 2 = 0
    test    rsi, rsi
    jz      .lcat_chk2
    cmp     rsi, 65536
    jb      .lcat_chk2
    mov     r12, [rsi]
.lcat_chk2:
    test    rdi, rdi
    jz      .lcat_alloc
    cmp     rdi, 65536
    jb      .lcat_alloc
    mov     r13, [rdi]

.lcat_alloc:
    lea     r14, [r12 + r13]        ; total_len
    lea     rcx, [r14 * 8 + 16]     ; bytes
    call    _pyfasm_alloc
    mov     r15, rax                ; new_list
    mov     [r15], r14              ; store total_len

    ; Copy from list 1
    xor     rbx, rbx
.lcat_cp1:
    cmp     rbx, r12
    jge     .lcat_cp2_start
    mov     rax, [rsi + rbx * 8 + 8]
    mov     [r15 + rbx * 8 + 8], rax
    inc     rbx
    jmp     .lcat_cp1

.lcat_cp2_start:
    xor     rcx, rcx
.lcat_cp2:
    cmp     rcx, r13
    jge     .lcat_done
    mov     rax, [rdi + rcx * 8 + 8]
    mov     [r15 + rbx * 8 + 8], rax
    inc     rbx
    inc     rcx
    jmp     .lcat_cp2

.lcat_done:
    mov     rax, r15
    add     rsp, 40
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

_pyfasm_str_isdigit:
    ; RCX = null-terminated string pointer
    test    rcx, rcx
    jnz     .sdi_chk
    xor     eax, eax
    ret
.sdi_chk:
    movzx   eax, byte [rcx]
    test    al, al
    jnz     .sdi_loop
    xor     eax, eax
    ret
.sdi_loop:
    movzx   eax, byte [rcx]
    test    al, al
    jz      .sdi_true
    cmp     al, '0'
    jl      .sdi_false
    cmp     al, '9'
    jg      .sdi_false
    inc     rcx
    jmp     .sdi_loop
.sdi_true:
    mov     eax, 1
    ret
.sdi_false:
    xor     eax, eax
    ret

_pyfasm_str_isascii:
    ; RCX = null-terminated string pointer
    test    rcx, rcx
    jnz     .sia_loop
    mov     eax, 1
    ret
.sia_loop:
    movzx   eax, byte [rcx]
    test    al, al
    jz      .sia_true
    cmp     al, 127
    ja      .sia_false
    inc     rcx
    jmp     .sia_loop
.sia_true:
    mov     eax, 1
    ret
.sia_false:
    xor     eax, eax
    ret

nanogemm_simd_isa:
get_simd_isa:
_pyfasm_nanogemm_simd_isa:
    lea     rax, [szNanoGemmISA]
    ret

matmul:
nanogemm_matmul:
_pyfasm_nanogemm_matmul:
    ; RCX = A (list pointer or 2D list), RDX = B (list pointer or 2D list)
    test    rcx, rcx
    jnz     .ngm_chk_b
    xor     eax, eax
    ret
.ngm_chk_b:
    test    rdx, rdx
    jnz     .ngm_start
    xor     eax, eax
    ret
.ngm_start:
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
    mov     [rsp + 0], rcx          ; A
    mov     [rsp + 8], rdx          ; B

    mov     rax, [rcx]
    test    rax, rax
    jz      .ngm_empty

    mov     r8, [rcx + 8]           ; A[0]
    mov     r9, [rdx + 8]           ; B[0]
    cmp     r8, 0x10000
    jb      .ngm_1d_dot
    test    r8, 7
    jnz     .ngm_1d_dot
    mov     rax, [r8]
    cmp     rax, 10000000
    ja      .ngm_1d_dot

    ; --- 2D Matrix Multiplication ---
    mov     r12, [rcx]              ; r12 = M
    mov     r13, [r8]               ; r13 = K
    mov     r14, [r9]               ; r14 = N
    mov     [rsp + 16], r12         ; M
    mov     [rsp + 24], r13         ; K
    mov     [rsp + 32], r14         ; N

    mov     rax, r12
    inc     rax
    shl     rax, 3                  ; (M + 1) * 8
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rsp + 40], rax         ; C
    mov     r12, [rsp + 16]
    mov     [rax], r12

    xor     rbx, rbx                ; i = 0
.ngm_2d_row_loop:
    cmp     rbx, [rsp + 16]
    jge     .ngm_2d_done

    mov     rax, [rsp + 32]         ; N
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     r15, rax                ; C[i]
    mov     rax, [rsp + 32]
    mov     [r15], rax

    mov     rax, [rsp + 40]
    mov     [rax + rbx * 8 + 8], r15

    xor     rsi, rsi                ; j = 0
.ngm_2d_col_loop:
    cmp     rsi, [rsp + 32]
    jge     .ngm_2d_row_next

    xor     r11, r11                ; acc = 0
    xor     rdi, rdi                ; k = 0
.ngm_2d_dot_loop:
    cmp     rdi, [rsp + 24]
    jge     .ngm_2d_store_cell

    mov     rax, [rsp + 0]
    mov     rax, [rax + rbx * 8 + 8]
    mov     rax, [rax + rdi * 8 + 8]

    mov     r10, [rsp + 8]
    mov     r10, [r10 + rdi * 8 + 8]
    mov     r10, [r10 + rsi * 8 + 8]

    imul    rax, r10
    add     r11, rax
    inc     rdi
    jmp     .ngm_2d_dot_loop

.ngm_2d_store_cell:
    mov     [r15 + rsi * 8 + 8], r11
    inc     rsi
    jmp     .ngm_2d_col_loop

.ngm_2d_row_next:
    inc     rbx
    jmp     .ngm_2d_row_loop

.ngm_2d_done:
    mov     rax, [rsp + 40]
    jmp     .ngm_epilog

.ngm_1d_dot:
    mov     rcx, [rsp + 0]
    mov     rdx, [rsp + 8]
    mov     r8, [rcx]
    mov     r9, [rdx]
    cmp     r8, r9
    cmovg   r8, r9
    xor     rax, rax
    xor     rcx, rcx
.ngm_1d_loop:
    cmp     rcx, r8
    jge     .ngm_1d_done
    mov     r10, [rsp + 0]
    mov     r10, [r10 + rcx * 8 + 8]
    mov     r11, [rsp + 8]
    mov     r11, [r11 + rcx * 8 + 8]
    imul    r10, r11
    add     rax, r10
    inc     rcx
    jmp     .ngm_1d_loop
.ngm_1d_done:
    jmp     .ngm_epilog

.ngm_empty:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
.ngm_epilog:
    add     rsp, 64
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

_pyfasm_np_zeros:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    test    rdx, rdx
    jnz     .npz_2d
    mov     r12, rcx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r12
    xor     rcx, rcx
.npz_1d_clr:
    cmp     rcx, r12
    jge     .npz_done
    mov     qword [rax + rcx * 8 + 8], 0
    inc     rcx
    jmp     .npz_1d_clr
.npz_2d:
    mov     r12, rcx
    mov     r13, rdx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     [rbx], r12
    xor     rsi, rsi
.npz_2d_loop:
    cmp     rsi, r12
    jge     .npz_2d_ret
    mov     rax, r13
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r13
    xor     rcx, rcx
.npz_row_clr:
    cmp     rcx, r13
    jge     .npz_row_done
    mov     qword [rax + rcx * 8 + 8], 0
    inc     rcx
    jmp     .npz_row_clr
.npz_row_done:
    mov     [rbx + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npz_2d_loop
.npz_2d_ret:
    mov     rax, rbx
.npz_done:
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_ones:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    test    rdx, rdx
    jnz     .npo_2d
    mov     r12, rcx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r12
    mov     rdx, 3FF0000000000000h
    xor     rcx, rcx
.npo_1d_set:
    cmp     rcx, r12
    jge     .npo_done
    mov     [rax + rcx * 8 + 8], rdx
    inc     rcx
    jmp     .npo_1d_set
.npo_2d:
    mov     r12, rcx
    mov     r13, rdx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     [rbx], r12
    xor     rsi, rsi
.npo_2d_loop:
    cmp     rsi, r12
    jge     .npo_2d_ret
    mov     rax, r13
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r13
    mov     rdx, 3FF0000000000000h
    xor     rcx, rcx
.npo_row_set:
    cmp     rcx, r13
    jge     .npo_row_done
    mov     [rax + rcx * 8 + 8], rdx
    inc     rcx
    jmp     .npo_row_set
.npo_row_done:
    mov     [rbx + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npo_2d_loop
.npo_2d_ret:
    mov     rax, rbx
.npo_done:
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

math_gcd:
gcd:
_pyfasm_math_gcd:
    ; RCX = a, RDX = b
    mov     rax, rcx
    test    rax, rax
    jns     .gcd_chk_b
    neg     rax
.gcd_chk_b:
    mov     rcx, rdx
    test    rcx, rcx
    jns     .gcd_loop
    neg     rcx
.gcd_loop:
    test    rcx, rcx
    jz      .gcd_done
    xor     edx, edx
    div     rcx                     ; rax = rax / rcx, rdx = rax % rcx
    mov     rax, rcx                ; a = b
    mov     rcx, rdx                ; b = remainder
    jmp     .gcd_loop
.gcd_done:
    ret

_pyfasm_math_gcd_list:
    ; RCX = list_ptr [len, elt0, elt1, ...]
    ; Returns RAX = GCD of all elements
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .mgl_zero

    mov     rbx, rcx
    mov     rdi, [rbx]          ; length
    test    rdi, rdi
    jz      .mgl_zero

    ; First element
    mov     rax, [rbx + 8]
    test    rax, rax
    jns     .mgl_chk1
    neg     rax
.mgl_chk1:
    mov     r12, 1              ; index = 1
.mgl_loop:
    cmp     r12, rdi
    jge     .mgl_done

    mov     rdx, [rbx + r12 * 8 + 8] ; b = elt[i]
    mov     rcx, rax                 ; a = current gcd
    sub     rsp, 32
    call    _pyfasm_math_gcd         ; rax = gcd(a, b)
    add     rsp, 32
    inc     r12
    jmp     .mgl_loop

.mgl_done:
    jmp     .mgl_ret

.mgl_zero:
    xor     eax, eax
.mgl_ret:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

math_lcm:
lcm:
_pyfasm_math_lcm:
    ; RCX = a, RDX = b
    test    rcx, rcx
    jz      .lcm_zero
    test    rdx, rdx
    jz      .lcm_zero
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    mov     rbx, rcx                ; a
    mov     r12, rdx                ; b
    call    _pyfasm_math_gcd        ; rax = gcd(a, b)
    test    rax, rax
    jz      .lcm_done
    mov     r8, rax                 ; r8 = gcd
    mov     rax, rbx
    imul    rax, r12                ; a * b
    test    rax, rax
    jns     .lcm_div
    neg     rax                     ; abs(a * b)
.lcm_div:
    xor     edx, edx
    div     r8                      ; abs(a * b) / gcd
.lcm_done:
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.lcm_zero:
    xor     eax, eax
    ret

math_isqrt:
isqrt:
_pyfasm_math_isqrt:
    ; RCX = n (non-negative int)
    test    rcx, rcx
    jns     .isqrt_start
    xor     eax, eax
    ret
.isqrt_start:
    test    rcx, rcx
    jnz     .isqrt_non_zero
    xor     eax, eax
    ret
.isqrt_non_zero:
    mov     r8, rcx                 ; r8 = n
    mov     r9, rcx                 ; x = n
.isqrt_loop:
    mov     rax, r8
    xor     edx, edx
    div     r9                      ; rax = n / x
    add     rax, r9                 ; rax = x + n / x
    shr     rax, 1                  ; next_x = (x + n / x) / 2
    cmp     rax, r9
    jge     .isqrt_ret              ; while next_x < x
    mov     r9, rax                 ; x = next_x
    jmp     .isqrt_loop
.isqrt_ret:
    mov     rax, r9
    ret

math_factorial:
factorial:
_pyfasm_math_factorial:
    ; RCX = n
    mov     rax, 1
    test    rcx, rcx
    jle     .fact_done
.fact_loop:
    imul    rax, rcx
    dec     rcx
    jnz     .fact_loop
.fact_done:
    ret

itertools_chain:
chain:
_pyfasm_itertools_chain:
    ; RCX = list a, RDX = list b
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    mov     r12, rcx                ; r12 = list a
    mov     r13, rdx                ; r13 = list b
    xor     r14, r14                ; len_a = 0
    xor     r15, r15                ; len_b = 0
    test    r12, r12
    jz      .chn_chk_b
    mov     r14, [r12]
.chn_chk_b:
    test    r13, r13
    jz      .chn_alloc
    mov     r15, [r13]
.chn_alloc:
    mov     rcx, r14
    add     rcx, r15                ; total len
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = new list
    mov     rax, r14
    add     rax, r15
    mov     [rbx], rax              ; store total len
    xor     rcx, rcx
.chn_loop_a:
    cmp     rcx, r14
    jge     .chn_copy_b
    mov     rdx, [r12 + rcx * 8 + 8]
    mov     [rbx + rcx * 8 + 8], rdx
    inc     rcx
    jmp     .chn_loop_a
.chn_copy_b:
    xor     rdx, rdx
.chn_loop_b:
    cmp     rdx, r15
    jge     .chn_done
    mov     rax, [r13 + rdx * 8 + 8]
    mov     r8, r14
    add     r8, rdx
    mov     [rbx + r8 * 8 + 8], rax
    inc     rdx
    jmp     .chn_loop_b
.chn_done:
    mov     rax, rbx
    add     rsp, 40
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

itertools_accumulate:
accumulate:
_pyfasm_itertools_accumulate:
    ; RCX = list
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     r12, rcx
    xor     r13, r13
    test    r12, r12
    jz      .acc_alloc
    mov     r13, [r12]
.acc_alloc:
    mov     rcx, r13
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = res list
    mov     [rbx], r13
    test    r13, r13
    jz      .acc_done
    xor     r14, r14
    xor     rcx, rcx
.acc_loop:
    cmp     rcx, r13
    jge     .acc_done
    mov     rdx, [r12 + rcx * 8 + 8]
    add     r14, rdx
    mov     [rbx + rcx * 8 + 8], r14
    inc     rcx
    jmp     .acc_loop
.acc_done:
    mov     rax, rbx
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

functools_reduce:
reduce:
_pyfasm_functools_reduce:
    ; RCX = function pointer, RDX = list, R8 = initial, R9 = has_initial
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    mov     r12, rcx                ; r12 = fn
    mov     r13, rdx                ; r13 = list
    xor     r14, r14
    test    r13, r13
    jz      .red_ret_zero
    mov     r14, [r13]
    test    r14, r14
    jz      .red_ret_zero
    test    r9, r9
    jnz     .red_with_init
    mov     r15, [r13 + 8]          ; acc = list[0]
    mov     rbx, 1                  ; start at 1
    jmp     .red_loop
.red_with_init:
    mov     r15, r8                 ; acc = initial
    xor     rbx, rbx
.red_loop:
    cmp     rbx, r14
    jge     .red_done
    mov     rcx, r15                ; arg 0 = acc
    mov     rdx, [r13 + rbx * 8 + 8] ; arg 1 = item
    call    r12
    mov     r15, rax                ; acc = result
    inc     rbx
    jmp     .red_loop
.red_done:
    mov     rax, r15
    jmp     .red_exit
.red_ret_zero:
    xor     eax, eax
.red_exit:
    add     rsp, 40
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

math_sumprod:
sumprod:
_pyfasm_math_sumprod:
    ; RCX = list a, RDX = list b -> RAX = sum(a[i] * b[i])
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    xor     rax, rax
    test    rcx, rcx
    jz      .sp_done
    test    rdx, rdx
    jz      .sp_done
    mov     rsi, rcx
    mov     rdi, rdx
    mov     r12, [rsi]
    mov     r13, [rdi]
    cmp     r12, r13
    cmovg   r12, r13
    test    r12, r12
    jle     .sp_done
    xor     ecx, ecx
.sp_loop:
    cmp     rcx, r12
    jge     .sp_done
    mov     rdx, [rsi + rcx * 8 + 8]
    imul    rdx, [rdi + rcx * 8 + 8]
    add     rax, rdx
    inc     rcx
    jmp     .sp_loop
.sp_done:
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

itertools_batched:
batched:
_pyfasm_itertools_batched:
    ; RCX = list, RDX = batch size n -> RAX = list of batch lists
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
    mov     rsi, rcx
    mov     r12, rdx
    test    rsi, rsi
    jz      .bat_empty
    cmp     r12, 1
    jl      .bat_empty
    mov     r13, [rsi]
    test    r13, r13
    jle     .bat_empty

    mov     rax, r13
    add     rax, r12
    dec     rax
    xor     edx, edx
    div     r12
    mov     r14, rax

    mov     rcx, r14
    call    _pyfasm_list_create
    mov     rbx, rax
    mov     [rbx], r14

    xor     r15, r15
    xor     edi, edi
.bat_outer_loop:
    cmp     r15, r14
    jge     .bat_finish

    mov     rcx, r13
    sub     rcx, rdi
    cmp     rcx, r12
    cmovg   rcx, r12
    mov     [rsp + 32], rcx

    call    _pyfasm_list_create
    mov     r8, rax
    mov     rcx, [rsp + 32]
    mov     [r8], rcx

    xor     edx, edx
.bat_inner_loop:
    cmp     rdx, [rsp + 32]
    jge     .bat_inner_done
    mov     rax, [rsi + rdi * 8 + 8]
    mov     [r8 + rdx * 8 + 8], rax
    inc     rdi
    inc     rdx
    jmp     .bat_inner_loop
.bat_inner_done:
    mov     [rbx + r15 * 8 + 8], r8
    inc     r15
    jmp     .bat_outer_loop

.bat_finish:
    mov     rax, rbx
    jmp     .bat_ret
.bat_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
.bat_ret:
    add     rsp, 48
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

os_cpu_count:
cpu_count:
process_cpu_count:
_pyfasm_os_cpu_count:
    mov     rax, [gs:60h]
    test    rax, rax
    jz      .cpu_def
    movzx   eax, byte [rax + 0B8h]
    test    eax, eax
    jnz     .cpu_ret
.cpu_def:
    mov     eax, 8
.cpu_ret:
    ret


_pyfasm_load_ext_symbol:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    mov     [rbp - 8], rdx
    call    [LoadLibraryA]
    test    rax, rax
    jz      .les_fail
    mov     rcx, rax
    mov     rdx, [rbp - 8]
    call    [GetProcAddress]
    jmp     .les_ret
.les_fail:
    xor     eax, eax
.les_ret:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_darkdetect_theme:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_is_dark_theme
    test    eax, eax
    jz      .ddt_light
    lea     rax, [szDarkStr]
    mov     rsp, rbp
    pop     rbp
    ret
.ddt_light:
    lea     rax, [szLightStr]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_int_to_str:
    ; RCX = integer
    ; Returns RAX = pointer to newly allocated null-terminated string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 80
    and     rsp, -16

    lea     rdi, [rbp - 32]
    mov     byte [rdi], 0
    mov     rax, rcx

    test    rax, rax
    jnz     .its_check_neg
    dec     rdi
    mov     byte [rdi], '0'
    jmp     .its_copy_alloc

.its_check_neg:
    xor     ebx, ebx
    test    rax, rax
    jns     .its_loop
    mov     ebx, 1
    neg     rax

.its_loop:
    test    rax, rax
    jz      .its_finish
    mov     r8, rax
    mov     rdx, 0CCCCCCCCCCCCCCCDh
    mul     rdx
    shr     rdx, 3
    lea     rcx, [rdx + rdx * 4]
    shl     rcx, 1
    sub     r8, rcx
    add     r8b, '0'
    dec     rdi
    mov     [rdi], r8b
    mov     rax, rdx
    jmp     .its_loop

.its_finish:
    test    ebx, ebx
    jz      .its_copy_alloc
    dec     rdi
    mov     byte [rdi], '-'

.its_copy_alloc:
    mov     rsi, rdi
    lea     rcx, [rbp - 32]
    sub     rcx, rsi
    inc     rcx
    mov     rbx, rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     rdx, rax
    mov     rcx, rbx
    rep     movsb
    mov     rax, rdx

    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_is_utf8_str_ptr:
    ; RCX = candidate value -> RAX = 1 if readable committed UTF-8 C-string, else 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .iu_no
    cmp     rsi, 65536
    jb      .iu_no
    mov     rax, 00007FFFFFFF0000h
    cmp     rsi, rax
    jae     .iu_no

    ; VirtualQuery(rsi, &mbi_at_rsp_32, 48)
    mov     rcx, rsi
    lea     rdx, [rsp + 32]
    mov     r8d, 48
    call    [VirtualQuery]
    test    rax, rax
    jz      .iu_no
    cmp     dword [rsp + 64], 1000h     ; MEM_COMMIT
    jne     .iu_no
    mov     eax, dword [rsp + 68]       ; Protect
    test    eax, 100h                   ; PAGE_GUARD
    jnz     .iu_no
    test    eax, 0EEh                   ; readable protection
    jz      .iu_no

    mov     rax, [rsp + 32]             ; BaseAddress
    add     rax, [rsp + 56]             ; + RegionSize
    sub     rax, rsi
    jbe     .iu_no
    xor     ebx, ebx
    cmp     rax, 256
    jb      .iu_have_limit
    mov     rax, 256
    mov     ebx, 1
.iu_have_limit:
    mov     r8, rax
    xor     r9d, r9d
.iu_loop:
    cmp     r9, r8
    jae     .iu_hit_limit
    movzx   eax, byte [rsi + r9]
    test    al, al
    jz      .iu_yes
    cmp     al, 80h
    jb      .iu_ascii

    cmp     al, 0C2h
    jb      .iu_no
    cmp     al, 0DFh
    jbe     .iu_mb1
    cmp     al, 0EFh
    jbe     .iu_mb2
    cmp     al, 0F4h
    jbe     .iu_mb3
    jmp     .iu_no

.iu_mb1:
    lea     r10, [r9 + 1]
    cmp     r10, r8
    jae     .iu_mb_limit
    movzx   edx, byte [rsi + r9 + 1]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    add     r9, 2
    jmp     .iu_loop

.iu_mb2:
    lea     r10, [r9 + 2]
    cmp     r10, r8
    jae     .iu_mb_limit
    movzx   edx, byte [rsi + r9 + 1]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    movzx   edx, byte [rsi + r9 + 2]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    add     r9, 3
    jmp     .iu_loop

.iu_mb3:
    lea     r10, [r9 + 3]
    cmp     r10, r8
    jae     .iu_mb_limit
    movzx   edx, byte [rsi + r9 + 1]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    movzx   edx, byte [rsi + r9 + 2]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    movzx   edx, byte [rsi + r9 + 3]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    add     r9, 4
    jmp     .iu_loop

.iu_mb_limit:
    test    ebx, ebx
    jnz     .iu_yes
    jmp     .iu_no

.iu_ascii:
    cmp     al, 9
    je      .iu_ascii_ok
    cmp     al, 10
    je      .iu_ascii_ok
    cmp     al, 13
    je      .iu_ascii_ok
    cmp     al, 32
    jb      .iu_no
    cmp     al, 126
    ja      .iu_no
.iu_ascii_ok:
    inc     r9
    jmp     .iu_loop

.iu_hit_limit:
    test    ebx, ebx
    jnz     .iu_yes
.iu_no:
    xor     eax, eax
    jmp     .iu_ret
.iu_yes:
    mov     eax, 1
.iu_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_auto:
    ; RCX = value (int64, f64 bits, or UTF-8 string pointer)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    mov     rax, rbx
    sar     rax, 48
    test    rax, rax
    jz      .pa_not_flt
    cmp     rax, -1
    je      .pa_not_flt
    call    _pyfasm_eval_print_clean_float
    jmp     .pa_done
.pa_not_flt:
    mov     rcx, rbx
    call    _pyfasm_is_utf8_str_ptr
    mov     rcx, rbx
    test    eax, eax
    jz      .pa_int
    call    _pyfasm_print_str
    jmp     .pa_done
.pa_int:
    call    _pyfasm_print_int
.pa_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_float_bits:
    ; RCX = IEEE-754 float64 bits
    movq    xmm0, rcx
    jmp     _pyfasm_print_float

_pyfasm_print_str_repr:
    ; RCX = string pointer -> prints 'text' or None
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jnz     .psr_nonnull
    lea     rcx, [none_str]
    call    _pyfasm_print_str
    jmp     .psr_done
.psr_nonnull:
    lea     rcx, [squote_str]
    call    _pyfasm_print_str
    mov     rcx, rbx
    call    _pyfasm_print_str
    lea     rcx, [squote_str]
    call    _pyfasm_print_str
.psr_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_auto_repr:
    ; RCX = value -> prints 'str' if UTF-8 string pointer, else int
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    mov     rcx, rbx
    test    eax, eax
    jz      .par_int
    call    _pyfasm_print_str_repr
    jmp     .par_done
.par_int:
    call    _pyfasm_print_int
.par_done:
    lea     rsp, [rbp - 8]
    pop     rbx
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
    sub     rsp, 80
    and     rsp, -16

    mov     rax, rcx
    test    rax, rax
    jns     .positive

    ; Negative number
    mov     rbx, rax
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    mov     rax, rbx
    neg     rax

.positive:
    lea     rdi, [rbp - 32]         ; end of temporary digit buffer
    mov     byte [rdi], 0           ; null-terminator
    mov     rsi, rax
    mov     r9, 0CCCCCCCCCCCCCCCDh  ; reciprocal multiplier for fast division by 10 (from porth/Lemire)

.digit_loop:
    mov     rax, rsi
    mul     r9                      ; rdx = (rsi * r9) >> 64
    shr     rdx, 3                  ; rdx = quotient
    lea     rcx, [rdx + rdx * 4]
    add     rcx, rcx                ; rcx = quotient * 10
    mov     rax, rsi
    sub     rax, rcx                ; rax = remainder (0..9)
    add     al, '0'
    dec     rdi
    mov     [rdi], al
    mov     rsi, rdx                ; update quotient
    test    rsi, rsi
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

_pyfasm_print_list_with:
    ; RCX = list pointer, RDX = element printer function pointer (takes RCX)
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
    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jnz     .plw_not_null
    lea     rcx, [lbrack_str]
    call    _pyfasm_print_str
    lea     rcx, [rbrack_str]
    call    _pyfasm_print_str
    jmp     .plw_ret

.plw_not_null:
    test    rbx, rbx
    js      .plw_is_int
    cmp     rbx, 65536
    jb      .plw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jb      .plw_is_ptr
.plw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
    jmp     .plw_ret

.plw_is_ptr:
    lea     rcx, [lbrack_str]
    call    _pyfasm_print_str
    mov     r12, [rbx]
    xor     r13, r13

.plw_loop:
    cmp     r13, r12
    jge     .plw_end
    test    r13, r13
    jz      .plw_elem
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str

.plw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    inc     r13
    jmp     .plw_loop

.plw_end:
    lea     rcx, [rbrack_str]
    call    _pyfasm_print_str

.plw_ret:
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

_pyfasm_print_list:
    lea     rdx, [_pyfasm_print_auto_repr]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_int:
    lea     rdx, [_pyfasm_print_int]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_str:
    lea     rdx, [_pyfasm_print_str_repr]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_float:
    lea     rdx, [_pyfasm_print_float_bits]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_int:
    lea     rdx, [_pyfasm_print_list_int]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_str:
    lea     rdx, [_pyfasm_print_list_str]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_float:
    lea     rdx, [_pyfasm_print_list_float]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_auto:
    lea     rdx, [_pyfasm_print_list]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_3d_int:
    lea     rdx, [_pyfasm_print_list_2d_int]
    jmp     _pyfasm_print_list_with

_pyfasm_print_tuple_with:
    ; RCX = tuple pointer, RDX = element printer function pointer (takes RCX)
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
    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jnz     .ptw_not_null
    lea     rcx, [lparen_str]
    call    _pyfasm_print_str
    lea     rcx, [rparen_str]
    call    _pyfasm_print_str
    jmp     .ptw_ret

.ptw_not_null:
    test    rbx, rbx
    js      .ptw_is_int
    cmp     rbx, 65536
    jb      .ptw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jb      .ptw_is_ptr
.ptw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
    jmp     .ptw_ret

.ptw_is_ptr:
    lea     rcx, [lparen_str]
    call    _pyfasm_print_str
    mov     r12, [rbx]
    xor     r13, r13

.ptw_loop:
    cmp     r13, r12
    jge     .ptw_after_loop
    test    r13, r13
    jz      .ptw_elem
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str

.ptw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    inc     r13
    jmp     .ptw_loop

.ptw_after_loop:
    cmp     r12, 1
    jne     .ptw_end
    lea     rcx, [comma_str]
    call    _pyfasm_print_str

.ptw_end:
    lea     rcx, [rparen_str]
    call    _pyfasm_print_str

.ptw_ret:
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

_pyfasm_print_tuple:
    lea     rdx, [_pyfasm_print_auto_repr]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_int:
    lea     rdx, [_pyfasm_print_int]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_str:
    lea     rdx, [_pyfasm_print_str_repr]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_float:
    lea     rdx, [_pyfasm_print_float_bits]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_list:
    lea     rdx, [_pyfasm_print_list]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_dict_with:
    ; RCX = dict_ptr, RDX = key_printer(rcx), R8 = val_printer(rcx)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    mov     r15, r8
    test    rbx, rbx
    jz      .pdw_empty
    test    rbx, rbx
    js      .pdw_is_int
    cmp     rbx, 65536
    jb      .pdw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .pdw_is_int

    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    mov     r12, [rbx]
    xor     r13, r13
    xor     edi, edi
.pdw_loop:
    cmp     r13, r12
    jge     .pdw_end
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .pdw_next
    cmp     rax, -1
    je      .pdw_next

    test    edi, edi
    jz      .pdw_no_comma
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str
.pdw_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
    lea     rcx, [colon_sp_str]
    call    _pyfasm_print_str
    mov     rcx, [rsi + 16]
    call    r15
.pdw_next:
    inc     r13
    jmp     .pdw_loop
.pdw_end:
    lea     rcx, [rbrace_str]
    call    _pyfasm_print_str
    jmp     .pdw_ret
.pdw_empty:
    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    lea     rcx, [rbrace_str]
    call    _pyfasm_print_str
    jmp     .pdw_ret
.pdw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
.pdw_ret:
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

_pyfasm_print_set_with:
    ; RCX = set_ptr (hash table or list-backed), RDX = elem_printer(rcx)
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

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .psw_empty
    test    rbx, rbx
    js      .psw_is_int
    cmp     rbx, 65536
    jb      .psw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .psw_is_int

    mov     r12, [rbx]
    cmp     r12, 256
    jb      .psw_list_mode
    cmp     qword [rbx + 8], 0
    jle     .psw_empty

    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    xor     r13, r13
    xor     edi, edi
.psw_ht_loop:
    cmp     r13, r12
    jge     .psw_end
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .psw_ht_next
    cmp     rax, -1
    je      .psw_ht_next
    test    edi, edi
    jz      .psw_ht_no_comma
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str
.psw_ht_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
.psw_ht_next:
    inc     r13
    jmp     .psw_ht_loop

.psw_list_mode:
    test    r12, r12
    jle     .psw_empty
    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    xor     r13, r13
.psw_lst_loop:
    cmp     r13, r12
    jge     .psw_end
    test    r13, r13
    jz      .psw_lst_elem
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str
.psw_lst_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    inc     r13
    jmp     .psw_lst_loop

.psw_end:
    lea     rcx, [rbrace_str]
    call    _pyfasm_print_str
    jmp     .psw_ret
.psw_empty:
    lea     rcx, [empty_set_str]
    call    _pyfasm_print_str
    jmp     .psw_ret
.psw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
.psw_ret:
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

_pyfasm_str_to_repr:
    ; RCX = string pointer -> RAX = heap string "'...'" or None
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    test    rcx, rcx
    jnz     .strr_nonnull
    lea     rax, [none_str]
    jmp     .strr_done
.strr_nonnull:
    mov     rdx, rcx
    lea     rcx, [squote_str]
    call    _pyfasm_str_concat
    mov     rcx, rax
    lea     rdx, [squote_str]
    call    _pyfasm_str_concat
.strr_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_auto_to_str:
    ; RCX = value -> RAX = string pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    mov     rax, rbx
    sar     rax, 48
    test    rax, rax
    jz      .ats_not_flt
    cmp     rax, -1
    je      .ats_not_flt
    call    _pyfasm_eval_float_to_clean_str
    jmp     .ats_done
.ats_not_flt:
    mov     rcx, rbx
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .ats_int
    mov     rax, rbx
    jmp     .ats_done
.ats_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.ats_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_auto_to_repr:
    ; RCX = value -> RAX = repr string pointer ('str' if UTF-8 ptr, else int str)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    mov     rcx, rbx
    test    eax, eax
    jz      .atr_int
    call    _pyfasm_str_to_repr
    jmp     .atr_done
.atr_int:
    call    _pyfasm_int_to_str
.atr_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_to_str_with:
    ; RCX = list pointer, RDX = elem_to_str(rcx)->rax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .ltsw_empty
    test    rbx, rbx
    js      .ltsw_int
    cmp     rbx, 65536
    jb      .ltsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .ltsw_int

    lea     r15, [lbrack_str]
    mov     r12, [rbx]
    xor     r13, r13
.ltsw_loop:
    cmp     r13, r12
    jge     .ltsw_close
    test    r13, r13
    jz      .ltsw_elem
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.ltsw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .ltsw_loop
.ltsw_close:
    mov     rcx, r15
    lea     rdx, [rbrack_str]
    call    _pyfasm_str_concat
    jmp     .ltsw_ret
.ltsw_empty:
    lea     rcx, [lbrack_str]
    lea     rdx, [rbrack_str]
    call    _pyfasm_str_concat
    jmp     .ltsw_ret
.ltsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.ltsw_ret:
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

_pyfasm_list_to_str:
    lea     rdx, [_pyfasm_auto_to_repr]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_int_to_str:
    lea     rdx, [_pyfasm_int_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_str_to_str:
    lea     rdx, [_pyfasm_str_to_repr]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_float_to_str:
    lea     rdx, [_pyfasm_float_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_int_to_str:
    lea     rdx, [_pyfasm_list_int_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_str_to_str:
    lea     rdx, [_pyfasm_list_str_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_float_to_str:
    lea     rdx, [_pyfasm_list_float_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_auto_to_str:
    lea     rdx, [_pyfasm_list_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_3d_int_to_str:
    lea     rdx, [_pyfasm_list_2d_int_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_tuple_to_str_with:
    ; RCX = tuple pointer, RDX = elem_to_str(rcx)->rax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .ttsw_empty
    test    rbx, rbx
    js      .ttsw_int
    cmp     rbx, 65536
    jb      .ttsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .ttsw_int

    lea     r15, [lparen_str]
    mov     r12, [rbx]
    xor     r13, r13
.ttsw_loop:
    cmp     r13, r12
    jge     .ttsw_after_loop
    test    r13, r13
    jz      .ttsw_elem
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.ttsw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .ttsw_loop
.ttsw_after_loop:
    cmp     r12, 1
    jne     .ttsw_close
    mov     rcx, r15
    lea     rdx, [comma_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.ttsw_close:
    mov     rcx, r15
    lea     rdx, [rparen_str]
    call    _pyfasm_str_concat
    jmp     .ttsw_ret
.ttsw_empty:
    lea     rcx, [lparen_str]
    lea     rdx, [rparen_str]
    call    _pyfasm_str_concat
    jmp     .ttsw_ret
.ttsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.ttsw_ret:
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

_pyfasm_tuple_to_str:
    lea     rdx, [_pyfasm_auto_to_repr]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_int_to_str:
    lea     rdx, [_pyfasm_int_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_str_to_str:
    lea     rdx, [_pyfasm_str_to_repr]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_float_to_str:
    lea     rdx, [_pyfasm_float_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_list_to_str:
    lea     rdx, [_pyfasm_list_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_dict_to_str_with:
    ; RCX = dict_ptr, RDX = key_to_str(rcx)->rax, R8 = val_to_str(rcx)->rax
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

    mov     rbx, rcx
    mov     r14, rdx
    mov     r15, r8
    test    rbx, rbx
    jz      .dtsw_empty
    test    rbx, rbx
    js      .dtsw_int
    cmp     rbx, 65536
    jb      .dtsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .dtsw_int

    lea     rax, [lbrace_str]
    mov     [rsp + 40], rax
    mov     r12, [rbx]
    xor     r13, r13
    xor     edi, edi
.dtsw_loop:
    cmp     r13, r12
    jge     .dtsw_close
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .dtsw_next
    cmp     rax, -1
    je      .dtsw_next

    test    edi, edi
    jz      .dtsw_no_comma
    mov     rcx, [rsp + 40]
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     [rsp + 40], rax
.dtsw_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
    mov     rcx, [rsp + 40]
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     rcx, rax
    lea     rdx, [colon_sp_str]
    call    _pyfasm_str_concat
    mov     [rsp + 40], rax

    mov     rcx, [rsi + 16]
    call    r15
    mov     rcx, [rsp + 40]
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     [rsp + 40], rax
.dtsw_next:
    inc     r13
    jmp     .dtsw_loop

.dtsw_close:
    mov     rcx, [rsp + 40]
    lea     rdx, [rbrace_str]
    call    _pyfasm_str_concat
    jmp     .dtsw_ret
.dtsw_empty:
    lea     rcx, [lbrace_str]
    lea     rdx, [rbrace_str]
    call    _pyfasm_str_concat
    jmp     .dtsw_ret
.dtsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.dtsw_ret:
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

_pyfasm_set_to_str_with:
    ; RCX = set_ptr, RDX = elem_to_str(rcx)->rax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .stsw_empty
    test    rbx, rbx
    js      .stsw_int
    cmp     rbx, 65536
    jb      .stsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .stsw_int

    mov     r12, [rbx]
    cmp     r12, 256
    jb      .stsw_list_mode
    cmp     qword [rbx + 8], 0
    jle     .stsw_empty

    lea     r15, [lbrace_str]
    xor     r13, r13
    xor     edi, edi
.stsw_ht_loop:
    cmp     r13, r12
    jge     .stsw_close
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .stsw_ht_next
    cmp     rax, -1
    je      .stsw_ht_next
    test    edi, edi
    jz      .stsw_ht_no_comma
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.stsw_ht_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
.stsw_ht_next:
    inc     r13
    jmp     .stsw_ht_loop

.stsw_list_mode:
    test    r12, r12
    jle     .stsw_empty
    lea     r15, [lbrace_str]
    xor     r13, r13
.stsw_lst_loop:
    cmp     r13, r12
    jge     .stsw_close
    test    r13, r13
    jz      .stsw_lst_elem
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.stsw_lst_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .stsw_lst_loop

.stsw_close:
    mov     rcx, r15
    lea     rdx, [rbrace_str]
    call    _pyfasm_str_concat
    jmp     .stsw_ret
.stsw_empty:
    lea     rax, [empty_set_str]
    jmp     .stsw_ret
.stsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.stsw_ret:
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

_pyfasm_str_to_int:
    ; RCX = UTF-8 decimal string pointer or integer -> RAX = signed int64
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jnz     .sti_parse
    mov     rax, rbx
    jmp     .sti_ret

.sti_parse:
    mov     rsi, rbx
.sti_ws:
    movzx   eax, byte [rsi]
    cmp     al, ' '
    je      .sti_ws_next
    cmp     al, 9
    je      .sti_ws_next
    cmp     al, 10
    je      .sti_ws_next
    cmp     al, 13
    jne     .sti_sign
.sti_ws_next:
    inc     rsi
    jmp     .sti_ws

.sti_sign:
    xor     ebx, ebx
    cmp     byte [rsi], '-'
    jne     .sti_chk_plus
    mov     ebx, 1
    inc     rsi
    jmp     .sti_digits_init
.sti_chk_plus:
    cmp     byte [rsi], '+'
    jne     .sti_digits_init
    inc     rsi

.sti_digits_init:
    xor     eax, eax
.sti_loop:
    movzx   edx, byte [rsi]
    cmp     dl, '0'
    jb      .sti_apply_sign
    cmp     dl, '9'
    ja      .sti_apply_sign
    sub     dl, '0'
    imul    rax, rax, 10
    add     rax, rdx
    inc     rsi
    jmp     .sti_loop

.sti_apply_sign:
    test    ebx, ebx
    jz      .sti_ret
    neg     rax
.sti_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_to_float:
    ; RCX = string pointer or int64 -> RAX = IEEE-754 float64 bits
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jnz     .stf_parse
    cvtsi2sd xmm0, rbx
    movq    rax, xmm0
    jmp     .stf_ret

.stf_parse:
    mov     rsi, rbx
.stf_ws:
    movzx   eax, byte [rsi]
    cmp     al, ' '
    je      .stf_ws_next
    cmp     al, 9
    je      .stf_ws_next
    cmp     al, 10
    je      .stf_ws_next
    cmp     al, 13
    jne     .stf_sign
.stf_ws_next:
    inc     rsi
    jmp     .stf_ws

.stf_sign:
    xor     ebx, ebx
    cmp     byte [rsi], '-'
    jne     .stf_chk_plus
    mov     ebx, 1
    inc     rsi
    jmp     .stf_init
.stf_chk_plus:
    cmp     byte [rsi], '+'
    jne     .stf_init
    inc     rsi

.stf_init:
    xorpd   xmm0, xmm0
    movsd   xmm2, [flt_ten]
.stf_int_loop:
    movzx   eax, byte [rsi]
    cmp     al, '0'
    jb      .stf_chk_dot
    cmp     al, '9'
    ja      .stf_chk_dot
    sub     eax, '0'
    mulsd   xmm0, xmm2
    cvtsi2sd xmm1, eax
    addsd   xmm0, xmm1
    inc     rsi
    jmp     .stf_int_loop

.stf_chk_dot:
    cmp     byte [rsi], '.'
    jne     .stf_apply_sign
    inc     rsi
    movsd   xmm3, [flt_ten]
.stf_frac_loop:
    movzx   eax, byte [rsi]
    cmp     al, '0'
    jb      .stf_apply_sign
    cmp     al, '9'
    ja      .stf_apply_sign
    sub     eax, '0'
    cvtsi2sd xmm1, eax
    divsd   xmm1, xmm3
    addsd   xmm0, xmm1
    mulsd   xmm3, xmm2
    inc     rsi
    jmp     .stf_frac_loop

.stf_apply_sign:
    test    ebx, ebx
    jz      .stf_pack
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.stf_pack:
    movq    rax, xmm0
.stf_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_utf8_next_char:
    ; RCX = str_ptr, RDX = byte_offset
    ; Returns RAX = heap 1-char UTF-8 null-terminated str (or 0 if NUL), RDX = new byte_offset
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     r12, rdx
    test    rsi, rsi
    jz      .unc_eof
    add     rsi, r12
    movzx   eax, byte [rsi]
    test    al, al
    jz      .unc_eof

    mov     rbx, 1
    cmp     al, 0C2h
    jb      .unc_copy
    cmp     al, 0DFh
    jbe     .unc_len2
    cmp     al, 0EFh
    jbe     .unc_len3
    cmp     al, 0F4h
    jbe     .unc_len4
    jmp     .unc_copy
.unc_len2:
    mov     rbx, 2
    jmp     .unc_clamp
.unc_len3:
    mov     rbx, 3
    jmp     .unc_clamp
.unc_len4:
    mov     rbx, 4
.unc_clamp:
    mov     r13, 1
.unc_chk_loop:
    cmp     r13, rbx
    jae     .unc_copy
    cmp     byte [rsi + r13], 0
    je      .unc_trunc
    inc     r13
    jmp     .unc_chk_loop
.unc_trunc:
    mov     rbx, r13

.unc_copy:
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.unc_cp_loop:
    cmp     rcx, rbx
    jae     .unc_finish
    mov     r8b, byte [rsi + rcx]
    mov     byte [rax + rcx], r8b
    inc     rcx
    jmp     .unc_cp_loop
.unc_finish:
    mov     byte [rax + rbx], 0
    lea     rdx, [r12 + rbx]
    jmp     .unc_ret

.unc_eof:
    xor     eax, eax
    mov     rdx, r12
.unc_ret:
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_split:
    ; RCX = str_ptr, RDX = sep_ptr (0 or "" => split on ASCII whitespace runs)
    ; Returns RAX = list_ptr [count, str0, str1, ...]
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

    mov     r15, rcx                ; str_ptr
    mov     r13, rdx                ; sep_ptr
    test    r15, r15
    jnz     .ssp_alloc_list
    mov     ecx, 16
    call    _pyfasm_list_create
    jmp     .ssp_ret

.ssp_alloc_list:
    mov     rcx, r15
    call    _pyfasm_str_len
    lea     rcx, [rax + 2]
    cmp     rcx, 16
    jae     .ssp_cap_ok
    mov     ecx, 16
.ssp_cap_ok:
    call    _pyfasm_list_create
    mov     r12, rax                ; r12 = result list

    test    r13, r13
    jz      .ssp_ws_init
    cmp     byte [r13], 0
    je      .ssp_ws_init

    ; Explicit separator mode
    mov     rcx, r13
    call    _pyfasm_str_len
    mov     r14, rax                ; r14 = sep_len
    mov     rsi, r15                ; cur
    mov     rdi, r15                ; token start

.ssp_sep_loop:
    cmp     byte [rsi], 0
    je      .ssp_sep_last
    xor     ecx, ecx
.ssp_cmp_loop:
    cmp     rcx, r14
    jae     .ssp_sep_match
    mov     al, byte [rsi + rcx]
    test    al, al
    jz      .ssp_sep_nomatch
    cmp     al, byte [r13 + rcx]
    jne     .ssp_sep_nomatch
    inc     rcx
    jmp     .ssp_cmp_loop

.ssp_sep_nomatch:
    inc     rsi
    jmp     .ssp_sep_loop

.ssp_sep_match:
    mov     rbx, rsi
    sub     rbx, rdi
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ssp_sm_cp:
    cmp     rcx, rbx
    jae     .ssp_sm_nul
    mov     dl, byte [rdi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ssp_sm_cp
.ssp_sm_nul:
    mov     byte [rax + rbx], 0
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_list_append
    add     rsi, r14
    mov     rdi, rsi
    jmp     .ssp_sep_loop

.ssp_sep_last:
    mov     rbx, rsi
    sub     rbx, rdi
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ssp_sl_cp:
    cmp     rcx, rbx
    jae     .ssp_sl_nul
    mov     dl, byte [rdi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ssp_sl_cp
.ssp_sl_nul:
    mov     byte [rax + rbx], 0
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_list_append
    jmp     .ssp_done

.ssp_ws_init:
    mov     rsi, r15
.ssp_ws_skip:
    mov     al, byte [rsi]
    test    al, al
    jz      .ssp_done
    cmp     al, ' '
    je      .ssp_ws_adv
    cmp     al, 9
    je      .ssp_ws_adv
    cmp     al, 10
    je      .ssp_ws_adv
    cmp     al, 13
    jne     .ssp_ws_tok
.ssp_ws_adv:
    inc     rsi
    jmp     .ssp_ws_skip

.ssp_ws_tok:
    mov     rdi, rsi
.ssp_ws_scan:
    mov     al, byte [rsi]
    test    al, al
    jz      .ssp_ws_emit
    cmp     al, ' '
    je      .ssp_ws_emit
    cmp     al, 9
    je      .ssp_ws_emit
    cmp     al, 10
    je      .ssp_ws_emit
    cmp     al, 13
    je      .ssp_ws_emit
    inc     rsi
    jmp     .ssp_ws_scan

.ssp_ws_emit:
    mov     rbx, rsi
    sub     rbx, rdi
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ssp_ws_cp:
    cmp     rcx, rbx
    jae     .ssp_ws_nul
    mov     dl, byte [rdi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ssp_ws_cp
.ssp_ws_nul:
    mov     byte [rax + rbx], 0
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_list_append
    jmp     .ssp_ws_skip

.ssp_done:
    mov     rax, r12
.ssp_ret:
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

_pyfasm_input:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16

    mov     rcx, [hStdIn]
    test    rcx, rcx
    jnz     .inp_check_console
    mov     ecx, -10                ; STD_INPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdIn], rax
    mov     rcx, rax
    lea     rdx, [consoleMode]
    call    [GetConsoleMode]
    mov     [isStdInConsole], eax
    mov     rcx, [hStdIn]

.inp_check_console:
    cmp     dword [isStdInConsole], 0
    je      .inp_read_file

    ; Interactive Windows console input via ReadConsoleW -> UTF-8
    lea     rdx, [inp_wbuf]
    mov     r8d, 2047
    lea     r9, [bytesRead]
    mov     dword [bytesRead], 0
    mov     qword [rsp + 32], 0
    call    [ReadConsoleW]
    test    eax, eax
    jz      .inp_empty
    mov     eax, dword [bytesRead]
    test    eax, eax
    jz      .inp_empty

    mov     ecx, 65001              ; CP_UTF8
    xor     edx, edx
    lea     r8, [inp_wbuf]
    mov     r9d, eax
    lea     rax, [inp_buf]
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 4095
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    call    [WideCharToMultiByte]
    test    eax, eax
    jle     .inp_empty
    mov     edi, eax
    lea     rsi, [inp_buf]
    mov     byte [rsi + rdi], 0
    jmp     .inp_strip

.inp_read_file:
    mov     rcx, [hStdIn]
    lea     rdx, [inp_buf]
    mov     r8d, 4095
    lea     r9, [bytesRead]
    mov     dword [bytesRead], 0
    mov     qword [rsp + 32], 0
    call    [ReadFile]
    test    eax, eax
    jz      .inp_empty
    mov     eax, dword [bytesRead]
    test    eax, eax
    jz      .inp_empty
    mov     edi, eax
    lea     rsi, [inp_buf]
    mov     byte [rsi + rdi], 0

.inp_strip:
    test    rdi, rdi
    jz      .inp_alloc
    movzx   eax, byte [rsi + rdi - 1]
    cmp     al, 10                  ; LF
    je      .inp_dec
    cmp     al, 13                  ; CR
    je      .inp_dec
    jmp     .inp_alloc
.inp_dec:
    dec     rdi
    mov     byte [rsi + rdi], 0
    jmp     .inp_strip

.inp_alloc:
    lea     rcx, [rdi + 1]
    mov     rbx, rdi
    call    _pyfasm_alloc
    mov     r12, rax
    mov     rdi, r12
    lea     rsi, [inp_buf]
    mov     rcx, rbx
    rep     movsb
    mov     byte [rdi], 0
    mov     rax, r12
    jmp     .inp_ret

.inp_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0

.inp_ret:
    lea     rsp, [rbp - 32]
    pop     r12
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

_pyfasm_alloc:
    ; RCX = size in bytes
    jmp     _pyfasm_alloc_memory

_pyfasm_free:
    ; RCX = pointer
    jmp     _pyfasm_free_memory

_pyfasm_init_gui:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 128
    and     rsp, -16
    cmp     qword [_pyfasm_h_inst], 0
    jne     .gui_already_init

    xor     ecx, ecx
    call    [GetModuleHandleA]
    mov     [_pyfasm_h_inst], rax

    ; Create Solid Dark Brushes
    mov     ecx, 001A110Fh          ; #0f111a
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_bg], rax

    mov     ecx, 002E1F1Dh          ; #1d1f2e
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_card], rax

    mov     ecx, 00201614h          ; #141620
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_input], rax

    mov     ecx, 00A56A1Fh          ; #1f6aa5 modern accent
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_orange], rax

    mov     ecx, 007B4814h          ; #14487b pressed accent
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_orange_press], rax

    mov     ecx, 005C4430h          ; selection highlight
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_sel], rax

    ; Create Modern GDI Pens for borders
    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 00A56A1Fh
    call    [CreatePen]
    mov     [_pyfasm_hpen_orange], rax

    ; Load Application Icons (ID 1 from PE resources, or fallback to 'icon.ico' file)
    mov     rcx, [_pyfasm_h_inst]
    mov     edx, 1                  ; ID 1
    mov     r8d, 1                  ; IMAGE_ICON
    mov     r9d, 32                 ; cx = 32
    mov     qword [rsp + 32], 32    ; cy = 32
    mov     qword [rsp + 40], 0     ; LR_DEFAULTCOLOR
    call    [LoadImageW]
    mov     [_pyfasm_h_icon_big], rax

    mov     rcx, [_pyfasm_h_inst]
    mov     edx, 1                  ; ID 1
    mov     r8d, 1                  ; IMAGE_ICON
    mov     r9d, 16                 ; cx = 16
    mov     qword [rsp + 32], 16    ; cy = 16
    mov     qword [rsp + 40], 0     ; LR_DEFAULTCOLOR
    call    [LoadImageW]
    mov     [_pyfasm_h_icon_small], rax

    ; Fallback: if not embedded in PE resource, try loading 'icon.ico' from disk
    cmp     qword [_pyfasm_h_icon_big], 0
    jne     .icon_loaded_ok
    xor     ecx, ecx
    lea     rdx, [wszIconFile]
    mov     r8d, 1                  ; IMAGE_ICON
    mov     r9d, 32
    mov     qword [rsp + 32], 32
    mov     qword [rsp + 40], 10h   ; LR_LOADFROMFILE
    call    [LoadImageW]
    mov     [_pyfasm_h_icon_big], rax

    xor     ecx, ecx
    lea     rdx, [wszIconFile]
    mov     r8d, 1                  ; IMAGE_ICON
    mov     r9d, 16
    mov     qword [rsp + 32], 16
    mov     qword [rsp + 40], 10h   ; LR_LOADFROMFILE
    call    [LoadImageW]
    mov     [_pyfasm_h_icon_small], rax
.icon_loaded_ok:

    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 00554133h          ; #334155 (Dark Slate Border)
    call    [CreatePen]
    mov     [_pyfasm_hpen_slate], rax

    mov     ecx, 00261B14h          ; elevated dark slate card background #141b26
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_card_sel], rax

    mov     ecx, 0045A728h          ; green pill background #28a745
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_green_pill], rax

    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 0045A728h
    call    [CreatePen]
    mov     [_pyfasm_hpen_green_pill], rax

    ; Create Modern Segoe UI Fonts
    ; 1. Normal UI Font (Segoe UI, 14px, FW_NORMAL 400)
    mov     rcx, -14
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 400
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5     ; CLEARTYPE_QUALITY
    mov     qword [rsp + 96], 0
    lea     rax, [wszSegoeUI]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_h_font_ui], rax
    mov     [_pyfasm_h_font], rax

    ; 2. Bold UI Font (Segoe UI, 14px, FW_BOLD 700)
    mov     rcx, -14
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 700   ; FW_BOLD
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5     ; CLEARTYPE_QUALITY
    mov     qword [rsp + 96], 0
    lea     rax, [wszSegoeUI]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_h_font_bold], rax

    ; 3. Large Title Font (Segoe UI, 18px, FW_BOLD 700)
    mov     rcx, -18
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 700   ; FW_BOLD
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5     ; CLEARTYPE_QUALITY
    mov     qword [rsp + 96], 0
    lea     rax, [wszSegoeUI]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_h_font_title], rax

    ; 4. Monospace Code Font (Consolas, 13px, FW_NORMAL 400)
    mov     rcx, -13
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 400
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5     ; CLEARTYPE_QUALITY
    mov     qword [rsp + 96], 0
    lea     rax, [wszConsolas]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_h_font_mono], rax

    ; Load standard arrow cursor IDC_ARROW (32512)
    xor     ecx, ecx
    mov     edx, 32512
    call    [LoadCursorA]
    mov     r11, rax

    ; Setup WNDCLASSEXW (80 bytes)
    mov     dword [_pyfasm_wc], 80          ; cbSize
    mov     dword [_pyfasm_wc + 4], 3       ; CS_HREDRAW | CS_VREDRAW
    lea     rax, [_pyfasm_wnd_proc]
    mov     qword [_pyfasm_wc + 8], rax     ; lpfnWndProc
    mov     dword [_pyfasm_wc + 16], 0      ; cbClsExtra
    mov     dword [_pyfasm_wc + 20], 0      ; cbWndExtra
    mov     rax, [_pyfasm_h_inst]
    mov     qword [_pyfasm_wc + 24], rax    ; hInstance
    mov     rax, [_pyfasm_h_icon_big]
    mov     qword [_pyfasm_wc + 32], rax    ; hIcon (32x32)
    mov     qword [_pyfasm_wc + 40], r11    ; hCursor (IDC_ARROW)
    mov     rax, [_pyfasm_hbr_bg]
    mov     qword [_pyfasm_wc + 48], rax    ; hbrBackground = solid dark brush!
    mov     qword [_pyfasm_wc + 56], 0      ; lpszMenuName
    lea     rax, [_pyfasm_wnd_class_w]
    mov     qword [_pyfasm_wc + 64], rax    ; lpszClassName
    mov     rax, [_pyfasm_h_icon_small]
    mov     qword [_pyfasm_wc + 72], rax    ; hIconSm (16x16)

    lea     rcx, [_pyfasm_wc]
    call    [RegisterClassExW]

    ; Create Canvas Background Brush
    mov     ecx, 001E1616h
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_canvas], rax

    ; Setup WNDCLASSEXW for Card (PyFasmCardClassW)
    lea     rax, [_pyfasm_card_wnd_proc]
    mov     qword [_pyfasm_wc + 8], rax
    mov     rax, [_pyfasm_hbr_card]
    mov     qword [_pyfasm_wc + 48], rax
    lea     rax, [_pyfasm_card_class_w]
    mov     qword [_pyfasm_wc + 64], rax
    lea     rcx, [_pyfasm_wc]
    call    [RegisterClassExW]

    ; Setup WNDCLASSEXW for Canvas (PyFasmCanvasClassW)
    lea     rax, [_pyfasm_canvas_wnd_proc]
    mov     qword [_pyfasm_wc + 8], rax
    mov     rax, [_pyfasm_hbr_canvas]
    mov     qword [_pyfasm_wc + 48], rax
    lea     rax, [_pyfasm_canvas_class_w]
    mov     qword [_pyfasm_wc + 64], rax
    lea     rcx, [_pyfasm_wc]
    call    [RegisterClassExW]

    ; Also register ANSI class fallback
    lea     rax, [_pyfasm_wnd_class]
    mov     qword [_pyfasm_wc + 64], rax
    lea     rcx, [_pyfasm_wc]
    call    [RegisterClassExA]

.gui_already_init:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_utf8_to_wide:
    ; RCX = utf8_src, RDX = wide_dst, R8 = max_wide_chars
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jz      .u2w_null

    mov     [rsp + 40], r8      ; param 6: cchWideChar = max_wide_chars
    mov     [rsp + 32], rdx     ; param 5: lpWideCharStr = wide_dst
    mov     r9d, -1             ; param 4: cbMultiByte = -1 (null-terminated)
    mov     r8, rcx             ; param 3: lpMultiByteStr = utf8_src
    xor     edx, edx            ; param 2: dwFlags = 0
    mov     ecx, 65001          ; param 1: CodePage = CP_UTF8
    call    [MultiByteToWideChar]
    jmp     .u2w_ret

.u2w_null:
    test    rdx, rdx
    jz      .u2w_ret
    mov     word [rdx], 0

.u2w_ret:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_window_title:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    mov     [_pyfasm_wnd_title_ptr], rcx
    test    rcx, rcx
    jz      .set_title_done
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    mov     rcx, [_pyfasm_h_wnd]
    test    rcx, rcx
    jz      .set_title_done
    lea     rdx, [_pyfasm_wide_buf]
    call    [SetWindowTextW]
.set_title_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_window:
    ; RCX = title string (or 0 for default), RDX = width (or 0 for 1420), R8 = height (or 0 for 900)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 128
    and     rsp, -16

    mov     [rsp + 96], rcx     ; title
    mov     [rsp + 104], rdx    ; width
    mov     rax, r8
    test    rax, rax
    jnz     .h_ok
    mov     rax, 900
.h_ok:
    mov     [rsp + 88], rax     ; height

    call    _pyfasm_init_gui

    ; If explicit title passed in RCX ([rsp+96]), store into _pyfasm_wnd_title_ptr
    mov     rax, [rsp + 96]
    test    rax, rax
    jz      .cw_title_src
    mov     [_pyfasm_wnd_title_ptr], rax
.cw_title_src:
    mov     rcx, [_pyfasm_wnd_title_ptr]
    test    rcx, rcx
    jz      .use_default_title
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 1024
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_wide_buf]
    jmp     .title_done
.use_default_title:
    lea     r8, [_pyfasm_wnd_title_w]
.title_done:

    ; Determine width
    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .w_ok
    mov     r10, 1100
.w_ok:

    ; CreateWindowExW(0, _pyfasm_wnd_class_w, title, WS_OVERLAPPEDWINDOW, 40, 40, width, height, 0, 0, hInstance, 0)
    xor     ecx, ecx
    lea     rdx, [_pyfasm_wnd_class_w]
    mov     r9d, 00CF0000h          ; WS_OVERLAPPEDWINDOW (not WS_VISIBLE - hidden until styled!)
    mov     qword [rsp + 32], 40    ; X
    mov     qword [rsp + 40], 40    ; Y
    mov     [rsp + 48], r10         ; nWidth
    mov     rax, [rsp + 88]
    mov     [rsp + 56], rax         ; nHeight
    mov     qword [rsp + 64], 0     ; hWndParent
    mov     qword [rsp + 72], 0     ; hMenu
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax         ; hInstance
    mov     qword [rsp + 88], 0     ; lpParam
    call    [CreateWindowExW]
    mov     [_pyfasm_h_wnd], rax

    ; Set Window & Taskbar Icons
    cmp     qword [_pyfasm_h_icon_big], 0
    jz      .skip_wm_seticon
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 80h                ; WM_SETICON
    mov     r8d, 1                  ; ICON_BIG (Taskbar & Alt+Tab)
    mov     r9, [_pyfasm_h_icon_big]
    call    [SendMessageW]

    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 80h                ; WM_SETICON
    xor     r8d, r8d                ; ICON_SMALL (Titlebar & Tray)
    mov     r9, [_pyfasm_h_icon_small]
    call    [SendMessageW]
.skip_wm_seticon:

    ; Set DWM Immersive Dark Mode on titlebar (Attribute 20 for Win10 20H1+ and Win11)
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 20                 ; DWMWA_USE_IMMERSIVE_DARK_MODE
    lea     r8, [_pyfasm_dark_mode_val]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]

    ; Fallback Attribute 19 (for Windows 10 versions before 20H1)
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 19                 ; DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1
    lea     r8, [_pyfasm_dark_mode_val]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]

    ; Attribute 35: DWMWA_CAPTION_COLOR (Windows 11)
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 35
    lea     r8, [_pyfasm_caption_color]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]

    ; Attribute 36: DWMWA_TEXT_COLOR (Windows 11)
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 36
    lea     r8, [_pyfasm_caption_text_color]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]

    ; Apply Windows 10/11 DarkMode theme via UXTHEME
    mov     rcx, [_pyfasm_h_wnd]
    lea     rdx, [wszDarkModeExplorer]
    xor     r8, r8
    call    [SetWindowTheme]

    ; Force non-client frame update to apply dark title bar immediately
    mov     rcx, [_pyfasm_h_wnd]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 27h   ; SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
    call    [SetWindowPos]

    ; ShowWindow, UpdateWindow & SetForegroundWindow
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 5                  ; SW_SHOW
    call    [ShowWindow]

    mov     rcx, [_pyfasm_h_wnd]
    call    [UpdateWindow]

    mov     rcx, [_pyfasm_h_wnd]
    call    [SetForegroundWindow]

    mov     rax, [_pyfasm_h_wnd]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ensure_window:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    cmp     qword [_pyfasm_h_wnd], 0
    jne     .window_already_exists
    xor     ecx, ecx
    xor     edx, edx
    xor     r8d, r8d
    call    _pyfasm_create_window
.window_already_exists:
    mov     rax, [_pyfasm_h_wnd]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_apply_font:
    ; RCX = control HWND
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     rax, [_pyfasm_h_font_ui]
    test    rax, rax
    jnz     .has_font
    mov     rax, [_pyfasm_h_font]
.has_font:
    test    rax, rax
    jz      .no_font
    mov     rdx, 30h                ; WM_SETFONT
    mov     r8, rax                 ; hFont
    mov     r9d, 1                  ; bRedraw = TRUE
    call    [SendMessageW]
.no_font:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_register_widget:
    ; RCX = hwnd, RDX = parent_hwnd, R8 = widget_type, R9 = req_w, [rbp+48] = req_h
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .reg_done

    test    rdx, rdx
    jnz     .reg_p_ok
    mov     rdx, [_pyfasm_h_wnd]
.reg_p_ok:
    mov     rax, [_pyfasm_layout_count]
    xor     ecx, ecx
.chk_loop:
    cmp     rcx, rax
    jge     .add_new
    mov     rdi, rcx
    shl     rdi, 6
    lea     rbx, [_pyfasm_layout_table + rdi]
    cmp     [rbx], rsi
    je      .update_existing
    inc     rcx
    jmp     .chk_loop

.add_new:
    cmp     rax, 256
    jge     .reg_done
    mov     rdi, rax
    shl     rdi, 6
    lea     rbx, [_pyfasm_layout_table + rdi]
    inc     qword [_pyfasm_layout_count]

    mov     [rbx + 0], rsi
    mov     [rbx + 8], rdx
    mov     dword [rbx + 16], r8d
    mov     dword [rbx + 20], 0
    mov     dword [rbx + 24], 0
    mov     dword [rbx + 28], 0
    mov     dword [rbx + 32], 0
    mov     dword [rbx + 36], 1
    mov     dword [rbx + 40], 1
    mov     dword [rbx + 44], 4
    mov     dword [rbx + 48], 4
    mov     dword [rbx + 52], r9d
    mov     eax, dword [rbp + 48]
    mov     dword [rbx + 56], eax
    mov     dword [rbx + 60], 0

    lea     rax, [_pyfasm_widget_aux + rdi]
    mov     qword [rax + 0], 0
    mov     dword [rax + 8], -1
    mov     dword [rax + 12], -1
    mov     qword [rax + 16], 0
    mov     qword [rax + 24], 0
    mov     qword [rax + 32], 0
    mov     qword [rax + 40], 0
    mov     qword [rax + 48], 0
    mov     qword [rax + 56], 0
    jmp     .reg_done

.update_existing:
    mov     [rbx + 8], rdx
    mov     dword [rbx + 16], r8d
    mov     dword [rbx + 52], r9d
    mov     eax, dword [rbp + 48]
    mov     dword [rbx + 56], eax

.reg_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_set_grid:
    ; RCX = widget HWND, RDX = row, R8 = col, R9 = sticky
    ; [rbp+48] = padx, [rbp+56] = pady, [rbp+64] = colspan, [rbp+72] = rowspan
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jz      .grid_done

    mov     rax, [_pyfasm_layout_count]
    xor     r10d, r10d
.grid_find:
    cmp     r10, rax
    jge     .grid_not_found
    mov     r11, r10
    shl     r11, 6
    lea     rbx, [_pyfasm_layout_table + r11]
    cmp     [rbx], rcx
    je      .grid_found
    inc     r10
    jmp     .grid_find

.grid_not_found:
    cmp     rax, 256
    jge     .grid_done
    mov     r11, rax
    shl     r11, 6
    lea     rbx, [_pyfasm_layout_table + r11]
    inc     qword [_pyfasm_layout_count]
    mov     [rbx], rcx
    mov     r10, [_pyfasm_h_wnd]
    mov     [rbx + 8], r10
    mov     dword [rbx + 16], 0
    mov     dword [rbx + 52], 0
    mov     dword [rbx + 56], 0
    mov     dword [rbx + 60], 0
    lea     r10, [_pyfasm_widget_aux + r11]
    mov     qword [r10 + 0], 0
    mov     dword [r10 + 8], -1
    mov     dword [r10 + 12], -1
    mov     qword [r10 + 16], 0
    mov     qword [r10 + 24], 0
    mov     qword [r10 + 32], 0
    mov     qword [r10 + 40], 0
    mov     qword [r10 + 48], 0
    mov     qword [r10 + 56], 0

.grid_found:
    mov     dword [rbx + 20], 1
    mov     dword [rbx + 24], edx
    mov     dword [rbx + 28], r8d
    mov     dword [rbx + 32], r9d
    mov     eax, dword [rbp + 48]
    mov     dword [rbx + 44], eax
    mov     eax, dword [rbp + 56]
    mov     dword [rbx + 48], eax
    mov     eax, dword [rbp + 64]
    test    eax, eax
    jnz     .grid_cs_ok
    mov     eax, 1
.grid_cs_ok:
    mov     dword [rbx + 36], eax
    mov     eax, dword [rbp + 72]
    test    eax, eax
    jnz     .grid_rs_ok
    mov     eax, 1
.grid_rs_ok:
    mov     dword [rbx + 40], eax

.grid_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_grid_columnconfigure:
    ; RCX = container HWND, RDX = col index, R8 = weight, R9 = minsize
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jnz     .gcc_c_ok
    mov     rcx, [_pyfasm_h_wnd]
.gcc_c_ok:
    cmp     rdx, 32
    jae     .gcc_done
    mov     r12, rcx

    mov     rax, [_pyfasm_container_cfg_count]
    xor     r10d, r10d
.gcc_find:
    cmp     r10, rax
    jge     .gcc_new
    mov     r11, r10
    imul    r11, 272
    lea     rbx, [_pyfasm_container_cfg_table + r11]
    cmp     [rbx], r12
    je      .gcc_set
    inc     r10
    jmp     .gcc_find

.gcc_new:
    cmp     rax, 32
    jge     .gcc_done
    mov     r10, rax
    mov     r11, r10
    imul    r11, 272
    lea     rbx, [_pyfasm_container_cfg_table + r11]
    inc     qword [_pyfasm_container_cfg_count]
    push    rdi
    mov     rdi, rbx
    xor     eax, eax
    mov     ecx, 34
    rep     stosq
    lea     rdi, [_pyfasm_container_min_table + r11]
    mov     ecx, 34
    rep     stosq
    pop     rdi
    mov     [rbx], r12
    lea     rax, [_pyfasm_container_min_table + r11]
    mov     [rax], r12

.gcc_set:
    mov     dword [rbx + 8 + rdx*4], r8d
    imul    r11, r10, 272
    lea     rax, [_pyfasm_container_min_table + r11]
    mov     [rax], r12
    mov     dword [rax + 8 + rdx*4], r9d

.gcc_done:
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_grid_rowconfigure:
    ; RCX = container HWND, RDX = row index, R8 = weight, R9 = minsize
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jnz     .grc_c_ok
    mov     rcx, [_pyfasm_h_wnd]
.grc_c_ok:
    cmp     rdx, 32
    jae     .grc_done
    mov     r12, rcx

    mov     rax, [_pyfasm_container_cfg_count]
    xor     r10d, r10d
.grc_find:
    cmp     r10, rax
    jge     .grc_new
    mov     r11, r10
    imul    r11, 272
    lea     rbx, [_pyfasm_container_cfg_table + r11]
    cmp     [rbx], r12
    je      .grc_set
    inc     r10
    jmp     .grc_find

.grc_new:
    cmp     rax, 32
    jge     .grc_done
    mov     r10, rax
    mov     r11, r10
    imul    r11, 272
    lea     rbx, [_pyfasm_container_cfg_table + r11]
    inc     qword [_pyfasm_container_cfg_count]
    push    rdi
    mov     rdi, rbx
    xor     eax, eax
    mov     ecx, 34
    rep     stosq
    lea     rdi, [_pyfasm_container_min_table + r11]
    mov     ecx, 34
    rep     stosq
    pop     rdi
    mov     [rbx], r12
    lea     rax, [_pyfasm_container_min_table + r11]
    mov     [rax], r12

.grc_set:
    mov     dword [rbx + 136 + rdx*4], r8d
    imul    r11, r10, 272
    lea     rax, [_pyfasm_container_min_table + r11]
    mov     [rax], r12
    mov     dword [rax + 136 + rdx*4], r9d

.grc_done:
    lea     rsp, [rbp - 16]
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_set_pack:
    ; RCX = widget HWND, RDX = side, R8 = fill, R9 = expand, [rbp+48] = padx, [rbp+56] = pady
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jz      .pack_done

    mov     rax, [_pyfasm_layout_count]
    xor     r10d, r10d
.pack_find:
    cmp     r10, rax
    jge     .pack_not_found
    mov     r11, r10
    shl     r11, 6
    lea     rbx, [_pyfasm_layout_table + r11]
    cmp     [rbx], rcx
    je      .pack_found
    inc     r10
    jmp     .pack_find

.pack_not_found:
    cmp     rax, 256
    jge     .pack_done
    mov     r11, rax
    shl     r11, 6
    lea     rbx, [_pyfasm_layout_table + r11]
    inc     qword [_pyfasm_layout_count]
    mov     [rbx], rcx
    mov     r10, [_pyfasm_h_wnd]
    mov     [rbx + 8], r10
    mov     dword [rbx + 16], 0
    mov     dword [rbx + 36], 1
    mov     dword [rbx + 40], 1
    mov     dword [rbx + 52], 0
    mov     dword [rbx + 56], 0
    mov     dword [rbx + 60], 0
    lea     r10, [_pyfasm_widget_aux + r11]
    mov     qword [r10 + 0], 0
    mov     dword [r10 + 8], -1
    mov     dword [r10 + 12], -1
    mov     qword [r10 + 16], 0
    mov     qword [r10 + 24], 0
    mov     qword [r10 + 32], 0
    mov     qword [r10 + 40], 0
    mov     qword [r10 + 48], 0
    mov     qword [r10 + 56], 0

.pack_found:
    mov     dword [rbx + 20], 2
    mov     dword [rbx + 24], edx
    mov     dword [rbx + 28], r8d
    mov     dword [rbx + 32], r9d
    mov     eax, dword [rbp + 48]
    mov     dword [rbx + 44], eax
    mov     eax, dword [rbp + 56]
    mov     dword [rbx + 48], eax

.pack_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_set_place:
    ; RCX = widget HWND, RDX = x, R8 = y, R9 = width, [rbp+48] = height
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jz      .place_done

    mov     rax, [_pyfasm_layout_count]
    xor     r10d, r10d
.place_find:
    cmp     r10, rax
    jge     .place_done
    mov     r11, r10
    shl     r11, 6
    lea     rbx, [_pyfasm_layout_table + r11]
    cmp     [rbx], rcx
    je      .place_found
    inc     r10
    jmp     .place_find

.place_found:
    mov     dword [rbx + 20], 3
    mov     dword [rbx + 24], edx
    mov     dword [rbx + 28], r8d
    mov     dword [rbx + 52], r9d
    mov     eax, dword [rbp + 48]
    mov     dword [rbx + 56], eax

.place_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_unpack_pad:
    ; ECX = packed_pad -> RAX = (p2 << 32) | p1
    mov     eax, ecx
    test    eax, 80000000h
    jnz     .up_asym
    test    eax, eax
    jns     .up_sym
    xor     eax, eax
.up_sym:
    mov     edx, eax
    shl     rdx, 32
    or      rax, rdx
    ret
.up_asym:
    mov     edx, eax
    and     eax, 7FFFh
    shr     edx, 15
    and     edx, 7FFFh
    shl     rdx, 32
    or      rax, rdx
    ret

_pyfasm_measure_frame_natural:
    ; RCX = frame_hwnd, RDX = recursion depth (0..6) -> RAX = (h << 32) | w
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 400
    and     rsp, -16

    mov     r12, rcx
    mov     r13, rdx
    cmp     r13, 6
    jl      .mfn_start
    mov     rax, (40 shl 32) or 40
    jmp     .mfn_done

.mfn_start:
    lea     rdi, [rsp + 64]
    xor     eax, eax
    mov     ecx, 32
    rep     stosq
    mov     dword [rsp + 320], 0
    mov     dword [rsp + 324], 0
    mov     dword [rsp + 328], 0
    mov     dword [rsp + 332], 0
    mov     dword [rsp + 336], 0
    mov     dword [rsp + 340], 0

    mov     r14, [_pyfasm_layout_count]
    xor     r15d, r15d
.mfn_loop:
    cmp     r15, r14
    jge     .mfn_reduce
    mov     rax, r15
    shl     rax, 6
    lea     rbx, [_pyfasm_layout_table + rax]
    cmp     [rbx + 8], r12
    jne     .mfn_next
    cmp     [rbx], r12
    je      .mfn_next

    cmp     dword [rbx + 16], 2
    jne     .mfn_not_subframe
    mov     eax, [rbx + 52]
    mov     edx, [rbx + 56]
    test    eax, eax
    jle     .mfn_sub_nat
    test    edx, edx
    jle     .mfn_sub_nat
    shl     rdx, 32
    or      rax, rdx
    jmp     .mfn_got_wh
.mfn_sub_nat:
    mov     rcx, [rbx]
    lea     rdx, [r13 + 1]
    call    _pyfasm_measure_frame_natural
    mov     edx, eax
    mov     rcx, rax
    shr     rcx, 32
    cmp     dword [rbx + 52], 0
    jle     .mfn_sf_w_ok
    mov     edx, [rbx + 52]
.mfn_sf_w_ok:
    cmp     dword [rbx + 56], 0
    jle     .mfn_sf_h_ok
    mov     ecx, [rbx + 56]
.mfn_sf_h_ok:
    mov     eax, edx
    shl     rcx, 32
    or      rax, rcx
    jmp     .mfn_got_wh

.mfn_not_subframe:
    mov     rcx, rbx
    call    _pyfasm_measure_widget

.mfn_got_wh:
    mov     rsi, rax
    mov     ecx, [rbx + 44]
    call    _pyfasm_unpack_pad
    mov     edx, eax
    shr     rax, 32
    add     edx, eax
    mov     edi, esi
    add     edi, edx

    mov     ecx, [rbx + 48]
    call    _pyfasm_unpack_pad
    mov     edx, eax
    shr     rax, 32
    add     edx, eax
    shr     rsi, 32
    add     esi, edx

    mov     eax, [rbx + 20]
    cmp     eax, 1
    je      .mfn_grid
    cmp     eax, 2
    je      .mfn_pack
    cmp     eax, 3
    je      .mfn_next
    add     [rsp + 328], esi
    add     dword [rsp + 328], 8
    cmp     edi, [rsp + 332]
    jle     .mfn_next
    mov     [rsp + 332], edi
    jmp     .mfn_next

.mfn_pack:
    mov     eax, [rbx + 24]
    cmp     eax, 1
    ja      .mfn_pack_lr
    add     [rsp + 328], esi
    cmp     edi, [rsp + 332]
    jle     .mfn_next
    mov     [rsp + 332], edi
    jmp     .mfn_next
.mfn_pack_lr:
    add     [rsp + 336], edi
    cmp     esi, [rsp + 340]
    jle     .mfn_next
    mov     [rsp + 340], esi
    jmp     .mfn_next

.mfn_grid:
    mov     eax, [rbx + 24]
    mov     ecx, [rbx + 28]
    cmp     eax, 31
    ja      .mfn_next
    cmp     ecx, 31
    ja      .mfn_next
    mov     edx, [rbx + 36]
    test    edx, edx
    jg      .mfn_cs_ok
    mov     edx, 1
.mfn_cs_ok:
    add     edx, ecx
    cmp     edx, 32
    jle     .mfn_mc_clamp
    mov     edx, 32
.mfn_mc_clamp:
    cmp     edx, [rsp + 320]
    jle     .mfn_mc_ok
    mov     [rsp + 320], edx
.mfn_mc_ok:
    mov     r8d, [rbx + 40]
    test    r8d, r8d
    jg      .mfn_rs_ok
    mov     r8d, 1
.mfn_rs_ok:
    add     r8d, eax
    cmp     r8d, 32
    jle     .mfn_mr_clamp
    mov     r8d, 32
.mfn_mr_clamp:
    cmp     r8d, [rsp + 324]
    jle     .mfn_mr_ok
    mov     [rsp + 324], r8d
.mfn_mr_ok:
    cmp     dword [rbx + 36], 1
    jg      .mfn_g_rcheck
    cmp     edi, [rsp + 64 + rcx*4]
    jle     .mfn_g_rcheck
    mov     [rsp + 64 + rcx*4], edi
.mfn_g_rcheck:
    cmp     dword [rbx + 40], 1
    jg      .mfn_next
    cmp     esi, [rsp + 192 + rax*4]
    jle     .mfn_next
    mov     [rsp + 192 + rax*4], esi

.mfn_next:
    inc     r15
    jmp     .mfn_loop

.mfn_reduce:
    xor     r8d, r8d
    xor     ecx, ecx
    mov     edx, [rsp + 320]
.mfn_sum_w:
    cmp     ecx, edx
    jge     .mfn_sum_w_done
    add     r8d, [rsp + 64 + rcx*4]
    inc     ecx
    jmp     .mfn_sum_w
.mfn_sum_w_done:
    xor     r9d, r9d
    xor     ecx, ecx
    mov     edx, [rsp + 324]
.mfn_sum_h:
    cmp     ecx, edx
    jge     .mfn_sum_h_done
    add     r9d, [rsp + 192 + rcx*4]
    inc     ecx
    jmp     .mfn_sum_h
.mfn_sum_h_done:
    mov     eax, [rsp + 332]
    add     eax, [rsp + 336]
    cmp     eax, r8d
    jge     .mfn_w_fin
    mov     eax, r8d
.mfn_w_fin:
    cmp     eax, 32
    jge     .mfn_w_min
    mov     eax, 32
.mfn_w_min:
    mov     ecx, [rsp + 340]
    mov     edx, [rsp + 328]
    cmp     ecx, edx
    jge     .mfn_h_cmp
    mov     ecx, edx
.mfn_h_cmp:
    cmp     ecx, r9d
    jge     .mfn_h_fin
    mov     ecx, r9d
.mfn_h_fin:
    cmp     ecx, 32
    jge     .mfn_h_min
    mov     ecx, 32
.mfn_h_min:
    mov     eax, eax
    shl     rcx, 32
    or      rax, rcx

.mfn_done:
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

_pyfasm_measure_widget:
    ; RCX = layout_entry_ptr -> RAX = (h << 32) | w
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 96
    and     rsp, -16

    mov     rbx, rcx
    mov     rsi, [rbx + 0]
    mov     edi, [rbx + 16]
    mov     r12d, [rbx + 52]

    cmp     edi, 2
    jne     .mw_not_frame
    mov     edx, [rbx + 56]
    test    byte [rbx + 60], 1
    jnz     .mw_frame_expl
    test    r12d, r12d
    jle     .mw_frame_nat
    test    edx, edx
    jle     .mw_frame_nat
.mw_frame_expl:
    test    r12d, r12d
    jg      .mw_fe_w
    mov     r12d, 120
.mw_fe_w:
    test    edx, edx
    jg      .mw_fe_h
    mov     edx, 40
.mw_fe_h:
    mov     eax, r12d
    shl     rdx, 32
    or      rax, rdx
    jmp     .mw_done
.mw_frame_nat:
    mov     rcx, rsi
    xor     edx, edx
    call    _pyfasm_measure_frame_natural
    mov     ecx, eax
    mov     rdx, rax
    shr     rdx, 32
    cmp     r12d, 0
    jle     .mw_fn_w
    mov     ecx, r12d
.mw_fn_w:
    cmp     dword [rbx + 56], 0
    jle     .mw_fn_h
    mov     edx, [rbx + 56]
.mw_fn_h:
    mov     eax, ecx
    shl     rdx, 32
    or      rax, rdx
    jmp     .mw_done

.mw_not_frame:
    cmp     edi, 0
    je      .mw_measure_text
    cmp     edi, 3
    je      .mw_measure_text
    cmp     edi, 4
    je      .mw_measure_text

    mov     eax, r12d
    mov     edx, [rbx + 56]
    cmp     edi, 1
    jne     .mw_chk5
    test    eax, eax
    jg      .mw_e_h
    mov     eax, 180
.mw_e_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 32
    jmp     .mw_pack_ret
.mw_chk5:
    cmp     edi, 5
    jne     .mw_chk6
    test    eax, eax
    jg      .mw_l_h
    mov     eax, 280
.mw_l_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 180
    jmp     .mw_pack_ret
.mw_chk6:
    cmp     edi, 6
    jne     .mw_chk7
    test    eax, eax
    jg      .mw_c_h
    mov     eax, 480
.mw_c_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 360
    jmp     .mw_pack_ret
.mw_chk7:
    cmp     edi, 7
    jne     .mw_chk9
    test    eax, eax
    jg      .mw_t_h
    mov     eax, 300
.mw_t_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 140
    jmp     .mw_pack_ret
.mw_chk9:
    cmp     edi, 9
    jne     .mw_chk10
    test    eax, eax
    jg      .mw_cb_h
    mov     eax, 180
.mw_cb_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 32
    jmp     .mw_pack_ret
.mw_chk10:
    cmp     edi, 10
    jne     .mw_chk11
    test    eax, eax
    jg      .mw_s_h
    mov     eax, 180
.mw_s_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 28
    jmp     .mw_pack_ret
.mw_chk11:
    test    eax, eax
    jg      .mw_d_h
    mov     eax, 160
.mw_d_h:
    test    edx, edx
    jg      .mw_pack_ret
    mov     edx, 24
    jmp     .mw_pack_ret

.mw_measure_text:
    mov     dword [rsp + 48], 0
    mov     dword [rsp + 52], 0
    mov     dword [rsp + 56], 0
    mov     dword [rsp + 60], 0
    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    [GetWindowTextW]
    mov     r8d, eax
    mov     dword [rsp + 64], 40
    mov     dword [rsp + 68], 20
    test    r8d, r8d
    jle     .mw_txt_apply_pad

    mov     [rsp + 72], r8d
    mov     rcx, rsi
    call    [GetDC]
    test    rax, rax
    jz      .mw_txt_apply_pad
    mov     [rsp + 80], rax

    mov     rcx, rbx
    sub     rcx, _pyfasm_layout_table
    lea     rdx, [_pyfasm_widget_aux + rcx]
    mov     rdx, [rdx + 32]
    test    rdx, rdx
    jnz     .mw_sel_font
    mov     rdx, [_pyfasm_h_font_ui]
.mw_sel_font:
    test    rdx, rdx
    jz      .mw_do_dt
    mov     rcx, [rsp + 80]
    call    [SelectObject]
    mov     [rsp + 88], rax
    jmp     .mw_dt_call
.mw_do_dt:
    mov     qword [rsp + 88], 0
.mw_dt_call:
    mov     rcx, [rsp + 80]
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, [rsp + 72]
    lea     r9, [rsp + 48]
    mov     qword [rsp + 32], 400h
    call    [DrawTextW]
    mov     rdx, [rsp + 88]
    test    rdx, rdx
    jz      .mw_rel_dc
    mov     rcx, [rsp + 80]
    call    [SelectObject]
.mw_rel_dc:
    mov     rcx, rsi
    mov     rdx, [rsp + 80]
    call    [ReleaseDC]
    mov     eax, [rsp + 56]
    mov     edx, [rsp + 60]
    cmp     eax, 8
    jge     .mw_rw_ok
    mov     eax, 8
.mw_rw_ok:
    cmp     edx, 14
    jge     .mw_rh_ok
    mov     edx, 14
.mw_rh_ok:
    mov     [rsp + 64], eax
    mov     [rsp + 68], edx

.mw_txt_apply_pad:
    mov     eax, [rsp + 64]
    mov     edx, [rsp + 68]
    cmp     edi, 0
    jne     .mw_tp_btn
    add     eax, 12
    add     edx, 8
    cmp     r12d, 0
    jle     .mw_lbl_h
    mov     eax, r12d
.mw_lbl_h:
    cmp     dword [rbx + 56], 0
    jle     .mw_pack_ret
    mov     edx, [rbx + 56]
    jmp     .mw_pack_ret

.mw_tp_btn:
    cmp     edi, 3
    jne     .mw_tp_chk
    add     eax, 26
    cmp     eax, r12d
    jge     .mw_btn_wmin
    mov     eax, r12d
.mw_btn_wmin:
    cmp     eax, 60
    jge     .mw_btn_h
    mov     eax, 60
.mw_btn_h:
    add     edx, 14
    cmp     edx, [rbx + 56]
    jge     .mw_btn_hmin
    mov     edx, [rbx + 56]
.mw_btn_hmin:
    cmp     edx, 30
    jge     .mw_pack_ret
    mov     edx, 30
    jmp     .mw_pack_ret

.mw_tp_chk:
    add     eax, 34
    cmp     eax, r12d
    jge     .mw_chk_wmin
    mov     eax, r12d
.mw_chk_wmin:
    cmp     eax, 80
    jge     .mw_chk_h
    mov     eax, 80
.mw_chk_h:
    add     edx, 8
    cmp     edx, [rbx + 56]
    jge     .mw_chk_hmin
    mov     edx, [rbx + 56]
.mw_chk_hmin:
    cmp     edx, 24
    jge     .mw_pack_ret
    mov     edx, 24

.mw_pack_ret:
    mov     eax, eax
    shl     rdx, 32
    or      rax, rdx

.mw_done:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_apply_layout:
    ; RCX = container HWND (if 0, uses [_pyfasm_h_wnd])
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 960
    and     rsp, -16

    test    rcx, rcx
    jnz     .al_c_ok
    mov     rcx, [_pyfasm_h_wnd]
.al_c_ok:
    mov     r12, rcx
    test    r12, r12
    jz      .al_exit

    mov     r13, [_pyfasm_layout_count]
    test    r13, r13
    jz      .al_exit

    mov     rcx, r12
    lea     rdx, [rsp + 64]
    call    [GetClientRect]
    mov     eax, [rsp + 72]
    sub     eax, [rsp + 64]
    cmp     eax, 16
    jge     .al_cw_ok
    mov     eax, 800
.al_cw_ok:
    mov     [rsp + 80], eax
    mov     edx, [rsp + 76]
    sub     edx, [rsp + 68]
    cmp     edx, 16
    jge     .al_ch_ok
    mov     edx, 600
.al_ch_ok:
    mov     [rsp + 84], edx

    mov     qword [rsp + 88], 0
    mov     qword [rsp + 96], 0
    mov     rax, [_pyfasm_container_cfg_count]
    xor     ecx, ecx
.al_find_cfg:
    cmp     rcx, rax
    jge     .al_cfg_done
    mov     r10, rcx
    imul    r10, 272
    lea     rdx, [_pyfasm_container_cfg_table + r10]
    cmp     [rdx], r12
    jne     .al_find_cfg_next
    mov     [rsp + 88], rdx
    lea     rdx, [_pyfasm_container_min_table + r10]
    mov     [rsp + 96], rdx
    jmp     .al_cfg_done
.al_find_cfg_next:
    inc     rcx
    jmp     .al_find_cfg
.al_cfg_done:

    lea     rdi, [rsp + 160]
    xor     eax, eax
    mov     ecx, 64
    rep     stosq

    mov     dword [rsp + 104], 0
    mov     dword [rsp + 108], 0
    mov     dword [rsp + 128], 0
    mov     dword [rsp + 132], 0
    mov     dword [rsp + 144], 0
    mov     dword [rsp + 148], 0
    mov     dword [rsp + 152], 0
    mov     dword [rsp + 156], 0

    xor     r14d, r14d
.al_p1_loop:
    cmp     r14, r13
    jge     .al_p1_done
    mov     rax, r14
    shl     rax, 6
    lea     rbx, [_pyfasm_layout_table + rax]
    cmp     [rbx + 8], r12
    jne     .al_p1_next
    cmp     [rbx], r12
    je      .al_p1_next

    mov     rcx, rbx
    call    _pyfasm_measure_widget
    mov     rsi, rax
    mov     ecx, [rbx + 44]
    call    _pyfasm_unpack_pad
    mov     edx, eax
    shr     rax, 32
    add     edx, eax
    mov     edi, esi
    add     edi, edx

    mov     ecx, [rbx + 48]
    call    _pyfasm_unpack_pad
    mov     edx, eax
    shr     rax, 32
    add     edx, eax
    shr     rsi, 32
    add     esi, edx

    mov     eax, [rbx + 20]
    cmp     eax, 1
    je      .al_p1_grid
    cmp     eax, 2
    je      .al_p1_pack
    jmp     .al_p1_next

.al_p1_pack:
    mov     dword [rsp + 132], 1
    mov     eax, [rbx + 24]
    cmp     eax, 1
    ja      .al_p1_pack_lr
    add     [rsp + 152], esi
    cmp     dword [rbx + 32], 0
    je      .al_p1_next
    inc     dword [rsp + 144]
    jmp     .al_p1_next
.al_p1_pack_lr:
    add     [rsp + 156], edi
    cmp     dword [rbx + 32], 0
    je      .al_p1_next
    inc     dword [rsp + 148]
    jmp     .al_p1_next

.al_p1_grid:
    mov     dword [rsp + 128], 1
    mov     eax, [rbx + 24]
    mov     ecx, [rbx + 28]
    cmp     eax, 31
    ja      .al_p1_next
    cmp     ecx, 31
    ja      .al_p1_next
    mov     edx, [rbx + 36]
    test    edx, edx
    jg      .al_p1_cs
    mov     edx, 1
.al_p1_cs:
    mov     r8d, ecx
    add     r8d, edx
    cmp     r8d, 32
    jle     .al_p1_mc
    mov     r8d, 32
.al_p1_mc:
    cmp     r8d, [rsp + 104]
    jle     .al_p1_mc2
    mov     [rsp + 104], r8d
.al_p1_mc2:
    mov     r9d, [rbx + 40]
    test    r9d, r9d
    jg      .al_p1_rs
    mov     r9d, 1
.al_p1_rs:
    mov     r8d, eax
    add     r8d, r9d
    cmp     r8d, 32
    jle     .al_p1_mr
    mov     r8d, 32
.al_p1_mr:
    cmp     r8d, [rsp + 108]
    jle     .al_p1_mr2
    mov     [rsp + 108], r8d
.al_p1_mr2:
    cmp     edx, 1
    jg      .al_p1_chk_r1
    cmp     edi, [rsp + 160 + rcx*4]
    jle     .al_p1_chk_r1
    mov     [rsp + 160 + rcx*4], edi
.al_p1_chk_r1:
    cmp     r9d, 1
    jg      .al_p1_next
    cmp     esi, [rsp + 288 + rax*4]
    jle     .al_p1_next
    mov     [rsp + 288 + rax*4], esi

.al_p1_next:
    inc     r14
    jmp     .al_p1_loop
.al_p1_done:

    cmp     dword [rsp + 128], 0
    je      .al_grid_solved
    xor     r14d, r14d
.al_p1b_loop:
    cmp     r14, r13
    jge     .al_p1b_done
    mov     rax, r14
    shl     rax, 6
    lea     rbx, [_pyfasm_layout_table + rax]
    cmp     [rbx + 8], r12
    jne     .al_p1b_next
    cmp     [rbx], r12
    je      .al_p1b_next
    cmp     dword [rbx + 20], 1
    jne     .al_p1b_next
    cmp     dword [rbx + 36], 1
    jg      .al_p1b_do
    cmp     dword [rbx + 40], 1
    jle     .al_p1b_next
.al_p1b_do:
    mov     rcx, rbx
    call    _pyfasm_measure_widget
    mov     rsi, rax
    mov     ecx, [rbx + 44]
    call    _pyfasm_unpack_pad
    mov     edx, eax
    shr     rax, 32
    add     edx, eax
    mov     edi, esi
    add     edi, edx
    mov     ecx, [rbx + 48]
    call    _pyfasm_unpack_pad
    mov     edx, eax
    shr     rax, 32
    add     edx, eax
    shr     rsi, 32
    add     esi, edx

    mov     ecx, [rbx + 28]
    mov     edx, [rbx + 36]
    cmp     edx, 1
    jle     .al_p1b_row
    cmp     ecx, 31
    ja      .al_p1b_row
    mov     r8d, ecx
    add     r8d, edx
    cmp     r8d, 32
    jle     .al_p1b_cs_c
    mov     r8d, 32
.al_p1b_cs_c:
    xor     eax, eax
    mov     r9d, ecx
.al_p1b_cs_sum:
    cmp     r9d, r8d
    jge     .al_p1b_cs_chk
    add     eax, [rsp + 160 + r9*4]
    inc     r9d
    jmp     .al_p1b_cs_sum
.al_p1b_cs_chk:
    sub     edi, eax
    jle     .al_p1b_row
    dec     r8d
    add     [rsp + 160 + r8*4], edi
.al_p1b_row:
    mov     ecx, [rbx + 24]
    mov     edx, [rbx + 40]
    cmp     edx, 1
    jle     .al_p1b_next
    cmp     ecx, 31
    ja      .al_p1b_next
    mov     r8d, ecx
    add     r8d, edx
    cmp     r8d, 32
    jle     .al_p1b_rs_c
    mov     r8d, 32
.al_p1b_rs_c:
    xor     eax, eax
    mov     r9d, ecx
.al_p1b_rs_sum:
    cmp     r9d, r8d
    jge     .al_p1b_rs_chk
    add     eax, [rsp + 288 + r9*4]
    inc     r9d
    jmp     .al_p1b_rs_sum
.al_p1b_rs_chk:
    sub     esi, eax
    jle     .al_p1b_next
    dec     r8d
    add     [rsp + 288 + r8*4], esi
.al_p1b_next:
    inc     r14
    jmp     .al_p1b_loop
.al_p1b_done:

    mov     r10, [rsp + 96]
    test    r10, r10
    jz      .al_min_done
    xor     ecx, ecx
    mov     edx, [rsp + 104]
.al_min_c:
    cmp     ecx, edx
    jge     .al_min_r_init
    mov     eax, [r10 + 8 + rcx*4]
    cmp     eax, [rsp + 160 + rcx*4]
    jle     .al_min_cn
    mov     [rsp + 160 + rcx*4], eax
.al_min_cn:
    inc     ecx
    jmp     .al_min_c
.al_min_r_init:
    xor     ecx, ecx
    mov     edx, [rsp + 108]
.al_min_r:
    cmp     ecx, edx
    jge     .al_min_done
    mov     eax, [r10 + 136 + rcx*4]
    cmp     eax, [rsp + 288 + rcx*4]
    jle     .al_min_rn
    mov     [rsp + 288 + rcx*4], eax
.al_min_rn:
    inc     ecx
    jmp     .al_min_r
.al_min_done:

    mov     rsi, [rsp + 88]
    test    rsi, rsi
    jz      .al_pos_calc
    xor     r8d, r8d
    xor     r9d, r9d
    mov     r11d, -1
    xor     ecx, ecx
    mov     edx, [rsp + 104]
.al_cw_sum:
    cmp     ecx, edx
    jge     .al_cw_dist
    add     r8d, [rsp + 160 + rcx*4]
    mov     eax, [rsi + 8 + rcx*4]
    test    eax, eax
    jle     .al_cw_sn
    add     r9d, eax
    mov     r11d, ecx
.al_cw_sn:
    inc     ecx
    jmp     .al_cw_sum
.al_cw_dist:
    test    r9d, r9d
    jle     .al_rh_prep
    mov     edi, [rsp + 80]
    sub     edi, r8d
    xor     r10d, r10d
    xor     ecx, ecx
    mov     r14d, [rsp + 104]
.al_cw_apply:
    cmp     ecx, r14d
    jge     .al_cw_rem
    mov     r8d, [rsi + 8 + rcx*4]
    test    r8d, r8d
    jle     .al_cw_an
    mov     eax, edi
    imul    eax, r8d
    cdq
    idiv    r9d
    add     r10d, eax
    add     [rsp + 160 + rcx*4], eax
    cmp     dword [rsp + 160 + rcx*4], 16
    jge     .al_cw_an
    mov     dword [rsp + 160 + rcx*4], 16
.al_cw_an:
    inc     ecx
    jmp     .al_cw_apply
.al_cw_rem:
    cmp     r11d, 0
    jl      .al_rh_prep
    sub     edi, r10d
    add     [rsp + 160 + r11*4], edi
    cmp     dword [rsp + 160 + r11*4], 16
    jge     .al_rh_prep
    mov     dword [rsp + 160 + r11*4], 16

.al_rh_prep:
    xor     r8d, r8d
    xor     r9d, r9d
    mov     r11d, -1
    xor     ecx, ecx
    mov     edx, [rsp + 108]
.al_rh_sum:
    cmp     ecx, edx
    jge     .al_rh_dist
    add     r8d, [rsp + 288 + rcx*4]
    mov     eax, [rsi + 136 + rcx*4]
    test    eax, eax
    jle     .al_rh_sn
    add     r9d, eax
    mov     r11d, ecx
.al_rh_sn:
    inc     ecx
    jmp     .al_rh_sum
.al_rh_dist:
    test    r9d, r9d
    jle     .al_pos_calc
    mov     edi, [rsp + 84]
    sub     edi, r8d
    xor     r10d, r10d
    xor     ecx, ecx
    mov     r14d, [rsp + 108]
.al_rh_apply:
    cmp     ecx, r14d
    jge     .al_rh_rem
    mov     r8d, [rsi + 136 + rcx*4]
    test    r8d, r8d
    jle     .al_rh_an
    mov     eax, edi
    imul    eax, r8d
    cdq
    idiv    r9d
    add     r10d, eax
    add     [rsp + 288 + rcx*4], eax
    cmp     dword [rsp + 288 + rcx*4], 16
    jge     .al_rh_an
    mov     dword [rsp + 288 + rcx*4], 16
.al_rh_an:
    inc     ecx
    jmp     .al_rh_apply
.al_rh_rem:
    cmp     r11d, 0
    jl      .al_pos_calc
    sub     edi, r10d
    add     [rsp + 288 + r11*4], edi
    cmp     dword [rsp + 288 + r11*4], 16
    jge     .al_pos_calc
    mov     dword [rsp + 288 + r11*4], 16

.al_pos_calc:
    xor     eax, eax
    xor     ecx, ecx
    mov     edx, [rsp + 104]
.al_cp_loop:
    cmp     ecx, edx
    jge     .al_rp_init
    mov     [rsp + 416 + rcx*4], eax
    add     eax, [rsp + 160 + rcx*4]
    inc     ecx
    jmp     .al_cp_loop
.al_rp_init:
    xor     eax, eax
    xor     ecx, ecx
    mov     edx, [rsp + 108]
.al_rp_loop:
    cmp     ecx, edx
    jge     .al_grid_solved
    mov     [rsp + 544 + rcx*4], eax
    add     eax, [rsp + 288 + rcx*4]
    inc     ecx
    jmp     .al_rp_loop

.al_grid_solved:
    mov     dword [rsp + 112], 0
    mov     dword [rsp + 116], 0
    mov     eax, [rsp + 80]
    mov     [rsp + 120], eax
    mov     eax, [rsp + 84]
    mov     [rsp + 124], eax
    mov     dword [rsp + 136], 10
    mov     dword [rsp + 672], 0
    mov     dword [rsp + 676], 0
    mov     ecx, [rsp + 144]
    test    ecx, ecx
    jle     .al_pk_eh
    mov     eax, [rsp + 84]
    sub     eax, [rsp + 152]
    jle     .al_pk_eh
    cdq
    idiv    ecx
    mov     [rsp + 672], eax
.al_pk_eh:
    mov     ecx, [rsp + 148]
    test    ecx, ecx
    jle     .al_p2_start
    mov     eax, [rsp + 80]
    sub     eax, [rsp + 156]
    jle     .al_p2_start
    cdq
    idiv    ecx
    mov     [rsp + 676], eax

.al_p2_start:
    xor     r15d, r15d
.al_p2_loop:
    cmp     r15, r13
    jge     .al_recurse_start
    mov     rax, r15
    shl     rax, 6
    lea     rbx, [_pyfasm_layout_table + rax]
    cmp     [rbx + 8], r12
    jne     .al_p2_next
    cmp     [rbx], r12
    je      .al_p2_next

    mov     rcx, rbx
    call    _pyfasm_measure_widget
    mov     [rsp + 680], rax
    mov     ecx, [rbx + 44]
    call    _pyfasm_unpack_pad
    mov     [rsp + 688], rax
    mov     ecx, [rbx + 48]
    call    _pyfasm_unpack_pad
    mov     [rsp + 696], rax

    mov     eax, [rbx + 20]
    cmp     eax, 1
    je      .al_p2_grid
    cmp     eax, 2
    je      .al_p2_pack
    cmp     eax, 3
    je      .al_p2_place

    mov     ecx, [rsp + 680]
    mov     eax, [rsp + 80]
    sub     eax, 24
    cmp     eax, 40
    jge     .al_m0_wmax
    mov     eax, 40
.al_m0_wmax:
    cmp     ecx, eax
    jle     .al_m0_wok
    mov     ecx, eax
.al_m0_wok:
    mov     edx, [rsp + 684]
    mov     r8d, [rsp + 136]
    lea     eax, [r8d + edx + 8]
    mov     [rsp + 136], eax
    mov     dword [rsp + 704], 12
    mov     [rsp + 708], r8d
    mov     [rsp + 712], ecx
    mov     [rsp + 716], edx
    jmp     .al_do_move

.al_p2_place:
    mov     eax, [rbx + 24]
    mov     [rsp + 704], eax
    mov     eax, [rbx + 28]
    mov     [rsp + 708], eax
    mov     eax, [rbx + 52]
    test    eax, eax
    jg      .al_pl_w
    mov     eax, [rsp + 680]
.al_pl_w:
    mov     [rsp + 712], eax
    mov     eax, [rbx + 56]
    test    eax, eax
    jg      .al_pl_h
    mov     eax, [rsp + 684]
.al_pl_h:
    mov     [rsp + 716], eax
    jmp     .al_do_move

.al_p2_grid:
    mov     eax, [rbx + 24]
    mov     ecx, [rbx + 28]
    cmp     eax, 31
    ja      .al_p2_next
    cmp     ecx, 31
    ja      .al_p2_next
    mov     r8d, [rsp + 416 + rcx*4]
    mov     r9d, [rsp + 544 + rax*4]
    xor     r10d, r10d
    mov     edx, [rbx + 36]
    test    edx, edx
    jg      .al_g_cs1
    mov     edx, 1
.al_g_cs1:
    mov     edi, ecx
    add     edi, edx
    cmp     edi, 32
    jle     .al_g_cs2
    mov     edi, 32
.al_g_cs2:
    cmp     ecx, edi
    jge     .al_g_rs0
    add     r10d, [rsp + 160 + rcx*4]
    inc     ecx
    jmp     .al_g_cs2
.al_g_rs0:
    xor     r11d, r11d
    mov     edx, [rbx + 40]
    test    edx, edx
    jg      .al_g_rs1
    mov     edx, 1
.al_g_rs1:
    mov     edi, eax
    add     edi, edx
    cmp     edi, 32
    jle     .al_g_rs2
    mov     edi, 32
.al_g_rs2:
    cmp     eax, edi
    jge     .al_g_inner
    add     r11d, [rsp + 288 + rax*4]
    inc     eax
    jmp     .al_g_rs2

.al_g_inner:
    add     r8d, [rsp + 688]
    sub     r10d, [rsp + 688]
    sub     r10d, [rsp + 692]
    cmp     r10d, 1
    jge     .al_gi_w
    mov     r10d, 1
.al_gi_w:
    add     r9d, [rsp + 696]
    sub     r11d, [rsp + 696]
    sub     r11d, [rsp + 700]
    cmp     r11d, 1
    jge     .al_gi_h
    mov     r11d, 1
.al_gi_h:
    mov     edi, [rbx + 32]
    mov     eax, edi
    and     eax, 12
    cmp     eax, 12
    jne     .al_g_no_ew
    mov     [rsp + 704], r8d
    mov     [rsp + 712], r10d
    jmp     .al_g_vert
.al_g_no_ew:
    mov     edx, [rsp + 680]
    cmp     edx, r10d
    jle     .al_g_mw_ok
    mov     edx, r10d
.al_g_mw_ok:
    mov     [rsp + 712], edx
    test    edi, 8
    jz      .al_g_chk_e
    mov     [rsp + 704], r8d
    jmp     .al_g_vert
.al_g_chk_e:
    test    edi, 4
    jz      .al_g_ctr_x
    mov     eax, r8d
    add     eax, r10d
    sub     eax, edx
    mov     [rsp + 704], eax
    jmp     .al_g_vert
.al_g_ctr_x:
    mov     eax, r10d
    sub     eax, edx
    shr     eax, 1
    add     eax, r8d
    mov     [rsp + 704], eax

.al_g_vert:
    mov     eax, edi
    and     eax, 3
    cmp     eax, 3
    jne     .al_g_no_ns
    mov     [rsp + 708], r9d
    mov     [rsp + 716], r11d
    jmp     .al_do_move
.al_g_no_ns:
    mov     edx, [rsp + 684]
    cmp     edx, r11d
    jle     .al_g_mh_ok
    mov     edx, r11d
.al_g_mh_ok:
    mov     [rsp + 716], edx
    test    edi, 1
    jz      .al_g_chk_s
    mov     [rsp + 708], r9d
    jmp     .al_do_move
.al_g_chk_s:
    test    edi, 2
    jz      .al_g_ctr_y
    mov     eax, r9d
    add     eax, r11d
    sub     eax, edx
    mov     [rsp + 708], eax
    jmp     .al_do_move
.al_g_ctr_y:
    mov     eax, r11d
    sub     eax, edx
    shr     eax, 1
    add     eax, r9d
    mov     [rsp + 708], eax
    jmp     .al_do_move

.al_p2_pack:
    mov     eax, [rsp + 120]
    sub     eax, [rsp + 112]
    mov     edx, [rsp + 124]
    sub     edx, [rsp + 116]
    cmp     eax, 1
    jle     .al_p2_next
    cmp     edx, 1
    jle     .al_p2_next

    mov     ecx, [rbx + 24]
    cmp     ecx, 1
    ja      .al_pk_lr
    mov     r8d, [rsp + 684]
    add     r8d, [rsp + 696]
    add     r8d, [rsp + 700]
    cmp     dword [rbx + 32], 0
    je      .al_pk_tb_noexp
    add     r8d, [rsp + 672]
.al_pk_tb_noexp:
    cmp     r8d, edx
    jle     .al_pk_tb_h
    mov     r8d, edx
.al_pk_tb_h:
    mov     r9d, [rsp + 112]
    mov     r10d, eax
    mov     r11d, r8d
    test    ecx, ecx
    jnz     .al_pk_bot
    mov     eax, [rsp + 116]
    add     [rsp + 116], r11d
    jmp     .al_pk_inner
.al_pk_bot:
    mov     eax, [rsp + 124]
    sub     eax, r11d
    mov     [rsp + 124], eax
    jmp     .al_pk_inner

.al_pk_lr:
    mov     r8d, [rsp + 680]
    add     r8d, [rsp + 688]
    add     r8d, [rsp + 692]
    cmp     dword [rbx + 32], 0
    je      .al_pk_lr_noexp
    add     r8d, [rsp + 676]
.al_pk_lr_noexp:
    cmp     r8d, eax
    jle     .al_pk_lr_w
    mov     r8d, eax
.al_pk_lr_w:
    mov     eax, [rsp + 116]
    mov     r10d, r8d
    mov     r11d, edx
    cmp     ecx, 2
    jne     .al_pk_right
    mov     r9d, [rsp + 112]
    add     [rsp + 112], r10d
    jmp     .al_pk_inner
.al_pk_right:
    mov     r9d, [rsp + 120]
    sub     r9d, r10d
    mov     [rsp + 120], r9d

.al_pk_inner:
    add     r9d, [rsp + 688]
    sub     r10d, [rsp + 688]
    sub     r10d, [rsp + 692]
    cmp     r10d, 1
    jge     .al_pki_w
    mov     r10d, 1
.al_pki_w:
    add     eax, [rsp + 696]
    sub     r11d, [rsp + 696]
    sub     r11d, [rsp + 700]
    cmp     r11d, 1
    jge     .al_pki_h
    mov     r11d, 1
.al_pki_h:
    mov     edi, [rbx + 28]
    test    edi, 1
    jz      .al_pk_nofx
    mov     [rsp + 704], r9d
    mov     [rsp + 712], r10d
    jmp     .al_pk_fy
.al_pk_nofx:
    mov     ecx, [rsp + 680]
    cmp     ecx, r10d
    jle     .al_pk_fxw
    mov     ecx, r10d
.al_pk_fxw:
    mov     [rsp + 712], ecx
    mov     edx, r10d
    sub     edx, ecx
    shr     edx, 1
    add     edx, r9d
    mov     [rsp + 704], edx
.al_pk_fy:
    test    edi, 2
    jz      .al_pk_nofy
    mov     [rsp + 708], eax
    mov     [rsp + 716], r11d
    jmp     .al_do_move
.al_pk_nofy:
    mov     ecx, [rsp + 684]
    cmp     ecx, r11d
    jle     .al_pk_fyh
    mov     ecx, r11d
.al_pk_fyh:
    mov     [rsp + 716], ecx
    mov     edx, r11d
    sub     edx, ecx
    shr     edx, 1
    add     edx, eax
    mov     [rsp + 708], edx

.al_do_move:
    mov     r10d, [rsp + 712]
    cmp     r10d, 1
    jge     .al_dm_w
    mov     r10d, 1
.al_dm_w:
    mov     r11d, [rsp + 716]
    cmp     r11d, 1
    jge     .al_dm_h
    mov     r11d, 1
.al_dm_h:
    cmp     dword [rbx + 16], 9
    jne     .al_dm_call
    add     r11d, 180
.al_dm_call:
    mov     rcx, [rbx]
    mov     edx, [rsp + 704]
    mov     r8d, [rsp + 708]
    mov     r9d, r10d
    movsxd  rax, r11d
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 1
    call    [MoveWindow]

.al_p2_next:
    inc     r15
    jmp     .al_p2_loop

.al_recurse_start:
    xor     r15d, r15d
.al_rec_loop:
    cmp     r15, r13
    jge     .al_exit
    mov     rax, r15
    shl     rax, 6
    lea     rbx, [_pyfasm_layout_table + rax]
    cmp     [rbx + 8], r12
    jne     .al_rec_next
    cmp     [rbx], r12
    je      .al_rec_next
    cmp     dword [rbx + 16], 2
    jne     .al_rec_next
    mov     rcx, [rbx]
    call    _pyfasm_apply_layout
.al_rec_next:
    inc     r15
    jmp     .al_rec_loop

.al_exit:
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

_pyfasm_create_frame:
    ; RCX = parent_hwnd, RDX = w, R8 = h, R9 = corner_radius, [rbp+48] = fg_color
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    mov     [rsp + 144], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 112]
    test    rax, rax
    jnz     .cf_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 112], rax
.cf_p_ok:
    mov     r10, [rsp + 120]
    test    r10, r10
    jg      .cf_iw_ok
    mov     r10d, 100
.cf_iw_ok:
    mov     r11, [rsp + 128]
    test    r11, r11
    jg      .cf_ih_ok
    mov     r11d, 40
.cf_ih_ok:

    xor     ecx, ecx
    lea     rdx, [_pyfasm_card_class_w]
    xor     r8, r8
    mov     r9d, 56000000h
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     [rsp + 48], r10
    mov     [rsp + 56], r11
    mov     rax, [rsp + 112]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [rsp + 152], rax

    mov     rcx, rax
    mov     rdx, [rsp + 112]
    mov     r8, 2
    mov     r9, [rsp + 120]
    mov     rax, [rsp + 128]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rdx, [rsp + 144]
    test    rdx, rdx
    jz      .cf_done
    mov     rcx, [rsp + 152]
    xor     r8d, r8d
    call    _pyfasm_widget_set_colors
.cf_done:
    mov     rax, [rsp + 152]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_canvas:
    ; RCX = parent_hwnd, RDX = w, R8 = h
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 112]
    test    rax, rax
    jnz     .cca_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 112], rax
.cca_p_ok:
    mov     rax, [rsp + 120]
    test    rax, rax
    jg      .cca_w_ok
    mov     qword [rsp + 120], 480
.cca_w_ok:
    mov     rax, [rsp + 128]
    test    rax, rax
    jg      .cca_h_ok
    mov     qword [rsp + 128], 360
.cca_h_ok:

    xor     ecx, ecx
    lea     rdx, [_pyfasm_canvas_class_w]
    xor     r8, r8
    mov     r9d, 56000000h
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     rax, [rsp + 120]
    mov     [rsp + 48], rax
    mov     rax, [rsp + 128]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 112]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [rsp + 136], rax

    mov     rcx, rax
    mov     rdx, [rsp + 112]
    mov     r8, 6
    mov     r9, [rsp + 120]
    mov     rax, [rsp + 128]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, [rsp + 136]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_card_wnd_proc:
    ; RCX = hWnd, RDX = uMsg, R8 = wParam, R9 = lParam
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 128
    and     rsp, -16

    mov     [rsp + 64], rcx
    mov     [rsp + 72], rdx
    mov     [rsp + 80], r8
    mov     [rsp + 88], r9

    cmp     edx, 0005h
    je      .cwp_size
    cmp     edx, 000Fh
    je      .cwp_paint
    cmp     edx, 0014h
    je      .cwp_erasebkgnd
    cmp     edx, 002Bh
    je      .cwp_fwd_main
    cmp     edx, 002Ch
    je      .cwp_fwd_main
    cmp     edx, 0111h
    je      .cwp_fwd_main
    cmp     edx, 0114h
    je      .cwp_fwd_main
    cmp     edx, 0115h
    je      .cwp_fwd_main
    cmp     edx, 0138h
    je      .cwp_ctlcolor
    cmp     edx, 0133h
    je      .cwp_ctlcolor
    cmp     edx, 0134h
    je      .cwp_ctlcolor
    cmp     edx, 0135h
    je      .cwp_ctlcolor

    call    [DefWindowProcW]
    jmp     .cwp_exit

.cwp_size:
    mov     rcx, [rsp + 64]
    call    _pyfasm_apply_layout
    mov     rcx, [rsp + 64]
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]
    xor     eax, eax
    jmp     .cwp_exit

.cwp_erasebkgnd:
    mov     eax, 1
    jmp     .cwp_exit

.cwp_fwd_main:
    mov     rcx, [_pyfasm_h_wnd]
    test    rcx, rcx
    jz      .cwp_cmd_zero
    cmp     rcx, [rsp + 64]
    je      .cwp_cmd_zero
    mov     edx, dword [rsp + 72]
    mov     r8, [rsp + 80]
    mov     r9, [rsp + 88]
    call    [SendMessageW]
    jmp     .cwp_exit
.cwp_cmd_zero:
    xor     eax, eax
    jmp     .cwp_exit

.cwp_ctlcolor:
    mov     rcx, [rsp + 80]
    mov     rdx, [rsp + 88]
    mov     r8d, dword [rsp + 72]
    mov     r9, [rsp + 64]
    call    _pyfasm_handle_ctlcolor
    jmp     .cwp_exit

.cwp_paint:
    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 96]
    call    [BeginPaint]
    test    rax, rax
    jz      .cwp_paint_done
    mov     rbx, rax

    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 32]
    call    [GetClientRect]

    mov     rcx, [rsp + 64]
    call    _pyfasm_find_widget_slot
    mov     r8, [_pyfasm_hbr_card]
    cmp     rax, 0
    jl      .cwp_use_brush
    shl     rax, 6
    lea     rdi, [_pyfasm_widget_aux + rax]
    cmp     dword [rdi + 8], -2
    jne     .cwp_chk_hbr
    mov     r8, [_pyfasm_hbr_bg]
    jmp     .cwp_use_brush
.cwp_chk_hbr:
    mov     rax, [rdi + 0]
    test    rax, rax
    jz      .cwp_use_brush
    mov     r8, rax
.cwp_use_brush:
    test    r8, r8
    jnz     .cwp_fill
    mov     r8, [_pyfasm_hbr_bg]
.cwp_fill:
    mov     rcx, rbx
    lea     rdx, [rsp + 32]
    call    [FillRect]

    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 96]
    call    [EndPaint]

.cwp_paint_done:
    xor     eax, eax

.cwp_exit:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_wnd_proc:
    ; RCX = hWnd, RDX = uMsg, R8 = wParam, R9 = lParam
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 160
    and     rsp, -16

    mov     [rsp + 64], rcx
    mov     [rsp + 72], rdx
    mov     [rsp + 80], r8
    mov     [rsp + 88], r9

    cmp     edx, 000Fh
    je      .cv_paint
    cmp     edx, 0014h
    je      .cv_erase
    cmp     edx, 0005h
    je      .cv_size
    cmp     edx, 0201h
    je      .cv_lbutton

    call    [DefWindowProcW]
    jmp     .cv_exit

.cv_erase:
    mov     eax, 1
    jmp     .cv_exit

.cv_size:
    mov     rcx, [rsp + 64]
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]
    xor     eax, eax
    jmp     .cv_exit

.cv_lbutton:
    mov     rcx, [rsp + 64]
    mov     r12, [_pyfasm_bind_cnt]
    xor     r13d, r13d
.cv_lb_loop:
    cmp     r13, r12
    jge     .cv_lb_done
    imul    rax, r13, 24
    lea     rsi, [_pyfasm_binds + rax]
    cmp     dword [rsi + 8], 3
    jne     .cv_lb_next
    mov     rax, [rsi + 0]
    cmp     rax, rcx
    je      .cv_lb_fire
    cmp     rax, [_pyfasm_h_wnd]
    jne     .cv_lb_next
.cv_lb_fire:
    mov     rcx, [rsi + 16]
    mov     rdx, 8000000000000001h
    call    _pyfasm_invoke_cb
    mov     rcx, [rsp + 64]
.cv_lb_next:
    inc     r13
    jmp     .cv_lb_loop
.cv_lb_done:
    xor     eax, eax
    jmp     .cv_exit

.cv_paint:
    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 96]
    call    [BeginPaint]
    test    rax, rax
    jz      .cv_paint_done
    mov     rbx, rax

    mov     rcx, [rsp + 64]
    call    _pyfasm_find_widget_slot
    xor     r14, r14
    xor     r15, r15
    cmp     rax, 0
    jl      .cv_no_aux
    shl     rax, 6
    lea     rsi, [_pyfasm_widget_aux + rax]
    mov     r14, [rsi + 48]
    mov     r15, [rsi + 0]
.cv_no_aux:
    test    r14, r14
    jz      .cv_fill_bg
    mov     rax, 5059464D46494721h
    cmp     [r14], rax
    jne     .cv_chk_tkcanv
    mov     rcx, [rsp + 64]
    mov     rdx, rbx
    mov     r8, r14
    call    _pyfasm_mpl_paint_hwnd
    jmp     .cv_endpaint

.cv_chk_tkcanv:
    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 32]
    call    [GetClientRect]
    mov     r8, r15
    test    r8, r8
    jnz     .cv_tk_fill
    mov     r8, [_pyfasm_hbr_card]
    test    r8, r8
    jnz     .cv_tk_fill
    mov     r8, [_pyfasm_hbr_bg]
.cv_tk_fill:
    mov     rcx, rbx
    lea     rdx, [rsp + 32]
    call    [FillRect]
    mov     rax, 50594643414E5621h
    cmp     [r14], rax
    jne     .cv_endpaint
    mov     rcx, rbx
    mov     rdx, r14
    call    _pyfasm_canvas_replay
    jmp     .cv_endpaint

.cv_fill_bg:
    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 32]
    call    [GetClientRect]
    mov     r8, r15
    test    r8, r8
    jnz     .cv_bg_go
    mov     r8, [_pyfasm_hbr_card]
    test    r8, r8
    jnz     .cv_bg_go
    mov     r8, [_pyfasm_hbr_bg]
.cv_bg_go:
    mov     rcx, rbx
    lea     rdx, [rsp + 32]
    call    [FillRect]

.cv_endpaint:
    mov     rcx, [rsp + 64]
    lea     rdx, [rsp + 96]
    call    [EndPaint]

.cv_paint_done:
    xor     eax, eax

.cv_exit:
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

_pyfasm_create_label:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = parent_hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    mov     [rsp + 144], rax
    mov     rax, [rbp + 56]
    mov     [rsp + 152], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 152]
    test    rax, rax
    jnz     .lbl_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 152], rax
.lbl_p_ok:
    mov     rcx, [rsp + 112]
    test    rcx, rcx
    jz      .lbl_empty_txt
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_wide_buf]
    jmp     .lbl_txt_ready
.lbl_empty_txt:
    xor     r8, r8
.lbl_txt_ready:
    mov     rax, [rsp + 136]
    test    rax, rax
    jg      .lbl_w_ok
    mov     eax, 120
.lbl_w_ok:
    mov     r10, [rsp + 144]
    test    r10, r10
    jg      .lbl_h_ok
    mov     r10d, 24
.lbl_h_ok:
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    mov     r9d, 50000000h
    mov     r11, [rsp + 120]
    mov     [rsp + 32], r11
    mov     r11, [rsp + 128]
    mov     [rsp + 40], r11
    mov     [rsp + 48], rax
    mov     [rsp + 56], r10
    mov     rax, [rsp + 152]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_last_label_hwnd], rax
    mov     [rsp + 160], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rcx, [rsp + 160]
    mov     rdx, [rsp + 152]
    xor     r8d, r8d
    mov     r9, [rsp + 136]
    mov     rax, [rsp + 144]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, [rsp + 160]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_edit:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = parent_hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .edt_h_ok
    mov     rax, 32
.edt_h_ok:
    mov     [rsp + 144], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .edt_id_ok
    mov     rax, 100
.edt_id_ok:
    mov     [rsp + 152], rax
    mov     rax, [rbp + 64]
    mov     [rsp + 160], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 160]
    test    rax, rax
    jnz     .edt_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 160], rax
.edt_p_ok:
    mov     rcx, [rsp + 112]
    test    rcx, rcx
    jz      .edt_empty_txt
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_wide_buf]
    jmp     .edt_txt_ready
.edt_empty_txt:
    xor     r8, r8
.edt_txt_ready:
    mov     rax, [rsp + 136]
    test    rax, rax
    jg      .edt_w_ok
    mov     eax, 200
    mov     [rsp + 136], rax
.edt_w_ok:
    mov     ecx, 200h
    lea     rdx, [szEditClassW]
    mov     r9d, 50810080h
    mov     r10, [rsp + 120]
    mov     [rsp + 32], r10
    mov     r10, [rsp + 128]
    mov     [rsp + 40], r10
    mov     [rsp + 48], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 160]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 152]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_last_edit_hwnd], rax
    mov     [rsp + 168], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rcx, [rsp + 168]
    mov     rdx, [rsp + 160]
    mov     r8, 1
    mov     r9, [rsp + 136]
    mov     rax, [rsp + 144]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, [rsp + 168]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_textbox:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = parent_hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .tb_h_ok
    mov     rax, 180
.tb_h_ok:
    mov     [rsp + 144], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .tb_id_ok
    mov     rax, 100
.tb_id_ok:
    mov     [rsp + 152], rax
    mov     rax, [rbp + 64]
    mov     [rsp + 160], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 160]
    test    rax, rax
    jnz     .tb_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 160], rax
.tb_p_ok:
    mov     rcx, [rsp + 112]
    test    rcx, rcx
    jz      .tb_empty_txt
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_wide_buf]
    jmp     .tb_txt_ready
.tb_empty_txt:
    xor     r8, r8
.tb_txt_ready:
    mov     rax, [rsp + 136]
    test    rax, rax
    jg      .tb_w_ok
    mov     eax, 340
    mov     [rsp + 136], rax
.tb_w_ok:
    mov     ecx, 200h
    lea     rdx, [szEditClassW]
    mov     r9d, 50A11044h
    mov     r10, [rsp + 120]
    mov     [rsp + 32], r10
    mov     r10, [rsp + 128]
    mov     [rsp + 40], r10
    mov     [rsp + 48], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 160]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 152]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_last_edit_hwnd], rax
    mov     [rsp + 168], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rcx, [rsp + 168]
    mov     rdx, [rsp + 160]
    mov     r8, 7
    mov     r9, [rsp + 136]
    mov     rax, [rsp + 144]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, [rsp + 168]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_button:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = callback_fn, [rbp+72] = parent_hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .btn_h_ok
    mov     rax, 34
.btn_h_ok:
    mov     [rsp + 144], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .btn_id_ok
    mov     rax, 1000
    add     rax, [_pyfasm_ctrl_count]
.btn_id_ok:
    mov     [rsp + 152], rax
    mov     rax, [rbp + 64]
    mov     [rsp + 160], rax
    mov     rax, [rbp + 72]
    mov     [rsp + 168], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 168]
    test    rax, rax
    jnz     .btn_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 168], rax
.btn_p_ok:
    mov     rcx, [rsp + 112]
    test    rcx, rcx
    jz      .btn_empty_txt
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_wide_buf]
    jmp     .btn_txt_ready
.btn_empty_txt:
    xor     r8, r8
.btn_txt_ready:
    mov     rax, [rsp + 136]
    test    rax, rax
    jg      .btn_w_ok
    mov     eax, 120
    mov     [rsp + 136], rax
.btn_w_ok:
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    mov     r9d, 5001000Bh
    mov     r10, [rsp + 120]
    mov     [rsp + 32], r10
    mov     r10, [rsp + 128]
    mov     [rsp + 40], r10
    mov     [rsp + 48], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 168]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 152]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_last_btn_hwnd], rax
    mov     [rsp + 176], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rcx, [_pyfasm_ctrl_count]
    cmp     rcx, 128
    jge     .skip_btn_cb
    mov     r8, [rsp + 152]
    mov     r9, [rsp + 160]
    mov     dword [_pyfasm_ctrl_ids + rcx*4], r8d
    mov     qword [_pyfasm_ctrl_callbacks + rcx*8], r9
    mov     rax, [rsp + 176]
    mov     qword [_pyfasm_ctrl_hwnds + rcx*8], rax
    inc     qword [_pyfasm_ctrl_count]
.skip_btn_cb:

    mov     rcx, [rsp + 176]
    mov     rdx, [rsp + 168]
    mov     r8, 3
    mov     r9, [rsp + 136]
    mov     rax, [rsp + 144]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rcx, [rsp + 176]
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .btn_done
    shl     rax, 6
    mov     r8d, dword [rsp + 152]
    mov     dword [_pyfasm_widget_aux + rax + 56], r8d
.btn_done:
    mov     rax, [rsp + 176]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_checkbox:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = callback_fn, [rbp+72] = parent_hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 112], rcx
    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .chk_h_ok
    mov     rax, 28
.chk_h_ok:
    mov     [rsp + 144], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .chk_id_ok
    mov     rax, 2000
    add     rax, [_pyfasm_ctrl_count]
.chk_id_ok:
    mov     [rsp + 152], rax
    mov     rax, [rbp + 64]
    mov     [rsp + 160], rax
    mov     rax, [rbp + 72]
    mov     [rsp + 168], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 168]
    test    rax, rax
    jnz     .chk_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 168], rax
.chk_p_ok:
    mov     rcx, [rsp + 112]
    test    rcx, rcx
    jz      .chk_empty_txt
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_wide_buf]
    jmp     .chk_txt_ready
.chk_empty_txt:
    xor     r8, r8
.chk_txt_ready:
    mov     rax, [rsp + 136]
    test    rax, rax
    jg      .chk_w_ok
    mov     eax, 200
    mov     [rsp + 136], rax
.chk_w_ok:
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    mov     r9d, 50010003h
    mov     r10, [rsp + 120]
    mov     [rsp + 32], r10
    mov     r10, [rsp + 128]
    mov     [rsp + 40], r10
    mov     [rsp + 48], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 168]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 152]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_last_btn_hwnd], rax
    mov     [rsp + 176], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rcx, [_pyfasm_ctrl_count]
    cmp     rcx, 128
    jge     .skip_chk_cb
    mov     r8, [rsp + 152]
    mov     r9, [rsp + 160]
    mov     dword [_pyfasm_ctrl_ids + rcx*4], r8d
    mov     qword [_pyfasm_ctrl_callbacks + rcx*8], r9
    mov     rax, [rsp + 176]
    mov     qword [_pyfasm_ctrl_hwnds + rcx*8], rax
    inc     qword [_pyfasm_ctrl_count]
.skip_chk_cb:

    mov     rcx, [rsp + 176]
    mov     rdx, [rsp + 168]
    mov     r8, 4
    mov     r9, [rsp + 136]
    mov     rax, [rsp + 144]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, [rsp + 176]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_listbox:
    ; RCX = 0, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = parent_hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 192
    and     rsp, -16

    mov     [rsp + 120], rdx
    mov     [rsp + 128], r8
    mov     [rsp + 136], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .lb_h_ok
    mov     rax, 240
.lb_h_ok:
    mov     [rsp + 144], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .lb_id_ok
    mov     rax, 3001
.lb_id_ok:
    mov     [rsp + 152], rax
    mov     rax, [rbp + 64]
    mov     [rsp + 160], rax

    call    _pyfasm_ensure_window

    mov     rax, [rsp + 160]
    test    rax, rax
    jnz     .lb_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 160], rax
.lb_p_ok:
    mov     rax, [rsp + 136]
    test    rax, rax
    jg      .lb_w_ok
    mov     eax, 400
    mov     [rsp + 136], rax
.lb_w_ok:
    mov     ecx, 200h
    lea     rdx, [szListBoxClassW]
    xor     r8, r8
    mov     r9d, 50200151h
    mov     r10, [rsp + 120]
    mov     [rsp + 32], r10
    mov     r10, [rsp + 128]
    mov     [rsp + 40], r10
    mov     [rsp + 48], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 160]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 152]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_last_list_hwnd], rax
    mov     [rsp + 168], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rcx, [rsp + 168]
    mov     rdx, [rsp + 160]
    mov     r8, 5
    mov     r9, [rsp + 136]
    mov     rax, [rsp + 144]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, [rsp + 168]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_get_edit_text:
    ; RCX = hwnd, RDX = buf, R8 = max_len
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .ge_hwnd_ok
    mov     rcx, [_pyfasm_last_edit_hwnd]
.ge_hwnd_ok:
    test    rcx, rcx
    jz      .ge_null_ret
    test    rdx, rdx
    jnz     .ge_buf_ok
    lea     rdx, [_pyfasm_edit_buf]
.ge_buf_ok:
    test    r8, r8
    jnz     .ge_len_ok
    mov     r8d, 2048
.ge_len_ok:
    mov     [rsp + 32], rdx
    call    [GetWindowTextW]
    mov     rax, [rsp + 32]
    mov     rsp, rbp
    pop     rbp
    ret
.ge_null_ret:
    lea     rax, [none_str]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_text:
    ; RCX = hwnd, RDX = text (UTF-8 string from Python code)
    push    rbp
    mov     rbp, rsp
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .st_hwnd_ok
    mov     rcx, [_pyfasm_last_label_hwnd]
.st_hwnd_ok:
    test    rcx, rcx
    jz      .st_ret
    mov     rsi, rcx
    mov     rcx, rdx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    call    [SetWindowTextW]
.st_ret:
    lea     rsp, [rbp - 8]
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_append_cmd:
    ; RCX = hwnd, RDX = kind(1:line,2:rect,3:oval,4:text), R8 = x1, R9 = y1, [rbp+48]=x2, [rbp+56]=y2_or_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    mov     r12d, edx
    mov     [rsp + 32], r8d
    mov     [rsp + 36], r9d
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .cac_done
    shl     rax, 6
    lea     rsi, [_pyfasm_widget_aux + rax]
    mov     rdi, [rsi + 48]
    test    rdi, rdi
    jz      .cac_alloc_list
    mov     rax, 50594643414E5621h
    cmp     [rdi], rax
    je      .cac_have_list
.cac_alloc_list:
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     rax, 50594643414E5621h
    mov     [rdi + 0], rax
    mov     qword [rdi + 8], 0
    mov     qword [rdi + 16], 128
    mov     ecx, 128 * 32
    call    _pyfasm_alloc
    mov     [rdi + 24], rax
    mov     [rsi + 48], rdi
.cac_have_list:
    mov     rax, [rdi + 8]
    cmp     rax, [rdi + 16]
    jge     .cac_done
    inc     qword [rdi + 8]
    shl     rax, 5
    add     rax, [rdi + 24]
    mov     dword [rax + 0], r12d
    mov     ecx, dword [_pyfasm_canvas_color]
    mov     dword [rax + 4], ecx
    mov     ecx, [rsp + 32]
    mov     dword [rax + 8], ecx
    mov     ecx, [rsp + 36]
    mov     dword [rax + 12], ecx
    mov     ecx, dword [rbp + 48]
    mov     dword [rax + 16], ecx
    cmp     r12d, 4
    je      .cac_is_txt
    mov     ecx, dword [rbp + 56]
    mov     dword [rax + 20], ecx
    mov     qword [rax + 24], 0
    jmp     .cac_inv
.cac_is_txt:
    mov     dword [rax + 20], 0
    mov     rcx, [rbp + 56]
    mov     [rax + 24], rcx
.cac_inv:
    mov     rcx, rbx
    xor     edx, edx
    xor     r8d, r8d
    call    [InvalidateRect]
.cac_done:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_replay:
    ; RCX = hdc, RDX = PYFCANV! ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 96
    and     rsp, -16

    mov     rbx, rcx
    mov     r12, rdx
    test    r12, r12
    jz      .crp_done
    mov     r13, [r12 + 8]
    mov     r14, [r12 + 24]
    xor     r15d, r15d
.crp_loop:
    cmp     r15, r13
    jge     .crp_done
    mov     rsi, r15
    shl     rsi, 5
    add     rsi, r14

    mov     eax, [rsi + 4]
    cmp     eax, -1
    jne     .crp_col_ok
    mov     eax, [_pyfasm_theme_text]
.crp_col_ok:
    mov     [rsp + 48], eax
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 0
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0

    xor     ecx, ecx
    mov     edx, 2
    mov     r8d, eax
    call    [CreatePen]
    mov     [rsp + 56], rax
    test    rax, rax
    jz      .crp_brush
    mov     rcx, rbx
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 64], rax
.crp_brush:
    mov     ecx, [rsp + 48]
    call    [CreateSolidBrush]
    mov     [rsp + 72], rax
    test    rax, rax
    jz      .crp_dispatch
    mov     rcx, rbx
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 80], rax

.crp_dispatch:
    mov     eax, [rsi + 0]
    cmp     eax, 1
    jne     .crp_chk2
    mov     rcx, rbx
    movsxd  rdx, dword [rsi + 8]
    movsxd  r8, dword [rsi + 12]
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, rbx
    movsxd  rdx, dword [rsi + 16]
    movsxd  r8, dword [rsi + 20]
    call    [LineTo]
    jmp     .crp_cleanup

.crp_chk2:
    cmp     eax, 2
    jne     .crp_chk3
    mov     rcx, rbx
    movsxd  rdx, dword [rsi + 8]
    movsxd  r8, dword [rsi + 12]
    movsxd  r9, dword [rsi + 16]
    movsxd  rax, dword [rsi + 20]
    mov     [rsp + 32], rax
    call    [Rectangle]
    jmp     .crp_cleanup

.crp_chk3:
    cmp     eax, 3
    jne     .crp_chk4
    mov     rcx, rbx
    movsxd  rdx, dword [rsi + 8]
    movsxd  r8, dword [rsi + 12]
    movsxd  r9, dword [rsi + 16]
    movsxd  rax, dword [rsi + 20]
    mov     [rsp + 32], rax
    call    [Ellipse]
    jmp     .crp_cleanup

.crp_chk4:
    cmp     eax, 4
    jne     .crp_cleanup
    mov     rcx, [rsi + 24]
    test    rcx, rcx
    jz      .crp_cleanup
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
    mov     [rsp + 88], rax
    mov     rcx, rbx
    mov     edx, 1
    call    [SetBkMode]
    mov     rcx, rbx
    mov     edx, [rsp + 48]
    call    [SetTextColor]
    mov     rcx, rbx
    movsxd  rdx, dword [rsi + 8]
    movsxd  r8, dword [rsi + 12]
    lea     r9, [_pyfasm_wide_buf]
    mov     rax, [rsp + 88]
    mov     [rsp + 32], rax
    call    [TextOutW]

.crp_cleanup:
    mov     rdx, [rsp + 80]
    test    rdx, rdx
    jz      .crp_restp
    mov     rcx, rbx
    call    [SelectObject]
.crp_restp:
    mov     rdx, [rsp + 64]
    test    rdx, rdx
    jz      .crp_delb
    mov     rcx, rbx
    call    [SelectObject]
.crp_delb:
    mov     rcx, [rsp + 72]
    test    rcx, rcx
    jz      .crp_delp
    call    [DeleteObject]
.crp_delp:
    mov     rcx, [rsp + 56]
    test    rcx, rcx
    jz      .crp_next
    call    [DeleteObject]
.crp_next:
    inc     r15
    jmp     .crp_loop

.crp_done:
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

_pyfasm_canvas_create_line:
    ; RCX = hwnd, RDX = x1, R8 = y1, R9 = x2, [rbp+48] = y2
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .ccl_h_ok
    mov     rcx, [_pyfasm_h_wnd]
.ccl_h_ok:
    mov     rax, [rbp + 48]
    mov     [rsp + 32], r9
    mov     [rsp + 40], rax
    mov     r9, r8
    mov     r8, rdx
    mov     edx, 1
    call    _pyfasm_canvas_append_cmd
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_create_rectangle:
    ; RCX = hwnd, RDX = x1, R8 = y1, R9 = x2, [rbp+48] = y2
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .ccr_h_ok
    mov     rcx, [_pyfasm_h_wnd]
.ccr_h_ok:
    mov     rax, [rbp + 48]
    mov     [rsp + 32], r9
    mov     [rsp + 40], rax
    mov     r9, r8
    mov     r8, rdx
    mov     edx, 2
    call    _pyfasm_canvas_append_cmd
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_create_oval:
    ; RCX = hwnd, RDX = x1, R8 = y1, R9 = x2, [rbp+48] = y2
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .cco_h_ok
    mov     rcx, [_pyfasm_h_wnd]
.cco_h_ok:
    mov     rax, [rbp + 48]
    mov     [rsp + 32], r9
    mov     [rsp + 40], rax
    mov     r9, r8
    mov     r8, rdx
    mov     edx, 3
    call    _pyfasm_canvas_append_cmd
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_create_text:
    ; RCX = hwnd, RDX = x, R8 = y, R9 = utf8_str_ptr
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .cct_h_ok
    mov     rcx, [_pyfasm_h_wnd]
.cct_h_ok:
    mov     qword [rsp + 32], 0
    mov     [rsp + 40], r9
    mov     r9, r8
    mov     r8, rdx
    mov     edx, 4
    call    _pyfasm_canvas_append_cmd
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_listbox_add:
    ; RCX = hwnd, RDX = text OR list/tuple (also handles ComboBox type == 9)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .la_hwnd_ok
    mov     rcx, [_pyfasm_last_list_hwnd]
.la_hwnd_ok:
    test    rcx, rcx
    jz      .la_done
    mov     rbx, rcx
    mov     rsi, rdx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .la_lb_mode
    shl     rax, 6
    cmp     dword [_pyfasm_layout_table + rax + 16], 9
    jne     .la_lb_mode
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_combobox_add
    jmp     .la_done

.la_lb_mode:
    mov     rcx, rsi
    call    _pyfasm_is_list
    test    eax, eax
    jz      .la_single
    mov     rdi, [rsi]
    xor     r12d, r12d
.la_loop:
    cmp     r12, rdi
    jge     .la_done
    mov     rcx, [rsi + r12*8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 1024
    call    _pyfasm_utf8_to_wide
    mov     rcx, rbx
    mov     edx, 180h
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    inc     r12
    jmp     .la_loop

.la_single:
    mov     rcx, rsi
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 1024
    call    _pyfasm_utf8_to_wide
    mov     rcx, rbx
    mov     edx, 180h
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
.la_done:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_listbox_clear:
    ; RCX = hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .lc_hwnd_ok
    mov     rcx, [_pyfasm_last_list_hwnd]
.lc_hwnd_ok:
    test    rcx, rcx
    jz      .lc_done
    mov     rbx, rcx
    call    _pyfasm_find_widget_slot
    mov     edx, 184h           ; LB_RESETCONTENT
    cmp     rax, 0
    jl      .lc_send
    shl     rax, 6
    cmp     dword [_pyfasm_layout_table + rax + 16], 9
    jne     .lc_send
    mov     edx, 14Bh           ; CB_RESETCONTENT
.lc_send:
    mov     rcx, rbx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
.lc_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_listbox_count:
    ; RCX = listbox or combobox hwnd -> RAX = number of items
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .ln_hwnd_ok
    mov     rcx, [_pyfasm_last_list_hwnd]
.ln_hwnd_ok:
    xor     eax, eax
    test    rcx, rcx
    jz      .ln_done
    mov     rbx, rcx
    call    _pyfasm_find_widget_slot
    mov     edx, 18Bh           ; LB_GETCOUNT
    cmp     rax, 0
    jl      .ln_send
    shl     rax, 6
    cmp     dword [_pyfasm_layout_table + rax + 16], 9
    jne     .ln_send
    mov     edx, 146h           ; CB_GETCOUNT
.ln_send:
    mov     rcx, rbx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    movsxd  rax, eax
    test    rax, rax
    jns     .ln_done
    xor     eax, eax
.ln_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_register_hotkey:
    ; RCX = id, RDX = vk_code
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    call    _pyfasm_ensure_window
    mov     r9, rdx
    mov     r8d, 4000h
    mov     rdx, rcx
    mov     rcx, [_pyfasm_h_wnd]
    call    [RegisterHotKey]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_run_window_loop:
    push    rbp
    mov     rbp, rsp
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    cmp     qword [_pyfasm_h_wnd], 0
    jne     .start_msg_loop_ready
    xor     ecx, ecx
    xor     edx, edx
    xor     r8d, r8d
    call    _pyfasm_create_window

.start_msg_loop_ready:
    mov     rcx, [_pyfasm_h_wnd]
    call    _pyfasm_apply_layout
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 5
    call    [ShowWindow]
    mov     rcx, [_pyfasm_h_wnd]
    call    [UpdateWindow]

.start_msg_loop:
    lea     rcx, [_pyfasm_msg]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [GetMessageW]
    test    eax, eax
    jle     .msg_loop_done

    cmp     dword [_pyfasm_msg + 8], 100h
    jne     .rwl_trans
    mov     r12, [_pyfasm_bind_cnt]
    xor     r13d, r13d
.rwl_bind_loop:
    cmp     r13, r12
    jge     .rwl_trans
    imul    rax, r13, 24
    lea     rdx, [_pyfasm_binds + rax]
    mov     ecx, [rdx + 8]
    cmp     ecx, 2
    je      .rwl_bind_fire
    cmp     ecx, 1
    jne     .rwl_bind_next
    cmp     qword [_pyfasm_msg + 16], 0Dh
    jne     .rwl_bind_next
.rwl_bind_fire:
    mov     rcx, [rdx + 16]
    mov     rdx, 8000000000000001h
    call    _pyfasm_invoke_cb
.rwl_bind_next:
    inc     r13
    jmp     .rwl_bind_loop

.rwl_trans:
    lea     rcx, [_pyfasm_msg]
    call    [TranslateMessage]
    lea     rcx, [_pyfasm_msg]
    call    [DispatchMessageW]
    jmp     .start_msg_loop

.msg_loop_done:
    lea     rsp, [rbp - 16]
    pop     r13
    pop     r12
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_invoke_cb:
    ; RCX = callback fn or PYFCLOSU ptr, RDX = opt_arg or 8000000000000001h
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .icb_zero

    mov     r8, 8000000000000001h
    mov     r9, 8000000000000001h
    mov     rax, 505946434C4F5355h
    cmp     [rbx], rax
    jne     .icb_plain
    mov     rcx, rbx
    mov     rdx, rsi
    call    qword [rbx + 8]
    jmp     .icb_done

.icb_plain:
    cmp     rsi, r8
    je      .icb_no_arg
    mov     rcx, rsi
    mov     rdx, r8
    call    rbx
    jmp     .icb_done
.icb_no_arg:
    mov     rcx, [_pyfasm_last_gui_instance]
    mov     rdx, r8
    call    rbx
    jmp     .icb_done

.icb_zero:
    xor     eax, eax
.icb_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_handle_ctlcolor:
    ; RCX = hdc, RDX = ctl_hwnd, R8 = uMsg, R9 = parent_hwnd -> RAX = HBRUSH
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    mov     rsi, rdx
    mov     edi, r8d
    mov     r12, r9

    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    mov     r13, rax

    mov     edx, [_pyfasm_theme_text]
    cmp     r13, 0
    jl      .hcc_tc_ok
    shl     r13, 6
    mov     eax, dword [_pyfasm_widget_aux + r13 + 12]
    cmp     eax, -1
    je      .hcc_tc_ok
    mov     edx, eax
.hcc_tc_ok:
    mov     rcx, rbx
    call    [SetTextColor]

    cmp     r13, 0
    jl      .hcc_no_custom
    mov     rax, qword [_pyfasm_widget_aux + r13 + 0]
    test    rax, rax
    jz      .hcc_no_custom
    mov     [rsp + 32], rax
    mov     rcx, rbx
    mov     edx, dword [_pyfasm_widget_aux + r13 + 8]
    call    [SetBkColor]
    cmp     edi, 133h
    je      .hcc_opq
    cmp     edi, 134h
    je      .hcc_opq
    mov     edx, 1
    jmp     .hcc_setbm
.hcc_opq:
    mov     edx, 2
.hcc_setbm:
    mov     rcx, rbx
    call    [SetBkMode]
    mov     rax, [rsp + 32]
    jmp     .hcc_done

.hcc_no_custom:
    cmp     edi, 133h
    je      .hcc_edit
    cmp     edi, 134h
    je      .hcc_edit

    mov     rcx, rbx
    mov     edx, 1
    call    [SetBkMode]

    test    r12, r12
    jnz     .hcc_chk_parent
    mov     rcx, rsi
    call    [GetParent]
    mov     r12, rax
.hcc_chk_parent:
    cmp     r12, [_pyfasm_h_wnd]
    je      .hcc_root_bg
    test    r12, r12
    jz      .hcc_root_bg
    mov     rcx, r12
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .hcc_card_bg
    shl     rax, 6
    cmp     dword [_pyfasm_widget_aux + rax + 8], -2
    je      .hcc_root_bg
    mov     rax, qword [_pyfasm_widget_aux + rax + 0]
    test    rax, rax
    jnz     .hcc_done
.hcc_card_bg:
    mov     rax, [_pyfasm_hbr_card]
    test    rax, rax
    jnz     .hcc_done
.hcc_root_bg:
    mov     rax, [_pyfasm_hbr_bg]
    jmp     .hcc_done

.hcc_edit:
    mov     rcx, rbx
    mov     edx, 2
    call    [SetBkMode]
    mov     rcx, rbx
    mov     edx, [_pyfasm_theme_input]
    call    [SetBkColor]
    mov     rax, [_pyfasm_hbr_input]

.hcc_done:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_wnd_proc:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 112
    and     rsp, -16

    mov     [rsp + 64], rcx
    mov     [rsp + 72], edx
    mov     rbx, r8
    mov     rsi, r9

    cmp     edx, 2
    je      .wnd_destroy
    cmp     edx, 5
    je      .wnd_size
    cmp     edx, 14h
    je      .wnd_erasebkgnd
    cmp     edx, 2Ch
    je      .wnd_measureitem
    cmp     edx, 2Bh
    je      .wnd_drawitem
    cmp     edx, 111h
    je      .wnd_command
    cmp     edx, 113h
    je      .wnd_timer
    cmp     edx, 114h
    je      .wnd_hscroll
    cmp     edx, 138h
    je      .wnd_ctlcolor
    cmp     edx, 133h
    je      .wnd_ctlcolor
    cmp     edx, 134h
    je      .wnd_ctlcolor
    cmp     edx, 135h
    je      .wnd_ctlcolor
    cmp     edx, 312h
    je      .wnd_hotkey

    call    [DefWindowProcW]
    jmp     .wnd_proc_ret

.wnd_size:
    mov     rcx, [_pyfasm_h_wnd]
    call    _pyfasm_apply_layout
    mov     rcx, [_pyfasm_h_wnd]
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_erasebkgnd:
    mov     rcx, [_pyfasm_h_wnd]
    lea     rdx, [_pyfasm_rc_client]
    call    [GetClientRect]
    mov     rcx, rbx
    lea     rdx, [_pyfasm_rc_client]
    mov     r8, [_pyfasm_hbr_bg]
    call    [FillRect]
    mov     eax, 1
    jmp     .wnd_proc_ret

.wnd_destroy:
    mov     rcx, [_pyfasm_hbr_bg]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hbr_card]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hbr_input]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hbr_orange]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hbr_orange_press]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hpen_orange]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hpen_slate]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hbr_card_sel]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hbr_sel]
    test    rcx, rcx
    jz      .wd_skip_sel
    call    [DeleteObject]
.wd_skip_sel:
    mov     rcx, [_pyfasm_h_font_ui]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_h_font_bold]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_h_font_mono]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_h_font_title]
    call    [DeleteObject]
    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_measureitem:
    mov     dword [rsi + 16], 28
    mov     eax, 1
    jmp     .wnd_proc_ret

.wnd_drawitem:
    mov     eax, [rsi + 0]
    cmp     eax, 2
    je      .wdi_listbox
    cmp     eax, 4
    je      .wdi_button
    xor     eax, eax
    jmp     .wnd_proc_ret

.wdi_listbox:
    cmp     dword [rsi + 8], -1
    je      .wdi_done
    mov     rcx, [rsi + 24]
    mov     edx, 189h
    mov     r8d, [rsi + 8]
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    cmp     eax, 0
    jle     .wdi_done
    mov     [rsp + 80], eax
    mov     r8, [_pyfasm_hbr_input]
    test    dword [rsi + 16], 1
    jz      .wdi_lb_bg
    mov     r8, [_pyfasm_hbr_sel]
    test    r8, r8
    jnz     .wdi_lb_bg
    mov     r8, [_pyfasm_hbr_card_sel]
.wdi_lb_bg:
    mov     rcx, [rsi + 32]
    lea     rdx, [rsi + 40]
    call    [FillRect]
    mov     rcx, [rsi + 32]
    mov     edx, 1
    call    [SetBkMode]
    mov     rcx, [rsi + 32]
    mov     edx, [_pyfasm_theme_text]
    test    dword [rsi + 16], 1
    jz      .wdi_lb_tc
    mov     edx, 00FFFFFFh
.wdi_lb_tc:
    call    [SetTextColor]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_ui]
    call    [SelectObject]
    mov     r12, rax
    mov     eax, [rsi + 40]
    add     eax, 8
    mov     [rsp + 48], eax
    mov     eax, [rsi + 44]
    mov     [rsp + 52], eax
    mov     eax, [rsi + 48]
    mov     [rsp + 56], eax
    mov     eax, [rsi + 52]
    mov     [rsp + 60], eax
    mov     rcx, [rsi + 32]
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, [rsp + 80]
    lea     r9, [rsp + 48]
    mov     qword [rsp + 32], 24h
    call    [DrawTextW]
    mov     rcx, [rsi + 32]
    mov     rdx, r12
    call    [SelectObject]
    jmp     .wdi_done

.wdi_button:
    mov     r12, [rsi + 24]
    mov     r13, [rsi + 32]
    mov     qword [rsp + 88], 0
    mov     qword [rsp + 96], 0
    mov     qword [rsp + 104], 0

    mov     rcx, r12
    call    [GetParent]
    mov     r8, [_pyfasm_hbr_bg]
    test    rax, rax
    jz      .wdi_b_par_fill
    cmp     rax, [_pyfasm_h_wnd]
    je      .wdi_b_par_fill
    mov     rcx, rax
    call    _pyfasm_find_widget_slot
    mov     r8, [_pyfasm_hbr_card]
    cmp     rax, 0
    jl      .wdi_b_par_fill
    shl     rax, 6
    mov     rdx, qword [_pyfasm_widget_aux + rax + 0]
    test    rdx, rdx
    jz      .wdi_b_par_fill
    mov     r8, rdx
.wdi_b_par_fill:
    mov     [rsp + 80], r8
    mov     rcx, r13
    lea     rdx, [rsi + 40]
    call    [FillRect]

    mov     rcx, r12
    call    _pyfasm_find_widget_slot
    xor     r14, r14
    cmp     rax, 0
    jl      .wdi_b_use_accent
    shl     rax, 6
    lea     r14, [_pyfasm_widget_aux + rax]
    cmp     dword [r14 + 8], -2
    je      .wdi_b_draw_text
    mov     rdx, [r14 + 0]
    test    rdx, rdx
    jz      .wdi_b_use_accent
    test    dword [rsi + 16], 1
    jz      .wdi_b_sel_br
    mov     eax, [r14 + 8]
    shr     eax, 1
    and     eax, 007F7F7Fh
    mov     ecx, eax
    call    [CreateSolidBrush]
    mov     [rsp + 88], rax
    mov     rdx, rax
    jmp     .wdi_b_sel_br
.wdi_b_use_accent:
    mov     rdx, [_pyfasm_hbr_orange]
    test    dword [rsi + 16], 1
    jz      .wdi_b_sel_br
    mov     rdx, [_pyfasm_hbr_orange_press]
.wdi_b_sel_br:
    mov     rcx, r13
    call    [SelectObject]
    mov     [rsp + 96], rax

    mov     ecx, 8
    call    [GetStockObject]
    mov     rcx, r13
    mov     rdx, rax
    call    [SelectObject]
    mov     [rsp + 104], rax

    mov     rcx, r13
    mov     edx, [rsi + 40]
    mov     r8d, [rsi + 44]
    mov     r9d, [rsi + 48]
    mov     eax, [rsi + 52]
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 10
    mov     qword [rsp + 48], 10
    call    [RoundRect]

    mov     rcx, r13
    mov     rdx, [rsp + 104]
    call    [SelectObject]
    mov     rcx, r13
    mov     rdx, [rsp + 96]
    call    [SelectObject]
    mov     rcx, [rsp + 88]
    test    rcx, rcx
    jz      .wdi_b_draw_text
    call    [DeleteObject]

.wdi_b_draw_text:
    mov     rcx, r12
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    [GetWindowTextW]
    test    eax, eax
    jle     .wdi_done
    mov     [rsp + 80], eax
    mov     rcx, r13
    mov     edx, 1
    call    [SetBkMode]
    mov     edx, 00FFFFFFh
    test    r14, r14
    jz      .wdi_b_tc_ok
    cmp     dword [r14 + 8], -2
    jne     .wdi_b_tc_chk
    mov     edx, [_pyfasm_theme_text]
.wdi_b_tc_chk:
    mov     eax, [r14 + 12]
    cmp     eax, -1
    je      .wdi_b_tc_ok
    mov     edx, eax
.wdi_b_tc_ok:
    mov     rcx, r13
    call    [SetTextColor]
    mov     rdx, [_pyfasm_h_font_ui]
    test    r14, r14
    jz      .wdi_b_font_ok
    cmp     qword [r14 + 32], 0
    je      .wdi_b_font_ok
    mov     rdx, [r14 + 32]
.wdi_b_font_ok:
    mov     rcx, r13
    call    [SelectObject]
    mov     [rsp + 96], rax
    mov     rcx, r13
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, [rsp + 80]
    lea     r9, [rsi + 40]
    mov     qword [rsp + 32], 25h
    call    [DrawTextW]
    mov     rcx, r13
    mov     rdx, [rsp + 96]
    call    [SelectObject]

.wdi_done:
    mov     eax, 1
    jmp     .wnd_proc_ret

.wnd_ctlcolor:
    mov     rcx, rbx
    mov     rdx, rsi
    mov     r8d, [rsp + 72]
    mov     r9, [rsp + 64]
    call    _pyfasm_handle_ctlcolor
    jmp     .wnd_proc_ret

.wnd_timer:
    mov     r12, [_pyfasm_timer_cnt]
    xor     r13d, r13d
.wt_loop:
    cmp     r13, r12
    jge     .wt_done
    imul    rax, r13, 24
    lea     r14, [_pyfasm_timers + rax]
    cmp     [r14 + 0], rbx
    jne     .wt_next
    mov     rcx, [r14 + 8]
    test    rcx, rcx
    jnz     .wt_kw
    mov     rcx, [_pyfasm_h_wnd]
.wt_kw:
    mov     rdx, rbx
    call    [KillTimer]
    mov     qword [r14 + 0], 0
    mov     rcx, [r14 + 16]
    mov     rdx, 8000000000000001h
    call    _pyfasm_invoke_cb
    jmp     .wt_done
.wt_next:
    inc     r13
    jmp     .wt_loop
.wt_done:
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_hscroll:
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .whs_done
    shl     rax, 6
    mov     r12, qword [_pyfasm_widget_aux + rax + 48]
    test    r12, r12
    jz      .whs_done
    mov     rax, 505946534C445221h
    cmp     [r12], rax
    jne     .whs_done
    mov     rcx, rsi
    mov     edx, 400h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    cvtsi2sd xmm0, eax
    mov     rax, 1000
    cvtsi2sd xmm1, rax
    divsd   xmm0, xmm1
    movsd   xmm1, [r12 + 16]
    subsd   xmm1, [r12 + 8]
    mulsd   xmm0, xmm1
    addsd   xmm0, [r12 + 8]
    movq    rdx, xmm0
    mov     rcx, [r12 + 24]
    call    _pyfasm_invoke_cb
.whs_done:
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_command:
    mov     rax, rbx
    shr     rax, 16
    and     eax, 0FFFFh
    mov     r12d, ebx
    and     r12d, 0FFFFh

    cmp     eax, 300h
    je      .wc_en_change
    cmp     eax, 1
    je      .wc_cbn_selchange
    test    eax, eax
    je      .wc_bn_clicked
    jmp     .cmd_done

.wc_en_change:
    cmp     dword [_pyfasm_sv_updating], 0
    jne     .cmd_done
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .cmd_done
    shl     rax, 6
    mov     r13, qword [_pyfasm_widget_aux + rax + 40]
    test    r13, r13
    jz      .cmd_done
    mov     dword [_pyfasm_sv_updating], 1
    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 1024
    call    [GetWindowTextW]
    lea     rcx, [_pyfasm_wide_buf]
    call    _pyfasm_wide_to_utf8
    mov     [r13 + 8], rax
    mov     rcx, r13
    call    _pyfasm_fire_sv_traces
    mov     dword [_pyfasm_sv_updating], 0
    jmp     .cmd_done

.wc_cbn_selchange:
    mov     rcx, rsi
    mov     edx, 147h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    cmp     eax, 0
    jl      .cmd_done
    mov     rcx, rsi
    mov     edx, 148h
    mov     r8d, eax
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    lea     rcx, [_pyfasm_wide_buf]
    call    _pyfasm_wide_to_utf8
    mov     r13, rax
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .wc_cbn_cb
    shl     rax, 6
    mov     rcx, qword [_pyfasm_widget_aux + rax + 40]
    test    rcx, rcx
    jz      .wc_cbn_cb
    mov     rdx, r13
    call    _pyfasm_unified_set
.wc_cbn_cb:
    mov     r14, [_pyfasm_ctrl_count]
    xor     ecx, ecx
.wc_cbn_loop:
    cmp     rcx, r14
    jge     .cmd_done
    cmp     [_pyfasm_ctrl_hwnds + rcx*8], rsi
    je      .wc_cbn_hit
    cmp     [_pyfasm_ctrl_ids + rcx*4], r12d
    je      .wc_cbn_hit
    inc     rcx
    jmp     .wc_cbn_loop
.wc_cbn_hit:
    mov     rcx, [_pyfasm_ctrl_callbacks + rcx*8]
    mov     rdx, r13
    call    _pyfasm_invoke_cb
    jmp     .cmd_done

.wc_bn_clicked:
    mov     r13, [_pyfasm_seg_cnt]
    xor     r14d, r14d
.wc_seg_outer:
    cmp     r14, r13
    jge     .wc_std_ctrl
    mov     rax, r14
    shl     rax, 7
    lea     rbx, [_pyfasm_segs + rax]
    mov     rcx, [rbx + 8]
    xor     edx, edx
.wc_seg_inner:
    cmp     rdx, rcx
    jge     .wc_seg_next
    cmp     [rbx + 40 + rdx*8], rsi
    je      .wc_seg_hit
    inc     rdx
    jmp     .wc_seg_inner
.wc_seg_next:
    inc     r14
    jmp     .wc_seg_outer

.wc_seg_hit:
    mov     [rbx + 16], rdx
    xor     r14d, r14d
.wc_seg_recol:
    cmp     r14, [rbx + 8]
    jge     .wc_seg_text
    mov     rcx, [rbx + 40 + r14*8]
    cmp     [rbx + 16], r14
    jne     .wc_seg_unsel
    mov     edx, [_pyfasm_theme_accent]
    mov     r8, 01000000h
    or      rdx, r8
    mov     r9, rdx
    shl     r9, 32
    or      rdx, r9
    mov     r8, 8000000000000000h
    or      rdx, r8
    xor     r8d, r8d
    jmp     .wc_seg_setc
.wc_seg_unsel:
    mov     edx, [_pyfasm_theme_card]
    mov     r8, 01000000h
    or      rdx, r8
    mov     r9, rdx
    shl     r9, 32
    or      rdx, r9
    mov     r8, 8000000000000000h
    or      rdx, r8
    mov     r8d, [_pyfasm_theme_text]
    mov     r9, 01000000h
    or      r8, r9
    mov     r9, r8
    shl     r9, 32
    or      r8, r9
    mov     r9, 8000000000000000h
    or      r8, r9
.wc_seg_setc:
    call    _pyfasm_widget_set_colors
    inc     r14
    jmp     .wc_seg_recol

.wc_seg_text:
    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    [GetWindowTextW]
    lea     rcx, [_pyfasm_wide_buf]
    call    _pyfasm_wide_to_utf8
    mov     r13, rax
    mov     rcx, [rbx + 32]
    test    rcx, rcx
    jz      .wc_seg_cb
    mov     rdx, r13
    call    _pyfasm_unified_set
.wc_seg_cb:
    mov     rcx, [rbx + 24]
    mov     rdx, r13
    call    _pyfasm_invoke_cb
    jmp     .cmd_done

.wc_std_ctrl:
    mov     r14, [_pyfasm_ctrl_count]
    xor     ecx, ecx
.wc_loop:
    cmp     rcx, r14
    jge     .cmd_done
    cmp     [_pyfasm_ctrl_hwnds + rcx*8], rsi
    je      .wc_found
    cmp     dword [_pyfasm_ctrl_ids + rcx*4], r12d
    je      .wc_found
    inc     rcx
    jmp     .wc_loop
.wc_found:
    mov     rcx, [_pyfasm_ctrl_callbacks + rcx*8]
    mov     rdx, 8000000000000001h
    call    _pyfasm_invoke_cb

.cmd_done:
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_hotkey:
    xor     eax, eax

.wnd_proc_ret:
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

; ============================================================
; Native Windows Taskbar System Tray Engine (Punto Switcher)
; ============================================================
_pyfasm_init_tray:
    push    rbp
    mov     rbp, rsp
    push    r12
    push    rsi
    push    rdi
    sub     rsp, 128
    and     rsp, -16

    cmp     qword [_pyfasm_tray_hwnd], 0
    jne     .tray_done

    xor     ecx, ecx
    call    [GetModuleHandleA]
    mov     [_pyfasm_h_inst], rax

    ; Setup WNDCLASSEXW for hidden message-only window
    mov     dword [_pyfasm_tray_wc], 80
    mov     dword [_pyfasm_tray_wc + 4], 0
    lea     rax, [_pyfasm_tray_wnd_proc]
    mov     qword [_pyfasm_tray_wc + 8], rax
    mov     dword [_pyfasm_tray_wc + 16], 0
    mov     dword [_pyfasm_tray_wc + 20], 0
    mov     rax, [_pyfasm_h_inst]
    mov     qword [_pyfasm_tray_wc + 24], rax
    mov     qword [_pyfasm_tray_wc + 32], 0
    mov     qword [_pyfasm_tray_wc + 40], 0
    mov     qword [_pyfasm_tray_wc + 48], 0
    mov     qword [_pyfasm_tray_wc + 56], 0
    lea     rax, [_pyfasm_tray_class_w]
    mov     qword [_pyfasm_tray_wc + 64], rax
    mov     qword [_pyfasm_tray_wc + 72], 0

    lea     rcx, [_pyfasm_tray_wc]
    call    [RegisterClassExW]

    ; Create Hidden Top-Level Window (WS_POPUP = 80000000h)
    xor     ecx, ecx
    lea     rdx, [_pyfasm_tray_class_w]
    lea     r8, [wszTrayTipOn]
    mov     r9d, 80000000h      ; WS_POPUP (required for Shell_NotifyIcon to attach cleanly)
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 0
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_tray_hwnd], rax

    ; Register Global Hotkeys: Pause/Break (0x13), F8 (0x77)
    mov     rcx, [_pyfasm_tray_hwnd]
    mov     edx, 101
    mov     r8d, 4000h          ; MOD_NOREPEAT
    mov     r9d, 13h            ; VK_PAUSE
    call    [RegisterHotKey]

    mov     rcx, [_pyfasm_tray_hwnd]
    mov     edx, 102
    mov     r8d, 4000h          ; MOD_NOREPEAT
    mov     r9d, 77h            ; VK_F8
    call    [RegisterHotKey]

    ; Load Tray Icon
    xor     ecx, ecx
    lea     rdx, [wszTrayIconFile]
    mov     r8d, 1              ; IMAGE_ICON
    mov     r9d, 16             ; cx
    mov     qword [rsp + 32], 16 ; cy
    mov     qword [rsp + 40], 10h ; LR_LOADFROMFILE
    call    [LoadImageW]
    mov     r12, rax
    test    r12, r12
    jnz     .icon_loaded

    ; Fallback to LoadIconW with IDI_INFORMATION (32516 - clear visible icon)
    xor     ecx, ecx
    mov     edx, 32516          ; IDI_INFORMATION
    call    [LoadIconW]
    mov     r12, rax

.icon_loaded:
    ; Init NOTIFYICONDATAW (V4 = 976 bytes on Win64)
    mov     dword [_pyfasm_tray_nid], 976
    mov     rax, [_pyfasm_tray_hwnd]
    mov     qword [_pyfasm_tray_nid + 8], rax
    mov     dword [_pyfasm_tray_nid + 16], 1
    mov     dword [_pyfasm_tray_nid + 20], 7 ; NIF_ICON | NIF_MESSAGE | NIF_TIP
    mov     dword [_pyfasm_tray_nid + 24], 464h ; WM_USER + 100
    mov     qword [_pyfasm_tray_nid + 32], r12

    lea     rsi, [wszTrayTipOn]
    lea     rdi, [_pyfasm_tray_nid + 40]
    mov     ecx, 64
.cpy_tip:
    mov     ax, [rsi]
    mov     [rdi], ax
    add     rsi, 2
    add     rdi, 2
    dec     ecx
    jnz     .cpy_tip

    xor     ecx, ecx            ; NIM_ADD
    lea     rdx, [_pyfasm_tray_nid]
    call    [Shell_NotifyIconW]

.tray_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     r12
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_run_tray_loop:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16

    call    _pyfasm_init_tray

.tray_msg_loop:
    lea     rcx, [_pyfasm_msg]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [GetMessageW]
    test    eax, eax
    jle     .tray_loop_done

    lea     rcx, [_pyfasm_msg]
    call    [TranslateMessage]

    lea     rcx, [_pyfasm_msg]
    call    [DispatchMessageW]
    jmp     .tray_msg_loop

.tray_loop_done:
    mov     ecx, 2              ; NIM_DELETE
    lea     rdx, [_pyfasm_tray_nid]
    call    [Shell_NotifyIconW]

    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_tray_wnd_proc:
    push    rbp
    mov     rbp, rsp
    push    r12
    push    rsi
    push    rdi
    push    rbx
    push    r13
    sub     rsp, 64
    and     rsp, -16

    cmp     edx, 312h           ; WM_HOTKEY
    je      .thotkey
    cmp     edx, 464h           ; WM_USER + 100 (tray notification)
    je      .ttray_event
    cmp     edx, 111h           ; WM_COMMAND
    je      .ttray_cmd
    cmp     edx, 2              ; WM_DESTROY
    je      .tdestroy

    call    [DefWindowProcW]
    jmp     .tret

.thotkey:
    ; Pause/Break or F8 pressed!
    cmp     dword [_pyfasm_tray_sound], 1
    jne     .skip_thotkey_beep
    mov     ecx, -1
    call    [MessageBeep]
.skip_thotkey_beep:
    call    [GetForegroundWindow]
    test    rax, rax
    jz      .skip_post_lang
    mov     rbx, rax

    mov     rcx, rbx
    mov     edx, 50h                ; WM_INPUTLANGCHANGEREQUEST
    xor     r8d, r8d
    mov     r9, 2                   ; INPUTLANGCHANGE_FORWARD
    call    [PostMessageW]

    call    [GetCurrentThreadId]
    mov     r12d, eax
    mov     rcx, rbx
    xor     edx, edx
    call    [GetWindowThreadProcessId]
    mov     r13d, eax
    test    r13d, r13d
    jz      .skip_post_lang
    cmp     r12d, r13d
    je      .skip_post_lang

    mov     ecx, r12d
    mov     edx, r13d
    mov     r8d, 1
    call    [AttachThreadInput]

    mov     ecx, 1                  ; HKL_NEXT
    xor     edx, edx
    call    [ActivateKeyboardLayout]

    mov     ecx, r12d
    mov     edx, r13d
    xor     r8d, r8d
    call    [AttachThreadInput]

.skip_post_lang:
    mov     ecx, 1                  ; HKL_NEXT
    xor     edx, edx
    call    [ActivateKeyboardLayout]
    xor     eax, eax
    jmp     .tret

.ttray_event:
    cmp     r9w, 202h           ; WM_LBUTTONUP
    je      .ttoggle_auto
    cmp     r9w, 205h           ; WM_RBUTTONUP
    je      .tshow_menu
    xor     eax, eax
    jmp     .tret

.ttoggle_auto:
    xor     dword [_pyfasm_tray_enabled], 1
    cmp     dword [_pyfasm_tray_sound], 1
    jne     .no_tsnd
    mov     ecx, -1
    call    [MessageBeep]
.no_tsnd:
    cmp     dword [_pyfasm_tray_enabled], 1
    je      .ttip_on
    lea     rsi, [wszTrayTipOff]
    jmp     .apply_ttip
.ttip_on:
    lea     rsi, [wszTrayTipOn]
.apply_ttip:
    lea     rdi, [_pyfasm_tray_nid + 40]
    mov     ecx, 64
.ttip_loop:
    mov     ax, [rsi]
    mov     [rdi], ax
    add     rsi, 2
    add     rdi, 2
    dec     ecx
    jnz     .ttip_loop

    mov     ecx, 1              ; NIM_MODIFY
    lea     rdx, [_pyfasm_tray_nid]
    call    [Shell_NotifyIconW]
    xor     eax, eax
    jmp     .tret

.tshow_menu:
    call    [CreatePopupMenu]
    mov     r12, rax

    mov     rcx, r12
    xor     edx, edx
    cmp     dword [_pyfasm_tray_enabled], 1
    jne     .tm_no_auto
    mov     edx, 8              ; MF_CHECKED
.tm_no_auto:
    mov     r8d, 201
    lea     r9, [wszMenuAuto]
    call    [AppendMenuW]

    mov     rcx, r12
    xor     edx, edx
    cmp     dword [_pyfasm_tray_sound], 1
    jne     .tm_no_snd
    mov     edx, 8              ; MF_CHECKED
.tm_no_snd:
    mov     r8d, 202
    lea     r9, [wszMenuSound]
    call    [AppendMenuW]

    mov     rcx, r12
    mov     edx, 800h           ; MF_SEPARATOR
    xor     r8d, r8d
    xor     r9d, r9d
    call    [AppendMenuW]

    mov     rcx, r12
    mov     edx, 1              ; MF_GRAYED
    mov     r8d, 203
    lea     r9, [wszMenuHotkey]
    call    [AppendMenuW]

    mov     rcx, r12
    mov     edx, 800h           ; MF_SEPARATOR
    xor     r8d, r8d
    xor     r9d, r9d
    call    [AppendMenuW]

    mov     rcx, r12
    xor     edx, edx
    mov     r8d, 204
    lea     r9, [wszMenuExit]
    call    [AppendMenuW]

    lea     rcx, [_pyfasm_cursor_pt]
    call    [GetCursorPos]

    mov     rcx, [_pyfasm_tray_hwnd]
    call    [SetForegroundWindow]

    mov     rcx, r12
    mov     edx, 2              ; TPM_RIGHTBUTTON
    mov     r8d, dword [_pyfasm_cursor_pt]
    mov     r9d, dword [_pyfasm_cursor_pt + 4]
    mov     qword [rsp + 32], 0
    mov     rax, [_pyfasm_tray_hwnd]
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    call    [TrackPopupMenu]

    mov     rcx, r12
    call    [DestroyMenu]
    xor     eax, eax
    jmp     .tret

.ttray_cmd:
    movzx   eax, r8w
    cmp     eax, 201
    je      .ttoggle_auto
    cmp     eax, 202
    jne     .chk_tcmd_exit
    xor     dword [_pyfasm_tray_sound], 1
    jmp     .tret
.chk_tcmd_exit:
    cmp     eax, 204
    jne     .tret
    mov     ecx, 2              ; NIM_DELETE
    lea     rdx, [_pyfasm_tray_nid]
    call    [Shell_NotifyIconW]
    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax
    jmp     .tret

.tdestroy:
    mov     ecx, 2
    lea     rdx, [_pyfasm_tray_nid]
    call    [Shell_NotifyIconW]
    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax
    jmp     .tret

.tret:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     rbx
    pop     rdi
    pop     rsi
    pop     r12
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_message_box:
    ; RCX = title, RDX = message
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rsi, rcx
    mov     rdi, rdx

    ; Convert message (RDX) to wide buffer
    mov     rcx, rdi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

    ; Convert title (RCX) to wide buffer
    mov     rcx, rsi
    lea     rdx, [_pyfasm_edit_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

    xor     ecx, ecx                ; hWnd = 0
    lea     rdx, [_pyfasm_wide_buf] ; lpText
    lea     r8, [_pyfasm_edit_buf]  ; lpCaption
    xor     r9d, r9d                ; uType = MB_OK (0)
    call    [MessageBoxW]

    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_slice:
    ; RCX = UTF-8 str pointer, RDX = lower, R8 = upper, R9 = step
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 96
    and     rsp, -16

    test    rcx, rcx
    jz      .ss_null

    mov     rsi, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     r14, r9
    test    r14, r14
    jnz     .ss_step_nz
    mov     r14, 1
.ss_step_nz:
    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     [rsp + 64], rax         ; byte_len
    test    rax, rax
    jnz     .ss_nonempty
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    jmp     .ss_exit

.ss_nonempty:
    lea     rcx, [rax * 8 + 16]
    call    _pyfasm_alloc
    mov     r15, rax                ; offsets array
    xor     edx, edx                ; byte index
    xor     ebx, ebx                ; codepoint count
    mov     r8, [rsp + 64]
.ss_scan_cp:
    cmp     rdx, r8
    jae     .ss_scan_done
    mov     al, byte [rsi + rdx]
    and     al, 0C0h
    cmp     al, 80h
    je      .ss_scan_next
    mov     [r15 + rbx * 8], rdx
    inc     rbx
.ss_scan_next:
    inc     rdx
    jmp     .ss_scan_cp
.ss_scan_done:
    mov     [r15 + rbx * 8], r8     ; sentinel byte_len

    mov     rcx, r8
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rsp + 48], rax         ; out_buf base

    cmp     r14, 0
    jl      .ss_neg_step

    ; Forward slice (r14 > 0)
    cmp     r12, 0
    jge     .ss_pos_l_ge0
    add     r12, rbx
    cmp     r12, 0
    jge     .ss_pos_l_ge0
    xor     r12, r12
.ss_pos_l_ge0:
    cmp     r12, rbx
    jle     .ss_pos_l_ok
    mov     r12, rbx
.ss_pos_l_ok:
    cmp     r13, -999999
    jne     .ss_pos_chk_u
    mov     r13, rbx
    jmp     .ss_pos_u_ok
.ss_pos_chk_u:
    cmp     r13, 0
    jge     .ss_pos_u_ge0
    add     r13, rbx
    cmp     r13, 0
    jge     .ss_pos_u_ge0
    xor     r13, r13
.ss_pos_u_ge0:
    cmp     r13, rbx
    jle     .ss_pos_u_ok
    mov     r13, rbx
.ss_pos_u_ok:
.ss_pos_loop:
    cmp     r12, r13
    jge     .ss_done_copy
    mov     r8, [r15 + r12 * 8]
    mov     r9, [r15 + r12 * 8 + 8]
    sub     r9, r8
    mov     r10, rsi
    add     r10, r8
    xor     ecx, ecx
.ss_pos_cp:
    cmp     rcx, r9
    jae     .ss_pos_cp_done
    mov     al, byte [r10 + rcx]
    mov     byte [rdi], al
    inc     rdi
    inc     rcx
    jmp     .ss_pos_cp
.ss_pos_cp_done:
    add     r12, r14
    jmp     .ss_pos_loop

.ss_neg_step:
    cmp     r12, 0
    jne     .ss_neg_norm_l
    cmp     r13, -999999
    jne     .ss_neg_norm_l
    lea     r12, [rbx - 1]
    mov     r13, -1
    jmp     .ss_neg_loop

.ss_neg_norm_l:
    cmp     r12, 0
    jge     .ss_neg_l_ge0
    add     r12, rbx
    cmp     r12, -1
    jge     .ss_neg_l_ge0
    mov     r12, -1
.ss_neg_l_ge0:
    cmp     r12, rbx
    jl      .ss_neg_l_ok
    lea     r12, [rbx - 1]
.ss_neg_l_ok:
    cmp     r13, -999999
    jne     .ss_neg_chk_u
    mov     r13, -1
    jmp     .ss_neg_loop
.ss_neg_chk_u:
    cmp     r13, 0
    jge     .ss_neg_u_ge0
    add     r13, rbx
    cmp     r13, -1
    jge     .ss_neg_u_ge0
    mov     r13, -1
.ss_neg_u_ge0:
    cmp     r13, rbx
    jl      .ss_neg_loop
    lea     r13, [rbx - 1]

.ss_neg_loop:
    cmp     r12, r13
    jle     .ss_done_copy
    cmp     r12, 0
    jl      .ss_done_copy
    mov     r8, [r15 + r12 * 8]
    mov     r9, [r15 + r12 * 8 + 8]
    sub     r9, r8
    mov     r10, rsi
    add     r10, r8
    xor     ecx, ecx
.ss_neg_cp:
    cmp     rcx, r9
    jae     .ss_neg_cp_done
    mov     al, byte [r10 + rcx]
    mov     byte [rdi], al
    inc     rdi
    inc     rcx
    jmp     .ss_neg_cp
.ss_neg_cp_done:
    add     r12, r14
    jmp     .ss_neg_loop

.ss_done_copy:
    mov     byte [rdi], 0
    mov     rax, [rsp + 48]
    jmp     .ss_exit

.ss_null:
    xor     eax, eax
.ss_exit:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_slice:
    ; RCX = list pointer, RDX = lower, R8 = upper, R9 = step
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .ls_null

    mov     rsi, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     r14, r9

    mov     r15, [rsi]

    test    r14, r14
    jnz     .l_check_step
    mov     r14, 1
.l_check_step:
    cmp     r14, -1
    jne     .l_fwd_slice

    mov     rcx, r15
    inc     rcx
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rdi], r15
    mov     r10, rax

    mov     rcx, r15
    test    rcx, rcx
    jz      .l_rev_done

    lea     rbx, [rsi + r15 * 8]
    lea     rdi, [rdi + 8]
.l_rev_loop:
    mov     rax, [rbx]
    mov     [rdi], rax
    add     rdi, 8
    sub     rbx, 8
    dec     rcx
    jnz     .l_rev_loop
.l_rev_done:
    mov     rax, r10
    jmp     .ls_exit

.l_fwd_slice:
    cmp     r12, 0
    jge     .ll_pos
    add     r12, r15
    cmp     r12, 0
    jge     .ll_pos
    xor     r12, r12
.ll_pos:
    cmp     r12, r15
    jle     .ll_clamp
    mov     r12, r15
.ll_clamp:
    cmp     r13, -999999
    jne     .l_chk_u_neg
    mov     r13, r15
    jmp     .ll_u_clamp
.l_chk_u_neg:
    cmp     r13, 0
    jge     .ll_u_pos
    add     r13, r15
    cmp     r13, 0
    jge     .ll_u_pos
    xor     r13, r13
.ll_u_pos:
    cmp     r13, r15
    jle     .ll_u_clamp
    mov     r13, r15
.ll_u_clamp:
    mov     rax, r13
    sub     rax, r12
    jge     .l_sl_ok
    xor     eax, eax
.l_sl_ok:
    mov     rbx, rax

    mov     rcx, rbx
    inc     rcx
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rdi], rbx
    mov     r10, rax

    test    rbx, rbx
    jz      .l_copy_done
    lea     rsi, [rsi + r12 * 8 + 8]
    lea     rdi, [rdi + 8]
    mov     rcx, rbx
    rep     movsq
.l_copy_done:
    mov     rax, r10
    jmp     .ls_exit

.ls_null:
    xor     eax, eax
.ls_exit:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    pop     rbp
    ret

"""


def get_win64_dll_entry() -> str:
    return """
proc DllEntryPoint hinstDLL, fdwReason, lpvReserved
    mov eax, 1
    ret
endp
"""


def get_win64_export_section(dll_name: str, function_names: list[str]) -> str:
    """Emits the PE64 .edata export section."""
    if not function_names:
        return ""
    from pyfasm.codegen_x64 import safe_asm_label
    exports = []
    for fn in function_names:
        safe_fn = safe_asm_label(fn)
        exports.append(f"           {safe_fn}, '{fn}'")
    exports_str = ", \\\n".join(exports)
    return f"""
section '.edata' export data readable
    export '{dll_name}', \\
{exports_str}
"""


def _get_win64_full_runtime_imports() -> str:
    """Returns the IData section with Win32 API imports."""
    return """
section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', \\
            user32, 'USER32.DLL', \\
            gdi32, 'GDI32.DLL', \\
            comdlg32, 'COMDLG32.DLL', \\
            shell32, 'SHELL32.DLL', \\
            dwmapi, 'DWMAPI.DLL', \\
            uxtheme, 'UXTHEME.DLL', \\
            advapi32, 'ADVAPI32.DLL', \\
            wininet, 'WININET.DLL'

    import kernel32, \\
           GetStdHandle, 'GetStdHandle', \\
           WriteFile, 'WriteFile', \\
           ReadFile, 'ReadFile', \\
           CreateFileA, 'CreateFileA', \\
           GetFileSize, 'GetFileSize', \\
           SetFilePointer, 'SetFilePointer', \\
           GetTickCount64, 'GetTickCount64', \\
           Sleep, 'Sleep', \\
           VirtualAlloc, 'VirtualAlloc', \\
           VirtualFree, 'VirtualFree', \\
           VirtualQuery, 'VirtualQuery', \\
           CreateThread, 'CreateThread', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           GetModuleHandleA, 'GetModuleHandleA', \\
           MultiByteToWideChar, 'MultiByteToWideChar', \\
           WideCharToMultiByte, 'WideCharToMultiByte', \\
           SetConsoleOutputCP, 'SetConsoleOutputCP', \\
           SetConsoleCP, 'SetConsoleCP', \\
           GetConsoleMode, 'GetConsoleMode', \\
           WriteConsoleW, 'WriteConsoleW', \\
           ReadConsoleW, 'ReadConsoleW', \\
           GetCurrentThreadId, 'GetCurrentThreadId', \\
           LoadLibraryA, 'LoadLibraryA', \\
           GetProcAddress, 'GetProcAddress', \\
           FreeLibrary, 'FreeLibrary', \\
           ExitProcess, 'ExitProcess'

    import user32, \\
           MessageBoxA, 'MessageBoxA', \\
           MessageBoxW, 'MessageBoxW', \\
           RegisterClassExA, 'RegisterClassExA', \\
           RegisterClassExW, 'RegisterClassExW', \\
           CreateWindowExA, 'CreateWindowExA', \\
           CreateWindowExW, 'CreateWindowExW', \\
           ShowWindow, 'ShowWindow', \\
           SetWindowPos, 'SetWindowPos', \\
           UpdateWindow, 'UpdateWindow', \\
           SetForegroundWindow, 'SetForegroundWindow', \\
           SetWindowTextA, 'SetWindowTextA', \\
           SetWindowTextW, 'SetWindowTextW', \\
           GetWindowTextA, 'GetWindowTextA', \\
           GetWindowTextW, 'GetWindowTextW', \\
           SendMessageA, 'SendMessageA', \\
           SendMessageW, 'SendMessageW', \\
           RegisterHotKey, 'RegisterHotKey', \\
           UnregisterHotKey, 'UnregisterHotKey', \\
           AttachThreadInput, 'AttachThreadInput', \\
           GetWindowThreadProcessId, 'GetWindowThreadProcessId', \\
           LoadCursorA, 'LoadCursorA', \\
           LoadIconA, 'LoadIconA', \\
           LoadIconW, 'LoadIconW', \\
           LoadImageW, 'LoadImageW', \\
           FillRect, 'FillRect', \\
           DrawTextW, 'DrawTextW', \\
           GetClientRect, 'GetClientRect', \\
           GetForegroundWindow, 'GetForegroundWindow', \\
           PostMessageW, 'PostMessageW', \\
           GetMessageA, 'GetMessageA', \\
           GetMessageW, 'GetMessageW', \\
           TranslateMessage, 'TranslateMessage', \\
           DispatchMessageA, 'DispatchMessageA', \\
           DispatchMessageW, 'DispatchMessageW', \\
           DefWindowProcA, 'DefWindowProcA', \\
           DefWindowProcW, 'DefWindowProcW', \\
           PostQuitMessage, 'PostQuitMessage', \\
           MessageBeep, 'MessageBeep', \\
           CreatePopupMenu, 'CreatePopupMenu', \\
           AppendMenuW, 'AppendMenuW', \\
           TrackPopupMenu, 'TrackPopupMenu', \\
           DestroyMenu, 'DestroyMenu', \\
           GetCursorPos, 'GetCursorPos', \\
           ActivateKeyboardLayout, 'ActivateKeyboardLayout', \\
           GetDC, 'GetDC', \\
           ReleaseDC, 'ReleaseDC', \\
           PeekMessageW, 'PeekMessageW', \\
           GetAsyncKeyState, 'GetAsyncKeyState', \\
           ScreenToClient, 'ScreenToClient', \\
           DestroyWindow, 'DestroyWindow', \\
           AdjustWindowRectEx, 'AdjustWindowRectEx', \\
           InvalidateRect, 'InvalidateRect', \\
           BeginPaint, 'BeginPaint', \\
           EndPaint, 'EndPaint', \\
           GetParent, 'GetParent', \\
           SetParent, 'SetParent', \\
           MoveWindow, 'MoveWindow', \\
           FrameRect, 'FrameRect', \\
           SetTimer, 'SetTimer', \\
           KillTimer, 'KillTimer', \\
           EnableWindow, 'EnableWindow', \\
           GetKeyState, 'GetKeyState'

    import gdi32, \\
           CreateSolidBrush, 'CreateSolidBrush', \\
           CreatePen, 'CreatePen', \\
           RoundRect, 'RoundRect', \\
           SetTextColor, 'SetTextColor', \\
           SetBkColor, 'SetBkColor', \\
           SetBkMode, 'SetBkMode', \\
           CreateFontW, 'CreateFontW', \\
           DeleteObject, 'DeleteObject', \\
           SelectObject, 'SelectObject', \\
           GetStockObject, 'GetStockObject', \\
           MoveToEx, 'MoveToEx', \\
           LineTo, 'LineTo', \\
           Rectangle, 'Rectangle', \\
           Ellipse, 'Ellipse', \\
           TextOutW, 'TextOutW', \\
           GetTextExtentPoint32W, 'GetTextExtentPoint32W', \\
           Polygon, 'Polygon', \\
           Polyline, 'Polyline', \\
           Arc, 'Arc', \\
           CreateDIBSection, 'CreateDIBSection', \\
           StretchBlt, 'StretchBlt', \\
           SetDIBitsToDevice, 'SetDIBitsToDevice', \\
           ExtTextOutW, 'ExtTextOutW', \\
           CreateCompatibleDC, 'CreateCompatibleDC', \\
           CreateCompatibleBitmap, 'CreateCompatibleBitmap', \\
           BitBlt, 'BitBlt', \\
           DeleteDC, 'DeleteDC'

    import comdlg32, \\
           GetOpenFileNameW, 'GetOpenFileNameW', \\
           GetSaveFileNameW, 'GetSaveFileNameW'

    import shell32, \\
           Shell_NotifyIconW, 'Shell_NotifyIconW', \\
           Shell_NotifyIconA, 'Shell_NotifyIconA'

    import dwmapi, \\
           DwmSetWindowAttribute, 'DwmSetWindowAttribute'

    import uxtheme, \\
           SetWindowTheme, 'SetWindowTheme' 

    import advapi32, \\
           RegOpenKeyExA, 'RegOpenKeyExA', \\
           RegQueryValueExA, 'RegQueryValueExA', \\
           RegCloseKey, 'RegCloseKey'

    import wininet, \\
           InternetOpenA, 'InternetOpenA', \\
           InternetOpenUrlA, 'InternetOpenUrlA', \\
           InternetReadFile, 'InternetReadFile', \\
           InternetCloseHandle, 'InternetCloseHandle'
"""


from typing import Optional, Set

_WIN64_CONSOLE_RUNTIME_DATA = """
section '.data' data readable writeable
    hStdOut         dq 0
    hStdIn          dq 0
    bytesWritten    dq 0
    bytesRead       dq 0
    crlf_str        db 13, 10, 0
    minus_str       db '-', 0
    dot_str         db '.', 0
    none_str        db 'None', 0
    szNanoGemmISA   db 'AVX2+FMA (PyFASM NanoGEMM Native SIMD)', 0
    flt_1m          dq 1000000.0
    flt_ten         dq 10.0
    flt_zero        dq 0.0
    lbrack_str      db '[', 0
    rbrack_str      db ']', 0
    lbrace_str      db '{', 0
    rbrace_str      db '}', 0
    lparen_str      db '(', 0
    rparen_str      db ')', 0
    comma_str       db ',', 0
    comma_sp_str    db ', ', 0
    colon_sp_str    db ': ', 0
    squote_str      db 39, 0
    empty_set_str   db 'set()', 0
    align 8
    inp_buf         rb 4096
    align 8
    inp_wbuf        rw 2048
    align 4
    consoleMode     dd 0
    isStdOutConsole dd 0
    isStdInConsole  dd 0
    align 8
    _pyfasm_int_buf rb 32
"""

_WIN64_NET_RUNTIME_DATA = """
    ; WinINet HTTP Client & Response Data
    _pyfasm_http_agent      db 'PyFASM-Native/1.0', 0
    _pyfasm_http_ok_str     db 'OK', 0
    _pyfasm_http_err_str    db 'Error', 0
    align 4
    _pyfasm_http_read_bytes dd 0
    align 8
    _pyfasm_http_resp_obj   dq 0, 0, 0, 0 ; [status_code, text, json, reason]
    align 8
    _pyfasm_http_buf        rb 65536 ; 64KB HTTP response buffer
    align 8
    _pyfasm_http_url_buf    rb 2048  ; 2KB URL + query params buffer
    align 8
    _pyfasm_strip_buf       rb 65536
"""

_WIN64_CONSOLE_RUNTIME_CODE = """section '.text' code readable executable

_pyfasm_init_io:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, 65001              ; CP_UTF8
    call    [SetConsoleOutputCP]
    mov     ecx, 65001              ; CP_UTF8
    call    [SetConsoleCP]
    mov     ecx, -11                ; STD_OUTPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdOut], rax
    mov     rcx, rax
    lea     rdx, [consoleMode]
    call    [GetConsoleMode]
    mov     [isStdOutConsole], eax
    mov     ecx, -10                ; STD_INPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdIn], rax
    mov     rcx, rax
    lea     rdx, [consoleMode]
    call    [GetConsoleMode]
    mov     [isStdInConsole], eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_str:
    ; RCX = pointer to null-terminated UTF-8 string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .done_print_str

    ; Calculate UTF-8 byte length
    xor     eax, eax
    mov     rdi, rsi
    mov     rcx, -1
    repne   scasb
    not     rcx
    dec     rcx
    mov     rbx, rcx                ; byte length in rbx
    test    rbx, rbx
    jz      .done_print_str

    cmp     dword [isStdOutConsole], 0
    je      .print_str_file
    cmp     rbx, 32768
    ja      .print_str_file

    ; Query UTF-16 character count
    mov     ecx, 65001              ; CP_UTF8
    xor     edx, edx
    mov     r8, rsi
    mov     r9d, ebx
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    call    [MultiByteToWideChar]
    test    eax, eax
    jle     .print_str_file
    cmp     eax, 1024
    jg      .print_str_file

    mov     r12d, eax
    sub     rsp, 2112               ; shadow (32) + args (32) + 1024 wchars (2048), 16-byte aligned
    mov     ecx, 65001
    xor     edx, edx
    mov     r8, rsi
    mov     r9d, ebx
    lea     rax, [rsp + 64]
    mov     [rsp + 32], rax
    mov     [rsp + 40], r12
    call    [MultiByteToWideChar]
    test    eax, eax
    jle     .print_str_console_fail

    mov     rcx, [hStdOut]
    lea     rdx, [rsp + 64]
    mov     r8d, eax
    lea     r9, [rsp + 48]
    mov     dword [rsp + 48], 0
    mov     qword [rsp + 32], 0
    call    [WriteConsoleW]
    test    eax, eax
    jz      .print_str_console_fail
    add     rsp, 2112
    jmp     .done_print_str

.print_str_console_fail:
    add     rsp, 2112

.print_str_file:
    ; WriteFile(hStdOut, rsi, rbx, &bytesWritten, NULL)
    mov     rcx, [hStdOut]
    mov     rdx, rsi
    mov     r8, rbx
    lea     r9, [rsp + 48]
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 32], 0
    call    [WriteFile]

.done_print_str:
    lea     rsp, [rbp - 32]
    pop     r12
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
    test    rcx, rcx
    jz      .sl_zero
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
.sl_zero:
    xor     eax, eax
    ret

_pyfasm_utf8_len:
    ; RCX = pointer to null-terminated UTF-8 string -> RAX = codepoint count
    test    rcx, rcx
    jz      .ul_zero
    xor     eax, eax
.ul_loop:
    movzx   edx, byte [rcx]
    test    dl, dl
    jz      .ul_done
    and     dl, 0C0h
    cmp     dl, 80h
    je      .ul_cont
    inc     rax
.ul_cont:
    inc     rcx
    jmp     .ul_loop
.ul_zero:
    xor     eax, eax
.ul_done:
    ret

_pyfasm_utf8_getitem:
    ; RCX = str_ptr, RDX = signed codepoint index
    ; Returns RAX = heap-allocated 1-codepoint UTF-8 string (or "" if out of range)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     r12, rdx
    test    rsi, rsi
    jz      .ug_empty
    cmp     r12, 0
    jge     .ug_nonneg
    mov     rcx, rsi
    call    _pyfasm_utf8_len
    add     r12, rax
    cmp     r12, 0
    jl      .ug_empty

.ug_nonneg:
    xor     r13d, r13d
.ug_scan:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .ug_empty
    mov     edx, eax
    and     dl, 0C0h
    cmp     dl, 80h
    je      .ug_step_only
    cmp     r13, r12
    je      .ug_found
    inc     r13
.ug_step_only:
    inc     rsi
    jmp     .ug_scan

.ug_found:
    movzx   eax, byte [rsi]
    mov     rbx, 1
    cmp     al, 0C2h
    jb      .ug_alloc
    cmp     al, 0DFh
    jbe     .ug_len2
    cmp     al, 0EFh
    jbe     .ug_len3
    cmp     al, 0F4h
    jbe     .ug_len4
    jmp     .ug_alloc
.ug_len2:
    mov     rbx, 2
    jmp     .ug_clamp
.ug_len3:
    mov     rbx, 3
    jmp     .ug_clamp
.ug_len4:
    mov     rbx, 4
.ug_clamp:
    mov     r13, 1
.ug_chk:
    cmp     r13, rbx
    jae     .ug_alloc
    cmp     byte [rsi + r13], 0
    je      .ug_trunc
    inc     r13
    jmp     .ug_chk
.ug_trunc:
    mov     rbx, r13

.ug_alloc:
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ug_cp:
    cmp     rcx, rbx
    jae     .ug_nul
    mov     dl, byte [rsi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ug_cp
.ug_nul:
    mov     byte [rax + rbx], 0
    jmp     .ug_ret

.ug_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.ug_ret:
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    sub     rsp, 64
    and     rsp, -16
    ucomisd xmm0, [flt_zero]
    jae     .flt_pos
    movsd   [rbp - 24], xmm0
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    movsd   xmm0, [rbp - 24]
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.flt_pos:
    movsd   [rbp - 24], xmm0
    cvttsd2si rax, xmm0
    mov     [rbp - 32], rax
    mov     rcx, rax
    call    _pyfasm_print_int
    lea     rcx, [dot_str]
    call    _pyfasm_print_str

    movsd   xmm0, [rbp - 24]
    cvtsi2sd xmm1, qword [rbp - 32]
    subsd   xmm0, xmm1
    mulsd   xmm0, [flt_1m]
    mov     rax, 3FE0000000000000h
    movq    xmm1, rax
    addsd   xmm0, xmm1
    cvttsd2si rax, xmm0
    test    rax, rax
    jns     .frac_nonneg
    xor     eax, eax
.frac_nonneg:
    cmp     rax, 1000000
    jl      .frac_check_zero
    mov     rax, 999999
.frac_check_zero:
    test    rax, rax
    jnz     .frac_padded
    xor     ecx, ecx
    call    _pyfasm_print_int
    jmp     .flt_done
.frac_padded:
    lea     rdi, [rbp - 42]
    mov     byte [rdi], 0
    mov     rbx, 10
    mov     ecx, 6
.frac_digit_loop:
    xor     edx, edx
    div     rbx
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    dec     ecx
    jnz     .frac_digit_loop
    mov     rcx, rdi
    call    _pyfasm_print_str
.flt_done:
    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rbx
    pop     rbp
    ret

_pyfasm_float_to_str:
    ; RCX = IEEE-754 float64 bits -> RAX = heap-allocated string pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 96
    and     rsp, -16

    mov     [rbp - 40], rcx
    mov     ecx, 64
    call    _pyfasm_alloc
    mov     r12, rax
    mov     rdi, rax

    movq    xmm0, qword [rbp - 40]
    ucomisd xmm0, [flt_zero]
    jae     .fts_pos
    mov     byte [rdi], '-'
    inc     rdi
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.fts_pos:
    movsd   [rbp - 48], xmm0
    cvttsd2si rax, xmm0
    mov     [rbp - 56], rax

    lea     rsi, [rbp - 64]
    mov     byte [rsi], 0
    mov     rbx, 10
    test    rax, rax
    jnz     .fts_int_loop
    mov     byte [rdi], '0'
    inc     rdi
    jmp     .fts_dot
.fts_int_loop:
    test    rax, rax
    jz      .fts_int_copy
    xor     edx, edx
    div     rbx
    add     dl, '0'
    dec     rsi
    mov     [rsi], dl
    jmp     .fts_int_loop
.fts_int_copy:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .fts_dot
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .fts_int_copy

.fts_dot:
    mov     byte [rdi], '.'
    inc     rdi

    movsd   xmm0, [rbp - 48]
    cvtsi2sd xmm1, qword [rbp - 56]
    subsd   xmm0, xmm1
    mulsd   xmm0, [flt_1m]
    mov     rax, 3FE0000000000000h
    movq    xmm1, rax
    addsd   xmm0, xmm1
    cvttsd2si rax, xmm0
    test    rax, rax
    jns     .fts_frac_nonneg
    xor     eax, eax
.fts_frac_nonneg:
    cmp     rax, 1000000
    jl      .fts_frac_check_zero
    mov     rax, 999999
.fts_frac_check_zero:
    test    rax, rax
    jnz     .fts_frac_digits
    mov     byte [rdi], '0'
    inc     rdi
    jmp     .fts_done

.fts_frac_digits:
    mov     rbx, 10
    mov     ecx, 6
    lea     rsi, [rdi + 5]
.fts_frac_loop:
    xor     edx, edx
    div     rbx
    add     dl, '0'
    mov     [rsi], dl
    dec     rsi
    dec     ecx
    jnz     .fts_frac_loop
    add     rdi, 6

.fts_done:
    mov     byte [rdi], 0
    mov     rax, r12
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret


_pyfasm_file_open:
    ; RCX = filename string, RDX = mode string (e.g. "w", "r", "a", or 0)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx
    mov     rdi, rdx

    mov     ebx, 'r'
    test    rdi, rdi
    jz      .fo_mode_ready
    movzx   ebx, byte [rdi]
.fo_mode_ready:

    cmp     ebx, 'w'
    je      .fo_mode_write
    cmp     ebx, 'a'
    je      .fo_mode_append

    ; Mode 'r'
    mov     rcx, rsi
    mov     edx, 80000000h          ; GENERIC_READ
    mov     r8d, 1                  ; FILE_SHARE_READ
    xor     r9d, r9d
    mov     qword [rsp + 32], 3      ; OPEN_EXISTING
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    jmp     .fo_open_done

.fo_mode_write:
    mov     rcx, rsi
    mov     edx, 40000000h          ; GENERIC_WRITE
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 2      ; CREATE_ALWAYS
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    jmp     .fo_open_done

.fo_mode_append:
    mov     rcx, rsi
    mov     edx, 40000000h          ; GENERIC_WRITE
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 4      ; OPEN_ALWAYS
    mov     qword [rsp + 40], 80h    ; FILE_ATTRIBUTE_NORMAL
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    cmp     rax, -1
    je      .fo_open_done
    mov     rbx, rax
    mov     rcx, rax
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, 2                  ; FILE_END
    call    [SetFilePointer]
    mov     rax, rbx

.fo_open_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_file_write_data:
    ; RCX = file handle, RDX = content string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 64
    and     rsp, -16

    test    rcx, rcx
    jz      .err_f_write
    cmp     rcx, -1
    je      .err_f_write

    mov     rbx, rcx
    mov     rsi, rdx

    mov     rcx, rsi
    test    rcx, rcx
    jz      .zero_len_write
    call    _pyfasm_str_len
    mov     r8, rax
    jmp     .do_f_write
.zero_len_write:
    xor     r8d, r8d
.do_f_write:
    mov     rcx, rbx
    mov     rdx, rsi
    lea     r9, [rsp + 40]
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    jmp     .f_write_done

.err_f_write:
    xor     eax, eax
.f_write_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_file_read_all:
    ; RCX = file handle
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16

    test    rcx, rcx
    jz      .empty_f_read
    cmp     rcx, -1
    je      .empty_f_read

    mov     rbx, rcx

    mov     rcx, rbx
    xor     edx, edx
    call    [GetFileSize]
    cmp     eax, -1
    je      .empty_f_read
    test    eax, eax
    jz      .empty_f_read

    mov     esi, eax

    lea     ecx, [rsi + 1]
    call    _pyfasm_alloc
    test    rax, rax
    jz      .empty_f_read
    mov     rdi, rax

    mov     rcx, rbx
    mov     rdx, rdi
    mov     r8d, esi
    lea     r9, [rsp + 40]
    mov     qword [rsp + 32], 0
    call    [ReadFile]

    mov     eax, [rsp + 40]
    mov     byte [rdi + rax], 0
    mov     rax, rdi
    jmp     .f_read_done

.empty_f_read:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.f_read_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_file_close:
    ; RCX = file handle
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jz      .fc_close_done
    cmp     rcx, -1
    je      .fc_close_done

    call    [CloseHandle]
.fc_close_done:
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

_pyfasm_str_concat:
    ; RCX = str1, RDX = str2
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     rbx, rdx

    ; Calculate len(str1)
    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     [rsp + 32], rax                ; len1

    ; Calculate len(str2)
    mov     rcx, rbx
    call    _pyfasm_str_len
    mov     r8, rax                        ; len2

    ; Allocate len1 + len2 + 1 bytes
    mov     rax, [rsp + 32]
    add     rax, r8
    inc     rax                            ; +1 for null terminator
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax                       ; rdi = new buffer
    mov     [rsp + 40], rax                ; save return pointer

    test    rsi, rsi
    jz      .copy_s2_init
.copy_s1:
    mov     al, [rsi]
    test    al, al
    jz      .copy_s2_init
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .copy_s1

.copy_s2_init:
    test    rbx, rbx
    jz      .concat_null_term
.copy_s2:
    mov     al, [rbx]
    mov     [rdi], al
    test    al, al
    jz      .concat_done
    inc     rbx
    inc     rdi
    jmp     .copy_s2

.concat_null_term:
    mov     byte [rdi], 0
.concat_done:
    mov     rax, [rsp + 40]
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_join:
    ; RCX = sep_str, RDX = seq_ptr
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
    mov     rsi, rcx
    mov     rbx, rdx
    test    rbx, rbx
    jz      .join_empty
    mov     r12, [rbx]
    test    r12, r12
    jle     .join_empty

    mov     rcx, [rbx + 8]
    call    _pyfasm_auto_to_str
    mov     r15, rax
    mov     r13, 1
.join_loop:
    cmp     r13, r12
    jge     .join_done
    mov     rcx, r15
    mov     rdx, rsi
    call    _pyfasm_str_concat
    mov     r15, rax
    mov     rcx, [rbx + r13 * 8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .join_loop

.join_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    mov     r15, rax
.join_done:
    mov     rax, r15
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

_pyfasm_str_removeprefix:
    ; RCX = str, RDX = prefix
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    call    _pyfasm_str_startswith
    test    eax, eax
    jz      .rmp_ret_orig
    mov     rcx, rsi
    call    _pyfasm_str_len
    add     rbx, rax
.rmp_ret_orig:
    mov     rax, rbx
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_removesuffix:
    ; RCX = str, RDX = suffix
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    call    _pyfasm_str_endswith
    test    eax, eax
    jz      .rms_ret_orig
    mov     rcx, rbx
    call    _pyfasm_str_len
    mov     rdi, rax
    mov     rcx, rsi
    call    _pyfasm_str_len
    sub     rdi, rax
    lea     rcx, [rdi + 1]
    call    _pyfasm_alloc
    mov     rsi, rax
    mov     rcx, rdi
    mov     rdx, rbx
.rms_copy:
    test    rcx, rcx
    jz      .rms_done
    mov     al, [rdx]
    mov     [rsi], al
    inc     rdx
    inc     rsi
    dec     rcx
    jmp     .rms_copy
.rms_done:
    mov     byte [rsi], 0
    sub     rsi, rdi
    mov     rax, rsi
    jmp     .rms_ret
.rms_ret_orig:
    mov     rax, rbx
.rms_ret:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_replace:
    ; RCX = target, RDX = old_str, R8 = new_str
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
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
    test    rbx, rbx
    jz      .srep_ret_empty
    test    rsi, rsi
    jz      .srep_ret_orig

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     r12, rax
    test    r12, r12
    jz      .srep_ret_orig

    mov     rcx, rdi
    call    _pyfasm_str_len
    mov     r13, rax

    mov     ecx, 65536
    call    _pyfasm_alloc
    mov     r14, rax
    mov     r15, rax

.srep_loop:
    mov     al, [rbx]
    test    al, al
    jz      .srep_finish

    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_str_startswith
    test    eax, eax
    jz      .srep_copy_char

    mov     rcx, r13
    mov     rdx, rdi
.srep_copy_new:
    test    rcx, rcx
    jz      .srep_adv_old
    mov     al, [rdx]
    mov     [r15], al
    inc     rdx
    inc     r15
    dec     rcx
    jmp     .srep_copy_new
.srep_adv_old:
    add     rbx, r12
    jmp     .srep_loop

.srep_copy_char:
    mov     al, [rbx]
    mov     [r15], al
    inc     rbx
    inc     r15
    jmp     .srep_loop

.srep_finish:
    mov     byte [r15], 0
    mov     rax, r14
    jmp     .srep_ret
.srep_ret_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    jmp     .srep_ret
.srep_ret_orig:
    mov     rax, rbx
.srep_ret:
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

_pyfasm_str_cmp:
    ; RCX = key1, RDX = key2
    ; Returns RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .cmp_eq
    test    rcx, rcx
    jz      .cmp_ne
    js      .cmp_ne
    test    rdx, rdx
    jz      .cmp_ne
    js      .cmp_ne
    cmp     rcx, 65536
    jb      .cmp_ne
    cmp     rdx, 65536
    jb      .cmp_ne
.cmp_loop:
    mov     al, [rcx]
    mov     ah, [rdx]
    cmp     al, ah
    jne     .cmp_ne
    test    al, al
    jz      .cmp_eq
    inc     rcx
    inc     rdx
    jmp     .cmp_loop
.cmp_ne:
    xor     eax, eax
    ret
.cmp_eq:
    mov     eax, 1
    ret

_pyfasm_str_contains:
    ; RCX = haystack, RDX = needle
    ; Returns 1 if needle in haystack, 0 otherwise
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx

    mov     rsi, rcx
    mov     rbx, rdx
    test    rbx, rbx
    jz      .sc_found
    cmp     byte [rbx], 0
    jz      .sc_found
    test    rsi, rsi
    jz      .sc_not_found

.sc_outer:
    mov     al, [rsi]
    test    al, al
    jz      .sc_not_found

    mov     rdi, rsi
    mov     rdx, rbx
.sc_inner:
    mov     cl, [rdx]
    test    cl, cl
    jz      .sc_found
    cmp     cl, [rdi]
    jne     .sc_advance
    inc     rdi
    inc     rdx
    jmp     .sc_inner

.sc_advance:
    inc     rsi
    jmp     .sc_outer

.sc_found:
    mov     rax, 1
    jmp     .sc_ret

.sc_not_found:
    xor     rax, rax

.sc_ret:
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_lower:
    ; RCX = string
    ; Returns RAX = new lowercase string in heap
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .lower_empty

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax
    inc     rax
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax

.lower_loop:
    mov     al, [rsi]
    test    al, al
    jz      .lower_done
    cmp     al, 'A'
    jb      .lower_chk_utf8
    cmp     al, 'Z'
    ja      .lower_chk_utf8
    add     al, 32
    jmp     .lower_store
.lower_chk_utf8:
    cmp     al, 0D0h
    jne     .lower_store
    mov     dl, [rsi + 1]
    test    dl, dl
    jz      .lower_store
    cmp     dl, 81h
    jne     .lower_ru_ap
    ; Yo (D0 81) -> yo (D1 91)
    mov     byte [rdi], 0D1h
    mov     byte [rdi + 1], 91h
    add     rsi, 2
    add     rdi, 2
    jmp     .lower_loop
.lower_ru_ap:
    cmp     dl, 90h
    jb      .lower_store
    cmp     dl, 9Fh
    ja      .lower_ru_rya
    ; A..P (D0 90..9F) -> a..p (D0 B0..BF)
    add     dl, 20h
    mov     byte [rdi], 0D0h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .lower_loop
.lower_ru_rya:
    cmp     dl, 0A0h
    jb      .lower_store
    cmp     dl, 0AFh
    ja      .lower_store
    ; R..Ya (D0 A0..AF) -> r..ya (D1 80..8F)
    sub     dl, 20h
    mov     byte [rdi], 0D1h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .lower_loop
.lower_store:
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .lower_loop

.lower_done:
    mov     byte [rdi], 0
    pop     rax
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.lower_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_upper:
    ; RCX = string
    ; Returns RAX = new uppercase string in heap
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .upper_empty

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax
    inc     rax
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax

.upper_loop:
    mov     al, [rsi]
    test    al, al
    jz      .upper_done
    cmp     al, 'a'
    jb      .upper_chk_utf8
    cmp     al, 'z'
    ja      .upper_chk_utf8
    sub     al, 32
    jmp     .upper_store
.upper_chk_utf8:
    cmp     al, 0D0h
    je      .upper_d0
    cmp     al, 0D1h
    je      .upper_d1
    jmp     .upper_store
.upper_d0:
    mov     dl, [rsi + 1]
    test    dl, dl
    jz      .upper_store
    cmp     dl, 0B0h
    jb      .upper_store
    cmp     dl, 0BFh
    ja      .upper_store
    ; a..p (D0 B0..BF) -> A..P (D0 90..9F)
    sub     dl, 20h
    mov     byte [rdi], 0D0h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .upper_loop
.upper_d1:
    mov     dl, [rsi + 1]
    test    dl, dl
    jz      .upper_store
    cmp     dl, 91h
    jne     .upper_d1_rya
    ; yo (D1 91) -> Yo (D0 81)
    mov     byte [rdi], 0D0h
    mov     byte [rdi + 1], 81h
    add     rsi, 2
    add     rdi, 2
    jmp     .upper_loop
.upper_d1_rya:
    cmp     dl, 80h
    jb      .upper_store
    cmp     dl, 8Fh
    ja      .upper_store
    ; r..ya (D1 80..8F) -> R..Ya (D0 A0..AF)
    add     dl, 20h
    mov     byte [rdi], 0D0h
    mov     [rdi + 1], dl
    add     rsi, 2
    add     rdi, 2
    jmp     .upper_loop
.upper_store:
    mov     [rdi], al
    inc     rsi
    inc     rdi
    jmp     .upper_loop

.upper_done:
    mov     byte [rdi], 0
    pop     rax
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.upper_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_startswith:
    ; RCX = str, RDX = prefix
    ; Returns RAX = 1 if starts with prefix, 0 otherwise
    test    rdx, rdx
    jz      .sw_true
    cmp     byte [rdx], 0
    jz      .sw_true
    test    rcx, rcx
    jz      .sw_false
.sw_loop:
    mov     al, [rdx]
    test    al, al
    jz      .sw_true
    cmp     al, [rcx]
    jne     .sw_false
    inc     rcx
    inc     rdx
    jmp     .sw_loop
.sw_true:
    mov     eax, 1
    ret
.sw_false:
    xor     eax, eax
    ret

_pyfasm_str_endswith:
    ; RCX = str, RDX = suffix
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    mov     rdi, rdx
    test    rdi, rdi
    jz      .ew_true
    cmp     byte [rdi], 0
    jz      .ew_true
    test    rsi, rsi
    jz      .ew_false

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     rbx, rax

    mov     rcx, rdi
    call    _pyfasm_str_len

    cmp     rbx, rax
    jl      .ew_false

    sub     rbx, rax
    add     rsi, rbx

    mov     rcx, rsi
    mov     rdx, rdi
    call    _pyfasm_str_cmp
    jmp     .ew_ret

.ew_true:
    mov     eax, 1
    jmp     .ew_ret

.ew_false:
    xor     eax, eax

.ew_ret:
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_strip:
    ; RCX = string
    ; Returns RAX = trimmed string in heap
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .strip_empty

.strip_leading:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .strip_empty
    cmp     al, 32
    ja      .strip_leading_done
    inc     rsi
    jmp     .strip_leading
.strip_leading_done:

    mov     rdi, rsi
.strip_find_end:
    cmp     byte [rdi], 0
    jz      .strip_found_end
    inc     rdi
    jmp     .strip_find_end
.strip_found_end:
    dec     rdi

.strip_trailing:
    cmp     rdi, rsi
    jb      .strip_empty
    movzx   eax, byte [rdi]
    cmp     al, 32
    ja      .strip_trailing_done
    dec     rdi
    jmp     .strip_trailing
.strip_trailing_done:

    mov     rbx, rdi
    sub     rbx, rsi
    inc     rbx

    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    mov     rdi, rax
    push    rax

    mov     rcx, rbx
    rep     movsb
    mov     byte [rdi], 0

    pop     rax
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.strip_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    lea     rsp, [rbp - 24]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_dict_create:
    ; RCX = initial capacity (0 = default 256; rounded up to power of 2, min 256)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rax, 256
    test    rcx, rcx
    jle     .cap_ok
    cmp     rcx, rax
    jbe     .cap_ok
.cap_pow2_loop:
    cmp     rax, 1048576
    jae     .cap_ok
    shl     rax, 1
    cmp     rax, rcx
    jb      .cap_pow2_loop
.cap_ok:
    mov     rbx, rax
    lea     rax, [rbx + rbx * 2]
    shl     rax, 3
    add     rax, 16
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], rbx
    mov     qword [rax + 8], 0
    lea     rdi, [rax + 16]
    lea     rcx, [rbx + rbx * 2]
    mov     rdx, rax
    xor     eax, eax
    rep     stosq
    mov     rax, rdx
    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_hash:
    ; RCX = null-terminated string or 64-bit integer
    ; Returns RAX = 64-bit FNV-1a hash (never 0 or -1)
    test    rcx, rcx
    jz      .hash_zero
    js      .hash_int
    cmp     rcx, 65536
    jb      .hash_int
    mov     rax, 0CBF29CE484222325h
    mov     rdx, 100000001B3h
.hash_loop:
    movzx   r8d, byte [rcx]
    test    r8b, r8b
    jz      .hash_done
    xor     rax, r8
    imul    rax, rdx
    inc     rcx
    jmp     .hash_loop
.hash_zero:
    mov     rax, 0CBF29CE484222325h
    ret
.hash_int:
    mov     rax, rcx
    mov     rdx, 100000001B3h
    imul    rax, rdx
    test    rax, rax
    jz      .hash_one
    cmp     rax, -1
    je      .hash_one
    ret
.hash_done:
    test    rax, rax
    jz      .hash_one
    cmp     rax, -1
    je      .hash_one
    ret
.hash_one:
    mov     rax, 1
    ret

_pyfasm_dict_set:
    ; RCX = dict_ptr, RDX = key_str, R8 = val
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dict_set_done
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    test    r14, r14
    jz      .dict_set_done
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
    mov     qword [rsp + 40], 0
.dict_probe:
    cmp     r11, [rbx]
    jge     .dict_use_tombstone_or_done

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dict_slot_empty

    cmp     rax, -1
    je      .dict_slot_tombstone

    cmp     rax, r13
    jne     .dict_next_slot

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dict_update_val

.dict_next_slot:
    inc     rdi
    and     rdi, r14
    inc     r11
    jmp     .dict_probe

.dict_slot_tombstone:
    cmp     qword [rsp + 40], 0
    jne     .dict_next_slot
    mov     [rsp + 40], rcx
    jmp     .dict_next_slot

.dict_use_tombstone_or_done:
    mov     rcx, [rsp + 40]
    test    rcx, rcx
    jz      .dict_set_done
    jmp     .dict_insert_at_rcx

.dict_slot_empty:
    mov     rax, [rsp + 40]
    test    rax, rax
    jz      .dict_insert_at_rcx
    mov     rcx, rax

.dict_insert_at_rcx:
    mov     [rcx], r13
    mov     [rcx + 8], rsi
    mov     [rcx + 16], r12
    inc     qword [rbx + 8]
    jmp     .dict_set_done

.dict_update_val:
    mov     [rcx + 16], r12

.dict_set_done:
    mov     rax, rbx
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

_pyfasm_dict_get:
    ; RCX = dict_ptr, RDX = key_str, R8 = default_val
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
    test    rcx, rcx
    jz      .dict_get_default
    mov     rbx, rcx
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    test    r14, r14
    jz      .dict_get_default
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
.dict_get_probe:
    cmp     r11, [rbx]
    jge     .dict_get_default

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dict_get_default

    cmp     rax, r13
    jne     .dict_get_next

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dict_get_found

.dict_get_next:
    inc     rdi
    and     rdi, r14
    inc     r11
    jmp     .dict_get_probe

.dict_get_found:
    mov     rax, [rcx + 16]
    jmp     .dict_get_ret

.dict_get_default:
    mov     rax, r12

.dict_get_ret:
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

; ============================================================
; Dictionary Tuple Key Support (FNV-1a tuple hashing & comparison)
; ============================================================
_pyfasm_tuple_hash:
    ; RCX = pointer to tuple [num_elts, elt0, elt1, ...]
    ; Returns RAX = 64-bit FNV-1a hash
    push    rbx
    push    rsi
    test    rcx, rcx
    jz      .th_zero
    mov     rsi, rcx
    mov     rbx, [rsi]             ; num_elts
    test    rbx, rbx
    jz      .th_zero
    mov     rax, 0CBF29CE484222325h
    mov     r10, 100000001B3h
.th_loop:
    add     rsi, 8
    mov     r8, [rsi]              ; current element
    xor     rax, r8
    imul    rax, r10
    dec     rbx
    jnz     .th_loop
    test    rax, rax
    jz      .th_one
    cmp     rax, -1
    jne     .th_ret
.th_one:
    mov     rax, 1
.th_ret:
    pop     rsi
    pop     rbx
    ret
.th_zero:
    mov     rax, 0CBF29CE484222325h
    pop     rsi
    pop     rbx
    ret

_pyfasm_tuple_cmp:
    ; RCX = tuple1, RDX = tuple2
    ; Returns RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .tc_eq
    test    rcx, rcx
    jz      .tc_ne
    test    rdx, rdx
    jz      .tc_ne
    mov     r8, [rcx]              ; len1
    cmp     r8, [rdx]              ; len2
    jne     .tc_ne
    test    r8, r8
    jz      .tc_eq
.tc_loop:
    add     rcx, 8
    add     rdx, 8
    mov     rax, [rcx]
    cmp     rax, [rdx]
    jne     .tc_ne
    dec     r8
    jnz     .tc_loop
.tc_eq:
    mov     eax, 1
    ret
.tc_ne:
    xor     eax, eax
    ret

_pyfasm_dict_set_tuple:
    ; RCX = dict_ptr, RDX = tuple_key_ptr, R8 = val
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dst_done
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_tuple_hash
    mov     r13, rax

    mov     r14, [rbx]             ; capacity
    test    r14, r14
    jz      .dst_done
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
    mov     qword [rsp + 40], 0
.dst_probe:
    cmp     r11, [rbx]
    jge     .dst_use_tombstone_or_done

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]             ; slot hash
    test    rax, rax
    jz      .dst_slot_empty

    cmp     rax, -1
    je      .dst_slot_tombstone

    cmp     rax, r13
    jne     .dst_next_slot

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]         ; existing tuple in slot
    mov     rdx, rsi               ; target tuple
    call    _pyfasm_tuple_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dst_update_val

.dst_next_slot:
    inc     rdi
    and     rdi, r14
    inc     r11
    jmp     .dst_probe

.dst_slot_tombstone:
    cmp     qword [rsp + 40], 0
    jne     .dst_next_slot
    mov     [rsp + 40], rcx
    jmp     .dst_next_slot

.dst_use_tombstone_or_done:
    mov     rcx, [rsp + 40]
    test    rcx, rcx
    jz      .dst_done
    jmp     .dst_insert_at_rcx

.dst_slot_empty:
    mov     rax, [rsp + 40]
    test    rax, rax
    jz      .dst_insert_at_rcx
    mov     rcx, rax

.dst_insert_at_rcx:
    mov     [rcx], r13
    mov     [rcx + 8], rsi
    mov     [rcx + 16], r12
    inc     qword [rbx + 8]
    jmp     .dst_done

.dst_update_val:
    mov     [rcx + 16], r12

.dst_done:
    mov     rax, rbx
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

_pyfasm_dict_get_tuple:
    ; RCX = dict_ptr, RDX = tuple_key_ptr, R8 = default_val
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
    test    rcx, rcx
    jz      .dgt_default
    mov     rbx, rcx
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_tuple_hash
    mov     r13, rax

    mov     r14, [rbx]             ; capacity
    test    r14, r14
    jz      .dgt_default
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11               ; probe counter
.dgt_probe:
    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dgt_default

    cmp     rax, r13
    jne     .dgt_next_slot

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_tuple_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jnz     .dgt_found

.dgt_next_slot:
    inc     r11
    cmp     r11, [rbx]
    jge     .dgt_default
    inc     rdi
    and     rdi, r14
    jmp     .dgt_probe

.dgt_found:
    mov     rax, [rcx + 16]
    jmp     .dgt_ret

.dgt_default:
    mov     rax, r12

.dgt_ret:
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

_pyfasm_dict_contains:
    ; RCX = dict_ptr, RDX = key_str
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     r8, -999999999
    call    _pyfasm_dict_get
    cmp     rax, -999999999
    setne   al
    movzx   rax, al
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_dict_len:
    test    rcx, rcx
    jz      .dict_len_zero
    mov     rax, [rcx + 8]
    ret
.dict_len_zero:
    xor     eax, eax
    ret

_pyfasm_dict_remove:
    ; RCX = dict_ptr, RDX = key
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
    test    rcx, rcx
    jz      .rem_done
    mov     rbx, rcx
    mov     rsi, rdx

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    dec     r14
    and     rax, r14
    mov     rdi, rax

    xor     r11, r11
.rem_probe:
    cmp     r11, [rbx]
    jge     .rem_done

    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .rem_done

    cmp     rax, r13
    jne     .rem_next

    push    rcx
    push    r11
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     r11
    pop     rcx
    test    eax, eax
    jz      .rem_next

    ; Found: mark as tombstone (-1)
    mov     qword [rcx], -1
    mov     qword [rcx + 8], 0
    mov     qword [rcx + 16], 0
    dec     qword [rbx + 8]
    mov     eax, 1
    jmp     .rem_ret

.rem_next:
    inc     r11
    inc     rdi
    and     rdi, r14
    jmp     .rem_probe

.rem_done:
    xor     eax, eax
.rem_ret:
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

_pyfasm_dict_values:
    ; RCX = dict_ptr -> returns RAX = list of values
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dval_empty
    mov     rcx, [rbx + 8]
    call    _pyfasm_list_create
    mov     r12, rax
    mov     r13, [rbx]
    xor     r14, r14
.dval_loop:
    cmp     r14, r13
    jge     .dval_done
    lea     rax, [r14 + r14 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .dval_next
    cmp     rax, -1
    je      .dval_next
    mov     rcx, r12
    mov     rdx, [rsi + 16]
    call    _pyfasm_list_append
.dval_next:
    inc     r14
    jmp     .dval_loop
.dval_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     r12, rax
.dval_done:
    mov     rax, r12
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

_pyfasm_dict_keys:
    ; RCX = dict_ptr -> returns RAX = list of keys
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .dkey_empty
    mov     rcx, [rbx + 8]
    call    _pyfasm_list_create
    mov     r12, rax
    mov     r13, [rbx]
    xor     r14, r14
.dkey_loop:
    cmp     r14, r13
    jge     .dkey_done
    lea     rax, [r14 + r14 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .dkey_next
    cmp     rax, -1
    je      .dkey_next
    mov     rcx, r12
    mov     rdx, [rsi + 8]
    call    _pyfasm_list_append
.dkey_next:
    inc     r14
    jmp     .dkey_loop
.dkey_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     r12, rax
.dkey_done:
    mov     rax, r12
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

_pyfasm_dict_items:
    ; RCX = dict_ptr -> returns RAX = list of (key, val) pairs
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
    mov     rbx, rcx
    test    rbx, rbx
    jz      .ditem_empty
    mov     rcx, [rbx + 8]
    call    _pyfasm_list_create
    mov     r12, rax
    mov     r13, [rbx]
    xor     r14, r14
.ditem_loop:
    cmp     r14, r13
    jge     .ditem_done
    lea     rax, [r14 + r14 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .ditem_next
    cmp     rax, -1
    je      .ditem_next
    mov     ecx, 2
    call    _pyfasm_list_create
    mov     rdi, rax
    mov     rcx, rdi
    mov     rdx, [rsi + 8]
    call    _pyfasm_list_append
    mov     rcx, rdi
    mov     rdx, [rsi + 16]
    call    _pyfasm_list_append
    mov     rcx, r12
    mov     rdx, rdi
    call    _pyfasm_list_append
.ditem_next:
    inc     r14
    jmp     .ditem_loop
.ditem_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     r12, rax
.ditem_done:
    mov     rax, r12
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

_pyfasm_set_create:
    jmp     _pyfasm_dict_create

_pyfasm_set_add:
    mov     r8, 1
    jmp     _pyfasm_dict_set

_pyfasm_set_contains:
    jmp     _pyfasm_dict_contains

_pyfasm_set_remove:
    jmp     _pyfasm_dict_remove

_pyfasm_set_len:
    jmp     _pyfasm_dict_len

_pyfasm_str_count:
    ; RCX = str (haystack), RDX = sub (needle, can be string pointer or single char)
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
    xor     r14, r14            ; count = 0
    test    rcx, rcx
    jz      .sc_done
    test    rdx, rdx
    jz      .sc_done
    mov     rsi, rcx            ; rsi = haystack
    mov     rdi, rdx            ; rdi = needle

    ; Check if needle is a pointer (>= 65536) or single char (< 65536)
    cmp     rdi, 65536
    jae     .sc_needle_is_str

    ; Needle is single char byte
    movzx   ebx, dil
    test    bl, bl
    jz      .sc_done
.sc_char_loop:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .sc_done
    cmp     al, bl
    jne     .sc_char_next
    inc     r14
.sc_char_next:
    inc     rsi
    jmp     .sc_char_loop

.sc_needle_is_str:
    ; Needle is a string pointer
    mov     rcx, rdi
    sub     rsp, 32
    call    _pyfasm_str_len
    add     rsp, 32
    mov     r12, rax            ; r12 = needle len
    test    r12, r12
    jz      .sc_done

    ; If needle len is 1, optimize to char loop
    cmp     r12, 1
    jne     .sc_str_loop
    movzx   ebx, byte [rdi]
    jmp     .sc_char_loop

.sc_str_loop:
    ; Needle len >= 2
    movzx   eax, byte [rsi]
    test    al, al
    jz      .sc_done
    ; Check if haystack[0..r12-1] matches needle[0..r12-1]
    xor     rcx, rcx
.sc_match_loop:
    cmp     rcx, r12
    jge     .sc_matched
    mov     al, [rsi + rcx]
    test    al, al
    jz      .sc_done            ; reached end of haystack
    cmp     al, [rdi + rcx]
    jne     .sc_no_match
    inc     rcx
    jmp     .sc_match_loop

.sc_matched:
    inc     r14
    add     rsi, r12            ; advance past non-overlapping match
    jmp     .sc_str_loop

.sc_no_match:
    inc     rsi
    jmp     .sc_str_loop

.sc_done:
    mov     rax, r14
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

_pyfasm_list_count:
    ; RCX = list_ptr, RDX = item
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16
    xor     r13, r13            ; count = 0
    test    rcx, rcx
    jz      .lc_done
    mov     rbx, rcx            ; list
    mov     rsi, rdx            ; item
    mov     rdi, [rbx]          ; length
    xor     r12, r12            ; index = 0
.lc_loop:
    cmp     r12, rdi
    jge     .lc_done
    mov     rax, [rbx + r12 * 8 + 8]
    cmp     rax, rsi
    je      .lc_inc
    ; If both are >= 65536, try str_cmp
    cmp     rsi, 65536
    jb      .lc_next
    cmp     rax, 65536
    jb      .lc_next
    mov     rcx, rax
    mov     rdx, rsi
    sub     rsp, 32
    call    _pyfasm_str_cmp
    add     rsp, 32
    test    eax, eax
    jz      .lc_next
.lc_inc:
    inc     r13
.lc_next:
    inc     r12
    jmp     .lc_loop
.lc_done:
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

_pyfasm_set_from_str:
    ; RCX = null-terminated string
    ; Returns RAX = list_ptr of unique 1-character strings
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 320            ; 256 bytes for visited table + 32 shadow space + alignment
    and     rsp, -16

    test    rcx, rcx
    jz      .sfs_empty

    mov     rsi, rcx            ; rsi = string ptr

    ; Zero-out 256-byte visited array on stack
    lea     rdi, [rsp + 32]
    mov     ecx, 32             ; 32 * 8 = 256 bytes
    xor     eax, eax
    rep stosq

    ; Allocate list for up to 256 elements: 256 * 8 + 16 = 2064 bytes
    mov     ecx, 2064
    sub     rsp, 32
    call    _pyfasm_alloc
    add     rsp, 32
    mov     rbx, rax            ; rbx = list_ptr
    mov     qword [rbx], 0      ; length = 0

.sfs_loop:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .sfs_done

    lea     rdi, [rsp + 32]
    cmp     byte [rdi + rax], 0
    jne     .sfs_next

    ; Mark as visited
    mov     byte [rdi + rax], 1

    ; Allocate 16-byte memory for 1-character string: [char, 0]
    mov     r14, rax
    mov     ecx, 16
    sub     rsp, 32
    call    _pyfasm_alloc
    add     rsp, 32
    mov     byte [rax], r14b
    mov     byte [rax + 1], 0

    ; Append to list
    mov     rcx, rbx            ; list
    mov     rdx, rax            ; item (1-char string)
    sub     rsp, 32
    call    _pyfasm_list_append
    add     rsp, 32

.sfs_next:
    inc     rsi
    jmp     .sfs_loop

.sfs_done:
    mov     rax, rbx
    jmp     .sfs_ret

.sfs_empty:
    mov     ecx, 16
    sub     rsp, 32
    call    _pyfasm_list_create
    add     rsp, 32
.sfs_ret:
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

_pyfasm_set_from_list:
    ; RCX = list_ptr [len, elt0, elt1, ...]
    ; Returns RAX = new list_ptr with unique elements
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .sfl_empty

    mov     rbx, rcx            ; rbx = source list
    mov     r12, [rbx]          ; length
    test    r12, r12
    jz      .sfl_empty

    ; Allocate new list
    lea     rcx, [r12 * 8 + 16]
    sub     rsp, 32
    call    _pyfasm_alloc
    add     rsp, 32
    mov     rdi, rax            ; rdi = new unique list
    mov     qword [rdi], 0      ; length = 0

    xor     r13, r13            ; src idx = 0
.sfl_loop:
    cmp     r13, r12
    jge     .sfl_done
    mov     rdx, [rbx + r13 * 8 + 8] ; candidate item
    mov     rcx, rdi            ; new list
    sub     rsp, 32
    call    _pyfasm_list_contains
    add     rsp, 32
    test    eax, eax
    jnz     .sfl_next           ; already in unique list

    ; Append to new list
    mov     rcx, rdi
    mov     rdx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    _pyfasm_list_append
    add     rsp, 32
.sfl_next:
    inc     r13
    jmp     .sfl_loop

.sfl_done:
    mov     rax, rdi
    jmp     .sfl_ret

.sfl_empty:
    mov     ecx, 16
    sub     rsp, 32
    call    _pyfasm_list_create
    add     rsp, 32
.sfl_ret:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_from_iterable:
    ; RCX = str or list
    test    rcx, rcx
    jz      .sfi_empty
    cmp     qword [rcx], 1000000
    ja      _pyfasm_set_from_str
    cmp     byte [rcx], 0
    je      .sfi_empty
    movzx   eax, byte [rcx]
    cmp     al, 32
    jb      _pyfasm_set_from_list
    cmp     al, 126
    ja      _pyfasm_set_from_list
    movzx   edx, byte [rcx + 1]
    test    dl, dl
    jz      _pyfasm_set_from_str
    cmp     dl, 32
    jb      _pyfasm_set_from_list
    cmp     dl, 126
    ja      _pyfasm_set_from_list
    jmp     _pyfasm_set_from_str

.sfi_empty:
    mov     ecx, 16
    jmp     _pyfasm_list_create

_pyfasm_list_contains:
    ; RCX = list_ptr, RDX = item
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .plc_not_found
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, [rbx]
    test    rdi, rdi
    jz      .plc_not_found
    xor     r12, r12
.plc_loop:
    cmp     r12, rdi
    jge     .plc_not_found
    mov     rax, [rbx + r12 * 8 + 8]
    cmp     rax, rsi
    je      .plc_found
    cmp     rsi, 65536
    jb      .plc_next
    cmp     rax, 65536
    jb      .plc_next
    mov     rcx, rax
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    test    eax, eax
    jnz     .plc_found
.plc_next:
    inc     r12
    jmp     .plc_loop
.plc_found:
    mov     eax, 1
    jmp     .plc_ret
.plc_not_found:
    xor     eax, eax
.plc_ret:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret


_pyfasm_random_choice:
    ; RCX = list pointer
    push    rbp
    mov     rbp, rsp
    test    rcx, rcx
    jz      .rc_null
    mov     r8, [rcx]
    test    r8, r8
    jz      .rc_null
    push    rcx
    rdtsc
    pop     rcx
    xor     edx, edx
    div     r8d
    mov     rax, [rcx + rdx * 8 + 8]
    mov     rsp, rbp
    pop     rbp
    ret
.rc_null:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_pop:
    ; RCX = list_ptr
    test    rcx, rcx
    jz      .lp_empty
    mov     rdx, [rcx]
    test    rdx, rdx
    jz      .lp_empty
    mov     rax, [rcx + rdx * 8]
    dec     qword [rcx]
    ret
.lp_empty:
    xor     eax, eax
    ret

_pyfasm_map:
    ; RCX = seq_ptr, RDX = func_ptr
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
    test    rcx, rcx
    jz      .map_empty
    test    rdx, rdx
    jz      .map_empty
    mov     rbx, rcx     ; seq_ptr
    mov     rsi, rdx     ; func_ptr
    mov     r12, [rbx]   ; length
    lea     rcx, [r12 * 8 + 16]
    call    _pyfasm_alloc
    mov     rdi, rax     ; new list
    mov     [rdi], r12   ; new list length
    xor     r13, r13     ; idx = 0
.map_loop:
    cmp     r13, r12
    jge     .map_done
    mov     rax, 505946434C4F5355h
    cmp     qword [rsi], rax
    jne     .map_plain_call
    mov     rcx, rsi
    mov     rdx, [rbx + r13 * 8 + 8]
    mov     rax, [rsi + 8]
    sub     rsp, 32
    call    rax
    add     rsp, 32
    jmp     .map_store_elt
.map_plain_call:
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
.map_store_elt:
    mov     [rdi + r13 * 8 + 8], rax
    inc     r13
    jmp     .map_loop
.map_done:
    mov     rax, rdi
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
.map_empty:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
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

_pyfasm_filter:
    ; RCX = seq_ptr, RDX = func_ptr
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
    test    rcx, rcx
    jz      .filt_empty
    test    rdx, rdx
    jz      .filt_empty
    mov     rbx, rcx     ; seq_ptr
    mov     rsi, rdx     ; func_ptr
    mov     r12, [rbx]   ; length
    lea     rcx, [r12 * 8 + 16]
    call    _pyfasm_alloc
    mov     rdi, rax     ; new list
    xor     r13, r13     ; in_idx = 0
    xor     r14, r14     ; out_idx = 0
.filt_loop:
    cmp     r13, r12
    jge     .filt_done
    mov     rax, 505946434C4F5355h
    cmp     qword [rsi], rax
    jne     .filt_plain_call
    mov     rcx, rsi
    mov     rdx, [rbx + r13 * 8 + 8]
    mov     rax, [rsi + 8]
    sub     rsp, 32
    call    rax
    add     rsp, 32
    jmp     .filt_chk_res
.filt_plain_call:
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
.filt_chk_res:
    test    rax, rax
    jz      .filt_skip
    mov     rax, [rbx + r13 * 8 + 8]
    mov     [rdi + r14 * 8 + 8], rax
    inc     r14
.filt_skip:
    inc     r13
    jmp     .filt_loop
.filt_done:
    mov     [rdi], r14   ; stored filtered length
    mov     rax, rdi
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
.filt_empty:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
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

_pyfasm_gen_next:
    ; RCX = gen_ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    test    rcx, rcx
    jz      .gn_empty
    mov     rbx, rcx
    cmp     qword [rbx + 16], 1   ; done?
    je      .gn_empty
    mov     rax, [rbx + 8]        ; step function pointer
    mov     rcx, rbx
    call    rax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.gn_empty:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_create:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    test    ecx, ecx
    jnz     .plc_cap
    mov     ecx, 256
.plc_cap:
    shl     ecx, 3
    add     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_append:
    test    rcx, rcx
    jz      .la_ret
    mov     rax, [rcx]
    mov     [rcx + rax * 8 + 8], rdx
    inc     qword [rcx]
.la_ret:
    mov     rax, rcx
    ret

_pyfasm_list_extend:
    ; RCX = dest list pointer, RDX = src iterable/list pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    test    rcx, rcx
    jz      .le_ret
    test    rdx, rdx
    jz      .le_ret
    cmp     rdx, 65536
    jb      .le_ret
    mov     rsi, rcx
    mov     rdi, rdx
    mov     rbx, [rdi]              ; src len
    test    rbx, rbx
    jle     .le_ret
    xor     ecx, ecx                ; i = 0
.le_loop:
    cmp     rcx, rbx
    jge     .le_ret
    mov     rdx, [rdi + rcx * 8 + 8]
    mov     rax, [rsi]
    mov     [rsi + rax * 8 + 8], rdx
    inc     qword [rsi]
    inc     rcx
    jmp     .le_loop
.le_ret:
    mov     rax, rsi
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_insert:
    ; RCX = list pointer
    ; RDX = insertion index (signed 64-bit int)
    ; R8  = value to insert
    test    rcx, rcx
    jz      .pli_ret
    mov     rax, [rcx]              ; current length
    ; Clamp index: if rdx < 0: rdx = max(0, rdx + rax)
    test    rdx, rdx
    jge     .pli_check_high
    add     rdx, rax
    test    rdx, rdx
    jge     .pli_shift_prep
    xor     edx, edx
    jmp     .pli_shift_prep
.pli_check_high:
    cmp     rdx, rax
    jle     .pli_shift_prep
    mov     rdx, rax                ; clamp to current length
.pli_shift_prep:
    mov     r11, rax                ; r11 = current length
.pli_shift_loop:
    cmp     r11, rdx
    jle     .pli_do_insert
    mov     r10, [rcx + r11 * 8]    ; element at index r11 - 1
    mov     [rcx + (r11 + 1) * 8], r10 ; shift right by 1 slot
    dec     r11
    jmp     .pli_shift_loop
.pli_do_insert:
    mov     [rcx + (rdx + 1) * 8], r8
    inc     qword [rcx]             ; length++
.pli_ret:
    xor     eax, eax                ; list.insert returns None
    ret

bisect:
bisect_right:
_pyfasm_bisect:
_pyfasm_bisect_right:
    ; RCX = list pointer
    ; RDX = target value x
    test    rcx, rcx
    jnz     .bsr_start
    xor     eax, eax
    ret
.bsr_start:
    mov     r9, [rcx]               ; hi = len(arr)
.bsr_loop:
    cmp     r8, r9
    jge     .bsr_done
    mov     rax, r8
    add     rax, r9
    sar     rax, 1                  ; mid = (lo + hi) / 2
    mov     r10, [rcx + rax * 8 + 8] ; arr[mid]
    cmp     rdx, r10
    jl      .bsr_hi                 ; if x < arr[mid]: hi = mid
    lea     r8, [rax + 1]           ; else: lo = mid + 1
    jmp     .bsr_loop
.bsr_hi:
    mov     r9, rax
    jmp     .bsr_loop
.bsr_done:
    mov     rax, r8                 ; return lo
    ret

bisect_left:
_pyfasm_bisect_left:
    ; RCX = list pointer
    ; RDX = target value x
    test    rcx, rcx
    jnz     .bsl_start
    xor     eax, eax
    ret
.bsl_start:
    mov     r9, [rcx]               ; hi = len(arr)
.bsl_loop:
    cmp     r8, r9
    jge     .bsl_done
    mov     rax, r8
    add     rax, r9
    sar     rax, 1                  ; mid = (lo + hi) / 2
    mov     r10, [rcx + rax * 8 + 8] ; arr[mid]
    cmp     r10, rdx
    jl      .bsl_lo                 ; if arr[mid] < x: lo = mid + 1
    mov     r9, rax                 ; else: hi = mid
    jmp     .bsl_loop
.bsl_lo:
    lea     r8, [rax + 1]
    jmp     .bsl_loop
.bsl_done:
    mov     rax, r8                 ; return lo
    ret

_pyfasm_str_to_char_list:
    ; RCX = string pointer -> RAX = list of 1-character string pointers
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16
    mov     r12, rcx
    test    r12, r12
    jz      .s2l_empty
    mov     rcx, r12
    call    _pyfasm_str_len
    mov     r13, rax                ; r13 = length in bytes
    mov     rcx, r13
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = list pointer
    test    r13, r13
    jz      .s2l_done
    xor     r14, r14
.s2l_loop:
    cmp     r14, r13
    jge     .s2l_done
    movzx   eax, byte [r12 + r14]
    mov     r15d, 1                 ; default 1 byte
    cmp     al, 0C0h
    jb      .s2l_got_len
    cmp     al, 0E0h
    jb      .s2l_len2
    cmp     al, 0F0h
    jb      .s2l_len3
    mov     r15d, 4
    jmp     .s2l_got_len
.s2l_len2:
    mov     r15d, 2
    jmp     .s2l_got_len
.s2l_len3:
    mov     r15d, 3
.s2l_got_len:
    mov     ecx, 16
    call    _pyfasm_alloc
    lea     rsi, [r12 + r14]
    xor     ecx, ecx
.s2l_copy:
    cmp     ecx, r15d
    jge     .s2l_copied
    mov     r8b, byte [rsi + rcx]
    mov     byte [rax + rcx], r8b
    inc     ecx
    jmp     .s2l_copy
.s2l_copied:
    mov     byte [rax + rcx], 0     ; null terminator
    add     r14, r15
    mov     rcx, rbx
    mov     rdx, rax
    call    _pyfasm_list_append
    jmp     .s2l_loop
.s2l_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     rbx, rax
.s2l_done:
    mov     rax, rbx
    lea     rsp, [rbp - 48]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

zip:
_pyfasm_zip:
    ; RCX = list a (or str a), RDX = list b (or str b)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16
    mov     r12, rcx                ; r12 = list a
    mov     r13, rdx                ; r13 = list b
    test    r12, r12
    jz      .zip_a_ready
    mov     rcx, r12
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .zip_a_ready
    mov     rcx, r12
    call    _pyfasm_str_to_char_list
    mov     r12, rax
.zip_a_ready:
    test    r13, r13
    jz      .zip_b_ready
    mov     rcx, r13
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .zip_b_ready
    mov     rcx, r13
    call    _pyfasm_str_to_char_list
    mov     r13, rax
.zip_b_ready:
    xor     r14, r14                ; min_len = 0
    test    r12, r12
    jz      .zip_alloc_empty
    test    r13, r13
    jz      .zip_alloc_empty
    mov     rax, [r12]
    mov     rdx, [r13]
    cmp     rax, rdx
    cmovle  r14, rax
    cmovg   r14, rdx
.zip_alloc_empty:
    mov     rcx, r14
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = result list
    mov     [rbx], r14              ; store length
    test    r14, r14
    jz      .zip_ret

    xor     r15, r15                ; i = 0
.zip_loop:
    cmp     r15, r14
    jge     .zip_ret
    ; Allocate 2-tuple: 24 bytes
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     qword [rax], 2          ; tuple len = 2
    mov     rdx, [r12 + r15 * 8 + 8] ; a[i]
    mov     [rax + 8], rdx
    mov     rdx, [r13 + r15 * 8 + 8] ; b[i]
    mov     [rax + 16], rdx
    mov     [rbx + r15 * 8 + 8], rax ; store tuple in result list
    inc     r15
    jmp     .zip_loop

.zip_ret:
    mov     rax, rbx
    lea     rsp, [rbp - 40]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

enumerate:
_pyfasm_enumerate:
    ; RCX = list a (or str a), RDX = start index
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16
    mov     r12, rcx                ; r12 = list a
    mov     r13, rdx                ; r13 = start index
    test    r12, r12
    jz      .enum_ready
    mov     rcx, r12
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .enum_ready
    mov     rcx, r12
    call    _pyfasm_str_to_char_list
    mov     r12, rax
.enum_ready:
    xor     r14, r14                ; len = 0
    test    r12, r12
    jz      .enum_alloc_empty
    mov     r14, [r12]
.enum_alloc_empty:
    mov     rcx, r14
    call    _pyfasm_list_create
    mov     rbx, rax
    mov     [rbx], r14
    test    r14, r14
    jz      .enum_ret

    xor     r15, r15                ; i = 0
.enum_loop:
    cmp     r15, r14
    jge     .enum_ret
    ; Allocate 2-tuple: 24 bytes
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     rdx, r15
    add     rdx, r13                ; i + start
    mov     [rax + 8], rdx
    mov     rdx, [r12 + r15 * 8 + 8] ; item
    mov     [rax + 16], rdx
    mov     [rbx + r15 * 8 + 8], rax
    inc     r15
    jmp     .enum_loop

.enum_ret:
    mov     rax, rbx
    lea     rsp, [rbp - 40]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

heappush:
_pyfasm_heappush:
    ; RCX = heap list pointer, RDX = item
    test    rcx, rcx
    jz      .hp_ret
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 32
    mov     rbx, rcx                ; rbx = heap
    mov     r12, rdx                ; r12 = item
    ; Append item to end
    mov     rcx, rbx
    mov     rdx, r12
    call    _pyfasm_list_append
    ; pos = len - 1
    mov     rax, [rbx]
    dec     rax                     ; rax = pos
.hp_siftup:
    test    rax, rax
    jle     .hp_done                ; while pos > 0
    mov     rdx, rax
    dec     rdx
    sar     rdx, 1                  ; parent = (pos - 1) / 2
    mov     r8, [rbx + rdx * 8 + 8] ; heap[parent]
    mov     r9, [rbx + rax * 8 + 8] ; heap[pos]
    cmp     r9, r8
    jge     .hp_done                ; if heap[pos] >= heap[parent]: done
    ; swap heap[pos] and heap[parent]
    mov     [rbx + rax * 8 + 8], r8
    mov     [rbx + rdx * 8 + 8], r9
    mov     rax, rdx                ; pos = parent
    jmp     .hp_siftup
.hp_done:
    add     rsp, 32
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
.hp_ret:
    xor     eax, eax
    ret

heappop:
_pyfasm_heappop:
    ; RCX = heap list pointer
    test    rcx, rcx
    jnz     .hpo_chk_len
    xor     eax, eax
    ret
.hpo_chk_len:
    mov     rax, [rcx]
    test    rax, rax
    jnz     .hpo_start
    xor     eax, eax
    ret
.hpo_start:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     rbx, rcx                ; rbx = heap
    mov     r12, [rbx + 8]          ; return item = heap[0]
    mov     rax, [rbx]
    dec     rax                     ; last_pos = len - 1
    mov     [rbx], rax              ; len--
    test    rax, rax
    jz      .hpo_done               ; if was 1 item, now 0
    ; move last item to root: heap[0] = heap[last_pos]
    mov     rdx, [rbx + (rax + 1) * 8]
    mov     [rbx + 8], rdx
    xor     r13, r13                ; pos = 0
    mov     r14, rax                ; count = len
.hpo_siftdown:
    mov     rax, r13
    shl     rax, 1
    inc     rax                     ; child = 2 * pos + 1
    cmp     rax, r14
    jge     .hpo_done               ; if child >= count: break
    mov     rdx, rax
    inc     rdx                     ; right = child + 1
    cmp     rdx, r14
    jge     .hpo_cmp_child
    mov     r8, [rbx + rax * 8 + 8] ; heap[child]
    mov     r9, [rbx + rdx * 8 + 8] ; heap[right]
    cmp     r9, r8
    cmovl   rax, rdx                ; if heap[right] < heap[child]: child = right
.hpo_cmp_child:
    mov     r8, [rbx + r13 * 8 + 8] ; heap[pos]
    mov     r9, [rbx + rax * 8 + 8] ; heap[child]
    cmp     r8, r9
    jle     .hpo_done               ; if heap[pos] <= heap[child]: break
    ; swap heap[pos] and heap[child]
    mov     [rbx + r13 * 8 + 8], r9
    mov     [rbx + rax * 8 + 8], r8
    mov     r13, rax                ; pos = child
    jmp     .hpo_siftdown
.hpo_done:
    mov     rax, r12                ; return popped root
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

heapreplace:
_pyfasm_heapreplace:
    ; RCX = heap list pointer, RDX = new item
    test    rcx, rcx
    jnz     .hpr_chk_len
    xor     eax, eax
    ret
.hpr_chk_len:
    mov     rax, [rcx]
    test    rax, rax
    jnz     .hpr_start
    xor     eax, eax
    ret
.hpr_start:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     rbx, rcx                ; rbx = heap
    mov     r12, [rbx + 8]          ; r12 = return old root
    mov     [rbx + 8], rdx          ; heap[0] = new_item
    xor     r13, r13                ; pos = 0
    mov     r14, [rbx]              ; count = len
.hpr_siftdown:
    mov     rax, r13
    shl     rax, 1
    inc     rax                     ; child = 2 * pos + 1
    cmp     rax, r14
    jge     .hpr_done               ; if child >= count: break
    mov     rdx, rax
    inc     rdx                     ; right = child + 1
    cmp     rdx, r14
    jge     .hpr_cmp_child
    mov     r8, [rbx + rax * 8 + 8] ; heap[child]
    mov     r9, [rbx + rdx * 8 + 8] ; heap[right]
    cmp     r9, r8
    cmovl   rax, rdx                ; if heap[right] < heap[child]: child = right
.hpr_cmp_child:
    mov     r8, [rbx + r13 * 8 + 8] ; heap[pos]
    mov     r9, [rbx + rax * 8 + 8] ; heap[child]
    cmp     r8, r9
    jle     .hpr_done               ; if heap[pos] <= heap[child]: break
    ; swap heap[pos] and heap[child]
    mov     [rbx + r13 * 8 + 8], r9
    mov     [rbx + rax * 8 + 8], r8
    mov     r13, rax                ; pos = child
    jmp     .hpr_siftdown
.hpr_done:
    mov     rax, r12                ; return old root
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

heapify:
_pyfasm_heapify:
    ; RCX = heap list pointer
    test    rcx, rcx
    jnz     .hpy_chk_len
    xor     eax, eax
    ret
.hpy_chk_len:
    mov     rax, [rcx]
    cmp     rax, 1
    jle     .hpy_ret_zero           ; if len <= 1: already a heap
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    mov     rbx, rcx                ; rbx = heap
    mov     r14, [rbx]              ; r14 = count = len
    mov     r15, r14
    shr     r15, 1
    dec     r15                     ; r15 = start_pos = (len / 2) - 1
.hpy_loop:
    test    r15, r15
    js      .hpy_done               ; while start_pos >= 0
    mov     r13, r15                ; pos = start_pos
.hpy_siftdown:
    mov     rax, r13
    shl     rax, 1
    inc     rax                     ; child = 2 * pos + 1
    cmp     rax, r14
    jge     .hpy_next               ; if child >= count: next start_pos
    mov     rdx, rax
    inc     rdx                     ; right = child + 1
    cmp     rdx, r14
    jge     .hpy_cmp_child
    mov     r8, [rbx + rax * 8 + 8] ; heap[child]
    mov     r9, [rbx + rdx * 8 + 8] ; heap[right]
    cmp     r9, r8
    cmovl   rax, rdx                ; if heap[right] < heap[child]: child = right
.hpy_cmp_child:
    mov     r8, [rbx + r13 * 8 + 8] ; heap[pos]
    mov     r9, [rbx + rax * 8 + 8] ; heap[child]
    cmp     r8, r9
    jle     .hpy_next               ; if heap[pos] <= heap[child]: next start_pos
    ; swap heap[pos] and heap[child]
    mov     [rbx + r13 * 8 + 8], r9
    mov     [rbx + rax * 8 + 8], r8
    mov     r13, rax                ; pos = child
    jmp     .hpy_siftdown
.hpy_next:
    dec     r15
    jmp     .hpy_loop
.hpy_done:
    add     rsp, 40
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
.hpy_ret_zero:
    xor     eax, eax                ; return None
    ret

sorted:
_pyfasm_sorted:
    ; RCX = list pointer
    test    rcx, rcx
    jnz     .srt_chk
    xor     eax, eax
    ret
.srt_chk:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    mov     rsi, rcx                ; rsi = src list
    mov     r12, [rsi]              ; r12 = len
    ; Allocate new list
    mov     rax, r12
    inc     rax
    shl     rax, 3                  ; (len + 1) * 8
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rdi, rax                ; rdi = dst list
    mov     [rdi], r12              ; store len
    ; Copy elements
    xor     rcx, rcx
.srt_cp:
    cmp     rcx, r12
    jge     .srt_sort
    mov     rax, [rsi + rcx * 8 + 8]
    mov     [rdi + rcx * 8 + 8], rax
    inc     rcx
    jmp     .srt_cp
.srt_sort:
    cmp     r12, 2
    jl      .srt_done
    mov     rbx, 1                  ; i = 1
.srt_outer:
    cmp     rbx, r12
    jge     .srt_done
    mov     r13, [rdi + rbx * 8 + 8] ; key = dst[i]
    mov     rcx, rbx
    dec     rcx                     ; j = i - 1
.srt_inner:
    test    rcx, rcx
    js      .srt_place
    mov     rax, [rdi + rcx * 8 + 8] ; dst[j]
    mov     r8, rax
    mov     r9, r13
    cmp     r8, 65536
    jb      .srt_cmp_sc
    cmp     r9, 65536
    jb      .srt_cmp_sc
    mov     r10, [r8]
    cmp     r10, 1
    jle     .srt_cmp_1
    mov     r8, [r8 + 16]
    mov     r9, [r9 + 16]
    jmp     .srt_cmp_sc
.srt_cmp_1:
    mov     r8, [r8 + 8]
    mov     r9, [r9 + 8]
.srt_cmp_sc:
    cmp     r8, r9
    jle     .srt_place              ; if dst[j] <= key: break
    mov     [rdi + (rcx + 1) * 8 + 8], rax ; dst[j + 1] = dst[j]
    dec     rcx
    jmp     .srt_inner
.srt_place:
    mov     [rdi + (rcx + 1) * 8 + 8], r13 ; dst[j + 1] = key
    inc     rbx
    jmp     .srt_outer
.srt_done:
    mov     rax, rdi                ; return sorted list pointer
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

sort:
_pyfasm_list_sort:
    ; RCX = list pointer
    test    rcx, rcx
    jnz     .lsrt_start
    xor     eax, eax
    ret
.lsrt_start:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    mov     rdi, rcx
    mov     r12, [rdi]              ; r12 = len
    cmp     r12, 2
    jl      .lsrt_done
    mov     rbx, 1                  ; i = 1
.lsrt_outer:
    cmp     rbx, r12
    jge     .lsrt_done
    mov     r13, [rdi + rbx * 8 + 8] ; key = dst[i]
    mov     rcx, rbx
    dec     rcx                     ; j = i - 1
.lsrt_inner:
    test    rcx, rcx
    js      .lsrt_place
    mov     rax, [rdi + rcx * 8 + 8] ; dst[j]
    mov     r8, rax
    mov     r9, r13
    cmp     r8, 65536
    jb      .lsrt_cmp_sc
    cmp     r9, 65536
    jb      .lsrt_cmp_sc
    mov     r10, [r8]
    cmp     r10, 1
    jle     .lsrt_cmp_1
    mov     r8, [r8 + 16]
    mov     r9, [r9 + 16]
    jmp     .lsrt_cmp_sc
.lsrt_cmp_1:
    mov     r8, [r8 + 8]
    mov     r9, [r9 + 8]
.lsrt_cmp_sc:
    cmp     r8, r9
    jle     .lsrt_place              ; if dst[j] <= key: break
    mov     [rdi + (rcx + 1) * 8 + 8], rax ; dst[j + 1] = dst[j]
    dec     rcx
    jmp     .lsrt_inner
.lsrt_place:
    mov     [rdi + (rcx + 1) * 8 + 8], r13 ; dst[j + 1] = key
    inc     rbx
    jmp     .lsrt_outer
.lsrt_done:
    xor     eax, eax                ; sort() returns None (0)
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_eq:
    ; RCX = list 1, RDX = list 2
    ; Returns: RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .leq_ret1
    test    rcx, rcx
    jz      .leq_ret0
    test    rdx, rdx
    jz      .leq_ret0
    cmp     rcx, 65536
    jb      .leq_ret0
    cmp     rdx, 65536
    jb      .leq_ret0
    mov     rax, [rcx]              ; length of list 1
    cmp     rax, [rdx]              ; length of list 2
    jne     .leq_ret0
    test    rax, rax
    jz      .leq_ret1               ; both empty lists -> equal!
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    mov     rsi, rcx                ; list 1
    mov     rdi, rdx                ; list 2
    mov     r12, [rsi]              ; length
    xor     rbx, rbx                ; index = 0
.leq_elem_loop:
    cmp     rbx, r12
    jge     .leq_all_match
    mov     r13, [rsi + rbx * 8 + 8] ; list1[i]
    mov     r14, [rdi + rbx * 8 + 8] ; list2[i]
    cmp     r13, r14
    jne     .leq_elem_diff
    inc     rbx
    jmp     .leq_elem_loop
.leq_elem_diff:
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
.leq_ret0:
    xor     eax, eax
    ret
.leq_all_match:
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
.leq_ret1:
    mov     eax, 1
    ret

_pyfasm_list2d_eq:
    ; RCX = list 1, RDX = list 2
    ; Returns: RAX = 1 if equal, 0 if not equal
    cmp     rcx, rdx
    je      .l2eq_ret1
    test    rcx, rcx
    jz      .l2eq_ret0
    test    rdx, rdx
    jz      .l2eq_ret0
    cmp     rcx, 65536
    jb      .l2eq_ret0
    cmp     rdx, 65536
    jb      .l2eq_ret0
    mov     rax, [rcx]              ; length of list 1
    cmp     rax, [rdx]              ; length of list 2
    jne     .l2eq_ret0
    test    rax, rax
    jz      .l2eq_ret1              ; both empty lists -> equal!
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 48
    mov     rsi, rcx                ; list 1
    mov     rdi, rdx                ; list 2
    mov     r12, [rsi]              ; length
    xor     rbx, rbx                ; index = 0
.l2eq_loop:
    cmp     rbx, r12
    jge     .l2eq_all_match
    mov     rcx, [rsi + rbx * 8 + 8] ; list1[i]
    mov     rdx, [rdi + rbx * 8 + 8] ; list2[i]
    call    _pyfasm_list_eq
    test    rax, rax
    jz      .l2eq_mismatch
    inc     rbx
    jmp     .l2eq_loop
.l2eq_mismatch:
    xor     eax, eax
    add     rsp, 48
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.l2eq_all_match:
    mov     eax, 1
    add     rsp, 48
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.l2eq_ret0:
    xor     eax, eax
    ret
.l2eq_ret1:
    mov     eax, 1
    ret

_pyfasm_list_repeat:
    ; RCX = list pointer
    ; RDX = count (signed 64-bit int)
    ; Returns: RAX = new list pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40

    mov     rsi, rcx                ; rsi = src_list
    mov     r12, rdx                ; r12 = count
    test    r12, r12
    jle     .lrep_empty
    test    rsi, rsi
    jz      .lrep_empty
    cmp     rsi, 65536
    jb      .lrep_empty

    mov     r13, [rsi]              ; r13 = src_len
    test    r13, r13
    jz      .lrep_empty

    ; total_len = src_len * count
    mov     rax, r13
    imul    rax, r12
    mov     r14, rax                ; r14 = total_len

    ; bytes = total_len * 8 + 16
    lea     rcx, [r14 * 8 + 16]
    call    _pyfasm_alloc
    mov     rdi, rax                ; rdi = new_list
    mov     [rdi], r14              ; store total_len

    ; Copy elements: outer loop = count, inner loop = src_len
    xor     rbx, rbx                ; dest_idx = 0
    xor     r15, r15                ; rep_i = 0
.lrep_outer:
    cmp     r15, r12
    jge     .lrep_done
    xor     r8, r8                  ; elem_j = 0
.lrep_inner:
    cmp     r8, r13
    jge     .lrep_inner_done
    mov     rax, [rsi + r8 * 8 + 8]
    mov     [rdi + rbx * 8 + 8], rax
    inc     rbx
    inc     r8
    jmp     .lrep_inner
.lrep_inner_done:
    inc     r15
    jmp     .lrep_outer

.lrep_empty:
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 0
    mov     rdi, rax

.lrep_done:
    mov     rax, rdi
    add     rsp, 40
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

_pyfasm_list_concat:
    ; RCX = list 1, RDX = list 2
    ; Returns: RAX = new concatenated list
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40

    mov     rsi, rcx                ; list 1
    mov     rdi, rdx                ; list 2
    xor     r12, r12                ; len 1 = 0
    xor     r13, r13                ; len 2 = 0
    test    rsi, rsi
    jz      .lcat_chk2
    cmp     rsi, 65536
    jb      .lcat_chk2
    mov     r12, [rsi]
.lcat_chk2:
    test    rdi, rdi
    jz      .lcat_alloc
    cmp     rdi, 65536
    jb      .lcat_alloc
    mov     r13, [rdi]

.lcat_alloc:
    lea     r14, [r12 + r13]        ; total_len
    lea     rcx, [r14 * 8 + 16]     ; bytes
    call    _pyfasm_alloc
    mov     r15, rax                ; new_list
    mov     [r15], r14              ; store total_len

    ; Copy from list 1
    xor     rbx, rbx
.lcat_cp1:
    cmp     rbx, r12
    jge     .lcat_cp2_start
    mov     rax, [rsi + rbx * 8 + 8]
    mov     [r15 + rbx * 8 + 8], rax
    inc     rbx
    jmp     .lcat_cp1

.lcat_cp2_start:
    xor     rcx, rcx
.lcat_cp2:
    cmp     rcx, r13
    jge     .lcat_done
    mov     rax, [rdi + rcx * 8 + 8]
    mov     [r15 + rbx * 8 + 8], rax
    inc     rbx
    inc     rcx
    jmp     .lcat_cp2

.lcat_done:
    mov     rax, r15
    add     rsp, 40
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

_pyfasm_str_isdigit:
    ; RCX = null-terminated string pointer
    test    rcx, rcx
    jnz     .sdi_chk
    xor     eax, eax
    ret
.sdi_chk:
    movzx   eax, byte [rcx]
    test    al, al
    jnz     .sdi_loop
    xor     eax, eax
    ret
.sdi_loop:
    movzx   eax, byte [rcx]
    test    al, al
    jz      .sdi_true
    cmp     al, '0'
    jl      .sdi_false
    cmp     al, '9'
    jg      .sdi_false
    inc     rcx
    jmp     .sdi_loop
.sdi_true:
    mov     eax, 1
    ret
.sdi_false:
    xor     eax, eax
    ret

_pyfasm_str_isascii:
    ; RCX = null-terminated string pointer
    test    rcx, rcx
    jnz     .sia_loop
    mov     eax, 1
    ret
.sia_loop:
    movzx   eax, byte [rcx]
    test    al, al
    jz      .sia_true
    cmp     al, 127
    ja      .sia_false
    inc     rcx
    jmp     .sia_loop
.sia_true:
    mov     eax, 1
    ret
.sia_false:
    xor     eax, eax
    ret

nanogemm_simd_isa:
get_simd_isa:
_pyfasm_nanogemm_simd_isa:
    lea     rax, [szNanoGemmISA]
    ret

matmul:
nanogemm_matmul:
_pyfasm_nanogemm_matmul:
    ; RCX = A (list pointer or 2D list), RDX = B (list pointer or 2D list)
    test    rcx, rcx
    jnz     .ngm_chk_b
    xor     eax, eax
    ret
.ngm_chk_b:
    test    rdx, rdx
    jnz     .ngm_start
    xor     eax, eax
    ret
.ngm_start:
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
    mov     [rsp + 0], rcx          ; A
    mov     [rsp + 8], rdx          ; B

    mov     rax, [rcx]
    test    rax, rax
    jz      .ngm_empty

    mov     r8, [rcx + 8]           ; A[0]
    mov     r9, [rdx + 8]           ; B[0]
    cmp     r8, 0x10000
    jb      .ngm_1d_dot
    test    r8, 7
    jnz     .ngm_1d_dot
    mov     rax, [r8]
    cmp     rax, 10000000
    ja      .ngm_1d_dot

    ; --- 2D Matrix Multiplication ---
    mov     r12, [rcx]              ; r12 = M
    mov     r13, [r8]               ; r13 = K
    mov     r14, [r9]               ; r14 = N
    mov     [rsp + 16], r12         ; M
    mov     [rsp + 24], r13         ; K
    mov     [rsp + 32], r14         ; N

    mov     rax, r12
    inc     rax
    shl     rax, 3                  ; (M + 1) * 8
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rsp + 40], rax         ; C
    mov     r12, [rsp + 16]
    mov     [rax], r12

    xor     rbx, rbx                ; i = 0
.ngm_2d_row_loop:
    cmp     rbx, [rsp + 16]
    jge     .ngm_2d_done

    mov     rax, [rsp + 32]         ; N
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     r15, rax                ; C[i]
    mov     rax, [rsp + 32]
    mov     [r15], rax

    mov     rax, [rsp + 40]
    mov     [rax + rbx * 8 + 8], r15

    xor     rsi, rsi                ; j = 0
.ngm_2d_col_loop:
    cmp     rsi, [rsp + 32]
    jge     .ngm_2d_row_next

    xor     r11, r11                ; acc = 0
    xor     rdi, rdi                ; k = 0
.ngm_2d_dot_loop:
    cmp     rdi, [rsp + 24]
    jge     .ngm_2d_store_cell

    mov     rax, [rsp + 0]
    mov     rax, [rax + rbx * 8 + 8]
    mov     rax, [rax + rdi * 8 + 8]

    mov     r10, [rsp + 8]
    mov     r10, [r10 + rdi * 8 + 8]
    mov     r10, [r10 + rsi * 8 + 8]

    imul    rax, r10
    add     r11, rax
    inc     rdi
    jmp     .ngm_2d_dot_loop

.ngm_2d_store_cell:
    mov     [r15 + rsi * 8 + 8], r11
    inc     rsi
    jmp     .ngm_2d_col_loop

.ngm_2d_row_next:
    inc     rbx
    jmp     .ngm_2d_row_loop

.ngm_2d_done:
    mov     rax, [rsp + 40]
    jmp     .ngm_epilog

.ngm_1d_dot:
    mov     rcx, [rsp + 0]
    mov     rdx, [rsp + 8]
    mov     r8, [rcx]
    mov     r9, [rdx]
    cmp     r8, r9
    cmovg   r8, r9
    xor     rax, rax
    xor     rcx, rcx
.ngm_1d_loop:
    cmp     rcx, r8
    jge     .ngm_1d_done
    mov     r10, [rsp + 0]
    mov     r10, [r10 + rcx * 8 + 8]
    mov     r11, [rsp + 8]
    mov     r11, [r11 + rcx * 8 + 8]
    imul    r10, r11
    add     rax, r10
    inc     rcx
    jmp     .ngm_1d_loop
.ngm_1d_done:
    jmp     .ngm_epilog

.ngm_empty:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     qword [rax], 0
.ngm_epilog:
    add     rsp, 64
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

_pyfasm_np_zeros:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    test    rdx, rdx
    jnz     .npz_2d
    mov     r12, rcx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r12
    xor     rcx, rcx
.npz_1d_clr:
    cmp     rcx, r12
    jge     .npz_done
    mov     qword [rax + rcx * 8 + 8], 0
    inc     rcx
    jmp     .npz_1d_clr
.npz_2d:
    mov     r12, rcx
    mov     r13, rdx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     [rbx], r12
    xor     rsi, rsi
.npz_2d_loop:
    cmp     rsi, r12
    jge     .npz_2d_ret
    mov     rax, r13
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r13
    xor     rcx, rcx
.npz_row_clr:
    cmp     rcx, r13
    jge     .npz_row_done
    mov     qword [rax + rcx * 8 + 8], 0
    inc     rcx
    jmp     .npz_row_clr
.npz_row_done:
    mov     [rbx + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npz_2d_loop
.npz_2d_ret:
    mov     rax, rbx
.npz_done:
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_np_ones:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 40
    test    rdx, rdx
    jnz     .npo_2d
    mov     r12, rcx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r12
    mov     rdx, 3FF0000000000000h
    xor     rcx, rcx
.npo_1d_set:
    cmp     rcx, r12
    jge     .npo_done
    mov     [rax + rcx * 8 + 8], rdx
    inc     rcx
    jmp     .npo_1d_set
.npo_2d:
    mov     r12, rcx
    mov     r13, rdx
    mov     rax, r12
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     [rbx], r12
    xor     rsi, rsi
.npo_2d_loop:
    cmp     rsi, r12
    jge     .npo_2d_ret
    mov     rax, r13
    inc     rax
    shl     rax, 3
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], r13
    mov     rdx, 3FF0000000000000h
    xor     rcx, rcx
.npo_row_set:
    cmp     rcx, r13
    jge     .npo_row_done
    mov     [rax + rcx * 8 + 8], rdx
    inc     rcx
    jmp     .npo_row_set
.npo_row_done:
    mov     [rbx + rsi * 8 + 8], rax
    inc     rsi
    jmp     .npo_2d_loop
.npo_2d_ret:
    mov     rax, rbx
.npo_done:
    add     rsp, 40
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

math_gcd:
gcd:
_pyfasm_math_gcd:
    ; RCX = a, RDX = b
    mov     rax, rcx
    test    rax, rax
    jns     .gcd_chk_b
    neg     rax
.gcd_chk_b:
    mov     rcx, rdx
    test    rcx, rcx
    jns     .gcd_loop
    neg     rcx
.gcd_loop:
    test    rcx, rcx
    jz      .gcd_done
    xor     edx, edx
    div     rcx                     ; rax = rax / rcx, rdx = rax % rcx
    mov     rax, rcx                ; a = b
    mov     rcx, rdx                ; b = remainder
    jmp     .gcd_loop
.gcd_done:
    ret

_pyfasm_math_gcd_list:
    ; RCX = list_ptr [len, elt0, elt1, ...]
    ; Returns RAX = GCD of all elements
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .mgl_zero

    mov     rbx, rcx
    mov     rdi, [rbx]          ; length
    test    rdi, rdi
    jz      .mgl_zero

    ; First element
    mov     rax, [rbx + 8]
    test    rax, rax
    jns     .mgl_chk1
    neg     rax
.mgl_chk1:
    mov     r12, 1              ; index = 1
.mgl_loop:
    cmp     r12, rdi
    jge     .mgl_done

    mov     rdx, [rbx + r12 * 8 + 8] ; b = elt[i]
    mov     rcx, rax                 ; a = current gcd
    sub     rsp, 32
    call    _pyfasm_math_gcd         ; rax = gcd(a, b)
    add     rsp, 32
    inc     r12
    jmp     .mgl_loop

.mgl_done:
    jmp     .mgl_ret

.mgl_zero:
    xor     eax, eax
.mgl_ret:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

math_lcm:
lcm:
_pyfasm_math_lcm:
    ; RCX = a, RDX = b
    test    rcx, rcx
    jz      .lcm_zero
    test    rdx, rdx
    jz      .lcm_zero
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    mov     rbx, rcx                ; a
    mov     r12, rdx                ; b
    call    _pyfasm_math_gcd        ; rax = gcd(a, b)
    test    rax, rax
    jz      .lcm_done
    mov     r8, rax                 ; r8 = gcd
    mov     rax, rbx
    imul    rax, r12                ; a * b
    test    rax, rax
    jns     .lcm_div
    neg     rax                     ; abs(a * b)
.lcm_div:
    xor     edx, edx
    div     r8                      ; abs(a * b) / gcd
.lcm_done:
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.lcm_zero:
    xor     eax, eax
    ret

math_isqrt:
isqrt:
_pyfasm_math_isqrt:
    ; RCX = n (non-negative int)
    test    rcx, rcx
    jns     .isqrt_start
    xor     eax, eax
    ret
.isqrt_start:
    test    rcx, rcx
    jnz     .isqrt_non_zero
    xor     eax, eax
    ret
.isqrt_non_zero:
    mov     r8, rcx                 ; r8 = n
    mov     r9, rcx                 ; x = n
.isqrt_loop:
    mov     rax, r8
    xor     edx, edx
    div     r9                      ; rax = n / x
    add     rax, r9                 ; rax = x + n / x
    shr     rax, 1                  ; next_x = (x + n / x) / 2
    cmp     rax, r9
    jge     .isqrt_ret              ; while next_x < x
    mov     r9, rax                 ; x = next_x
    jmp     .isqrt_loop
.isqrt_ret:
    mov     rax, r9
    ret

math_factorial:
factorial:
_pyfasm_math_factorial:
    ; RCX = n
    mov     rax, 1
    test    rcx, rcx
    jle     .fact_done
.fact_loop:
    imul    rax, rcx
    dec     rcx
    jnz     .fact_loop
.fact_done:
    ret

itertools_chain:
chain:
_pyfasm_itertools_chain:
    ; RCX = list a, RDX = list b
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    mov     r12, rcx                ; r12 = list a
    mov     r13, rdx                ; r13 = list b
    xor     r14, r14                ; len_a = 0
    xor     r15, r15                ; len_b = 0
    test    r12, r12
    jz      .chn_chk_b
    mov     r14, [r12]
.chn_chk_b:
    test    r13, r13
    jz      .chn_alloc
    mov     r15, [r13]
.chn_alloc:
    mov     rcx, r14
    add     rcx, r15                ; total len
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = new list
    mov     rax, r14
    add     rax, r15
    mov     [rbx], rax              ; store total len
    xor     rcx, rcx
.chn_loop_a:
    cmp     rcx, r14
    jge     .chn_copy_b
    mov     rdx, [r12 + rcx * 8 + 8]
    mov     [rbx + rcx * 8 + 8], rdx
    inc     rcx
    jmp     .chn_loop_a
.chn_copy_b:
    xor     rdx, rdx
.chn_loop_b:
    cmp     rdx, r15
    jge     .chn_done
    mov     rax, [r13 + rdx * 8 + 8]
    mov     r8, r14
    add     r8, rdx
    mov     [rbx + r8 * 8 + 8], rax
    inc     rdx
    jmp     .chn_loop_b
.chn_done:
    mov     rax, rbx
    add     rsp, 40
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

itertools_accumulate:
accumulate:
_pyfasm_itertools_accumulate:
    ; RCX = list
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    mov     r12, rcx
    xor     r13, r13
    test    r12, r12
    jz      .acc_alloc
    mov     r13, [r12]
.acc_alloc:
    mov     rcx, r13
    call    _pyfasm_list_create
    mov     rbx, rax                ; rbx = res list
    mov     [rbx], r13
    test    r13, r13
    jz      .acc_done
    xor     r14, r14
    xor     rcx, rcx
.acc_loop:
    cmp     rcx, r13
    jge     .acc_done
    mov     rdx, [r12 + rcx * 8 + 8]
    add     r14, rdx
    mov     [rbx + rcx * 8 + 8], r14
    inc     rcx
    jmp     .acc_loop
.acc_done:
    mov     rax, rbx
    add     rsp, 32
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

functools_reduce:
reduce:
_pyfasm_functools_reduce:
    ; RCX = function pointer, RDX = list, R8 = initial, R9 = has_initial
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    mov     r12, rcx                ; r12 = fn
    mov     r13, rdx                ; r13 = list
    xor     r14, r14
    test    r13, r13
    jz      .red_ret_zero
    mov     r14, [r13]
    test    r14, r14
    jz      .red_ret_zero
    test    r9, r9
    jnz     .red_with_init
    mov     r15, [r13 + 8]          ; acc = list[0]
    mov     rbx, 1                  ; start at 1
    jmp     .red_loop
.red_with_init:
    mov     r15, r8                 ; acc = initial
    xor     rbx, rbx
.red_loop:
    cmp     rbx, r14
    jge     .red_done
    mov     rcx, r15                ; arg 0 = acc
    mov     rdx, [r13 + rbx * 8 + 8] ; arg 1 = item
    call    r12
    mov     r15, rax                ; acc = result
    inc     rbx
    jmp     .red_loop
.red_done:
    mov     rax, r15
    jmp     .red_exit
.red_ret_zero:
    xor     eax, eax
.red_exit:
    add     rsp, 40
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

math_sumprod:
sumprod:
_pyfasm_math_sumprod:
    ; RCX = list a, RDX = list b -> RAX = sum(a[i] * b[i])
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    xor     rax, rax
    test    rcx, rcx
    jz      .sp_done
    test    rdx, rdx
    jz      .sp_done
    mov     rsi, rcx
    mov     rdi, rdx
    mov     r12, [rsi]
    mov     r13, [rdi]
    cmp     r12, r13
    cmovg   r12, r13
    test    r12, r12
    jle     .sp_done
    xor     ecx, ecx
.sp_loop:
    cmp     rcx, r12
    jge     .sp_done
    mov     rdx, [rsi + rcx * 8 + 8]
    imul    rdx, [rdi + rcx * 8 + 8]
    add     rax, rdx
    inc     rcx
    jmp     .sp_loop
.sp_done:
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

itertools_batched:
batched:
_pyfasm_itertools_batched:
    ; RCX = list, RDX = batch size n -> RAX = list of batch lists
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
    mov     rsi, rcx
    mov     r12, rdx
    test    rsi, rsi
    jz      .bat_empty
    cmp     r12, 1
    jl      .bat_empty
    mov     r13, [rsi]
    test    r13, r13
    jle     .bat_empty

    mov     rax, r13
    add     rax, r12
    dec     rax
    xor     edx, edx
    div     r12
    mov     r14, rax

    mov     rcx, r14
    call    _pyfasm_list_create
    mov     rbx, rax
    mov     [rbx], r14

    xor     r15, r15
    xor     edi, edi
.bat_outer_loop:
    cmp     r15, r14
    jge     .bat_finish

    mov     rcx, r13
    sub     rcx, rdi
    cmp     rcx, r12
    cmovg   rcx, r12
    mov     [rsp + 32], rcx

    call    _pyfasm_list_create
    mov     r8, rax
    mov     rcx, [rsp + 32]
    mov     [r8], rcx

    xor     edx, edx
.bat_inner_loop:
    cmp     rdx, [rsp + 32]
    jge     .bat_inner_done
    mov     rax, [rsi + rdi * 8 + 8]
    mov     [r8 + rdx * 8 + 8], rax
    inc     rdi
    inc     rdx
    jmp     .bat_inner_loop
.bat_inner_done:
    mov     [rbx + r15 * 8 + 8], r8
    inc     r15
    jmp     .bat_outer_loop

.bat_finish:
    mov     rax, rbx
    jmp     .bat_ret
.bat_empty:
    xor     ecx, ecx
    call    _pyfasm_list_create
.bat_ret:
    add     rsp, 48
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

os_cpu_count:
cpu_count:
process_cpu_count:
_pyfasm_os_cpu_count:
    mov     rax, [gs:60h]
    test    rax, rax
    jz      .cpu_def
    movzx   eax, byte [rax + 0B8h]
    test    eax, eax
    jnz     .cpu_ret
.cpu_def:
    mov     eax, 8
.cpu_ret:
    ret


_pyfasm_load_ext_symbol:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    mov     [rbp - 8], rdx
    call    [LoadLibraryA]
    test    rax, rax
    jz      .les_fail
    mov     rcx, rax
    mov     rdx, [rbp - 8]
    call    [GetProcAddress]
    jmp     .les_ret
.les_fail:
    xor     eax, eax
.les_ret:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_int_to_str:
    ; RCX = integer
    ; Returns RAX = pointer to newly allocated null-terminated string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 80
    and     rsp, -16

    lea     rdi, [rbp - 32]
    mov     byte [rdi], 0
    mov     rax, rcx

    test    rax, rax
    jnz     .its_check_neg
    dec     rdi
    mov     byte [rdi], '0'
    jmp     .its_copy_alloc

.its_check_neg:
    xor     ebx, ebx
    test    rax, rax
    jns     .its_loop
    mov     ebx, 1
    neg     rax

.its_loop:
    test    rax, rax
    jz      .its_finish
    mov     r8, rax
    mov     rdx, 0CCCCCCCCCCCCCCCDh
    mul     rdx
    shr     rdx, 3
    lea     rcx, [rdx + rdx * 4]
    shl     rcx, 1
    sub     r8, rcx
    add     r8b, '0'
    dec     rdi
    mov     [rdi], r8b
    mov     rax, rdx
    jmp     .its_loop

.its_finish:
    test    ebx, ebx
    jz      .its_copy_alloc
    dec     rdi
    mov     byte [rdi], '-'

.its_copy_alloc:
    mov     rsi, rdi
    lea     rcx, [rbp - 32]
    sub     rcx, rsi
    inc     rcx
    mov     rbx, rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     rdx, rax
    mov     rcx, rbx
    rep     movsb
    mov     rax, rdx

    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_is_utf8_str_ptr:
    ; RCX = candidate value -> RAX = 1 if readable committed UTF-8 C-string, else 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .iu_no
    cmp     rsi, 65536
    jb      .iu_no
    mov     rax, 00007FFFFFFF0000h
    cmp     rsi, rax
    jae     .iu_no

    ; VirtualQuery(rsi, &mbi_at_rsp_32, 48)
    mov     rcx, rsi
    lea     rdx, [rsp + 32]
    mov     r8d, 48
    call    [VirtualQuery]
    test    rax, rax
    jz      .iu_no
    cmp     dword [rsp + 64], 1000h     ; MEM_COMMIT
    jne     .iu_no
    mov     eax, dword [rsp + 68]       ; Protect
    test    eax, 100h                   ; PAGE_GUARD
    jnz     .iu_no
    test    eax, 0EEh                   ; readable protection
    jz      .iu_no

    mov     rax, [rsp + 32]             ; BaseAddress
    add     rax, [rsp + 56]             ; + RegionSize
    sub     rax, rsi
    jbe     .iu_no
    xor     ebx, ebx
    cmp     rax, 256
    jb      .iu_have_limit
    mov     rax, 256
    mov     ebx, 1
.iu_have_limit:
    mov     r8, rax
    xor     r9d, r9d
.iu_loop:
    cmp     r9, r8
    jae     .iu_hit_limit
    movzx   eax, byte [rsi + r9]
    test    al, al
    jz      .iu_yes
    cmp     al, 80h
    jb      .iu_ascii

    cmp     al, 0C2h
    jb      .iu_no
    cmp     al, 0DFh
    jbe     .iu_mb1
    cmp     al, 0EFh
    jbe     .iu_mb2
    cmp     al, 0F4h
    jbe     .iu_mb3
    jmp     .iu_no

.iu_mb1:
    lea     r10, [r9 + 1]
    cmp     r10, r8
    jae     .iu_mb_limit
    movzx   edx, byte [rsi + r9 + 1]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    add     r9, 2
    jmp     .iu_loop

.iu_mb2:
    lea     r10, [r9 + 2]
    cmp     r10, r8
    jae     .iu_mb_limit
    movzx   edx, byte [rsi + r9 + 1]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    movzx   edx, byte [rsi + r9 + 2]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    add     r9, 3
    jmp     .iu_loop

.iu_mb3:
    lea     r10, [r9 + 3]
    cmp     r10, r8
    jae     .iu_mb_limit
    movzx   edx, byte [rsi + r9 + 1]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    movzx   edx, byte [rsi + r9 + 2]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    movzx   edx, byte [rsi + r9 + 3]
    and     dl, 0C0h
    cmp     dl, 80h
    jne     .iu_no
    add     r9, 4
    jmp     .iu_loop

.iu_mb_limit:
    test    ebx, ebx
    jnz     .iu_yes
    jmp     .iu_no

.iu_ascii:
    cmp     al, 9
    je      .iu_ascii_ok
    cmp     al, 10
    je      .iu_ascii_ok
    cmp     al, 13
    je      .iu_ascii_ok
    cmp     al, 32
    jb      .iu_no
    cmp     al, 126
    ja      .iu_no
.iu_ascii_ok:
    inc     r9
    jmp     .iu_loop

.iu_hit_limit:
    test    ebx, ebx
    jnz     .iu_yes
.iu_no:
    xor     eax, eax
    jmp     .iu_ret
.iu_yes:
    mov     eax, 1
.iu_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_auto:
    ; RCX = value (int64, f64 bits, or UTF-8 string pointer)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    mov     rax, rbx
    sar     rax, 48
    test    rax, rax
    jz      .pa_not_flt
    cmp     rax, -1
    je      .pa_not_flt
    call    _pyfasm_eval_print_clean_float
    jmp     .pa_done
.pa_not_flt:
    mov     rcx, rbx
    call    _pyfasm_is_utf8_str_ptr
    mov     rcx, rbx
    test    eax, eax
    jz      .pa_int
    call    _pyfasm_print_str
    jmp     .pa_done
.pa_int:
    call    _pyfasm_print_int
.pa_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_float_bits:
    ; RCX = IEEE-754 float64 bits
    movq    xmm0, rcx
    jmp     _pyfasm_print_float

_pyfasm_print_str_repr:
    ; RCX = string pointer -> prints 'text' or None
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jnz     .psr_nonnull
    lea     rcx, [none_str]
    call    _pyfasm_print_str
    jmp     .psr_done
.psr_nonnull:
    lea     rcx, [squote_str]
    call    _pyfasm_print_str
    mov     rcx, rbx
    call    _pyfasm_print_str
    lea     rcx, [squote_str]
    call    _pyfasm_print_str
.psr_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_auto_repr:
    ; RCX = value -> prints 'str' if UTF-8 string pointer, else int
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    mov     rcx, rbx
    test    eax, eax
    jz      .par_int
    call    _pyfasm_print_str_repr
    jmp     .par_done
.par_int:
    call    _pyfasm_print_int
.par_done:
    lea     rsp, [rbp - 8]
    pop     rbx
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
    sub     rsp, 80
    and     rsp, -16

    mov     rax, rcx
    test    rax, rax
    jns     .positive

    ; Negative number
    mov     rbx, rax
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    mov     rax, rbx
    neg     rax

.positive:
    lea     rdi, [rbp - 32]         ; end of temporary digit buffer
    mov     byte [rdi], 0           ; null-terminator
    mov     rsi, rax
    mov     r9, 0CCCCCCCCCCCCCCCDh  ; reciprocal multiplier for fast division by 10 (from porth/Lemire)

.digit_loop:
    mov     rax, rsi
    mul     r9                      ; rdx = (rsi * r9) >> 64
    shr     rdx, 3                  ; rdx = quotient
    lea     rcx, [rdx + rdx * 4]
    add     rcx, rcx                ; rcx = quotient * 10
    mov     rax, rsi
    sub     rax, rcx                ; rax = remainder (0..9)
    add     al, '0'
    dec     rdi
    mov     [rdi], al
    mov     rsi, rdx                ; update quotient
    test    rsi, rsi
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

_pyfasm_print_list_with:
    ; RCX = list pointer, RDX = element printer function pointer (takes RCX)
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
    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jnz     .plw_not_null
    lea     rcx, [lbrack_str]
    call    _pyfasm_print_str
    lea     rcx, [rbrack_str]
    call    _pyfasm_print_str
    jmp     .plw_ret

.plw_not_null:
    test    rbx, rbx
    js      .plw_is_int
    cmp     rbx, 65536
    jb      .plw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jb      .plw_is_ptr
.plw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
    jmp     .plw_ret

.plw_is_ptr:
    lea     rcx, [lbrack_str]
    call    _pyfasm_print_str
    mov     r12, [rbx]
    xor     r13, r13

.plw_loop:
    cmp     r13, r12
    jge     .plw_end
    test    r13, r13
    jz      .plw_elem
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str

.plw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    inc     r13
    jmp     .plw_loop

.plw_end:
    lea     rcx, [rbrack_str]
    call    _pyfasm_print_str

.plw_ret:
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

_pyfasm_print_list:
    lea     rdx, [_pyfasm_print_auto_repr]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_int:
    lea     rdx, [_pyfasm_print_int]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_str:
    lea     rdx, [_pyfasm_print_str_repr]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_float:
    lea     rdx, [_pyfasm_print_float_bits]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_int:
    lea     rdx, [_pyfasm_print_list_int]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_str:
    lea     rdx, [_pyfasm_print_list_str]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_float:
    lea     rdx, [_pyfasm_print_list_float]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_2d_auto:
    lea     rdx, [_pyfasm_print_list]
    jmp     _pyfasm_print_list_with

_pyfasm_print_list_3d_int:
    lea     rdx, [_pyfasm_print_list_2d_int]
    jmp     _pyfasm_print_list_with

_pyfasm_print_tuple_with:
    ; RCX = tuple pointer, RDX = element printer function pointer (takes RCX)
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
    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jnz     .ptw_not_null
    lea     rcx, [lparen_str]
    call    _pyfasm_print_str
    lea     rcx, [rparen_str]
    call    _pyfasm_print_str
    jmp     .ptw_ret

.ptw_not_null:
    test    rbx, rbx
    js      .ptw_is_int
    cmp     rbx, 65536
    jb      .ptw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jb      .ptw_is_ptr
.ptw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
    jmp     .ptw_ret

.ptw_is_ptr:
    lea     rcx, [lparen_str]
    call    _pyfasm_print_str
    mov     r12, [rbx]
    xor     r13, r13

.ptw_loop:
    cmp     r13, r12
    jge     .ptw_after_loop
    test    r13, r13
    jz      .ptw_elem
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str

.ptw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    inc     r13
    jmp     .ptw_loop

.ptw_after_loop:
    cmp     r12, 1
    jne     .ptw_end
    lea     rcx, [comma_str]
    call    _pyfasm_print_str

.ptw_end:
    lea     rcx, [rparen_str]
    call    _pyfasm_print_str

.ptw_ret:
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

_pyfasm_print_tuple:
    lea     rdx, [_pyfasm_print_auto_repr]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_int:
    lea     rdx, [_pyfasm_print_int]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_str:
    lea     rdx, [_pyfasm_print_str_repr]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_float:
    lea     rdx, [_pyfasm_print_float_bits]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_tuple_list:
    lea     rdx, [_pyfasm_print_list]
    jmp     _pyfasm_print_tuple_with

_pyfasm_print_dict_with:
    ; RCX = dict_ptr, RDX = key_printer(rcx), R8 = val_printer(rcx)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    mov     r15, r8
    test    rbx, rbx
    jz      .pdw_empty
    test    rbx, rbx
    js      .pdw_is_int
    cmp     rbx, 65536
    jb      .pdw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .pdw_is_int

    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    mov     r12, [rbx]
    xor     r13, r13
    xor     edi, edi
.pdw_loop:
    cmp     r13, r12
    jge     .pdw_end
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .pdw_next
    cmp     rax, -1
    je      .pdw_next

    test    edi, edi
    jz      .pdw_no_comma
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str
.pdw_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
    lea     rcx, [colon_sp_str]
    call    _pyfasm_print_str
    mov     rcx, [rsi + 16]
    call    r15
.pdw_next:
    inc     r13
    jmp     .pdw_loop
.pdw_end:
    lea     rcx, [rbrace_str]
    call    _pyfasm_print_str
    jmp     .pdw_ret
.pdw_empty:
    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    lea     rcx, [rbrace_str]
    call    _pyfasm_print_str
    jmp     .pdw_ret
.pdw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
.pdw_ret:
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

_pyfasm_print_set_with:
    ; RCX = set_ptr (hash table or list-backed), RDX = elem_printer(rcx)
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

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .psw_empty
    test    rbx, rbx
    js      .psw_is_int
    cmp     rbx, 65536
    jb      .psw_is_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .psw_is_int

    mov     r12, [rbx]
    cmp     r12, 256
    jb      .psw_list_mode
    cmp     qword [rbx + 8], 0
    jle     .psw_empty

    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    xor     r13, r13
    xor     edi, edi
.psw_ht_loop:
    cmp     r13, r12
    jge     .psw_end
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .psw_ht_next
    cmp     rax, -1
    je      .psw_ht_next
    test    edi, edi
    jz      .psw_ht_no_comma
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str
.psw_ht_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
.psw_ht_next:
    inc     r13
    jmp     .psw_ht_loop

.psw_list_mode:
    test    r12, r12
    jle     .psw_empty
    lea     rcx, [lbrace_str]
    call    _pyfasm_print_str
    xor     r13, r13
.psw_lst_loop:
    cmp     r13, r12
    jge     .psw_end
    test    r13, r13
    jz      .psw_lst_elem
    lea     rcx, [comma_sp_str]
    call    _pyfasm_print_str
.psw_lst_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    inc     r13
    jmp     .psw_lst_loop

.psw_end:
    lea     rcx, [rbrace_str]
    call    _pyfasm_print_str
    jmp     .psw_ret
.psw_empty:
    lea     rcx, [empty_set_str]
    call    _pyfasm_print_str
    jmp     .psw_ret
.psw_is_int:
    mov     rcx, rbx
    call    _pyfasm_print_int
.psw_ret:
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

_pyfasm_str_to_repr:
    ; RCX = string pointer -> RAX = heap string "'...'" or None
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    test    rcx, rcx
    jnz     .strr_nonnull
    lea     rax, [none_str]
    jmp     .strr_done
.strr_nonnull:
    mov     rdx, rcx
    lea     rcx, [squote_str]
    call    _pyfasm_str_concat
    mov     rcx, rax
    lea     rdx, [squote_str]
    call    _pyfasm_str_concat
.strr_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_auto_to_str:
    ; RCX = value -> RAX = string pointer
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    mov     rax, rbx
    sar     rax, 48
    test    rax, rax
    jz      .ats_not_flt
    cmp     rax, -1
    je      .ats_not_flt
    call    _pyfasm_eval_float_to_clean_str
    jmp     .ats_done
.ats_not_flt:
    mov     rcx, rbx
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jz      .ats_int
    mov     rax, rbx
    jmp     .ats_done
.ats_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.ats_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_auto_to_repr:
    ; RCX = value -> RAX = repr string pointer ('str' if UTF-8 ptr, else int str)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    mov     rcx, rbx
    test    eax, eax
    jz      .atr_int
    call    _pyfasm_str_to_repr
    jmp     .atr_done
.atr_int:
    call    _pyfasm_int_to_str
.atr_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_to_str_with:
    ; RCX = list pointer, RDX = elem_to_str(rcx)->rax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .ltsw_empty
    test    rbx, rbx
    js      .ltsw_int
    cmp     rbx, 65536
    jb      .ltsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .ltsw_int

    lea     r15, [lbrack_str]
    mov     r12, [rbx]
    xor     r13, r13
.ltsw_loop:
    cmp     r13, r12
    jge     .ltsw_close
    test    r13, r13
    jz      .ltsw_elem
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.ltsw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .ltsw_loop
.ltsw_close:
    mov     rcx, r15
    lea     rdx, [rbrack_str]
    call    _pyfasm_str_concat
    jmp     .ltsw_ret
.ltsw_empty:
    lea     rcx, [lbrack_str]
    lea     rdx, [rbrack_str]
    call    _pyfasm_str_concat
    jmp     .ltsw_ret
.ltsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.ltsw_ret:
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

_pyfasm_list_to_str:
    lea     rdx, [_pyfasm_auto_to_repr]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_int_to_str:
    lea     rdx, [_pyfasm_int_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_str_to_str:
    lea     rdx, [_pyfasm_str_to_repr]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_float_to_str:
    lea     rdx, [_pyfasm_float_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_int_to_str:
    lea     rdx, [_pyfasm_list_int_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_str_to_str:
    lea     rdx, [_pyfasm_list_str_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_float_to_str:
    lea     rdx, [_pyfasm_list_float_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_2d_auto_to_str:
    lea     rdx, [_pyfasm_list_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_list_3d_int_to_str:
    lea     rdx, [_pyfasm_list_2d_int_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_tuple_to_str_with:
    ; RCX = tuple pointer, RDX = elem_to_str(rcx)->rax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .ttsw_empty
    test    rbx, rbx
    js      .ttsw_int
    cmp     rbx, 65536
    jb      .ttsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .ttsw_int

    lea     r15, [lparen_str]
    mov     r12, [rbx]
    xor     r13, r13
.ttsw_loop:
    cmp     r13, r12
    jge     .ttsw_after_loop
    test    r13, r13
    jz      .ttsw_elem
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.ttsw_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .ttsw_loop
.ttsw_after_loop:
    cmp     r12, 1
    jne     .ttsw_close
    mov     rcx, r15
    lea     rdx, [comma_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.ttsw_close:
    mov     rcx, r15
    lea     rdx, [rparen_str]
    call    _pyfasm_str_concat
    jmp     .ttsw_ret
.ttsw_empty:
    lea     rcx, [lparen_str]
    lea     rdx, [rparen_str]
    call    _pyfasm_str_concat
    jmp     .ttsw_ret
.ttsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.ttsw_ret:
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

_pyfasm_tuple_to_str:
    lea     rdx, [_pyfasm_auto_to_repr]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_int_to_str:
    lea     rdx, [_pyfasm_int_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_str_to_str:
    lea     rdx, [_pyfasm_str_to_repr]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_float_to_str:
    lea     rdx, [_pyfasm_float_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_tuple_list_to_str:
    lea     rdx, [_pyfasm_list_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_dict_to_str_with:
    ; RCX = dict_ptr, RDX = key_to_str(rcx)->rax, R8 = val_to_str(rcx)->rax
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

    mov     rbx, rcx
    mov     r14, rdx
    mov     r15, r8
    test    rbx, rbx
    jz      .dtsw_empty
    test    rbx, rbx
    js      .dtsw_int
    cmp     rbx, 65536
    jb      .dtsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .dtsw_int

    lea     rax, [lbrace_str]
    mov     [rsp + 40], rax
    mov     r12, [rbx]
    xor     r13, r13
    xor     edi, edi
.dtsw_loop:
    cmp     r13, r12
    jge     .dtsw_close
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .dtsw_next
    cmp     rax, -1
    je      .dtsw_next

    test    edi, edi
    jz      .dtsw_no_comma
    mov     rcx, [rsp + 40]
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     [rsp + 40], rax
.dtsw_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
    mov     rcx, [rsp + 40]
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     rcx, rax
    lea     rdx, [colon_sp_str]
    call    _pyfasm_str_concat
    mov     [rsp + 40], rax

    mov     rcx, [rsi + 16]
    call    r15
    mov     rcx, [rsp + 40]
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     [rsp + 40], rax
.dtsw_next:
    inc     r13
    jmp     .dtsw_loop

.dtsw_close:
    mov     rcx, [rsp + 40]
    lea     rdx, [rbrace_str]
    call    _pyfasm_str_concat
    jmp     .dtsw_ret
.dtsw_empty:
    lea     rcx, [lbrace_str]
    lea     rdx, [rbrace_str]
    call    _pyfasm_str_concat
    jmp     .dtsw_ret
.dtsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.dtsw_ret:
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

_pyfasm_set_to_str_with:
    ; RCX = set_ptr, RDX = elem_to_str(rcx)->rax
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 40
    and     rsp, -16

    mov     rbx, rcx
    mov     r14, rdx
    test    rbx, rbx
    jz      .stsw_empty
    test    rbx, rbx
    js      .stsw_int
    cmp     rbx, 65536
    jb      .stsw_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .stsw_int

    mov     r12, [rbx]
    cmp     r12, 256
    jb      .stsw_list_mode
    cmp     qword [rbx + 8], 0
    jle     .stsw_empty

    lea     r15, [lbrace_str]
    xor     r13, r13
    xor     edi, edi
.stsw_ht_loop:
    cmp     r13, r12
    jge     .stsw_close
    lea     rax, [r13 + r13 * 2]
    shl     rax, 3
    lea     rsi, [rbx + 16 + rax]
    mov     rax, [rsi]
    test    rax, rax
    jz      .stsw_ht_next
    cmp     rax, -1
    je      .stsw_ht_next
    test    edi, edi
    jz      .stsw_ht_no_comma
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.stsw_ht_no_comma:
    mov     edi, 1
    mov     rcx, [rsi + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
.stsw_ht_next:
    inc     r13
    jmp     .stsw_ht_loop

.stsw_list_mode:
    test    r12, r12
    jle     .stsw_empty
    lea     r15, [lbrace_str]
    xor     r13, r13
.stsw_lst_loop:
    cmp     r13, r12
    jge     .stsw_close
    test    r13, r13
    jz      .stsw_lst_elem
    mov     rcx, r15
    lea     rdx, [comma_sp_str]
    call    _pyfasm_str_concat
    mov     r15, rax
.stsw_lst_elem:
    mov     rcx, [rbx + r13 * 8 + 8]
    call    r14
    mov     rcx, r15
    mov     rdx, rax
    call    _pyfasm_str_concat
    mov     r15, rax
    inc     r13
    jmp     .stsw_lst_loop

.stsw_close:
    mov     rcx, r15
    lea     rdx, [rbrace_str]
    call    _pyfasm_str_concat
    jmp     .stsw_ret
.stsw_empty:
    lea     rax, [empty_set_str]
    jmp     .stsw_ret
.stsw_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
.stsw_ret:
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

_pyfasm_str_to_int:
    ; RCX = UTF-8 decimal string pointer or integer -> RAX = signed int64
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jnz     .sti_parse
    mov     rax, rbx
    jmp     .sti_ret

.sti_parse:
    mov     rsi, rbx
.sti_ws:
    movzx   eax, byte [rsi]
    cmp     al, ' '
    je      .sti_ws_next
    cmp     al, 9
    je      .sti_ws_next
    cmp     al, 10
    je      .sti_ws_next
    cmp     al, 13
    jne     .sti_sign
.sti_ws_next:
    inc     rsi
    jmp     .sti_ws

.sti_sign:
    xor     ebx, ebx
    cmp     byte [rsi], '-'
    jne     .sti_chk_plus
    mov     ebx, 1
    inc     rsi
    jmp     .sti_digits_init
.sti_chk_plus:
    cmp     byte [rsi], '+'
    jne     .sti_digits_init
    inc     rsi

.sti_digits_init:
    xor     eax, eax
.sti_loop:
    movzx   edx, byte [rsi]
    cmp     dl, '0'
    jb      .sti_apply_sign
    cmp     dl, '9'
    ja      .sti_apply_sign
    sub     dl, '0'
    imul    rax, rax, 10
    add     rax, rdx
    inc     rsi
    jmp     .sti_loop

.sti_apply_sign:
    test    ebx, ebx
    jz      .sti_ret
    neg     rax
.sti_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_to_float:
    ; RCX = string pointer or int64 -> RAX = IEEE-754 float64 bits
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jnz     .stf_parse
    cvtsi2sd xmm0, rbx
    movq    rax, xmm0
    jmp     .stf_ret

.stf_parse:
    mov     rsi, rbx
.stf_ws:
    movzx   eax, byte [rsi]
    cmp     al, ' '
    je      .stf_ws_next
    cmp     al, 9
    je      .stf_ws_next
    cmp     al, 10
    je      .stf_ws_next
    cmp     al, 13
    jne     .stf_sign
.stf_ws_next:
    inc     rsi
    jmp     .stf_ws

.stf_sign:
    xor     ebx, ebx
    cmp     byte [rsi], '-'
    jne     .stf_chk_plus
    mov     ebx, 1
    inc     rsi
    jmp     .stf_init
.stf_chk_plus:
    cmp     byte [rsi], '+'
    jne     .stf_init
    inc     rsi

.stf_init:
    xorpd   xmm0, xmm0
    movsd   xmm2, [flt_ten]
.stf_int_loop:
    movzx   eax, byte [rsi]
    cmp     al, '0'
    jb      .stf_chk_dot
    cmp     al, '9'
    ja      .stf_chk_dot
    sub     eax, '0'
    mulsd   xmm0, xmm2
    cvtsi2sd xmm1, eax
    addsd   xmm0, xmm1
    inc     rsi
    jmp     .stf_int_loop

.stf_chk_dot:
    cmp     byte [rsi], '.'
    jne     .stf_apply_sign
    inc     rsi
    movsd   xmm3, [flt_ten]
.stf_frac_loop:
    movzx   eax, byte [rsi]
    cmp     al, '0'
    jb      .stf_apply_sign
    cmp     al, '9'
    ja      .stf_apply_sign
    sub     eax, '0'
    cvtsi2sd xmm1, eax
    divsd   xmm1, xmm3
    addsd   xmm0, xmm1
    mulsd   xmm3, xmm2
    inc     rsi
    jmp     .stf_frac_loop

.stf_apply_sign:
    test    ebx, ebx
    jz      .stf_pack
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.stf_pack:
    movq    rax, xmm0
.stf_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_utf8_next_char:
    ; RCX = str_ptr, RDX = byte_offset
    ; Returns RAX = heap 1-char UTF-8 null-terminated str (or 0 if NUL), RDX = new byte_offset
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     r12, rdx
    test    rsi, rsi
    jz      .unc_eof
    add     rsi, r12
    movzx   eax, byte [rsi]
    test    al, al
    jz      .unc_eof

    mov     rbx, 1
    cmp     al, 0C2h
    jb      .unc_copy
    cmp     al, 0DFh
    jbe     .unc_len2
    cmp     al, 0EFh
    jbe     .unc_len3
    cmp     al, 0F4h
    jbe     .unc_len4
    jmp     .unc_copy
.unc_len2:
    mov     rbx, 2
    jmp     .unc_clamp
.unc_len3:
    mov     rbx, 3
    jmp     .unc_clamp
.unc_len4:
    mov     rbx, 4
.unc_clamp:
    mov     r13, 1
.unc_chk_loop:
    cmp     r13, rbx
    jae     .unc_copy
    cmp     byte [rsi + r13], 0
    je      .unc_trunc
    inc     r13
    jmp     .unc_chk_loop
.unc_trunc:
    mov     rbx, r13

.unc_copy:
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.unc_cp_loop:
    cmp     rcx, rbx
    jae     .unc_finish
    mov     r8b, byte [rsi + rcx]
    mov     byte [rax + rcx], r8b
    inc     rcx
    jmp     .unc_cp_loop
.unc_finish:
    mov     byte [rax + rbx], 0
    lea     rdx, [r12 + rbx]
    jmp     .unc_ret

.unc_eof:
    xor     eax, eax
    mov     rdx, r12
.unc_ret:
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_split:
    ; RCX = str_ptr, RDX = sep_ptr (0 or "" => split on ASCII whitespace runs)
    ; Returns RAX = list_ptr [count, str0, str1, ...]
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

    mov     r15, rcx                ; str_ptr
    mov     r13, rdx                ; sep_ptr
    test    r15, r15
    jnz     .ssp_alloc_list
    mov     ecx, 16
    call    _pyfasm_list_create
    jmp     .ssp_ret

.ssp_alloc_list:
    mov     rcx, r15
    call    _pyfasm_str_len
    lea     rcx, [rax + 2]
    cmp     rcx, 16
    jae     .ssp_cap_ok
    mov     ecx, 16
.ssp_cap_ok:
    call    _pyfasm_list_create
    mov     r12, rax                ; r12 = result list

    test    r13, r13
    jz      .ssp_ws_init
    cmp     byte [r13], 0
    je      .ssp_ws_init

    ; Explicit separator mode
    mov     rcx, r13
    call    _pyfasm_str_len
    mov     r14, rax                ; r14 = sep_len
    mov     rsi, r15                ; cur
    mov     rdi, r15                ; token start

.ssp_sep_loop:
    cmp     byte [rsi], 0
    je      .ssp_sep_last
    xor     ecx, ecx
.ssp_cmp_loop:
    cmp     rcx, r14
    jae     .ssp_sep_match
    mov     al, byte [rsi + rcx]
    test    al, al
    jz      .ssp_sep_nomatch
    cmp     al, byte [r13 + rcx]
    jne     .ssp_sep_nomatch
    inc     rcx
    jmp     .ssp_cmp_loop

.ssp_sep_nomatch:
    inc     rsi
    jmp     .ssp_sep_loop

.ssp_sep_match:
    mov     rbx, rsi
    sub     rbx, rdi
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ssp_sm_cp:
    cmp     rcx, rbx
    jae     .ssp_sm_nul
    mov     dl, byte [rdi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ssp_sm_cp
.ssp_sm_nul:
    mov     byte [rax + rbx], 0
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_list_append
    add     rsi, r14
    mov     rdi, rsi
    jmp     .ssp_sep_loop

.ssp_sep_last:
    mov     rbx, rsi
    sub     rbx, rdi
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ssp_sl_cp:
    cmp     rcx, rbx
    jae     .ssp_sl_nul
    mov     dl, byte [rdi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ssp_sl_cp
.ssp_sl_nul:
    mov     byte [rax + rbx], 0
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_list_append
    jmp     .ssp_done

.ssp_ws_init:
    mov     rsi, r15
.ssp_ws_skip:
    mov     al, byte [rsi]
    test    al, al
    jz      .ssp_done
    cmp     al, ' '
    je      .ssp_ws_adv
    cmp     al, 9
    je      .ssp_ws_adv
    cmp     al, 10
    je      .ssp_ws_adv
    cmp     al, 13
    jne     .ssp_ws_tok
.ssp_ws_adv:
    inc     rsi
    jmp     .ssp_ws_skip

.ssp_ws_tok:
    mov     rdi, rsi
.ssp_ws_scan:
    mov     al, byte [rsi]
    test    al, al
    jz      .ssp_ws_emit
    cmp     al, ' '
    je      .ssp_ws_emit
    cmp     al, 9
    je      .ssp_ws_emit
    cmp     al, 10
    je      .ssp_ws_emit
    cmp     al, 13
    je      .ssp_ws_emit
    inc     rsi
    jmp     .ssp_ws_scan

.ssp_ws_emit:
    mov     rbx, rsi
    sub     rbx, rdi
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.ssp_ws_cp:
    cmp     rcx, rbx
    jae     .ssp_ws_nul
    mov     dl, byte [rdi + rcx]
    mov     byte [rax + rcx], dl
    inc     rcx
    jmp     .ssp_ws_cp
.ssp_ws_nul:
    mov     byte [rax + rbx], 0
    mov     rcx, r12
    mov     rdx, rax
    call    _pyfasm_list_append
    jmp     .ssp_ws_skip

.ssp_done:
    mov     rax, r12
.ssp_ret:
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

_pyfasm_input:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16

    mov     rcx, [hStdIn]
    test    rcx, rcx
    jnz     .inp_check_console
    mov     ecx, -10                ; STD_INPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdIn], rax
    mov     rcx, rax
    lea     rdx, [consoleMode]
    call    [GetConsoleMode]
    mov     [isStdInConsole], eax
    mov     rcx, [hStdIn]

.inp_check_console:
    cmp     dword [isStdInConsole], 0
    je      .inp_read_file

    ; Interactive Windows console input via ReadConsoleW -> UTF-8
    lea     rdx, [inp_wbuf]
    mov     r8d, 2047
    lea     r9, [bytesRead]
    mov     dword [bytesRead], 0
    mov     qword [rsp + 32], 0
    call    [ReadConsoleW]
    test    eax, eax
    jz      .inp_empty
    mov     eax, dword [bytesRead]
    test    eax, eax
    jz      .inp_empty

    mov     ecx, 65001              ; CP_UTF8
    xor     edx, edx
    lea     r8, [inp_wbuf]
    mov     r9d, eax
    lea     rax, [inp_buf]
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 4095
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    call    [WideCharToMultiByte]
    test    eax, eax
    jle     .inp_empty
    mov     edi, eax
    lea     rsi, [inp_buf]
    mov     byte [rsi + rdi], 0
    jmp     .inp_strip

.inp_read_file:
    mov     rcx, [hStdIn]
    lea     rdx, [inp_buf]
    mov     r8d, 4095
    lea     r9, [bytesRead]
    mov     dword [bytesRead], 0
    mov     qword [rsp + 32], 0
    call    [ReadFile]
    test    eax, eax
    jz      .inp_empty
    mov     eax, dword [bytesRead]
    test    eax, eax
    jz      .inp_empty
    mov     edi, eax
    lea     rsi, [inp_buf]
    mov     byte [rsi + rdi], 0

.inp_strip:
    test    rdi, rdi
    jz      .inp_alloc
    movzx   eax, byte [rsi + rdi - 1]
    cmp     al, 10                  ; LF
    je      .inp_dec
    cmp     al, 13                  ; CR
    je      .inp_dec
    jmp     .inp_alloc
.inp_dec:
    dec     rdi
    mov     byte [rsi + rdi], 0
    jmp     .inp_strip

.inp_alloc:
    lea     rcx, [rdi + 1]
    mov     rbx, rdi
    call    _pyfasm_alloc
    mov     r12, rax
    mov     rdi, r12
    lea     rsi, [inp_buf]
    mov     rcx, rbx
    rep     movsb
    mov     byte [rdi], 0
    mov     rax, r12
    jmp     .inp_ret

.inp_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0

.inp_ret:
    lea     rsp, [rbp - 32]
    pop     r12
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

_pyfasm_alloc:
    ; RCX = size in bytes
    jmp     _pyfasm_alloc_memory

_pyfasm_free:
    ; RCX = pointer
    jmp     _pyfasm_free_memory



_pyfasm_str_slice:
    ; RCX = UTF-8 str pointer, RDX = lower, R8 = upper, R9 = step
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 96
    and     rsp, -16

    test    rcx, rcx
    jz      .ss_null

    mov     rsi, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     r14, r9
    test    r14, r14
    jnz     .ss_step_nz
    mov     r14, 1
.ss_step_nz:
    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     [rsp + 64], rax         ; byte_len
    test    rax, rax
    jnz     .ss_nonempty
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    jmp     .ss_exit

.ss_nonempty:
    lea     rcx, [rax * 8 + 16]
    call    _pyfasm_alloc
    mov     r15, rax                ; offsets array
    xor     edx, edx                ; byte index
    xor     ebx, ebx                ; codepoint count
    mov     r8, [rsp + 64]
.ss_scan_cp:
    cmp     rdx, r8
    jae     .ss_scan_done
    mov     al, byte [rsi + rdx]
    and     al, 0C0h
    cmp     al, 80h
    je      .ss_scan_next
    mov     [r15 + rbx * 8], rdx
    inc     rbx
.ss_scan_next:
    inc     rdx
    jmp     .ss_scan_cp
.ss_scan_done:
    mov     [r15 + rbx * 8], r8     ; sentinel byte_len

    mov     rcx, r8
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rsp + 48], rax         ; out_buf base

    cmp     r14, 0
    jl      .ss_neg_step

    ; Forward slice (r14 > 0)
    cmp     r12, 0
    jge     .ss_pos_l_ge0
    add     r12, rbx
    cmp     r12, 0
    jge     .ss_pos_l_ge0
    xor     r12, r12
.ss_pos_l_ge0:
    cmp     r12, rbx
    jle     .ss_pos_l_ok
    mov     r12, rbx
.ss_pos_l_ok:
    cmp     r13, -999999
    jne     .ss_pos_chk_u
    mov     r13, rbx
    jmp     .ss_pos_u_ok
.ss_pos_chk_u:
    cmp     r13, 0
    jge     .ss_pos_u_ge0
    add     r13, rbx
    cmp     r13, 0
    jge     .ss_pos_u_ge0
    xor     r13, r13
.ss_pos_u_ge0:
    cmp     r13, rbx
    jle     .ss_pos_u_ok
    mov     r13, rbx
.ss_pos_u_ok:
.ss_pos_loop:
    cmp     r12, r13
    jge     .ss_done_copy
    mov     r8, [r15 + r12 * 8]
    mov     r9, [r15 + r12 * 8 + 8]
    sub     r9, r8
    mov     r10, rsi
    add     r10, r8
    xor     ecx, ecx
.ss_pos_cp:
    cmp     rcx, r9
    jae     .ss_pos_cp_done
    mov     al, byte [r10 + rcx]
    mov     byte [rdi], al
    inc     rdi
    inc     rcx
    jmp     .ss_pos_cp
.ss_pos_cp_done:
    add     r12, r14
    jmp     .ss_pos_loop

.ss_neg_step:
    cmp     r12, 0
    jne     .ss_neg_norm_l
    cmp     r13, -999999
    jne     .ss_neg_norm_l
    lea     r12, [rbx - 1]
    mov     r13, -1
    jmp     .ss_neg_loop

.ss_neg_norm_l:
    cmp     r12, 0
    jge     .ss_neg_l_ge0
    add     r12, rbx
    cmp     r12, -1
    jge     .ss_neg_l_ge0
    mov     r12, -1
.ss_neg_l_ge0:
    cmp     r12, rbx
    jl      .ss_neg_l_ok
    lea     r12, [rbx - 1]
.ss_neg_l_ok:
    cmp     r13, -999999
    jne     .ss_neg_chk_u
    mov     r13, -1
    jmp     .ss_neg_loop
.ss_neg_chk_u:
    cmp     r13, 0
    jge     .ss_neg_u_ge0
    add     r13, rbx
    cmp     r13, -1
    jge     .ss_neg_u_ge0
    mov     r13, -1
.ss_neg_u_ge0:
    cmp     r13, rbx
    jl      .ss_neg_loop
    lea     r13, [rbx - 1]

.ss_neg_loop:
    cmp     r12, r13
    jle     .ss_done_copy
    cmp     r12, 0
    jl      .ss_done_copy
    mov     r8, [r15 + r12 * 8]
    mov     r9, [r15 + r12 * 8 + 8]
    sub     r9, r8
    mov     r10, rsi
    add     r10, r8
    xor     ecx, ecx
.ss_neg_cp:
    cmp     rcx, r9
    jae     .ss_neg_cp_done
    mov     al, byte [r10 + rcx]
    mov     byte [rdi], al
    inc     rdi
    inc     rcx
    jmp     .ss_neg_cp
.ss_neg_cp_done:
    add     r12, r14
    jmp     .ss_neg_loop

.ss_done_copy:
    mov     byte [rdi], 0
    mov     rax, [rsp + 48]
    jmp     .ss_exit

.ss_null:
    xor     eax, eax
.ss_exit:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_list_slice:
    ; RCX = list pointer, RDX = lower, R8 = upper, R9 = step
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16

    test    rcx, rcx
    jz      .ls_null

    mov     rsi, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     r14, r9

    mov     r15, [rsi]

    test    r14, r14
    jnz     .l_check_step
    mov     r14, 1
.l_check_step:
    cmp     r14, -1
    jne     .l_fwd_slice

    mov     rcx, r15
    inc     rcx
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rdi], r15
    mov     r10, rax

    mov     rcx, r15
    test    rcx, rcx
    jz      .l_rev_done

    lea     rbx, [rsi + r15 * 8]
    lea     rdi, [rdi + 8]
.l_rev_loop:
    mov     rax, [rbx]
    mov     [rdi], rax
    add     rdi, 8
    sub     rbx, 8
    dec     rcx
    jnz     .l_rev_loop
.l_rev_done:
    mov     rax, r10
    jmp     .ls_exit

.l_fwd_slice:
    cmp     r12, 0
    jge     .ll_pos
    add     r12, r15
    cmp     r12, 0
    jge     .ll_pos
    xor     r12, r12
.ll_pos:
    cmp     r12, r15
    jle     .ll_clamp
    mov     r12, r15
.ll_clamp:
    cmp     r13, -999999
    jne     .l_chk_u_neg
    mov     r13, r15
    jmp     .ll_u_clamp
.l_chk_u_neg:
    cmp     r13, 0
    jge     .ll_u_pos
    add     r13, r15
    cmp     r13, 0
    jge     .ll_u_pos
    xor     r13, r13
.ll_u_pos:
    cmp     r13, r15
    jle     .ll_u_clamp
    mov     r13, r15
.ll_u_clamp:
    mov     rax, r13
    sub     rax, r12
    jge     .l_sl_ok
    xor     eax, eax
.l_sl_ok:
    mov     rbx, rax

    mov     rcx, rbx
    inc     rcx
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rdi], rbx
    mov     r10, rax

    test    rbx, rbx
    jz      .l_copy_done
    lea     rsi, [rsi + r12 * 8 + 8]
    lea     rdi, [rdi + 8]
    mov     rcx, rbx
    rep     movsq
.l_copy_done:
    mov     rax, r10
    jmp     .ls_exit

.ls_null:
    xor     eax, eax
.ls_exit:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    pop     rbp
    ret

; ============================================================
; Native JSON Parser (Pure x86-64 recursive-descent)
; ============================================================
_pyfasm_json_skip_ws:
.jsw_loop:
    mov     al, [rsi]
    cmp     al, ' '
    je      .jsw_next
    cmp     al, 9                   ; \t
    je      .jsw_next
    cmp     al, 10                  ; \n
    je      .jsw_next
    cmp     al, 13                  ; \r
    je      .jsw_next
    ret
.jsw_next:
    inc     rsi
    jmp     .jsw_loop

_pyfasm_json_parse:
    ; RCX = pointer to JSON string
    ; Returns RAX = parsed dict, list, str, or int
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .jp_null
    mov     rsi, rcx
    call    _pyfasm_json_parse_val
    jmp     .jp_ret
.jp_null:
    xor     eax, eax
.jp_ret:
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_json_parse_val:
    call    _pyfasm_json_skip_ws
    mov     al, [rsi]
    test    al, al
    jz      .jpv_zero
    cmp     al, '{'
    je      _pyfasm_json_parse_obj
    cmp     al, '['
    je      _pyfasm_json_parse_arr
    cmp     al, '"'
    je      _pyfasm_json_parse_str
    cmp     al, 't'
    je      .jpv_true
    cmp     al, 'T'
    je      .jpv_true
    cmp     al, 'f'
    je      .jpv_false
    cmp     al, 'F'
    je      .jpv_false
    cmp     al, 'n'
    je      .jpv_null
    cmp     al, 'N'
    je      .jpv_null
    cmp     al, '-'
    je      _pyfasm_json_parse_num
    cmp     al, '0'
    jb      .jpv_zero
    cmp     al, '9'
    jbe     _pyfasm_json_parse_num
.jpv_zero:
    xor     eax, eax
    ret
.jpv_true:
    add     rsi, 4                  ; skip 'true'
    mov     eax, 1
    ret
.jpv_false:
    add     rsi, 5                  ; skip 'false'
    xor     eax, eax
    ret
.jpv_null:
    add     rsi, 4                  ; skip 'null'
    xor     eax, eax
    ret

_pyfasm_json_parse_num:
    xor     rax, rax
    xor     r8d, r8d                ; sign = 0
    cmp     byte [rsi], '-'
    jne     .jpn_loop
    mov     r8d, 1                  ; negative
    inc     rsi
.jpn_loop:
    movzx   ecx, byte [rsi]
    cmp     cl, '0'
    jb      .jpn_done
    cmp     cl, '9'
    ja      .jpn_done
    sub     cl, '0'
    imul    rax, 10
    add     rax, rcx
    inc     rsi
    jmp     .jpn_loop
.jpn_done:
    test    r8d, r8d
    jz      .jpn_ret
    neg     rax
.jpn_ret:
    ret

_pyfasm_json_parse_str:
    ; Expects [rsi] == '"'
    inc     rsi
    mov     rdi, rsi                ; rdi = start
.jps_scan:
    mov     al, [rsi]
    test    al, al
    jz      .jps_copy
    cmp     al, '"'
    je      .jps_copy
    cmp     al, 92                  ; backslash '\'
    jne     .jps_next
    inc     rsi
    cmp     byte [rsi], 0
    je      .jps_copy
.jps_next:
    inc     rsi
    jmp     .jps_scan
.jps_copy:
    mov     rcx, rsi
    sub     rcx, rdi                ; rcx = length in bytes
    push    rcx
    push    rdi
    inc     rcx                     ; +1 for null terminator
    call    _pyfasm_alloc
    pop     rdi
    pop     rcx
    push    rax                     ; save allocated string ptr
    mov     rdx, rax                ; dest in rdx
.jps_unescape:
    cmp     rdi, rsi
    jge     .jps_finish
    mov     al, [rdi]
    cmp     al, 92                  ; backslash
    jne     .jps_put
    inc     rdi
    cmp     rdi, rsi
    jge     .jps_finish
    mov     al, [rdi]
    cmp     al, 'n'
    jne     .jps_chk_r
    mov     al, 10
    jmp     .jps_put
.jps_chk_r:
    cmp     al, 'r'
    jne     .jps_chk_t
    mov     al, 13
    jmp     .jps_put
.jps_chk_t:
    cmp     al, 't'
    jne     .jps_put
    mov     al, 9
.jps_put:
    mov     [rdx], al
    inc     rdx
    inc     rdi
    jmp     .jps_unescape
.jps_finish:
    mov     byte [rdx], 0
    cmp     byte [rsi], '"'
    jne     .jps_ret
    inc     rsi
.jps_ret:
    pop     rax
    ret

_pyfasm_json_parse_arr:
    ; Expects [rsi] == '['
    inc     rsi
    xor     ecx, ecx                ; default capacity
    call    _pyfasm_list_create
    push    rbx
    mov     rbx, rax                ; rbx = list ptr
.jpa_loop:
    call    _pyfasm_json_skip_ws
    mov     al, [rsi]
    test    al, al
    jz      .jpa_done
    cmp     al, ']'
    je      .jpa_done
    cmp     al, ','
    jne     .jpa_val
    inc     rsi
    call    _pyfasm_json_skip_ws
.jpa_val:
    cmp     byte [rsi], ']'
    je      .jpa_done
    call    _pyfasm_json_parse_val
    mov     rdx, rax                ; value in rdx
    mov     rcx, rbx                ; list in rcx
    call    _pyfasm_list_append
    jmp     .jpa_loop
.jpa_done:
    cmp     byte [rsi], ']'
    jne     .jpa_ret
    inc     rsi
.jpa_ret:
    mov     rax, rbx
    pop     rbx
    ret

_pyfasm_json_parse_obj:
    ; Expects [rsi] == '{'
    inc     rsi
    xor     ecx, ecx                ; default capacity (16)
    call    _pyfasm_dict_create
    push    rbx
    mov     rbx, rax                ; rbx = dict ptr
.jpo_loop:
    call    _pyfasm_json_skip_ws
    mov     al, [rsi]
    test    al, al
    jz      .jpo_done
    cmp     al, '}'
    je      .jpo_done
    cmp     al, ','
    jne     .jpo_key
    inc     rsi
    call    _pyfasm_json_skip_ws
.jpo_key:
    cmp     byte [rsi], '}'
    je      .jpo_done
    cmp     byte [rsi], '"'
    jne     .jpo_done               ; invalid key
    call    _pyfasm_json_parse_str
    push    rax                     ; save key on stack
    call    _pyfasm_json_skip_ws
    cmp     byte [rsi], ':'
    jne     .jpo_err
    inc     rsi                     ; skip ':'
    call    _pyfasm_json_parse_val
    mov     r8, rax                 ; value in r8
    pop     rdx                     ; key in rdx
    mov     rcx, rbx                ; dict in rcx
    call    _pyfasm_dict_set
    jmp     .jpo_loop
.jpo_err:
    pop     rax
.jpo_done:
    cmp     byte [rsi], '}'
    jne     .jpo_ret
    inc     rsi
.jpo_ret:
    mov     rax, rbx
    pop     rbx
    ret
"""

_WIN64_NET_RUNTIME_CODE = """
_pyfasm_strip_html:
    ; RCX = pointer to input HTML string
    ; Returns RAX = pointer to stripped plain text string (_pyfasm_strip_buf)
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx

    mov     rsi, rcx
    lea     rdi, [_pyfasm_strip_buf]
    test    rsi, rsi
    jz      .done_empty

    xor     ebx, ebx                       ; ebx = in_tag flag (0 or 1)

.scan_loop:
    movzx   eax, byte [rsi]
    test    al, al
    jz      .finish_scan

    cmp     al, '<'
    je      .enter_tag

    cmp     al, '>'
    je      .exit_tag

    test    ebx, ebx
    jnz     .skip_char                     ; inside <...>, skip byte

    ; Check for HTML entity &...;
    cmp     al, '&'
    je      .check_entity

    mov     [rdi], al
    inc     rdi
    inc     rsi
    jmp     .scan_loop

.enter_tag:
    mov     ebx, 1
    inc     rsi
    jmp     .scan_loop

.exit_tag:
    xor     ebx, ebx
    inc     rsi
    jmp     .scan_loop

.skip_char:
    inc     rsi
    jmp     .scan_loop

.check_entity:
    ; Check &quot; -> "
    cmp     dword [rsi + 1], 'quot'
    jne     .check_amp
    cmp     byte [rsi + 5], ';'
    jne     .check_amp
    mov     byte [rdi], '"'
    inc     rdi
    add     rsi, 6
    jmp     .scan_loop

.check_amp:
    cmp     dword [rsi + 1], 'amp;'
    jne     .check_lt
    mov     byte [rdi], '&'
    inc     rdi
    add     rsi, 5
    jmp     .scan_loop

.check_lt:
    cmp     word [rsi + 1], 'lt'
    jne     .check_gt
    cmp     byte [rsi + 3], ';'
    jne     .check_gt
    mov     byte [rdi], '<'
    inc     rdi
    add     rsi, 4
    jmp     .scan_loop

.check_gt:
    cmp     word [rsi + 1], 'gt'
    jne     .check_apos
    cmp     byte [rsi + 3], ';'
    jne     .check_apos
    mov     byte [rdi], '>'
    inc     rdi
    add     rsi, 4
    jmp     .scan_loop

.check_apos:
    cmp     dword [rsi + 1], '#39;'
    jne     .entity_default
    mov     byte [rdi], "'"
    inc     rdi
    add     rsi, 5
    jmp     .scan_loop

.entity_default:
    mov     [rdi], al
    inc     rdi
    inc     rsi
    jmp     .scan_loop

.finish_scan:
    mov     byte [rdi], 0
    lea     rax, [_pyfasm_strip_buf]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.done_empty:
    mov     byte [_pyfasm_strip_buf], 0
    lea     rax, [_pyfasm_strip_buf]
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_http_get:
    ; RCX = pointer to URL string (e.g. "https://api.stackexchange.com/...")
    ; RDX = pointer to params dictionary (or 0)
    ; Returns RAX = pointer to _pyfasm_http_resp_obj
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx                       ; save URL in rsi
    mov     r12, rdx                       ; save params dict in r12

    ; Format URL with query parameters if params dict provided
    test    r12, r12
    jz      .use_direct_url

    ; Copy base URL to _pyfasm_http_url_buf
    lea     rdi, [_pyfasm_http_url_buf]
    mov     rcx, rsi
.copy_base_url:
    mov     al, [rcx]
    test    al, al
    jz      .base_url_copied
    mov     [rdi], al
    inc     rcx
    inc     rdi
    jmp     .copy_base_url
.base_url_copied:
    ; Check if dict has items
    mov     rax, [r12 + 8]                 ; count of items
    test    rax, rax
    jz      .url_finish
    ; Append '?'
    mov     byte [rdi], '?'
    inc     rdi

    ; Loop over dict slots: capacity = [r12]
    mov     r13, [r12]                     ; capacity
    lea     r14, [r12 + 16]                ; slot ptr
.dict_url_loop:
    test    r13, r13
    jz      .dict_url_done
    dec     r13
    mov     rax, [r14]                     ; slot hash
    test    rax, rax
    jz      .next_url_slot
    cmp     rax, -1
    je      .next_url_slot
    ; Non-empty slot: key = [r14 + 8], val = [r14 + 16]
    mov     rcx, [r14 + 8]                 ; key string
    test    rcx, rcx
    jz      .next_url_slot
.copy_key_loop:
    mov     al, [rcx]
    test    al, al
    jz      .key_copied
    mov     [rdi], al
    inc     rcx
    inc     rdi
    jmp     .copy_key_loop
.key_copied:
    mov     byte [rdi], '='
    inc     rdi
    ; Copy val: could be string (> 65536) or int
    mov     rcx, [r14 + 16]                ; val
    cmp     rcx, 65536
    jb      .copy_val_int
.copy_val_str:
    mov     al, [rcx]
    test    al, al
    jz      .val_copied
    mov     [rdi], al
    inc     rcx
    inc     rdi
    jmp     .copy_val_str
.copy_val_int:
    mov     rax, rcx
    push    r14
    push    r13
    mov     r8, rax
    test    r8, r8
    jns     .pos_val_int
    mov     byte [rdi], '-'
    inc     rdi
    neg     r8
.pos_val_int:
    mov     rax, r8
    mov     r9, 10
    lea     r10, [_pyfasm_int_buf + 30]
    mov     byte [r10], 0
.val_digit_loop:
    xor     edx, edx
    div     r9
    add     dl, '0'
    dec     r10
    mov     [r10], dl
    test    rax, rax
    jnz     .val_digit_loop
.copy_digits:
    mov     al, [r10]
    test    al, al
    jz      .digits_copied
    mov     [rdi], al
    inc     r10
    inc     rdi
    jmp     .copy_digits
.digits_copied:
    pop     r13
    pop     r14
.val_copied:
    mov     byte [rdi], '&'
    inc     rdi
.next_url_slot:
    add     r14, 24
    jmp     .dict_url_loop
.dict_url_done:
    cmp     byte [rdi - 1], '&'
    jne     .url_finish
    dec     rdi
.url_finish:
    mov     byte [rdi], 0
    lea     rsi, [_pyfasm_http_url_buf]
    jmp     .do_http_connect

.use_direct_url:
    ; rsi is already direct url

.do_http_connect:
    ; InternetOpenA
    lea     rcx, [_pyfasm_http_agent]
    mov     edx, 1                         ; INTERNET_OPEN_TYPE_DIRECT
    xor     r8, r8                         ; proxy = NULL
    xor     r9, r9                         ; proxy bypass = NULL
    mov     qword [rsp + 32], 0            ; flags = 0
    call    [InternetOpenA]
    test    rax, rax
    jz      .http_fail
    mov     rbx, rax                       ; rbx = hInternet

    ; InternetOpenUrlA
    mov     rcx, rbx
    mov     rdx, rsi                       ; lpszUrl
    xor     r8, r8                         ; headers = NULL
    xor     r9, r9                         ; headers length = 0
    mov     rax, 84000100h                 ; INTERNET_FLAG_RELOAD | INTERNET_FLAG_SECURE | INTERNET_FLAG_NO_CACHE_WRITE
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 0            ; dwContext = 0
    call    [InternetOpenUrlA]
    test    rax, rax
    jz      .http_close_session
    mov     rsi, rax                       ; rsi = hFile / hUrl

    ; InternetReadFile
    mov     rcx, rsi
    lea     rdx, [_pyfasm_http_buf]
    mov     r8d, 65535                    ; max bytes to read
    lea     r9, [_pyfasm_http_read_bytes]
    call    [InternetReadFile]

    ; Null-terminate response
    mov     eax, [_pyfasm_http_read_bytes]
    mov     byte [_pyfasm_http_buf + rax], 0

    ; Close hUrl
    mov     rcx, rsi
    call    [InternetCloseHandle]

    ; Close hInternet
    mov     rcx, rbx
    call    [InternetCloseHandle]

    ; Populate response object: [status_code, text, json, reason]
    mov     qword [_pyfasm_http_resp_obj], 200
    lea     rax, [_pyfasm_http_buf]
    mov     qword [_pyfasm_http_resp_obj + 8], rax
    mov     qword [_pyfasm_http_resp_obj + 16], 0
    lea     rax, [_pyfasm_http_ok_str]
    mov     qword [_pyfasm_http_resp_obj + 24], rax

    lea     rax, [_pyfasm_http_resp_obj]
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

.http_close_session:
    mov     rcx, rbx
    call    [InternetCloseHandle]

.http_fail:
    mov     qword [_pyfasm_http_resp_obj], 0
    mov     byte [_pyfasm_http_buf], 0
    lea     rax, [_pyfasm_http_buf]
    mov     qword [_pyfasm_http_resp_obj + 8], rax
    mov     qword [_pyfasm_http_resp_obj + 16], 0
    lea     rax, [_pyfasm_http_err_str]
    mov     qword [_pyfasm_http_resp_obj + 24], rax

    lea     rax, [_pyfasm_http_resp_obj]
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret
"""

_WIN64_CONSOLE_RUNTIME_IMPORTS = """
section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL'

    import kernel32, \\
           GetStdHandle, 'GetStdHandle', \\
           WriteFile, 'WriteFile', \\
           ReadFile, 'ReadFile', \\
           CreateFileA, 'CreateFileA', \\
           GetFileSize, 'GetFileSize', \\
           SetFilePointer, 'SetFilePointer', \\
           GetTickCount64, 'GetTickCount64', \\
           Sleep, 'Sleep', \\
           VirtualAlloc, 'VirtualAlloc', \\
           VirtualFree, 'VirtualFree', \\
           VirtualQuery, 'VirtualQuery', \\
           CreateThread, 'CreateThread', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           GetModuleHandleA, 'GetModuleHandleA', \\
           MultiByteToWideChar, 'MultiByteToWideChar', \\
           WideCharToMultiByte, 'WideCharToMultiByte', \\
           SetConsoleOutputCP, 'SetConsoleOutputCP', \\
           SetConsoleCP, 'SetConsoleCP', \\
           GetConsoleMode, 'GetConsoleMode', \\
           WriteConsoleW, 'WriteConsoleW', \\
           ReadConsoleW, 'ReadConsoleW', \\
           GetCurrentThreadId, 'GetCurrentThreadId', \\
           LoadLibraryA, 'LoadLibraryA', \\
           GetProcAddress, 'GetProcAddress', \\
           FreeLibrary, 'FreeLibrary', \\
           ExitProcess, 'ExitProcess'
"""

_WIN64_NET_RUNTIME_IMPORTS = """
section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', \\
            wininet, 'WININET.DLL'

    import kernel32, \\
           GetStdHandle, 'GetStdHandle', \\
           WriteFile, 'WriteFile', \\
           ReadFile, 'ReadFile', \\
           CreateFileA, 'CreateFileA', \\
           GetFileSize, 'GetFileSize', \\
           SetFilePointer, 'SetFilePointer', \\
           GetTickCount64, 'GetTickCount64', \\
           Sleep, 'Sleep', \\
           VirtualAlloc, 'VirtualAlloc', \\
           VirtualFree, 'VirtualFree', \\
           VirtualQuery, 'VirtualQuery', \\
           CreateThread, 'CreateThread', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           GetModuleHandleA, 'GetModuleHandleA', \\
           MultiByteToWideChar, 'MultiByteToWideChar', \\
           WideCharToMultiByte, 'WideCharToMultiByte', \\
           SetConsoleOutputCP, 'SetConsoleOutputCP', \\
           SetConsoleCP, 'SetConsoleCP', \\
           GetConsoleMode, 'GetConsoleMode', \\
           WriteConsoleW, 'WriteConsoleW', \\
           ReadConsoleW, 'ReadConsoleW', \\
           GetCurrentThreadId, 'GetCurrentThreadId', \\
           LoadLibraryA, 'LoadLibraryA', \\
           GetProcAddress, 'GetProcAddress', \\
           FreeLibrary, 'FreeLibrary', \\
           ExitProcess, 'ExitProcess'

    import wininet, \\
           InternetOpenA, 'InternetOpenA', \\
           InternetOpenUrlA, 'InternetOpenUrlA', \\
           InternetReadFile, 'InternetReadFile', \\
           InternetCloseHandle, 'InternetCloseHandle'
"""


_WIN64_FORMAT_SPEC_HELPERS_ASM = """
_pyfasm_bool_to_str:
    ; RCX = truth value -> RAX = pointer to static 'True' / 'False'
    lea     rax, [_pyfasm_false_text]
    test    rcx, rcx
    jz      .bts_done
    lea     rax, [_pyfasm_true_text]
.bts_done:
    ret

_pyfasm_print_bool:
    ; RCX = truth value
    lea     rax, [_pyfasm_false_text]
    test    rcx, rcx
    jz      .pb_print
    lea     rax, [_pyfasm_true_text]
.pb_print:
    mov     rcx, rax
    jmp     _pyfasm_print_str

_pyfasm_true_text   db 'True', 0
_pyfasm_false_text  db 'False', 0

_pyfasm_print_list_bool:
    lea     rdx, [_pyfasm_print_bool]
    jmp     _pyfasm_print_list_with

_pyfasm_print_tuple_bool:
    lea     rdx, [_pyfasm_print_bool]
    jmp     _pyfasm_print_tuple_with

_pyfasm_list_bool_to_str:
    lea     rdx, [_pyfasm_bool_to_str]
    jmp     _pyfasm_list_to_str_with

_pyfasm_tuple_bool_to_str:
    lea     rdx, [_pyfasm_bool_to_str]
    jmp     _pyfasm_tuple_to_str_with

_pyfasm_int_to_base:
    ; RCX = value (int64), RDX = base (2..16), R8 = uppercase (0/1) -> RAX = heap str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 128
    and     rsp, -16

    cmp     rdx, 2
    jl      .itb_base10
    cmp     rdx, 16
    jle     .itb_base_ok
.itb_base10:
    mov     edx, 10
.itb_base_ok:
    mov     rbx, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     qword [rsp + 112], 0
    test    rbx, rbx
    jns     .itb_abs
    mov     qword [rsp + 112], 1
    neg     rbx
.itb_abs:
    lea     rdi, [rsp + 110]
    test    rbx, rbx
    jnz     .itb_div_loop
    mov     byte [rdi], '0'
    dec     rdi
    jmp     .itb_sign
.itb_div_loop:
    test    rbx, rbx
    jz      .itb_sign
    mov     rax, rbx
    xor     edx, edx
    div     r12
    mov     rbx, rax
    cmp     dl, 10
    jl      .itb_digit
    sub     dl, 10
    test    r13, r13
    jnz     .itb_upper
    add     dl, 'a'
    jmp     .itb_store
.itb_upper:
    add     dl, 'A'
    jmp     .itb_store
.itb_digit:
    add     dl, '0'
.itb_store:
    mov     byte [rdi], dl
    dec     rdi
    jmp     .itb_div_loop
.itb_sign:
    cmp     qword [rsp + 112], 0
    je      .itb_alloc
    mov     byte [rdi], '-'
    dec     rdi
.itb_alloc:
    inc     rdi
    lea     rsi, [rsp + 111]
    mov     r12, rsi
    sub     r12, rdi
    mov     rsi, rdi
    lea     rcx, [r12 + 1]
    call    _pyfasm_alloc
    xor     ecx, ecx
.itb_cpy:
    cmp     rcx, r12
    jge     .itb_nul
    mov     dl, [rsi + rcx]
    mov     [rax + rcx], dl
    inc     rcx
    jmp     .itb_cpy
.itb_nul:
    mov     byte [rax + rcx], 0
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_pad_left:
    ; RCX = str_ptr, RDX = min_width (int64), R8 = pad_char (byte) -> RAX = heap str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    mov     r12, rdx
    mov     r13, r8
    xor     esi, esi
    test    rbx, rbx
    jz      .spl_len_ok
    mov     rcx, rbx
    call    _pyfasm_str_len
    mov     rsi, rax
.spl_len_ok:
    cmp     rsi, r12
    jl      .spl_need_pad
    test    rbx, rbx
    jz      .spl_empty_alloc
    mov     rax, rbx
    jmp     .spl_ret
.spl_empty_alloc:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    jmp     .spl_ret
.spl_need_pad:
    mov     rcx, r12
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     [rsp + 32], rax
    mov     rcx, r12
    sub     rcx, rsi
    mov     rdx, rbx
    cmp     r13b, '0'
    jne     .spl_write_pad
    test    rsi, rsi
    jz      .spl_write_pad
    mov     al, [rdx]
    cmp     al, '-'
    je      .spl_copy_sign
    cmp     al, '+'
    jne     .spl_write_pad
.spl_copy_sign:
    mov     [rdi], al
    inc     rdi
    inc     rdx
    dec     rsi
.spl_write_pad:
    test    rcx, rcx
    jle     .spl_copy_rest
    mov     [rdi], r13b
    inc     rdi
    dec     rcx
    jmp     .spl_write_pad
.spl_copy_rest:
    test    rsi, rsi
    jle     .spl_finish
    mov     al, [rdx]
    mov     [rdi], al
    inc     rdx
    inc     rdi
    dec     rsi
    jmp     .spl_copy_rest
.spl_finish:
    mov     byte [rdi], 0
    mov     rax, [rsp + 32]
.spl_ret:
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_float_to_str_prec:
    ; XMM0 = double val, RDX = precision (int64) -> RAX = heap str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 144
    and     rsp, -16

    movq    [rsp + 120], xmm0
    mov     r12, rdx
    test    r12, r12
    jns     .fp_p_max
    xor     r12d, r12d
.fp_p_max:
    cmp     r12, 12
    jle     .fp_p_ok
    mov     r12, 12
.fp_p_ok:
    movq    rax, xmm0
    xor     r14d, r14d
    bt      rax, 63
    jnc     .fp_pos
    mov     r14d, 1
    btr     rax, 63
.fp_pos:
    mov     rcx, rax
    shr     rcx, 52
    cmp     rcx, 1072
    jae     .fp_fallback
    mov     r13, 1
    mov     rcx, r12
.fp_pow_loop:
    test    rcx, rcx
    jz      .fp_pow_done
    imul    r13, r13, 10
    dec     rcx
    jmp     .fp_pow_loop
.fp_pow_done:
    movq    xmm0, rax
    cvtsi2sd xmm1, r13
    mulsd   xmm0, xmm1
    movq    rax, xmm0
    mov     rcx, rax
    shr     rcx, 52
    cmp     rcx, 1085
    jae     .fp_fallback
    mov     rax, 3FE0000000000000h
    movq    xmm2, rax
    addsd   xmm0, xmm2
    movq    rax, xmm0
    mov     rcx, rax
    shr     rcx, 52
    cmp     rcx, 1085
    jae     .fp_fallback
    cvttsd2si rbx, xmm0

    mov     rax, rbx
    xor     edx, edx
    div     r13
    mov     rbx, rax            ; int_part
    mov     rsi, rdx            ; frac_part

    lea     rdi, [rsp + 110]
    test    r12, r12
    jz      .fp_int_part
    mov     rcx, r12
    mov     r8d, 10
.fp_frac_loop:
    mov     rax, rsi
    xor     edx, edx
    div     r8
    mov     rsi, rax
    add     dl, '0'
    mov     [rdi], dl
    dec     rdi
    dec     rcx
    jnz     .fp_frac_loop
    mov     byte [rdi], '.'
    dec     rdi
.fp_int_part:
    test    rbx, rbx
    jnz     .fp_int_loop
    mov     byte [rdi], '0'
    dec     rdi
    jmp     .fp_sign
.fp_int_loop:
    test    rbx, rbx
    jz      .fp_sign
    mov     rax, rbx
    xor     edx, edx
    mov     r8d, 10
    div     r8
    mov     rbx, rax
    add     dl, '0'
    mov     [rdi], dl
    dec     rdi
    jmp     .fp_int_loop
.fp_sign:
    test    r14d, r14d
    jz      .fp_alloc
    mov     byte [rdi], '-'
    dec     rdi
.fp_alloc:
    inc     rdi
    lea     rcx, [rsp + 111]
    sub     rcx, rdi
    mov     r12, rcx
    mov     rsi, rdi
    inc     rcx
    call    _pyfasm_alloc
    xor     ecx, ecx
.fp_cpy:
    cmp     rcx, r12
    jge     .fp_nul
    mov     dl, [rsi + rcx]
    mov     [rax + rcx], dl
    inc     rcx
    jmp     .fp_cpy
.fp_nul:
    mov     byte [rax + rcx], 0
    jmp     .fp_ret
.fp_fallback:
    movq    xmm0, [rsp + 120]
    call    _pyfasm_float_to_str
.fp_ret:
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
"""

_WIN64_GUI_EXTRA_HELPERS_ASM = """
_pyfasm_register_control_callback:
    ; RCX = hwnd, RDX = callback ptr
    push    rbp
    mov     rbp, rsp
    test    rcx, rcx
    jz      .rcc_done
    mov     r9, [_pyfasm_ctrl_count]
    xor     r8d, r8d
.rcc_loop:
    cmp     r8, r9
    jge     .rcc_done
    cmp     [_pyfasm_ctrl_hwnds + r8*8], rcx
    jne     .rcc_next
    mov     [_pyfasm_ctrl_callbacks + r8*8], rdx
    jmp     .rcc_done
.rcc_next:
    inc     r8
    jmp     .rcc_loop
.rcc_done:
    xor     eax, eax
    pop     rbp
    ret

_pyfasm_checkbox_get:
    ; RCX = hwnd -> RAX = 1 if checked else 0
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .cbg_ok
    xor     eax, eax
    jmp     .cbg_ret
.cbg_ok:
    mov     edx, 00F0h          ; BM_GETCHECK
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    cmp     eax, 1
    sete    al
    movzx   eax, al
.cbg_ret:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_checkbox_set:
    ; RCX = hwnd, RDX = checked (bool)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .cbs_ret
    xor     r8d, r8d
    test    rdx, rdx
    setne   r8b
    mov     edx, 00F1h          ; BM_SETCHECK
    xor     r9d, r9d
    call    [SendMessageW]
.cbs_ret:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_resize_window:
    ; RCX = width, RDX = height
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    mov     r8, [_pyfasm_h_wnd]
    test    r8, r8
    jz      .rw_ret
    mov     [rsp + 32], rcx
    mov     [rsp + 40], rdx
    mov     qword [rsp + 48], 6 ; SWP_NOMOVE | SWP_NOZORDER
    mov     rcx, r8
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SetWindowPos]
.rw_ret:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_show_window:
    ; RCX = hwnd (or 0 -> [_pyfasm_h_wnd])
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .sw_ok
    mov     rcx, [_pyfasm_h_wnd]
.sw_ok:
    mov     rbx, rcx
    test    rbx, rbx
    jz      .sw_ret
    mov     rcx, rbx
    mov     edx, 5              ; SW_SHOW
    call    [ShowWindow]
    mov     rcx, rbx
    call    [UpdateWindow]
.sw_ret:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_destroy_window:
    ; RCX = hwnd (or 0 -> [_pyfasm_h_wnd])
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .dw_ok
    mov     rcx, [_pyfasm_h_wnd]
.dw_ok:
    test    rcx, rcx
    jz      .dw_ret
    call    [DestroyWindow]
.dw_ret:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_window_close_cb:
    ; Callback form of root.destroy / app.quit / window.close (timer or button command):
    ; destroys the main window, which posts WM_QUIT and ends the event loop.
    xor     ecx, ecx
    jmp     _pyfasm_destroy_window

_pyfasm_canvas_set_color:
    ; RCX = COLORREF (0x00BBGGRR or -1 for default)
    mov     dword [_pyfasm_canvas_color], ecx
    xor     eax, eax
    ret

_pyfasm_is_stringvar:
    ; RCX = candidate pointer -> RAX = 1 if valid heap StringVar ('PYFSVAR!'), else 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16
    mov     rsi, rcx
    test    rsi, rsi
    jz      .isv_no
    cmp     rsi, 65536
    jb      .isv_no
    mov     rax, 00007FFFFFFF0000h
    cmp     rsi, rax
    jae     .isv_no
    mov     rcx, rsi
    lea     rdx, [rsp + 32]
    mov     r8d, 48
    call    [VirtualQuery]
    test    rax, rax
    jz      .isv_no
    cmp     dword [rsp + 64], 1000h     ; MEM_COMMIT
    jne     .isv_no
    mov     eax, dword [rsp + 68]
    test    eax, 100h
    jnz     .isv_no
    test    eax, 0EEh
    jz      .isv_no
    mov     rax, [rsp + 32]
    add     rax, [rsp + 56]
    sub     rax, rsi
    cmp     rax, 16
    jb      .isv_no
    mov     rax, 5059465356415221h      ; 'PYFSVAR!'
    cmp     qword [rsi], rax
    jne     .isv_no
    mov     eax, 1
    jmp     .isv_ret
.isv_no:
    xor     eax, eax
.isv_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_is_list:
    ; RCX = candidate pointer -> RAX = 1 if readable valid PyFASM list/tuple [len, ...], else 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16
    mov     rsi, rcx
    test    rsi, rsi
    jz      .isl_no
    test    rsi, 7
    jnz     .isl_no
    cmp     rsi, 65536
    jb      .isl_no
    mov     rax, 00007FFFFFFF0000h
    cmp     rsi, rax
    jae     .isl_no
    mov     rcx, rsi
    lea     rdx, [rsp + 32]
    mov     r8d, 48
    call    [VirtualQuery]
    test    rax, rax
    jz      .isl_no
    cmp     dword [rsp + 64], 1000h     ; MEM_COMMIT
    jne     .isl_no
    mov     eax, dword [rsp + 68]
    test    eax, 100h
    jnz     .isl_no
    test    eax, 0EEh
    jz      .isl_no
    mov     rax, [rsp + 32]
    add     rax, [rsp + 56]
    sub     rax, rsi
    cmp     rax, 16
    jb      .isl_no
    mov     rbx, qword [rsi]
    cmp     rbx, 0
    jl      .isl_no
    cmp     rbx, 65536
    ja      .isl_no
    cmp     rbx, 256
    jb      .isl_yes
    mov     rcx, rsi
    call    _pyfasm_is_utf8_str_ptr
    test    eax, eax
    jnz     .isl_no
.isl_yes:
    mov     eax, 1
    jmp     .isl_ret
.isl_no:
    xor     eax, eax
.isl_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_combobox_add:
    ; RCX = hwnd, RDX = item text OR list/tuple of texts
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .cba_h
    mov     rcx, [_pyfasm_last_combo_hwnd]
.cba_h:
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .cba_done
    test    rsi, rsi
    jz      .cba_done
    mov     rcx, rsi
    call    _pyfasm_is_list
    test    eax, eax
    jz      .cba_single
    mov     rdi, [rsi]
    xor     r12d, r12d
.cba_loop:
    cmp     r12, rdi
    jge     .cba_sel0
    mov     rcx, [rsi + r12*8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
    mov     rcx, rbx
    mov     edx, 143h           ; CB_ADDSTRING
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    inc     r12
    jmp     .cba_loop
.cba_single:
    mov     rcx, rsi
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
    mov     rcx, rbx
    mov     edx, 143h
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
.cba_sel0:
    mov     rcx, rbx
    mov     edx, 147h           ; CB_GETCURSEL
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    cmp     eax, 0
    jge     .cba_done
    mov     rcx, rbx
    mov     edx, 14Eh           ; CB_SETCURSEL
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
.cba_done:
    xor     eax, eax
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_wide_to_utf8:
    ; RCX = wide_src -> RAX = heap null-terminated UTF-8 string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16
    mov     rsi, rcx
    test    rsi, rsi
    jz      .w2u_empty
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     ecx, 65001                  ; CP_UTF8
    xor     edx, edx
    mov     r8, rsi
    mov     r9d, -1
    call    [WideCharToMultiByte]
    mov     rbx, rax
    test    rbx, rbx
    jle     .w2u_empty
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    mov     [rsp + 64], rax
    mov     [rsp + 32], rax
    mov     [rsp + 40], rbx
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     ecx, 65001
    xor     edx, edx
    mov     r8, rsi
    mov     r9d, -1
    call    [WideCharToMultiByte]
    mov     rax, [rsp + 64]
    jmp     .w2u_ret
.w2u_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.w2u_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_stringvar_create:
    ; RCX = initial value ptr (or 0) -> RAX = StringVar ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jnz     .svc_has
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    mov     rbx, rax
.svc_has:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     rdx, 5059465356415221h
    mov     [rax], rdx
    mov     [rax + 8], rbx
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_fire_sv_traces:
    ; RCX = sv_ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, [_pyfasm_sv_trace_cnt]
    xor     edi, edi
.fst_loop:
    cmp     rdi, rsi
    jge     .fst_done
    imul    rax, rdi, 24
    lea     rdx, [_pyfasm_sv_traces + rax]
    cmp     [rdx + 0], rbx
    jne     .fst_next
    mov     rcx, [rdx + 8]
    test    rcx, rcx
    jz      .fst_next
    mov     rdx, 8000000000000001h
    call    _pyfasm_invoke_cb
.fst_next:
    inc     rdi
    jmp     .fst_loop
.fst_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_unified_get:
    ; RCX = StringVar or HWND -> RAX = value
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jnz     .ug_chk
    mov     rbx, [_pyfasm_last_edit_hwnd]
.ug_chk:
    mov     rcx, rbx
    call    _pyfasm_is_stringvar
    test    eax, eax
    jz      .ug_hwnd
    mov     rax, [rbx + 8]
    jmp     .ug_ret
.ug_hwnd:
    test    rbx, rbx
    jz      .ug_empty
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .ug_text
    shl     rax, 6
    mov     ecx, dword [_pyfasm_layout_table + rax + 16]
    cmp     ecx, 4
    jne     .ug_chk_combo
    mov     rcx, rbx
    call    _pyfasm_checkbox_get
    jmp     .ug_ret
.ug_chk_combo:
    cmp     ecx, 9
    jne     .ug_chk_slider
    mov     rcx, rbx
    mov     edx, 147h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    cmp     eax, 0
    jl      .ug_empty
    mov     rcx, rbx
    mov     edx, 148h
    mov     r8d, eax
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    lea     rcx, [_pyfasm_wide_buf]
    call    _pyfasm_wide_to_utf8
    jmp     .ug_ret
.ug_chk_slider:
    cmp     ecx, 10
    jne     .ug_text
    mov     rsi, qword [_pyfasm_widget_aux + rax + 48]
    mov     rcx, rbx
    mov     edx, 400h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    cvtsi2sd xmm0, eax
    mov     eax, 1000
    cvtsi2sd xmm1, rax
    divsd   xmm0, xmm1
    test    rsi, rsi
    jz      .ug_sl_ret
    movsd   xmm1, [rsi + 16]
    subsd   xmm1, [rsi + 8]
    mulsd   xmm0, xmm1
    addsd   xmm0, [rsi + 8]
.ug_sl_ret:
    movq    rax, xmm0
    jmp     .ug_ret
.ug_text:
    mov     rcx, rbx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 1024
    call    [GetWindowTextW]
    lea     rcx, [_pyfasm_wide_buf]
    call    _pyfasm_wide_to_utf8
    jmp     .ug_ret
.ug_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.ug_ret:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_unified_set:
    ; RCX = StringVar or HWND, RDX = value
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jnz     .us_chk
    mov     rbx, [_pyfasm_last_label_hwnd]
.us_chk:
    mov     rcx, rbx
    call    _pyfasm_is_stringvar
    test    eax, eax
    jz      .us_hwnd
    test    rsi, rsi
    jnz     .us_sv_store
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    mov     rsi, rax
.us_sv_store:
    mov     [rbx + 8], rsi
    mov     dword [_pyfasm_sv_updating], 1
    mov     rdi, [_pyfasm_layout_count]
    xor     ecx, ecx
.us_sync_loop:
    cmp     rcx, rdi
    jge     .us_sync_done
    mov     rax, rcx
    shl     rax, 6
    cmp     qword [_pyfasm_widget_aux + rax + 40], rbx
    jne     .us_sync_next
    push    rcx
    mov     rcx, qword [_pyfasm_layout_table + rax + 0]
    mov     rdx, rsi
    call    _pyfasm_set_text
    pop     rcx
.us_sync_next:
    inc     rcx
    jmp     .us_sync_loop
.us_sync_done:
    mov     rcx, rbx
    call    _pyfasm_fire_sv_traces
    mov     dword [_pyfasm_sv_updating], 0
    xor     eax, eax
    jmp     .us_ret

.us_hwnd:
    test    rbx, rbx
    jz      .us_ret
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .us_plain_txt
    shl     rax, 6
    mov     ecx, dword [_pyfasm_layout_table + rax + 16]
    cmp     ecx, 11
    jne     .us_chk_sl
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_progressbar_set
    jmp     .us_ret
.us_chk_sl:
    cmp     ecx, 10
    jne     .us_plain_txt
    mov     rdi, qword [_pyfasm_widget_aux + rax + 48]
    mov     rax, 7FFFFFFFFFFFh
    cmp     rsi, rax
    ja      .us_sl_f64
    cvtsi2sd xmm0, rsi
    jmp     .us_sl_map
.us_sl_f64:
    movq    xmm0, rsi
.us_sl_map:
    test    rdi, rdi
    jz      .us_sl_send
    movsd   xmm1, [rdi + 16]
    subsd   xmm1, [rdi + 8]
    xorpd   xmm2, xmm2
    ucomisd xmm1, xmm2
    jbe     .us_sl_send
    subsd   xmm0, [rdi + 8]
    divsd   xmm0, xmm1
    mov     eax, 1000
    cvtsi2sd xmm1, rax
    mulsd   xmm0, xmm1
.us_sl_send:
    cvttsd2si r9d, xmm0
    mov     rcx, rbx
    mov     edx, 405h
    mov     r8d, 1
    call    [SendMessageW]
    jmp     .us_ret
.us_plain_txt:
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_set_text
.us_ret:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_canvas_clear:
    ; RCX = hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16
    test    rcx, rcx
    jnz     .cc_h_ok
    mov     rcx, [_pyfasm_h_wnd]
.cc_h_ok:
    mov     rbx, rcx
    test    rbx, rbx
    jz      .cc_ret
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .cc_inv
    shl     rax, 6
    mov     rsi, qword [_pyfasm_widget_aux + rax + 48]
    test    rsi, rsi
    jz      .cc_inv
    mov     rax, 50594643414E5621h
    cmp     [rsi], rax
    jne     .cc_inv
    mov     qword [rsi + 8], 0
.cc_inv:
    mov     rcx, rbx
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]
.cc_ret:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_find_widget_slot:
    ; RCX = hwnd -> RAX = 0..255 or -1
    test    rcx, rcx
    jz      .fws_nf
    mov     r8, [_pyfasm_layout_count]
    xor     eax, eax
.fws_loop:
    cmp     rax, r8
    jge     .fws_nf
    mov     rdx, rax
    shl     rdx, 6
    cmp     qword [_pyfasm_layout_table + rdx], rcx
    je      .fws_ret
    inc     rax
    jmp     .fws_loop
.fws_nf:
    mov     rax, -1
.fws_ret:
    ret

_pyfasm_resolve_packed_color:
    ; RCX = packed64 -> RAX = 0x00BBGGRR, -2 (transparent), or -1 (unset)
    test    rcx, rcx
    jz      .rpc_unset
    mov     rax, rcx
    bt      rax, 63
    jnc     .rpc_unset
    cmp     dword [_pyfasm_dark_mode_val], 0
    je      .rpc_use_half
    shr     rax, 32
.rpc_use_half:
    test    eax, 40000000h
    jnz     .rpc_transp
    test    eax, 01000000h
    jz      .rpc_unset
    and     eax, 00FFFFFFh
    ret
.rpc_transp:
    mov     rax, -2
    ret
.rpc_unset:
    mov     rax, -1
    ret

_pyfasm_parse_hex_nibble:
    cmp     al, '0'
    jb      .phn_bad
    cmp     al, '9'
    ja      .phn_af
    sub     al, '0'
    movzx   eax, al
    ret
.phn_af:
    or      al, 20h
    cmp     al, 'a'
    jb      .phn_bad
    cmp     al, 'f'
    ja      .phn_bad
    sub     al, 'a' - 10
    movzx   eax, al
    ret
.phn_bad:
    mov     eax, -1
    ret

_pyfasm_parse_color_one32:
    ; RCX = str_ptr -> EAX = 0x40000000 (transp), 0x01BBGGRR, or 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    test    rsi, rsi
    jz      .pco_zero
.pco_ws:
    movzx   eax, byte [rsi]
    cmp     al, ' '
    je      .pco_ws_n
    cmp     al, 9
    je      .pco_ws_n
    jmp     .pco_chk
.pco_ws_n:
    inc     rsi
    jmp     .pco_ws
.pco_chk:
    test    al, al
    jz      .pco_zero
    cmp     al, '#'
    jne     .pco_named
    inc     rsi
    mov     rcx, rsi
    call    _pyfasm_str_len
    cmp     rax, 6
    jge     .pco_hex6
    cmp     rax, 3
    jne     .pco_zero
    mov     al, [rsi + 0]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    imul    ebx, eax, 17
    mov     al, [rsi + 1]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    imul    ecx, eax, 17
    shl     ecx, 8
    or      ebx, ecx
    mov     al, [rsi + 2]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    imul    edx, eax, 17
    shl     edx, 16
    mov     eax, ebx
    or      eax, edx
    or      eax, 01000000h
    jmp     .pco_done
.pco_hex6:
    mov     al, [rsi + 0]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    shl     eax, 4
    mov     ebx, eax
    mov     al, [rsi + 1]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    or      ebx, eax
    mov     al, [rsi + 2]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    shl     eax, 4
    mov     ecx, eax
    mov     al, [rsi + 3]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    or      ecx, eax
    shl     ecx, 8
    or      ebx, ecx
    mov     al, [rsi + 4]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    shl     eax, 4
    mov     ecx, eax
    mov     al, [rsi + 5]
    call    _pyfasm_parse_hex_nibble
    cmp     eax, 0
    jl      .pco_zero
    or      ecx, eax
    shl     ecx, 16
    mov     eax, ebx
    or      eax, ecx
    or      eax, 01000000h
    jmp     .pco_done

.pco_named:
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    xor     ecx, ecx
.pco_lc:
    cmp     ecx, 15
    jge     .pco_match
    mov     al, [rsi + rcx]
    test    al, al
    jz      .pco_match
    cmp     al, ' '
    je      .pco_match
    cmp     al, 'A'
    jb      .pco_lcs
    cmp     al, 'Z'
    ja      .pco_lcs
    add     al, 32
.pco_lcs:
    mov     [rsp + 32 + rcx], al
    inc     ecx
    jmp     .pco_lc
.pco_match:
    mov     eax, [rsp + 32]
    cmp     eax, 6E617274h
    jne     .pco_white
    mov     eax, 40000000h
    jmp     .pco_done
.pco_white:
    cmp     eax, 74696877h
    jne     .pco_black
    mov     eax, 01FFFFFFh
    jmp     .pco_done
.pco_black:
    cmp     eax, 63616C62h
    jne     .pco_red
    mov     eax, 01000000h
    jmp     .pco_done
.pco_red:
    cmp     eax, 00646572h
    jne     .pco_green
    mov     eax, 012626DCh
    jmp     .pco_done
.pco_green:
    cmp     eax, 65657267h
    jne     .pco_blue
    mov     eax, 014AA316h
    jmp     .pco_done
.pco_blue:
    cmp     eax, 65756C62h
    jne     .pco_gray
    mov     eax, 01EB6325h
    jmp     .pco_done
.pco_gray:
    cmp     eax, 79617267h
    je      .pco_is_gray
    cmp     eax, 79657267h
    jne     .pco_orange
.pco_is_gray:
    mov     eax, 01808080h
    jmp     .pco_done
.pco_orange:
    cmp     eax, 6E61726Fh
    jne     .pco_yellow
    mov     eax, 010C58EAh
    jmp     .pco_done
.pco_yellow:
    cmp     eax, 6C6C6579h
    jne     .pco_cyan
    mov     eax, 0108B3EAh
    jmp     .pco_done
.pco_cyan:
    cmp     eax, 6E617963h
    jne     .pco_purple
    mov     eax, 01D4B606h
    jmp     .pco_done
.pco_purple:
    cmp     eax, 70727570h
    jne     .pco_pink
    mov     eax, 01EA3393h
    jmp     .pco_done
.pco_pink:
    cmp     eax, 6B6E6970h
    jne     .pco_navy
    mov     eax, 019948ECh
    jmp     .pco_done
.pco_navy:
    cmp     eax, 7976616Eh
    jne     .pco_teal
    mov     eax, 01800000h
    jmp     .pco_done
.pco_teal:
    cmp     eax, 6C616574h
    jne     .pco_gold
    mov     eax, 01808000h
    jmp     .pco_done
.pco_gold:
    cmp     eax, 646C6F67h
    jne     .pco_silver
    mov     eax, 0100D7FFh
    jmp     .pco_done
.pco_silver:
    cmp     eax, 766C6973h
    jne     .pco_dark
    mov     eax, 01C0C0C0h
    jmp     .pco_done
.pco_dark:
    cmp     eax, 6B726164h
    jne     .pco_light
    mov     eax, 01404040h
    cmp     byte [rsp + 36], 'b'
    jne     .pco_d_g
    mov     eax, 018B0000h
    jmp     .pco_done
.pco_d_g:
    cmp     byte [rsp + 36], 'r'
    jne     .pco_done
    mov     eax, 0100008Bh
    jmp     .pco_done
.pco_light:
    cmp     eax, 6867696Ch
    jne     .pco_zero
    mov     eax, 01D3D3D3h
    jmp     .pco_done
.pco_zero:
    xor     eax, eax
.pco_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_parse_color:
    ; RCX = str_ptr, tuple/list [light, dark], or packed64 -> RAX = packed64
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16

    test    rcx, rcx
    jz      .pc_zero
    mov     rax, rcx
    bt      rax, 63
    jc      .pc_done

    mov     rbx, rcx
    call    _pyfasm_is_list
    test    eax, eax
    jz      .pc_str
    cmp     qword [rbx], 2
    jl      .pc_list1
    mov     rcx, [rbx + 8]
    call    _pyfasm_parse_color_one32
    mov     esi, eax
    mov     rcx, [rbx + 16]
    call    _pyfasm_parse_color_one32
    shl     rax, 32
    or      rax, rsi
    mov     rdx, 8000000000000000h
    or      rax, rdx
    jmp     .pc_done
.pc_list1:
    cmp     qword [rbx], 1
    jl      .pc_zero
    mov     rbx, [rbx + 8]
.pc_str:
    mov     rcx, rbx
    call    _pyfasm_parse_color_one32
    test    eax, eax
    jz      .pc_zero
    mov     edx, eax
    shl     rdx, 32
    or      rax, rdx
    mov     rdx, 8000000000000000h
    or      rax, rdx
    jmp     .pc_done
.pc_zero:
    xor     eax, eax
.pc_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_set_colors:
    ; RCX = hwnd, RDX = fg_p64 (or 0), R8 = tc_p64 (or 0)
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
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .wsc_done
    shl     rax, 6
    lea     r12, [_pyfasm_widget_aux + rax]

    test    rsi, rsi
    jz      .wsc_tc
    bt      rsi, 63
    jc      .wsc_fg_pk
    mov     rcx, rsi
    call    _pyfasm_parse_color
    mov     rsi, rax
    test    rsi, rsi
    jz      .wsc_tc
.wsc_fg_pk:
    mov     [r12 + 16], rsi
    mov     rcx, rsi
    call    _pyfasm_resolve_packed_color
    mov     dword [r12 + 8], eax
    mov     rcx, [r12 + 0]
    test    rcx, rcx
    jz      .wsc_new_br
    call    [DeleteObject]
    mov     qword [r12 + 0], 0
.wsc_new_br:
    mov     ecx, [r12 + 8]
    cmp     ecx, 0
    jl      .wsc_tc
    call    [CreateSolidBrush]
    mov     [r12 + 0], rax

.wsc_tc:
    test    rdi, rdi
    jz      .wsc_inv
    bt      rdi, 63
    jc      .wsc_tc_pk
    mov     rcx, rdi
    call    _pyfasm_parse_color
    mov     rdi, rax
    test    rdi, rdi
    jz      .wsc_inv
.wsc_tc_pk:
    mov     [r12 + 24], rdi
    mov     rcx, rdi
    call    _pyfasm_resolve_packed_color
    mov     dword [r12 + 12], eax

.wsc_inv:
    mov     rcx, rbx
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]
.wsc_done:
    xor     eax, eax
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_font:
    ; RCX = family str_ptr (or 0), RDX = size_pt, R8 = bold, R9 = italic -> RAX = HFONT
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 160
    and     rsp, -16

    mov     rsi, rcx
    mov     ebx, r8d
    mov     [rsp + 116], r9d

    mov     eax, edx
    cmp     eax, 4
    jge     .cfnt_sz
    mov     eax, 13
.cfnt_sz:
    imul    eax, 4
    cdq
    mov     ecx, 3
    idiv    ecx
    neg     eax
    mov     [rsp + 112], eax

    test    rsi, rsi
    jz      .cfnt_def_fam
    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 64
    call    _pyfasm_utf8_to_wide
    lea     rax, [_pyfasm_wide_buf]
    jmp     .cfnt_fam_ok
.cfnt_def_fam:
    lea     rax, [wszSegoeUI]
.cfnt_fam_ok:
    mov     [rsp + 120], rax

    movsxd  rcx, dword [rsp + 112]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     eax, 400
    test    ebx, ebx
    jz      .cfnt_wt_ok
    mov     eax, 700
.cfnt_wt_ok:
    mov     [rsp + 32], rax
    mov     eax, [rsp + 116]
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5
    mov     qword [rsp + 96], 0
    mov     rax, [rsp + 120]
    mov     [rsp + 104], rax
    call    [CreateFontW]

    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_set_font:
    ; RCX = hwnd, RDX = HFONT
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .wsf_done
    test    rsi, rsi
    jz      .wsf_done
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .wsf_send
    shl     rax, 6
    mov     qword [_pyfasm_widget_aux + rax + 32], rsi
.wsf_send:
    mov     rcx, rbx
    mov     edx, 30h
    mov     r8, rsi
    mov     r9d, 1
    call    [SendMessageW]
.wsf_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_stringvar_bind:
    ; RCX = sv_ptr, RDX = hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .svb_done
    test    rsi, rsi
    jz      .svb_done
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .svb_done
    shl     rax, 6
    mov     qword [_pyfasm_widget_aux + rax + 40], rbx
    mov     rdx, [rbx + 8]
    test    rdx, rdx
    jz      .svb_done
    mov     dword [_pyfasm_sv_updating], 1
    mov     rcx, rsi
    call    _pyfasm_set_text
    mov     dword [_pyfasm_sv_updating], 0
.svb_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_stringvar_trace:
    ; RCX = sv_ptr, RDX = mode_str_or_0, R8 = cb_ptr
    test    rcx, rcx
    jz      .svt_done
    test    r8, r8
    jz      .svt_done
    mov     rax, [_pyfasm_sv_trace_cnt]
    cmp     rax, 64
    jge     .svt_done
    inc     qword [_pyfasm_sv_trace_cnt]
    imul    rax, 24
    lea     r9, [_pyfasm_sv_traces + rax]
    mov     [r9 + 0], rcx
    mov     [r9 + 8], r8
    mov     qword [r9 + 16], 0
.svt_done:
    xor     eax, eax
    ret

_pyfasm_refresh_theme_brushes:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16

    cmp     dword [_pyfasm_dark_mode_val], 0
    je      .rtb_light
    mov     dword [_pyfasm_theme_bg], 001A110Fh
    mov     dword [_pyfasm_theme_card], 002B241Eh
    mov     dword [_pyfasm_theme_input], 00241D18h
    mov     dword [_pyfasm_theme_text], 00F0EAE4h
    mov     dword [_pyfasm_theme_muted], 00A89988h
    jmp     .rtb_rebuild
.rtb_light:
    mov     dword [_pyfasm_theme_bg], 00FCF8F4h
    mov     dword [_pyfasm_theme_card], 00FFFFFFh
    mov     dword [_pyfasm_theme_input], 00F5F0EBh
    mov     dword [_pyfasm_theme_text], 002A170Fh
    mov     dword [_pyfasm_theme_muted], 00786958h

.rtb_rebuild:
    mov     rcx, [_pyfasm_hbr_bg]
    test    rcx, rcx
    jz      .rtb_b1
    call    [DeleteObject]
.rtb_b1:
    mov     ecx, [_pyfasm_theme_bg]
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_bg], rax

    mov     rcx, [_pyfasm_hbr_card]
    test    rcx, rcx
    jz      .rtb_b2
    call    [DeleteObject]
.rtb_b2:
    mov     ecx, [_pyfasm_theme_card]
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_card], rax

    mov     rcx, [_pyfasm_hbr_input]
    test    rcx, rcx
    jz      .rtb_b3
    call    [DeleteObject]
.rtb_b3:
    mov     ecx, [_pyfasm_theme_input]
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_input], rax

    ; Re-resolve dual-mode packed widget colors across all registered slots
    mov     rsi, [_pyfasm_layout_count]
    xor     edi, edi
.rtb_wloop:
    cmp     rdi, rsi
    jge     .rtb_dwm
    mov     rax, rdi
    shl     rax, 6
    lea     rbx, [_pyfasm_widget_aux + rax]
    mov     rcx, qword [_pyfasm_layout_table + rax]
    mov     rdx, [rbx + 16]
    mov     r8, [rbx + 24]
    test    rdx, rdx
    jnz     .rtb_upd
    test    r8, r8
    jz      .rtb_wnext
.rtb_upd:
    call    _pyfasm_widget_set_colors
.rtb_wnext:
    inc     rdi
    jmp     .rtb_wloop

.rtb_dwm:
    mov     rcx, [_pyfasm_h_wnd]
    test    rcx, rcx
    jz      .rtb_done
    mov     edx, 20
    lea     r8, [_pyfasm_dark_mode_val]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]
    mov     rcx, [_pyfasm_h_wnd]
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]
.rtb_done:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_appearance_mode:
    ; RCX = mode str ("dark" / "light" / "system")
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .sam_done
    mov     al, [rcx]
    or      al, 20h
    cmp     al, 'l'
    jne     .sam_chk_d
    mov     dword [_pyfasm_dark_mode_val], 0
    jmp     .sam_apply
.sam_chk_d:
    cmp     al, 'd'
    jne     .sam_sys
    mov     dword [_pyfasm_dark_mode_val], 1
    jmp     .sam_apply
.sam_sys:
    call    _pyfasm_is_dark_theme
    mov     dword [_pyfasm_dark_mode_val], eax
.sam_apply:
    call    _pyfasm_refresh_theme_brushes
.sam_done:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_default_color_theme:
    ; RCX = theme str ("blue" / "green" / "dark-blue")
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .sdct_done
    mov     al, [rcx]
    or      al, 20h
    cmp     al, 'g'
    jne     .sdct_chk_db
    mov     dword [_pyfasm_theme_accent], 00529B2Eh
    mov     dword [_pyfasm_theme_accent_press], 003B7020h
    jmp     .sdct_br
.sdct_chk_db:
    cmp     al, 'd'
    jne     .sdct_blue
    mov     dword [_pyfasm_theme_accent], 008B4A1Ah
    mov     dword [_pyfasm_theme_accent_press], 00653512h
    jmp     .sdct_br
.sdct_blue:
    mov     dword [_pyfasm_theme_accent], 00A56A1Fh
    mov     dword [_pyfasm_theme_accent_press], 007B4814h
.sdct_br:
    mov     rcx, [_pyfasm_hbr_orange]
    test    rcx, rcx
    jz      .sdct_b1
    call    [DeleteObject]
.sdct_b1:
    mov     ecx, [_pyfasm_theme_accent]
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_orange], rax
    mov     rcx, [_pyfasm_hbr_orange_press]
    test    rcx, rcx
    jz      .sdct_b2
    call    [DeleteObject]
.sdct_b2:
    mov     ecx, [_pyfasm_theme_accent_press]
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_orange_press], rax
.sdct_done:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_configure:
    ; RCX = hwnd, RDX = text_or_0, R8 = fg_p64_or_0, R9 = tc_p64_or_0, [rbp+48] = values_or_0, [rbp+56] = state_or_0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    test    rbx, rbx
    jz      .wcfg_done
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9

    test    rsi, rsi
    jz      .wcfg_col
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_set_text

.wcfg_col:
    test    rdi, rdi
    jnz     .wcfg_docol
    test    r12, r12
    jz      .wcfg_vals
.wcfg_docol:
    mov     rcx, rbx
    mov     rdx, rdi
    mov     r8, r12
    call    _pyfasm_widget_set_colors

.wcfg_vals:
    mov     rsi, [rbp + 48]
    test    rsi, rsi
    jz      .wcfg_state
    mov     rcx, rsi
    call    _pyfasm_is_list
    test    eax, eax
    jz      .wcfg_state
    ; Clear and repopulate ComboBox if slot is type 9
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .wcfg_state
    shl     rax, 6
    cmp     dword [_pyfasm_layout_table + rax + 16], 9
    jne     .wcfg_state
    mov     rcx, rbx
    mov     edx, 14Bh           ; CB_RESETCONTENT
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    mov     rdi, [rsi]
    xor     r12d, r12d
.wcfg_vloop:
    cmp     r12, rdi
    jge     .wcfg_vsel
    mov     rcx, [rsi + r12*8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
    mov     rcx, rbx
    mov     edx, 143h           ; CB_ADDSTRING
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    inc     r12
    jmp     .wcfg_vloop
.wcfg_vsel:
    mov     rcx, rbx
    mov     edx, 14Eh           ; CB_SETCURSEL
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]

.wcfg_state:
    mov     rsi, [rbp + 56]
    test    rsi, rsi
    jz      .wcfg_done
    mov     al, [rsi]
    or      al, 20h
    cmp     al, 'd'             ; "disabled"
    sete    dl
    movzx   edx, dl
    xor     edx, 1              ; TRUE if not disabled
    mov     rcx, rbx
    call    [EnableWindow]

.wcfg_done:
    xor     eax, eax
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_segmented:
    ; RCX = parent, RDX = values_list, R8 = cb, R9 = sv, [rbp+48] = w, [rbp+56] = h, [rbp+64] = id
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

    mov     r12, rcx            ; parent
    mov     r13, rdx            ; values_list
    mov     r14, r8             ; cb
    mov     r15, r9             ; sv

    mov     rcx, r12
    mov     rdx, [rbp + 48]     ; w
    mov     r8, [rbp + 56]      ; h
    mov     r9d, 8
    mov     qword [rsp + 32], 0
    call    _pyfasm_create_frame
    mov     rbx, rax            ; frame hwnd

    mov     rax, [_pyfasm_seg_cnt]
    cmp     rax, 16
    jge     .cseg_done
    inc     qword [_pyfasm_seg_cnt]
    shl     rax, 7
    lea     rsi, [_pyfasm_segs + rax]
    mov     [rsi + 0], rbx
    mov     qword [rsi + 8], 0
    mov     qword [rsi + 16], 0
    mov     [rsi + 24], r14
    mov     [rsi + 32], r15

    test    r13, r13
    jz      .cseg_done
    mov     rcx, r13
    call    _pyfasm_is_list
    test    eax, eax
    jz      .cseg_done
    mov     rdi, [r13]
    cmp     rdi, 8
    jle     .cseg_cnt_ok
    mov     rdi, 8
.cseg_cnt_ok:
    mov     [rsi + 8], rdi
    xor     r12d, r12d
.cseg_bloop:
    cmp     r12, rdi
    jge     .cseg_done
    mov     rcx, [r13 + r12*8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     rax, [rbp + 56]
    mov     [rsp + 32], rax
    mov     rax, [rbp + 64]
    add     rax, r12
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    mov     [rsp + 56], rbx
    call    _pyfasm_create_button
    mov     [rsi + 40 + r12*8], rax

    push    rax
    mov     rcx, rax
    xor     edx, edx
    mov     r8, r12
    mov     r9d, 15             ; NSEW
    mov     qword [rsp + 32], 1
    mov     qword [rsp + 40], 1
    mov     qword [rsp + 48], 1
    mov     qword [rsp + 56], 1
    call    _pyfasm_widget_set_grid
    mov     rcx, rbx
    mov     rdx, r12
    mov     r8d, 1
    xor     r9d, r9d
    call    _pyfasm_grid_columnconfigure
    pop     rcx
    test    r12, r12
    jz      .cseg_sel0
    mov     edx, [_pyfasm_theme_card]
    mov     r8, 01000000h
    or      rdx, r8
    mov     r9, rdx
    shl     r9, 32
    or      rdx, r9
    mov     r8, 8000000000000000h
    or      rdx, r8
    mov     r8d, [_pyfasm_theme_text]
    mov     r9, 01000000h
    or      r8, r9
    mov     r9, r8
    shl     r9, 32
    or      r8, r9
    mov     r9, 8000000000000000h
    or      r8, r9
    call    _pyfasm_widget_set_colors
    jmp     .cseg_nextb
.cseg_sel0:
    mov     edx, [_pyfasm_theme_accent]
    mov     r8, 01000000h
    or      rdx, r8
    mov     r9, rdx
    shl     r9, 32
    or      rdx, r9
    mov     r8, 8000000000000000h
    or      rdx, r8
    xor     r8d, r8d
    call    _pyfasm_widget_set_colors
.cseg_nextb:
    inc     r12
    jmp     .cseg_bloop

.cseg_done:
    mov     rax, rbx
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

_pyfasm_create_combobox:
    ; RCX = parent, RDX = values_list, R8 = cb, R9 = sv, [rbp+48] = w, [rbp+56] = h, [rbp+64] = id
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 160
    and     rsp, -16

    mov     [rsp + 112], rcx    ; parent
    mov     r12, rdx            ; values_list
    mov     r13, r8             ; cb
    mov     [rsp + 120], r9     ; sv
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .ccb_w
    mov     eax, 180
.ccb_w:
    mov     [rsp + 128], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jg      .ccb_h
    mov     eax, 32
.ccb_h:
    mov     [rsp + 136], rax
    mov     rax, [rbp + 64]
    test    rax, rax
    jnz     .ccb_id
    mov     rax, 4000
    add     rax, [_pyfasm_ctrl_count]
.ccb_id:
    mov     [rsp + 144], rax

    call    _pyfasm_ensure_window
    mov     rax, [rsp + 112]
    test    rax, rax
    jnz     .ccb_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 112], rax
.ccb_p_ok:
    xor     ecx, ecx
    lea     rdx, [_pyfasm_combo_class_w]
    xor     r8, r8
    mov     r9d, 50210003h      ; WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_TABSTOP | CBS_DROPDOWNLIST
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     rax, [rsp + 128]
    mov     [rsp + 48], rax
    mov     rax, [rsp + 136]
    add     rax, 180
    mov     [rsp + 56], rax
    mov     rax, [rsp + 112]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rbx, rax
    mov     [_pyfasm_last_combo_hwnd], rbx
    mov     rcx, rbx
    call    _pyfasm_apply_font

    mov     rcx, rbx
    mov     rdx, [rsp + 112]
    mov     r8, 9
    mov     r9, [rsp + 128]
    mov     rax, [rsp + 136]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rcx, [_pyfasm_ctrl_count]
    cmp     rcx, 128
    jge     .ccb_sv
    mov     rax, [rsp + 144]
    mov     dword [_pyfasm_ctrl_ids + rcx*4], eax
    mov     qword [_pyfasm_ctrl_callbacks + rcx*8], r13
    mov     qword [_pyfasm_ctrl_hwnds + rcx*8], rbx
    inc     qword [_pyfasm_ctrl_count]

.ccb_sv:
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .ccb_items
    shl     rax, 6
    mov     rcx, [rsp + 120]
    mov     qword [_pyfasm_widget_aux + rax + 40], rcx
    mov     ecx, dword [rsp + 144]
    mov     dword [_pyfasm_widget_aux + rax + 56], ecx

.ccb_items:
    test    r12, r12
    jz      .ccb_done
    mov     rcx, r12
    call    _pyfasm_is_list
    test    eax, eax
    jz      .ccb_done
    mov     rsi, [r12]
    xor     edi, edi
.ccb_iloop:
    cmp     rdi, rsi
    jge     .ccb_isel
    mov     rcx, [r12 + rdi*8 + 8]
    call    _pyfasm_auto_to_str
    mov     rcx, rax
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
    mov     rcx, rbx
    mov     edx, 143h
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
    inc     rdi
    jmp     .ccb_iloop
.ccb_isel:
    mov     rcx, rbx
    mov     edx, 14Eh
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]

.ccb_done:
    mov     rax, rbx
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_slider:
    ; RCX = parent, RDX = from_f64, R8 = to_f64, R9 = cb, [rbp+48] = w, [rbp+56] = h, [rbp+64] = id
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    sub     rsp, 160
    and     rsp, -16

    mov     [rsp + 112], rcx    ; parent
    mov     r12, rdx            ; from_f64
    mov     r13, r8             ; to_f64
    mov     [rsp + 120], r9     ; cb
    mov     rax, [rbp + 48]
    test    rax, rax
    jg      .csl_w
    mov     eax, 180
.csl_w:
    mov     [rsp + 128], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jg      .csl_h
    mov     eax, 28
.csl_h:
    mov     [rsp + 136], rax
    mov     rax, [rbp + 64]
    test    rax, rax
    jnz     .csl_id
    mov     rax, 5000
    add     rax, [_pyfasm_ctrl_count]
.csl_id:
    mov     [rsp + 144], rax

    call    _pyfasm_ensure_window
    mov     rax, [rsp + 112]
    test    rax, rax
    jnz     .csl_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 112], rax
.csl_p_ok:
    xor     ecx, ecx
    lea     rdx, [_pyfasm_trackbar_class_w]
    xor     r8, r8
    mov     r9d, 50010000h      ; WS_CHILD | WS_VISIBLE | WS_TABSTOP | TBS_HORZ
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     rax, [rsp + 128]
    mov     [rsp + 48], rax
    mov     rax, [rsp + 136]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 112]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 144]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rbx, rax
    mov     [_pyfasm_last_slider_hwnd], rbx

    mov     rcx, rbx
    mov     edx, 406h           ; TBM_SETRANGE
    mov     r8d, 1
    mov     r9d, 03E80000h      ; max=1000 << 16 | min=0
    call    [SendMessageW]

    mov     rcx, rbx
    mov     rdx, [rsp + 112]
    mov     r8, 10
    mov     r9, [rsp + 128]
    mov     rax, [rsp + 136]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     ecx, 32
    call    _pyfasm_alloc
    mov     rsi, rax
    mov     rax, 505946534C445221h ; 'PYFSLDR!'
    mov     [rsi + 0], rax
    mov     [rsi + 8], r12
    mov     [rsi + 16], r13
    mov     rax, [rsp + 120]
    mov     [rsi + 24], rax

    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .csl_done
    shl     rax, 6
    mov     qword [_pyfasm_widget_aux + rax + 48], rsi

.csl_done:
    mov     rax, rbx
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_progressbar:
    ; RCX = parent, RDX = w, R8 = h, R9 = mode -> RAX = hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 160
    and     rsp, -16

    mov     [rsp + 112], rcx
    test    rdx, rdx
    jg      .cpb_w
    mov     edx, 200
.cpb_w:
    mov     [rsp + 120], rdx
    test    r8, r8
    jg      .cpb_h
    mov     r8d, 16
.cpb_h:
    mov     [rsp + 128], r8

    call    _pyfasm_ensure_window
    mov     rax, [rsp + 112]
    test    rax, rax
    jnz     .cpb_p_ok
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 112], rax
.cpb_p_ok:
    xor     ecx, ecx
    lea     rdx, [_pyfasm_progress_class_w]
    xor     r8, r8
    mov     r9d, 50000001h      ; WS_CHILD | WS_VISIBLE | PBS_SMOOTH
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     rax, [rsp + 120]
    mov     [rsp + 48], rax
    mov     rax, [rsp + 128]
    mov     [rsp + 56], rax
    mov     rax, [rsp + 112]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rbx, rax
    mov     [_pyfasm_last_prog_hwnd], rbx

    mov     rcx, rbx
    mov     edx, 406h           ; PBM_SETRANGE32
    xor     r8d, r8d
    mov     r9d, 1000
    call    [SendMessageW]

    mov     rcx, rbx
    mov     rdx, [rsp + 112]
    mov     r8, 11
    mov     r9, [rsp + 120]
    mov     rax, [rsp + 128]
    mov     [rsp + 32], rax
    call    _pyfasm_register_widget

    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_progressbar_set:
    ; RCX = hwnd, RDX = float64 (0.0..1.0) or int (0..100)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .pbs_h
    mov     rcx, [_pyfasm_last_prog_hwnd]
.pbs_h:
    test    rcx, rcx
    jz      .pbs_done
    mov     rax, 7FFFFFFFFFFFh
    cmp     rdx, rax
    ja      .pbs_f64
    imul    r8d, edx, 10
    jmp     .pbs_send
.pbs_f64:
    movq    xmm0, rdx
    mov     eax, 1000
    cvtsi2sd xmm1, rax
    mulsd   xmm0, xmm1
    cvttsd2si r8d, xmm0
.pbs_send:
    cmp     r8d, 0
    jge     .pbs_hi
    xor     r8d, r8d
.pbs_hi:
    cmp     r8d, 1000
    jle     .pbs_go
    mov     r8d, 1000
.pbs_go:
    mov     edx, 402h           ; PBM_SETPOS
    xor     r9d, r9d
    call    [SendMessageW]
.pbs_done:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_filedialog_open:
    ; RCX = title_or_0, RDX = filter_or_0 -> RAX = utf8_path (or "")
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    lea     rdi, [_pyfasm_fd_ofn_buf]
    xor     eax, eax
    mov     ecx, 20
    rep     stosq
    mov     word [_pyfasm_fd_wide_buf], 0

    mov     dword [_pyfasm_fd_ofn_buf + 0], 152
    mov     rax, [_pyfasm_h_wnd]
    mov     qword [_pyfasm_fd_ofn_buf + 8], rax
    lea     rax, [_pyfasm_ofn_filter]
    mov     qword [_pyfasm_fd_ofn_buf + 24], rax
    mov     dword [_pyfasm_fd_ofn_buf + 44], 1
    lea     rax, [_pyfasm_fd_wide_buf]
    mov     qword [_pyfasm_fd_ofn_buf + 48], rax
    mov     dword [_pyfasm_fd_ofn_buf + 56], 512
    test    rbx, rbx
    jz      .fdo_call
    mov     rcx, rbx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 256
    call    _pyfasm_utf8_to_wide
    lea     rax, [_pyfasm_wide_buf]
    mov     qword [_pyfasm_fd_ofn_buf + 88], rax
.fdo_call:
    mov     dword [_pyfasm_fd_ofn_buf + 96], 1808h
    lea     rcx, [_pyfasm_fd_ofn_buf]
    call    [GetOpenFileNameW]
    test    eax, eax
    jz      .fdo_cancel
    lea     rcx, [_pyfasm_fd_wide_buf]
    call    _pyfasm_wide_to_utf8
    jmp     .fdo_done
.fdo_cancel:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.fdo_done:
    lea     rsp, [rbp - 16]
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_filedialog_save:
    ; RCX = title_or_0, RDX = defext_or_0, R8 = filter_or_0, R9 = initfile_or_0 -> RAX = utf8_path (or "")
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16

    mov     rbx, rcx
    mov     r12, r9
    lea     rdi, [_pyfasm_fd_ofn_buf]
    xor     eax, eax
    mov     ecx, 20
    rep     stosq
    mov     word [_pyfasm_fd_wide_buf], 0

    test    r12, r12
    jz      .fds_init_done
    mov     rcx, r12
    lea     rdx, [_pyfasm_fd_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
.fds_init_done:
    mov     dword [_pyfasm_fd_ofn_buf + 0], 152
    mov     rax, [_pyfasm_h_wnd]
    mov     qword [_pyfasm_fd_ofn_buf + 8], rax
    lea     rax, [_pyfasm_ofn_filter]
    mov     qword [_pyfasm_fd_ofn_buf + 24], rax
    mov     dword [_pyfasm_fd_ofn_buf + 44], 1
    lea     rax, [_pyfasm_fd_wide_buf]
    mov     qword [_pyfasm_fd_ofn_buf + 48], rax
    mov     dword [_pyfasm_fd_ofn_buf + 56], 512
    test    rbx, rbx
    jz      .fds_call
    mov     rcx, rbx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 256
    call    _pyfasm_utf8_to_wide
    lea     rax, [_pyfasm_wide_buf]
    mov     qword [_pyfasm_fd_ofn_buf + 88], rax
.fds_call:
    mov     dword [_pyfasm_fd_ofn_buf + 96], 0Ah
    lea     rcx, [_pyfasm_fd_ofn_buf]
    call    [GetSaveFileNameW]
    test    eax, eax
    jz      .fds_cancel
    lea     rcx, [_pyfasm_fd_wide_buf]
    call    _pyfasm_wide_to_utf8
    jmp     .fds_done
.fds_cancel:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.fds_done:
    lea     rsp, [rbp - 24]
    pop     r12
    pop     rdi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_msgbox_info:
    ; RCX = title, RDX = msg, R8 = flags -> RAX = 1
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     [rsp + 32], r8d
    test    rsi, rsi
    jz      .mbi_notxt
    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 512
    call    _pyfasm_utf8_to_wide
    jmp     .mbi_title
.mbi_notxt:
    mov     word [_pyfasm_wide_buf], 0
.mbi_title:
    test    rbx, rbx
    jz      .mbi_notit
    mov     rcx, rbx
    lea     rdx, [_pyfasm_fd_wide_buf]
    mov     r8d, 256
    call    _pyfasm_utf8_to_wide
    lea     r8, [_pyfasm_fd_wide_buf]
    jmp     .mbi_call
.mbi_notit:
    lea     r8, [_pyfasm_wnd_title_w]
.mbi_call:
    mov     rcx, [_pyfasm_h_wnd]
    lea     rdx, [_pyfasm_wide_buf]
    mov     r9d, [rsp + 32]
    call    [MessageBoxW]
    mov     eax, 1
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_after:
    ; RCX = hwnd_or_0, RDX = ms, R8 = cb_ptr -> RAX = timer_id
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .aft_h
    mov     rcx, [_pyfasm_h_wnd]
.aft_h:
    mov     rbx, rcx
    mov     rsi, rdx
    cmp     rsi, 1
    jge     .aft_ms_ok
    mov     esi, 1
.aft_ms_ok:
    mov     rax, [_pyfasm_timer_cnt]
    cmp     rax, 32
    jge     .aft_fail
    inc     qword [_pyfasm_timer_cnt]
    lea     r9, [rax + 9001]
    imul    rax, 24
    lea     r10, [_pyfasm_timers + rax]
    mov     [r10 + 0], r9
    mov     [r10 + 8], rbx
    mov     [r10 + 16], r8
    mov     [rsp + 32], r9
    mov     rcx, rbx
    mov     rdx, r9
    mov     r8d, esi
    xor     r9d, r9d
    call    [SetTimer]
    mov     rax, [rsp + 32]
    jmp     .aft_done
.aft_fail:
    xor     eax, eax
.aft_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_bind:
    ; RCX = hwnd, RDX = event_str, R8 = cb_ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    test    rdx, rdx
    jz      .wb_done
    test    r8, r8
    jz      .wb_done
    mov     rax, [_pyfasm_bind_cnt]
    cmp     rax, 64
    jge     .wb_done
    mov     rbx, rcx
    mov     rsi, r8
    mov     rcx, rdx
    call    _pyfasm_str_lower
    mov     r8d, 2              ; <Key>
    mov     rcx, rax
    lea     rdx, [_pyfasm_str_tag_return]
    call    _pyfasm_str_contains
    test    eax, eax
    jz      .wb_chk_b1
    mov     r8d, 1              ; <Return>
    jmp     .wb_store
.wb_chk_b1:
    lea     rdx, [_pyfasm_str_tag_btn1]
    call    _pyfasm_str_contains
    test    eax, eax
    jz      .wb_store
    mov     r8d, 3              ; <Button-1>
.wb_store:
    mov     rax, [_pyfasm_bind_cnt]
    inc     qword [_pyfasm_bind_cnt]
    imul    rax, 24
    lea     rcx, [_pyfasm_binds + rax]
    mov     [rcx + 0], rbx
    mov     [rcx + 8], r8
    mov     [rcx + 16], rsi
.wb_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_grid_propagate:
    ; RCX = hwnd, RDX = flag (0 = disabled -> set bit 0, 1 = enabled -> clear bit 0)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rdx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .gp_done
    shl     rax, 6
    test    rbx, rbx
    jz      .gp_disable
    and     dword [_pyfasm_layout_table + rax + 60], 0FFFFFFFEh
    jmp     .gp_done
.gp_disable:
    or      dword [_pyfasm_layout_table + rax + 60], 1
.gp_done:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_winfo_width:
    ; RCX = hwnd -> RAX = width
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .wiw_ok
    mov     rcx, [_pyfasm_h_wnd]
.wiw_ok:
    test    rcx, rcx
    jz      .wiw_zero
    lea     rdx, [rsp + 32]
    call    [GetClientRect]
    mov     eax, [rsp + 40]
    sub     eax, [rsp + 32]
    jmp     .wiw_done
.wiw_zero:
    xor     eax, eax
.wiw_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_winfo_height:
    ; RCX = hwnd -> RAX = height
    push    rbp
    mov     rbp, rsp
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .wih_ok
    mov     rcx, [_pyfasm_h_wnd]
.wih_ok:
    test    rcx, rcx
    jz      .wih_zero
    lea     rdx, [rsp + 32]
    call    [GetClientRect]
    mov     eax, [rsp + 44]
    sub     eax, [rsp + 36]
    jmp     .wih_done
.wih_zero:
    xor     eax, eax
.wih_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_textbox_append:
    ; RCX = hwnd, RDX = utf8_str
    push    rbp
    mov     rbp, rsp
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .tba_done
    test    rdx, rdx
    jz      .tba_done
    mov     rsi, rcx
    mov     rcx, rdx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8d, 1024
    call    _pyfasm_utf8_to_wide
    mov     rcx, rsi
    mov     edx, 0B1h           ; EM_SETSEL
    mov     r8d, -1
    mov     r9d, -1
    call    [SendMessageW]
    mov     rcx, rsi
    mov     edx, 0C2h           ; EM_REPLACESEL
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
.tba_done:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rsi
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; PyQt5 / PyQt6 / PySide6 / PySide2 Native Layout Engine
; ============================================================
_pyfasm_qt_create_widget:
    ; RCX = parent_or_0 -> RAX = hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    cmp     qword [_pyfasm_h_wnd], 0
    jne     .qtc_chk_p
    test    rbx, rbx
    jnz     .qtc_chk_p
    call    _pyfasm_ensure_window
    mov     rax, [_pyfasm_h_wnd]
    jmp     .qtc_done
.qtc_chk_p:
    mov     rcx, rbx
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0
    call    _pyfasm_create_frame
.qtc_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_layout_new:
    ; RCX = kind (1=VBox,2=HBox,3=Grid), RDX = parent_hwnd_or_0 -> RAX = PYFQLAY!
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     ecx, 64
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     rax, 505946514C415921h ; 'PYFQLAY!'
    mov     [rdi + 0], rax
    mov     [rdi + 8], rbx
    mov     [rdi + 16], rsi
    mov     qword [rdi + 24], 0
    mov     qword [rdi + 32], 64
    mov     ecx, 64 * 32
    call    _pyfasm_alloc
    mov     [rdi + 40], rax
    mov     qword [rdi + 48], 8
    mov     qword [rdi + 56], 6
    test    rsi, rsi
    jz      .qln_done
    mov     rcx, rsi
    mov     rdx, rdi
    call    _pyfasm_qt_widget_set_layout
.qln_done:
    mov     rax, rdi
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_layout_add_widget:
    ; RCX = lay_ptr, RDX = widget_hwnd, R8 = row_or_stretch, R9 = col, [rbp+48]=rowspan, [rbp+56]=colspan
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .qlaw_done
    test    rdx, rdx
    jz      .qlaw_done
    mov     rax, [rcx + 24]
    cmp     rax, [rcx + 32]
    jge     .qlaw_done
    inc     qword [rcx + 24]
    shl     rax, 5
    add     rax, [rcx + 40]
    mov     [rax + 0], rdx
    mov     dword [rax + 8], r8d
    mov     dword [rax + 12], r9d
    mov     ebx, dword [rbp + 48]
    test    ebx, ebx
    jg      .qlaw_rs
    mov     ebx, 1
.qlaw_rs:
    mov     dword [rax + 16], ebx
    mov     ebx, dword [rbp + 56]
    test    ebx, ebx
    jg      .qlaw_cs
    mov     ebx, 1
.qlaw_cs:
    mov     dword [rax + 20], ebx
    mov     dword [rax + 24], 0
    cmp     qword [rcx + 16], 0
    je      .qlaw_done
    mov     rsi, rcx
    mov     rcx, [rcx + 16]
    mov     rdx, rsi
    call    _pyfasm_qt_widget_set_layout
.qlaw_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_layout_add_layout:
    ; RCX = lay_ptr, RDX = sublay_ptr, R8 = row, R9 = col
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .qlal_done
    test    rdx, rdx
    jz      .qlal_done
    mov     rax, [rcx + 24]
    cmp     rax, [rcx + 32]
    jge     .qlal_done
    inc     qword [rcx + 24]
    shl     rax, 5
    add     rax, [rcx + 40]
    mov     [rax + 0], rdx
    mov     dword [rax + 8], r8d
    mov     dword [rax + 12], r9d
    mov     dword [rax + 16], 1
    mov     dword [rax + 20], 1
    mov     dword [rax + 24], 1 ; sublayout flag
    cmp     qword [rcx + 16], 0
    je      .qlal_done
    mov     rsi, rcx
    mov     rcx, [rcx + 16]
    mov     rdx, rsi
    call    _pyfasm_qt_widget_set_layout
.qlal_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_layout_set_margins:
    ; RCX = lay_ptr, RDX = margin
    test    rcx, rcx
    jz      .qlm_d
    mov     [rcx + 48], rdx
.qlm_d:
    xor     eax, eax
    ret

_pyfasm_qt_layout_add_stretch:
    xor     eax, eax
    ret

_pyfasm_qt_widget_set_layout:
    ; RCX = owner_hwnd, RDX = lay_ptr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 80
    and     rsp, -16

    test    rcx, rcx
    jnz     .qsl_h
    mov     rcx, [_pyfasm_h_wnd]
.qsl_h:
    mov     r12, rcx
    mov     r13, rdx
    test    r12, r12
    jz      .qsl_done
    test    r13, r13
    jz      .qsl_done
    mov     [r13 + 16], r12

    mov     r14, [r13 + 24]
    xor     r15d, r15d
.qsl_loop:
    cmp     r15, r14
    jge     .qsl_apply
    mov     rsi, r15
    shl     rsi, 5
    add     rsi, [r13 + 40]
    mov     rbx, [rsi + 0]
    test    rbx, rbx
    jz      .qsl_next

    test    dword [rsi + 24], 1
    jz      .qsl_widget
    ; Sublayout -> allocate child frame once if sublay.owner == 0
    mov     rax, [rbx + 16]
    test    rax, rax
    jnz     .qsl_sub_have_frame
    mov     rcx, r12
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 0
    call    _pyfasm_create_frame
    mov     [rbx + 16], rax
.qsl_sub_have_frame:
    mov     rdi, rax
    mov     rcx, rdi
    mov     rdx, rbx
    call    _pyfasm_qt_widget_set_layout
    mov     rbx, rdi
    jmp     .qsl_assign

.qsl_widget:
    mov     rcx, rbx
    mov     rdx, r12
    call    [SetParent]
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qsl_assign
    shl     rax, 6
    mov     qword [_pyfasm_layout_table + rax + 8], r12

.qsl_assign:
    ; Default expand=1 for Frames(2), ListBox(5), Canvas(6), Textbox(7), sublayouts
    mov     edi, 0
    test    dword [rsi + 24], 1
    jz      .qsl_chk_type
    mov     edi, 1
    jmp     .qsl_mode
.qsl_chk_type:
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qsl_mode
    shl     rax, 6
    mov     ecx, dword [_pyfasm_layout_table + rax + 16]
    cmp     ecx, 2
    je      .qsl_exp1
    cmp     ecx, 5
    je      .qsl_exp1
    cmp     ecx, 6
    je      .qsl_exp1
    cmp     ecx, 7
    je      .qsl_exp1
    cmp     dword [rsi + 8], 0
    jle     .qsl_mode
.qsl_exp1:
    mov     edi, 1

.qsl_mode:
    mov     rax, [r13 + 8]      ; 1=VBox, 2=HBox, 3=Grid
    cmp     rax, 3
    je      .qsl_grid
    cmp     rax, 2
    je      .qsl_hbox
    ; VBox: pack(side=top(0), fill=both(3), expand=edi, padx=6, pady=4)
    mov     rcx, rbx
    xor     edx, edx
    mov     r8d, 3
    mov     r9d, edi
    mov     rax, [r13 + 48]
    mov     [rsp + 32], rax
    mov     qword [rsp + 40], 4
    call    _pyfasm_widget_set_pack
    jmp     .qsl_next
.qsl_hbox:
    ; HBox: pack(side=left(2), fill=both(3), expand=edi, padx=4, pady=6)
    mov     rcx, rbx
    mov     edx, 2
    mov     r8d, 3
    mov     r9d, edi
    mov     qword [rsp + 32], 4
    mov     rax, [r13 + 48]
    mov     [rsp + 40], rax
    call    _pyfasm_widget_set_pack
    jmp     .qsl_next
.qsl_grid:
    mov     rcx, rbx
    movsxd  rdx, dword [rsi + 8]
    movsxd  r8, dword [rsi + 12]
    mov     r9d, 15
    mov     qword [rsp + 32], 4
    mov     qword [rsp + 40], 4
    movsxd  rax, dword [rsi + 20]
    mov     [rsp + 48], rax
    movsxd  rax, dword [rsi + 16]
    mov     [rsp + 56], rax
    call    _pyfasm_widget_set_grid
    mov     rcx, r12
    movsxd  rdx, dword [rsi + 12]
    mov     r8d, 1
    xor     r9d, r9d
    call    _pyfasm_grid_columnconfigure
    test    edi, edi
    jz      .qsl_next
    mov     rcx, r12
    movsxd  rdx, dword [rsi + 8]
    mov     r8d, 1
    xor     r9d, r9d
    call    _pyfasm_grid_rowconfigure

.qsl_next:
    inc     r15
    jmp     .qsl_loop

.qsl_apply:
    mov     rcx, r12
    call    _pyfasm_apply_layout

.qsl_done:
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

_pyfasm_qt_set_central_widget:
    ; RCX = main_wnd, RDX = central_hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jnz     .qsc_m
    mov     rcx, [_pyfasm_h_wnd]
.qsc_m:
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .qsc_done
    test    rsi, rsi
    jz      .qsc_done
    cmp     rbx, rsi
    je      .qsc_done
    mov     rcx, rsi
    mov     rdx, rbx
    call    [SetParent]
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qsc_grid
    shl     rax, 6
    mov     qword [_pyfasm_layout_table + rax + 8], rbx
.qsc_grid:
    mov     rcx, rsi
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, 15
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 1
    mov     qword [rsp + 56], 1
    call    _pyfasm_widget_set_grid
    mov     rcx, rbx
    xor     edx, edx
    mov     r8d, 1
    xor     r9d, r9d
    call    _pyfasm_grid_columnconfigure
    mov     rcx, rbx
    xor     edx, edx
    mov     r8d, 1
    xor     r9d, r9d
    call    _pyfasm_grid_rowconfigure
    mov     rcx, rbx
    call    _pyfasm_apply_layout
.qsc_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_combobox_index:
    ; RCX = hwnd -> RAX = cursel
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .qci_h
    mov     rcx, [_pyfasm_last_combo_hwnd]
.qci_h:
    test    rcx, rcx
    jz      .qci_zero
    mov     edx, 147h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .qci_done
.qci_zero:
    xor     eax, eax
.qci_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_combobox_set_index:
    ; RCX = hwnd, RDX = idx
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .qcsi_h
    mov     rcx, [_pyfasm_last_combo_hwnd]
.qcsi_h:
    test    rcx, rcx
    jz      .qcsi_done
    mov     r8d, edx
    mov     edx, 14Eh
    xor     r9d, r9d
    call    [SendMessageW]
.qcsi_done:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_tab_add:
    ; RCX = tab_frame_hwnd, RDX = page_hwnd, R8 = title_str -> RAX = page_hwnd
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 64
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .qta_done
    test    rsi, rsi
    jz      .qta_done
    mov     rcx, rsi
    mov     rdx, rbx
    call    [SetParent]
    mov     rcx, rsi
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qta_pack
    shl     rax, 6
    mov     qword [_pyfasm_layout_table + rax + 8], rbx
.qta_pack:
    mov     rcx, rsi
    xor     edx, edx
    mov     r8d, 3
    mov     r9d, 1
    mov     qword [rsp + 32], 4
    mov     qword [rsp + 40], 4
    call    _pyfasm_widget_set_pack
    mov     rcx, rbx
    call    _pyfasm_apply_layout
.qta_done:
    mov     rax, rsi
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_set_value:
    ; RCX = hwnd, RDX = val (int or float64 bits)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rbx, rbx
    jz      .qsv_done
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qsv_done
    shl     rax, 6
    mov     ecx, dword [_pyfasm_layout_table + rax + 16]
    cmp     ecx, 10             ; Slider
    je      .qsv_uni
    cmp     ecx, 11             ; ProgressBar
    je      .qsv_pb
    ; Edit / SpinBox
    mov     rax, rsi
    sar     rax, 48
    test    rax, rax
    jz      .qsv_is_int
    cmp     rax, -1
    jne     .qsv_flt
.qsv_is_int:
    mov     rcx, rsi
    call    _pyfasm_int_to_str
    jmp     .qsv_set
.qsv_flt:
    mov     rcx, rsi
    call    _pyfasm_float_to_str
.qsv_set:
    mov     rcx, rbx
    mov     rdx, rax
    call    _pyfasm_set_text
    jmp     .qsv_done
.qsv_pb:
    mov     rax, rsi
    sar     rax, 48
    test    rax, rax
    jz      .qsv_pb_int
    cmp     rax, -1
    jne     .qsv_uni
.qsv_pb_int:
    imul    r8d, esi, 10
    mov     rcx, rbx
    mov     edx, 402h           ; PBM_SETPOS (0..100 -> 0..1000)
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .qsv_done
.qsv_uni:
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_unified_set
.qsv_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_get_value:
    ; RCX = hwnd -> RAX = int (or float64 for slider)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jz      .qgv_zero
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qgv_zero
    shl     rax, 6
    mov     ecx, dword [_pyfasm_layout_table + rax + 16]
    cmp     ecx, 10             ; Slider
    jne     .qgv_edit
    mov     rcx, rbx
    call    _pyfasm_unified_get
    jmp     .qgv_done
.qgv_edit:
    mov     rcx, rbx
    call    _pyfasm_unified_get
    mov     rcx, rax
    call    _pyfasm_str_to_int
    jmp     .qgv_done
.qgv_zero:
    xor     eax, eax
.qgv_done:
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qt_set_range:
    ; RCX = hwnd, RDX = min_val (int), R8 = max_val (int)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
    test    rbx, rbx
    jz      .qsr_done
    mov     rcx, rbx
    call    _pyfasm_find_widget_slot
    cmp     rax, 0
    jl      .qsr_done
    shl     rax, 6
    mov     ecx, dword [_pyfasm_layout_table + rax + 16]
    cmp     ecx, 10             ; Slider PYFSLDR!
    jne     .qsr_done
    mov     rcx, qword [_pyfasm_widget_aux + rax + 48]
    test    rcx, rcx
    jz      .qsr_done
    cvtsi2sd xmm0, rsi
    movsd   qword [rcx + 8], xmm0
    cvtsi2sd xmm1, rdi
    movsd   qword [rcx + 16], xmm1
.qsr_done:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qtimer_new:
    ; -> RAX = PYFQTIMR ptr
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     rdx, 5059465154494D52h ; 'PYFQTIMR'
    mov     qword [rax + 0], rdx
    mov     qword [rax + 8], 0
    mov     qword [rax + 16], 100
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_qtimer_connect:
    ; RCX = timer ptr, RDX = cb ptr
    test    rcx, rcx
    jz      .qtc2_d
    mov     qword [rcx + 8], rdx
.qtc2_d:
    xor     eax, eax
    ret

_pyfasm_qtimer_start:
    ; RCX = timer ptr, RDX = interval_ms
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .qts_d
    mov     rax, 5059465154494D52h
    cmp     qword [rcx], rax
    jne     .qts_d
    test    rdx, rdx
    jg      .qts_ms_ok
    mov     rdx, qword [rcx + 16]
.qts_ms_ok:
    mov     qword [rcx + 16], rdx
    mov     r8, qword [rcx + 8]
    xor     ecx, ecx
    call    _pyfasm_after
.qts_d:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
"""

_WIN64_WS2_32_IMPORT_BLOCK = """
    import ws2_32, \\
           WSAStartup, 'WSAStartup', \\
           WSACleanup, 'WSACleanup', \\
           socket, 'socket', \\
           setsockopt, 'setsockopt', \\
           inet_addr, 'inet_addr', \\
           htons, 'htons', \\
           bind, 'bind', \\
           listen, 'listen', \\
           accept, 'accept', \\
           recv, 'recv', \\
           send, 'send', \\
           closesocket, 'closesocket'
"""


def _append_ws2_32_imports(idata: str) -> str:
    head, tail = idata.lstrip("\n").split("\n\n", 1)
    head = head.rstrip() + ", \\\n            ws2_32, 'WS2_32.DLL'"
    return "\n" + head + "\n\n" + tail.rstrip() + "\n" + _WIN64_WS2_32_IMPORT_BLOCK


def get_win64_runtime_data(features: Optional[Set[str]] = None) -> str:
    """Returns runtime data structures (buffers, handles, constants)."""
    needs_gui = features is None or any(f in features for f in ("gui", "tray", "hook", "pygame", "matplotlib"))
    needs_net = features is None or "net" in features
    needs_pygame = features is not None and "pygame" in features
    needs_http = features is not None and "http_server" in features

    if not needs_gui:
        data = _WIN64_CONSOLE_RUNTIME_DATA
        if needs_net:
            data += "\n" + _WIN64_NET_RUNTIME_DATA
    else:
        data = _get_win64_full_runtime_data()

    from .runtime_core_x64 import get_core_x64_data
    data += "\n" + get_core_x64_data()

    if needs_gui:
        from .runtime_win64_matplotlib import WIN64_MPL_RUNTIME_DATA
        data += "\n" + WIN64_MPL_RUNTIME_DATA
    if needs_pygame:
        from .runtime_win64_pygame import WIN64_PYGAME_RUNTIME_DATA
        data += "\n" + WIN64_PYGAME_RUNTIME_DATA
    if needs_http:
        from .runtime_win64_http import WIN64_HTTP_RUNTIME_DATA
        data += "\n" + WIN64_HTTP_RUNTIME_DATA
    return data


def get_win64_runtime_code(features: Optional[Set[str]] = None) -> str:
    """Returns native assembly routines with strict 16-byte stack alignment."""
    needs_gui = features is None or any(f in features for f in ("gui", "tray", "hook", "pygame", "matplotlib"))
    needs_net = features is None or "net" in features
    needs_pygame = features is not None and "pygame" in features
    needs_http = features is not None and "http_server" in features

    from .runtime_core_x64 import get_core_x64_code
    if not needs_gui:
        code = _WIN64_CONSOLE_RUNTIME_CODE
        if needs_net:
            code += "\n" + _WIN64_NET_RUNTIME_CODE
        code += "\n" + _WIN64_FORMAT_SPEC_HELPERS_ASM + "\n" + get_core_x64_code()
    else:
        code = _get_win64_full_runtime_code() + "\n" + _WIN64_FORMAT_SPEC_HELPERS_ASM + "\n" + _WIN64_GUI_EXTRA_HELPERS_ASM + "\n" + get_core_x64_code()

    if needs_gui:
        from .runtime_win64_matplotlib import WIN64_MPL_RUNTIME_CODE
        code += "\n" + WIN64_MPL_RUNTIME_CODE
    if needs_pygame:
        from .runtime_win64_pygame import WIN64_PYGAME_RUNTIME_CODE
        code += "\n" + WIN64_PYGAME_RUNTIME_CODE
    if needs_http:
        from .runtime_win64_http import WIN64_HTTP_RUNTIME_CODE
        code += "\n" + WIN64_HTTP_RUNTIME_CODE
    return code


def get_win64_runtime_imports(features: Optional[Set[str]] = None) -> str:
    """Returns the IData section with Win32 API imports."""
    needs_gui = features is None or any(f in features for f in ("gui", "tray", "hook", "pygame", "matplotlib"))
    needs_net = features is None or "net" in features
    needs_http = features is not None and "http_server" in features

    if not needs_gui:
        idata = _WIN64_NET_RUNTIME_IMPORTS if needs_net else _WIN64_CONSOLE_RUNTIME_IMPORTS
    else:
        idata = _get_win64_full_runtime_imports()

    if needs_http:
        idata = _append_ws2_32_imports(idata)
    return idata
