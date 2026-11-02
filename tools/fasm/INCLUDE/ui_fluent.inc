; ==============================================================================
; FASM Modern SDK - Fluent Dark UI & Owner-Drawn Engine (x86-64)
; File: include/ui_fluent.inc
; Dark Theme, Immersive Windows 10/11 Titlebars, Rounded Buttons & Card Components
; ==============================================================================

; ------------------------------------------------------------------------------
; Brand & Surface Color Equates (Catppuccin & Stack Overflow Palette)
; ------------------------------------------------------------------------------
COLOR_DEEP_DARK_BG      = 0017110Eh     ; #0E1117 - Deep Canvas Background
COLOR_PANEL_SURFACE     = 00261B16h     ; #161B26 - Left Sidebar / Surface
COLOR_CARD_BG           = 002C201Ah     ; #1A202C - Card Unselected Surface
COLOR_CARD_HOVER        = 00382922h     ; #222938 - Card Hover
COLOR_CARD_ACTIVE       = 003F2C24h     ; #242C3F - Card Selected
COLOR_CARD_BORDER       = 003D2E24h     ; #242E3D - Card Border
COLOR_INPUT_BG          = 00221611h     ; #111622 - Details / Code Input Background
COLOR_INPUT_BORDER      = 0048372Dh     ; #2D3748 - Input Border

; Accents
COLOR_SO_ORANGE         = 002480F4h     ; #F48024 - Stack Overflow Orange (BGR)
COLOR_SO_ORANGE_HOVER   = 000B67DAh     ; #DA670B
COLOR_SO_ORANGE_BRD     = 003D8FFFh     ; #FF8F3D

COLOR_SUCCESS_EMERALD   = 0081B910h     ; #10B981 - Green Accepted Pill
COLOR_SUCCESS_BG        = 003B4E06h     ; #064E3B
COLOR_TEXT_PRIMARY      = 00F8F8FCh     ; #FCF8F8 - Pure White Text
COLOR_TEXT_MUTED        = 0094A3B8h     ; #B8A394 - Muted Slate Text
COLOR_TEXT_DIM          = 0071645Bh     ; #5B6471 - Subtle Gray

; DWM Attributes
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

macro EnableImmersiveDarkMode hwnd
{
        local ..dwDarkVal
        jmp @f
        align 4
        ..dwDarkVal dd 1
    @@:
        lea     r8, [..dwDarkVal]
        invoke  DwmSetWindowAttribute, hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, r8, 4
}
