"""Win64 native 2D game engine runtime (GDI double-buffered backbuffer + events + input) for pygame."""

WIN64_PYGAME_RUNTIME_DATA = """
    ; --- Native Pygame Win32 GDI Runtime Data ---
    align 8
    _pyfasm_pg_class_w      du 'PyFasmPygameClassW', 0
    _pyfasm_pg_title_w      du 'PyFASM Pygame Window', 0
    align 8
    _pyfasm_pg_hwnd         dq 0
    _pyfasm_pg_mem_dc       dq 0
    _pyfasm_pg_bmp          dq 0
    _pyfasm_pg_old_bmp      dq 0
    _pyfasm_pg_width        dq 800
    _pyfasm_pg_height       dq 600
    _pyfasm_pg_last_tick    dq 0
    _pyfasm_pg_ev_head      dq 0
    _pyfasm_pg_ev_tail      dq 0
    _pyfasm_pg_mouse_x      dq 0
    _pyfasm_pg_mouse_y      dq 0
    _pyfasm_pg_running      dq 1
    align 8
    _pyfasm_pg_wc           rb 80
    _pyfasm_pg_msg          rb 48
    _pyfasm_pg_ps           rb 80
    _pyfasm_pg_rc           rd 4
    _pyfasm_pg_pt           rd 4
    align 8
    _pyfasm_pg_keys_arr     rq 260
    align 8
    ; Circular queue of 64 events: each slot = [qword type, qword key, qword x, qword y] (32 bytes)
    _pyfasm_pg_ev_queue     rb 2048
"""

WIN64_PYGAME_RUNTIME_CODE = """
_pyfasm_pg_enqueue_ev:
    ; RCX = ev_type, RDX = key, R8 = x, R9 = y
    push    rbp
    mov     rbp, rsp
    push    rbx
    mov     rax, [_pyfasm_pg_ev_tail]
    mov     rbx, rax
    and     rbx, 63
    shl     rbx, 5
    lea     r10, [_pyfasm_pg_ev_queue + rbx]
    mov     [r10], rcx
    mov     [r10 + 8], rdx
    mov     [r10 + 16], r8
    mov     [r10 + 24], r9
    inc     qword [_pyfasm_pg_ev_tail]
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_vk_to_py:
    ; RCX = Win32 VK -> RAX = Pygame K_* keycode
    mov     eax, ecx
    cmp     eax, 41h                ; 'A'
    jb      .pvk_done
    cmp     eax, 5Ah                ; 'Z'
    ja      .pvk_done
    add     eax, 32                 ; normalize to lowercase ASCII 'a'..'z' (Pygame K_a..K_z)
.pvk_done:
    ret

_pyfasm_pg_wnd_proc:
    ; RCX = hwnd, RDX = uMsg, R8 = wParam, R9 = lParam
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 80
    and     rsp, -16

    cmp     edx, 000Fh              ; WM_PAINT
    je      .pg_paint
    cmp     edx, 0014h              ; WM_ERASEBKGND
    je      .pg_erase
    cmp     edx, 0100h              ; WM_KEYDOWN
    je      .pg_keydown
    cmp     edx, 0104h              ; WM_SYSKEYDOWN
    je      .pg_keydown
    cmp     edx, 0101h              ; WM_KEYUP
    je      .pg_keyup
    cmp     edx, 0201h              ; WM_LBUTTONDOWN
    je      .pg_mdown
    cmp     edx, 0202h              ; WM_LBUTTONUP
    je      .pg_mup
    cmp     edx, 0200h              ; WM_MOUSEMOVE
    je      .pg_mmove
    cmp     edx, 0010h              ; WM_CLOSE
    je      .pg_close
    cmp     edx, 0002h              ; WM_DESTROY
    je      .pg_destroy

    call    [DefWindowProcW]
    jmp     .pg_wp_done

.pg_erase:
    mov     rax, 1
    jmp     .pg_wp_done

.pg_paint:
    mov     rbx, rcx
    lea     rdx, [_pyfasm_pg_ps]
    call    [BeginPaint]
    mov     rsi, rax
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pg_end_paint
    mov     rcx, rsi
    xor     edx, edx
    xor     r8d, r8d
    mov     r9, [_pyfasm_pg_width]
    mov     rax, [_pyfasm_pg_height]
    mov     [rsp + 32], rax
    mov     rax, [_pyfasm_pg_mem_dc]
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 00CC0020h ; SRCCOPY
    call    [BitBlt]
.pg_end_paint:
    mov     rcx, rbx
    lea     rdx, [_pyfasm_pg_ps]
    call    [EndPaint]
    xor     eax, eax
    jmp     .pg_wp_done

.pg_keydown:
    mov     rcx, r8
    call    _pyfasm_pg_vk_to_py
    mov     rdx, rax
    mov     ecx, 768                ; pygame.KEYDOWN
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_pg_enqueue_ev
    xor     eax, eax
    jmp     .pg_wp_done

.pg_keyup:
    mov     rcx, r8
    call    _pyfasm_pg_vk_to_py
    mov     rdx, rax
    mov     ecx, 769                ; pygame.KEYUP
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_pg_enqueue_ev
    xor     eax, eax
    jmp     .pg_wp_done

.pg_mdown:
    movzx   r8d, r9w
    shr     r9, 16
    movzx   r9d, r9w
    mov     [_pyfasm_pg_mouse_x], r8
    mov     [_pyfasm_pg_mouse_y], r9
    mov     ecx, 1025               ; pygame.MOUSEBUTTONDOWN
    mov     edx, 1
    call    _pyfasm_pg_enqueue_ev
    xor     eax, eax
    jmp     .pg_wp_done

.pg_mup:
    movzx   r8d, r9w
    shr     r9, 16
    movzx   r9d, r9w
    mov     [_pyfasm_pg_mouse_x], r8
    mov     [_pyfasm_pg_mouse_y], r9
    mov     ecx, 1026               ; pygame.MOUSEBUTTONUP
    mov     edx, 1
    call    _pyfasm_pg_enqueue_ev
    xor     eax, eax
    jmp     .pg_wp_done

.pg_mmove:
    movzx   r8d, r9w
    shr     r9, 16
    movzx   r9d, r9w
    mov     [_pyfasm_pg_mouse_x], r8
    mov     [_pyfasm_pg_mouse_y], r9
    xor     eax, eax
    jmp     .pg_wp_done

.pg_close:
    mov     rbx, rcx
    mov     ecx, 256                ; pygame.QUIT
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_pg_enqueue_ev
    mov     rcx, rbx
    call    [DestroyWindow]
    xor     eax, eax
    jmp     .pg_wp_done

.pg_destroy:
    mov     ecx, 256                ; pygame.QUIT
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    call    _pyfasm_pg_enqueue_ev
    xor     ecx, ecx
    call    [PostQuitMessage]
    xor     eax, eax

.pg_wp_done:
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_init:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    call    [GetTickCount64]
    mov     [_pyfasm_pg_last_tick], rax
    mov     qword [_pyfasm_pg_ev_head], 0
    mov     qword [_pyfasm_pg_ev_tail], 0
    mov     qword [_pyfasm_pg_running], 1
    mov     rax, 1
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_set_mode:
    ; RCX = size_tuple_or_width (if >= 65536 and [rcx]>=2 then (w, h), else rcx=w, rdx=h)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 112
    and     rsp, -16

    mov     rsi, 800
    mov     rdi, 600
    cmp     rcx, 65536
    jb      .psm_direct_wh
    cmp     qword [rcx], 2
    jl      .psm_direct_wh
    mov     rsi, [rcx + 8]
    mov     rdi, [rcx + 16]
    jmp     .psm_wh_ready
.psm_direct_wh:
    test    rcx, rcx
    jz      .psm_wh_ready
    mov     rsi, rcx
    test    rdx, rdx
    jz      .psm_wh_ready
    mov     rdi, rdx
.psm_wh_ready:
    test    rsi, rsi
    jg      .psm_w_ok
    mov     rsi, 800
.psm_w_ok:
    test    rdi, rdi
    jg      .psm_h_ok
    mov     rdi, 600
.psm_h_ok:
    mov     [_pyfasm_pg_width], rsi
    mov     [_pyfasm_pg_height], rdi

    ; Register WNDCLASSEXW
    xor     ecx, ecx
    call    [GetModuleHandleA]
    mov     rbx, rax

    xor     ecx, ecx
    mov     edx, 32512              ; IDC_ARROW
    call    [LoadCursorA]
    mov     r11, rax

    mov     dword [_pyfasm_pg_wc], 80
    mov     dword [_pyfasm_pg_wc + 4], 3
    lea     rax, [_pyfasm_pg_wnd_proc]
    mov     qword [_pyfasm_pg_wc + 8], rax
    mov     dword [_pyfasm_pg_wc + 16], 0
    mov     dword [_pyfasm_pg_wc + 20], 0
    mov     qword [_pyfasm_pg_wc + 24], rbx
    mov     qword [_pyfasm_pg_wc + 32], 0
    mov     qword [_pyfasm_pg_wc + 40], r11
    mov     qword [_pyfasm_pg_wc + 48], 0
    mov     qword [_pyfasm_pg_wc + 56], 0
    lea     rax, [_pyfasm_pg_class_w]
    mov     qword [_pyfasm_pg_wc + 64], rax
    mov     qword [_pyfasm_pg_wc + 72], 0

    lea     rcx, [_pyfasm_pg_wc]
    call    [RegisterClassExW]

    ; Compute outer window rect from desired client width x height
    mov     dword [_pyfasm_pg_rc], 0
    mov     dword [_pyfasm_pg_rc + 4], 0
    mov     dword [_pyfasm_pg_rc + 8], esi
    mov     dword [_pyfasm_pg_rc + 12], edi
    lea     rcx, [_pyfasm_pg_rc]
    mov     edx, 00CA0000h          ; WS_OVERLAPPEDWINDOW without maximize resize clutter (WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX)
    xor     r8d, r8d
    xor     r9d, r9d
    call    [AdjustWindowRectEx]

    mov     r10d, dword [_pyfasm_pg_rc + 8]
    sub     r10d, dword [_pyfasm_pg_rc]
    mov     r11d, dword [_pyfasm_pg_rc + 12]
    sub     r11d, dword [_pyfasm_pg_rc + 4]

    xor     ecx, ecx
    lea     rdx, [_pyfasm_pg_class_w]
    lea     r8, [_pyfasm_pg_title_w]
    mov     r9d, 10CA0000h          ; WS_VISIBLE | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX
    mov     eax, 80000000h
    cdqe
    mov     [rsp + 32], rax
    mov     [rsp + 40], rax
    mov     [rsp + 48], r10
    mov     [rsp + 56], r11
    mov     qword [rsp + 64], 0
    mov     qword [rsp + 72], 0
    mov     [rsp + 80], rbx
    mov     qword [rsp + 88], 0
    call    [CreateWindowExW]
    mov     [_pyfasm_pg_hwnd], rax

    ; Dark title bar (optional DWM)
    test    rax, rax
    jz      .psm_ret_zero
    mov     rcx, rax
    call    [GetDC]
    mov     rbx, rax
    mov     rcx, rbx
    call    [CreateCompatibleDC]
    mov     [_pyfasm_pg_mem_dc], rax

    mov     rcx, rbx
    mov     rdx, rsi
    mov     r8, rdi
    call    [CreateCompatibleBitmap]
    mov     [_pyfasm_pg_bmp], rax

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rax
    call    [SelectObject]
    mov     [_pyfasm_pg_old_bmp], rax

    mov     rcx, [_pyfasm_pg_hwnd]
    mov     rdx, rbx
    call    [ReleaseDC]

    mov     rcx, [_pyfasm_pg_hwnd]
    mov     edx, 5
    call    [ShowWindow]
    mov     rcx, [_pyfasm_pg_hwnd]
    call    [UpdateWindow]

    mov     rax, [_pyfasm_pg_hwnd]
    jmp     .psm_exit
.psm_ret_zero:
    xor     eax, eax
.psm_exit:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_set_caption:
    ; RCX = utf8 title string
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    test    rcx, rcx
    jz      .psc_done
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    mov     rcx, [_pyfasm_pg_hwnd]
    test    rcx, rcx
    jz      .psc_done
    lea     rdx, [_pyfasm_wide_buf]
    call    [SetWindowTextW]
.psc_done:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_unpack_color:
    ; RCX = tuple (r, g, b) or int 0xRRGGBB -> EAX = Win32 COLORREF (0x00BBGGRR)
    cmp     rcx, 65536
    jb      .puc_int
    cmp     qword [rcx], 3
    jl      .puc_int
    mov     r8, [rcx + 8]           ; R
    mov     r9, [rcx + 16]          ; G
    mov     r10, [rcx + 24]         ; B
    and     r8d, 0FFh
    and     r9d, 0FFh
    and     r10d, 0FFh
    shl     r10d, 16
    shl     r9d, 8
    mov     eax, r8d
    or      eax, r9d
    or      eax, r10d
    ret
.puc_int:
    mov     eax, ecx
    mov     r8d, eax
    shr     r8d, 16
    and     r8d, 0FFh               ; R
    mov     r9d, eax
    and     r9d, 0000FF00h          ; G << 8
    mov     r10d, eax
    and     r10d, 0FFh
    shl     r10d, 16                ; B << 16
    mov     eax, r8d
    or      eax, r9d
    or      eax, r10d
    ret

_pyfasm_pg_unpack_rect:
    ; RCX = pygame.Rect pointer or 4-tuple (x, y, w, h) -> writes _pyfasm_pg_rc [left, top, right, bottom]
    test    rcx, rcx
    jz      .pur_zero
    cmp     rcx, 65536
    jb      .pur_zero
    mov     rax, 5059465245435421h  ; 'PYFRECT!'
    cmp     [rcx], rax
    je      .pur_rect_obj
    cmp     qword [rcx], 4
    jl      .pur_rect_obj
    mov     eax, dword [rcx + 8]    ; x
    mov     edx, dword [rcx + 16]   ; y
    mov     r8d, dword [rcx + 24]   ; w
    mov     r9d, dword [rcx + 32]   ; h
    jmp     .pur_store
.pur_rect_obj:
    mov     eax, dword [rcx + 48]   ; obj.x
    mov     edx, dword [rcx + 56]   ; obj.y
    mov     r8d, dword [rcx + 64]   ; obj.w
    mov     r9d, dword [rcx + 72]   ; obj.h
.pur_store:
    mov     dword [_pyfasm_pg_rc], eax
    mov     dword [_pyfasm_pg_rc + 4], edx
    add     eax, r8d
    add     edx, r9d
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     dword [_pyfasm_pg_rc + 12], edx
    ret
.pur_zero:
    xor     eax, eax
    mov     dword [_pyfasm_pg_rc], eax
    mov     dword [_pyfasm_pg_rc + 4], eax
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     dword [_pyfasm_pg_rc + 12], eax
    ret

_pyfasm_pg_fill:
    ; RCX = surface, RDX = color
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pf_done
    mov     rcx, rdx
    call    _pyfasm_pg_unpack_color
    mov     ecx, eax
    call    [CreateSolidBrush]
    mov     rbx, rax
    mov     dword [_pyfasm_pg_rc], 0
    mov     dword [_pyfasm_pg_rc + 4], 0
    mov     eax, dword [_pyfasm_pg_width]
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     eax, dword [_pyfasm_pg_height]
    mov     dword [_pyfasm_pg_rc + 12], eax
    mov     rcx, [_pyfasm_pg_mem_dc]
    lea     rdx, [_pyfasm_pg_rc]
    mov     r8, rbx
    call    [FillRect]
    mov     rcx, rbx
    call    [DeleteObject]
.pf_done:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_draw_rect:
    ; RCX = surf, RDX = color, R8 = rect, R9 = border_width
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pdr_done
    mov     rbx, rdx
    mov     r12, r9
    mov     rcx, r8
    call    _pyfasm_pg_unpack_rect
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    test    r12, r12
    jnz     .pdr_outline
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     rsi, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    lea     rdx, [_pyfasm_pg_rc]
    mov     r8, rsi
    call    [FillRect]
    mov     rcx, rsi
    call    [DeleteObject]
    jmp     .pdr_done

.pdr_outline:
    xor     ecx, ecx
    mov     edx, r12d
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    mov     ecx, 5                  ; NULL_BRUSH
    call    [GetStockObject]
    mov     rdi, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rsi
    call    [SelectObject]
    mov     rbx, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rdi
    call    [SelectObject]
    mov     rdi, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], rax
    call    [Rectangle]
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rbx
    call    [SelectObject]
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rdi
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]

.pdr_done:
    xor     eax, eax
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_draw_circle:
    ; RCX = surf, RDX = color, R8 = center (x, y), R9 = radius, [rbp+48] = width
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 64
    and     rsp, -16
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pdc_done

    xor     r12d, r12d
    xor     r13d, r13d
    cmp     r8, 65536
    jb      .pdc_got_center
    cmp     qword [r8], 2
    jl      .pdc_got_center
    mov     r12d, dword [r8 + 8]
    mov     r13d, dword [r8 + 16]
.pdc_got_center:
    mov     eax, r12d
    sub     eax, r9d
    mov     dword [_pyfasm_pg_rc], eax
    mov     eax, r13d
    sub     eax, r9d
    mov     dword [_pyfasm_pg_rc + 4], eax
    mov     eax, r12d
    add     eax, r9d
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     eax, r13d
    add     eax, r9d
    mov     dword [_pyfasm_pg_rc + 12], eax

    mov     rcx, rdx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     rdi, rax

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rsi
    call    [SelectObject]
    mov     r12, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rdi
    call    [SelectObject]
    mov     r13, rax

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], rax
    call    [Ellipse]

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, r12
    call    [SelectObject]
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, r13
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
    mov     rcx, rdi
    call    [DeleteObject]

.pdc_done:
    xor     eax, eax
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_draw_line:
    ; RCX = surf, RDX = color, R8 = p1 (x,y), R9 = p2 (x,y), [rbp+48] = width
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    sub     rsp, 64
    and     rsp, -16
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pdl_done
    mov     r12, r8
    mov     r13, r9
    mov     rcx, rdx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    mov     edx, dword [rbp + 48]
    test    edx, edx
    jg      .pdl_w_ok
    mov     edx, 1
.pdl_w_ok:
    xor     ecx, ecx
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rsi
    call    [SelectObject]
    mov     rbx, rax

    xor     edx, edx
    xor     r8d, r8d
    cmp     r12, 65536
    jb      .pdl_m1
    mov     edx, dword [r12 + 8]
    mov     r8d, dword [r12 + 16]
.pdl_m1:
    mov     rcx, [_pyfasm_pg_mem_dc]
    xor     r9d, r9d
    call    [MoveToEx]

    xor     edx, edx
    xor     r8d, r8d
    cmp     r13, 65536
    jb      .pdl_l2
    mov     edx, dword [r13 + 8]
    mov     r8d, dword [r13 + 16]
.pdl_l2:
    mov     rcx, [_pyfasm_pg_mem_dc]
    call    [LineTo]

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rbx
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]

.pdl_done:
    xor     eax, eax
    lea     rsp, [rbp - 32]
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_draw_ellipse:
    ; RCX = surf, RDX = color, R8 = rect, R9 = width
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    sub     rsp, 64
    and     rsp, -16
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pde_done
    mov     rbx, rdx
    mov     rcx, r8
    call    _pyfasm_pg_unpack_rect
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    xor     ecx, ecx
    mov     edx, 1
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     rdi, rax

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rsi
    call    [SelectObject]
    mov     r12, rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, rdi
    call    [SelectObject]
    mov     r13, rax

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], rax
    call    [Ellipse]

    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, r12
    call    [SelectObject]
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, r13
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
    mov     rcx, rdi
    call    [DeleteObject]

.pde_done:
    xor     eax, eax
    lea     rsp, [rbp - 40]
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_font_render:
    ; RCX = text_str, RDX = color -> RAX = text_surf [magic, text_str, colorref]
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rcx, rdx
    call    _pyfasm_pg_unpack_color
    mov     esi, eax
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     rdx, 5059465047545854h  ; 'PYFPGTXT'
    mov     [rax], rdx
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_blit:
    ; RCX = screen_surf, RDX = text_surf_or_str, R8 = dest (x, y) or Rect
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 64
    and     rsp, -16
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pb_done
    test    rdx, rdx
    jz      .pb_done
    cmp     rdx, 65536
    jb      .pb_done

    xor     esi, esi
    xor     edi, edi
    cmp     r8, 65536
    jb      .pb_pos_ready
    mov     rax, 5059465245435421h
    cmp     [r8], rax
    je      .pb_pos_rect
    mov     esi, dword [r8 + 8]
    mov     edi, dword [r8 + 16]
    jmp     .pb_pos_ready
.pb_pos_rect:
    mov     esi, dword [r8 + 48]
    mov     edi, dword [r8 + 56]
.pb_pos_ready:

    mov     rax, 5059465047545854h  ; 'PYFPGTXT'
    cmp     [rdx], rax
    jne     .pb_raw_str
    mov     r10d, dword [rdx + 16]
    mov     rbx, [rdx + 8]
    jmp     .pb_draw_text
.pb_raw_str:
    mov     r10d, 00FFFFFFh
    mov     rbx, rdx

.pb_draw_text:
    test    rbx, rbx
    jz      .pb_done
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     edx, r10d
    call    [SetTextColor]
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]
    mov     rcx, rbx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    mov     [rsp + 48], rax
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     edx, esi
    mov     r8d, edi
    lea     r9, [_pyfasm_wide_buf]
    mov     rax, [rsp + 48]
    mov     [rsp + 32], rax
    call    [TextOutW]

.pb_done:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_pump_messages:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
.ppm_loop:
    lea     rcx, [_pyfasm_pg_msg]
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    mov     qword [rsp + 32], 1     ; PM_REMOVE
    call    [PeekMessageW]
    test    eax, eax
    jz      .ppm_done
    lea     rcx, [_pyfasm_pg_msg]
    call    [TranslateMessage]
    lea     rcx, [_pyfasm_pg_msg]
    call    [DispatchMessageW]
    jmp     .ppm_loop
.ppm_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_flip:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 88
    and     rsp, -16
    call    _pyfasm_pg_pump_messages
    mov     rax, [_pyfasm_pg_hwnd]
    test    rax, rax
    jz      .pfl_done
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pfl_done
    mov     rcx, rax
    call    [GetDC]
    mov     rbx, rax
    test    rbx, rbx
    jz      .pfl_done
    mov     rcx, rbx
    xor     edx, edx
    xor     r8d, r8d
    mov     r9, [_pyfasm_pg_width]
    mov     rax, [_pyfasm_pg_height]
    mov     [rsp + 32], rax
    mov     rax, [_pyfasm_pg_mem_dc]
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 00CC0020h
    call    [BitBlt]
    mov     rcx, [_pyfasm_pg_hwnd]
    mov     rdx, rbx
    call    [ReleaseDC]
.pfl_done:
    xor     eax, eax
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_poll_events:
    ; Drains queued events and returns PyFASM list pointer [count, ev0, ev1, ...]
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 48
    and     rsp, -16
    call    _pyfasm_pg_pump_messages

    mov     rsi, [_pyfasm_pg_ev_head]
    mov     rdi, [_pyfasm_pg_ev_tail]
    mov     rbx, rdi
    sub     rbx, rsi
    test    rbx, rbx
    jg      .ppe_has_cnt
    xor     ebx, ebx
    jmp     .ppe_alloc_list
.ppe_has_cnt:
    cmp     rbx, 64
    jle     .ppe_alloc_list
    mov     rbx, 64
    mov     rsi, rdi
    sub     rsi, 64

.ppe_alloc_list:
    lea     rcx, [rbx + 1]
    shl     rcx, 3
    call    _pyfasm_alloc
    mov     r12, rax
    mov     [r12], rbx
    xor     ecx, ecx
.ppe_fill:
    cmp     rcx, rbx
    jge     .ppe_done
    mov     [rsp + 32], rcx
    mov     ecx, 80
    call    _pyfasm_alloc
    mov     rcx, [rsp + 32]
    lea     rdx, [rsi + rcx]
    and     rdx, 63
    shl     rdx, 5
    lea     r10, [_pyfasm_pg_ev_queue + rdx]
    mov     r8, [r10]               ; type
    mov     [rax + 32], r8
    mov     r8, [r10 + 8]           ; key
    mov     [rax + 40], r8
    mov     r8, [r10 + 16]          ; x
    mov     [rax + 48], r8
    mov     r8, [r10 + 24]          ; y
    mov     [rax + 56], r8
    mov     [r12 + rcx * 8 + 8], rax
    inc     rcx
    jmp     .ppe_fill

.ppe_done:
    mov     [_pyfasm_pg_ev_head], rdi
    mov     rax, r12
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_get_pressed:
    ; Returns 256-slot PyFASM list [256, k0, ...] with bit 0x8000 mapped to 1/0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    mov     qword [_pyfasm_pg_keys_arr], 256
    xor     ebx, ebx
.pgp_loop:
    cmp     ebx, 256
    jge     .pgp_done
    mov     ecx, ebx
    cmp     ecx, 'a'
    jb      .pgp_chk
    cmp     ecx, 'z'
    ja      .pgp_chk
    sub     ecx, 32                 ; map lowercase K_a..K_z -> VK 'A'..'Z'
.pgp_chk:
    call    [GetAsyncKeyState]
    shr     ax, 15
    and     eax, 1
    mov     [_pyfasm_pg_keys_arr + rbx * 8 + 8], rax
    inc     ebx
    jmp     .pgp_loop
.pgp_done:
    lea     rax, [_pyfasm_pg_keys_arr]
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_mouse_get_pos:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 48
    and     rsp, -16
    lea     rcx, [_pyfasm_pg_pt]
    call    [GetCursorPos]
    mov     rcx, [_pyfasm_pg_hwnd]
    test    rcx, rcx
    jz      .pmgp_alloc
    lea     rdx, [_pyfasm_pg_pt]
    call    [ScreenToClient]
.pmgp_alloc:
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     qword [rax], 2
    movsxd  rcx, dword [_pyfasm_pg_pt]
    mov     [rax + 8], rcx
    movsxd  rcx, dword [_pyfasm_pg_pt + 4]
    mov     [rax + 16], rcx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_mouse_get_pressed:
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    and     rsp, -16
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     qword [rbx], 3
    mov     ecx, 1                  ; VK_LBUTTON
    call    [GetAsyncKeyState]
    shr     ax, 15
    and     eax, 1
    mov     [rbx + 8], rax
    mov     ecx, 4                  ; VK_MBUTTON
    call    [GetAsyncKeyState]
    shr     ax, 15
    and     eax, 1
    mov     [rbx + 16], rax
    mov     ecx, 2                  ; VK_RBUTTON
    call    [GetAsyncKeyState]
    shr     ax, 15
    and     eax, 1
    mov     [rbx + 24], rax
    mov     rax, rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_clock_tick:
    ; RCX = clock (unused), RDX = fps -> returns elapsed ms
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rdx                ; fps
    call    [GetTickCount64]
    mov     rsi, rax                ; now
    mov     rcx, rsi
    sub     rcx, [_pyfasm_pg_last_tick]
    test    rbx, rbx
    jle     .pct_done
    mov     rax, 1000
    xor     edx, edx
    div     rbx                     ; target ms = 1000 / fps
    cmp     rcx, rax
    jge     .pct_done
    sub     rax, rcx
    mov     rcx, rax
    call    [Sleep]
    call    [GetTickCount64]
    mov     rsi, rax
    mov     rcx, rsi
    sub     rcx, [_pyfasm_pg_last_tick]
.pct_done:
    mov     [_pyfasm_pg_last_tick], rsi
    mov     rax, rcx
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_get_ticks:
    sub     rsp, 40
    call    [GetTickCount64]
    add     rsp, 40
    ret

_pyfasm_pg_delay:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     rax, rcx
    test    rcx, rcx
    jle     .pd_done
    call    [Sleep]
.pd_done:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_rect_new:
    ; RCX = x, RDX = y, R8 = w, R9 = h
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
    mov     r12, r9
    mov     ecx, 96
    call    _pyfasm_alloc
    mov     rcx, 5059465245435421h  ; 'PYFRECT!'
    mov     [rax], rcx
    mov     [rax + 48], rbx
    mov     [rax + 56], rsi
    mov     [rax + 64], rdi
    mov     [rax + 72], r12
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_rect_colliderect:
    ; RCX = rect_a, RDX = rect_b -> RAX = 1 if intersecting else 0
    test    rcx, rcx
    jz      .prc_false
    test    rdx, rdx
    jz      .prc_false
    mov     r8, [rcx + 48]          ; a.x
    mov     r9, [rcx + 64]
    add     r9, r8                  ; a.right
    mov     r10, [rdx + 48]         ; b.x
    mov     r11, [rdx + 64]
    add     r11, r10                ; b.right
    cmp     r9, r10
    jle     .prc_false
    cmp     r8, r11
    jge     .prc_false
    mov     r8, [rcx + 56]          ; a.y
    mov     r9, [rcx + 72]
    add     r9, r8                  ; a.bottom
    mov     r10, [rdx + 56]         ; b.y
    mov     r11, [rdx + 72]
    add     r11, r10                ; b.bottom
    cmp     r9, r10
    jle     .prc_false
    cmp     r8, r11
    jge     .prc_false
    mov     rax, 1
    ret
.prc_false:
    xor     eax, eax
    ret

_pyfasm_pg_rect_collidepoint:
    ; RCX = rect, RDX = x_or_tuple, R8 = y (when RDX < 65536)
    test    rcx, rcx
    jz      .pcp_false
    cmp     rdx, 65536
    jb      .pcp_xy
    cmp     qword [rdx], 2
    jl      .pcp_false
    mov     r8, [rdx + 16]
    mov     rdx, [rdx + 8]
.pcp_xy:
    mov     r9, [rcx + 48]
    cmp     rdx, r9
    jl      .pcp_false
    add     r9, [rcx + 64]
    cmp     rdx, r9
    jge     .pcp_false
    mov     r9, [rcx + 56]
    cmp     r8, r9
    jl      .pcp_false
    add     r9, [rcx + 72]
    cmp     r8, r9
    jge     .pcp_false
    mov     rax, 1
    ret
.pcp_false:
    xor     eax, eax
    ret

_pyfasm_pg_quit:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     qword [_pyfasm_pg_running], 0
    cmp     qword [_pyfasm_pg_old_bmp], 0
    je      .pq_del_bmp
    cmp     qword [_pyfasm_pg_mem_dc], 0
    je      .pq_del_bmp
    mov     rcx, [_pyfasm_pg_mem_dc]
    mov     rdx, [_pyfasm_pg_old_bmp]
    call    [SelectObject]
.pq_del_bmp:
    mov     rcx, [_pyfasm_pg_bmp]
    test    rcx, rcx
    jz      .pq_del_dc
    call    [DeleteObject]
    mov     qword [_pyfasm_pg_bmp], 0
.pq_del_dc:
    mov     rcx, [_pyfasm_pg_mem_dc]
    test    rcx, rcx
    jz      .pq_del_wnd
    call    [DeleteDC]
    mov     qword [_pyfasm_pg_mem_dc], 0
.pq_del_wnd:
    mov     rcx, [_pyfasm_pg_hwnd]
    test    rcx, rcx
    jz      .pq_done
    call    [DestroyWindow]
    mov     qword [_pyfasm_pg_hwnd], 0
.pq_done:
    xor     eax, eax
    mov     rsp, rbp
    pop     rbp
    ret
"""
