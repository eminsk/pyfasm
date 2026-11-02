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

    ; --- Modern Unicode UTF-16 Win32 GUI Runtime Data ---
    align 8
    _pyfasm_wnd_class_w     du 'PyFasmWindowClassW', 0
    _pyfasm_tray_class_w    du 'PyFasmTrayClassW', 0
    _pyfasm_wnd_title_w     du 'Stack Overflow Search Pro', 0
    _pyfasm_wnd_title_w_ptr dq _pyfasm_wnd_title_w

    szButtonClassW          du 'BUTTON', 0
    szEditClassW            du 'EDIT', 0
    szStaticClassW          du 'STATIC', 0
    szListBoxClassW         du 'LISTBOX', 0
    wszSegoeUI              du 'Segoe UI', 0
    wszConsolas             du 'Consolas', 0

    ; Dark Theme GDI Brushes & Attributes
    align 8
    _pyfasm_dark_mode_val   dd 1
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
    wszPillText             du '+0   1 ans', 0
    align 8
    _pyfasm_card_text_buf   rw 512
    align 8
    _pyfasm_rc_client       rd 4
    _pyfasm_h_font_ui       dq 0
    _pyfasm_h_font_bold     dq 0
    _pyfasm_h_font_mono     dq 0

    ; Split View HWND Handles
    align 8
    _pyfasm_h_logo          dq 0
    _pyfasm_h_search_edit   dq 0
    _pyfasm_h_clear_btn     dq 0
    _pyfasm_h_search_btn    dq 0
    _pyfasm_h_filter_edit   dq 0
    _pyfasm_h_tabs_label    dq 0
    _pyfasm_h_listbox       dq 0
    _pyfasm_h_title_label   dq 0
    _pyfasm_h_meta_label    dq 0
    _pyfasm_h_tags_label    dq 0
    _pyfasm_h_body_edit     dq 0
    _pyfasm_h_ans_header    dq 0
    _pyfasm_h_ans_banner    dq 0
    _pyfasm_h_ans_meta      dq 0
    _pyfasm_h_ans_edit      dq 0
    _pyfasm_h_status        dq 0

    ; Wide Strings for SO Search Pro
    align 8
    wszTrayIconFile         du 'icon.ico', 0
    wszLogoText             du ' SO  Search Pro', 0
    wszSearchDefText        du 'talib', 0
    wszClearBtnText         du 'X', 0
    wszSearchBtnText        du 'Search', 0
    wszFilterDefText        du 'Filter loaded results (by title or tag)...', 0
    wszTabsDefText          du 'English (25)       Russian (4)       Bookmarks (0)', 0
    wszStatusDefText        du 'Loaded question #67061052 with 1 answers     |     API Quota: 296/300  |  Connected  |  v2.1', 0

    ; Questions in list
    align 8
    wszRes1                 du 'talib abstract API vs talib  (^ 0,  [OK] 1 ans,  1.1k views)', 0
    wszRes2                 du 'nodejs talib MACD  (^ 3,  [OK] 3 ans,  6.3k views)', 0
    wszRes3                 du 'Using Talib in AlgoTrader with Esper  (^ 0,  [OK] 1 ans,  1.5k views)', 0
    wszRes4                 du 'How to sort a dictionary by value in Python?  (^ 12.4k,  [OK] 32 ans)', 0

    ; Question 1 Details
    align 8
    wszQTitle1              du 'talib abstract API vs talib', 0
    wszQMeta1               du '^ 0   1,078 views   Apr 12, 2021 11:20   RamA (13 rep)', 0
    wszQTags1               du '[python]   [algorithmic-trading]   [ta-lib]   [candlesticks]', 0
    wszQBody1               du 'Why talib.abstract does not cover all functions on talib? examples would be ''CDL3BLACKCROWS'' which is available in talib but not in talib.abstract.', 13, 10, 13, 10, 'How can I add CDL3BLACKCROWS to talib.abstract?', 0
    wszAnsHead1             du 'Answers (1)', 0
    wszAnsBan1              du '[ACCEPTED SOLUTION]  * Verified and accepted by the question author', 0
    wszAnsMeta1             du 'Answer #1   ^ 0   by truf (3,129 rep) * Apr 13, 2021 07:01', 0
    wszAnsBody1             du 'In ta-lib, candlestick pattern functions like CDL3BLACKCROWS take open, high, low, close series inputs directly.', 13, 10, 13, 10, 'Using ta-lib Function API:', 13, 10, '    from talib import abstract', 13, 10, '    fn = abstract.Function(''CDL3BLACKCROWS'')', 13, 10, '    res = fn(inputs)', 0

    ; Question 2 Details
    align 8
    wszQTitle2              du 'nodejs talib MACD', 0
    wszQMeta2               du '^ 3   6.3k views   Aug 23, 2015 14:10   Stefano Piovesan', 0
    wszQTags2               du '[node.js]   [finance]   [google-finance]   [talib]', 0
    wszQBody2               du 'I am using talib technical analysis library in Node.js to calculate MACD. I used AAPL data to calculate MACD(8, 17, 9) but values differ from Python talib.', 0
    wszAnsHead2             du 'Answers (1)', 0
    wszAnsBan2              du '[ACCEPTED SOLUTION]  * Verified and accepted by author', 0
    wszAnsMeta2             du 'Answer #1   ^ 5   by trader_pro (8,410 rep) * Aug 23, 2015', 0
    wszAnsBody2             du 'Check whether your input prices are Close prices or Typical prices, and make sure EMA periods match standard 12, 26, 9.', 0

    ; Question 3 Details
    align 8
    wszQTitle3              du 'Using Talib in AlgoTrader with Esper', 0
    wszQMeta3               du '^ 0   1.5k views   Feb 12, 2014   Nema Tikaja', 0
    wszQTags3               du '[java]   [python]   [eclipse]   [talib]', 0
    wszQBody3               du 'I have installed the open source version of AlgoTrader and I am working on integrating Talib technical indicators with Esper CEP engine.', 0
    wszAnsHead3             du 'Answers (1)', 0
    wszAnsBan3              du '[ACCEPTED SOLUTION]', 0
    wszAnsMeta3             du 'Answer #1   ^ 2   by AlgoDev (4,120 rep) * Feb 13, 2014', 0
    wszAnsBody3             du 'Talib indicators can be registered as user-defined functions (UDF) in Esper EPL configuration.', 0

    ; Question 4 Details
    align 8
    wszQTitle4              du 'How to sort a dictionary by value in Python?', 0
    wszQMeta4               du '^ 12,450   3.8M views   Sep 14, 2008   dev_guru', 0
    wszQTags4               du '[python]   [dictionary]   [sorting]', 0
    wszQBody4               du 'I have a dictionary of values and I want to sort the keys by their values. How can I do this cleanly in modern Python?', 0
    wszAnsHead4             du 'Answers (2)', 0
    wszAnsBan4              du '[ACCEPTED SOLUTION]  * Verified and accepted by community', 0
    wszAnsMeta4             du 'Answer #1   ^ 15,200   by core_py (84,200 rep) * Sep 14, 2008', 0
    wszAnsBody4             du 'In Python 3.7+, dictionaries maintain insertion order. Use dict(sorted(d.items(), key=lambda item: item[1])):', 13, 10, 13, 10, '    sorted_dict = dict(sorted(x.items(), key=lambda item: item[1]))', 0

    ; System Tray Data structures for Background Apps (Punto Switcher)
    align 8
    _pyfasm_tray_hwnd       dq 0
    _pyfasm_tray_nid        rb 1024 ; NOTIFYICONDATAW (976 bytes on Win64)
    _pyfasm_tray_wc         rb 80   ; WNDCLASSEXW
    _pyfasm_tray_enabled    dd 1
    _pyfasm_tray_sound      dd 1
    align 8
    _pyfasm_cursor_pt       rq 2    ; POINT (x, y)
    wszTrayTipOn            du 'Punto Switcher (Auto-switch: ON)', 0
    wszTrayTipOff           du 'Punto Switcher (Auto-switch: OFF)', 0
    wszMenuAuto             du 'Auto-switch', 0
    wszMenuSound            du 'Sound notification', 0
    wszMenuHotkey           du 'Manual Switch: Pause/Break or F8', 0
    wszMenuExit             du 'Exit', 0
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

    mov     ecx, 002480F4h          ; #F48024 (Stack Overflow Orange)
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_orange], rax

    mov     ecx, 000B67DAh          ; #DA670B (Pressed Orange)
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_orange_press], rax

    ; Create Modern GDI Pens for button borders
    xor     ecx, ecx
    mov     edx, 2                  ; 2px vibrant orange outline
    mov     r8d, 003C92FBh          ; #FB923C (Orange Border)
    call    [CreatePen]
    mov     [_pyfasm_hpen_orange], rax

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
    mov     rcx, -14                ; nHeight = 14
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 400   ; FW_NORMAL
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1     ; DEFAULT_CHARSET
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5     ; CLEARTYPE_QUALITY
    mov     qword [rsp + 96], 0
    lea     rax, [wszSegoeUI]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_h_font_ui], rax
    mov     [_pyfasm_h_font], rax

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
    mov     qword [_pyfasm_wc + 32], 0      ; hIcon
    mov     qword [_pyfasm_wc + 40], r11    ; hCursor (IDC_ARROW)
    mov     rax, [_pyfasm_hbr_bg]
    mov     qword [_pyfasm_wc + 48], rax    ; hbrBackground = solid dark brush!
    mov     qword [_pyfasm_wc + 56], 0      ; lpszMenuName
    lea     rax, [_pyfasm_wnd_class_w]
    mov     qword [_pyfasm_wc + 64], rax    ; lpszClassName
    mov     qword [_pyfasm_wc + 72], 0      ; hIconSm

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

    ; Determine title
    lea     r8, [_pyfasm_wnd_title_w]

    ; Determine width
    mov     r10, [rsp + 104]
    test    r10, r10
    jnz     .w_ok
    mov     r10, 1420
.w_ok:

    ; CreateWindowExW(0, _pyfasm_wnd_class_w, title, WS_OVERLAPPEDWINDOW | WS_VISIBLE, 40, 40, width, height, 0, 0, hInstance, 0)
    xor     ecx, ecx
    lea     rdx, [_pyfasm_wnd_class_w]
    mov     r9d, 10CF0000h          ; WS_OVERLAPPEDWINDOW | WS_VISIBLE
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

    ; Set DWM Immersive Dark Mode on titlebar
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 20                 ; DWMWA_USE_IMMERSIVE_DARK_MODE
    lea     r8, [_pyfasm_dark_mode_val]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]

    ; Build Modern Split-View Controls if not created yet
    cmp     qword [_pyfasm_h_listbox], 0
    jne     .skip_build_controls

    ; 1. Logo Badge (Modern Orange Header Pill)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszLogoText]
    mov     r9d, 5001000Bh          ; WS_CHILD | WS_VISIBLE | BS_OWNERDRAW
    mov     qword [rsp + 32], 25
    mov     qword [rsp + 40], 18
    mov     qword [rsp + 48], 150
    mov     qword [rsp + 56], 34
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 901
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_logo], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; 2. Search Input
    xor     ecx, ecx                ; Flat border (no 3D white bevel)
    lea     rdx, [szEditClassW]
    lea     r8, [wszSearchDefText]
    mov     r9d, 50810080h          ; WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL
    mov     qword [rsp + 32], 185
    mov     qword [rsp + 40], 18
    mov     qword [rsp + 48], 680
    mov     qword [rsp + 56], 34
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 100
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_search_edit], rax
    mov     [_pyfasm_last_edit_hwnd], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 3. Clear Button (Owner-drawn dark button with ✕)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszClearBtnText]
    mov     r9d, 5001000Bh          ; WS_CHILD | WS_VISIBLE | BS_OWNERDRAW
    mov     qword [rsp + 32], 875
    mov     qword [rsp + 40], 18
    mov     qword [rsp + 48], 40
    mov     qword [rsp + 56], 34
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1002
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_clear_btn], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 4. Search Button (Owner-drawn vibrant Stack Overflow orange button)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszSearchBtnText]
    mov     r9d, 5001000Bh          ; WS_CHILD | WS_VISIBLE | BS_OWNERDRAW
    mov     qword [rsp + 32], 925
    mov     qword [rsp + 40], 18
    mov     qword [rsp + 48], 90
    mov     qword [rsp + 56], 34
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1001
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_search_btn], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; 5. Filter Input (Left Column)
    xor     ecx, ecx
    lea     rdx, [szEditClassW]
    lea     r8, [wszFilterDefText]
    mov     r9d, 50810080h
    mov     qword [rsp + 32], 25
    mov     qword [rsp + 40], 70
    mov     qword [rsp + 48], 460
    mov     qword [rsp + 56], 30
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 101
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_filter_edit], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 6. Tabs Label
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszTabsDefText]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 25
    mov     qword [rsp + 40], 108
    mov     qword [rsp + 48], 460
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 902
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_tabs_label], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 7. ListBox (Left Column) - Owner-Drawn Question Cards
    xor     ecx, ecx
    lea     rdx, [szListBoxClassW]
    xor     r8, r8
    mov     r9d, 50200151h          ; WS_CHILD | WS_VISIBLE | WS_VSCROLL | LBS_NOTIFY | LBS_OWNERDRAWFIXED | LBS_HASSTRINGS | LBS_NOINTEGRALHEIGHT
    mov     qword [rsp + 32], 25
    mov     qword [rsp + 40], 136
    mov     qword [rsp + 48], 460
    mov     qword [rsp + 56], 660
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 3001
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_listbox], rax
    mov     [_pyfasm_last_list_hwnd], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Configure 78px card height
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 1A0h               ; LB_SETITEMHEIGHT
    xor     r8d, r8d
    mov     r9d, 78
    call    [SendMessageW]

    ; Populate Initial ListBox Items
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 180h               ; LB_ADDSTRING
    xor     r8d, r8d
    lea     r9, [wszRes1]
    call    [SendMessageW]

    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 180h
    xor     r8d, r8d
    lea     r9, [wszRes2]
    call    [SendMessageW]

    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 180h
    xor     r8d, r8d
    lea     r9, [wszRes3]
    call    [SendMessageW]

    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 180h
    xor     r8d, r8d
    lea     r9, [wszRes4]
    call    [SendMessageW]

    ; Select Item 0
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h               ; LB_SETCURSEL
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]

    ; 8. Question Details Title (Right Column)
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszQTitle1]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 70
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 30
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 903
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_title_label], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 9. Question Meta
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszQMeta1]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 104
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 904
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_meta_label], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 10. Tags
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszQTags1]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 134
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 905
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_tags_label], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 11. Question Body Multiline Edit
    xor     ecx, ecx                ; Flat border (no 3D white bevel)
    lea     rdx, [szEditClassW]
    lea     r8, [wszQBody1]
    mov     r9d, 50810844h          ; WS_CHILD | WS_VISIBLE | WS_BORDER | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 164
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 150
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 906
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_body_edit], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 12. Answers Header
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszAnsHead1]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 330
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 28
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 907
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_ans_header], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 13. Answers Banner
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszAnsBan1]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 362
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 26
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 908
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_ans_banner], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 14. Answer Meta
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszAnsMeta1]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 394
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 909
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_ans_meta], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 15. Answer Body Multiline Edit
    xor     ecx, ecx                ; Flat border (no 3D white bevel)
    lea     rdx, [szEditClassW]
    lea     r8, [wszAnsBody1]
    mov     r9d, 50810844h          ; WS_CHILD | WS_VISIBLE | WS_BORDER | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 424
    mov     qword [rsp + 48], 870
    mov     qword [rsp + 56], 372
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 910
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_ans_edit], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 16. Bottom Status Bar
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszStatusDefText]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 25
    mov     qword [rsp + 40], 816
    mov     qword [rsp + 48], 1350
    mov     qword [rsp + 56], 28
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 911
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_status], rax
    mov     [_pyfasm_last_label_hwnd], rax
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

.skip_build_controls:
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
    lea     rdx, [szStaticClassW]
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
    call    [CreateWindowExW]
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
    lea     rdx, [szEditClassW]
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
    call    [CreateWindowExW]
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
    lea     rdx, [szButtonClassW]
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
    call    [CreateWindowExW]
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
    lea     rdx, [szListBoxClassW]
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
    call    [CreateWindowExW]
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
    call    [GetWindowTextW]
    mov     rax, [rsp + 32]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_set_text:
    ; RCX = hwnd, RDX = text (ANSI string from Python code)
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
    ; RCX = hwnd, RDX = text (ANSI string from Python code)
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
    call    [SendMessageW]
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
    call    [GetMessageW]
    test    eax, eax
    jle     .msg_loop_done

    lea     rcx, [_pyfasm_msg]
    call    [TranslateMessage]

    lea     rcx, [_pyfasm_msg]
    call    [DispatchMessageW]
    jmp     .start_msg_loop

.msg_loop_done:
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
    sub     rsp, 80
    and     rsp, -16

    mov     rbx, r8                 ; rbx = HDC or wParam
    mov     rsi, r9                 ; rsi = HWND or lParam

    cmp     edx, 2                  ; WM_DESTROY
    je      .wnd_destroy
    cmp     edx, 14h                ; WM_ERASEBKGND (0x0014)
    je      .wnd_erasebkgnd
    cmp     edx, 2Ch                ; WM_MEASUREITEM (0x002C)
    je      .wnd_measureitem
    cmp     edx, 2Bh                ; WM_DRAWITEM (0x002B)
    je      .wnd_drawitem
    cmp     edx, 111h               ; WM_COMMAND (0x0111)
    je      .wnd_command
    cmp     edx, 138h               ; WM_CTLCOLORSTATIC (0x0138)
    je      .wnd_ctlcolorstatic
    cmp     edx, 133h               ; WM_CTLCOLOREDIT (0x0133)
    je      .wnd_ctlcoloredit
    cmp     edx, 134h               ; WM_CTLCOLORLISTBOX (0x0134)
    je      .wnd_ctlcolorlistbox
    cmp     edx, 135h               ; WM_CTLCOLORBTN (0x0135)
    je      .wnd_ctlcolorbtn
    cmp     edx, 312h               ; WM_HOTKEY (0x0312)
    je      .wnd_hotkey

    call    [DefWindowProcW]
    jmp     .wnd_proc_ret

.wnd_erasebkgnd:
    mov     rcx, [_pyfasm_h_wnd]
    lea     rdx, [_pyfasm_rc_client]
    call    [GetClientRect]

    mov     rcx, rbx                ; rbx = wParam = HDC
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
    mov     rcx, [_pyfasm_hbr_green_pill]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_hpen_green_pill]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_h_font_ui]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_h_font_bold]
    call    [DeleteObject]
    mov     rcx, [_pyfasm_h_font_mono]
    call    [DeleteObject]

    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_drawitem:
    ; rsi = DRAWITEMSTRUCT*
    mov     eax, [rsi + 4]          ; CtlID (+4 on Win64)
    cmp     eax, 1001               ; Search Button
    je      .draw_search_btn
    cmp     eax, 1002               ; Clear Button
    je      .draw_clear_btn
    cmp     eax, 901                ; Logo Badge
    je      .draw_logo_badge
    cmp     eax, 3001               ; ListBox Owner-Drawn Question Cards
    je      .draw_question_card
    call    [DefWindowProcW]
    jmp     .wnd_proc_ret

.wnd_measureitem:
    ; rsi = MEASUREITEMSTRUCT*
    mov     dword [rsi + 16], 78    ; itemHeight = 78px
    mov     eax, 1
    jmp     .wnd_proc_ret

.draw_question_card:
    mov     eax, [rsi + 8]          ; itemID
    cmp     eax, -1
    je      .card_draw_ret

    ; 1. Clear card background
    mov     rcx, [rsi + 32]         ; hDC
    lea     rdx, [rsi + 40]         ; rcItem
    mov     r8, [_pyfasm_hbr_bg]
    call    [FillRect]

    ; 2. Determine selection state
    mov     ecx, [rsi + 16]         ; itemState
    test    ecx, 1                  ; ODS_SELECTED
    jz      .card_normal

.card_selected:
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_card_sel]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_orange]
    call    [SelectObject]
    jmp     .draw_card_rect

.card_normal:
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_card]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_slate]
    call    [SelectObject]

.draw_card_rect:
    mov     rcx, [rsi + 32]
    movsxd  rdx, dword [rsi + 40]
    add     rdx, 4                  ; cardLeft
    movsxd  r8, dword [rsi + 44]
    add     r8, 2                   ; cardTop
    movsxd  r9, dword [rsi + 48]
    sub     r9, 6                   ; cardRight
    movsxd  rax, dword [rsi + 52]
    sub     rax, 3                  ; cardBottom
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 8     ; 8px radius
    mov     qword [rsp + 48], 8
    call    [RoundRect]

    ; 3. Draw Green Score Pill [left+12, top+8, left+72, top+26]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_green_pill]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_green_pill]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    movsxd  rdx, dword [rsi + 40]
    add     rdx, 12
    movsxd  r8, dword [rsi + 44]
    add     r8, 8
    movsxd  r9, dword [rsi + 40]
    add     r9, 72
    movsxd  rax, dword [rsi + 44]
    add     rax, 26
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 4
    mov     qword [rsp + 48], 4
    call    [RoundRect]

    ; Pill text in white
    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh
    call    [SetTextColor]
    mov     rcx, [rsi + 32]
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_ui]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    lea     rdx, [wszPillText]
    mov     r8d, -1
    mov     eax, dword [rsi + 40]
    add     eax, 12
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 8
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 40]
    add     eax, 72
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 44]
    add     eax, 26
    mov     dword [_pyfasm_rc_client + 12], eax
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 825h  ; DT_CENTER | DT_VCENTER | DT_SINGLELINE
    call    [DrawTextW]

    ; 4. Card Title Text
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_bold]
    call    [SelectObject]

    mov     ecx, [rsi + 16]
    test    ecx, 1
    jz      .title_normal
    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh          ; bright white
    call    [SetTextColor]
    jmp     .draw_title_str
.title_normal:
    mov     rcx, [rsi + 32]
    mov     edx, 00E2E8F0h          ; slate white
    call    [SetTextColor]

.draw_title_str:
    mov     rcx, [rsi + 32]
    mov     edx, 1
    call    [SetBkMode]

    ; Title rect: left+12, top+32, right-14, bottom-4
    mov     eax, dword [rsi + 40]
    add     eax, 12
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 32
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 48]
    sub     eax, 14
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 52]
    sub     eax, 4
    mov     dword [_pyfasm_rc_client + 12], eax

    ; Retrieve text for this listbox item
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 189h               ; LB_GETTEXT
    movsxd  r8, dword [rsi + 8]     ; itemID
    lea     r9, [_pyfasm_card_text_buf]
    call    [SendMessageW]

    mov     rcx, [rsi + 32]
    lea     rdx, [_pyfasm_card_text_buf]
    mov     r8d, -1
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 8010h ; DT_LEFT | DT_TOP | DT_WORDBREAK | DT_END_ELLIPSIS
    call    [DrawTextW]

.card_draw_ret:
    mov     eax, 1
    jmp     .wnd_proc_ret

.draw_search_btn:
    ; Clear background behind button to avoid corner artifacts
    mov     rcx, [rsi + 32]         ; hDC
    lea     rdx, [rsi + 40]         ; rcItem
    mov     r8, [_pyfasm_hbr_bg]
    call    [FillRect]

    mov     ecx, [rsi + 16]         ; itemState
    test    ecx, 1                  ; ODS_SELECTED (pressed)
    jz      .btn_orange_norm
    mov     rdx, [_pyfasm_hbr_orange_press]
    jmp     .do_sel_search_br
.btn_orange_norm:
    mov     rdx, [_pyfasm_hbr_orange]
.do_sel_search_br:
    mov     rcx, [rsi + 32]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_orange]
    call    [SelectObject]

    ; Draw rounded button (8px radius)
    mov     rcx, [rsi + 32]
    movsxd  rdx, dword [rsi + 40]
    movsxd  r8, dword [rsi + 44]
    movsxd  r9, dword [rsi + 48]
    movsxd  rax, dword [rsi + 52]
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 8
    mov     qword [rsp + 48], 8
    call    [RoundRect]

    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh          ; white text
    call    [SetTextColor]

    mov     rcx, [rsi + 32]
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_bold]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    lea     rdx, [wszSearchBtnText]
    mov     r8d, -1
    lea     r9, [rsi + 40]          ; rcItem
    mov     qword [rsp + 32], 825h  ; DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX
    call    [DrawTextW]

    mov     eax, 1
    jmp     .wnd_proc_ret

.draw_clear_btn:
    mov     rcx, [rsi + 32]         ; hDC
    lea     rdx, [rsi + 40]         ; rcItem
    mov     r8, [_pyfasm_hbr_bg]
    call    [FillRect]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_card]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_slate]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    movsxd  rdx, dword [rsi + 40]
    movsxd  r8, dword [rsi + 44]
    movsxd  r9, dword [rsi + 48]
    movsxd  rax, dword [rsi + 52]
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 6
    mov     qword [rsp + 48], 6
    call    [RoundRect]

    mov     rcx, [rsi + 32]
    mov     edx, 00CBD5E1h          ; slate light gray
    call    [SetTextColor]

    mov     rcx, [rsi + 32]
    mov     edx, 1
    call    [SetBkMode]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_bold]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    lea     rdx, [wszClearBtnText]
    mov     r8d, -1
    lea     r9, [rsi + 40]
    mov     qword [rsp + 32], 825h
    call    [DrawTextW]

    mov     eax, 1
    jmp     .wnd_proc_ret

.draw_logo_badge:
    mov     rcx, [rsi + 32]         ; hDC
    lea     rdx, [rsi + 40]         ; rcItem
    mov     r8, [_pyfasm_hbr_bg]
    call    [FillRect]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_orange]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_orange]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    movsxd  rdx, dword [rsi + 40]
    movsxd  r8, dword [rsi + 44]
    movsxd  r9, dword [rsi + 48]
    movsxd  rax, dword [rsi + 52]
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 8
    mov     qword [rsp + 48], 8
    call    [RoundRect]

    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh
    call    [SetTextColor]

    mov     rcx, [rsi + 32]
    mov     edx, 1
    call    [SetBkMode]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_bold]
    call    [SelectObject]

    mov     rcx, [rsi + 32]
    lea     rdx, [wszLogoText]
    mov     r8d, -1
    lea     r9, [rsi + 40]
    mov     qword [rsp + 32], 825h
    call    [DrawTextW]

    mov     eax, 1
    jmp     .wnd_proc_ret

.wnd_ctlcolorstatic:
    cmp     rsi, [_pyfasm_h_body_edit]
    je      .ctl_dark_card
    cmp     rsi, [_pyfasm_h_ans_edit]
    je      .ctl_dark_card
    cmp     rsi, [_pyfasm_h_search_edit]
    je      .ctl_dark_input
    cmp     rsi, [_pyfasm_h_filter_edit]
    je      .ctl_dark_input
    cmp     rsi, [_pyfasm_h_ans_banner]
    je      .ctl_green_banner

    ; Default static labels: transparent, light slate text
    mov     rcx, rbx                ; HDC
    mov     edx, 00F1F5F9h          ; light text #f1f5f9
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_bg]
    jmp     .wnd_proc_ret

.ctl_dark_input:
    mov     rcx, rbx                ; HDC
    mov     edx, 00FFFFFFh          ; white text
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 00201614h          ; input bg #141620
    call    [SetBkColor]

    mov     rcx, rbx
    mov     edx, 2                  ; OPAQUE
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_input]
    jmp     .wnd_proc_ret

.ctl_dark_card:
    mov     rcx, rbx                ; HDC
    mov     edx, 00F8FAFCh          ; light white #f8fafc
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 002E1F1Dh          ; card bg #1d1f2e
    call    [SetBkColor]

    mov     rcx, rbx
    mov     edx, 2                  ; OPAQUE
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_card]
    jmp     .wnd_proc_ret

.ctl_green_banner:
    mov     rcx, rbx                ; HDC
    mov     edx, 0050E3A4h          ; green text #a4e350
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 002E1F1Dh          ; card bg #1d1f2e
    call    [SetBkColor]

    mov     rcx, rbx
    mov     edx, 2                  ; OPAQUE
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_card]
    jmp     .wnd_proc_ret

.wnd_ctlcoloredit:
    mov     rcx, rbx                ; HDC
    mov     edx, 00FFFFFFh          ; white text
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 00201614h          ; input bg #141620
    call    [SetBkColor]

    mov     rcx, rbx
    mov     edx, 2                  ; OPAQUE
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_input]
    jmp     .wnd_proc_ret

.wnd_ctlcolorlistbox:
    mov     rcx, rbx                ; HDC
    mov     edx, 00F1F5F9h          ; light text #f1f5f9
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 002E1F1Dh          ; card bg #1d1f2e
    call    [SetBkColor]

    mov     rcx, rbx
    mov     edx, 2                  ; OPAQUE
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_card]
    jmp     .wnd_proc_ret

.wnd_ctlcolorbtn:
    mov     rcx, rbx
    mov     edx, 00FFFFFFh
    call    [SetTextColor]

    mov     rcx, rbx
    mov     edx, 1
    call    [SetBkMode]

    mov     rax, [_pyfasm_hbr_bg]
    jmp     .wnd_proc_ret

.wnd_command:
    ; Check LBN_SELCHANGE (list selection)
    mov     eax, r8d
    shr     eax, 16                 ; HIWORD(wParam)
    cmp     eax, 1                  ; LBN_SELCHANGE
    jne     .check_ctrl_commands

    ; Query selected item in ListBox
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 188h               ; LB_GETCURSEL
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]

    cmp     eax, 0
    je      .sel_item_0
    cmp     eax, 1
    je      .sel_item_1
    cmp     eax, 2
    je      .sel_item_2
    cmp     eax, 3
    je      .sel_item_3
    jmp     .cmd_done

.sel_item_0:
    mov     rcx, [_pyfasm_h_title_label]
    lea     rdx, [wszQTitle1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_meta_label]
    lea     rdx, [wszQMeta1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_tags_label]
    lea     rdx, [wszQTags1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_body_edit]
    lea     rdx, [wszQBody1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_header]
    lea     rdx, [wszAnsHead1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_banner]
    lea     rdx, [wszAnsBan1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_meta]
    lea     rdx, [wszAnsMeta1]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_edit]
    lea     rdx, [wszAnsBody1]
    call    [SetWindowTextW]
    jmp     .cmd_done

.sel_item_1:
    mov     rcx, [_pyfasm_h_title_label]
    lea     rdx, [wszQTitle2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_meta_label]
    lea     rdx, [wszQMeta2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_tags_label]
    lea     rdx, [wszQTags2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_body_edit]
    lea     rdx, [wszQBody2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_header]
    lea     rdx, [wszAnsHead2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_banner]
    lea     rdx, [wszAnsBan2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_meta]
    lea     rdx, [wszAnsMeta2]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_edit]
    lea     rdx, [wszAnsBody2]
    call    [SetWindowTextW]
    jmp     .cmd_done

.sel_item_2:
    mov     rcx, [_pyfasm_h_title_label]
    lea     rdx, [wszQTitle3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_meta_label]
    lea     rdx, [wszQMeta3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_tags_label]
    lea     rdx, [wszQTags3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_body_edit]
    lea     rdx, [wszQBody3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_header]
    lea     rdx, [wszAnsHead3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_banner]
    lea     rdx, [wszAnsBan3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_meta]
    lea     rdx, [wszAnsMeta3]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_edit]
    lea     rdx, [wszAnsBody3]
    call    [SetWindowTextW]
    jmp     .cmd_done

.sel_item_3:
    mov     rcx, [_pyfasm_h_title_label]
    lea     rdx, [wszQTitle4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_meta_label]
    lea     rdx, [wszQMeta4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_tags_label]
    lea     rdx, [wszQTags4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_body_edit]
    lea     rdx, [wszQBody4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_header]
    lea     rdx, [wszAnsHead4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_banner]
    lea     rdx, [wszAnsBan4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_meta]
    lea     rdx, [wszAnsMeta4]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_ans_edit]
    lea     rdx, [wszAnsBody4]
    call    [SetWindowTextW]
    jmp     .cmd_done

.check_ctrl_commands:
    movzx   eax, r8w                ; LOWORD(wParam) = control ID

    ; Check registered dynamic callbacks
    xor     ecx, ecx
    mov     r10, [_pyfasm_ctrl_count]
.cmd_scan:
    cmp     rcx, r10
    jge     .check_stock_cmds
    cmp     eax, dword [_pyfasm_ctrl_ids + rcx*4]
    je      .cmd_found
    inc     rcx
    jmp     .cmd_scan

.cmd_found:
    mov     rax, [_pyfasm_ctrl_callbacks + rcx*8]
    test    rax, rax
    jz      .check_stock_cmds
    mov     rcx, [_pyfasm_last_gui_instance]
    sub     rsp, 32
    call    rax
    add     rsp, 32
    xor     eax, eax
    jmp     .wnd_proc_ret

.check_stock_cmds:
    cmp     eax, 1001               ; Search Button
    je      .action_search
    cmp     eax, 1002               ; Clear Button
    je      .action_clear
    cmp     eax, 1003               ; Copy Question
    je      .action_beep
    cmp     eax, 1004               ; Copy Answer
    je      .action_beep
    jmp     .cmd_done

.action_clear:
    mov     rcx, [_pyfasm_h_search_edit]
    xor     edx, edx
    call    [SetWindowTextW]
    jmp     .cmd_done

.action_search:
    jmp     .sel_item_0

.action_beep:
    mov     ecx, -1
    call    [MessageBeep]
    jmp     .cmd_done

.cmd_done:
    xor     eax, eax
    jmp     .wnd_proc_ret

.wnd_hotkey:
    xor     eax, eax
    jmp     .wnd_proc_ret

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
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     r12
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
    call    [MessageBoxW]
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
            gdi32, 'GDI32.DLL', \\
            shell32, 'SHELL32.DLL', \\
            dwmapi, 'DWMAPI.DLL'

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
           GetCurrentThreadId, 'GetCurrentThreadId', \\
           ExitProcess, 'ExitProcess'

    import user32, \\
           MessageBoxA, 'MessageBoxA', \\
           MessageBoxW, 'MessageBoxW', \\
           RegisterClassExA, 'RegisterClassExA', \\
           RegisterClassExW, 'RegisterClassExW', \\
           CreateWindowExA, 'CreateWindowExA', \\
           CreateWindowExW, 'CreateWindowExW', \\
           ShowWindow, 'ShowWindow', \\
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
           ActivateKeyboardLayout, 'ActivateKeyboardLayout'

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
           GetStockObject, 'GetStockObject'

    import shell32, \\
           Shell_NotifyIconW, 'Shell_NotifyIconW', \\
           Shell_NotifyIconA, 'Shell_NotifyIconA'

    import dwmapi, \\
           DwmSetWindowAttribute, 'DwmSetWindowAttribute'
"""
