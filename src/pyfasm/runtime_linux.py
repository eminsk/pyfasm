"""
Native Linux x86-64 ELF64 Runtime for PyFASM.
Outputs standard Linux ELF64 executable using direct Linux kernel syscalls.
No libc, no external dependencies required.
"""
from __future__ import annotations


def get_linux_runtime_header() -> str:
    """Returns the FASM ELF64 executable header."""
    return """format ELF64 executable 3
entry _pyfasm_entry_point

segment readable executable
"""


def get_linux_runtime_data() -> str:
    """Returns Linux runtime data structures."""
    from pyfasm.runtime_common import get_common_runtime_data
    return """
segment readable writeable
    crlf_str        db 10, 0
    linux_time_sec  dq 0
    linux_time_nsec dq 0

    ; --- Universal Linux GUI & Geometry Engine Data ---
    _pyfasm_h_wnd           dq 1
    _pyfasm_last_label_hwnd dq 0
    _pyfasm_last_edit_hwnd  dq 0
    _pyfasm_last_btn_hwnd   dq 0
    _pyfasm_last_list_hwnd  dq 0
    _pyfasm_ctrl_count      dq 0
    _pyfasm_ctrl_hwnds      rq 128
    _pyfasm_ctrl_ids        rd 128
    _pyfasm_ctrl_callbacks  rq 128
    _pyfasm_layout_count    dq 0
    _pyfasm_layout_table    rb 256 * 64
    _pyfasm_container_cfg_count dq 0
    _pyfasm_container_cfg_table rb 32 * 272
    _pyfasm_col_widths      rd 32
    _pyfasm_row_heights     rd 32
    _pyfasm_col_pos         rd 32
    _pyfasm_row_pos         rd 32
    _pyfasm_edit_buf        rb 2048
    _pyfasm_list_items      rb 128 * 64
    _pyfasm_gui_list_count  dq 0
    _pyfasm_gui_list_sel    dq 0
    _pyfasm_chk_state       dq 0
    _pyfasm_win_title       db 'PyFASM Linux App', 0
    _pyfasm_ansi_clear      db 27, '[2J', 27, '[H', 0
""" + get_common_runtime_data()


def get_linux_runtime_code() -> str:
    """Returns native Linux syscall routines (System V AMD64 ABI)."""
    from pyfasm.runtime_common import get_common_runtime_code
    return """
segment readable executable

_pyfasm_init_io:
    ret

_pyfasm_print_char:
    ; RCX = character code (in CL)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 16
    mov     byte [rsp], cl
    mov     rax, 1                  ; sys_write
    mov     rdi, 1                  ; stdout
    mov     rsi, rsp
    mov     rdx, 1
    syscall
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
    mov     rdx, rcx                ; rdx = length

    test    rdx, rdx
    jz      .done_print_str

    ; sys_write(stdout=1, buf=rsi, len=rdx)
    mov     rax, 1                  ; sys_write
    mov     rdi, 1                  ; stdout
    syscall

.done_print_str:
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_print_newline:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 16
    mov     byte [rsp], 10          ; LF newline
    mov     rax, 1                  ; sys_write
    mov     rdi, 1                  ; stdout
    mov     rsi, rsp                ; buffer
    mov     rdx, 1                  ; length
    syscall
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

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16

    xorps   xmm1, xmm1
    ucomisd xmm0, xmm1
    jae     .flt_pos
    ; Negative
    movsd   [rsp + 32], xmm0
    mov     byte [rsp], '-'
    mov     rax, 1
    mov     rdi, 1
    mov     rsi, rsp
    mov     rdx, 1
    syscall
    movsd   xmm0, [rsp + 32]
    xorps   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1

.flt_pos:
    movsd   [rsp + 32], xmm0
    cvttsd2si rax, xmm0
    mov     [rsp + 40], rax
    mov     rcx, rax
    call    _pyfasm_print_int

    ; Print dot
    mov     byte [rsp], '.'
    mov     rax, 1
    mov     rdi, 1
    mov     rsi, rsp
    mov     rdx, 1
    syscall

    ; Fraction (6 decimals with leading zeros)
    movsd   xmm0, [rsp + 32]
    cvtsi2sd xmm2, qword [rsp + 40]
    subsd   xmm0, xmm2
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
    lea     r8, [rsp + 22]
    mov     byte [r8], 0
    mov     r9, 10
    mov     ecx, 6
.frac_digit_loop:
    xor     rdx, rdx
    div     r9
    add     dl, '0'
    dec     r8
    mov     [r8], dl
    dec     ecx
    jnz     .frac_digit_loop
    mov     rax, 1
    mov     rdi, 1
    mov     rsi, r8
    mov     rdx, 6
    syscall
.flt_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_alloc_memory:
    ; RCX = bytes to allocate -> sys_mmap
    push    rbp
    mov     rbp, rsp
    mov     rsi, rcx                ; length
    xor     rdi, rdi                ; addr = 0
    mov     rdx, 3                  ; PROT_READ | PROT_WRITE
    mov     r10, 0x22               ; MAP_PRIVATE | MAP_ANONYMOUS
    mov     r8, -1                  ; fd = -1
    xor     r9, r9                  ; offset = 0
    mov     rax, 9                  ; sys_mmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_free_memory:
    ; RCX = ptr
    push    rbp
    mov     rbp, rsp
    mov     rdi, rcx
    mov     rsi, 4096               ; munmap default page
    mov     rax, 11                 ; sys_munmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_atomic_add:
    ; RCX = pointer to int64, RDX = value to add
    lock add qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_atomic_sub:
    ; RCX = pointer to int64, RDX = value to subtract
    lock sub qword [rcx], rdx
    mov     rax, [rcx]
    ret

_pyfasm_get_tick_count:
    ; High-resolution timestamp via RDTSC scaled to ms
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    ; Divide by typical 2.5 GHz (approx 2,500,000 cycles/ms)
    mov     rcx, 2500000
    xor     rdx, rdx
    div     rcx
    ret

_pyfasm_sleep_ms:
    ; RCX = milliseconds -> sys_nanosleep
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32

    ; sec = ms / 1000
    mov     rax, rcx
    xor     rdx, rdx
    mov     rbx, 1000
    div     rbx
    mov     [rsp], rax              ; tv_sec
    ; nsec = rem * 1000000
    imul    rdx, 1000000
    mov     [rsp + 8], rdx          ; tv_nsec

    mov     rdi, rsp
    xor     rsi, rsi
    mov     rax, 35                 ; sys_nanosleep
    syscall

    add     rsp, 32
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_alloc:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    mov     rsi, rcx                ; length
    xor     rdi, rdi                ; addr = NULL
    mov     rdx, 3                  ; PROT_READ | PROT_WRITE
    mov     r10, 34                 ; MAP_PRIVATE | MAP_ANONYMOUS
    mov     r8, -1                  ; fd = -1
    xor     r9, r9                  ; offset = 0
    mov     rax, 9                  ; sys_mmap
    syscall
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_free:
    xor     eax, eax
    ret

_pyfasm_init_gui:
    mov     qword [_pyfasm_h_wnd], 1
    mov     rax, 1
    ret

_pyfasm_set_window_title:
    ; RCX = title string
    test    rcx, rcx
    jz      .sw_done
    ; Copy to _pyfasm_win_title
    push    rsi
    push    rdi
    mov     rsi, rcx
    lea     rdi, [_pyfasm_win_title]
    mov     ecx, 63
.sw_copy:
    lodsb
    stosb
    test    al, al
    jz      .sw_copy_done
    dec     ecx
    jnz     .sw_copy
    mov     byte [rdi], 0
.sw_copy_done:
    pop     rdi
    pop     rsi
.sw_done:
    mov     rax, 1
    ret

_pyfasm_create_window:
    mov     rax, 1
    mov     [_pyfasm_h_wnd], rax
    ret

_pyfasm_register_widget:
    ; RCX = hwnd, RDX = parent, R8 = widget_type, R9 = req_w, [rsp+40] = req_h
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32

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
    shl     rcx, 6
    lea     rbx, [_pyfasm_layout_table + rcx]
    shr     rcx, 6
    cmp     [rbx], rsi
    je      .update_existing
    inc     rcx
    jmp     .chk_loop

.add_new:
    cmp     rax, 256
    jge     .reg_done
    mov     rcx, rax
    shl     rcx, 6
    lea     rbx, [_pyfasm_layout_table + rcx]
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
    jmp     .reg_done

.update_existing:
    mov     [rbx + 8], rdx
    mov     dword [rbx + 16], r8d
    mov     dword [rbx + 52], r9d
    mov     eax, dword [rbp + 48]
    mov     dword [rbx + 56], eax

.reg_done:
    add     rsp, 32
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
    mov     r11, [_pyfasm_h_wnd]
    mov     [rbx + 8], r11
    mov     dword [rbx + 16], 0
    mov     dword [rbx + 52], 120
    mov     dword [rbx + 56], 32

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
    add     rsp, 32
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

    test    rcx, rcx
    jnz     .gcc_c_ok
    mov     rcx, [_pyfasm_h_wnd]
.gcc_c_ok:
    mov     r12, rcx
    cmp     rdx, 32
    jae     .gcc_done

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
    mov     r11, rax
    imul    r11, 272
    lea     rbx, [_pyfasm_container_cfg_table + r11]
    inc     qword [_pyfasm_container_cfg_count]
    push    rdi
    mov     rdi, rbx
    xor     eax, eax
    mov     ecx, 34
    rep     stosq
    pop     rdi
    mov     [rbx], r12

.gcc_set:
    mov     dword [rbx + 8 + rdx*4], r8d

.gcc_done:
    add     rsp, 32
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

    test    rcx, rcx
    jnz     .grc_c_ok
    mov     rcx, [_pyfasm_h_wnd]
.grc_c_ok:
    mov     r12, rcx
    cmp     rdx, 32
    jae     .grc_done

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
    mov     r11, rax
    imul    r11, 272
    lea     rbx, [_pyfasm_container_cfg_table + r11]
    inc     qword [_pyfasm_container_cfg_count]
    push    rdi
    mov     rdi, rbx
    xor     eax, eax
    mov     ecx, 34
    rep     stosq
    pop     rdi
    mov     [rbx], r12

.grc_set:
    mov     dword [rbx + 136 + rdx*4], r8d

.grc_done:
    add     rsp, 32
    pop     r12
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_widget_set_pack:
    ret

_pyfasm_widget_set_place:
    ret

_pyfasm_apply_layout:
    ret

_pyfasm_create_frame:
    ; RCX = parent, RDX = w, R8 = h, R9 = corner_radius
    mov     rax, [_pyfasm_ctrl_count]
    add     rax, 100
    inc     qword [_pyfasm_ctrl_count]
    ret

_pyfasm_create_canvas:
    ; RCX = parent, RDX = w, R8 = h
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 200
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 7
    xor     edx, edx
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_label:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rdx, rcx
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 300
    mov     [_pyfasm_last_label_hwnd], rbx
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 1
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_edit:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rdx, rcx
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 400
    mov     [_pyfasm_last_edit_hwnd], rbx
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 2
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_textbox:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rdx, rcx
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 500
    mov     [_pyfasm_last_edit_hwnd], rbx
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 3
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_button:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = callback_fn
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rdx, rcx
    mov     rax, [_pyfasm_ctrl_count]
    cmp     rax, 128
    jge     .btn_reg_skip
    mov     r10, [rbp + 56]
    mov     r11, [rbp + 64]
    mov     dword [_pyfasm_ctrl_ids + rax*4], r10d
    mov     qword [_pyfasm_ctrl_callbacks + rax*8], r11
.btn_reg_skip:
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 600
    mov     [_pyfasm_last_btn_hwnd], rbx
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 4
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_checkbox:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rdx, rcx
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 700
    mov     [_pyfasm_last_btn_hwnd], rbx
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 5
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_listbox:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, [_pyfasm_ctrl_count]
    add     rbx, 800
    mov     [_pyfasm_last_list_hwnd], rbx
    inc     qword [_pyfasm_ctrl_count]
    mov     ecx, 6
    xor     edx, edx
    mov     r8, rbx
    call    _pyfasm_common_record_widget
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_register_hotkey:
    mov     rax, 1
    ret

_pyfasm_get_edit_text:
    lea     rax, [_pyfasm_edit_buf]
    ret

_pyfasm_set_text:
    ret

_pyfasm_checkbox_get:
    mov     rax, [_pyfasm_chk_state]
    ret

_pyfasm_checkbox_set:
    mov     [_pyfasm_chk_state], rdx
    ret

_pyfasm_listbox_append:
    ret

_pyfasm_listbox_clear:
    ret

_pyfasm_listbox_count:
    xor     eax, eax
    ret

_pyfasm_listbox_get_selected:
    lea     rax, [_pyfasm_edit_buf]
    ret

_pyfasm_canvas_create_line:
    ret

_pyfasm_canvas_create_text:
    ret

_pyfasm_wnd_proc:
    xor     eax, eax
    ret

_pyfasm_run_window_loop:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16

    call    _pyfasm_render_tui_window

    ; Execute registered button callback if available
    mov     rsi, [_pyfasm_ctrl_count]
    cmp     rsi, 128
    jle     .cb_cnt_ok
    mov     esi, 128
.cb_cnt_ok:
    xor     ebx, ebx
.cb_loop:
    cmp     rbx, rsi
    jge     .cb_done
    mov     rcx, qword [_pyfasm_ctrl_callbacks + rbx*8]
    test    rcx, rcx
    jz      .next_cb
    xor     edx, edx
    call    _pyfasm_invoke_cb
    jmp     .cb_done
.next_cb:
    inc     rbx
    jmp     .cb_loop
.cb_done:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_message_box:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_print_str
    call    _pyfasm_print_newline
    mov     rsp, rbp
    pop     rbp
    ret

; --- POSIX Linux x86-64 File I/O & Stdin Input (Win64 ABI -> Linux syscalls) ---
_pyfasm_file_open:
    ; RCX = path cstr, RDX = mode cstr_or_0 -> RAX = fd or -1
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    mov     rdi, rcx                ; path
    xor     esi, esi                ; O_RDONLY = 0
    test    rdx, rdx
    jz      .lfo_do
    movzx   eax, byte [rdx]
    cmp     al, 'w'
    je      .lfo_w
    cmp     al, 'a'
    je      .lfo_a
    jmp     .lfo_do
.lfo_w:
    mov     esi, 241h               ; O_WRONLY | O_CREAT | O_TRUNC
    jmp     .lfo_do
.lfo_a:
    mov     esi, 441h               ; O_WRONLY | O_CREAT | O_APPEND
.lfo_do:
    mov     edx, 1A4h               ; 0644o
    mov     rax, 2                  ; sys_open
    syscall
    cmp     rax, 0
    jge     .lfo_ok
    mov     rax, -1
.lfo_ok:
    pop     rdi
    pop     rsi
    pop     rbp
    ret

_pyfasm_file_write_bytes:
    ; RCX = fd, RDX = buf, R8 = byte_len -> RAX = bytes_written
    push    rsi
    push    rdi
    cmp     rcx, 0
    jl      .lfwb_err
    mov     rdi, rcx
    mov     rsi, rdx
    mov     rdx, r8
    mov     rax, 1                  ; sys_write
    syscall
    pop     rdi
    pop     rsi
    ret
.lfwb_err:
    mov     rax, -1
    pop     rdi
    pop     rsi
    ret

_pyfasm_file_read_bytes:
    ; RCX = fd, RDX = buf, R8 = max_bytes -> RAX = bytes_read
    push    rsi
    push    rdi
    cmp     rcx, 0
    jl      .lfrb_err
    mov     rdi, rcx
    mov     rsi, rdx
    mov     rdx, r8
    xor     eax, eax                ; sys_read
    syscall
    pop     rdi
    pop     rsi
    ret
.lfrb_err:
    xor     eax, eax
    pop     rdi
    pop     rsi
    ret

_pyfasm_file_write_data:
    ; RCX = fd, RDX = cstr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    test    rsi, rsi
    jz      .lfwd_d
    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     r8, rax
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_file_write_bytes
.lfwd_d:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_file_read_all:
    ; RCX = fd -> RAX = alloc cstr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    cmp     rbx, 0
    jl      .lfra_empty
    mov     rdi, rbx
    xor     esi, esi
    mov     edx, 2                  ; SEEK_END
    mov     rax, 8                  ; sys_lseek
    syscall
    cmp     rax, 0
    jle     .lfra_empty
    mov     rsi, rax                ; size
    mov     rdi, rbx
    xor     r10d, r10d
    push    rsi
    xor     esi, esi
    xor     edx, edx                ; SEEK_SET
    mov     rax, 8
    syscall
    pop     rsi
    lea     rcx, [rsi + 1]
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     rcx, rbx
    mov     rdx, rdi
    mov     r8, rsi
    call    _pyfasm_file_read_bytes
    cmp     rax, 0
    jge     .lfra_nul
    xor     eax, eax
.lfra_nul:
    mov     byte [rdi + rax], 0
    mov     rax, rdi
    jmp     .lfra_done
.lfra_empty:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
.lfra_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_file_close:
    ; RCX = fd
    push    rdi
    cmp     rcx, 0
    jl      .lfc_d
    mov     rdi, rcx
    mov     rax, 3                  ; sys_close
    syscall
.lfc_d:
    pop     rdi
    xor     eax, eax
    ret

_pyfasm_file_write:
    ; RCX = path, RDX = cstr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rsi, rdx
    lea     rdx, [.lfw_m]
    call    _pyfasm_file_open
    cmp     rax, 0
    jl      .lfw_d
    mov     rbx, rax
    mov     rcx, rbx
    mov     rdx, rsi
    call    _pyfasm_file_write_data
    mov     rcx, rbx
    call    _pyfasm_file_close
.lfw_d:
    xor     eax, eax
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
.lfw_m db 'w', 0

_pyfasm_input:
    ; RCX = prompt_or_0 -> RAX = alloc line cstr
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .linp_read
    call    _pyfasm_print_str
.linp_read:
    mov     ecx, 1024
    call    _pyfasm_alloc
    mov     rbx, rax
    xor     edi, edi                ; stdin = 0
    mov     rsi, rbx
    mov     edx, 1023
    xor     eax, eax                ; sys_read
    syscall
    cmp     rax, 0
    jle     .linp_empty
.linp_trim:
    cmp     rax, 0
    jle     .linp_nul
    movzx   ecx, byte [rbx + rax - 1]
    cmp     cl, 10
    je      .linp_dec
    cmp     cl, 13
    jne     .linp_nul
.linp_dec:
    dec     rax
    jmp     .linp_trim
.linp_empty:
    xor     eax, eax
.linp_nul:
    mov     byte [rbx + rax], 0
    mov     rax, rbx
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
""" + get_common_runtime_code()
