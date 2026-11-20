; ==============================================================================
; Stack Overflow Search Pro - 64-bit Windows Desktop Client
; Written in Pure x86-64 Assembly for Flat Assembler (FASM)
; Real Live API Search Engine (WinINet HTTPS) + Fluent Dark Owner-Drawn UI
; Modular Architecture inspired by screenvideo & copyprintwindows
; ==============================================================================

format PE64 GUI 5.0
entry start

include 'win64a.inc'
include 'const.inc'

; ==============================================================================
; Code Section
; ==============================================================================
section '.text' code readable executable

start:
        sub     rsp, 8

        ; Initialize Common Controls
        mov     dword [icc.dwSize], 8
        mov     dword [icc.dwICC], 00000008h ; ICC_TAB_CLASSES
        invoke  InitCommonControlsEx, icc

        ; Get Module Handle
        invoke  GetModuleHandle, 0
        mov     [hInstance], rax
        mov     [wc.hInstance], rax

        ; Create GDI Dark Theme Brushes & Pens
        invoke  CreateSolidBrush, COLOR_DEEP_DARK_BG ; Deep Dark Background (#0E1117)
        mov     [hBrushWin], rax
        invoke  CreateSolidBrush, COLOR_PANEL_SURFACE ; Panel Surface (#161B26)
        mov     [hBrushPanel], rax
        invoke  CreateSolidBrush, COLOR_CARD_BG ; Card Background (#1A202C)
        mov     [hBrushCard], rax
        invoke  CreateSolidBrush, COLOR_INPUT_BG ; Details / Input (#111622)
        mov     [hBrushInput], rax

        ; Create Typography Fonts (Segoe UI & Consolas)
        invoke  CreateFont, -14, 0, 0, 0, FW_NORMAL, 0, 0, 0,\
                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,\
                5, DEFAULT_PITCH, szFontUI
        mov     [hFontUI], rax

        invoke  CreateFont, -13, 0, 0, 0, FW_BOLD, 0, 0, 0,\
                204, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,\
                5, DEFAULT_PITCH, szFontUI
        mov     [hFontBold], rax

        invoke  CreateFont, -11, 0, 0, 0, FW_BOLD, 0, 0, 0,\
                204, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,\
                5, DEFAULT_PITCH, szFontUI
        mov     [hFontBadge], rax

        invoke  CreateFont, -18, 0, 0, 0, FW_BOLD, 0, 0, 0,\
                204, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,\
                5, DEFAULT_PITCH, szFontUI
        mov     [hFontTitle], rax

        invoke  CreateFont, -13, 0, 0, 0, FW_NORMAL, 0, 0, 0,\
                204, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,\
                5, FIXED_PITCH, szFontMono
        mov     [hFontMono], rax

        ; Register Window Class
        invoke  LoadCursor, 0, IDC_ARROW
        mov     [wc.hCursor], rax
        invoke  LoadImage, [hInstance], 1, IMAGE_ICON, 0, 0, LR_DEFAULTSIZE
        test    rax, rax
        jnz     @f
        invoke  LoadIcon, 0, IDI_APPLICATION
@@:
        mov     [wc.hIcon], rax
        mov     [wc.hIconSm], rax
        invoke  RegisterClassEx, wc
        test    rax, rax
        jz      .startup_error

        ; Create Main Window (1140 x 760, Centered)
        invoke  CreateWindowEx, 0, szClassName, szAppTitle,\
                WS_VISIBLE or WS_OVERLAPPEDWINDOW,\
                100, 100, 1140, 760,\
                NULL, NULL, [hInstance], NULL
        test    rax, rax
        jz      .startup_error
        mov     [hMainWnd], rax

        ; Set Big (Taskbar / Alt+Tab) and Small (Titlebar) Icons
        invoke  LoadImage, [hInstance], 1, IMAGE_ICON, 32, 32, LR_DEFAULTCOLOR
        invoke  SendMessage, [hMainWnd], WM_SETICON, ICON_BIG, rax
        invoke  LoadImage, [hInstance], 1, IMAGE_ICON, 16, 16, LR_DEFAULTCOLOR
        invoke  SendMessage, [hMainWnd], WM_SETICON, ICON_SMALL, rax

        ; Apply Windows 10/11 Immersive Dark Titlebar
        mov     dword [dwDarkVal], 1
        lea     r8, [dwDarkVal]
        invoke  DwmSetWindowAttribute, [hMainWnd], DWMWA_USE_IMMERSIVE_DARK_MODE, r8, 4
        lea     r8, [dwDarkVal]
        invoke  DwmSetWindowAttribute, [hMainWnd], DWMWA_USE_IMMERSIVE_DARK_MODE_10, r8, 4

        ; Message Loop
.msg_loop:
        lea     rcx, [msg]
        invoke  GetMessage, rcx, NULL, 0, 0
        test    eax, eax
        jle     .exit_app

        ; Intercept Enter key (VK_RETURN = 13) in Search Edit Box
        cmp     [msg.message], 0100h    ; WM_KEYDOWN
        jne     @f
        cmp     [msg.wParam], 13        ; VK_RETURN
        jne     @f
        mov     rax, [msg.hwnd]
        cmp     rax, [hEditSearch]
        jne     @f

        ; Enter key pressed -> Trigger Live Search immediately!
        invoke  SendMessage, [hMainWnd], WM_COMMAND, IDC_BTN_SEARCH, [hBtnSearch]
        jmp     .msg_loop

@@:
        lea     rcx, [msg]
        invoke  TranslateMessage, rcx
        lea     rcx, [msg]
        invoke  DispatchMessage, rcx
        jmp     .msg_loop

.startup_error:
        invoke  MessageBox, NULL, szStartupErr, szAppTitle, MB_ICONERROR or MB_OK

.exit_app:
        invoke  ExitProcess, [msg.wParam]

; ------------------------------------------------------------------------------
; Modular Logic Includes
; ------------------------------------------------------------------------------
include 'ui.inc'
include 'actions.inc'
include 'network.inc'

; ==============================================================================
; Data Section
; ==============================================================================
section '.data' data readable writeable
include 'data.inc'

; ==============================================================================
; BSS Section
; ==============================================================================
section '.bss' readable writeable
include 'bss.inc'

; ==============================================================================
; Import Section
; ==============================================================================
section '.idata' import data readable writeable

  library kernel32, 'KERNEL32.DLL',\
          user32,   'USER32.DLL',\
          gdi32,    'GDI32.DLL',\
          comctl32, 'COMCTL32.DLL',\
          shell32,  'SHELL32.DLL',\
          shlwapi,  'SHLWAPI.DLL',\
          wininet,  'WININET.DLL',\
          dwmapi,   'DWMAPI.DLL'

  import kernel32,\
         GetModuleHandle,     'GetModuleHandleA',\
         ExitProcess,         'ExitProcess',\
         LoadLibrary,         'LoadLibraryA',\
         CreateFile,          'CreateFileA',\
         SetFilePointer,      'SetFilePointer',\
         WriteFile,           'WriteFile',\
         ReadFile,            'ReadFile',\
         CloseHandle,         'CloseHandle',\
         GlobalAlloc,         'GlobalAlloc',\
         GlobalLock,          'GlobalLock',\
         GlobalUnlock,        'GlobalUnlock',\
         MultiByteToWideChar, 'MultiByteToWideChar',\
         WideCharToMultiByte, 'WideCharToMultiByte'

  import user32,\
         RegisterClassEx,   'RegisterClassExA',\
         CreateWindowEx,    'CreateWindowExA',\
         CreateWindowExW,   'CreateWindowExW',\
         DefWindowProc,     'DefWindowProcA',\
         DestroyWindow,     'DestroyWindow',\
         SendMessage,       'SendMessageA',\
         SendMessageW,      'SendMessageW',\
         PostMessage,       'PostMessageA',\
         GetMessage,        'GetMessageA',\
         TranslateMessage,  'TranslateMessage',\
         DispatchMessage,   'DispatchMessageA',\
         PostQuitMessage,   'PostQuitMessage',\
         ShowWindow,        'ShowWindow',\
         UpdateWindow,      'UpdateWindow',\
         MoveWindow,        'MoveWindow',\
         SetWindowText,     'SetWindowTextA',\
         SetWindowTextW,    'SetWindowTextW',\
         GetWindowText,     'GetWindowTextA',\
         GetClientRect,     'GetClientRect',\
         FillRect,          'FillRect',\
         DrawText,          'DrawTextA',\
         InvalidateRect,    'InvalidateRect',\
         BeginPaint,        'BeginPaint',\
         EndPaint,          'EndPaint',\
         OpenClipboard,     'OpenClipboard',\
         CloseClipboard,    'CloseClipboard',\
         EmptyClipboard,    'EmptyClipboard',\
         SetClipboardData,  'SetClipboardData',\
         LoadCursor,        'LoadCursorA',\
         LoadIcon,          'LoadIconA',\
         LoadImage,         'LoadImageA',\
         MessageBox,        'MessageBoxA'

  import gdi32,\
         SelectObject,      'SelectObject',\
         DeleteObject,      'DeleteObject',\
         CreateFont,        'CreateFontA',\
         CreateSolidBrush,  'CreateSolidBrush',\
         CreatePen,         'CreatePen',\
         RoundRect,         'RoundRect',\
         Rectangle,         'Rectangle',\
         SetTextColor,      'SetTextColor',\
         SetBkColor,        'SetBkColor',\
         SetBkMode,         'SetBkMode'

  import comctl32,\
         InitCommonControlsEx, 'InitCommonControlsEx'

  import shell32,\
         ShellExecute,      'ShellExecuteA'

  import shlwapi,\
         StrStrIA,          'StrStrIA'

  import wininet,\
         InternetOpen,        'InternetOpenA',\
         InternetOpenUrl,     'InternetOpenUrlA',\
         InternetReadFile,    'InternetReadFile',\
         InternetCloseHandle, 'InternetCloseHandle'

  import dwmapi,\
         DwmSetWindowAttribute, 'DwmSetWindowAttribute'

; ==============================================================================
; Resource Section (Application Icon & Modern Manifest)
; ==============================================================================
section '.rsrc' resource data readable

  directory RT_ICON, icons, \
            RT_GROUP_ICON, group_icons, \
            RT_MANIFEST, manifests

  resource icons, \
           1, LANG_NEUTRAL, icon_16, \
           2, LANG_NEUTRAL, icon_32, \
           3, LANG_NEUTRAL, icon_48, \
           4, LANG_NEUTRAL, icon_256

  resource group_icons, \
           1, LANG_NEUTRAL, main_icon

  resource manifests, \
           1, LANG_NEUTRAL, manifest_data

  icon main_icon, \
       icon_16,  'icon16.ico', \
       icon_32,  'icon32.ico', \
       icon_48,  'icon48.ico', \
       icon_256, 'icon256.ico'

  resdata manifest_data
    file 'manifest.xml'
  endres
