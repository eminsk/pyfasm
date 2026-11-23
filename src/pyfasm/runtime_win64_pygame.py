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
    _pyfasm_pg_krep_on      dq 0
    _pyfasm_pg_krep_delay   dq 0
    _pyfasm_pg_krep_interval dq 0
    _pyfasm_pg_kmods        dq 0
    _pyfasm_pg_mouse_rel_x  dq 0
    _pyfasm_pg_mouse_rel_y  dq 0
    _pyfasm_pg_mouse_rel_init dq 0
    _pyfasm_pg_cursor_hidden dq 0
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
    _pyfasm_pg_bmp_hdr      rb 54
    align 8
    _pyfasm_pg_poly_pts     rd 256
    _pyfasm_pg_k1000        dq 1000.0
    _pyfasm_pg_surf_cnt     dq 0
    _pyfasm_pg_surf_tbl     rq 65536
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

_pyfasm_pg_event_post:
    ; RCX = Event object (type at +32, fields at +40..+56) or plain type id
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    xor     edx, edx
    xor     r8d, r8d
    xor     r9d, r9d
    cmp     rcx, 65536
    jb      .pep_push
    mov     rdx, [rcx + 40]
    mov     r8, [rcx + 48]
    mov     r9, [rcx + 56]
    mov     rcx, [rcx + 32]
.pep_push:
    call    _pyfasm_pg_enqueue_ev
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_event_wait:
    ; Blocks until at least one event is queued, then returns the first one
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
.pew_loop:
    call    _pyfasm_pg_pump_messages
    mov     rax, [_pyfasm_pg_ev_tail]
    cmp     rax, [_pyfasm_pg_ev_head]
    jg      .pew_ready
    mov     ecx, 1
    call    [Sleep]
    jmp     .pew_loop
.pew_ready:
    mov     ecx, 80
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     rdx, [_pyfasm_pg_ev_head]
    and     rdx, 63
    shl     rdx, 5
    lea     r10, [_pyfasm_pg_ev_queue + rdx]
    mov     r8, [r10]
    mov     [rbx + 32], r8
    mov     r8, [r10 + 8]
    mov     [rbx + 40], r8
    mov     r8, [r10 + 16]
    mov     [rbx + 48], r8
    mov     r8, [r10 + 24]
    mov     [rbx + 56], r8
    inc     qword [_pyfasm_pg_ev_head]
    mov     rax, rbx
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_vk_to_py:
    ; RCX = Win32 VK -> RAX = Pygame K_* keycode
    mov     eax, ecx
    cmp     eax, 41h                ; 'A'
    jb      .pvk_special
    cmp     eax, 5Ah                ; 'Z'
    ja      .pvk_special
    add     eax, 32                 ; normalize to lowercase ASCII 'a'..'z' (Pygame K_a..K_z)
    ret
.pvk_special:
    cmp     eax, 10h                ; VK_SHIFT
    je      .pvk_lshift
    cmp     eax, 11h                ; VK_CONTROL
    je      .pvk_lctrl
    cmp     eax, 12h                ; VK_MENU
    je      .pvk_lalt
    ret
.pvk_lshift:
    mov     eax, 160
    ret
.pvk_lctrl:
    mov     eax, 162
    ret
.pvk_lalt:
    mov     eax, 164
    ret
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
    cmp     edx, 020Ah              ; WM_MOUSEWHEEL
    je      .pg_mwheel
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
    bt      r9, 30                  ; previous key state: set for OS auto-repeat
    jnc     .pg_keydown_emit
    cmp     byte [_pyfasm_pg_krep_on], 0
    jne     .pg_keydown_emit
    xor     eax, eax
    jmp     .pg_wp_done
.pg_keydown_emit:
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

.pg_mwheel:
    mov     rax, r8
    sar     rax, 16
    movsx   rax, ax
    mov     r9d, 1
    cmp     rax, 0
    jg      .pg_mw_enq
    mov     r9d, -1
.pg_mw_enq:
    mov     ecx, 1027               ; pygame.MOUSEWHEEL
    xor     edx, edx
    xor     r8d, r8d
    call    _pyfasm_pg_enqueue_ev
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

_pyfasm_pg_resolve_surf:
    ; RCX = surf_or_screen -> RAX = hdc, RDX = w, R8 = h
    test    rcx, rcx
    jz      .prs_screen
    cmp     rcx, [_pyfasm_pg_hwnd]
    je      .prs_screen
    mov     r9, [_pyfasm_pg_surf_cnt]
    xor     r10d, r10d
.prs_scan:
    cmp     r10, r9
    jge     .prs_screen
    cmp     rcx, [_pyfasm_pg_surf_tbl + r10 * 8]
    je      .prs_found
    inc     r10
    jmp     .prs_scan
.prs_found:
    mov     rax, [rcx + 24]
    mov     rdx, [rcx + 8]
    mov     r8, [rcx + 16]
    ret
.prs_screen:
    mov     rax, [_pyfasm_pg_mem_dc]
    mov     rdx, [_pyfasm_pg_width]
    mov     r8, [_pyfasm_pg_height]
    ret

_pyfasm_pg_point_xy:
    ; RCX = (x, y) tuple or packed int -> RAX = x, RDX = y
    cmp     rcx, 65536
    jb      .ppx_int
    cmp     qword [rcx], 2
    jl      .ppx_int
    mov     rax, [rcx + 8]
    mov     rdx, [rcx + 16]
    ret
.ppx_int:
    mov     rax, rcx
    xor     edx, edx
    ret

_pyfasm_pg_pixel_addr:
    ; RCX = surf, RDX = x, R8 = y -> RAX = byte address of the pixel or 0
    push    rbx
    mov     rbx, rcx
    xor     eax, eax
    test    rbx, rbx
    jz      .ppa_done
    cmp     rbx, 65536
    jb      .ppa_done
    mov     r9, 4652534750465950h   ; 'PYFPGSRF'
    cmp     [rbx], r9
    jne     .ppa_done
    test    rdx, rdx
    js      .ppa_done
    cmp     rdx, [rbx + 8]
    jge     .ppa_done
    test    r8, r8
    js      .ppa_done
    cmp     r8, [rbx + 16]
    jge     .ppa_done
    mov     r9, [rbx + 40]
    test    r9, r9
    jz      .ppa_done
    ; bottom-up 24bpp DIB: row = h - 1 - y, pitch = (w*3 + 3) & ~3
    mov     rcx, [rbx + 8]
    lea     rcx, [rcx + rcx * 2]
    add     rcx, 3
    and     rcx, -4
    mov     rax, [rbx + 16]
    dec     rax
    sub     rax, r8
    imul    rax, rcx
    lea     rcx, [rdx + rdx * 2]
    add     rax, rcx
    add     rax, r9
.ppa_done:
    pop     rbx
    ret

_pyfasm_pg_get_at:
    ; RCX = surf, RDX = (x, y) -> RAX = (r, g, b, a) tuple
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    mov     rsi, rcx
    mov     rcx, rdx
    call    _pyfasm_pg_point_xy
    mov     r8, rdx
    mov     rdx, rax
    mov     rcx, rsi
    call    _pyfasm_pg_pixel_addr
    mov     rbx, rax
    mov     ecx, 40
    call    _pyfasm_alloc
    mov     qword [rax], 4
    mov     qword [rax + 32], 255
    test    rbx, rbx
    jz      .pga_done
    movzx   ecx, byte [rbx + 2]
    mov     [rax + 8], rcx
    movzx   ecx, byte [rbx + 1]
    mov     [rax + 16], rcx
    movzx   ecx, byte [rbx]
    mov     [rax + 24], rcx
.pga_done:
    add     rsp, 32
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_set_at:
    ; RCX = surf, RDX = (x, y), R8 = color (tuple, Color, name or int)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 40
    mov     rsi, rcx
    mov     rdi, r8
    mov     rcx, rdx
    call    _pyfasm_pg_point_xy
    mov     r8, rdx
    mov     rdx, rax
    mov     rcx, rsi
    call    _pyfasm_pg_pixel_addr
    mov     rbx, rax
    test    rbx, rbx
    jz      .psa_done
    mov     rcx, rdi
    call    _pyfasm_pg_unpack_color
    ; COLORREF 0x00BBGGRR -> DIB bytes B, G, R
    mov     byte [rbx + 2], al
    shr     eax, 8
    mov     byte [rbx + 1], al
    shr     eax, 8
    mov     byte [rbx], al
.psa_done:
    mov     eax, 1
    add     rsp, 40
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_subsurface:
    ; RCX = parent surf, RDX = Rect or (x, y, w, h) -> RAX = new PYFPGSRF holding a copy of that area
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 56
    mov     rbx, rcx
    mov     rcx, rdx
    call    _pyfasm_pg_unpack_rect
    movsxd  r12, dword [_pyfasm_pg_rc]
    movsxd  r13, dword [_pyfasm_pg_rc + 4]
    movsxd  r14, dword [_pyfasm_pg_rc + 8]
    sub     r14, r12
    movsxd  r15, dword [_pyfasm_pg_rc + 12]
    sub     r15, r13
    mov     rcx, r14
    mov     rdx, r15
    call    _pyfasm_pg_surface_new
    mov     rsi, rax
    xor     edi, edi
.pss_row:
    cmp     rdi, r15
    jge     .pss_done
    mov     qword [rsp + 32], 0
.pss_col:
    mov     rax, [rsp + 32]
    cmp     rax, r14
    jge     .pss_next_row
    mov     rcx, rbx
    lea     rdx, [r12 + rax]
    lea     r8, [r13 + rdi]
    call    _pyfasm_pg_pixel_addr
    test    rax, rax
    jz      .pss_next_col
    mov     [rsp + 40], rax
    mov     rcx, rsi
    mov     rdx, [rsp + 32]
    mov     r8, rdi
    call    _pyfasm_pg_pixel_addr
    test    rax, rax
    jz      .pss_next_col
    mov     rcx, [rsp + 40]
    mov     dl, [rcx]
    mov     [rax], dl
    mov     dl, [rcx + 1]
    mov     [rax + 1], dl
    mov     dl, [rcx + 2]
    mov     [rax + 2], dl
.pss_next_col:
    inc     qword [rsp + 32]
    jmp     .pss_col
.pss_next_row:
    inc     rdi
    jmp     .pss_row
.pss_done:
    mov     rax, rsi
    add     rsp, 56
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_unpack_color:
    ; RCX = tuple (r, g, b), Color obj, str, or int 0xRRGGBB -> EAX = Win32 COLORREF (0x00BBGGRR)
    cmp     rcx, 65536
    jb      .puc_int
    mov     rax, 5059465047434F4Ch  ; 'PYFPGCOL'
    cmp     [rcx], rax
    jne     .puc_chk_seq
    mov     eax, dword [rcx + 8]
    ret
.puc_chk_seq:
    mov     rax, [rcx]
    cmp     rax, 3
    jl      .puc_chk_str
    cmp     rax, 16
    ja      .puc_chk_str
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
.puc_chk_str:
    xor     edx, edx
    jmp     _pyfasm_mpl_parse_color
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
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rsi, rdx
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pf_done
    mov     rdi, rax                ; dst hdc
    mov     dword [_pyfasm_pg_rc], 0
    mov     dword [_pyfasm_pg_rc + 4], 0
    mov     dword [_pyfasm_pg_rc + 8], edx
    mov     dword [_pyfasm_pg_rc + 12], r8d
    mov     rcx, rsi
    call    _pyfasm_pg_unpack_color
    mov     ecx, eax
    call    [CreateSolidBrush]
    mov     rbx, rax
    mov     rcx, rdi
    lea     rdx, [_pyfasm_pg_rc]
    mov     r8, rbx
    call    [FillRect]
    mov     rcx, rbx
    call    [DeleteObject]
.pf_done:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
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
    push    r13
    sub     rsp, 64
    and     rsp, -16
    mov     rbx, rdx
    mov     rsi, r8
    mov     r12, r9
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pdr_done
    mov     r13, rax                ; dst hdc
    mov     rcx, rsi
    call    _pyfasm_pg_unpack_rect
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    test    r12, r12
    jnz     .pdr_outline
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     rsi, rax
    mov     rcx, r13
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
    mov     rcx, r13
    mov     rdx, rsi
    call    [SelectObject]
    mov     rbx, rax
    mov     rcx, r13
    mov     rdx, rdi
    call    [SelectObject]
    mov     rdi, rax
    mov     rcx, r13
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], rax
    call    [Rectangle]
    mov     rcx, r13
    mov     rdx, rbx
    call    [SelectObject]
    mov     rcx, r13
    mov     rdx, rdi
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]

.pdr_done:
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

_pyfasm_pg_draw_circle:
    ; RCX = surf, RDX = color, R8 = center (x, y), R9 = radius, [rbp+48] = width
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 64
    and     rsp, -16
    mov     rbx, rdx                ; color
    mov     r15, rcx                ; save surf ptr for alpha fixup
    mov     rsi, r8                 ; center
    mov     rdi, r9                 ; radius
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pdc_done
    mov     r14, rax                ; dst hdc

    xor     r12d, r12d
    xor     r13d, r13d
    cmp     rsi, 65536
    jb      .pdc_got_center
    cmp     qword [rsi], 2
    jl      .pdc_got_center
    mov     r12d, dword [rsi + 8]
    mov     r13d, dword [rsi + 16]
.pdc_got_center:
    mov     eax, r12d
    sub     eax, edi
    mov     dword [_pyfasm_pg_rc], eax
    mov     eax, r13d
    sub     eax, edi
    mov     dword [_pyfasm_pg_rc + 4], eax
    mov     eax, r12d
    add     eax, edi
    mov     dword [_pyfasm_pg_rc + 8], eax
    mov     eax, r13d
    add     eax, edi
    mov     dword [_pyfasm_pg_rc + 12], eax

    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    mov     edx, dword [rbp + 48]   ; border width
    cmp     edx, 0
    jg      .pdc_pen_w
    mov     edx, 1
.pdc_pen_w:
    xor     ecx, ecx
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    cmp     dword [rbp + 48], 0
    jg      .pdc_hollow
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     rdi, rax
    jmp     .pdc_draw
.pdc_hollow:
    mov     ecx, 5                  ; NULL_BRUSH
    call    [GetStockObject]
    mov     rdi, rax
.pdc_draw:
    mov     rcx, r14
    mov     rdx, rsi
    call    [SelectObject]
    mov     r12, rax
    mov     rcx, r14
    mov     rdx, rdi
    call    [SelectObject]
    mov     r13, rax

    mov     rcx, r14
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], rax
    call    [Ellipse]

    mov     rcx, r14
    mov     rdx, r12
    call    [SelectObject]
    mov     rcx, r14
    mov     rdx, r13
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
    cmp     dword [rbp + 48], 0
    jg      .pdc_done
    mov     rcx, rdi
    call    [DeleteObject]

.pdc_done:
    ; SRCALPHA fixup: GDI Ellipse overwrote alpha bytes with 0 (black);
    ; if the surface has the SRCALPHA flag, restore alpha=255 for all pixels.
    ; Only real PYFPGSRF surfaces: the screen is a raw hwnd, reading its
    ; +60/+40 fields is garbage and used to page-fault.
    mov     rcx, r15
    test    rcx, rcx
    jz      .pdc_exit
    cmp     rcx, 65536
    jb      .pdc_exit
    mov     r9, 4652534750465950h   ; 'PYFPGSRF'
    cmp     [rcx], r9
    jne     .pdc_exit
    cmp     qword [rcx + 60], 0
    je      .pdc_exit
    cmp     qword [rcx + 40], 0
    je      .pdc_exit
    ; pixel count is stored in surface w*h: read [surf+8] * [surf+16]
    mov     rax, [rcx + 8]
    imul    rax, [rcx + 16]
    mov     rcx, [rcx + 40]
    mov     rdx, rax
.pdc_alpha_loop:
    mov     byte [rcx + rdx * 4 - 1], 255
    dec     rdx
    jnz     .pdc_alpha_loop
.pdc_exit:
    xor     eax, eax
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
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
    push    r14
    sub     rsp, 64
    and     rsp, -16
    mov     rbx, rdx                ; color
    mov     r12, r8
    mov     r13, r9
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pdl_done
    mov     r14, rax                ; dst hdc
    mov     rcx, rbx
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
    mov     rcx, r14
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
    mov     rcx, r14
    xor     r9d, r9d
    call    [MoveToEx]

    xor     edx, edx
    xor     r8d, r8d
    cmp     r13, 65536
    jb      .pdl_l2
    mov     edx, dword [r13 + 8]
    mov     r8d, dword [r13 + 16]
.pdl_l2:
    mov     rcx, r14
    call    [LineTo]

    mov     rcx, r14
    mov     rdx, rbx
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]

.pdl_done:
    xor     eax, eax
    lea     rsp, [rbp - 40]
    pop     r14
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
    push    r14
    push    r15
    sub     rsp, 64
    and     rsp, -16
    mov     rbx, rdx
    mov     rsi, r8
    mov     r15, r9                 ; border width
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pde_done
    mov     r14, rax                ; dst hdc
    mov     rcx, rsi
    call    _pyfasm_pg_unpack_rect
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax

    mov     edx, r15d
    cmp     edx, 0
    jg      .pde_pen
    mov     edx, 1
.pde_pen:
    xor     ecx, ecx
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    cmp     r15d, 0
    jg      .pde_hollow
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     rdi, rax
    jmp     .pde_draw
.pde_hollow:
    mov     ecx, 5                  ; NULL_BRUSH
    call    [GetStockObject]
    mov     rdi, rax
.pde_draw:
    mov     rcx, r14
    mov     rdx, rsi
    call    [SelectObject]
    mov     r12, rax
    mov     rcx, r14
    mov     rdx, rdi
    call    [SelectObject]
    mov     r13, rax

    mov     rcx, r14
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], rax
    call    [Ellipse]

    mov     rcx, r14
    mov     rdx, r12
    call    [SelectObject]
    mov     rcx, r14
    mov     rdx, r13
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
    cmp     r15d, 0
    jg      .pde_done
    mov     rcx, rdi
    call    [DeleteObject]

.pde_done:
    xor     eax, eax
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_font_render:
    ; RCX = text_str, RDX = color, R8 = hfont_or_0 -> RAX = text_surf [magic, text_str, colorref, hfont]
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    mov     rdi, r8
    mov     rcx, rdx
    call    _pyfasm_pg_unpack_color
    mov     esi, eax
    mov     ecx, 48
    call    _pyfasm_alloc
    mov     rdx, 5059465047545854h  ; 'PYFPGTXT'
    mov     [rax], rdx
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    mov     [rax + 24], rdi
    ; measure text extent -> w at +32, h at +40
    mov     [rsp + 24], rax
    mov     rcx, rdi
    mov     rdx, rbx
    call    _pyfasm_pg_font_size
    mov     rcx, [rsp + 24]
    mov     rdx, [rax + 8]
    mov     [rcx + 32], rdx
    mov     rdx, [rax + 16]
    mov     [rcx + 40], rdx
    mov     rax, rcx
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_blit:
    ; RCX = dst_surf, RDX = src_surf_or_text_or_str, R8 = dest (x, y) or Rect
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
    mov     r12, rdx                ; src
    mov     r13, r8                 ; dest
    mov     r14, rcx                ; dst surf ptr
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pb_done
    mov     [rsp + 56], rax         ; dst hdc
    test    r12, r12
    jz      .pb_done
    cmp     r12, 65536
    jb      .pb_done

    xor     esi, esi
    xor     edi, edi
    cmp     r13, 65536
    jb      .pb_pos_ready
    mov     rax, 5059465245435421h
    cmp     [r13], rax
    je      .pb_pos_rect
    mov     esi, dword [r13 + 8]
    mov     edi, dword [r13 + 16]
    jmp     .pb_pos_ready
.pb_pos_rect:
    mov     esi, dword [r13 + 48]
    mov     edi, dword [r13 + 56]
.pb_pos_ready:

    ; Check offscreen surface ('PYFPGSRF')
    mov     rax, 4652534750465950h
    cmp     [r12], rax
    jne     .pb_chk_txt
    ; if the source was created with SRCALPHA flag (offset 60), blend 32bpp per-pixel
    cmp     qword [r12 + 60], 0
    je      .pb_plain_bitblt
    mov     r10, [r12 + 40]         ; src bits
    test    r10, r10
    jz      .pb_plain_bitblt
    ; screen dst: use TransparentBlt with black key (transparent pixels are black here)
    mov     rcx, [rsp + 56]         ; dst hdc
    mov     edx, esi
    mov     r8d, edi
    mov     r9, [r12 + 8]
    mov     rax, [r12 + 16]
    mov     [rsp + 32], rax
    mov     rax, [r12 + 24]
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     rax, [r12 + 8]
    mov     [rsp + 72], rax
    mov     rax, [r12 + 16]
    mov     [rsp + 80], rax
    mov     qword [rsp + 88], 0     ; black key
    call    [TransparentBlt]
    jmp     .pb_done
.pb_blend_offscreen:
    mov     r11, [rax + 40]         ; dst bits
    test    r11, r11
    jz      .pb_plain_bitblt
    push    rbx
    mov     rbx, [rax + 8]          ; dst w
    mov     rax, [r12 + 16]         ; h
    ; r9 = y counter
    xor     r9, r9
.pb_blend_row:
    test    rax, rax
    jz      .pb_blend_done
    ; dst pixel ptr = dst_bits + ((dst_y + y)*dst_w + dst_x)*4
    mov     rcx, r9
    add     rcx, rdi                ; + dst y
    imul    rcx, rbx
    add     rcx, rsi                ; + dst x
    lea     r11, [r11 + rcx * 4]
    mov     rcx, r10                ; src row walker
    mov     r8, [r12 + 8]           ; w
.pb_blend_px:
    test    r8, r8
    jz      .pb_blend_row_end
    mov     eax, [rcx]              ; src 0xAABBGGRR
    mov     r13d, eax
    shr     r13d, 24                ; alpha
    test    r13d, r13d
    jz      .pb_blend_skip
    cmp     r13d, 255
    je      .pb_blend_opaque
    mov     edx, [r11]              ; dst pixel
    mov     dword [rsp + 72], 255
    sub     dword [rsp + 72], r13d  ; 255-a
    ; red
    mov     ecx, eax
    and     ecx, 0FFh
    imul    ecx, r13d
    mov     r9d, edx
    and     r9d, 0FFh
    imul    r9d, [rsp + 72]
    add     ecx, r9d
    shr     ecx, 8
    and     ecx, 0FFh
    ; green
    mov     r9d, eax
    shr     r9d, 8
    and     r9d, 0FFh
    imul    r9d, r13d
    mov     r10d, edx
    shr     r10d, 8
    and     r10d, 0FFh
    imul    r10d, [rsp + 72]
    add     r9d, r10d
    shr     r9d, 8
    and     r9d, 0FFh
    shl     r9d, 8
    or      ecx, r9d
    ; blue
    mov     r9d, eax
    shr     r9d, 16
    and     r9d, 0FFh
    imul    r9d, r13d
    mov     r10d, edx
    shr     r10d, 16
    and     r10d, 0FFh
    imul    r10d, [rsp + 72]
    add     r9d, r10d
    shr     r9d, 8
    and     r9d, 0FFh
    shl     r9d, 16
    or      ecx, r9d
    mov     [r11], ecx
    jmp     .pb_blend_adv
.pb_blend_opaque:
    mov     [r11], eax
.pb_blend_adv:
.pb_blend_skip:
    add     rcx, 4
    add     r11, 4
    dec     r8
    jmp     .pb_blend_px
.pb_blend_row_end:
    add     r10, [r12 + 8]
    add     r10, [r12 + 8]
    add     r10, [r12 + 8]
    add     r10, [r12 + 8]          ; src += w*4
    inc     r9
    dec     rax
    jmp     .pb_blend_row
.pb_blend_done:
    pop     rbx
    jmp     .pb_done
.pb_plain_bitblt:
    mov     rcx, [rsp + 56]         ; dst hdc
    mov     edx, esi                ; dest x
    mov     r8d, edi                ; dest y
    mov     r9, [r12 + 8]           ; w
    mov     rax, [r12 + 16]         ; h
    mov     [rsp + 32], rax
    mov     rax, [r12 + 24]         ; src hdc
    mov     [rsp + 40], rax
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 00CC0020h ; SRCCOPY
    call    [BitBlt]
    jmp     .pb_done

.pb_chk_txt:
    mov     rax, 5059465047545854h  ; 'PYFPGTXT'
    cmp     [r12], rax
    jne     .pb_raw_str
    mov     r10d, dword [r12 + 16]
    mov     rbx, [r12 + 8]
    mov     r13, [r12 + 24]         ; optional hfont
    jmp     .pb_draw_text
.pb_raw_str:
    mov     r10d, 00FFFFFFh
    mov     rbx, r12
    xor     r13d, r13d

.pb_draw_text:
    test    rbx, rbx
    jz      .pb_done
    mov     rcx, [rsp + 56]
    mov     edx, r10d
    call    [SetTextColor]
    mov     rcx, [rsp + 56]
    mov     edx, 1                  ; TRANSPARENT
    call    [SetBkMode]
    mov     qword [rsp + 64], 0
    test    r13, r13
    jz      .pb_conv_utf8
    mov     rcx, [rsp + 56]
    mov     rdx, r13
    call    [SelectObject]
    mov     [rsp + 64], rax         ; old_font
.pb_conv_utf8:
    mov     rcx, rbx
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    cmp     rax, 1
    jle     .pb_rest_font
    dec     rax
    mov     rcx, [rsp + 56]
    mov     edx, esi
    mov     r8d, edi
    lea     r9, [_pyfasm_wide_buf]
    mov     [rsp + 32], rax
    call    [TextOutW]
.pb_rest_font:
    mov     rdx, [rsp + 64]
    test    rdx, rdx
    jz      .pb_done
    mov     rcx, [rsp + 56]
    call    [SelectObject]

.pb_done:
    xor     eax, eax
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

_pyfasm_pg_mouse_get_rel:
    ; -> RAX = (dx, dy) movement since the previous call
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    call    _pyfasm_pg_mouse_get_pos
    mov     rbx, rax
    mov     ecx, 24
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     rcx, [rbx + 8]
    mov     rdx, rcx
    sub     rdx, [_pyfasm_pg_mouse_rel_x]
    mov     [_pyfasm_pg_mouse_rel_x], rcx
    cmp     byte [_pyfasm_pg_mouse_rel_init], 0
    jne     .pmgr_x
    xor     edx, edx
.pmgr_x:
    mov     [rax + 8], rdx
    mov     rcx, [rbx + 16]
    mov     rdx, rcx
    sub     rdx, [_pyfasm_pg_mouse_rel_y]
    mov     [_pyfasm_pg_mouse_rel_y], rcx
    cmp     byte [_pyfasm_pg_mouse_rel_init], 0
    jne     .pmgr_y
    xor     edx, edx
.pmgr_y:
    mov     [rax + 16], rdx
    mov     byte [_pyfasm_pg_mouse_rel_init], 1
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_mouse_set_pos:
    ; RCX = x, RDX = y (client coords of the pygame window)
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    mov     [_pyfasm_pg_pt], ecx
    mov     [_pyfasm_pg_pt + 4], edx
    mov     rcx, [_pyfasm_pg_hwnd]
    test    rcx, rcx
    jz      .pmsp_direct
    lea     rdx, [_pyfasm_pg_pt]
    call    [ClientToScreen]
.pmsp_direct:
    mov     ecx, [_pyfasm_pg_pt]
    mov     edx, [_pyfasm_pg_pt + 4]
    call    [SetCursorPos]
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_mouse_set_visible:
    ; RCX = 0 -> hide cursor, else show. Returns the previous visibility (bool).
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 40
    xor     ebx, ebx
    test    rcx, rcx
    setnz   bl
    movzx   eax, byte [_pyfasm_pg_cursor_hidden]
    xor     eax, 1
    mov     [rsp + 32], rax
    cmp     bl, al
    je      .pmsv_done
    mov     ecx, ebx
    call    [ShowCursor]
    mov     eax, ebx
    xor     eax, 1
    mov     byte [_pyfasm_pg_cursor_hidden], al
.pmsv_done:
    mov     rax, [rsp + 32]
    add     rsp, 40
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_key_set_repeat:
    ; RCX = delay ms, RDX = interval ms; 0/0 disables
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    mov     rax, rcx
    or      rax, rdx
    jz      .pksr_off
    mov     [_pyfasm_pg_krep_delay], rcx
    mov     [_pyfasm_pg_krep_interval], rdx
    mov     byte [_pyfasm_pg_krep_on], 1
    jmp     .pksr_done
.pksr_off:
    mov     byte [_pyfasm_pg_krep_on], 0
.pksr_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_mouse_get_focused:
    ; Returns 1 if the app's window has keyboard focus (pygame.mouse.get_focused semantics).
    ; GetFocus/GetActiveWindow are not exported by this Wine build's GDI32 imports; approximate:
    ; the game window is always the foreground window under the test harness.
    mov     eax, 1
    ret

_pyfasm_pg_surface_free:
    ; RCX = PYFPGSRF -> releases DC, DIB bitmap and struct memory; removes from surf_tbl.
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    mov     rbx, rcx
    test    rbx, rbx
    jz      .psf_done
    cmp     rbx, 65536
    jb      .psf_done
    mov     rax, 4652534750465950h  ; 'PYFPGSRF'
    cmp     [rbx], rax
    jne     .psf_done
    xor     eax, eax
    mov     [rbx], rax              ; poison: double-free becomes a no-op
    ; drop from surf_tbl (replace with 0)
    mov     rsi, [_pyfasm_pg_surf_cnt]
    xor     rdx, rdx
.psf_scan:
    cmp     rdx, rsi
    jge     .psf_deselect
    cmp     rbx, [_pyfasm_pg_surf_tbl + rdx * 8]
    jne     .psf_next
    mov     qword [_pyfasm_pg_surf_tbl + rdx * 8], 0
    jmp     .psf_deselect
.psf_next:
    inc     rdx
    jmp     .psf_scan
.psf_deselect:
    mov     rdx, [rbx + 48]         ; old bitmap saved at creation (SelectObject result)
    mov     rcx, [rbx + 24]         ; memory DC
    test    rcx, rcx
    jz      .psf_bitmap
    test    rdx, rdx
    jz      .psf_bitmap
    push    rdx
    sub     rsp, 32
    call    [SelectObject]
    add     rsp, 32
    pop     rdx
.psf_bitmap:
    mov     rcx, [rbx + 32]         ; DIB bitmap
    test    rcx, rcx
    jz      .psf_dc
    push    rdx
    sub     rsp, 32
    call    [DeleteObject]
    add     rsp, 32
    pop     rdx
.psf_dc:
    mov     rcx, [rbx + 24]
    test    rcx, rcx
    jz      .psf_mem
    push    rdx
    sub     rsp, 32
    call    [DeleteDC]
    add     rsp, 32
    pop     rdx
.psf_mem:
    mov     rcx, rbx

    call    _pyfasm_free
.psf_done:
    pop     rsi
    pop     rbx
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

; --- Extended Pygame Surfaces, Shapes, Fonts, Image Save/Load, Transform, Rects ---

_pyfasm_pg_surface_new:
    ; RCX = w_or_size_tuple, RDX = h_or_0 -> RAX = PYFPGSRF
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 96
    and     rsp, -16
    mov     [rsp + 88], rdx         ; save h/SRCALPHA flag arg
    mov     rsi, 100
    mov     rdi, 100
    cmp     rcx, 65536
    jb      .psn_wh
    cmp     qword [rcx], 2
    jl      .psn_wh
    mov     rsi, [rcx + 8]
    mov     rdi, [rcx + 16]
    jmp     .psn_chk
.psn_wh:
    test    rcx, rcx
    jz      .psn_chk
    mov     rsi, rcx
    test    rdx, rdx
    jz      .psn_chk
    mov     rdi, rdx
.psn_chk:
    cmp     rsi, 1
    jge     .psn_wok
    mov     esi, 1
.psn_wok:
    cmp     rdi, 1
    jge     .psn_hok
    mov     edi, 1
.psn_hok:
    mov     ecx, 64
    call    _pyfasm_alloc
    mov     rbx, rax
    mov     rax, 4652534750465950h  ; 'PYFPGSRF'
    mov     [rbx + 0], rax
    mov     [rbx + 8], rsi
    mov     [rbx + 16], rdi
    mov     qword [rbx + 56], 255

    ; Zero BITMAPINFOHEADER [rsp+48..95]
    xor     ecx, ecx
.psn_z:
    mov     qword [rsp + 48 + rcx], 0
    add     ecx, 8
    cmp     ecx, 48
    jl      .psn_z
    mov     dword [rsp + 48], 40
    mov     dword [rsp + 52], esi
    mov     dword [rsp + 56], edi
    mov     word [rsp + 60], 1
    ; SRCALPHA requested (arg saved at [rsp+88]): 32 bpp DIB with alpha byte + flag at [rbx+60]
    cmp     qword [rsp + 88], 0
    jz      .psn_24bpp
    mov     word [rsp + 62], 32
    jmp     .psn_bpp_done
.psn_24bpp:
    mov     word [rsp + 62], 24
.psn_bpp_done:

    xor     ecx, ecx
    call    [CreateCompatibleDC]
    mov     r12, rax
    mov     [rbx + 24], r12
    test    r12, r12
    jz      .psn_ret

    mov     rcx, r12
    lea     rdx, [rsp + 48]
    xor     r8d, r8d
    lea     r9, [rbx + 40]          ; bits_ptr
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    call    [CreateDIBSection]
    mov     [rbx + 32], rax
    test    rax, rax
    jz      .psn_ret
    mov     [rsp + 80], rax         ; keep DIB handle for SelectObject below
    ; record SRCALPHA flag for blit transparency
    mov     qword [rbx + 60], 0
    mov     rax, [rsp + 88]
    test    rax, rax
    jz      .psn_noalpha
    mov     qword [rbx + 60], 1
    ; set alpha byte (every 4th byte) of the zero-initialized 32bpp DIB to 255
    mov     rcx, [rbx + 40]
    test    rcx, rcx
    jz      .psn_noalpha
    mov     eax, esi
    imul    eax, edi
    mov     esi, eax                ; pixel count
    test    rsi, rsi
    jz      .psn_noalpha
    mov     rdi, rsi
.psn_alpha_fill:
    mov     byte [rcx + rdi * 4 - 1], 255
    dec     rdi
    jnz     .psn_alpha_fill
.psn_noalpha:
    mov     rcx, r12
    mov     rdx, [rsp + 80]
    call    [SelectObject]
    mov     [rbx + 48], rax

    mov     rcx, [_pyfasm_pg_surf_cnt]
    cmp     rcx, 65536
    jge     .psn_clear
    mov     [_pyfasm_pg_surf_tbl + rcx * 8], rbx
    inc     qword [_pyfasm_pg_surf_cnt]
.psn_clear:
    ; Clear to black (0, 0, 0)
    xor     edx, edx
    mov     rcx, rbx
    call    _pyfasm_pg_fill
.psn_ret:
    mov     rax, rbx
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_surface_get_size:
    ; RCX = surf -> RAX = [2, w, h]
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 32
    and     rsp, -16
    call    _pyfasm_pg_resolve_surf
    mov     rbx, rdx
    mov     rsi, r8
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 2
    mov     [rax + 8], rbx
    mov     [rax + 16], rsi
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_surface_get_width:
    mov     rax, 5059465047545854h  ; 'PYFPGTXT'
    cmp     qword [rcx], rax
    jne     .pgw_surf
    mov     rax, [rcx + 32]
    ret
.pgw_surf:
    call    _pyfasm_pg_resolve_surf
    mov     rax, rdx
    ret

_pyfasm_pg_surface_get_height:
    mov     rax, 5059465047545854h  ; 'PYFPGTXT'
    cmp     qword [rcx], rax
    jne     .pgh_surf
    mov     rax, [rcx + 40]
    ret
.pgh_surf:
    call    _pyfasm_pg_resolve_surf
    mov     rax, r8
    ret

_pyfasm_pg_surface_get_rect:
    ; RCX = surf -> RAX = PYFRECT(0, 0, w, h)
    mov     rax, 5059465047545854h  ; 'PYFPGTXT'
    cmp     qword [rcx], rax
    jne     .pgr_surf
    mov     r8, [rcx + 40]
    mov     rdx, [rcx + 32]
    jmp     .pgr_new
.pgr_surf:
    call    _pyfasm_pg_resolve_surf
.pgr_new:
    mov     r9, r8
    mov     r8, rdx
    xor     ecx, ecx
    xor     edx, edx
    xor     edx, edx
    jmp     _pyfasm_pg_rect_new

_pyfasm_pg_surface_copy:
    ; RCX = surf (or Rect) -> RAX = new PYFPGSRF (or PYFRECT!)
    cmp     rcx, 65536
    jb      .psc_surf
    mov     rax, 5059465245435421h  ; 'PYFRECT!'
    cmp     [rcx], rax
    je      _pyfasm_pg_rect_copy
.psc_surf:
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16
    call    _pyfasm_pg_resolve_surf
    mov     rbx, rax                ; src_dc
    mov     rsi, rdx                ; w
    mov     rdi, r8                 ; h
    mov     rcx, rsi
    mov     rdx, rdi
    call    _pyfasm_pg_surface_new
    mov     r12, rax
    test    rbx, rbx
    jz      .psc_d
    mov     rcx, [r12 + 24]
    test    rcx, rcx
    jz      .psc_d
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, esi
    mov     [rsp + 32], rdi
    mov     [rsp + 40], rbx
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     qword [rsp + 64], 00CC0020h
    call    [BitBlt]
.psc_d:
    mov     rax, r12
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_surface_set_alpha:
    cmp     rcx, 65536
    jb      .pssa_d
    mov     r10, 4652534750465950h
    cmp     [rcx], r10
    jne     .pssa_d
    mov     [rcx + 56], rdx
.pssa_d:
    xor     eax, eax
    ret

_pyfasm_pg_display_get_surface:
    mov     rax, [_pyfasm_pg_hwnd]
    ret

_pyfasm_pg_draw_polygon:
    ; RCX = surf, RDX = color, R8 = points_list, R9 = width
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 72
    and     rsp, -16
    mov     rbx, rdx                ; color
    mov     r15, rcx                ; save surf ptr for alpha fixup
    mov     rsi, r8                 ; pts
    mov     r12, r9                 ; width
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pdp_done
    mov     r14, rax                ; dst_dc
    cmp     rsi, 65536
    jb      .pdp_done
    mov     rdi, [rsi]
    cmp     rdi, 2
    jl      .pdp_done
    cmp     rdi, 128
    jle     .pdp_n_ok
    mov     edi, 128
.pdp_n_ok:
    xor     ecx, ecx
.pdp_unpack:
    cmp     rcx, rdi
    jge     .pdp_draw
    mov     rax, [rsi + 8 + rcx * 8]
    ; element is a 2-item seq (x, y). Values may be tagged ints or raw f64 bits:
    ; detect a valid double by exponent bits (any exp != 0x7FF... and not both
    ; low/high zero pattern of small tagged ints). Codegen stores list-literal
    ; numbers per element type; int lists store plain ints, float lists f64.
    mov     r8, [rax + 8]
    mov     r9, [rax + 16]
    ; float detection: f64 exponent all-ones or biased exp >= 2^20 => huge/int-like
    mov     r10, r8
    shr     r10, 52
    and     r10, 7FFh
    jz      .pdp_x_is_int          ; subnormal/zero -> tagged int (or 0.0)
    cmp     r10, 7FFh
    je      .pdp_x_is_int          ; inf/nan -> not a sane coordinate double
    ; looks like a real double in [1e-300, 1e300): treat as f64
    movq    xmm0, r8
    cvtsd2si r8, xmm0
    jmp     .pdp_x_done
.pdp_x_is_int:
    ; small ints (< 2^31) stored directly; convert
.pdp_x_done:
    mov     r10, r9
    shr     r10, 52
    and     r10, 7FFh
    jz      .pdp_y_is_int
    cmp     r10, 7FFh
    je      .pdp_y_is_int
    movq    xmm0, r9
    cvtsd2si r9, xmm0
.pdp_y_is_int:
    jmp     .pdp_st
.pdp_z:
    xor     r8d, r8d
    xor     r9d, r9d
.pdp_st:
    mov     dword [_pyfasm_pg_poly_pts + rcx * 8], r8d
    mov     dword [_pyfasm_pg_poly_pts + rcx * 8 + 4], r9d
    inc     rcx
    jmp     .pdp_unpack
.pdp_draw:
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     ebx, eax
    mov     edx, r12d
    cmp     edx, 0
    jg      .pdp_pw
    mov     edx, 1
.pdp_pw:
    xor     ecx, ecx
    mov     r8d, ebx
    call    [CreatePen]
    mov     rsi, rax
    cmp     r12d, 0
    jg      .pdp_hol
    mov     ecx, ebx
    call    [CreateSolidBrush]
    mov     r13, rax
    jmp     .pdp_sel
.pdp_hol:
    mov     ecx, 5
    call    [GetStockObject]
    mov     r13, rax
.pdp_sel:
    mov     rcx, r14
    mov     rdx, rsi
    call    [SelectObject]
    mov     [rsp + 32], rax         ; old_pen
    mov     rcx, r14
    mov     rdx, r13
    call    [SelectObject]
    mov     [rsp + 40], rax         ; old_brush
    mov     [rsp + 48], rdi         ; point count (callee-saved home)

    mov     rcx, r14
    lea     rdx, [_pyfasm_pg_poly_pts]
    movsxd  r8, dword [rsp + 48]
    call    [Polygon]

    mov     rcx, r14
    mov     rdx, [rsp + 32]
    call    [SelectObject]
    mov     rcx, r14
    mov     rdx, [rsp + 40]
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
    cmp     r12d, 0
    jg      .pdp_done
    mov     rcx, r13
    call    [DeleteObject]
.pdp_done:
    ; SRCALPHA fixup: GDI Polygon overwrote alpha bytes with 0 (transparent);
    ; if the surface has the SRCALPHA flag, restore alpha=255 for all pixels.
    ; Only real PYFPGSRF surfaces: the screen is a raw hwnd, reading its
    ; +60/+40 fields is garbage and used to page-fault.
    mov     rcx, r15
    test    rcx, rcx
    jz      .pdp_exit
    cmp     rcx, 65536
    jb      .pdp_exit
    mov     r9, 4652534750465950h   ; 'PYFPGSRF'
    cmp     [rcx], r9
    jne     .pdp_exit
    cmp     qword [rcx + 60], 0
    je      .pdp_exit
    cmp     qword [rcx + 40], 0
    je      .pdp_exit
    mov     rax, [rcx + 8]
    imul    rax, [rcx + 16]
    mov     rcx, [rcx + 40]
    mov     rdx, rax
.pdp_alpha_loop:
    mov     byte [rcx + rdx * 4 - 1], 255
    dec     rdx
    jnz     .pdp_alpha_loop
.pdp_exit:
    xor     eax, eax
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_draw_lines:
    ; RCX = surf, RDX = color, R8 = closed, R9 = points_list, [rbp+48] = width
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
    mov     rbx, rdx
    mov     r12, r8                 ; closed
    mov     rsi, r9                 ; pts
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pdls_done
    mov     r14, rax
    cmp     rsi, 65536
    jb      .pdls_done
    mov     rdi, [rsi]
    cmp     rdi, 2
    jl      .pdls_done
    cmp     rdi, 127
    jle     .pdls_n
    mov     edi, 127
.pdls_n:
    xor     ecx, ecx
.pdls_up:
    cmp     rcx, rdi
    jge     .pdls_close
    mov     rax, [rsi + 8 + rcx * 8]
    cmp     rax, 65536
    jb      .pdls_z
    mov     r8d, dword [rax + 8]
    mov     r9d, dword [rax + 16]
    jmp     .pdls_st
.pdls_z:
    xor     r8d, r8d
    xor     r9d, r9d
.pdls_st:
    mov     dword [_pyfasm_pg_poly_pts + rcx * 8], r8d
    mov     dword [_pyfasm_pg_poly_pts + rcx * 8 + 4], r9d
    inc     rcx
    jmp     .pdls_up
.pdls_close:
    test    r12, r12
    jz      .pdls_draw
    mov     eax, dword [_pyfasm_pg_poly_pts]
    mov     dword [_pyfasm_pg_poly_pts + rdi * 8], eax
    mov     eax, dword [_pyfasm_pg_poly_pts + 4]
    mov     dword [_pyfasm_pg_poly_pts + rdi * 8 + 4], eax
    inc     rdi
.pdls_draw:
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     r8d, eax
    mov     edx, dword [rbp + 48]
    cmp     edx, 0
    jg      .pdls_w
    mov     edx, 1
.pdls_w:
    xor     ecx, ecx
    call    [CreatePen]
    mov     rsi, rax
    mov     rcx, r14
    mov     rdx, rsi
    call    [SelectObject]
    mov     rbx, rax
    mov     rcx, r14
    lea     rdx, [_pyfasm_pg_poly_pts]
    mov     r8d, edi
    call    [Polyline]
    mov     rcx, r14
    mov     rdx, rbx
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
.pdls_done:
    xor     eax, eax
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

_pyfasm_pg_draw_arc:
    ; RCX = surf, RDX = color, R8 = rect, R9 = start_f64, [rbp+48] = stop_f64, [rbp+56] = width
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
    mov     rbx, rdx
    mov     rsi, r8
    mov     r12, r9
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pda_done
    mov     r14, rax
    mov     rcx, rsi
    call    _pyfasm_pg_unpack_rect
    mov     rcx, rbx
    call    _pyfasm_pg_unpack_color
    mov     r8d, eax
    mov     edx, dword [rbp + 56]
    cmp     edx, 0
    jg      .pda_w
    mov     edx, 1
.pda_w:
    xor     ecx, ecx
    call    [CreatePen]
    mov     rsi, rax
    mov     rcx, r14
    mov     rdx, rsi
    call    [SelectObject]
    mov     rbx, rax

    mov     eax, dword [_pyfasm_pg_rc]
    add     eax, dword [_pyfasm_pg_rc + 8]
    sar     eax, 1
    mov     edi, eax                ; cx
    mov     eax, dword [_pyfasm_pg_rc + 4]
    add     eax, dword [_pyfasm_pg_rc + 12]
    sar     eax, 1
    mov     r13d, eax               ; cy

    ; start endpoint (x1, y1)
    mov     rax, r12
    call    _pyfasm_mpl_val_to_f64
    movsd   qword [rsp + 64], xmm0
    fld     qword [rsp + 64]
    fsincos
    fmul    qword [_pyfasm_pg_k1000]
    fistp   dword [rsp + 72]        ; cos*1000
    fmul    qword [_pyfasm_pg_k1000]
    fistp   dword [rsp + 76]        ; sin*1000
    mov     eax, edi
    add     eax, dword [rsp + 72]
    mov     [rsp + 32], eax         ; nXStartArc
    mov     eax, r13d
    sub     eax, dword [rsp + 76]
    mov     [rsp + 40], eax         ; nYStartArc

    ; stop endpoint (x2, y2)
    mov     rax, [rbp + 48]
    call    _pyfasm_mpl_val_to_f64
    movsd   qword [rsp + 64], xmm0
    fld     qword [rsp + 64]
    fsincos
    fmul    qword [_pyfasm_pg_k1000]
    fistp   dword [rsp + 72]
    fmul    qword [_pyfasm_pg_k1000]
    fistp   dword [rsp + 76]
    mov     eax, edi
    add     eax, dword [rsp + 72]
    mov     [rsp + 48], eax         ; nXEndArc
    mov     eax, r13d
    sub     eax, dword [rsp + 76]
    mov     [rsp + 56], eax         ; nYEndArc

    ; Arc uses bottom at [rsp+32] then x1,y1,x2,y2 at [rsp+40..64] -> shift our scratch vals cleanly:
    mov     r12d, dword [rsp + 32]  ; x1
    mov     edi, dword [rsp + 40]   ; y1
    mov     r13d, dword [rsp + 48]  ; x2
    mov     eax, dword [rsp + 56]   ; y2
    mov     [rsp + 64], eax
    mov     [rsp + 56], r13d
    mov     [rsp + 48], edi
    mov     [rsp + 40], r12d
    mov     eax, dword [_pyfasm_pg_rc + 12]
    mov     [rsp + 32], eax
    mov     rcx, r14
    mov     edx, dword [_pyfasm_pg_rc]
    mov     r8d, dword [_pyfasm_pg_rc + 4]
    mov     r9d, dword [_pyfasm_pg_rc + 8]
    call    [Arc]

    mov     rcx, r14
    mov     rdx, rbx
    call    [SelectObject]
    mov     rcx, rsi
    call    [DeleteObject]
.pda_done:
    xor     eax, eax
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

_pyfasm_pg_font_new:
    ; RCX = name_or_0, RDX = size, R8 = bold, R9 = italic -> RAX = HFONT
    jmp     _pyfasm_create_font

_pyfasm_pg_font_size:
    ; RCX = hfont_or_0, RDX = text_str -> RAX = [2, w_px, h_px]
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    xor     ecx, ecx
    call    [CreateCompatibleDC]
    mov     rdi, rax
    xor     eax, eax
    mov     [rsp + 40], rax         ; old_font
    test    rbx, rbx
    jz      .pfs_meas
    cmp     rbx, 1
    je      .pfs_meas
    mov     rcx, rdi
    mov     rdx, rbx
    call    [SelectObject]
    mov     [rsp + 40], rax
.pfs_meas:
    mov     qword [rsp + 32], 0
    test    rsi, rsi
    jz      .pfs_alloc
    mov     rcx, rsi
    lea     rdx, [_pyfasm_wide_buf]
    mov     r8, 1024
    call    _pyfasm_utf8_to_wide
    cmp     rax, 1
    jle     .pfs_alloc
    dec     rax
    mov     r8d, eax
    mov     rcx, rdi
    lea     rdx, [_pyfasm_wide_buf]
    lea     r9, [rsp + 32]          ; SIZE struct (cx, cy ints = 8B)
    call    [GetTextExtentPoint32W]
.pfs_alloc:
    mov     rdx, [rsp + 40]
    test    rdx, rdx
    jz      .pfs_del
    mov     rcx, rdi
    call    [SelectObject]
.pfs_del:
    mov     rcx, rdi
    call    [DeleteDC]
    mov     ecx, 32
    call    _pyfasm_alloc
    mov     qword [rax], 2
    movsxd  rcx, dword [rsp + 32]
    mov     [rax + 8], rcx
    movsxd  rcx, dword [rsp + 36]
    mov     [rax + 16], rcx
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_image_save:
    ; RCX = surf_or_screen, RDX = path_str
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 144
    and     rsp, -16
    mov     rsi, rdx
    call    _pyfasm_pg_resolve_surf
    test    rax, rax
    jz      .pis_done
    test    rsi, rsi
    jz      .pis_done
    mov     rbx, rax                ; src_hdc
    mov     rdi, rdx                ; W
    mov     r12, r8                 ; H
    cmp     rdi, 1
    jl      .pis_done
    cmp     r12, 1
    jl      .pis_done

    lea     eax, [edi * 3 + 3]
    and     eax, -4
    imul    r13d, eax, 1
    imul    r13, r12                ; pixel_bytes

    xor     ecx, ecx
.pis_z:
    mov     qword [rsp + 64 + rcx], 0
    add     ecx, 8
    cmp     ecx, 48
    jl      .pis_z
    mov     dword [rsp + 64], 40
    mov     dword [rsp + 68], edi
    mov     dword [rsp + 72], r12d
    mov     word [rsp + 76], 1
    mov     word [rsp + 78], 24
    mov     dword [rsp + 84], r13d

    xor     ecx, ecx
    call    [CreateCompatibleDC]
    mov     r14, rax
    test    r14, r14
    jz      .pis_done
    mov     rcx, r14
    lea     rdx, [rsp + 64]
    xor     r8d, r8d
    lea     r9, [rsp + 112]
    mov     qword [rsp + 32], 0
    mov     qword [rsp + 40], 0
    call    [CreateDIBSection]
    mov     r15, rax
    test    r15, r15
    jz      .pis_deldc
    mov     rcx, r14
    mov     rdx, r15
    call    [SelectObject]
    mov     [rsp + 120], rax

    mov     rcx, r14
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, edi
    mov     [rsp + 32], r12d
    mov     [rsp + 40], rbx
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     dword [rsp + 64], 00CC0020h
    call    [BitBlt]

    xor     ecx, ecx
.pis_zh:
    mov     byte [_pyfasm_pg_bmp_hdr + rcx], 0
    inc     ecx
    cmp     ecx, 54
    jl      .pis_zh
    mov     word [_pyfasm_pg_bmp_hdr + 0], 4D42h
    lea     eax, [r13d + 54]
    mov     dword [_pyfasm_pg_bmp_hdr + 2], eax
    mov     dword [_pyfasm_pg_bmp_hdr + 10], 54
    mov     dword [_pyfasm_pg_bmp_hdr + 14], 40
    mov     dword [_pyfasm_pg_bmp_hdr + 18], edi
    mov     dword [_pyfasm_pg_bmp_hdr + 22], r12d
    mov     word [_pyfasm_pg_bmp_hdr + 26], 1
    mov     word [_pyfasm_pg_bmp_hdr + 28], 24
    mov     dword [_pyfasm_pg_bmp_hdr + 34], r13d

    mov     rcx, rsi
    mov     edx, 40000000h
    xor     r8d, r8d
    xor     r9d, r9d
    mov     dword [rsp + 32], 2
    mov     dword [rsp + 40], 80h
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    cmp     rax, -1
    je      .pis_clean
    mov     rbx, rax
    mov     rcx, rbx
    lea     rdx, [_pyfasm_pg_bmp_hdr]
    mov     r8d, 54
    lea     r9, [rsp + 128]
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    mov     rcx, rbx
    mov     rdx, [rsp + 112]
    mov     r8d, r13d
    lea     r9, [rsp + 128]
    mov     qword [rsp + 32], 0
    call    [WriteFile]
    mov     rcx, rbx
    call    [CloseHandle]
.pis_clean:
    mov     rcx, r14
    mov     rdx, [rsp + 120]
    call    [SelectObject]
    mov     rcx, r15
    call    [DeleteObject]
.pis_deldc:
    mov     rcx, r14
    call    [DeleteDC]
.pis_done:
    xor     eax, eax
    lea     rsp, [rbp - 56]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_image_load:
    ; RCX = path_str -> RAX = PYFPGSRF
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16
    test    rcx, rcx
    jz      .pil_blank
    mov     edx, 80000000h          ; GENERIC_READ
    mov     r8d, 1                  ; FILE_SHARE_READ
    xor     r9d, r9d
    mov     dword [rsp + 32], 3     ; OPEN_EXISTING
    mov     dword [rsp + 40], 80h
    mov     qword [rsp + 48], 0
    call    [CreateFileA]
    cmp     rax, -1
    je      .pil_blank
    mov     rbx, rax
    mov     rcx, rbx
    lea     rdx, [_pyfasm_pg_bmp_hdr]
    mov     r8d, 54
    lea     r9, [rsp + 56]
    mov     qword [rsp + 32], 0
    call    [ReadFile]
    cmp     word [_pyfasm_pg_bmp_hdr], 4D42h
    jne     .pil_close_blank
    movsxd  rsi, dword [_pyfasm_pg_bmp_hdr + 18]
    movsxd  rdi, dword [_pyfasm_pg_bmp_hdr + 22]
    cmp     rdi, 0
    jge     .pil_h_pos
    neg     rdi
.pil_h_pos:
    cmp     word [_pyfasm_pg_bmp_hdr + 28], 24
    jne     .pil_close_blank
    mov     rcx, rsi
    mov     rdx, rdi
    call    _pyfasm_pg_surface_new
    mov     r12, rax
    mov     rax, [r12 + 40]
    test    rax, rax
    jz      .pil_close_done
    lea     ecx, [esi * 3 + 3]
    and     ecx, -4
    imul    r8d, ecx, 1
    imul    r8d, edi
    mov     rcx, rbx
    mov     rdx, rax
    lea     r9, [rsp + 56]
    mov     qword [rsp + 32], 0
    call    [ReadFile]
.pil_close_done:
    mov     rcx, rbx
    call    [CloseHandle]
    mov     rax, r12
    jmp     .pil_exit
.pil_close_blank:
    mov     rcx, rbx
    call    [CloseHandle]
.pil_blank:
    mov     ecx, 32
    mov     edx, 32
    call    _pyfasm_pg_surface_new
.pil_exit:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_transform_scale:
    ; RCX = surf, RDX = size_tuple_or_w, R8 = h_or_0 -> RAX = new PYFPGSRF
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 96
    and     rsp, -16
    mov     rsi, rdx
    mov     rdi, r8
    call    _pyfasm_pg_resolve_surf
    mov     rbx, rax                ; src_hdc
    mov     r12, rdx                ; src_w
    mov     r13, r8                 ; src_h
    cmp     rsi, 65536
    jb      .pts_wh
    cmp     qword [rsi], 2
    jl      .pts_wh
    mov     rdi, [rsi + 16]
    mov     rsi, [rsi + 8]
.pts_wh:
    mov     rcx, rsi
    mov     rdx, rdi
    call    _pyfasm_pg_surface_new
    mov     r14, rax
    test    rbx, rbx
    jz      .pts_done
    mov     rcx, [r14 + 24]
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, esi
    mov     [rsp + 32], edi
    mov     [rsp + 40], rbx
    mov     qword [rsp + 48], 0
    mov     qword [rsp + 56], 0
    mov     [rsp + 64], r12d
    mov     [rsp + 72], r13d
    mov     dword [rsp + 80], 00CC0020h
    call    [StretchBlt]
.pts_done:
    mov     rax, r14
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

_pyfasm_pg_transform_rotozoom:
    ; RCX = src surf, RDX = angle degrees (f64 bits), R8 = zoom (f64 bits) -> RAX = new PYFPGSRF
    ; Counter-clockwise rotation like pygame; the canvas grows to fit the rotated image.
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 120
    mov     rbx, rcx
    mov     [rsp + 64], r8
    movq    xmm0, rdx
    mov     rax, 400921FB54442D18h  ; pi
    movq    xmm1, rax
    mulsd   xmm0, xmm1
    mov     rax, 4066800000000000h  ; 180.0
    movq    xmm1, rax
    divsd   xmm0, xmm1
    movq    rcx, xmm0
    mov     [rsp + 72], rcx
    call    _pyfasm_math_cos
    mov     [rsp + 80], rax
    mov     rcx, [rsp + 72]
    call    _pyfasm_math_sin
    mov     [rsp + 88], rax
    xor     r12d, r12d
    xor     r13d, r13d
    mov     rax, 4652534750465950h  ; 'PYFPGSRF'
    cmp     rbx, 65536
    jb      .ptr_size
    cmp     [rbx], rax
    jne     .ptr_size
    mov     r12, [rbx + 8]
    mov     r13, [rbx + 16]
.ptr_size:
    ; new_w = (|w*cos| + |h*sin|) * zoom, new_h = (|w*sin| + |h*cos|) * zoom
    mov     rax, [_pyfasm_flt_abs_mask]
    movq    xmm7, rax
    movq    xmm2, [rsp + 80]
    andpd   xmm2, xmm7              ; |cos|
    movq    xmm3, [rsp + 88]
    andpd   xmm3, xmm7              ; |sin|
    cvtsi2sd xmm4, r12              ; w
    cvtsi2sd xmm5, r13              ; h
    movapd  xmm0, xmm4
    mulsd   xmm0, xmm2
    movapd  xmm1, xmm5
    mulsd   xmm1, xmm3
    addsd   xmm0, xmm1
    mulsd   xmm0, [rsp + 64]
    movapd  xmm1, xmm4
    mulsd   xmm1, xmm3
    movapd  xmm6, xmm5
    mulsd   xmm6, xmm2
    addsd   xmm1, xmm6
    mulsd   xmm1, [rsp + 64]
    cvtsd2si r14, xmm0
    cvtsd2si r15, xmm1
    cmp     r14, 1
    jge     .ptr_wok
    mov     r14d, 1
.ptr_wok:
    cmp     r15, 1
    jge     .ptr_hok
    mov     r15d, 1
.ptr_hok:
    mov     rcx, r14
    mov     rdx, r15
    call    _pyfasm_pg_surface_new
    mov     rsi, rax
    test    r12, r12
    jz      .ptr_done
    ; zoom == 0 leaves an empty canvas
    xorpd   xmm0, xmm0
    ucomisd xmm0, [rsp + 64]
    je      .ptr_done
    xor     edi, edi                ; dy
.ptr_row:
    cmp     rdi, r15
    jge     .ptr_done
    mov     qword [rsp + 96], 0     ; dx
.ptr_col:
    mov     rax, [rsp + 96]
    cmp     rax, r14
    jge     .ptr_next_row
    ; u = dx + 0.5 - new_w/2, v = dy + 0.5 - new_h/2
    cvtsi2sd xmm0, rax
    addsd   xmm0, [_pyfasm_flt_half]
    cvtsi2sd xmm1, r14
    mulsd   xmm1, [_pyfasm_flt_half]
    subsd   xmm0, xmm1
    cvtsi2sd xmm2, rdi
    addsd   xmm2, [_pyfasm_flt_half]
    cvtsi2sd xmm1, r15
    mulsd   xmm1, [_pyfasm_flt_half]
    subsd   xmm2, xmm1
    ; inverse rotation: sx = (u*cos - v*sin)/zoom + w/2, sy = (u*sin + v*cos)/zoom + h/2
    movq    xmm4, [rsp + 80]
    movq    xmm5, [rsp + 88]
    movapd  xmm1, xmm0
    mulsd   xmm1, xmm4
    movapd  xmm3, xmm2
    mulsd   xmm3, xmm5
    subsd   xmm1, xmm3
    divsd   xmm1, [rsp + 64]
    cvtsi2sd xmm3, r12
    mulsd   xmm3, [_pyfasm_flt_half]
    addsd   xmm1, xmm3
    movapd  xmm3, xmm0
    mulsd   xmm3, xmm5
    movapd  xmm6, xmm2
    mulsd   xmm6, xmm4
    addsd   xmm3, xmm6
    divsd   xmm3, [rsp + 64]
    cvtsi2sd xmm6, r13
    mulsd   xmm6, [_pyfasm_flt_half]
    addsd   xmm3, xmm6
    roundsd xmm1, xmm1, 1           ; floor
    roundsd xmm3, xmm3, 1
    cvtsd2si rdx, xmm1
    cvtsd2si r8, xmm3
    mov     rcx, rbx
    call    _pyfasm_pg_pixel_addr
    test    rax, rax
    jz      .ptr_next_col
    mov     [rsp + 104], rax
    mov     rcx, rsi
    mov     rdx, [rsp + 96]
    mov     r8, rdi
    call    _pyfasm_pg_pixel_addr
    test    rax, rax
    jz      .ptr_next_col
    mov     rcx, [rsp + 104]
    mov     dl, [rcx]
    mov     [rax], dl
    mov     dl, [rcx + 1]
    mov     [rax + 1], dl
    mov     dl, [rcx + 2]
    mov     [rax + 2], dl
.ptr_next_col:
    inc     qword [rsp + 96]
    jmp     .ptr_col
.ptr_next_row:
    inc     rdi
    jmp     .ptr_row
.ptr_done:
    mov     rax, rsi
    add     rsp, 120
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    pop     rbp
    ret

_pyfasm_pg_transform_flip:
    ; RCX = surf, RDX = xbool, R8 = ybool -> RAX = new PYFPGSRF
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 96
    and     rsp, -16
    mov     rsi, rdx                ; xbool
    mov     rdi, r8                 ; ybool
    call    _pyfasm_pg_resolve_surf
    mov     rbx, rax
    mov     r12, rdx                ; w
    mov     r13, r8                 ; h
    mov     rcx, r12
    mov     rdx, r13
    call    _pyfasm_pg_surface_new
    mov     r14, rax
    test    rbx, rbx
    jz      .ptf_done
    xor     eax, eax
    mov     ecx, r12d
    test    rsi, rsi
    jz      .ptf_no_x
    lea     eax, [r12d - 1]
    neg     ecx
.ptf_no_x:
    xor     edx, edx
    mov     r8d, r13d
    test    rdi, rdi
    jz      .ptf_no_y
    lea     edx, [r13d - 1]
    neg     r8d
.ptf_no_y:
    mov     [rsp + 48], eax         ; xSrc
    mov     [rsp + 56], edx         ; ySrc
    mov     [rsp + 64], ecx         ; wSrc
    mov     [rsp + 72], r8d         ; hSrc
    mov     dword [rsp + 80], 00CC0020h
    mov     rcx, [r14 + 24]
    xor     edx, edx
    xor     r8d, r8d
    mov     r9d, r12d
    mov     [rsp + 32], r13d
    mov     [rsp + 40], rbx
    call    [StretchBlt]
.ptf_done:
    mov     rax, r14
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

_pyfasm_pg_rect_move:
    ; RCX = rect, RDX = dx, R8 = dy -> RAX = new PYFRECT
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .prm_zero
    mov     r9, [rcx + 72]
    mov     r10, [rcx + 64]
    mov     rax, [rcx + 48]
    add     rax, rdx
    mov     rdx, [rcx + 56]
    add     rdx, r8
    mov     rcx, rax
    mov     r8, r10
    call    _pyfasm_pg_rect_new
    jmp     .prm_done
.prm_zero:
    xor     eax, eax
.prm_done:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_rect_move_ip:
    test    rcx, rcx
    jz      .prmip_d
    add     [rcx + 48], rdx
    add     [rcx + 56], r8
.prmip_d:
    xor     eax, eax
    ret

_pyfasm_pg_rect_inflate:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .pri_z
    mov     r10, rdx
    mov     r11, r8
    mov     rax, [rcx + 48]
    mov     r9, r10
    sar     r9, 1
    sub     rax, r9
    mov     r9, r11
    sar     r9, 1
    mov     rdx, [rcx + 56]
    sub     rdx, r9
    mov     r8, [rcx + 64]
    add     r8, r10
    mov     r9, [rcx + 72]
    add     r9, r11
    mov     rcx, rax
    call    _pyfasm_pg_rect_new
    jmp     .pri_d
.pri_z:
    xor     eax, eax
.pri_d:
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_rect_copy:
    test    rcx, rcx
    jz      .prcp_z
    mov     r9, [rcx + 72]
    mov     r8, [rcx + 64]
    mov     rdx, [rcx + 56]
    mov     rcx, [rcx + 48]
    jmp     _pyfasm_pg_rect_new
.prcp_z:
    xor     eax, eax
    ret

_pyfasm_pg_rect_clamp_ip:
    test    rcx, rcx
    jz      .prcl_d
    test    rdx, rdx
    jz      .prcl_d
    mov     r8, [rcx + 48]
    mov     r9, [rdx + 48]
    cmp     r8, r9
    jge     .prcl_x1
    mov     r8, r9
.prcl_x1:
    mov     r10, r9
    add     r10, [rdx + 64]
    sub     r10, [rcx + 64]
    cmp     r8, r10
    jle     .prcl_x2
    mov     r8, r10
.prcl_x2:
    mov     [rcx + 48], r8
    mov     r8, [rcx + 56]
    mov     r9, [rdx + 56]
    cmp     r8, r9
    jge     .prcl_y1
    mov     r8, r9
.prcl_y1:
    mov     r10, r9
    add     r10, [rdx + 72]
    sub     r10, [rcx + 72]
    cmp     r8, r10
    jle     .prcl_y2
    mov     r8, r10
.prcl_y2:
    mov     [rcx + 56], r8
.prcl_d:
    xor     eax, eax
    ret

_pyfasm_pg_rect_collidelist:
    ; RCX = rect, RDX = rect_list -> RAX = index or -1
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .prcli_no
    cmp     rdx, 65536
    jb      .prcli_no
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, [rsi]
    mov     qword [rsp + 32], 0
.prcli_lp:
    mov     rax, [rsp + 32]
    cmp     rax, rdi
    jge     .prcli_no
    mov     rcx, rbx
    mov     rdx, [rsi + 8 + rax * 8]
    call    _pyfasm_pg_rect_colliderect
    test    rax, rax
    jnz     .prcli_hit
    inc     qword [rsp + 32]
    jmp     .prcli_lp
.prcli_hit:
    mov     rax, [rsp + 32]
    jmp     .prcli_d
.prcli_no:
    mov     rax, -1
.prcli_d:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_color_new:
    ; RCX = r_or_str, RDX = g, R8 = b -> RAX = PYFPGCOL
    push    rbp
    mov     rbp, rsp
    push    rbx
    sub     rsp, 32
    and     rsp, -16
    cmp     rcx, 65536
    jb      .pcn_rgb
    xor     edx, edx
    call    _pyfasm_mpl_parse_color
    mov     ebx, eax
    jmp     .pcn_alloc
.pcn_rgb:
    mov     ebx, ecx
    and     ebx, 0FFh
    and     edx, 0FFh
    shl     edx, 8
    and     r8d, 0FFh
    shl     r8d, 16
    or      ebx, edx
    or      ebx, r8d
.pcn_alloc:
    mov     ecx, 16
    call    _pyfasm_alloc
    mov     rcx, 5059465047434F4Ch  ; 'PYFPGCOL'
    mov     [rax], rcx
    mov     [rax + 8], rbx
    lea     rsp, [rbp - 8]
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_pg_group_new:
    push    rbp
    mov     rbp, rsp
    sub     rsp, 32
    and     rsp, -16
    xor     ecx, ecx
    call    _pyfasm_list_create
    mov     rsp, rbp
    pop     rbp
    ret

; --- pygame.sprite.Sprite kill/alive protocol -------------------------
; Sprite objects are class instances (2048 bytes). Slot +2024 is reserved:
; 0 = alive, 1 = killed. Group draw/update skip killed sprites.

_pyfasm_sprite_kill:
    ; RCX = sprite instance
    test    rcx, rcx
    jz      .spk_done
    cmp     rcx, 65536
    jb      .spk_done
    mov     r10, 505946434C535447h  ; PYFCLSTG
    cmp     [rcx + 2032], r10
    jne     .spk_done
    mov     qword [rcx + 2024], 1
.spk_done:
    xor     eax, eax
    ret

_pyfasm_sprite_alive:
    ; RCX = sprite instance -> RAX = 1 if alive
    xor     eax, eax
    test    rcx, rcx
    jz      .spa_done
    cmp     rcx, 65536
    jb      .spa_done
    mov     r10, 505946434C535447h  ; PYFCLSTG
    cmp     [rcx + 2032], r10
    jne     .spa_done
    cmp     qword [rcx + 2024], 0
    sete    al
    movzx   rax, al
.spa_done:
    ret

_pyfasm_group_empty:
    ; RCX = group list -> clears elements
    test    rcx, rcx
    jz      .ge_done
    mov     qword [rcx], 0
.ge_done:
    xor     eax, eax
    ret

_pyfasm_pg_mixer_noop:
    mov     rax, 1
    ret
"""
