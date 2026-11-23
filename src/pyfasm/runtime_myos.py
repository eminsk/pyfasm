"""
Native MyOS 10 x64 Runtime for PyFASM.
Outputs flat binary or ELF64 compatible with MyOS kernel execution.
"""
from __future__ import annotations


def get_myos_runtime_header() -> str:
    """Returns the FASM header for MyOS binary."""
    return """format binary as 'bin'
use64
org 0x1000000   ; Default MyOS userspace program base
jmp _pyfasm_entry_point
"""


def get_myos_runtime_data() -> str:
    from pyfasm.runtime_common import get_common_runtime_data
    return """
align 8
crlf_str        db 13, 10, 0

; --- Universal MyOS 10 LFB Framebuffer GUI & Geometry Engine Data ---
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
_pyfasm_win_title       db 'PyFASM MyOS 10 App', 0
_pyfasm_lfb_base        dq 0xFD000000   ; Default VESA / GOP 32bpp Framebuffer Base in MyOS
_pyfasm_lfb_width       dd 1024
_pyfasm_lfb_height      dd 768
_pyfasm_lfb_pitch       dd 4096
align 16
_pyfasm_myos_heap_ptr   dq _pyfasm_myos_heap_base
_pyfasm_myos_heap_base  rb 16 * 1024 * 1024
""" + get_common_runtime_data()


def get_myos_runtime_code() -> str:
    """Returns native MyOS routines: Serial port I/O & VGA framebuffer output."""
    from pyfasm.runtime_common import get_common_runtime_code
    return """
_pyfasm_alloc_memory:
_pyfasm_alloc:
    ; RCX = bytes to allocate
    push    rbx
    add     rcx, 15
    and     rcx, -16
    mov     rax, [_pyfasm_myos_heap_ptr]
    test    rax, rax
    jnz     .alloc_ok
    lea     rax, [_pyfasm_myos_heap_base]
.alloc_ok:
    lea     rbx, [rax + rcx]
    mov     [_pyfasm_myos_heap_ptr], rbx
    pop     rbx
    ret

_pyfasm_free_memory:
_pyfasm_free:
    xor     eax, eax
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
    ; CL = character
    mov     ah, cl
    mov     dx, 03FDh
.wait_tx:
    in      al, dx
    test    al, 20h
    jz      .wait_tx
    mov     dx, 03F8h
    mov     al, ah
    out     dx, al
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

_pyfasm_print_str:
    ; RCX = pointer to string
    test    rcx, rcx
    jz      .done_str_early
    push    rsi
    mov     rsi, rcx
.loop_str:
    lodsb
    test    al, al
    jz      .done_str
    mov     cl, al
    call    _pyfasm_print_char
    jmp     .loop_str
.done_str:
    pop     rsi
.done_str_early:
    ret

_pyfasm_print_newline:
    push    rax
    push    rcx
    mov     cl, 13
    call    _pyfasm_print_char
    mov     cl, 10
    call    _pyfasm_print_char
    pop     rcx
    pop     rax
    ret

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    movq    rcx, xmm0
    call    _pyfasm_float_to_str
    mov     rcx, rax
    call    _pyfasm_print_str
    mov     rsp, rbp
    pop     rbp
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

_pyfasm_init_gui:
    mov     qword [_pyfasm_h_wnd], 1
    mov     rax, 1
    ret

_pyfasm_set_window_title:
    mov     rax, 1
    ret

_pyfasm_create_window:
    mov     rax, 1
    mov     [_pyfasm_h_wnd], rax
    ret

_pyfasm_register_widget:
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
    mov     rax, [_pyfasm_ctrl_count]
    add     rax, 100
    inc     qword [_pyfasm_ctrl_count]
    ret

_pyfasm_create_canvas:
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

_pyfasm_file_open:
    mov     rax, -1
    ret

_pyfasm_file_write_bytes:
    mov     rax, -1
    ret

_pyfasm_file_read_bytes:
    xor     eax, eax
    ret

_pyfasm_file_write_data:
    xor     eax, eax
    ret

_pyfasm_file_read_all:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_file_close:
    xor     eax, eax
    ret

_pyfasm_file_write:
    xor     eax, eax
    ret

_pyfasm_input:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .myinp_e
    call    _pyfasm_print_str
.myinp_e:
    mov     ecx, 1
    call    _pyfasm_alloc
    mov     byte [rax], 0
    mov     rsp, rbp
    pop     rbp
    ret
""" + get_common_runtime_code()
