;============================================================================;
;                 PUNTO SWITCHER x64 — WINDOWS API HELPERS                   ;
;============================================================================;

VK_BACK    = 0x08
VK_TAB     = 0x09
VK_RETURN  = 0x0D
VK_SHIFT   = 0x10
VK_CONTROL = 0x11
VK_MENU    = 0x12
VK_PAUSE   = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE  = 0x1B
VK_SPACE   = 0x20
VK_LWIN    = 0x5B
VK_F8      = 0x77

WM_INPUTLANGCHANGEREQUEST = 0x0050
KLF_ACTIVATE              = 0x00000001
KLF_SETFORPROCESS         = 0x00000100

; Get current keyboard layout for the foreground window
; Returns RAX = 0 for EN, 1 for RU
GetCurrentLayout:
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 20h

    call    [GetForegroundWindow]
    test    rax, rax
    jz      .use_thread_0

    mov     rcx, rax
    xor     edx, edx
    call    [GetWindowThreadProcessId]
    mov     ecx, eax
    call    [GetKeyboardLayout]
    jmp     .check_hkl

.use_thread_0:
    xor     ecx, ecx
    call    [GetKeyboardLayout]

.check_hkl:
    test    rax, rax
    jz      .default_en

    ; Extract primary language ID (low 10 bits of low word)
    movzx   eax, ax
    and     eax, 0x03FF
    cmp     eax, 0x19       ; LANG_RUSSIAN
    je      .is_ru

.default_en:
    xor     eax, eax
    add     rsp, 20h
    pop     rdi
    pop     rsi
    pop     rbx
    ret

.is_ru:
    mov     eax, 1
    add     rsp, 20h
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Switch keyboard layout of the foreground window
; RCX = target_layout (0=EN, 1=RU)
SwitchKeyboardLayout:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 20h

    mov     r12, rcx        ; target_layout (0=EN, 1=RU)

    ; 1. Select target HKL
    cmp     r12, 1
    je      .load_ru
    mov     r13, [hkl_en]
    test    r13, r13
    jnz     .apply_hkl
    lea     rcx, [wszKlidEn]
    mov     edx, KLF_ACTIVATE
    call    [LoadKeyboardLayoutW]
    mov     r13, rax
    mov     [hkl_en], rax
    jmp     .apply_hkl

.load_ru:
    mov     r13, [hkl_ru]
    test    r13, r13
    jnz     .apply_hkl
    lea     rcx, [wszKlidRu]
    mov     edx, KLF_ACTIVATE
    call    [LoadKeyboardLayoutW]
    mov     r13, rax
    mov     [hkl_ru], rax

.apply_hkl:
    test    r13, r13
    jz      .done

    call    [GetForegroundWindow]
    mov     rbx, rax        ; hwnd
    test    rbx, rbx
    jz      .activate_self

    ; 2. PostMessageW directly to foreground window
    mov     rcx, rbx
    mov     edx, WM_INPUTLANGCHANGEREQUEST
    xor     r8d, r8d
    mov     r9, r13
    call    [PostMessageW]

    mov     rcx, rbx
    mov     edx, WM_INPUTLANGCHANGEREQUEST
    mov     r8d, 1
    mov     r9, r13
    call    [PostMessageW]

    ; 3. Get thread IDs
    call    [GetCurrentThreadId]
    mov     esi, eax        ; our_tid

    mov     rcx, rbx
    xor     edx, edx
    call    [GetWindowThreadProcessId]
    mov     edi, eax        ; target_tid

    test    edi, edi
    jz      .activate_self
    cmp     esi, edi
    je      .activate_self

    mov     ecx, esi
    mov     edx, edi
    mov     r8d, 1
    call    [AttachThreadInput]

    ; Get focused control (e.g. edit control in Notepad/Chrome/VS Code)
    call    [GetFocus]
    mov     r14, rax

    test    r14, r14
    jz      .activate_attached

    mov     rcx, r14
    mov     edx, WM_INPUTLANGCHANGEREQUEST
    xor     r8d, r8d
    mov     r9, r13
    call    [PostMessageW]

    mov     rcx, r14
    mov     edx, WM_INPUTLANGCHANGEREQUEST
    mov     r8d, 1
    mov     r9, r13
    call    [PostMessageW]

.activate_attached:
    mov     rcx, r13
    mov     edx, KLF_ACTIVATE + KLF_SETFORPROCESS
    call    [ActivateKeyboardLayout]

    mov     ecx, esi
    mov     edx, edi
    xor     r8d, r8d
    call    [AttachThreadInput]
    jmp     .done

.activate_self:
    mov     rcx, r13
    mov     edx, KLF_ACTIVATE + KLF_SETFORPROCESS
    call    [ActivateKeyboardLayout]

.done:
    add     rsp, 20h
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Send Backspaces using SendInput (batched)
; RCX = count
SendBackspaces:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 20h

    mov     r12, rcx
    test    r12, r12
    jz      .done
    cmp     r12, 100
    ja      .done

    lea     rdi, [input_events]
    xor     rbx, rbx
.loop:
    cmp     rbx, r12
    jae     .send

    ; Key Down
    mov     dword [rdi + 0], 1          ; type = INPUT_KEYBOARD
    mov     dword [rdi + 4], 0
    mov     word  [rdi + 8], VK_BACK    ; wVk
    mov     word  [rdi + 10], 0         ; wScan
    mov     dword [rdi + 12], 0         ; dwFlags = 0 (down)
    mov     dword [rdi + 16], 0
    mov     dword [rdi + 20], 0
    mov     qword [rdi + 24], 0
    mov     qword [rdi + 32], 0

    ; Key Up
    mov     dword [rdi + 40 + 0], 1     ; type = INPUT_KEYBOARD
    mov     dword [rdi + 40 + 4], 0
    mov     word  [rdi + 40 + 8], VK_BACK ; wVk
    mov     word  [rdi + 40 + 10], 0    ; wScan
    mov     dword [rdi + 40 + 12], 2    ; dwFlags = KEYEVENTF_KEYUP
    mov     dword [rdi + 40 + 16], 0
    mov     dword [rdi + 40 + 20], 0
    mov     qword [rdi + 40 + 24], 0
    mov     qword [rdi + 40 + 32], 0

    add     rdi, 80                     ; 2 structs * 40 bytes
    inc     rbx
    jmp     .loop

.send:
    mov     rax, r12
    shl     rax, 1                      ; count * 2
    mov     rcx, rax
    lea     rdx, [input_events]
    mov     r8d, 40
    call    [SendInput]

.done:
    add     rsp, 20h
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Send a string of UTF-16 characters using SendInput (batched)
; RCX = p_chars (UTF-16), RDX = count
SendUnicodeString:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 20h

    mov     rsi, rcx
    mov     r12, rdx
    test    r12, r12
    jz      .done
    cmp     r12, 100
    ja      .done

    lea     rdi, [input_events]
    xor     rbx, rbx
.loop:
    cmp     rbx, r12
    jae     .send

    movzx   eax, word [rsi + rbx*2]     ; Unicode char

    ; Key Down (KEYEVENTF_UNICODE = 4)
    mov     dword [rdi + 0], 1
    mov     dword [rdi + 4], 0
    mov     word  [rdi + 8], 0          ; wVk = 0
    mov     word  [rdi + 10], ax        ; wScan = unicode char
    mov     dword [rdi + 12], 4         ; dwFlags = KEYEVENTF_UNICODE
    mov     dword [rdi + 16], 0
    mov     dword [rdi + 20], 0
    mov     qword [rdi + 24], 0
    mov     qword [rdi + 32], 0

    ; Key Up (KEYEVENTF_UNICODE | KEYEVENTF_KEYUP = 6)
    mov     dword [rdi + 40 + 0], 1
    mov     dword [rdi + 40 + 4], 0
    mov     word  [rdi + 40 + 8], 0
    mov     word  [rdi + 40 + 10], ax
    mov     dword [rdi + 40 + 12], 6     ; KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    mov     dword [rdi + 40 + 16], 0
    mov     dword [rdi + 40 + 20], 0
    mov     qword [rdi + 40 + 24], 0
    mov     qword [rdi + 40 + 32], 0

    add     rdi, 80
    inc     rbx
    jmp     .loop

.send:
    mov     rax, r12
    shl     rax, 1                      ; count * 2
    mov     rcx, rax
    lea     rdx, [input_events]
    mov     r8d, 40
    call    [SendInput]

.done:
    add     rsp, 20h
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Play subtle sound notification
PlaySwitchSound:
    sub     rsp, 28h
    xor     ecx, ecx
    call    [MessageBeep]
    add     rsp, 28h
    ret
