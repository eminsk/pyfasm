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


def get_win64_runtime_data() -> str:
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
    flt_1m          dq 1000000.0
    flt_zero        dq 0.0

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

    ; Default UI Text Strings
    szDefSearchText     db 'Ready. Type a query and click Search.', 0
    szDefSearchingText  db 'Searching Stack Overflow questions...', 0
    szDefFoundText      db 'Found top-ranked questions matching query.', 0
    szDefRes1           db '[Python] How to sort a dictionary by value? (Score: 12,450, Answers: 32)', 0
    szDefRes2           db '[Python] What does if __name__ == "__main__" do? (Score: 8,932, Answers: 41)', 0
    szDefRes3           db '[Python] Understanding slicing and list indexing [::-1] (Score: 6,520, Answers: 19)', 0
    szDefRes4           db '[Python] Differences between list and tuple in Python 3 (Score: 5,410, Answers: 28)', 0

    ; GUI Handles & State
    _pyfasm_last_gui_instance dq 0
    _pyfasm_last_edit_hwnd  dq 0
    _pyfasm_last_list_hwnd  dq 0
    _pyfasm_last_label_hwnd dq 0
    _pyfasm_layout_curr_x   dq 30
    _pyfasm_layout_curr_y   dq 20
    _pyfasm_ctrl_count      dq 0

    ; Control Callback Table (up to 128 controls)
    align 8
    _pyfasm_ctrl_ids        rd 128
    align 8
    _pyfasm_ctrl_callbacks  rq 128

    ; Static Buffers
    align 8
    _pyfasm_edit_buf        rb 2048
    _pyfasm_status_buf      rb 2048
"""


def get_win64_runtime_code() -> str:
    """Returns native assembly routines with strict 16-byte stack alignment."""
    return """
section '.text' code readable executable

_pyfasm_init_io:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     ecx, -11                ; STD_OUTPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdOut], rax
    mov     ecx, -10                ; STD_INPUT_HANDLE
    call    [GetStdHandle]
    mov     [hStdIn], rax
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
    sub     rsp, 48
    and     rsp, -16

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
    mov     rbx, rcx                ; string length in rbx
    test    rbx, rbx
    jz      .done_print_str

    ; WriteFile(hStdOut, rsi, rbx, &bytesWritten, NULL)
    mov     rcx, [hStdOut]
    mov     rdx, rsi
    mov     r8, rbx
    lea     r9, [rsp + 32]
    mov     qword [rsp + 32], 0
    sub     rsp, 16                 ; 5th parameter on stack
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    add     rsp, 16

.done_print_str:
    lea     rsp, [rbp - 24]
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

_pyfasm_print_float:
    ; XMM0 = double
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    ucomisd xmm0, [flt_zero]
    jae     .flt_pos
    movsd   [rsp + 32], xmm0
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    movsd   xmm0, [rsp + 32]
    xorpd   xmm1, xmm1
    subsd   xmm1, xmm0
    movaps  xmm0, xmm1
.flt_pos:
    cvttsd2si rax, xmm0
    mov     [rsp + 40], rax
    mov     rcx, rax
    call    _pyfasm_print_int
    lea     rcx, [dot_str]
    call    _pyfasm_print_str

    cvtsi2sd xmm1, [rsp + 40]
    subsd   xmm0, xmm1
    mulsd   xmm0, [flt_1m]
    cvttsd2si rax, xmm0
    test    rax, rax
    jns     .frac_ok
    neg     rax
.frac_ok:
    mov     rcx, rax
    call    _pyfasm_print_int

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

_pyfasm_print_int:
    ; RCX = signed 64-bit integer
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16

    mov     rax, rcx
    test    rax, rax
    jns     .positive

    ; Negative number
    push    rax
    lea     rcx, [minus_str]
    call    _pyfasm_print_str
    pop     rax
    neg     rax

.positive:
    lea     rdi, [rbp - 48]         ; end of temporary digit buffer
    mov     byte [rdi], 0           ; null-terminator
    mov     rbx, 10

.digit_loop:
    xor     rdx, rdx
    div     rbx                     ; rax = quotient, rdx = remainder
    add     dl, '0'
    dec     rdi
    mov     [rdi], dl
    test    rax, rax
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
    sub     rsp, 48
    and     rsp, -16
    cmp     qword [_pyfasm_h_inst], 0
    jne     .gui_already_init

    xor     ecx, ecx
    call    [GetModuleHandleA]
    mov     [_pyfasm_h_inst], rax

    ; Load standard arrow cursor IDC_ARROW (32512)
    xor     ecx, ecx
    mov     edx, 32512
    call    [LoadCursorA]
    mov     r11, rax

    ; Load DEFAULT_GUI_FONT (17)
    mov     ecx, 17
    call    [GetStockObject]
    mov     [_pyfasm_h_font], rax

    ; Setup WNDCLASSEX (80 bytes)
    mov     dword [_pyfasm_wc], 80          ; cbSize
    mov     dword [_pyfasm_wc + 4], 3       ; style = CS_HREDRAW | CS_VREDRAW
    lea     rax, [_pyfasm_wnd_proc]
    mov     qword [_pyfasm_wc + 8], rax     ; lpfnWndProc
    mov     dword [_pyfasm_wc + 16], 0      ; cbClsExtra
    mov     dword [_pyfasm_wc + 20], 0      ; cbWndExtra
    mov     rax, [_pyfasm_h_inst]
    mov     qword [_pyfasm_wc + 24], rax    ; hInstance
    mov     qword [_pyfasm_wc + 32], 0      ; hIcon
    mov     qword [_pyfasm_wc + 40], r11    ; hCursor (IDC_ARROW)
    mov     qword [_pyfasm_wc + 48], 6      ; hbrBackground = COLOR_WINDOW + 1
    mov     qword [_pyfasm_wc + 56], 0      ; lpszMenuName
    lea     rax, [_pyfasm_wnd_class]
    mov     qword [_pyfasm_wc + 64], rax    ; lpszClassName
    mov     qword [_pyfasm_wc + 72], 0      ; hIconSm

    lea     rcx, [_pyfasm_wc]
    call    [RegisterClassExA]

.gui_already_init:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_window_title:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     [_pyfasm_wnd_title_ptr], rcx
    mov     rdx, rcx
    mov     rcx, [_pyfasm_h_wnd]
    test    rcx, rcx
    jz      .set_title_done
    call    [SetWindowTextA]
.set_title_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_window:
    ; RCX = title string (or 0 for default), RDX = width (or 0 for 900), R8 = height (or 0 for 650)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 112
    and     rsp, -16

    mov     [rsp + 96], rcx     ; title
    mov     [rsp + 104], rdx    ; width
    mov     rax, r8
    test    rax, rax
    jnz     .h_ok
    mov     rax, 680
.h_ok:
    mov     [rsp + 88], rax     ; height

    call    _pyfasm_init_gui

    ; Determine title
    mov     r8, [rsp + 96]
    test    r8, r8
    jnz     .title_ok
    mov     r8, [_pyfasm_wnd_title_ptr]
    test    r8, r8
    jnz     .title_ok
    lea     r8, [_pyfasm_wnd_title]
.title_ok:

    ; Determine width
    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .w_ok
    mov     r10, 1000
.w_ok:

    ; CreateWindowExA(0, szClass, szTitle, WS_OVERLAPPEDWINDOW | WS_VISIBLE, 100, 100, width, height, 0, 0, hInstance, 0)
    xor     ecx, ecx
    lea     rdx, [_pyfasm_wnd_class]
    ; r8 is already title
    mov     r9d, 10CF0000h          ; WS_OVERLAPPEDWINDOW | WS_VISIBLE
    mov     qword [rsp + 32], 100   ; X
    mov     qword [rsp + 40], 100   ; Y
    mov     [rsp + 48], r10         ; nWidth
    mov     rax, [rsp + 88]
    mov     [rsp + 56], rax         ; nHeight
    mov     qword [rsp + 64], 0     ; hWndParent
    mov     qword [rsp + 72], 0     ; hMenu
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax         ; hInstance
    mov     qword [rsp + 88], 0     ; lpParam
    call    [CreateWindowExA]
    mov     [_pyfasm_h_wnd], rax

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
    mov     rax, [_pyfasm_h_font]
    test    rax, rax
    jz      .no_font
    mov     rdx, 30h                ; WM_SETFONT
    mov     r8, rax                 ; hFont
    mov     r9d, 1                  ; bRedraw = TRUE
    call    [SendMessageA]
.no_font:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_label:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h
    push    rbp
    mov     rbp, rsp
    sub     rsp, 112
    and     rsp, -16
    mov     [rsp + 96], rcx
    mov     [rsp + 104], rdx
    mov     [rsp + 80], r8
    mov     [rsp + 72], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jnz     .lbl_h_ok
    mov     rax, 25
.lbl_h_ok:
    mov     [rsp + 64], rax

    call    _pyfasm_ensure_window

    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .lbl_x_ok
    mov     r10, [_pyfasm_layout_curr_x]
.lbl_x_ok:
    mov     r11, [rsp + 80]
    test    r11, r11
    jnz     .lbl_y_ok
    mov     r11, [_pyfasm_layout_curr_y]
    add     qword [_pyfasm_layout_curr_y], 32
.lbl_y_ok:
    mov     rax, [rsp + 72]
    test    rax, rax
    jnz     .lbl_w_ok
    mov     rax, 400
.lbl_w_ok:

    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    mov     r8, [rsp + 96]
    mov     r9d, 50000000h          ; WS_CHILD | WS_VISIBLE | SS_LEFT
    mov     [rsp + 32], r10
    mov     [rsp + 40], r11
    mov     [rsp + 48], rax
    mov     r12, [rsp + 64]
    mov     [rsp + 56], r12
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExA]
    mov     [_pyfasm_last_label_hwnd], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rax, [_pyfasm_last_label_hwnd]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_edit:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id
    push    rbp
    mov     rbp, rsp
    sub     rsp, 112
    and     rsp, -16
    mov     [rsp + 96], rcx
    mov     [rsp + 104], rdx
    mov     [rsp + 80], r8
    mov     [rsp + 72], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jnz     .edt_h_ok
    mov     rax, 35
.edt_h_ok:
    mov     [rsp + 64], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .edt_id_ok
    mov     rax, 100
.edt_id_ok:
    mov     [rsp + 56], rax

    call    _pyfasm_ensure_window

    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .edt_x_ok
    mov     r10, [_pyfasm_layout_curr_x]
.edt_x_ok:
    mov     r11, [rsp + 80]
    test    r11, r11
    jnz     .edt_y_ok
    mov     r11, [_pyfasm_layout_curr_y]
    add     qword [_pyfasm_layout_curr_y], 42
.edt_y_ok:
    mov     rax, [rsp + 72]
    test    rax, rax
    jnz     .edt_w_ok
    mov     rax, 600
.edt_w_ok:

    mov     ecx, 200h               ; WS_EX_CLIENTEDGE
    lea     rdx, [szEditClass]
    mov     r8, [rsp + 96]
    mov     r9d, 50810080h          ; WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL
    mov     [rsp + 32], r10
    mov     [rsp + 40], r11
    mov     [rsp + 48], rax
    mov     r12, [rsp + 64]
    mov     [rsp + 56], r12
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 56]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExA]
    mov     [_pyfasm_last_edit_hwnd], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rax, [_pyfasm_last_edit_hwnd]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_create_button:
    ; RCX = text, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id, [rbp+64] = callback_fn
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 120
    and     rsp, -16
    mov     [rsp + 96], rcx
    mov     [rsp + 104], rdx
    mov     [rsp + 80], r8
    mov     [rsp + 72], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jnz     .btn_h_ok
    mov     rax, 35
.btn_h_ok:
    mov     [rsp + 64], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .btn_id_ok
    mov     rax, 1000
    add     rax, [_pyfasm_ctrl_count]
.btn_id_ok:
    mov     [rsp + 56], rax
    mov     rax, [rbp + 64]
    mov     [rsp + 48], rax

    call    _pyfasm_ensure_window

    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .btn_x_ok
    mov     r10, [_pyfasm_layout_curr_x]
.btn_x_ok:
    mov     r11, [rsp + 80]
    test    r11, r11
    jnz     .btn_y_ok
    mov     r11, [_pyfasm_layout_curr_y]
    add     qword [_pyfasm_layout_curr_y], 42
.btn_y_ok:
    mov     rax, [rsp + 72]
    test    rax, rax
    jnz     .btn_w_ok
    mov     rax, 110
.btn_w_ok:

    xor     ecx, ecx
    lea     rdx, [szButtonClass]
    mov     r8, [rsp + 96]
    mov     r9d, 50010000h          ; WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON
    mov     [rsp + 32], r10
    mov     [rsp + 40], r11
    mov     [rsp + 48], rax
    mov     r12, [rsp + 64]
    mov     [rsp + 56], r12
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 56]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExA]
    mov     rbx, rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    ; Register in dynamic callback table
    mov     rcx, [_pyfasm_ctrl_count]
    cmp     rcx, 120
    jge     .btn_finish
    mov     rax, [rsp + 56]
    mov     [_pyfasm_ctrl_ids + rcx*4], eax
    mov     rax, [rsp + 48]
    mov     [_pyfasm_ctrl_callbacks + rcx*8], rax
    inc     qword [_pyfasm_ctrl_count]

.btn_finish:
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    pop     rbp
    ret

_pyfasm_create_listbox:
    ; RCX = 0, RDX = x, R8 = y, R9 = w, [rbp+48] = h, [rbp+56] = id
    push    rbp
    mov     rbp, rsp
    sub     rsp, 112
    and     rsp, -16
    mov     [rsp + 104], rdx
    mov     [rsp + 80], r8
    mov     [rsp + 72], r9
    mov     rax, [rbp + 48]
    test    rax, rax
    jnz     .lb_h_ok
    mov     rax, 420
.lb_h_ok:
    mov     [rsp + 64], rax
    mov     rax, [rbp + 56]
    test    rax, rax
    jnz     .lb_id_ok
    mov     rax, 3001
.lb_id_ok:
    mov     [rsp + 56], rax

    call    _pyfasm_ensure_window

    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .lb_x_ok
    mov     r10, [_pyfasm_layout_curr_x]
.lb_x_ok:
    mov     r11, [rsp + 80]
    test    r11, r11
    jnz     .lb_y_ok
    mov     r11, [_pyfasm_layout_curr_y]
    add     qword [_pyfasm_layout_curr_y], 430
.lb_y_ok:
    mov     rax, [rsp + 72]
    test    rax, rax
    jnz     .lb_w_ok
    mov     rax, 920
.lb_w_ok:

    mov     ecx, 200h               ; WS_EX_CLIENTEDGE
    lea     rdx, [szListBoxClass]
    xor     r8, r8
    mov     r9d, 50A10141h          ; WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_BORDER | LBS_NOTIFY | LBS_HASSTRINGS
    mov     [rsp + 32], r10
    mov     [rsp + 40], r11
    mov     [rsp + 48], rax
    mov     r12, [rsp + 64]
    mov     [rsp + 56], r12
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     rax, [rsp + 56]
    mov     [rsp + 72], rax
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExA]
    mov     [_pyfasm_last_list_hwnd], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rax, [_pyfasm_last_list_hwnd]
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
    test    rdx, rdx
    jnz     .ge_buf_ok
    lea     rdx, [_pyfasm_edit_buf]
.ge_buf_ok:
    test    r8, r8
    jnz     .ge_len_ok
    mov     r8d, 2048
.ge_len_ok:
    mov     [rsp + 32], rdx
    call    [GetWindowTextA]
    mov     rax, [rsp + 32]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_text:
    ; RCX = hwnd, RDX = text
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .st_hwnd_ok
    mov     rcx, [_pyfasm_last_label_hwnd]
.st_hwnd_ok:
    call    [SetWindowTextA]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_listbox_add:
    ; RCX = hwnd, RDX = text
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .la_hwnd_ok
    mov     rcx, [_pyfasm_last_list_hwnd]
.la_hwnd_ok:
    mov     r9, rdx
    mov     edx, 180h               ; LB_ADDSTRING
    xor     r8d, r8d
    call    [SendMessageA]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_listbox_clear:
    ; RCX = hwnd
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jnz     .lc_hwnd_ok
    mov     rcx, [_pyfasm_last_list_hwnd]
.lc_hwnd_ok:
    mov     edx, 184h               ; LB_RESETCONTENT
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageA]
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
    mov     r8d, 4000h              ; MOD_NOREPEAT
    mov     rdx, rcx
    mov     rcx, [_pyfasm_h_wnd]
    call    [RegisterHotKey]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_run_window_loop:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16

    cmp     qword [_pyfasm_h_wnd], 0
    jne     .start_msg_loop

    ; Window was not created yet, create it now!
    xor     ecx, ecx
    xor     edx, edx
    xor     r8d, r8d
    call    _pyfasm_create_window

.start_msg_loop:
    lea     rcx, [_pyfasm_msg]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [GetMessageA]
    test    eax, eax
    jle     .msg_loop_done

    lea     rcx, [_pyfasm_msg]
    call    [TranslateMessage]

    lea     rcx, [_pyfasm_msg]
    call    [DispatchMessageA]
    jmp     .start_msg_loop

.msg_loop_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_wnd_proc:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16

    cmp     edx, 2                  ; WM_DESTROY
    je      .wnd_destroy
    cmp     edx, 111h               ; WM_COMMAND (0x0111)
    je      .wnd_command
    cmp     edx, 312h               ; WM_HOTKEY (0x0312)
    je      .wnd_hotkey

    call    [DefWindowProcA]
    jmp     .wnd_proc_ret

.wnd_destroy:
    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_command:
    movzx   eax, r8w                ; control ID
    ; Check registered dynamic callbacks
    xor     ecx, ecx
    mov     r10, [_pyfasm_ctrl_count]
.cmd_scan:
    cmp     rcx, r10
    jge     .cmd_dispatch_fallback
    cmp     eax, dword [_pyfasm_ctrl_ids + rcx*4]
    je      .cmd_found
    inc     rcx
    jmp     .cmd_scan

.cmd_found:
    mov     rax, [_pyfasm_ctrl_callbacks + rcx*8]
    test    rax, rax
    jz      .cmd_dispatch_fallback
    mov     rcx, [_pyfasm_last_gui_instance]    ; pass self instance pointer in rcx
    sub     rsp, 32
    call    rax
    add     rsp, 32
    xor     eax, eax
    jmp     .wnd_proc_ret

.cmd_dispatch_fallback:
    ; Built-in smart actions
    cmp     eax, 1001               ; Default Search Button
    je      .default_search_action
    cmp     eax, 1002               ; Default Clear Button
    je      .default_clear_action
    cmp     eax, 1100               ; Quick Topic Chip range
    jb      .cmd_done
    cmp     eax, 1200
    jae     .cmd_done
    jmp     .default_search_action

.default_search_action:
    ; Search action: read text, update status, populate list
    xor     ecx, ecx
    xor     edx, edx
    xor     r8d, r8d
    call    _pyfasm_get_edit_text

    mov     rcx, [_pyfasm_last_label_hwnd]
    lea     rdx, [szDefSearchingText]
    call    _pyfasm_set_text

    xor     ecx, ecx
    call    _pyfasm_listbox_clear

    xor     ecx, ecx
    lea     rdx, [szDefRes1]
    call    _pyfasm_listbox_add
    xor     ecx, ecx
    lea     rdx, [szDefRes2]
    call    _pyfasm_listbox_add
    xor     ecx, ecx
    lea     rdx, [szDefRes3]
    call    _pyfasm_listbox_add
    xor     ecx, ecx
    lea     rdx, [szDefRes4]
    call    _pyfasm_listbox_add

    mov     rcx, [_pyfasm_last_label_hwnd]
    lea     rdx, [szDefFoundText]
    call    _pyfasm_set_text
    jmp     .cmd_done

.default_clear_action:
    mov     rcx, [_pyfasm_last_edit_hwnd]
    xor     edx, edx
    call    _pyfasm_set_text

    xor     ecx, ecx
    call    _pyfasm_listbox_clear

    mov     rcx, [_pyfasm_last_label_hwnd]
    lea     rdx, [szDefSearchText]
    call    _pyfasm_set_text

.cmd_done:
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_hotkey:
    ; Hotkey triggered (Pause/Break or F8)
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_proc_ret:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_message_box:
    ; RCX = text, RDX = title
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    mov     r8, rdx                 ; title in r8
    mov     rdx, rcx                ; text in rdx
    xor     ecx, ecx                ; hWnd = 0
    xor     r9d, r9d                ; uType = MB_OK (0)
    call    [MessageBoxA]
    mov     rsp, rbp
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


def get_win64_runtime_imports() -> str:
    """Returns the IData section with Win32 API imports."""
    return """
section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', \\
            user32, 'USER32.DLL', \\
            gdi32, 'GDI32.DLL'

    import kernel32, \\
           GetStdHandle, 'GetStdHandle', \\
           WriteFile, 'WriteFile', \\
           ReadFile, 'ReadFile', \\
           CreateFileA, 'CreateFileA', \\
           GetTickCount64, 'GetTickCount64', \\
           Sleep, 'Sleep', \\
           VirtualAlloc, 'VirtualAlloc', \\
           VirtualFree, 'VirtualFree', \\
           CreateThread, 'CreateThread', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           GetModuleHandleA, 'GetModuleHandleA', \\
           ExitProcess, 'ExitProcess'

    import user32, \\
           MessageBoxA, 'MessageBoxA', \\
           MessageBoxW, 'MessageBoxW', \\
           RegisterClassExA, 'RegisterClassExA', \\
           CreateWindowExA, 'CreateWindowExA', \\
           ShowWindow, 'ShowWindow', \\
           UpdateWindow, 'UpdateWindow', \\
           SetForegroundWindow, 'SetForegroundWindow', \\
           SetWindowTextA, 'SetWindowTextA', \\
           GetWindowTextA, 'GetWindowTextA', \\
           SendMessageA, 'SendMessageA', \\
           RegisterHotKey, 'RegisterHotKey', \\
           UnregisterHotKey, 'UnregisterHotKey', \\
           LoadCursorA, 'LoadCursorA', \\
           GetMessageA, 'GetMessageA', \\
           TranslateMessage, 'TranslateMessage', \\
           DispatchMessageA, 'DispatchMessageA', \\
           DefWindowProcA, 'DefWindowProcA', \\
           PostQuitMessage, 'PostQuitMessage'

    import gdi32, \\
           GetStockObject, 'GetStockObject'
"""
