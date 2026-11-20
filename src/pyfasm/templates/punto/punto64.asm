;============================================================================;
;                                                                            ;
;                 PUNTO SWITCHER FOR WINDOWS x64 — PURE FASM                 ;
;                      Native 64-bit Assembly Edition                        ;
;                                                                            ;
;============================================================================;

format PE64 GUI 5.0
entry start

include 'win64a.inc'

include 'layout.inc'
include 'windows.inc'
include 'converter.inc'

WM_TRAYICON     = 0x8001
IDM_AUTO        = 1001
IDM_SOUND       = 1002
IDM_AUTOSTART   = 1003
IDM_EXIT        = 1004

MF_STRING       = 0x0000
MF_SEPARATOR    = 0x0800
MF_GRAYED       = 0x0001
TPM_RIGHTBUTTON = 0x0002
TPM_BOTTOMALIGN = 0x0020

HKEY_CURRENT_USER = 0xFFFFFFFF80000001
KEY_READ          = 0x00020019
KEY_WRITE         = 0x00020006
KEY_ALL_ACCESS    = 0x000F003F
REG_SZ            = 1

NIM_ADD         = 0x00000000
NIM_MODIFY      = 0x00000001
NIM_DELETE      = 0x00000002
NIF_MESSAGE     = 0x00000001
NIF_ICON        = 0x00000002
NIF_TIP         = 0x00000004

;============================================================================;
;                              CODE SECTION                                  ;
;============================================================================;
section '.text' code readable executable

start:
    sub     rsp, 28h

    ; Enable Per-Monitor DPI Awareness
    lea     rcx, [szUser32]
    call    [GetModuleHandleA]
    test    rax, rax
    jz      .dpi_done
    mov     rcx, rax
    lea     rdx, [szSetProcessDPIAware]
    call    [GetProcAddress]
    test    rax, rax
    jz      .dpi_done
    call    rax
.dpi_done:

    ; 1. Get module handle
    xor     ecx, ecx
    call    [GetModuleHandleA]
    mov     [hInstance], rax

    ; Check autostart status in Windows Registry
    call    CheckAutostart

    ; Pre-load keyboard layouts (Unicode)
    lea     rcx, [wszKlidEn]
    mov     edx, KLF_ACTIVATE
    call    [LoadKeyboardLayoutW]
    mov     [hkl_en], rax

    lea     rcx, [wszKlidRu]
    mov     edx, KLF_ACTIVATE
    call    [LoadKeyboardLayoutW]
    mov     [hkl_ru], rax

    ; 2. Setup WNDCLASSEX
    lea     rdi, [wc]
    xor     eax, eax
    mov     ecx, sizeof.WNDCLASSEX
    rep stosb

    mov     dword [wc.cbSize], sizeof.WNDCLASSEX
    lea     rax, [WindowProc]
    mov     [wc.lpfnWndProc], rax
    mov     rax, [hInstance]
    mov     [wc.hInstance], rax
    lea     rax, [_class]
    mov     [wc.lpszClassName], rax

    ; Load custom icon from resources (ID 1)
    mov     rcx, [hInstance]
    mov     edx, 1
    call    [LoadIconA]
    test    rax, rax
    jnz     .icon_loaded
    xor     ecx, ecx
    mov     edx, 32512
    call    [LoadIconA]
.icon_loaded:
    mov     [wc.hIcon], rax
    mov     [wc.hIconSm], rax
    mov     [hAppIcon], rax

    ; 3. Register class
    lea     rcx, [wc]
    call    [RegisterClassExA]

    ; 4. Create background window
    sub     rsp, 60h
    xor     ecx, ecx
    lea     rdx, [_class]
    lea     r8, [_title]
    xor     r9d, r9d
    mov     dword [rsp+20h], 0
    mov     dword [rsp+28h], 0
    mov     dword [rsp+30h], 0
    mov     dword [rsp+38h], 0
    mov     qword [rsp+40h], 0
    mov     qword [rsp+48h], 0
    mov     rax, [hInstance]
    mov     qword [rsp+50h], rax
    mov     qword [rsp+58h], 0
    call    [CreateWindowExA]
    add     rsp, 60h
    mov     [hWnd], rax

    ; 5. Setup Tray Icon
    lea     rdi, [nid]
    xor     eax, eax
    mov     ecx, sizeof.NOTIFYICONDATAA
    rep stosb

    mov     dword [nid.cbSize], sizeof.NOTIFYICONDATAA
    mov     rax, [hWnd]
    mov     [nid.hWnd], rax
    mov     dword [nid.uID], 1
    mov     dword [nid.uFlags], NIF_MESSAGE + NIF_ICON + NIF_TIP
    mov     dword [nid.uCallbackMessage], WM_TRAYICON
    mov     rax, [hAppIcon]
    mov     [nid.hIcon], rax

    ; Copy tooltip
    lea     rsi, [_tray_tip]
    lea     rdi, [nid.szTip]
    mov     ecx, 64
    rep movsb

    xor     ecx, ecx            ; NIM_ADD
    lea     rdx, [nid]
    call    [Shell_NotifyIconA]

    ; 6. Install Low-Level Keyboard Hook
    mov     ecx, 13             ; WH_KEYBOARD_LL
    lea     rdx, [LowLevelKeyboardProc]
    mov     r8, [hInstance]
    xor     r9d, r9d
    call    [SetWindowsHookExA]
    mov     [hHook], rax

    ; 7. Message Loop
.msg_loop:
    lea     rcx, [msg]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    [GetMessageA]
    cmp     eax, 0
    jle     .cleanup
    lea     rcx, [msg]
    call    [TranslateMessage]
    lea     rcx, [msg]
    call    [DispatchMessageA]
    jmp     .msg_loop

.cleanup:
    cmp     qword [hHook], 0
    jz      .remove_tray
    mov     rcx, [hHook]
    call    [UnhookWindowsHookEx]

.remove_tray:
    mov     ecx, 2              ; NIM_DELETE
    lea     rdx, [nid]
    call    [Shell_NotifyIconA]

.exit:
    xor     ecx, ecx
    call    [ExitProcess]


;============================================================================;
;                     AUTOSTART HELPER FUNCTIONS                             ;
;============================================================================;
; Check if PuntoSwitcher64 is in HKCU\...\Run
CheckAutostart:
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 30h

    mov     qword [autostart_enabled], 0

    ; RegOpenKeyExA(HKEY_CURRENT_USER, szRegRunKey, 0, KEY_READ, &hRegKey)
    mov     rcx, HKEY_CURRENT_USER
    lea     rdx, [szRegRunKey]
    xor     r8d, r8d
    mov     r9d, KEY_READ
    lea     rax, [hRegKey]
    mov     qword [rsp+20h], rax
    call    [RegOpenKeyExA]
    test    eax, eax
    jnz     .done

    ; RegQueryValueExA(hRegKey, szRegRunVal, 0, 0, 0, 0)
    mov     rcx, [hRegKey]
    lea     rdx, [szRegRunVal]
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp+20h], 0
    mov     qword [rsp+28h], 0
    call    [RegQueryValueExA]
    test    eax, eax
    jnz     .close_key

    mov     qword [autostart_enabled], 1

.close_key:
    mov     rcx, [hRegKey]
    call    [RegCloseKey]

.done:
    add     rsp, 30h
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Toggle Windows autostart on / off
ToggleAutostart:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48h

    ; RegOpenKeyExA(HKEY_CURRENT_USER, szRegRunKey, 0, KEY_WRITE, &hRegKey)
    mov     rcx, HKEY_CURRENT_USER
    lea     rdx, [szRegRunKey]
    xor     r8d, r8d
    mov     r9d, KEY_WRITE
    lea     rax, [hRegKey]
    mov     qword [rsp+20h], rax
    call    [RegOpenKeyExA]
    test    eax, eax
    jnz     .done

    cmp     qword [autostart_enabled], 1
    je      .disable_autostart

    ; 1. GetModuleFileNameA(NULL, exe_path_buf, 260)
    xor     ecx, ecx
    lea     rdx, [exe_path_buf]
    mov     r8d, 260
    call    [GetModuleFileNameA]
    test    eax, eax
    jz      .close

    mov     r12d, eax           ; path length

    ; 2. Build quoted path: '"' + path + '"'
    mov     byte [quoted_path_buf], '"'
    lea     rsi, [exe_path_buf]
    lea     rdi, [quoted_path_buf + 1]
    mov     ecx, r12d
    rep movsb
    mov     byte [rdi], '"'
    mov     byte [rdi + 1], 0

    lea     r12d, [r12d + 3]    ; total bytes = len + '"' + '"' + null

    ; 3. RegSetValueExA(hRegKey, szRegRunVal, 0, REG_SZ, quoted_path_buf, cbData)
    mov     rcx, [hRegKey]
    lea     rdx, [szRegRunVal]
    xor     r8d, r8d
    mov     r9d, REG_SZ
    lea     rax, [quoted_path_buf]
    mov     qword [rsp+20h], rax
    mov     qword [rsp+28h], r12
    call    [RegSetValueExA]

    mov     qword [autostart_enabled], 1
    jmp     .close

.disable_autostart:
    ; RegDeleteValueA(hRegKey, szRegRunVal)
    mov     rcx, [hRegKey]
    lea     rdx, [szRegRunVal]
    call    [RegDeleteValueA]
    mov     qword [autostart_enabled], 0

.close:
    mov     rcx, [hRegKey]
    call    [RegCloseKey]

.done:
    add     rsp, 48h
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


;============================================================================;
;                           WINDOW PROCEDURE                                 ;
;============================================================================;
WindowProc:
    cmp     edx, WM_TRAYICON
    je      .wm_trayicon
    cmp     edx, 0x0111         ; WM_COMMAND
    je      .wm_command
    cmp     edx, 0x0002         ; WM_DESTROY
    je      .wm_destroy
    jmp     [DefWindowProcA]

.wm_trayicon:
    cmp     r9d, 0x0205         ; WM_RBUTTONUP
    je      .show_menu
    cmp     r9d, 0x0202         ; WM_LBUTTONUP
    je      .show_menu
    cmp     r9d, 0x007B         ; WM_CONTEXTMENU
    je      .show_menu
    xor     eax, eax
    ret

.show_menu:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 50h

    ; 1. Get physical cursor position (DPI-aware)
    lea     rcx, [cursor_pos]
    call    [GetCursorPos]
    movsxd  r12, dword [cursor_x]
    movsxd  r13, dword [cursor_y]

    test    r12d, r12d
    jnz     .got_pos
    test    r13d, r13d
    jnz     .got_pos

    ; Fallback: GetMessagePos
    call    [GetMessagePos]
    movsx   r12d, ax
    shr     eax, 16
    movsx   r13d, ax

.got_pos:
    mov     rcx, [hWnd]
    call    [SetForegroundWindow]

    call    [CreatePopupMenu]
    mov     [hMenu], rax

    ; Header
    mov     rcx, [hMenu]
    mov     edx, MF_STRING + MF_GRAYED
    xor     r8d, r8d
    lea     r9, [_menu_hdr]
    call    [AppendMenuA]

    ; Separator
    mov     rcx, [hMenu]
    mov     edx, MF_SEPARATOR
    xor     r8d, r8d
    xor     r9d, r9d
    call    [AppendMenuA]

    ; Auto-switch toggle item
    cmp     qword [auto_switch_enabled], 1
    jne     .auto_off
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_AUTO
    lea     r9, [_menu_auto_on]
    call    [AppendMenuA]
    jmp     .menu_sound
.auto_off:
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_AUTO
    lea     r9, [_menu_auto_off]
    call    [AppendMenuA]

.menu_sound:
    cmp     qword [sound_enabled], 1
    jne     .sound_off
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_SOUND
    lea     r9, [_menu_snd_on]
    call    [AppendMenuA]
    jmp     .menu_autostart
.sound_off:
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_SOUND
    lea     r9, [_menu_snd_off]
    call    [AppendMenuA]

.menu_autostart:
    ; Autostart with Windows toggle item
    cmp     qword [autostart_enabled], 1
    jne     .run_off
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_AUTOSTART
    lea     r9, [_menu_run_on]
    call    [AppendMenuA]
    jmp     .menu_rest
.run_off:
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_AUTOSTART
    lea     r9, [_menu_run_off]
    call    [AppendMenuA]

.menu_rest:
    ; Separator
    mov     rcx, [hMenu]
    mov     edx, MF_SEPARATOR
    xor     r8d, r8d
    xor     r9d, r9d
    call    [AppendMenuA]

    ; Manual Switch hotkey
    mov     rcx, [hMenu]
    mov     edx, MF_STRING + MF_GRAYED
    xor     r8d, r8d
    lea     r9, [_menu_hotkey]
    call    [AppendMenuA]

    ; Separator
    mov     rcx, [hMenu]
    mov     edx, MF_SEPARATOR
    xor     r8d, r8d
    xor     r9d, r9d
    call    [AppendMenuA]

    ; Exit
    mov     rcx, [hMenu]
    xor     edx, edx            ; MF_STRING
    mov     r8d, IDM_EXIT
    lea     r9, [_menu_exit]
    call    [AppendMenuA]

    ; TrackPopupMenu(hMenu, uFlags, x, y, nReserved, hWnd, prcRect)
    mov     rcx, [hMenu]
    mov     edx, TPM_BOTTOMALIGN or TPM_RIGHTBUTTON
    mov     r8d, r12d           ; X coordinate (at cursor)
    mov     r9d, r13d           ; Y coordinate (at cursor)
    mov     qword [rsp+20h], 0
    mov     rax, [hWnd]
    mov     qword [rsp+28h], rax
    mov     qword [rsp+30h], 0
    call    [TrackPopupMenu]

    mov     rcx, [hMenu]
    call    [DestroyMenu]

    ; Dismiss menu properly (MSDN KB135788)
    mov     rcx, [hWnd]
    xor     edx, edx            ; WM_NULL
    xor     r8d, r8d
    xor     r9d, r9d
    call    [PostMessageA]

    add     rsp, 50h
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    xor     eax, eax
    ret

.wm_command:
    movzx   eax, r8w            ; LOWORD(wParam)
    cmp     eax, IDM_AUTO
    je      .toggle_auto
    cmp     eax, IDM_SOUND
    je      .toggle_sound
    cmp     eax, IDM_AUTOSTART
    je      .toggle_run
    cmp     eax, IDM_EXIT
    je      .do_exit
    xor     eax, eax
    ret

.toggle_auto:
    xor     qword [auto_switch_enabled], 1
    xor     eax, eax
    ret

.toggle_sound:
    xor     qword [sound_enabled], 1
    xor     eax, eax
    ret

.toggle_run:
    sub     rsp, 28h
    call    ToggleAutostart
    add     rsp, 28h
    xor     eax, eax
    ret

.do_exit:
    sub     rsp, 28h
    xor     ecx, ecx
    call    [PostQuitMessage]
    add     rsp, 28h
    xor     eax, eax
    ret

.wm_destroy:
    sub     rsp, 28h
    xor     ecx, ecx
    call    [PostQuitMessage]
    add     rsp, 28h
    xor     eax, eax
    ret


;============================================================================;
;                     LOW-LEVEL KEYBOARD HOOK PROC                           ;
;============================================================================;
LowLevelKeyboardProc:
    ; RCX = nCode, RDX = wParam, R8 = lParam
    cmp     ecx, 0              ; HC_ACTION
    jl      .pass_hook

    cmp     edx, 0x0100         ; WM_KEYDOWN
    je      .process_key
    cmp     edx, 0x0104         ; WM_SYSKEYDOWN
    je      .process_key
    jmp     .pass_hook

.process_key:
    cmp     qword [is_processing], 1
    je      .pass_hook

    test    r8, r8
    jz      .pass_hook

    ; Save hook parameters on stack
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    rcx                 ; saved nCode
    push    rdx                 ; saved wParam
    push    r8                  ; saved lParam
    mov     rsi, r8             ; KBDLLHOOKSTRUCT pointer
    mov     ebx, [rsi]          ; vkCode
    mov     r12d, [rsi + 4]     ; scanCode
    sub     rsp, 28h

    ; 1. Hotkey: Pause/Break (0x13) or F8 (0x77)
    cmp     ebx, VK_PAUSE
    je      .handle_pause
    cmp     ebx, VK_F8
    je      .handle_f8

    ; 2. Control/Alt modifiers pressed - clear buffer
    mov     ecx, VK_CONTROL
    call    [GetAsyncKeyState]
    test    ax, ax
    jnz     .clear_buf

    mov     ecx, VK_MENU
    call    [GetAsyncKeyState]
    test    ax, ax
    jnz     .clear_buf

    ; 3. Navigation / Editing keys
    cmp     ebx, VK_TAB
    je      .clear_buf
    cmp     ebx, VK_ESCAPE
    je      .clear_buf
    cmp     ebx, 0x21           ; VK_PRIOR (Page Up)
    jb      .check_backspace
    cmp     ebx, 0x28           ; VK_DOWN
    jbe     .clear_buf
    cmp     ebx, 0x2E           ; VK_DELETE
    je      .clear_buf

.check_backspace:
    ; 4. Backspace: Undo last conversion OR remove char
    cmp     ebx, VK_BACK
    jne     .check_delimiters

    cmp     qword [can_undo], 1
    je      .do_undo

    cmp     qword [buffer_len], 0
    jz      .hook_pop_pass
    dec     qword [buffer_len]
    mov     qword [can_undo], 0
    jmp     .hook_pop_pass

.do_undo:
    mov     qword [can_undo], 0
    mov     qword [is_processing], 1

    ; Backspace converted word
    mov     rcx, [last_conv_len]
    call    SendBackspaces

    ; Replay original word
    lea     rcx, [orig_word_buf]
    mov     rdx, [last_conv_len]
    call    SendUnicodeString

    ; Switch layout back
    mov     rcx, [last_source_layout]
    call    SwitchKeyboardLayout

    mov     qword [is_processing], 0
    jmp     .hook_pop_pass

.check_delimiters:
    mov     qword [can_undo], 0

    ; 5. Space or Enter - Trigger word analysis
    cmp     ebx, VK_SPACE
    je      .trigger_analysis
    cmp     ebx, VK_RETURN
    je      .trigger_analysis
    jmp     .collect_char

.trigger_analysis:
    cmp     qword [auto_switch_enabled], 1
    jne     .clear_buf
    cmp     qword [buffer_len], 2
    jb      .clear_buf

    ; Analyze word
    call    GetCurrentLayout
    mov     r13, rax            ; current layout (0=EN, 1=RU)

    lea     rcx, [typed_buffer]
    mov     rdx, [buffer_len]
    mov     r8, r13
    call    AnalyzeWord
    test    eax, eax
    jz      .clear_buf

    ; Needs conversion!
    mov     qword [is_processing], 1

    ; Save original word for undo
    mov     rcx, [buffer_len]
    mov     [last_conv_len], rcx
    mov     [last_source_layout], r13

    lea     rsi, [typed_buffer]
    lea     rdi, [orig_word_buf]
    mov     rcx, [buffer_len]
    rep movsw

    ; Delete typed characters
    mov     rcx, [buffer_len]
    call    SendBackspaces

    ; Convert word
    cmp     r13, 0
    jne     .conv_to_en

    ; EN -> RU
    lea     rcx, [typed_buffer]
    lea     rdx, [conv_word_buf]
    mov     r8, [buffer_len]
    call    ConvertBufferToRu

    ; Type converted word
    lea     rcx, [conv_word_buf]
    mov     rdx, [buffer_len]
    call    SendUnicodeString

    ; Switch layout to RU
    mov     rcx, 1
    call    SwitchKeyboardLayout
    jmp     .finish_auto

.conv_to_en:
    ; RU -> EN
    lea     rcx, [typed_buffer]
    lea     rdx, [conv_word_buf]
    mov     r8, [buffer_len]
    call    ConvertBufferToEn

    ; Type converted word
    lea     rcx, [conv_word_buf]
    mov     rdx, [buffer_len]
    call    SendUnicodeString

    ; Switch layout to EN
    xor     ecx, ecx
    call    SwitchKeyboardLayout

.finish_auto:
    cmp     qword [sound_enabled], 1
    jne     .post_switch
    call    PlaySwitchSound

.post_switch:
    mov     qword [can_undo], 1
    mov     qword [buffer_len], 0
    mov     qword [is_processing], 0
    jmp     .hook_pop_pass

.collect_char:
    test    r12d, r12d
    jnz     .has_scan
    mov     ecx, ebx
    xor     edx, edx
    call    [MapVirtualKeyA]
    mov     r12d, eax
.has_scan:
    and     r12d, 0x7F
    cmp     r12d, 57
    ja      .hook_pop_pass

    ; Check Shift state
    mov     ecx, VK_SHIFT
    call    [GetAsyncKeyState]
    test    ax, ax
    setnz   bl                  ; bl = 1 if Shift

    ; Check CapsLock
    mov     ecx, VK_CAPITAL
    call    [GetKeyState]
    and     eax, 1
    mov     bh, al              ; bh = 1 if CapsLock

    call    GetCurrentLayout
    mov     r13, rax            ; layout

    ; Lookup in scan_table (8 bytes per entry)
    lea     rsi, [scan_table]
    movsxd  rax, r12d
    shl     rax, 3              ; rax = scan * 8

    cmp     r13, 1
    je      .ru_char

    ; EN Char
    xor     bl, bh              ; shift ^ caps
    test    bl, bl
    jnz     .en_shifted
    movzx   eax, word [rsi + rax + 0]
    jmp     .store_char
.en_shifted:
    movzx   eax, word [rsi + rax + 2]
    jmp     .store_char

.ru_char:
    xor     bl, bh              ; shift ^ caps
    test    bl, bl
    jnz     .ru_shifted
    movzx   eax, word [rsi + rax + 4]
    jmp     .store_char
.ru_shifted:
    movzx   eax, word [rsi + rax + 6]

.store_char:
    test    eax, eax
    jz      .hook_pop_pass

    ; Punctuation delimiters (.,;:)
    cmp     eax, '.'
    je      .punct_trigger
    cmp     eax, ','
    je      .punct_trigger
    cmp     eax, '!'
    je      .punct_trigger
    cmp     eax, '?'
    je      .punct_trigger
    cmp     eax, ';'
    je      .punct_trigger
    cmp     eax, ':'
    je      .punct_trigger

    ; Append to typed buffer
    mov     rcx, [buffer_len]
    cmp     rcx, 120
    jae     .hook_pop_pass

    mov     word [typed_buffer + rcx*2], ax
    inc     qword [buffer_len]
    mov     qword [can_undo], 0
    jmp     .hook_pop_pass

.punct_trigger:
    mov     rcx, [buffer_len]
    cmp     rcx, 120
    jae     .clear_buf
    mov     word [typed_buffer + rcx*2], ax
    inc     qword [buffer_len]
    jmp     .trigger_analysis

.handle_f8:
    ; F8: Only intercept if user just typed a word in buffer.
    ; If buffer is empty, let F8 pass directly through to Total Commander, VS Code, etc.!
    cmp     qword [buffer_len], 0
    jz      .hook_pop_pass
    jmp     .manual_switch

.handle_pause:
    ; Pause key: If buffer has a word, convert it. If empty, toggle active layout!
    cmp     qword [buffer_len], 0
    jnz     .manual_switch

    ; Empty buffer -> Toggle foreground window layout (EN <-> RU)
    mov     qword [is_processing], 1
    call    GetCurrentLayout
    xor     eax, 1              ; toggle 0 <-> 1
    mov     rcx, rax
    call    SwitchKeyboardLayout
    cmp     qword [sound_enabled], 1
    jne     .pause_done
    call    PlaySwitchSound
.pause_done:
    mov     qword [is_processing], 0
    jmp     .swallow_hotkey

.manual_switch:
    mov     qword [is_processing], 1
    cmp     qword [buffer_len], 0
    jz      .man_done

    call    GetCurrentLayout
    mov     r13, rax

    mov     rcx, [buffer_len]
    call    SendBackspaces

    cmp     r13, 0
    jne     .man_to_en

    ; EN -> RU
    lea     rcx, [typed_buffer]
    lea     rdx, [conv_word_buf]
    mov     r8, [buffer_len]
    call    ConvertBufferToRu

    lea     rcx, [conv_word_buf]
    mov     rdx, [buffer_len]
    call    SendUnicodeString

    mov     rcx, 1
    call    SwitchKeyboardLayout
    jmp     .man_finish

.man_to_en:
    lea     rcx, [typed_buffer]
    lea     rdx, [conv_word_buf]
    mov     r8, [buffer_len]
    call    ConvertBufferToEn

    lea     rcx, [conv_word_buf]
    mov     rdx, [buffer_len]
    call    SendUnicodeString

    xor     ecx, ecx
    call    SwitchKeyboardLayout

.man_finish:
    cmp     qword [sound_enabled], 1
    jne     .man_done
    call    PlaySwitchSound

.man_done:
    mov     qword [buffer_len], 0
    mov     qword [can_undo], 0
    mov     qword [is_processing], 0

.swallow_hotkey:
    add     rsp, 28h
    pop     r8
    pop     rdx
    pop     rcx
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx

    mov     eax, 1              ; swallow hotkey
    ret

.clear_buf:
    mov     qword [buffer_len], 0
    mov     qword [can_undo], 0

.hook_pop_pass:
    add     rsp, 28h
    pop     r8
    pop     rdx
    pop     rcx
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx

.pass_hook:
    sub     rsp, 28h
    mov     r9, r8              ; lParam
    mov     r8, rdx             ; wParam
    mov     edx, ecx            ; nCode
    mov     rcx, [hHook]        ; hHook
    call    [CallNextHookEx]
    add     rsp, 28h
    ret


;============================================================================;
;                              DATA SECTION                                  ;
;============================================================================;
section '.data' data readable writeable

_title          db 'PuntoSwitcher64', 0
_class          db 'PUNTO_SWITCHER_X64', 0
_tray_tip       db 'Punto Switcher x64', 0

_menu_hdr       db 'Punto Switcher x64', 0
_menu_auto_on   db 'Auto-switch: ON', 0
_menu_auto_off  db 'Auto-switch: OFF', 0
_menu_snd_on    db 'Sound: ON', 0
_menu_snd_off   db 'Sound: OFF', 0
_menu_run_on    db 'Autostart with Windows: ON', 0
_menu_run_off   db 'Autostart with Windows: OFF', 0
_menu_hotkey    db 'Manual Switch: Pause / F8', 0
_menu_exit      db 'Exit', 0

szUser32            db 'USER32.DLL', 0
szSetProcessDPIAware db 'SetProcessDPIAware', 0

szRegRunKey         db 'Software\Microsoft\Windows\CurrentVersion\Run', 0
szRegRunVal         db 'PuntoSwitcher64', 0

wszKlidEn       du '00000409', 0
wszKlidRu       du '00000419', 0

auto_switch_enabled dq 1
sound_enabled       dq 1
autostart_enabled   dq 0
is_processing       dq 0
can_undo            dq 0
buffer_len          dq 0
last_conv_len       dq 0
last_source_layout  dq 0

hInstance       dq ?
hAppIcon        dq ?
hkl_en          dq ?
hkl_ru          dq ?
hWnd            dq ?
hHook           dq ?
hMenu           dq ?
hRegKey         dq ?

wc  WNDCLASSEX
msg MSG
cursor_pos:
cursor_x dd 0
cursor_y dd 0
nid NOTIFYICONDATAA

exe_path_buf    rb 512
quoted_path_buf rb 512

;============================================================================;
;                              BSS SECTION                                   ;
;============================================================================;
section '.bss' readable writeable

typed_buffer    rw 256
orig_word_buf   rw 256
conv_word_buf   rw 256
temp_word_buf   rw 256
temp_norm_buf   rw 256
input_events    rb 40 * 256

;============================================================================;
;                             IMPORT SECTION                                 ;
;============================================================================;
section '.idata' import data readable writeable

library kernel32, 'KERNEL32.DLL', \
        user32,   'USER32.DLL',   \
        advapi32, 'ADVAPI32.DLL', \
        shell32,  'SHELL32.DLL'

include 'c:\asm\hdd\INCLUDE\api\kernel32.inc'
include 'c:\asm\hdd\INCLUDE\api\user32.inc'
include 'c:\asm\hdd\INCLUDE\api\advapi32.inc'
include 'c:\asm\hdd\INCLUDE\api\shell32.inc'

;============================================================================;
;                            RESOURCE SECTION                                ;
;============================================================================;
section '.rsrc' resource data readable

directory RT_ICON, icons, \
          RT_GROUP_ICON, group_icons

resource icons, \
         1, LANG_NEUTRAL, icon_data

resource group_icons, \
         1, LANG_NEUTRAL, main_icon

icon main_icon, icon_data, 'punto.ico'
