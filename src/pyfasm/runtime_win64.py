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

    ; Registry / Dark Detect Data
    _pyfasm_reg_theme_key   db 'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize', 0
    _pyfasm_reg_theme_val   db 'AppsUseLightTheme', 0
    align 4
    _pyfasm_reg_val_data    dd 0
    _pyfasm_reg_val_size    dd 4

    ; WinINet HTTP Client Data
    _pyfasm_http_agent      db 'PyFASM-Native/1.0', 0
    align 4
    _pyfasm_http_read_bytes dd 0
    align 8
    _pyfasm_http_buf        rb 65536 ; 64KB HTTP response buffer

    ; HTML entity stripping buffer
    align 8
    _pyfasm_strip_buf       rb 65536

    ; Theme Strings & Int Buffer
    szDarkStr               db 'Dark', 0
    szLightStr              db 'Light', 0
    align 8
    _pyfasm_int_buf         rb 32

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
    _pyfasm_last_btn_hwnd   dq 0
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
    _pyfasm_wnd_title_w     du 'PyFASM Application', 0
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
    _pyfasm_caption_color   dd 001A110Fh
    _pyfasm_caption_text_color dd 00FFFFFFh
    wszDarkModeExplorer     du 'DarkMode_Explorer', 0
    _pyfasm_split_view_enabled dd 0
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
    wszPillAns1             du '1 ans', 0
    wszPillAns3             du '3 ans', 0
    wszBrandBadge           du 'SO', 0
    wszBrandAppTitle        du 'Search Pro', 0
    wszBtnBothText          du 'Both v', 0
    wszBtnRelText           du 'Relevance v', 0
    wszBtnDarkText          du 'Dark v', 0
    wszLblQuickText         du 'Quick Search:', 0
    wszTabEnText            du 'English (25)', 0
    wszTabRuText            du 'Russian (4)', 0
    wszTabBmText            du 'Bookmarks (0)', 0
    wszChipPyText           du 'python', 0
    wszChipJsText           du 'javascript', 0
    wszChipReactText        du 'react', 0
    wszChipFastText         du 'fastapi', 0
    wszChipAsyncText        du 'asyncio', 0
    wszChipPandasText       du 'pandas', 0
    wszChipDockText         du 'docker', 0
    wszChipCppText          du 'c++', 0
    wszChipRustText         du 'rust', 0
    wszBtnSaveText          du 'Save', 0
    wszBtnCopyQText         du 'Copy Question', 0
    wszBtnCopyLText         du 'Copy Link', 0
    wszBtnBrowseText        du 'Browse', 0
    wszBtnCopyAText         du 'Copy Answer', 0
    wszBtnCopyCText         du 'Copy Code', 0
    wszCodeHdrText          du 'Python - 4 lines                                       Wrap | Copy Code', 0

    ; Rich Question Card 0
    wszCard0Meta            du '^ 0    1.1k views                   Apr 12, 2021', 0
    wszCard0Title           du 'talib abstract API vs talib', 0
    wszCard0Excerpt         du 'Why talib.abstract does not cover all functions on talib? examples would be CDL3BLACKCROWS...', 0
    wszCard0Tags            du '[python]  [algorithmic-trading]  [ta-lib]        RamA', 0

    ; Rich Question Card 1
    wszCard1Meta            du '^ 3    6.3k views                   Aug 23, 2015', 0
    wszCard1Title           du 'nodejs talib MACD', 0
    wszCard1Excerpt         du 'I am using talib technical analysis library in Node.js to calculate MACD. I used AAPL data to calculate MACD...', 0
    wszCard1Tags            du '[node.js]  [finance]  [google-finance]           Stefano Piovesan', 0

    ; Rich Question Card 2
    wszCard2Meta            du '^ 0    1.5k views                   Feb 12, 2014', 0
    wszCard2Title           du 'Using Talib in AlgoTrader with Esper', 0
    wszCard2Excerpt         du 'I have installed the open source version of AlgoTrader and I am working on integrating Talib technical indicators...', 0
    wszCard2Tags            du '[java]  [python]  [eclipse]                      Nema Tikaja', 0

    ; Rich Question Card 3
    wszCard3Meta            du '^ 1    2.5k views                   Nov 02, 2021', 0
    wszCard3Title           du 'import talib - ModuleNotFoundError: No module named talib', 0
    wszCard3Excerpt         du 'I have an issue with TA-Lib import I have created a view for my python project and when I import talib and run...', 0
    wszCard3Tags            du '[python]  [import]  [ta-lib]                     Farhad', 0

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


def _get_win64_full_runtime_code() -> str:
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
    sub     rsp, 48
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
    lea     rax, [_pyfasm_reg_val_data]
    mov     [rsp + 32], rax                ; lpData
    lea     rax, [_pyfasm_reg_val_size]
    mov     [rsp + 40], rax                ; lpcbData
    call    [RegQueryValueExA]

    push    rax
    mov     rcx, [rbp - 8]
    call    [RegCloseKey]
    pop     rax

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
    ; Returns RAX = pointer to null-terminated response buffer (_pyfasm_http_buf)
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx                       ; save URL in rsi

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

    lea     rax, [_pyfasm_http_buf]
    add     rsp, 64
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
    mov     byte [_pyfasm_http_buf], 0
    lea     rax, [_pyfasm_http_buf]
    add     rsp, 64
    pop     rbx
    pop     rdi
    pop     rsi
    mov     rsp, rbp
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

.copy_s1:
    mov     al, [rsi]
    mov     [rdi], al
    test    al, al
    jz      .copy_s2_init
    inc     rsi
    inc     rdi
    jmp     .copy_s1

.copy_s2_init:
.copy_s2:
    mov     al, [rbx]
    mov     [rdi], al
    test    al, al
    jz      .concat_done
    inc     rbx
    inc     rdi
    jmp     .copy_s2

.concat_done:
    mov     rax, [rsp + 40]
    add     rsp, 48
    pop     rbx
    pop     rdi
    pop     rsi
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
    test    rdx, rdx
    jz      .cmp_ne
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
    jb      .lower_store
    cmp     al, 'Z'
    ja      .lower_store
    add     al, 32
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
    jb      .upper_store
    cmp     al, 'z'
    ja      .upper_store
    sub     al, 32
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
    ; RCX = initial capacity (0 = default 16)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    test    rcx, rcx
    jnz     .cap_ok
    mov     rcx, 16
.cap_ok:
    mov     rbx, rcx
    lea     rax, [rbx + rbx * 2]
    shl     rax, 3
    add     rax, 16
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], rbx
    mov     qword [rax + 8], 0
    lea     rdi, [rax + 16]
    lea     rcx, [rbx + rbx * 2]
    shl     rcx, 1
    push    rax
    xor     eax, eax
    rep     stosq
    pop     rax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_hash:
    ; RCX = null-terminated string or 64-bit integer
    ; Returns RAX = 64-bit FNV-1a hash
    test    rcx, rcx
    jz      .hash_zero
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
    jnz     .hash_ret
    mov     rax, 1
    ret
.hash_done:
    test    rax, rax
    jnz     .hash_ret
    mov     rax, 1
.hash_ret:
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
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .dict_set_done
    mov     rbx, rcx
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    dec     r14
    and     rax, r14
    mov     rdi, rax

.dict_probe:
    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dict_slot_empty

    cmp     rax, r13
    jne     .dict_next_slot

    push    rcx
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     rcx
    test    eax, eax
    jnz     .dict_update_val

.dict_next_slot:
    inc     rdi
    and     rdi, r14
    jmp     .dict_probe

.dict_slot_empty:
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
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
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
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
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
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
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
    mov     ecx, 16
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
    ; Returns RAX = pointer to null-terminated string in _pyfasm_int_buf
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi

    lea     rdi, [_pyfasm_int_buf + 30]
    mov     byte [rdi + 1], 0
    mov     rax, rcx

    test    rax, rax
    jnz     .its_check_neg
    mov     byte [rdi], '0'
    mov     rax, rdi
    jmp     .its_done

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
    mov     [rdi], r8b
    dec     rdi
    mov     rax, rdx
    jmp     .its_loop

.its_finish:
    test    ebx, ebx
    jz      .its_pos
    mov     byte [rdi], '-'
    dec     rdi
.its_pos:
    inc     rdi
    mov     rax, rdi

.its_done:
    pop     rdi
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

    ; Determine title dynamically from _pyfasm_wnd_title_ptr if set
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

    ; Build Modern Split-View Controls only if explicitly enabled by project
    cmp     dword [_pyfasm_split_view_enabled], 1
    jne     .skip_build_controls

    ; 1. Brand Logo / Application Icon
    cmp     qword [_pyfasm_h_icon_big], 0
    jz      .create_logo_button_fallback

    ; Static icon control inside app header: 32x32 at (20, 14)
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    xor     r8, r8
    mov     r9d, 50000003h          ; WS_CHILD | WS_VISIBLE | SS_ICON
    mov     qword [rsp + 32], 20
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 32
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 901
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_logo], rax
    mov     rcx, rax
    mov     edx, 170h               ; STM_SETICON (0x0170)
    mov     r8, [_pyfasm_h_icon_big]
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .logo_ctrl_done

.create_logo_button_fallback:
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBrandBadge]
    mov     r9d, 5001000Bh          ; WS_CHILD | WS_VISIBLE | BS_OWNERDRAW
    mov     qword [rsp + 32], 20
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 34
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 901
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_logo], rax
.logo_ctrl_done:

    ; 1b. App Title "Search Pro" (Bold White Static Label)
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszBrandAppTitle]
    mov     r9d, 50000000h          ; WS_CHILD | WS_VISIBLE
    mov     qword [rsp + 32], 58
    mov     qword [rsp + 40], 16
    mov     qword [rsp + 48], 115
    mov     qword [rsp + 56], 28
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 905
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_title]
    mov     r9d, 1
    call    [SendMessageW]

    ; 2. Search Input Box
    xor     ecx, ecx
    lea     rdx, [szEditClassW]
    lea     r8, [wszSearchDefText]
    mov     r9d, 50810080h          ; WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL
    mov     qword [rsp + 32], 180
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 460
    mov     qword [rsp + 56], 32
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

    ; 3. Clear Button (X)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszClearBtnText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 665
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 34
    mov     qword [rsp + 56], 32
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

    ; 3b. Dropdown Pill 1 "Both v"
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnBothText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 705
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 85
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1003
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 3c. Dropdown Pill 2 "Relevance v"
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnRelText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 796
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 115
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1004
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 4. Search Button (Vibrant Orange)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszSearchBtnText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 918
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 95
    mov     qword [rsp + 56], 32
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

    ; 4b. Theme Pill "Dark v"
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnDarkText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 1020
    mov     qword [rsp + 40], 14
    mov     qword [rsp + 48], 85
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1005
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; 4c. Quick Search Chips Row (y = 56)
    xor     ecx, ecx
    lea     rdx, [szStaticClassW]
    lea     r8, [wszLblQuickText]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 20
    mov     qword [rsp + 40], 56
    mov     qword [rsp + 48], 105
    mov     qword [rsp + 56], 20
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 906
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     rdx, 30h
    mov     r8, [_pyfasm_h_font_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Chip 0: python (x=130, y=54, w=58, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipPyText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 130
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 58
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1020
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 1: javascript (x=194, y=54, w=80, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipJsText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 194
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 80
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1021
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 2: react (x=280, y=54, w=52, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipReactText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 280
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 52
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1022
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 3: fastapi (x=338, y=54, w=58, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipFastText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 338
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 58
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1023
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 4: asyncio (x=402, y=54, w=58, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipAsyncText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 402
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 58
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1024
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 5: pandas (x=466, y=54, w=58, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipPandasText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 466
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 58
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1025
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 6: docker (x=530, y=54, w=58, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipDockText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 530
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 58
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1026
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 7: c++ (x=594, y=54, w=44, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipCppText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 594
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 44
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1027
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Chip 8: rust (x=644, y=54, w=46, h=24)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszChipRustText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 644
    mov     qword [rsp + 40], 54
    mov     qword [rsp + 48], 46
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1028
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; 5. Filter Input (y = 86)
    xor     ecx, ecx
    lea     rdx, [szEditClassW]
    lea     r8, [wszFilterDefText]
    mov     r9d, 50810080h
    mov     qword [rsp + 32], 20
    mov     qword [rsp + 40], 86
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

    ; 6. Segmented Language Tabs (y = 122)
    ; Tab 1: English (25) - Active Orange Tab
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszTabEnText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 20
    mov     qword [rsp + 40], 122
    mov     qword [rsp + 48], 118
    mov     qword [rsp + 56], 28
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1010
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Tab 2: Russian (4)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszTabRuText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 144
    mov     qword [rsp + 40], 122
    mov     qword [rsp + 48], 112
    mov     qword [rsp + 56], 28
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1011
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Tab 3: Bookmarks (0)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszTabBmText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 262
    mov     qword [rsp + 40], 122
    mov     qword [rsp + 48], 125
    mov     qword [rsp + 56], 28
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1012
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; 7. ListBox (Left Column) - Owner-Drawn Question Cards
    xor     ecx, ecx
    lea     rdx, [szListBoxClassW]
    xor     r8, r8
    mov     r9d, 50200151h          ; WS_CHILD | WS_VISIBLE | WS_VSCROLL | LBS_NOTIFY | LBS_OWNERDRAWFIXED | LBS_HASSTRINGS | LBS_NOINTEGRALHEIGHT
    mov     qword [rsp + 32], 20
    mov     qword [rsp + 40], 160
    mov     qword [rsp + 48], 460
    mov     qword [rsp + 56], 645
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

    ; Configure 102px card height
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 1A0h               ; LB_SETITEMHEIGHT
    xor     r8d, r8d
    mov     r9d, 102
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
    mov     r8, [_pyfasm_h_font_title]
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

    ; 9b. Action Toolbar (y = 132)
    ; Button: Save (x=505)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnSaveText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 505
    mov     qword [rsp + 40], 132
    mov     qword [rsp + 48], 68
    mov     qword [rsp + 56], 26
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1030
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Button: Copy Question (x=580)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnCopyQText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 580
    mov     qword [rsp + 40], 132
    mov     qword [rsp + 48], 115
    mov     qword [rsp + 56], 26
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1031
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Button: Copy Link (x=702)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnCopyLText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 702
    mov     qword [rsp + 40], 132
    mov     qword [rsp + 48], 90
    mov     qword [rsp + 56], 26
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1032
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; Button: Browse (x=1305)
    xor     ecx, ecx
    lea     rdx, [szButtonClassW]
    lea     r8, [wszBtnBrowseText]
    mov     r9d, 5001000Bh
    mov     qword [rsp + 32], 1305
    mov     qword [rsp + 40], 132
    mov     qword [rsp + 48], 70
    mov     qword [rsp + 56], 26
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1033
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]

    ; 10. Tags (y = 166)
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
    mov     r8, [_pyfasm_h_font_mono]
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

    ; If modern split-view is active and label is targeted at header (y < 60),
    ; avoid creating overlapping duplicate controls over the header bar
    cmp     qword [_pyfasm_h_listbox], 0
    jz      .do_create_label_body
    cmp     qword [rsp + 80], 60
    jae     .do_create_label_body
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret
.do_create_label_body:
    mov     rax, [rbp + 48]
    test    rax, rax
    jnz     .lbl_h_ok
    mov     rax, 25
.lbl_h_ok:
    mov     [rsp + 64], rax

    call    _pyfasm_ensure_window

    mov     rcx, [rsp + 96]
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

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
    lea     r8, [_pyfasm_wide_buf]
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

    ; Check if search edit already created in split view
    cmp     qword [rsp + 56], 101       ; Search Entry ID
    jne     .chk_filter_id
    cmp     qword [_pyfasm_h_search_edit], 0
    jz      .do_create_edt
    mov     rax, [_pyfasm_h_search_edit]
    mov     rsp, rbp
    pop     rbp
    ret

.chk_filter_id:
    cmp     qword [rsp + 56], 102       ; Filter Entry ID
    jne     .do_create_edt
    cmp     qword [_pyfasm_h_filter_edit], 0
    jz      .do_create_edt
    mov     rax, [_pyfasm_h_filter_edit]
    mov     rsp, rbp
    pop     rbp
    ret

.do_create_edt:
    mov     rcx, [rsp + 96]
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

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
    lea     r8, [_pyfasm_wide_buf]
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

    ; Check if Search or Clear button already created
    cmp     qword [rsp + 56], 1001      ; Search Button ID
    jne     .chk_clear_id
    cmp     qword [_pyfasm_h_search_btn], 0
    jz      .do_create_btn
    mov     rax, [_pyfasm_h_search_btn]
    mov     rsp, rbp
    pop     rbp
    ret

.chk_clear_id:
    cmp     qword [rsp + 56], 1002      ; Clear Button ID
    jne     .do_create_btn
    cmp     qword [_pyfasm_h_clear_btn], 0
    jz      .do_create_btn
    mov     rax, [_pyfasm_h_clear_btn]
    mov     rsp, rbp
    pop     rbp
    ret

.do_create_btn:
    mov     rcx, [rsp + 96]
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

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
    lea     r8, [_pyfasm_wide_buf]
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
    mov     [_pyfasm_last_btn_hwnd], rax
    mov     rcx, rax
    call    _pyfasm_apply_font

    mov     rax, [_pyfasm_last_btn_hwnd]
    mov     rsp, rbp
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

    ; If main listbox already exists, reuse it to prevent huge gray overlapping rectangle!
    cmp     qword [_pyfasm_h_listbox], 0
    jz      .do_create_lb
    mov     rax, [_pyfasm_h_listbox]
    mov     rsp, rbp
    pop     rbp
    ret

.do_create_lb:
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
    mov     rsi, rcx
    mov     rcx, rdx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    call    [SetWindowTextW]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_listbox_add:
    ; RCX = hwnd, RDX = text (UTF-8 string from Python code)
    push    rbp
    mov     rbp, rsp
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jnz     .la_hwnd_ok
    mov     rcx, [_pyfasm_last_list_hwnd]
    test    rcx, rcx
    jnz     .la_hwnd_ok
    mov     rcx, [_pyfasm_h_listbox]
.la_hwnd_ok:
    mov     rsi, rcx
    mov     rcx, rdx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide

    mov     rcx, rsi
    mov     edx, 180h               ; LB_ADDSTRING
    xor     r8d, r8d
    lea     r9, [_pyfasm_wide_buf]
    call    [SendMessageW]
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
    mov     rcx, [_pyfasm_h_font_title]
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
    jmp     .draw_pill_button

.wnd_measureitem:
    ; rsi = MEASUREITEMSTRUCT*
    mov     dword [rsi + 16], 102   ; itemHeight = 102px
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

    ; 3. Draw Green Score Pill [left+12, top+8, left+68, top+24]
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
    add     r9, 68
    movsxd  rax, dword [rsi + 44]
    add     rax, 24
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 4
    mov     qword [rsp + 48], 4
    call    [RoundRect]

    ; Pill text in white (e.g. "1 ans")
    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh
    call    [SetTextColor]
    mov     rcx, [rsi + 32]
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_bold]
    call    [SelectObject]

    mov     eax, dword [rsi + 8]    ; itemID
    cmp     eax, 1
    je      .ans_is_3
    lea     rdx, [wszPillAns1]
    jmp     .draw_pill_lbl
.ans_is_3:
    lea     rdx, [wszPillAns3]
.draw_pill_lbl:
    mov     rcx, [rsi + 32]
    mov     r8d, -1
    mov     eax, dword [rsi + 40]
    add     eax, 12
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 8
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 40]
    add     eax, 68
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 44]
    add     eax, 24
    mov     dword [_pyfasm_rc_client + 12], eax
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 825h  ; DT_CENTER | DT_VCENTER | DT_SINGLELINE
    call    [DrawTextW]

    ; Line 1: Meta text (Score, Views, Date) [left+74, top+7, right-14, top+24]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_ui]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     edx, 0094A3B8h          ; #B8A394 slate
    call    [SetTextColor]

    mov     eax, dword [rsi + 8]    ; itemID
    cmp     eax, 0
    je      .meta_0
    cmp     eax, 1
    je      .meta_1
    cmp     eax, 2
    je      .meta_2
    lea     rdx, [wszCard3Meta]
    jmp     .draw_card_meta
.meta_0:
    lea     rdx, [wszCard0Meta]
    jmp     .draw_card_meta
.meta_1:
    lea     rdx, [wszCard1Meta]
    jmp     .draw_card_meta
.meta_2:
    lea     rdx, [wszCard2Meta]
.draw_card_meta:
    mov     rcx, [rsi + 32]
    mov     r8d, -1
    mov     eax, dword [rsi + 40]
    add     eax, 74
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 7
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 48]
    sub     eax, 14
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 44]
    add     eax, 24
    mov     dword [_pyfasm_rc_client + 12], eax
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 820h  ; DT_LEFT | DT_VCENTER | DT_SINGLELINE
    call    [DrawTextW]

    ; Line 2: Card Title Text (Bold White) [left+12, top+28, right-14, top+48]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_bold]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh          ; pure white
    call    [SetTextColor]

    mov     eax, dword [rsi + 8]
    cmp     eax, 0
    je      .title_0
    cmp     eax, 1
    je      .title_1
    cmp     eax, 2
    je      .title_2
    lea     rdx, [wszCard3Title]
    jmp     .draw_title_str
.title_0:
    lea     rdx, [wszCard0Title]
    jmp     .draw_title_str
.title_1:
    lea     rdx, [wszCard1Title]
    jmp     .draw_title_str
.title_2:
    lea     rdx, [wszCard2Title]
.draw_title_str:
    mov     rcx, [rsi + 32]
    mov     r8d, -1
    mov     eax, dword [rsi + 40]
    add     eax, 12
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 28
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 48]
    sub     eax, 14
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 44]
    add     eax, 48
    mov     dword [_pyfasm_rc_client + 12], eax
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 820h  ; DT_LEFT | DT_VCENTER | DT_SINGLELINE
    call    [DrawTextW]

    ; Line 3: Excerpt Text (Slate) [left+12, top+50, right-14, top+70]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_ui]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     edx, 00CBD5E1h          ; slate light gray
    call    [SetTextColor]

    mov     eax, dword [rsi + 8]
    cmp     eax, 0
    je      .ex_0
    cmp     eax, 1
    je      .ex_1
    cmp     eax, 2
    je      .ex_2
    lea     rdx, [wszCard3Excerpt]
    jmp     .draw_ex_str
.ex_0:
    lea     rdx, [wszCard0Excerpt]
    jmp     .draw_ex_str
.ex_1:
    lea     rdx, [wszCard1Excerpt]
    jmp     .draw_ex_str
.ex_2:
    lea     rdx, [wszCard2Excerpt]
.draw_ex_str:
    mov     rcx, [rsi + 32]
    mov     r8d, -1
    mov     eax, dword [rsi + 40]
    add     eax, 12
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 50
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 48]
    sub     eax, 14
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 44]
    add     eax, 70
    mov     dword [_pyfasm_rc_client + 12], eax
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 820h  ; DT_LEFT | DT_VCENTER | DT_SINGLELINE
    call    [DrawTextW]

    ; Line 4: Tags and Author [left+12, top+74, right-14, top+94]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_ui]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     edx, 00F8BD38h          ; #38BDF8 cyan text for tags!
    call    [SetTextColor]

    mov     eax, dword [rsi + 8]
    cmp     eax, 0
    je      .tag_0
    cmp     eax, 1
    je      .tag_1
    cmp     eax, 2
    je      .tag_2
    lea     rdx, [wszCard3Tags]
    jmp     .draw_tag_str
.tag_0:
    lea     rdx, [wszCard0Tags]
    jmp     .draw_tag_str
.tag_1:
    lea     rdx, [wszCard1Tags]
    jmp     .draw_tag_str
.tag_2:
    lea     rdx, [wszCard2Tags]
.draw_tag_str:
    mov     rcx, [rsi + 32]
    mov     r8d, -1
    mov     eax, dword [rsi + 40]
    add     eax, 12
    mov     dword [_pyfasm_rc_client], eax
    mov     eax, dword [rsi + 44]
    add     eax, 74
    mov     dword [_pyfasm_rc_client + 4], eax
    mov     eax, dword [rsi + 48]
    sub     eax, 14
    mov     dword [_pyfasm_rc_client + 8], eax
    mov     eax, dword [rsi + 44]
    add     eax, 94
    mov     dword [_pyfasm_rc_client + 12], eax
    lea     r9, [_pyfasm_rc_client]
    mov     qword [rsp + 32], 820h  ; DT_LEFT | DT_VCENTER | DT_SINGLELINE
    call    [DrawTextW]

.card_draw_ret:
    mov     eax, 1
    jmp     .wnd_proc_ret

.draw_pill_button:
    ; 1. Clear background
    mov     rcx, [rsi + 32]         ; hDC
    lea     rdx, [rsi + 40]         ; rcItem
    mov     r8, [_pyfasm_hbr_bg]
    call    [FillRect]

    ; 2. Choose brush & pen based on CtlID
    mov     eax, [rsi + 4]          ; CtlID
    cmp     eax, 1010               ; Selected Tab: English (25)
    je      .pill_orange

    ; Default dark pill button
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_card]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_slate]
    call    [SelectObject]
    jmp     .do_draw_pill_shape

.pill_orange:
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hbr_orange]
    call    [SelectObject]
    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_hpen_orange]
    call    [SelectObject]

.do_draw_pill_shape:
    mov     rcx, [rsi + 32]
    movsxd  rdx, dword [rsi + 40]
    movsxd  r8, dword [rsi + 44]
    movsxd  r9, dword [rsi + 48]
    movsxd  rax, dword [rsi + 52]
    mov     qword [rsp + 32], rax
    mov     qword [rsp + 40], 6
    mov     qword [rsp + 48], 6
    call    [RoundRect]

    ; 3. Choose text color
    mov     eax, [rsi + 4]
    cmp     eax, 1010               ; Orange tab -> white text
    je      .pill_txt_white
    cmp     eax, 1020
    jb      .pill_txt_slate
    cmp     eax, 1028
    jbe     .pill_txt_cyan          ; Chips 1020..1028 -> cyan text

.pill_txt_slate:
    mov     rcx, [rsi + 32]
    mov     edx, 00CBD5E1h          ; slate light text
    call    [SetTextColor]
    jmp     .do_draw_pill_text

.pill_txt_cyan:
    mov     rcx, [rsi + 32]
    mov     edx, 00F8BD38h          ; #38BDF8 cyan
    call    [SetTextColor]
    jmp     .do_draw_pill_text

.pill_txt_white:
    mov     rcx, [rsi + 32]
    mov     edx, 00FFFFFFh          ; pure white
    call    [SetTextColor]

.do_draw_pill_text:
    mov     rcx, [rsi + 32]
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]

    mov     rcx, [rsi + 32]
    mov     rdx, [_pyfasm_h_font_ui]
    call    [SelectObject]

    ; Get button text directly from window
    mov     rcx, [rsi + 24]         ; hwndItem
    lea     rdx, [_pyfasm_card_text_buf]
    mov     r8d, 256
    call    [GetWindowTextW]

    mov     rcx, [rsi + 32]
    lea     rdx, [_pyfasm_card_text_buf]
    mov     r8d, -1
    lea     r9, [rsi + 40]
    mov     qword [rsp + 32], 825h  ; DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX
    call    [DrawTextW]

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
    lea     rdx, [wszBrandBadge]
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

    ; Language / Bookmarks Tabs (1010..1012)
    cmp     eax, 1010
    je      .sel_item_0
    cmp     eax, 1011
    je      .sel_item_2
    cmp     eax, 1012
    je      .sel_item_3

    ; Quick Search Chips (1020..1028)
    cmp     eax, 1020
    jb      .cmd_done
    cmp     eax, 1028
    ja      .cmd_done

    cmp     eax, 1020
    je      .chip_py
    cmp     eax, 1021
    je      .chip_js
    cmp     eax, 1022
    je      .chip_react
    cmp     eax, 1023
    je      .chip_fast
    cmp     eax, 1024
    je      .chip_async
    cmp     eax, 1025
    je      .chip_pandas
    cmp     eax, 1026
    je      .chip_docker
    cmp     eax, 1027
    je      .chip_cpp
    cmp     eax, 1028
    je      .chip_rust
    jmp     .cmd_done

.chip_py:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipPyText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_0

.chip_js:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipJsText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    mov     r8d, 1
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_1

.chip_react:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipReactText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    mov     r8d, 1
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_1

.chip_fast:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipFastText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    mov     r8d, 3
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_3

.chip_async:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipAsyncText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_0

.chip_pandas:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipPandasText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    mov     r8d, 3
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_3

.chip_docker:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipDockText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    mov     r8d, 2
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_2

.chip_cpp:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipCppText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    mov     r8d, 2
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_2

.chip_rust:
    mov     rcx, [_pyfasm_h_search_edit]
    lea     rdx, [wszChipRustText]
    call    [SetWindowTextW]
    mov     rcx, [_pyfasm_h_listbox]
    mov     edx, 186h
    xor     r8d, r8d
    xor     r9d, r9d
    call    [SendMessageW]
    jmp     .sel_item_0

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

_pyfasm_str_slice:
    ; RCX = str pointer, RDX = lower, R8 = upper, R9 = step
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
    jz      .ss_null

    mov     rsi, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     r14, r9

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     r15, rax

    test    r14, r14
    jnz     .check_step
    mov     r14, 1
.check_step:
    cmp     r14, -1
    jne     .fwd_slice

    mov     rcx, r15
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     r10, rax

    mov     rcx, r15
    test    rcx, rcx
    jz      .rev_done

    lea     rbx, [rsi + r15 - 1]
.rev_loop:
    mov     al, [rbx]
    mov     [rdi], al
    inc     rdi
    dec     rbx
    dec     rcx
    jnz     .rev_loop
.rev_done:
    mov     byte [rdi], 0
    mov     rax, r10
    jmp     .ss_exit

.fwd_slice:
    cmp     r12, 0
    jge     .l_pos
    add     r12, r15
    cmp     r12, 0
    jge     .l_pos
    xor     r12, r12
.l_pos:
    cmp     r12, r15
    jle     .l_clamp
    mov     r12, r15
.l_clamp:
    cmp     r13, -999999
    jne     .chk_u_neg
    mov     r13, r15
    jmp     .u_clamp
.chk_u_neg:
    cmp     r13, 0
    jge     .u_pos
    add     r13, r15
    cmp     r13, 0
    jge     .u_pos
    xor     r13, r13
.u_pos:
    cmp     r13, r15
    jle     .u_clamp
    mov     r13, r15
.u_clamp:
    mov     rax, r13
    sub     rax, r12
    jge     .sl_ok
    xor     eax, eax
.sl_ok:
    mov     rbx, rax

    mov     rcx, rbx
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     r10, rax

    test    rbx, rbx
    jz      .copy_done
    lea     rsi, [rsi + r12]
    mov     rcx, rbx
    rep     movsb
.copy_done:
    mov     byte [rdi], 0
    mov     rax, r10
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
           CreateThread, 'CreateThread', \\
           WaitForSingleObject, 'WaitForSingleObject', \\
           CloseHandle, 'CloseHandle', \\
           GetModuleHandleA, 'GetModuleHandleA', \\
           MultiByteToWideChar, 'MultiByteToWideChar', \\
           WideCharToMultiByte, 'WideCharToMultiByte', \\
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
           ShowWindow, 'ShowWindow', \
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
    flt_1m          dq 1000000.0
    flt_zero        dq 0.0
    align 8
    _pyfasm_int_buf rb 32
"""

_WIN64_NET_RUNTIME_DATA = """
    ; WinINet HTTP Client Data
    _pyfasm_http_agent      db 'PyFASM-Native/1.0', 0
    align 4
    _pyfasm_http_read_bytes dd 0
    align 8
    _pyfasm_http_buf        rb 65536 ; 64KB HTTP response buffer
    align 8
    _pyfasm_strip_buf       rb 65536
"""

_WIN64_CONSOLE_RUNTIME_CODE = """section '.text' code readable executable

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

.copy_s1:
    mov     al, [rsi]
    mov     [rdi], al
    test    al, al
    jz      .copy_s2_init
    inc     rsi
    inc     rdi
    jmp     .copy_s1

.copy_s2_init:
.copy_s2:
    mov     al, [rbx]
    mov     [rdi], al
    test    al, al
    jz      .concat_done
    inc     rbx
    inc     rdi
    jmp     .copy_s2

.concat_done:
    mov     rax, [rsp + 40]
    add     rsp, 48
    pop     rbx
    pop     rdi
    pop     rsi
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
    test    rdx, rdx
    jz      .cmp_ne
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
    jb      .lower_store
    cmp     al, 'Z'
    ja      .lower_store
    add     al, 32
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
    jb      .upper_store
    cmp     al, 'z'
    ja      .upper_store
    sub     al, 32
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
    ; RCX = initial capacity (0 = default 16)
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    test    rcx, rcx
    jnz     .cap_ok
    mov     rcx, 16
.cap_ok:
    mov     rbx, rcx
    lea     rax, [rbx + rbx * 2]
    shl     rax, 3
    add     rax, 16
    mov     rcx, rax
    call    _pyfasm_alloc
    mov     [rax], rbx
    mov     qword [rax + 8], 0
    lea     rdi, [rax + 16]
    lea     rcx, [rbx + rbx * 2]
    shl     rcx, 1
    push    rax
    xor     eax, eax
    rep     stosq
    pop     rax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_str_hash:
    ; RCX = null-terminated string or 64-bit integer
    ; Returns RAX = 64-bit FNV-1a hash
    test    rcx, rcx
    jz      .hash_zero
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
    jnz     .hash_ret
    mov     rax, 1
    ret
.hash_done:
    test    rax, rax
    jnz     .hash_ret
    mov     rax, 1
.hash_ret:
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
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .dict_set_done
    mov     rbx, rcx
    mov     rsi, rdx
    mov     r12, r8

    mov     rcx, rsi
    call    _pyfasm_str_hash
    mov     r13, rax

    mov     r14, [rbx]
    dec     r14
    and     rax, r14
    mov     rdi, rax

.dict_probe:
    lea     rax, [rdi + rdi * 2]
    shl     rax, 3
    lea     rcx, [rbx + 16 + rax]

    mov     rax, [rcx]
    test    rax, rax
    jz      .dict_slot_empty

    cmp     rax, r13
    jne     .dict_next_slot

    push    rcx
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
    pop     rcx
    test    eax, eax
    jnz     .dict_update_val

.dict_next_slot:
    inc     rdi
    and     rdi, r14
    jmp     .dict_probe

.dict_slot_empty:
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
    mov     rcx, [rcx + 8]
    mov     rdx, rsi
    call    _pyfasm_str_cmp
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
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
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
    mov     rcx, [rbx + r13 * 8 + 8]
    sub     rsp, 32
    call    rsi
    add     rsp, 32
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
    mov     ecx, 16
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
    ; Returns RAX = pointer to null-terminated string in _pyfasm_int_buf
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rdi

    lea     rdi, [_pyfasm_int_buf + 30]
    mov     byte [rdi + 1], 0
    mov     rax, rcx

    test    rax, rax
    jnz     .its_check_neg
    mov     byte [rdi], '0'
    mov     rax, rdi
    jmp     .its_done

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
    mov     [rdi], r8b
    dec     rdi
    mov     rax, rdx
    jmp     .its_loop

.its_finish:
    test    ebx, ebx
    jz      .its_pos
    mov     byte [rdi], '-'
    dec     rdi
.its_pos:
    inc     rdi
    mov     rax, rdi

.its_done:
    pop     rdi
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



_pyfasm_str_slice:
    ; RCX = str pointer, RDX = lower, R8 = upper, R9 = step
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
    jz      .ss_null

    mov     rsi, rcx
    mov     r12, rdx
    mov     r13, r8
    mov     r14, r9

    mov     rcx, rsi
    call    _pyfasm_str_len
    mov     r15, rax

    test    r14, r14
    jnz     .check_step
    mov     r14, 1
.check_step:
    cmp     r14, -1
    jne     .fwd_slice

    mov     rcx, r15
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     r10, rax

    mov     rcx, r15
    test    rcx, rcx
    jz      .rev_done

    lea     rbx, [rsi + r15 - 1]
.rev_loop:
    mov     al, [rbx]
    mov     [rdi], al
    inc     rdi
    dec     rbx
    dec     rcx
    jnz     .rev_loop
.rev_done:
    mov     byte [rdi], 0
    mov     rax, r10
    jmp     .ss_exit

.fwd_slice:
    cmp     r12, 0
    jge     .l_pos
    add     r12, r15
    cmp     r12, 0
    jge     .l_pos
    xor     r12, r12
.l_pos:
    cmp     r12, r15
    jle     .l_clamp
    mov     r12, r15
.l_clamp:
    cmp     r13, -999999
    jne     .chk_u_neg
    mov     r13, r15
    jmp     .u_clamp
.chk_u_neg:
    cmp     r13, 0
    jge     .u_pos
    add     r13, r15
    cmp     r13, 0
    jge     .u_pos
    xor     r13, r13
.u_pos:
    cmp     r13, r15
    jle     .u_clamp
    mov     r13, r15
.u_clamp:
    mov     rax, r13
    sub     rax, r12
    jge     .sl_ok
    xor     eax, eax
.sl_ok:
    mov     rbx, rax

    mov     rcx, rbx
    inc     rcx
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     r10, rax

    test    rbx, rbx
    jz      .copy_done
    lea     rsi, [rsi + r12]
    mov     rcx, rbx
    rep     movsb
.copy_done:
    mov     byte [rdi], 0
    mov     rax, r10
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

_WIN64_NET_RUNTIME_CODE = """    mov     rsp, rbp
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
    ; Returns RAX = pointer to null-terminated response buffer (_pyfasm_http_buf)
    push    rbp
    mov     rbp, rsp
    push    rsi
    push    rdi
    push    rbx
    sub     rsp, 64
    and     rsp, -16

    mov     rsi, rcx                       ; save URL in rsi

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

    lea     rax, [_pyfasm_http_buf]
    add     rsp, 64
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
    mov     byte [_pyfasm_http_buf], 0
    lea     rax, [_pyfasm_http_buf]
    add     rsp, 64
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

    import kernel32, \
           GetStdHandle, 'GetStdHandle', \
           WriteFile, 'WriteFile', \
           ReadFile, 'ReadFile', \
           CreateFileA, 'CreateFileA', \
           GetFileSize, 'GetFileSize', \
           SetFilePointer, 'SetFilePointer', \
           GetTickCount64, 'GetTickCount64', \
           Sleep, 'Sleep', \
           VirtualAlloc, 'VirtualAlloc', \
           VirtualFree, 'VirtualFree', \
           CreateThread, 'CreateThread', \
           WaitForSingleObject, 'WaitForSingleObject', \
           CloseHandle, 'CloseHandle', \
           GetModuleHandleA, 'GetModuleHandleA', \
           MultiByteToWideChar, 'MultiByteToWideChar', \
           WideCharToMultiByte, 'WideCharToMultiByte', \
           GetCurrentThreadId, 'GetCurrentThreadId', \
           LoadLibraryA, 'LoadLibraryA', \
           GetProcAddress, 'GetProcAddress', \
           FreeLibrary, 'FreeLibrary', \
           ExitProcess, 'ExitProcess'
"""

_WIN64_NET_RUNTIME_IMPORTS = """
section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', \
            wininet, 'WININET.DLL'

    import kernel32, \
           GetStdHandle, 'GetStdHandle', \
           WriteFile, 'WriteFile', \
           ReadFile, 'ReadFile', \
           CreateFileA, 'CreateFileA', \
           GetFileSize, 'GetFileSize', \
           SetFilePointer, 'SetFilePointer', \
           GetTickCount64, 'GetTickCount64', \
           Sleep, 'Sleep', \
           VirtualAlloc, 'VirtualAlloc', \
           VirtualFree, 'VirtualFree', \
           CreateThread, 'CreateThread', \
           WaitForSingleObject, 'WaitForSingleObject', \
           CloseHandle, 'CloseHandle', \
           GetModuleHandleA, 'GetModuleHandleA', \
           MultiByteToWideChar, 'MultiByteToWideChar', \
           WideCharToMultiByte, 'WideCharToMultiByte', \
           GetCurrentThreadId, 'GetCurrentThreadId', \
           LoadLibraryA, 'LoadLibraryA', \
           GetProcAddress, 'GetProcAddress', \
           FreeLibrary, 'FreeLibrary', \
           ExitProcess, 'ExitProcess'

    import wininet, \
           InternetOpenA, 'InternetOpenA', \
           InternetOpenUrlA, 'InternetOpenUrlA', \
           InternetReadFile, 'InternetReadFile', \
           InternetCloseHandle, 'InternetCloseHandle'
"""


def get_win64_runtime_data(features: Optional[Set[str]] = None) -> str:
    """Returns runtime data structures (buffers, handles, constants)."""
    needs_gui = features is None or any(f in features for f in ("gui", "tray", "hook"))
    needs_net = features is None or "net" in features
    if not needs_gui:
        if needs_net:
            return _WIN64_CONSOLE_RUNTIME_DATA + "\n" + _WIN64_NET_RUNTIME_DATA
        return _WIN64_CONSOLE_RUNTIME_DATA
    return _get_win64_full_runtime_data()


def get_win64_runtime_code(features: Optional[Set[str]] = None) -> str:
    """Returns native assembly routines with strict 16-byte stack alignment."""
    needs_gui = features is None or any(f in features for f in ("gui", "tray", "hook"))
    needs_net = features is None or "net" in features
    if not needs_gui:
        if needs_net:
            return _WIN64_CONSOLE_RUNTIME_CODE + "\n" + _WIN64_NET_RUNTIME_CODE
        return _WIN64_CONSOLE_RUNTIME_CODE
    return _get_win64_full_runtime_code()


def get_win64_runtime_imports(features: Optional[Set[str]] = None) -> str:
    """Returns the IData section with Win32 API imports."""
    needs_gui = features is None or any(f in features for f in ("gui", "tray", "hook"))
    needs_net = features is None or "net" in features
    if not needs_gui:
        if needs_net:
            return _WIN64_NET_RUNTIME_IMPORTS
        return _WIN64_CONSOLE_RUNTIME_IMPORTS
    return _get_win64_full_runtime_imports()
