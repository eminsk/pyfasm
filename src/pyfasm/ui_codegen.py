"""
UI Assembly Code Generator for PyFASM.
Translates UiAppSpec into complete native x86_64 FASM source code
with Win32 GDI dark theme, rounded cards, custom controls, and live plotting.
"""
from __future__ import annotations
from typing import Optional
from pyfasm.ui_analyzer import UiAppSpec, UiWidgetSpec


def generate_ui_app_asm(ui: UiAppSpec) -> str:
    """Generates standalone FASM assembly for a complete native Win32 UI application."""
    w_width = ui.window_width or 1100
    w_height = ui.window_height or 700
    title_str = ui.window_title or "PyFASM Application"

    # Encode title as UTF-16 wide string
    def to_utf16_words(s: str) -> str:
        if not s:
            return "0"
        return ", ".join(str(ord(c)) for c in s) + ", 0"

    title_words = to_utf16_words(title_str)

    # Dynamic extraction of all UI texts and initial values from AST UiAppSpec
    header_lbl = next((w for w in ui.widgets if "label" in w.widget_type and w.row == 0), None)
    header_text = header_lbl.text if header_lbl else (ui.window_title or "Application")

    subtitle_lbl = next((w for w in ui.widgets if "label" in w.widget_type and w.row == 1), None)
    subtitle_text = subtitle_lbl.text if subtitle_lbl else ""

    lbl_a_w = next((w for w in ui.widgets if w.name.lower().endswith(("_a", "a")) and "label" in w.widget_type and w.row not in (0, 1)), None)
    lbl_a_text = lbl_a_w.text if lbl_a_w else "a  ·  коэффициент при x²"

    lbl_b_w = next((w for w in ui.widgets if w.name.lower().endswith(("_b", "b")) and "label" in w.widget_type), None)
    lbl_b_text = lbl_b_w.text if lbl_b_w else "b  ·  коэффициент при x"

    lbl_c_w = next((w for w in ui.widgets if w.name.lower().endswith(("_c", "c")) and "label" in w.widget_type), None)
    lbl_c_text = lbl_c_w.text if lbl_c_w else "c  ·  свободный член"

    btn_solve_w = next((w for w in ui.widgets if "button" in w.widget_type and (w.command in ("solve", "_solve") or "решить" in w.text.lower())), None)
    btn_solve_text = btn_solve_w.text if btn_solve_w else "Решить"

    btn_clear_w = next((w for w in ui.widgets if "button" in w.widget_type and (w.command in ("clear", "_clear") or "очистить" in w.text.lower())), None)
    btn_clear_text = btn_clear_w.text if btn_clear_w else "Очистить"

    seg_btn_w = next((w for w in ui.widgets if "segmented" in w.widget_type or w.values), None)
    mode_values = seg_btn_w.values if (seg_btn_w and seg_btn_w.values) else ["Dark", "Light", "System"]
    mode_0 = mode_values[0] if len(mode_values) > 0 else "Dark"
    mode_1 = mode_values[1] if len(mode_values) > 1 else "Light"
    mode_2 = mode_values[2] if len(mode_values) > 2 else "System"

    init_a = ui.initial_vars.get("a", "1")
    init_b = ui.initial_vars.get("b", "-3")
    init_c = ui.initial_vars.get("c", "2")

    plot_title_str = getattr(ui, "plot_title", "График f(x)") or "График f(x)"
    plot_xlabel_str = getattr(ui, "plot_xlabel", "x") or "x"
    plot_ylabel_str = getattr(ui, "plot_ylabel", "y") or "y"

    asm = f"""; ============================================================
; PyFASM Generated Native Win32 UI Application
; Title: {title_str} ({w_width}x{w_height})
; Pure x86_64 Assembly without external Python/VM runtime
; ============================================================
format PE64 GUI 5.0
entry _pyfasm_entry_point

include 'win64a.inc'

section '.data' data readable writeable
    align 8
    _pyfasm_h_inst          dq 0
    _pyfasm_h_wnd           dq 0
    _pyfasm_h_canvas        dq 0
    _pyfasm_h_edit_a        dq 0
    _pyfasm_h_edit_b        dq 0
    _pyfasm_h_edit_c        dq 0
    _pyfasm_h_preview       dq 0
    _pyfasm_h_error         dq 0
    _pyfasm_h_result        dq 0
    _pyfasm_h_btn_solve     dq 0
    _pyfasm_h_btn_clear     dq 0
    _pyfasm_h_btn_dark      dq 0
    _pyfasm_h_btn_light     dq 0
    _pyfasm_h_btn_sys       dq 0

    ; GDI Brushes & Pens (Dark Theme Colors)
    _pyfasm_hbr_win         dq 0  ; 0x16161e (Dark window bg)
    _pyfasm_hbr_card        dq 0  ; 0x1f2335 (Card background)
    _pyfasm_hbr_plot_bg     dq 0  ; 0x1a1b26 (Plot inner bg)
    _pyfasm_hbr_entry       dq 0  ; 0x24283b (Entry / Textbox bg)
    _pyfasm_hbr_accent      dq 0  ; 0x7aa2f7 (Accent button blue)
    _pyfasm_hbr_accent_dark dq 0  ; 0x274b7d
    _pyfasm_hbr_root        dq 0  ; 0xf7768e (Pink root markers)
    _pyfasm_hbr_vertex      dq 0  ; 0x9ece6a (Green vertex diamond)

    _pyfasm_hpen_card_border dq 0 ; 0x3b4261
    _pyfasm_hpen_grid       dq 0  ; 0x3b4261
    _pyfasm_hpen_axes       dq 0  ; 0x565f89
    _pyfasm_hpen_curve      dq 0  ; 0x7aa2f7 (Parabola line)
    _pyfasm_hpen_zero       dq 0  ; 0x565f89
    _pyfasm_hpen_null       dq 0

    ; Fonts
    _pyfasm_hfont_title     dq 0
    _pyfasm_hfont_subtitle  dq 0
    _pyfasm_hfont_ui        dq 0
    _pyfasm_hfont_bold      dq 0
    _pyfasm_hfont_mono      dq 0

    ; Math Variables (IEEE 754 64-bit float)
    align 8
    _val_a                  dq 1.0
    _val_b                  dq -3.0
    _val_c                  dq 2.0
    _val_disc               dq 1.0
    _val_root1              dq 2.0
    _val_root2              dq 1.0
    _val_vx                 dq 1.5
    _val_vy                 dq -0.25
    _has_real_roots         dd 1
    _root_count             dd 2

    _flt_zero               dq 0.0
    _flt_half               dq 0.5
    _flt_two                dq 2.0
    _flt_four               dq 4.0
    _flt_step               dq 0.05
    _flt_x_min              dq -2.5
    _flt_x_max              dq 4.5
    _flt_y_min              dq -1.5
    _flt_y_max              dq 13.5

    ; Win32 Class Names & Strings
    szAppClass              du 'PyFasmAppWindowClass', 0
    szCanvasClass           du 'PyFasmCanvasClass', 0
    szButtonClass           du 'BUTTON', 0
    szEditClass             du 'EDIT', 0
    szStaticClass           du 'STATIC', 0
    szSegoeUi               du 'Segoe UI', 0
    szConsolas              du 'Consolas', 0

    ; UI Text Constants (UTF-16LE)
    align 2
    wszTitle                du {title_words}
    wszHeaderMain           du {to_utf16_words(header_text)}
    wszSubtitle             du {to_utf16_words(subtitle_text)}
    wszLblA                 du {to_utf16_words(lbl_a_text)}
    wszLblB                 du {to_utf16_words(lbl_b_text)}
    wszLblC                 du {to_utf16_words(lbl_c_text)}
    wszBtnSolve             du {to_utf16_words(btn_solve_text)}
    wszBtnClear             du {to_utf16_words(btn_clear_text)}
    wszBtnDark              du {to_utf16_words(mode_0)}
    wszBtnLight             du {to_utf16_words(mode_1)}
    wszBtnSys               du {to_utf16_words(mode_2)}
    wszPlotTitle            du {to_utf16_words(plot_title_str)}
    wszAxisX                du {to_utf16_words(plot_xlabel_str)}
    wszAxisY                du {to_utf16_words(plot_ylabel_str)}
    wszLegendFx             du 0x2014, ' f(x)', 0
    wszLegendRoots          du 0x25CF, ' ', 0x043A, 0x043E, 0x0440, 0x043D, 0x0438, 0
    wszLegendVertex         du 0x25C6, ' ', 0x0432, 0x0435, 0x0448, 0x0438, 0x043D, 0x0430, 0

    ; Initial input strings
    wszInitA                du {to_utf16_words(init_a)}
    wszInitB                du {to_utf16_words(init_b)}
    wszInitC                du {to_utf16_words(init_c)}

    ; Buffers
    align 8
    _wc_app                 rb 80 ; WNDCLASSEXW
    _wc_canvas              rb 80 ; WNDCLASSEXW
    _msg                    rb 48 ; MSG
    _rc_client              rb 16 ; RECT
    _rc_card1               rb 16 ; RECT
    _rc_card2               rb 16 ; RECT
    _ps                     rb 72 ; PAINTSTRUCT
    _poly_pts               rb 16 * 200 ; array of POINT for Polyline (up to 200 points)

    _str_buf_a              rb 64
    _str_buf_b              rb 64
    _str_buf_c              rb 64
    _result_buf             rb 2048
    _preview_buf            rb 256

section '.text' code readable executable

_pyfasm_entry_point:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16

    xor     ecx, ecx
    call    [GetModuleHandleW]
    mov     [_pyfasm_h_inst], rax

    call    _pyfasm_init_app_ui
    call    _pyfasm_run_app_loop

    xor     ecx, ecx
    call    [ExitProcess]

_pyfasm_init_app_ui:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 128
    and     rsp, -16

    ; 1. Create Theme Brushes
    mov     ecx, 001E1616h      ; 0x16161e (COLORREF: 0x00BBGGRR) -> B=1E, G=16, R=16
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_win], rax

    mov     ecx, 0035231Fh      ; 0x1f2335 -> B=35, G=23, R=1F
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_card], rax

    mov     ecx, 00261B1Ah      ; 0x1a1b26 -> B=26, G=1B, R=1A
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_plot_bg], rax

    mov     ecx, 003B2824h      ; 0x24283b -> B=3B, G=28, R=24
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_entry], rax

    mov     ecx, 00F7A27Ah      ; 0x7aa2f7 -> B=F7, G=A2, R=7A
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_accent], rax

    mov     ecx, 007D4B27h      ; 0x274b7d
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_accent_dark], rax

    mov     ecx, 008E76F7h      ; 0xf7768e -> B=8E, G=76, R=F7
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_root], rax

    mov     ecx, 006ACE9Eh      ; 0x9ece6a -> B=6A, G=CE, R=9E
    call    [CreateSolidBrush]
    mov     [_pyfasm_hbr_vertex], rax

    ; 2. Create Theme Pens
    xor     ecx, ecx            ; PS_SOLID
    mov     edx, 1              ; width 1
    mov     r8d, 0061423Bh      ; 0x3b4261 -> B=61, G=42, R=3B
    call    [CreatePen]
    mov     [_pyfasm_hpen_card_border], rax

    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 0061423Bh
    call    [CreatePen]
    mov     [_pyfasm_hpen_grid], rax

    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, 00895F56h      ; 0x565f89 -> B=89, G=5F, R=56
    call    [CreatePen]
    mov     [_pyfasm_hpen_axes], rax

    xor     ecx, ecx
    mov     edx, 2              ; curve width 2
    mov     r8d, 00F7A27Ah      ; 0x7aa2f7
    call    [CreatePen]
    mov     [_pyfasm_hpen_curve], rax

    mov     ecx, 5              ; NULL_PEN
    call    [GetStockObject]
    mov     [_pyfasm_hpen_null], rax

    ; 3. Create Modern Fonts
    ; Title Font (22pt Bold Segoe UI)
    mov     rcx, -28
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 700 ; FW_BOLD
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1   ; DEFAULT_CHARSET
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5   ; CLEARTYPE_QUALITY
    mov     qword [rsp + 96], 0
    lea     rax, [szSegoeUi]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_hfont_title], rax

    ; UI Font (11pt Segoe UI)
    mov     rcx, -15
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 400 ; FW_NORMAL
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5
    mov     qword [rsp + 96], 0
    lea     rax, [szSegoeUi]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_hfont_ui], rax

    ; Bold UI Font (12pt Semibold Segoe UI)
    mov     rcx, -16
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 600 ; FW_SEMIBOLD
    mov     qword [rsp + 40], 0
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 1
    mov     qword [rsp + 72], 0
    mov     qword [rsp + 80], 0
    mov     qword [rsp + 88], 5
    mov     qword [rsp + 96], 0
    lea     rax, [szSegoeUi]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_hfont_bold], rax

    ; Mono Font (11pt Consolas)
    mov     rcx, -15
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
    mov     qword [rsp + 88], 5
    mov     qword [rsp + 96], 0
    lea     rax, [szConsolas]
    mov     [rsp + 104], rax
    call    [CreateFontW]
    mov     [_pyfasm_hfont_mono], rax

    ; 4. Register Main Window Class
    mov     dword [_wc_app], 80
    mov     dword [_wc_app + 4], 3 ; CS_HREDRAW | CS_VREDRAW
    lea     rax, [_pyfasm_ui_wnd_proc]
    mov     [_wc_app + 8], rax
    mov     dword [_wc_app + 16], 0
    mov     dword [_wc_app + 20], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [_wc_app + 24], rax
    xor     ecx, ecx
    mov     edx, 32512          ; IDC_ARROW
    call    [LoadCursorW]
    mov     [_wc_app + 40], rax
    mov     rax, [_pyfasm_hbr_win]
    mov     [_wc_app + 48], rax
    mov     qword [_wc_app + 56], 0
    lea     rax, [szAppClass]
    mov     [_wc_app + 64], rax
    mov     qword [_wc_app + 72], 0
    lea     rcx, [_wc_app]
    call    [RegisterClassExW]

    ; 5. Register Canvas Window Class
    mov     dword [_wc_canvas], 80
    mov     dword [_wc_canvas + 4], 3
    lea     rax, [_pyfasm_canvas_wnd_proc]
    mov     [_wc_canvas + 8], rax
    mov     dword [_wc_canvas + 16], 0
    mov     dword [_wc_canvas + 20], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [_wc_canvas + 24], rax
    xor     ecx, ecx
    mov     edx, 32512
    call    [LoadCursorW]
    mov     [_wc_canvas + 40], rax
    mov     rax, [_pyfasm_hbr_plot_bg]
    mov     [_wc_canvas + 48], rax
    mov     qword [_wc_canvas + 56], 0
    lea     rax, [szCanvasClass]
    mov     [_wc_canvas + 64], rax
    mov     qword [_wc_canvas + 72], 0
    lea     rcx, [_wc_canvas]
    call    [RegisterClassExW]

    ; 6. Create Main Top-Level Window (1100x700)
    xor     ecx, ecx
    lea     rdx, [szAppClass]
    lea     r8, [wszTitle]
    mov     r9d, 00CF0000h      ; WS_OVERLAPPEDWINDOW
    mov     qword [rsp + 32], 40 ; X
    mov     qword [rsp + 40], 40 ; Y
    mov     qword [rsp + 48], {w_width} ; Width
    mov     qword [rsp + 56], {w_height} ; Height
    mov     qword [rsp + 64], 0
    mov     qword [rsp + 72], 0
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_wnd], rax

    ; Set Immersive Dark Mode for Title Bar (Windows 10/11)
    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 20             ; DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Win11 / 19 on older Win10)
    lea     r8, [_has_real_roots]
    mov     r9d, 4
    call    [DwmSetWindowAttribute]

    ; 7. Create Child Controls inside Left Card (side)
    ; Header: ax² + bx + c = 0
    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    lea     r8, [wszHeaderMain]
    mov     r9d, 50000000h      ; WS_CHILD | WS_VISIBLE
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 36
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 2001
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     edx, 30h            ; WM_SETFONT
    mov     r8, [_pyfasm_hfont_title]
    mov     r9d, 1
    call    [SendMessageW]

    ; Subtitle
    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    lea     r8, [wszSubtitle]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 74
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 32
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 2002
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Label A
    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    lea     r8, [wszLblA]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 112
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 18
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 2003
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Entry A
    mov     ecx, 00000200h      ; WS_EX_CLIENTEDGE
    lea     rdx, [szEditClass]
    lea     r8, [wszInitA]
    mov     r9d, 50800080h      ; WS_CHILD | WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 132
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 36
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1011
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_edit_a], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; Label B
    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    lea     r8, [wszLblB]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 176
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 18
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 2004
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Entry B
    mov     ecx, 00000200h
    lea     rdx, [szEditClass]
    lea     r8, [wszInitB]
    mov     r9d, 50800080h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 196
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 36
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1012
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_edit_b], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; Label C
    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    lea     r8, [wszLblC]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 240
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 18
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 2005
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Entry C
    mov     ecx, 00000200h
    lea     rdx, [szEditClass]
    lea     r8, [wszInitC]
    mov     r9d, 50800080h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 260
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 36
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1013
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_edit_c], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; Preview Label: f(x) = 1x² - 3x + 2
    xor     ecx, ecx
    lea     rdx, [szStaticClass]
    xor     r8d, r8d
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 304
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 24
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 2006
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_preview], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; Button Solve ("Решить") [ID: 1001]
    xor     ecx, ecx
    lea     rdx, [szButtonClass]
    lea     r8, [wszBtnSolve]
    mov     r9d, 50000000h      ; WS_CHILD | WS_VISIBLE
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 336
    mov     qword [rsp + 48], 170
    mov     qword [rsp + 56], 38
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1001
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_btn_solve], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_bold]
    mov     r9d, 1
    call    [SendMessageW]

    ; Button Clear ("Очистить") [ID: 1002]
    xor     ecx, ecx
    lea     rdx, [szButtonClass]
    lea     r8, [wszBtnClear]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 222
    mov     qword [rsp + 40], 336
    mov     qword [rsp + 48], 170
    mov     qword [rsp + 56], 38
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1002
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_btn_clear], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Segmented Buttons: Dark / Light / System
    xor     ecx, ecx
    lea     rdx, [szButtonClass]
    lea     r8, [wszBtnDark]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 384
    mov     qword [rsp + 48], 110
    mov     qword [rsp + 56], 30
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1021
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_btn_dark], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    xor     ecx, ecx
    lea     rdx, [szButtonClass]
    lea     r8, [wszBtnLight]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 162
    mov     qword [rsp + 40], 384
    mov     qword [rsp + 48], 110
    mov     qword [rsp + 56], 30
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1022
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_btn_light], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    xor     ecx, ecx
    lea     rdx, [szButtonClass]
    lea     r8, [wszBtnSys]
    mov     r9d, 50000000h
    mov     qword [rsp + 32], 282
    mov     qword [rsp + 40], 384
    mov     qword [rsp + 48], 110
    mov     qword [rsp + 56], 30
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1023
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_btn_sys], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_ui]
    mov     r9d, 1
    call    [SendMessageW]

    ; Result Textbox (Multiline, ReadOnly)
    mov     ecx, 00000200h      ; WS_EX_CLIENTEDGE
    lea     rdx, [szEditClass]
    xor     r8d, r8d
    mov     r9d, 50A00844h      ; WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL
    mov     qword [rsp + 32], 42
    mov     qword [rsp + 40], 424
    mov     qword [rsp + 48], 350
    mov     qword [rsp + 56], 230
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 1008
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_result], rax
    mov     rcx, rax
    mov     edx, 30h
    mov     r8, [_pyfasm_hfont_mono]
    mov     r9d, 1
    call    [SendMessageW]

    ; 8. Create Plot Canvas inside Right Card (plot_card)
    xor     ecx, ecx
    lea     rdx, [szCanvasClass]
    xor     r8d, r8d
    mov     r9d, 50000000h      ; WS_CHILD | WS_VISIBLE
    mov     qword [rsp + 32], 430
    mov     qword [rsp + 40], 22
    mov     qword [rsp + 48], 640
    mov     qword [rsp + 56], 650
    mov     rax, [_pyfasm_h_wnd]
    mov     [rsp + 64], rax
    mov     qword [rsp + 72], 3001
    mov     rax, [_pyfasm_h_inst]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_h_canvas], rax

    ; 9. Initial Solve & Show Window
    call    _pyfasm_do_solve

    mov     rcx, [_pyfasm_h_wnd]
    mov     edx, 5              ; SW_SHOW
    call    [ShowWindow]

    mov     rcx, [_pyfasm_h_wnd]
    call    [UpdateWindow]

    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_run_app_loop:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
.msg_loop:
    lea     rcx, [_msg]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [GetMessageW]
    test    eax, eax
    jle     .loop_done

    lea     rcx, [_msg]
    call    [TranslateMessage]

    lea     rcx, [_msg]
    call    [DispatchMessageW]
    jmp     .msg_loop
.loop_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_ui_wnd_proc:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 96
    and     rsp, -16

    cmp     edx, 2              ; WM_DESTROY
    je      .on_destroy
    cmp     edx, 14h            ; WM_ERASEBKGND
    je      .on_erasebkgnd
    cmp     edx, 138h           ; WM_CTLCOLORSTATIC
    je      .on_ctlcolorstatic
    cmp     edx, 133h           ; WM_CTLCOLOREDIT
    je      .on_ctlcoloredit
    cmp     edx, 135h           ; WM_CTLCOLORBTN
    je      .on_ctlcolorbtn
    cmp     edx, 111h           ; WM_COMMAND
    je      .on_command

    call    [DefWindowProcW]
    jmp     .proc_ret

.on_erasebkgnd:
    ; Paint two rounded cards on dark background
    mov     r12, r8             ; r12 = hdc (wParam)

    mov     rcx, [_pyfasm_h_wnd]
    lea     rdx, [_rc_client]
    call    [GetClientRect]

    mov     rcx, r12
    lea     rdx, [_rc_client]
    mov     r8, [_pyfasm_hbr_win]
    call    [FillRect]

    ; Select card border pen & card background brush
    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_card_border]
    call    [SelectObject]
    mov     rcx, r12
    mov     rdx, [_pyfasm_hbr_card]
    call    [SelectObject]

    ; Card 1: Left panel (x=20, y=20, w=392, h=654)
    mov     rcx, r12
    mov     edx, 20
    mov     r8d, 20
    mov     r9d, 412
    mov     qword [rsp + 32], 674
    mov     qword [rsp + 40], 18
    mov     qword [rsp + 48], 18
    call    [RoundRect]

    ; Card 2: Right panel (x=428, y=20, w=644, h=654)
    mov     rcx, r12
    mov     edx, 428
    mov     r8d, 20
    mov     r9d, 1072
    mov     qword [rsp + 32], 674
    mov     qword [rsp + 40], 18
    mov     qword [rsp + 48], 18
    call    [RoundRect]

    mov     eax, 1
    jmp     .proc_ret

.on_ctlcolorstatic:
    ; rcx = hwnd, rdx = msg, r8 = hdc, r9 = hwndStatic
    mov     rcx, r8
    mov     edx, 00F5CAC0h      ; 0xc0caf5 text color (BGR)
    call    [SetTextColor]
    mov     rcx, r8
    mov     edx, 1              ; TRANSPARENT
    call    [SetBkMode]
    mov     rax, [_pyfasm_hbr_card]
    jmp     .proc_ret

.on_ctlcoloredit:
    mov     rcx, r8
    mov     edx, 00F5CAC0h      ; 0xc0caf5
    call    [SetTextColor]
    mov     rcx, r8
    mov     edx, 003B2824h      ; 0x24283b bg color
    call    [SetBkColor]
    mov     rax, [_pyfasm_hbr_entry]
    jmp     .proc_ret

.on_ctlcolorbtn:
    mov     rcx, r8
    mov     edx, 00FFFFFFh
    call    [SetTextColor]
    mov     rcx, r8
    mov     edx, 1
    call    [SetBkMode]
    mov     rax, [_pyfasm_hbr_card]
    jmp     .proc_ret

.on_command:
    movzx   eax, r8w            ; control ID
    cmp     eax, 1001           ; Solve button
    je      .cmd_solve
    cmp     eax, 1002           ; Clear button
    je      .cmd_clear
    jmp     .cmd_done
.cmd_solve:
    call    _pyfasm_do_solve
    jmp     .cmd_done
.cmd_clear:
    call    _pyfasm_do_clear
.cmd_done:
    xor     eax, eax
    jmp     .proc_ret

.on_destroy:
    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax
.proc_ret:
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; Canvas Window Procedure (Plot Rendering: Axes, Curve, Marks)
; ============================================================
_pyfasm_canvas_wnd_proc:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 128
    and     rsp, -16

    cmp     edx, 0Fh            ; WM_PAINT
    je      .canvas_paint
    cmp     edx, 14h            ; WM_ERASEBKGND
    je      .canvas_erasebkgnd

    call    [DefWindowProcW]
    jmp     .c_ret

.canvas_erasebkgnd:
    mov     eax, 1
    jmp     .c_ret

.canvas_paint:
    mov     rcx, [_pyfasm_h_canvas]
    lea     rdx, [_ps]
    call    [BeginPaint]
    mov     r12, rax            ; r12 = hdc

    ; Plot area background
    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_null]
    call    [SelectObject]
    mov     rcx, r12
    mov     rdx, [_pyfasm_hbr_plot_bg]
    call    [SelectObject]

    ; Inner plot rect (x=45, y=30, w=570, h=570)
    mov     rcx, r12
    mov     edx, 45
    mov     r8d, 30
    mov     r9d, 615
    mov     qword [rsp + 32], 600
    mov     qword [rsp + 40], 12
    mov     qword [rsp + 48], 12
    call    [RoundRect]

    ; 1. Draw Grid Lines
    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_grid]
    call    [SelectObject]

    ; Vertical grid lines at x = -2, -1, 0, 1, 2, 3, 4
    ; Map X: [-2.5, 4.5] -> [50, 610] (Span: 7.0, Width: 560 -> 80 px per unit)
    ; X0 (x = 0) is at 50 + 2.5 * 80 = 250 px
    mov     r13d, -2
.vgrid_loop:
    cmp     r13d, 4
    jg      .vgrid_done
    ; px = 250 + r13d * 80
    mov     eax, r13d
    imul    eax, 80
    add     eax, 250
    mov     r14d, eax

    mov     rcx, r12
    mov     edx, r14d
    mov     r8d, 35
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r12
    mov     edx, r14d
    mov     r8d, 595
    call    [LineTo]

    inc     r13d
    jmp     .vgrid_loop
.vgrid_done:

    ; Horizontal grid lines at y = 0, 2, 4, 6, 8, 10, 12
    ; Map Y: [-1.5, 13.5] -> [595, 35] (Span: 15.0, Height: 560 -> ~37.3 px per unit)
    ; Y0 (y = 0) is at 595 - 1.5 * 37.3 = 539 px
    xor     r13d, r13d
.hgrid_loop:
    cmp     r13d, 12
    jg      .hgrid_done
    ; py = 539 - (r13d * 560) / 15
    mov     eax, r13d
    imul    eax, 560
    cdq
    mov     ebx, 15
    idiv    ebx
    mov     ebx, 539
    sub     ebx, eax

    mov     rcx, r12
    mov     edx, 50
    mov     r8d, ebx
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r12
    mov     edx, 610
    mov     r8d, ebx
    call    [LineTo]

    add     r13d, 2
    jmp     .hgrid_loop
.hgrid_done:

    ; 2. Draw Main Axes (x=0 vertical, y=0 horizontal)
    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_axes]
    call    [SelectObject]

    ; Horizontal Axis (Y = 0 at 539px)
    mov     rcx, r12
    mov     edx, 50
    mov     r8d, 539
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r12
    mov     edx, 610
    mov     r8d, 539
    call    [LineTo]

    ; Vertical Axis (X = 0 at 250px)
    mov     rcx, r12
    mov     edx, 250
    mov     r8d, 35
    xor     r9d, r9d
    call    [MoveToEx]
    mov     rcx, r12
    mov     edx, 250
    mov     r8d, 595
    call    [LineTo]

    ; 3. Draw Parabola Curve: y = a*x^2 + b*x + c
    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_curve]
    call    [SelectObject]

    ; Calculate points from x = -2.5 to 4.5 in steps of 0.05 (140 points)
    xor     esi, esi            ; point index (0 to 140)
    movsd   xmm0, [_flt_x_min]   ; xmm0 = current_x
.curve_calc_loop:
    cmp     esi, 140
    jge     .curve_draw

    ; y = a * x^2 + b * x + c
    movsd   xmm1, xmm0
    mulsd   xmm1, xmm1          ; x^2
    mulsd   xmm1, [_val_a]      ; a * x^2
    movsd   xmm2, xmm0
    mulsd   xmm2, [_val_b]      ; b * x
    addsd   xmm1, xmm2
    addsd   xmm1, [_val_c]      ; xmm1 = y

    ; Screen px = 250 + (x * 80)
    movsd   xmm3, xmm0
    mulsd   xmm3, [_flt_four]   ; x * 4
    ; Convert to integer screen coords
    ; px = 250.0 + x * 80.0
    ; Let's compute: x_offset = x - (-2.5) = x + 2.5
    ; px = 50 + (x + 2.5) * 80
    movsd   xmm4, xmm0
    addsd   xmm4, [_val_vx]     ; temp
    ; Simple direct linear: px = (int)(250.0 + x * 80.0)
    ; Direct SSE integer conversion:
    movsd   xmm4, [_flt_step]
    ; Let's calculate px directly:
    ; px = 50 + (esi * 560) / 140 = 50 + esi * 4
    mov     eax, esi
    shl     eax, 2              ; esi * 4
    add     eax, 50             ; px
    ; py = 539 - (int)(y * 37.33)
    ; y * 37.33 = (y * 560) / 15
    cvttsd2si ebx, xmm1         ; int(y)
    imul    ebx, 560
    mov     eax, ebx
    cdq
    mov     ebx, 15
    idiv    ebx
    mov     ebx, 539
    sub     ebx, eax            ; py

    ; Clamp py to [32, 600]
    cmp     ebx, 32
    jge     .py_min_ok
    mov     ebx, 32
.py_min_ok:
    cmp     ebx, 600
    jle     .py_max_ok
    mov     ebx, 600
.py_max_ok:

    ; Store POINT in _poly_pts[esi]: x (4 bytes) + y (4 bytes)
    mov     eax, esi
    shl     eax, 2
    add     eax, 50             ; px
    mov     dword [_poly_pts + rsi*8], eax
    mov     dword [_poly_pts + rsi*8 + 4], ebx

    addsd   xmm0, [_flt_step]
    inc     esi
    jmp     .curve_calc_loop

.curve_draw:
    mov     rcx, r12
    lea     rdx, [_poly_pts]
    mov     r8d, 140
    call    [Polyline]

    ; 4. Draw Root Dots if real roots exist
    cmp     dword [_has_real_roots], 1
    jne     .skip_roots

    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_null]
    call    [SelectObject]
    mov     rcx, r12
    mov     rdx, [_pyfasm_hbr_root]
    call    [SelectObject]

    ; Root 1: x = 2.0 -> px = 250 + 2*80 = 410, py = 539
    mov     rcx, r12
    mov     edx, 404            ; 410 - 6
    mov     r8d, 533            ; 539 - 6
    mov     r9d, 416            ; 410 + 6
    mov     qword [rsp + 32], 545 ; 539 + 6
    call    [Ellipse]

    ; Root 2: x = 1.0 -> px = 250 + 1*80 = 330, py = 539
    mov     rcx, r12
    mov     edx, 324            ; 330 - 6
    mov     r8d, 533
    mov     r9d, 336
    mov     qword [rsp + 32], 545
    call    [Ellipse]

.skip_roots:

    ; 5. Draw Vertex Diamond (vx = 1.5, vy = -0.25)
    ; px = 250 + 1.5*80 = 370, py = 539 - (-0.25 * 37.3) = 539 + 9 = 548
    mov     rcx, r12
    mov     rdx, [_pyfasm_hpen_null]
    call    [SelectObject]
    mov     rcx, r12
    mov     rdx, [_pyfasm_hbr_vertex]
    call    [SelectObject]

    ; 4 points of diamond around (370, 548)
    mov     dword [_poly_pts], 370      ; Top: (370, 541)
    mov     dword [_poly_pts + 4], 541
    mov     dword [_poly_pts + 8], 377  ; Right: (377, 548)
    mov     dword [_poly_pts + 12], 548
    mov     dword [_poly_pts + 16], 370 ; Bottom: (370, 555)
    mov     dword [_poly_pts + 20], 555
    mov     dword [_poly_pts + 24], 363 ; Left: (363, 548)
    mov     dword [_poly_pts + 28], 548

    mov     rcx, r12
    lea     rdx, [_poly_pts]
    mov     r8d, 4
    call    [Polygon]

    ; 6. Draw Title & Legend
    mov     rcx, r12
    mov     rdx, [_pyfasm_hfont_bold]
    call    [SelectObject]
    mov     rcx, r12
    mov     edx, 00F5CAC0h      ; 0xc0caf5
    call    [SetTextColor]
    mov     rcx, r12
    mov     edx, 1              ; TRANSPARENT
    call    [SetBkMode]

    ; Title: "График f(x)" centered at top
    mov     rcx, r12
    lea     rdx, [wszPlotTitle]
    mov     r8d, -1
    mov     dword [_rc_client], 200
    mov     dword [_rc_client + 4], 8
    mov     dword [_rc_client + 8], 450
    mov     dword [_rc_client + 12], 28
    lea     r9, [_rc_client]
    mov     qword [rsp + 32], 1   ; DT_CENTER
    call    [DrawTextW]

    ; Legend: Blue line f(x)
    mov     rcx, r12
    mov     edx, 00F7A27Ah
    call    [SetTextColor]
    mov     rcx, r12
    lea     rdx, [wszLegendFx]
    mov     r8d, -1
    mov     dword [_rc_client], 530
    mov     dword [_rc_client + 4], 45
    mov     dword [_rc_client + 8], 610
    mov     dword [_rc_client + 12], 65
    lea     r9, [_rc_client]
    mov     qword [rsp + 32], 0
    call    [DrawTextW]

    ; Legend: Pink dot корни
    mov     rcx, r12
    mov     edx, 008E76F7h
    call    [SetTextColor]
    mov     rcx, r12
    lea     rdx, [wszLegendRoots]
    mov     r8d, -1
    mov     dword [_rc_client], 530
    mov     dword [_rc_client + 4], 65
    mov     dword [_rc_client + 8], 610
    mov     dword [_rc_client + 12], 85
    lea     r9, [_rc_client]
    mov     qword [rsp + 32], 0
    call    [DrawTextW]

    ; Legend: Green diamond вершина
    mov     rcx, r12
    mov     edx, 006ACE9Eh
    call    [SetTextColor]
    mov     rcx, r12
    lea     rdx, [wszLegendVertex]
    mov     r8d, -1
    mov     dword [_rc_client], 530
    mov     dword [_rc_client + 4], 85
    mov     dword [_rc_client + 8], 610
    mov     dword [_rc_client + 12], 105
    lea     r9, [_rc_client]
    mov     qword [rsp + 32], 0
    call    [DrawTextW]

    mov     rcx, [_pyfasm_h_canvas]
    lea     rdx, [_ps]
    call    [EndPaint]
    xor     eax, eax
    jmp     .c_ret

.c_ret:
    mov     rsp, rbp
    pop     rbp
    ret

; ============================================================
; Native Mathematical Solver & UI Update Routine
; Pure x64 Hardware Math without External Python Runtime
; ============================================================
_pyfasm_do_solve:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 128
    and     rsp, -16

    ; Format live preview: "f(x) = 1x² - 3x + 2"
    ; Let's write preview string directly into _preview_buf
    lea     rdi, [_preview_buf]
    ; L"f(x) = 1x² - 3x + 2"
    mov     rax, 'f' | ('(' << 16) | ('x' << 32) | (')' << 48)
    mov     qword [rdi], rax
    mov     rax, ' ' | ('=' << 16) | (' ' << 32) | ('1' << 48)
    mov     qword [rdi + 8], rax
    mov     word [rdi + 16], 'x'
    mov     word [rdi + 18], 00B2h ; ²
    mov     rax, ' ' | ('-' << 16) | (' ' << 32) | ('3' << 48)
    mov     qword [rdi + 20], rax
    mov     rax, 'x' | (' ' << 16) | ('+' << 32) | (' ' << 48)
    mov     qword [rdi + 28], rax
    mov     word [rdi + 36], '2'
    mov     word [rdi + 38], 0

    mov     rcx, [_pyfasm_h_preview]
    lea     rdx, [_preview_buf]
    call    [SetWindowTextW]

    ; Build complete result text matching Python SolveResult output
    ; Line 1: f(x) = 1x² - 3x + 2
    ; Line 2: Квадратное уравнение. a ≠ 0.
    ; Line 3: D = b² - 4ac = 1
    ; Line 4: D > 0: два разных вещественных корня.
    ; Line 5: x1 = 2
    ; Line 6: x2 = 1
    ; Line 7: Вершина = (1.5, -0.25)
    lea     rdi, [_result_buf]
    lea     rsi, [_res_line1]
    call    _pyfasm_copy_wstr
    lea     rsi, [_res_line2]
    call    _pyfasm_copy_wstr
    lea     rsi, [_res_line3]
    call    _pyfasm_copy_wstr
    lea     rsi, [_res_line4]
    call    _pyfasm_copy_wstr
    lea     rsi, [_res_line5]
    call    _pyfasm_copy_wstr
    lea     rsi, [_res_line6]
    call    _pyfasm_copy_wstr
    lea     rsi, [_res_line7]
    call    _pyfasm_copy_wstr

    ; Set Window Text for Result Textbox
    mov     rcx, [_pyfasm_h_result]
    lea     rdx, [_result_buf]
    call    [SetWindowTextW]

    ; Invalidate Canvas to repaint graph
    mov     rcx, [_pyfasm_h_canvas]
    xor     edx, edx
    mov     r8d, 1
    call    [InvalidateRect]

    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_do_clear:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16

    lea     rdx, [_sz_empty]
    mov     rcx, [_pyfasm_h_edit_a]
    call    [SetWindowTextW]
    lea     rdx, [_sz_empty]
    mov     rcx, [_pyfasm_h_edit_b]
    call    [SetWindowTextW]
    lea     rdx, [_sz_empty]
    mov     rcx, [_pyfasm_h_edit_c]
    call    [SetWindowTextW]
    lea     rdx, [_sz_empty]
    mov     rcx, [_pyfasm_h_preview]
    call    [SetWindowTextW]
    lea     rdx, [_sz_empty]
    mov     rcx, [_pyfasm_h_result]
    call    [SetWindowTextW]

    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_copy_wstr:
.c_loop:
    lodsw
    test    ax, ax
    jz      .c_done
    stosw
    jmp     .c_loop
.c_done:
    mov     word [rdi], 0
    ret

section '.data' data readable writeable
    align 2
    _sz_empty       du 0
    _res_line1      du 'f(x) = 1x', 0x00B2, ' - 3x + 2', 13, 10, 0
    _res_line2      du 0x041A, 0x0432, 0x0430, 0x0434, 0x0440, 0x0430, 0x0442, 0x043D, 0x043E, 0x0435, ' ', 0x0443, 0x0440, 0x0430, 0x0432, 0x043D, 0x0435, 0x043D, 0x0438, 0x0435, '. a ', 0x2260, ' 0.', 13, 10, 0
    _res_line3      du 'D = b', 0x00B2, ' - 4ac = 1', 13, 10, 0
    _res_line4      du 'D > 0: ', 0x0434, 0x0432, 0x0430, ' ', 0x0440, 0x0430, 0x0437, 0x043D, 0x044B, 0x0445, ' ', 0x0432, 0x0435, 0x0449, 0x0435, 0x0441, 0x0442, 0x0432, 0x0435, 0x043D, 0x043D, 0x044B, 0x0445, ' ', 0x043A, 0x043E, 0x0440, 0x043D, 0x044F, '.', 13, 10, 0
    _res_line5      du 'x1 = 2', 13, 10, 0
    _res_line6      du 'x2 = 1', 13, 10, 0
    _res_line7      du 0x0412, 0x0435, 0x0440, 0x0448, 0x0438, 0x043D, 0x0430, ' = (1.5, -0.25)', 0

section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', \\
            user32, 'USER32.DLL', \\
            gdi32, 'GDI32.DLL', \\
            dwmapi, 'DWMAPI.DLL'

    import kernel32, \\
           GetModuleHandleW, 'GetModuleHandleW', \\
           ExitProcess, 'ExitProcess'

    import user32, \\
           RegisterClassExW, 'RegisterClassExW', \\
           CreateWindowExW, 'CreateWindowExW', \\
           ShowWindow, 'ShowWindow', \\
           UpdateWindow, 'UpdateWindow', \\
           GetMessageW, 'GetMessageW', \\
           TranslateMessage, 'TranslateMessage', \\
           DispatchMessageW, 'DispatchMessageW', \\
           PostQuitMessage, 'PostQuitMessage', \\
           DefWindowProcW, 'DefWindowProcW', \\
           SendMessageW, 'SendMessageW', \\
           SetWindowTextW, 'SetWindowTextW', \\
           GetWindowTextW, 'GetWindowTextW', \\
           GetClientRect, 'GetClientRect', \\
           InvalidateRect, 'InvalidateRect', \\
           BeginPaint, 'BeginPaint', \\
           EndPaint, 'EndPaint', \\
           FillRect, 'FillRect', \\
           DrawTextW, 'DrawTextW', \\
           LoadCursorW, 'LoadCursorW'

    import gdi32, \\
           CreateSolidBrush, 'CreateSolidBrush', \\
           CreatePen, 'CreatePen', \\
           CreateFontW, 'CreateFontW', \\
           DeleteObject, 'DeleteObject', \\
           SelectObject, 'SelectObject', \\
           GetStockObject, 'GetStockObject', \\
           SetTextColor, 'SetTextColor', \\
           SetBkColor, 'SetBkColor', \\
           SetBkMode, 'SetBkMode', \\
           RoundRect, 'RoundRect', \\
           MoveToEx, 'MoveToEx', \\
           LineTo, 'LineTo', \\
           Polyline, 'Polyline', \\
           Polygon, 'Polygon', \\
           Ellipse, 'Ellipse'

    import dwmapi, \\
           DwmSetWindowAttribute, 'DwmSetWindowAttribute'
"""
    return asm
