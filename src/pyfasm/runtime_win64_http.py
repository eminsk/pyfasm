"""Win64 native Winsock2 HTTP/1.1 + RFC-8259 JSON server runtime for fastapi & uvicorn."""

WIN64_HTTP_RUNTIME_DATA = """
    ; --- Native FastAPI / Uvicorn Winsock2 HTTP Server Data ---
    align 8
    _pyfasm_http_srv_route_cnt dq 0
    align 8
    ; 128 route entries * 64 bytes = 8192 bytes:
    ;   +0: method_ptr, +8: pattern_ptr, +16: handler_ptr, +24: return_kind,
    ;   +32: param_count, +40: param_int_mask, +48: param_names_arr, +56: reserved
    _pyfasm_http_routes     rb 8192
    align 8
    _pyfasm_wsadata         rb 512
    _pyfasm_sockaddr        rb 32
    _pyfasm_sock_opt_one    dd 1
    align 8
    _pyfasm_http_req_buf    rb 16384
    _pyfasm_http_resp_hdr   rb 1024
    _pyfasm_http_json_buf   rb 65536
    _pyfasm_http_param_vals rq 16
    _pyfasm_http_listen_sock dq -1

    szHttp200Json   db 'HTTP/1.1 200 OK', 13, 10, 'Content-Type: application/json; charset=utf-8', 13, 10, 'Content-Length: ', 0
    szHttp200Html   db 'HTTP/1.1 200 OK', 13, 10, 'Content-Type: text/html; charset=utf-8', 13, 10, 'Content-Length: ', 0
    szHttp200Text   db 'HTTP/1.1 200 OK', 13, 10, 'Content-Type: text/plain; charset=utf-8', 13, 10, 'Content-Length: ', 0
    szHttpConnClose db 13, 10, 'Connection: close', 13, 10, 13, 10, 0
    szHttp404Resp   db 'HTTP/1.1 404 Not Found', 13, 10, 'Content-Type: application/json', 13, 10, 'Content-Length: 22', 13, 10, 'Connection: close', 13, 10, 13, 10, '{"detail":"Not Found"}', 0
    szHttpOpenApi   db '/openapi.json', 0
    szHttpOpenApiPre db '{"openapi":"3.0.0","info":{"title":"PyFASM64 FastAPI","version":"1.0.0"},"paths":{', 0
    szHttpOpenApiSuf db '}}', 0
    szHttpOpenApiItem db ':{"get":{"responses":{"200":{"description":"OK"}}}}', 0
    szJsonNull      db 'null', 0
    szJsonTrue      db 'true', 0
    szJsonFalse     db 'false', 0
    szEmptyStr      db 0
    szDefHost       db '127.0.0.1', 0
    szHttpContentLen db 'content-length:', 0
"""

WIN64_HTTP_RUNTIME_CODE = """
_pyfasm_json_write_escaped_str:
    ; RCX = utf8 str_ptr, RDI = dest cursor -> RAX = updated dest cursor
    lea     r9, [_pyfasm_http_json_buf + 65000]
    cmp     rdi, r9
    jae     .jwe_cap
    mov     byte [rdi], '"'
    inc     rdi
    test    rcx, rcx
    jz      .jwe_close
.jwe_loop:
    cmp     rdi, r9
    jae     .jwe_close
    movzx   eax, byte [rcx]
    test    al, al
    jz      .jwe_close
    cmp     al, '"'
    je      .jwe_esc_q
    cmp     al, 92
    je      .jwe_esc_bs
    cmp     al, 10
    je      .jwe_esc_n
    cmp     al, 13
    je      .jwe_esc_r
    cmp     al, 9
    je      .jwe_esc_t
    mov     [rdi], al
    inc     rdi
    inc     rcx
    jmp     .jwe_loop
.jwe_esc_q:
    mov     byte [rdi], 92
    mov     byte [rdi + 1], '"'
    add     rdi, 2
    inc     rcx
    jmp     .jwe_loop
.jwe_esc_bs:
    mov     byte [rdi], 92
    mov     byte [rdi + 1], 92
    add     rdi, 2
    inc     rcx
    jmp     .jwe_loop
.jwe_esc_n:
    mov     byte [rdi], 92
    mov     byte [rdi + 1], 'n'
    add     rdi, 2
    inc     rcx
    jmp     .jwe_loop
.jwe_esc_r:
    mov     byte [rdi], 92
    mov     byte [rdi + 1], 'r'
    add     rdi, 2
    inc     rcx
    jmp     .jwe_loop
.jwe_esc_t:
    mov     byte [rdi], 92
    mov     byte [rdi + 1], 't'
    add     rdi, 2
    inc     rcx
    jmp     .jwe_loop
.jwe_close:
    mov     byte [rdi], '"'
    inc     rdi
.jwe_cap:
    mov     rax, rdi
    ret

_pyfasm_json_copy_cstr:
    ; RCX = src, RDI = dest -> RAX = updated dest
    test    rcx, rcx
    jz      .jcc_done
    lea     r9, [_pyfasm_http_json_buf + 65000]
.jcc_loop:
    cmp     rdi, r9
    jae     .jcc_done
    mov     al, [rcx]
    test    al, al
    jz      .jcc_done
    mov     [rdi], al
    inc     rdi
    inc     rcx
    jmp     .jcc_loop
.jcc_done:
    mov     rax, rdi
    ret

_pyfasm_json_write_auto:
    ; RCX = val, RDX = kind (0=auto, 1=dict, 2=list, 3=str, 4=int, 5=float, 6=bool), RDI = dest -> RAX = dest
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    sub     rsp, 96
    and     rsp, -16

    mov     rbx, rcx
    mov     rsi, rdx

    cmp     rsi, 6
    je      .jwa_bool
    cmp     rsi, 5
    je      .jwa_float
    cmp     rsi, 4
    je      .jwa_int
    cmp     rsi, 3
    je      .jwa_str
    cmp     rsi, 2
    je      .jwa_list
    cmp     rsi, 1
    je      .jwa_dict

    ; Auto detection
    cmp     rbx, 65536
    jb      .jwa_int
    mov     rax, 00007FFFFFFF0000h
    cmp     rbx, rax
    jae     .jwa_int

    ; Check if committed readable pointer and detect dict before string (dict cap >= 256 has low byte 0)
    mov     rcx, rbx
    lea     rdx, [rsp + 32]
    mov     r8d, 48
    call    [VirtualQuery]
    test    rax, rax
    jz      .jwa_int
    cmp     dword [rsp + 64], 1000h     ; MEM_COMMIT
    jne     .jwa_int
    mov     eax, dword [rsp + 68]
    test    eax, 100h                   ; PAGE_GUARD
    jnz     .jwa_int
    test    eax, 0EEh                   ; readable
    jz      .jwa_int

    mov     r9, [rsp + 32]              ; BaseAddress
    add     r9, [rsp + 56]              ; + RegionSize
    sub     r9, rbx                     ; remaining bytes
    cmp     r9, 16
    jb      .jwa_try_str

    mov     rcx, [rbx]
    cmp     rcx, 256
    jb      .jwa_try_str
    cmp     rcx, 1048576
    ja      .jwa_try_str
    lea     rax, [rcx - 1]
    test    rax, rcx
    jnz     .jwa_try_str
    mov     r8, [rbx + 8]
    test    r8, r8
    js      .jwa_try_str
    cmp     r8, rcx
    ja      .jwa_try_str
    lea     rax, [rcx + rcx * 2]
    shl     rax, 3
    add     rax, 16
    cmp     rax, r9
    ja      .jwa_try_str
    jmp     .jwa_dict

.jwa_try_str:
    mov     [rsp + 80], r9
    mov     rcx, rbx
    call    _pyfasm_is_utf8_str_ptr
    test    rax, rax
    jnz     .jwa_str

    mov     r9, [rsp + 80]
    cmp     r9, 8
    jb      .jwa_int
    mov     rcx, [rbx]
    test    rcx, rcx
    js      .jwa_int
    cmp     rcx, 65536
    ja      .jwa_int
    lea     rax, [rcx + 1]
    shl     rax, 3
    cmp     rax, r9
    ja      .jwa_int
    jmp     .jwa_list

.jwa_bool:
    test    rbx, rbx
    jz      .jwa_false
    lea     rcx, [szJsonTrue]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    jmp     .jwa_done
.jwa_false:
    lea     rcx, [szJsonFalse]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    jmp     .jwa_done

.jwa_float:
    mov     rcx, rbx
    call    _pyfasm_float_to_str
    mov     rcx, rax
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    jmp     .jwa_done

.jwa_str:
    mov     rcx, rbx
    call    _pyfasm_json_write_escaped_str
    mov     rdi, rax
    jmp     .jwa_done

.jwa_int:
    mov     rcx, rbx
    call    _pyfasm_int_to_str
    mov     rcx, rax
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    jmp     .jwa_done

.jwa_list:
    mov     rcx, rbx
    call    _pyfasm_json_write_list
    mov     rdi, rax
    jmp     .jwa_done

.jwa_dict:
    mov     rcx, rbx
    call    _pyfasm_json_write_dict
    mov     rdi, rax

.jwa_done:
    mov     rax, rdi
    lea     rsp, [rbp - 16]
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_json_write_list:
    ; RCX = list_ptr [len, item0, ...], RDI = dest -> RAX = dest
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jnz     .jwl_ok
    lea     rcx, [szJsonNull]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    jmp     .jwl_done
.jwl_ok:
    mov     byte [rdi], '['
    inc     rdi
    mov     r12, [rbx]
    xor     esi, esi
.jwl_loop:
    cmp     rsi, r12
    jge     .jwl_end
    test    rsi, rsi
    jz      .jwl_elem
    mov     byte [rdi], ','
    inc     rdi
.jwl_elem:
    mov     rcx, [rbx + rsi * 8 + 8]
    xor     edx, edx
    call    _pyfasm_json_write_auto
    mov     rdi, rax
    inc     rsi
    jmp     .jwl_loop
.jwl_end:
    mov     byte [rdi], ']'
    inc     rdi
.jwl_done:
    mov     rax, rdi
    lea     rsp, [rbp - 24]
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_json_write_dict:
    ; RCX = dict_ptr [cap, count, slots (24 bytes: hash, key, val)], RDI = dest -> RAX = dest
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    and     rsp, -16
    mov     rbx, rcx
    test    rbx, rbx
    jnz     .jwd_ok
    lea     rcx, [szJsonNull]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    jmp     .jwd_done
.jwd_ok:
    mov     byte [rdi], '{'
    inc     rdi
    mov     r12, [rbx]              ; capacity
    xor     esi, esi                ; slot idx
    xor     r13d, r13d              ; emitted count
.jwd_loop:
    cmp     rsi, r12
    jge     .jwd_end
    lea     rax, [rsi + rsi * 2]
    shl     rax, 3
    lea     r10, [rbx + 16 + rax]
    mov     rcx, [r10]              ; hash
    test    rcx, rcx
    jz      .jwd_next
    cmp     rcx, -1
    je      .jwd_next

    test    r13d, r13d
    jz      .jwd_key
    mov     byte [rdi], ','
    inc     rdi
.jwd_key:
    inc     r13d
    mov     r14, [r10 + 8]          ; key (preserved across calls)
    mov     rcx, r14
    cmp     rcx, 65536
    jae     .jwd_chk_str_key
.jwd_int_key:
    call    _pyfasm_int_to_str
    mov     rcx, rax
    call    _pyfasm_json_write_escaped_str
    mov     rdi, rax
    jmp     .jwd_val
.jwd_chk_str_key:
    mov     rcx, r14
    call    _pyfasm_is_utf8_str_ptr
    test    rax, rax
    mov     rcx, r14
    jz      .jwd_int_key
    call    _pyfasm_json_write_escaped_str
    mov     rdi, rax

.jwd_val:
    mov     byte [rdi], ':'
    inc     rdi
    lea     rax, [rsi + rsi * 2]
    shl     rax, 3
    mov     rcx, [rbx + 16 + rax + 16]
    xor     edx, edx
    call    _pyfasm_json_write_auto
    mov     rdi, rax

.jwd_next:
    inc     rsi
    jmp     .jwd_loop

.jwd_end:
    mov     byte [rdi], '}'
    inc     rdi
.jwd_done:
    mov     rax, rdi
    lea     rsp, [rbp - 40]
    pop     r14
    pop     r13
    pop     r12
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_url_decode_alloc:
    ; RCX = src start, RDX = byte len -> RAX = newly allocated null-terminated decoded UTF-8 string
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 40
    and     rsp, -16
    mov     rsi, rcx
    mov     rbx, rdx
    lea     rcx, [rbx + 1]
    call    _pyfasm_alloc
    mov     rdi, rax
    mov     r10, rax
    xor     ecx, ecx
.uda_loop:
    cmp     rcx, rbx
    jge     .uda_done
    movzx   eax, byte [rsi + rcx]
    cmp     al, '+'
    je      .uda_plus
    cmp     al, '%'
    jne     .uda_store
    lea     r8, [rcx + 2]
    cmp     r8, rbx
    jge     .uda_store
    movzx   r8d, byte [rsi + rcx + 1]
    movzx   r9d, byte [rsi + rcx + 2]
    ; hex digit 1
    cmp     r8b, '9'
    jbe     .uda_h1_dig
    or      r8b, 20h
    sub     r8b, 'a' - 10
    jmp     .uda_h2
.uda_h1_dig:
    sub     r8b, '0'
.uda_h2:
    cmp     r9b, '9'
    jbe     .uda_h2_dig
    or      r9b, 20h
    sub     r9b, 'a' - 10
    jmp     .uda_comb
.uda_h2_dig:
    sub     r9b, '0'
.uda_comb:
    shl     r8d, 4
    or      r8d, r9d
    mov     [rdi], r8b
    inc     rdi
    add     rcx, 3
    jmp     .uda_loop
.uda_plus:
    mov     byte [rdi], ' '
    inc     rdi
    inc     rcx
    jmp     .uda_loop
.uda_store:
    mov     [rdi], al
    inc     rdi
    inc     rcx
    jmp     .uda_loop
.uda_done:
    mov     byte [rdi], 0
    mov     rax, r10
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_http_find_query_param:
    ; RCX = query_str (null-terminated), RDX = param_name -> RAX = decoded str ptr or 0
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 32
    and     rsp, -16
    test    rcx, rcx
    jz      .hq_not_found
    test    rdx, rdx
    jz      .hq_not_found
    mov     rsi, rcx
    mov     rdi, rdx
    ; rbx = len(param_name)
    xor     ebx, ebx
.hq_nlen:
    cmp     byte [rdi + rbx], 0
    je      .hq_scan
    inc     rbx
    jmp     .hq_nlen
.hq_scan:
    cmp     byte [rsi], 0
    je      .hq_not_found
    xor     r12d, r12d
.hq_cmp:
    cmp     r12, rbx
    jge     .hq_chk_eq
    mov     al, [rsi + r12]
    cmp     al, [rdi + r12]
    jne     .hq_skip_pair
    inc     r12
    jmp     .hq_cmp
.hq_chk_eq:
    cmp     byte [rsi + rbx], '='
    jne     .hq_skip_pair
    lea     rcx, [rsi + rbx + 1]
    xor     edx, edx
.hq_vlen:
    mov     al, [rcx + rdx]
    test    al, al
    jz      .hq_vfound
    cmp     al, '&'
    je      .hq_vfound
    inc     rdx
    jmp     .hq_vlen
.hq_vfound:
    call    _pyfasm_url_decode_alloc
    jmp     .hq_done
.hq_skip_pair:
    mov     al, [rsi]
    test    al, al
    jz      .hq_not_found
    inc     rsi
    cmp     al, '&'
    je      .hq_scan
    jmp     .hq_skip_pair
.hq_not_found:
    xor     eax, eax
.hq_done:
    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_http_match_path:
    ; RCX = pattern_str, RDX = req_path -> RAX = path_param_count (>=0 if match, -1 if mismatch)
    ; Populates _pyfasm_http_param_vals[0..path_param_count-1] with decoded string pointers
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    sub     rsp, 32
    and     rsp, -16

    mov     rsi, rcx                ; pattern
    mov     rdi, rdx                ; req_path
    xor     r12d, r12d              ; path_param_count

.hmp_loop:
    cmp     byte [rsi], '/'
    jne     .hmp_pat_no_slash
    inc     rsi
.hmp_pat_no_slash:
    cmp     byte [rdi], '/'
    jne     .hmp_req_no_slash
    inc     rdi
.hmp_req_no_slash:
    mov     al, [rsi]
    mov     bl, [rdi]
    test    al, al
    jnz     .hmp_check_req_end
    test    bl, bl
    jnz     .hmp_fail
    mov     rax, r12
    jmp     .hmp_done

.hmp_check_req_end:
    test    bl, bl
    jz      .hmp_fail

    ; Extract segment ends
    mov     r13, rsi
.hmp_pat_seg:
    mov     al, [r13]
    test    al, al
    jz      .hmp_pat_seg_done
    cmp     al, '/'
    je      .hmp_pat_seg_done
    inc     r13
    jmp     .hmp_pat_seg
.hmp_pat_seg_done:

    mov     r14, rdi
.hmp_req_seg:
    mov     al, [r14]
    test    al, al
    jz      .hmp_req_seg_done
    cmp     al, '/'
    je      .hmp_req_seg_done
    inc     r14
    jmp     .hmp_req_seg
.hmp_req_seg_done:

    cmp     byte [rsi], '{'
    jne     .hmp_lit_cmp
    mov     rcx, rdi
    mov     rdx, r14
    sub     rdx, rdi
    call    _pyfasm_url_decode_alloc
    cmp     r12, 16
    jge     .hmp_next_seg
    mov     [_pyfasm_http_param_vals + r12 * 8], rax
    inc     r12
    jmp     .hmp_next_seg

.hmp_lit_cmp:
    mov     rcx, r13
    sub     rcx, rsi
    mov     rdx, r14
    sub     rdx, rdi
    cmp     rcx, rdx
    jne     .hmp_fail
    xor     r8d, r8d
.hmp_lit_loop:
    cmp     r8, rcx
    jge     .hmp_next_seg
    mov     al, [rsi + r8]
    cmp     al, [rdi + r8]
    jne     .hmp_fail
    inc     r8
    jmp     .hmp_lit_loop

.hmp_next_seg:
    mov     rsi, r13
    mov     rdi, r14
    jmp     .hmp_loop

.hmp_fail:
    mov     rax, -1
.hmp_done:
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

_pyfasm_http_cstr_eq:
    ; RCX = a, RDX = b -> RAX = 1 if equal else 0
    test    rcx, rcx
    jz      .hce_no
    test    rdx, rdx
    jz      .hce_no
.hce_loop:
    mov     al, [rcx]
    cmp     al, [rdx]
    jne     .hce_no
    test    al, al
    jz      .hce_yes
    inc     rcx
    inc     rdx
    jmp     .hce_loop
.hce_yes:
    mov     rax, 1
    ret
.hce_no:
    xor     eax, eax
    ret

_pyfasm_http_send_all:
    ; RCX = sock, RDX = buf, R8 = total_len
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 40
    and     rsp, -16
    mov     rbx, rcx
    mov     rsi, rdx
    mov     rdi, r8
.hsa_loop:
    test    rdi, rdi
    jle     .hsa_done
    mov     rcx, rbx
    mov     rdx, rsi
    mov     r8d, edi
    xor     r9d, r9d
    call    [send]
    cmp     eax, 0
    jle     .hsa_done
    movsxd  rax, eax
    add     rsi, rax
    sub     rdi, rax
    jmp     .hsa_loop
.hsa_done:
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_http_register_route:
    ; RCX = method_str, RDX = pattern_str, R8 = handler_ptr, R9 = return_kind
    ; [rbp+48] = param_count, [rbp+56] = param_int_mask, [rbp+64] = param_names_arr
    push    rbp
    mov     rbp, rsp
    mov     rax, [_pyfasm_http_srv_route_cnt]
    cmp     rax, 128
    jge     .hrr_done
    shl     rax, 6                  ; * 64
    lea     r10, [_pyfasm_http_routes + rax]
    mov     [r10], rcx
    mov     [r10 + 8], rdx
    mov     [r10 + 16], r8
    mov     [r10 + 24], r9
    mov     rax, [rbp + 48]
    mov     [r10 + 32], rax
    mov     rax, [rbp + 56]
    mov     [r10 + 40], rax
    mov     rax, [rbp + 64]
    mov     [r10 + 48], rax
    inc     qword [_pyfasm_http_srv_route_cnt]
.hrr_done:
    xor     eax, eax
    pop     rbp
    ret

_pyfasm_http_send_openapi:
    ; RCX = client_sock
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    sub     rsp, 64
    and     rsp, -16
    mov     rbx, rcx
    lea     rdi, [_pyfasm_http_json_buf]
    lea     rcx, [szHttpOpenApiPre]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    mov     r12, [_pyfasm_http_srv_route_cnt]
    xor     esi, esi
.hoa_loop:
    cmp     rsi, r12
    jge     .hoa_end
    test    rsi, rsi
    jz      .hoa_path
    mov     byte [rdi], ','
    inc     rdi
.hoa_path:
    mov     rax, rsi
    shl     rax, 6
    mov     rcx, qword [_pyfasm_http_routes + rax + 8]
    call    _pyfasm_json_write_escaped_str
    mov     rdi, rax
    lea     rcx, [szHttpOpenApiItem]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    inc     rsi
    jmp     .hoa_loop
.hoa_end:
    lea     rcx, [szHttpOpenApiSuf]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    mov     byte [rdi], 0
    lea     rsi, [_pyfasm_http_json_buf]
    sub     rdi, rsi                ; body_len
    mov     [rsp + 32], rdi

    lea     rdi, [_pyfasm_http_resp_hdr]
    lea     rcx, [szHttp200Json]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    mov     rcx, [rsp + 32]
    call    _pyfasm_int_to_str
    mov     rcx, rax
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    lea     rcx, [szHttpConnClose]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    lea     rdx, [_pyfasm_http_resp_hdr]
    mov     r8, rdi
    sub     r8, rdx
    mov     rcx, rbx
    call    _pyfasm_http_send_all

    mov     rcx, rbx
    lea     rdx, [_pyfasm_http_json_buf]
    mov     r8, [rsp + 32]
    call    _pyfasm_http_send_all

    lea     rsp, [rbp - 32]
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret

_pyfasm_http_handle_client:
    ; RCX = client_sock
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13
    push    r14
    push    r15
    sub     rsp, 160
    and     rsp, -16

    mov     rbx, rcx                ; client_sock
    lea     rsi, [_pyfasm_http_req_buf]
    xor     r12d, r12d              ; total bytes received
    xor     r13d, r13d              ; body_ptr = 0
.hhc_hdr_recv:
    mov     rax, 16383
    sub     rax, r12
    jle     .hhc_parse_line
    mov     rcx, rbx
    lea     rdx, [rsi + r12]
    mov     r8d, eax
    xor     r9d, r9d
    call    [recv]
    cmp     eax, 0
    jg      .hhc_hdr_got
    test    r12, r12
    jz      .hhc_close
    jmp     .hhc_parse_line
.hhc_hdr_got:
    movsxd  rax, eax
    add     r12, rax
    mov     byte [rsi + r12], 0
    xor     ecx, ecx
.hhc_find_crlf:
    lea     rax, [rcx + 3]
    cmp     rax, r12
    jge     .hhc_hdr_recv
    cmp     dword [rsi + rcx], 0A0D0A0Dh ; CRLFCRLF
    je      .hhc_got_hdr_end
    inc     rcx
    jmp     .hhc_find_crlf
.hhc_got_hdr_end:
    lea     r14, [rcx + 4]          ; hdr_end offset
    lea     r13, [rsi + r14]        ; body_ptr

    ; Scan headers [rsi .. rsi+r14] case-insensitively for 'content-length:'
    xor     ecx, ecx
    xor     r15d, r15d              ; expected content_length
.hhc_cl_scan:
    lea     rax, [rcx + 15]
    cmp     rax, r14
    jge     .hhc_recv_body
    xor     edx, edx
.hhc_cl_cmp:
    cmp     edx, 15
    je      .hhc_cl_match
    lea     r8, [rsi + rcx]
    mov     al, [r8 + rdx]
    cmp     al, 'A'
    jb      .hhc_cl_lc
    cmp     al, 'Z'
    ja      .hhc_cl_lc
    or      al, 20h
.hhc_cl_lc:
    cmp     al, [szHttpContentLen + rdx]
    jne     .hhc_cl_next
    inc     edx
    jmp     .hhc_cl_cmp
.hhc_cl_next:
    inc     rcx
    jmp     .hhc_cl_scan
.hhc_cl_match:
    add     rcx, 15
.hhc_cl_ws:
    cmp     rcx, r14
    jge     .hhc_recv_body
    mov     al, [rsi + rcx]
    cmp     al, ' '
    je      .hhc_cl_ws_inc
    cmp     al, 9
    jne     .hhc_cl_digits
.hhc_cl_ws_inc:
    inc     rcx
    jmp     .hhc_cl_ws
.hhc_cl_digits:
    cmp     rcx, r14
    jge     .hhc_recv_body
    movzx   eax, byte [rsi + rcx]
    cmp     al, '0'
    jb      .hhc_recv_body
    cmp     al, '9'
    ja      .hhc_recv_body
    sub     al, '0'
    imul    r15, r15, 10
    add     r15, rax
    inc     rcx
    jmp     .hhc_cl_digits

.hhc_recv_body:
    add     r15, r14                ; need = hdr_end + content_length
    cmp     r15, 16383
    jle     .hhc_body_loop
    mov     r15, 16383
.hhc_body_loop:
    cmp     r12, r15
    jge     .hhc_parse_line
    mov     rax, r15
    sub     rax, r12
    mov     rcx, rbx
    lea     rdx, [rsi + r12]
    mov     r8d, eax
    xor     r9d, r9d
    call    [recv]
    cmp     eax, 0
    jle     .hhc_parse_line
    movsxd  rax, eax
    add     r12, rax
    mov     byte [rsi + r12], 0
    jmp     .hhc_body_loop

.hhc_parse_line:
    ; Method is at rsi..space
    mov     r14, rsi                ; method_ptr
    xor     ecx, ecx
.hhc_m_end:
    mov     al, [rsi + rcx]
    test    al, al
    jz      .hhc_send_404
    cmp     al, ' '
    je      .hhc_m_sp
    inc     rcx
    jmp     .hhc_m_end
.hhc_m_sp:
    mov     byte [rsi + rcx], 0
    lea     r15, [rsi + rcx + 1]    ; req_uri
    mov     [rsp + 64], r15
    xor     ecx, ecx
    xor     edx, edx                ; query_ptr = 0
.hhc_u_end:
    mov     al, [r15 + rcx]
    test    al, al
    jz      .hhc_u_done
    cmp     al, ' '
    je      .hhc_u_term
    cmp     al, 13
    je      .hhc_u_term
    cmp     al, 10
    je      .hhc_u_term
    cmp     al, '?'
    jne     .hhc_u_next
    mov     byte [r15 + rcx], 0
    lea     rdx, [r15 + rcx + 1]
    jmp     .hhc_u_scan_q
.hhc_u_next:
    inc     rcx
    jmp     .hhc_u_end
.hhc_u_scan_q:
    inc     rcx
    mov     al, [r15 + rcx]
    test    al, al
    jz      .hhc_u_done
    cmp     al, ' '
    je      .hhc_u_term
    cmp     al, 13
    je      .hhc_u_term
    cmp     al, 10
    je      .hhc_u_term
    jmp     .hhc_u_scan_q
.hhc_u_term:
    mov     byte [r15 + rcx], 0
.hhc_u_done:
    mov     [rsp + 72], rdx         ; query_ptr

    ; Check /openapi.json
    mov     rcx, r15
    lea     rdx, [szHttpOpenApi]
    call    _pyfasm_http_cstr_eq
    test    rax, rax
    jz      .hhc_match_routes
    mov     rcx, rbx
    call    _pyfasm_http_send_openapi
    jmp     .hhc_close

.hhc_match_routes:
    xor     esi, esi                ; route_idx
.hhc_route_loop:
    cmp     rsi, [_pyfasm_http_srv_route_cnt]
    jge     .hhc_send_404
    mov     rax, rsi
    shl     rax, 6
    lea     r12, [_pyfasm_http_routes + rax]
    mov     rcx, [r12]              ; route.method
    mov     rdx, r14                ; req.method
    call    _pyfasm_http_cstr_eq
    test    rax, rax
    jz      .hhc_route_next
    mov     rcx, [r12 + 8]          ; route.pattern
    mov     rdx, r15                ; req.path
    call    _pyfasm_http_match_path
    cmp     rax, 0
    jl      .hhc_route_next

    ; Matched route in r12! rax = path_param_cnt, [rsp+72] = query_ptr, r13 = body_ptr
    mov     [rsp + 80], rax         ; next_arg_slot
    mov     rcx, [r12 + 32]         ; total param_count
    mov     rdx, rax                ; fill remaining query/body params starting from path_param_cnt
.hhc_fill_extra_params:
    cmp     rdx, rcx
    jge     .hhc_conv_types
    cmp     rdx, 16
    jge     .hhc_conv_types
    mov     [rsp + 88], rcx
    mov     [rsp + 96], rdx
    mov     r8, [r12 + 48]          ; param_names_arr
    xor     eax, eax
    test    r8, r8
    jz      .hhc_try_body
    mov     r9, [r8 + rdx * 8]      ; param_name
    mov     rcx, [rsp + 72]         ; query_ptr
    mov     rdx, r9
    call    _pyfasm_http_find_query_param
    test    rax, rax
    jnz     .hhc_store_extra
.hhc_try_body:
    mov     rax, r13
    test    rax, rax
    jnz     .hhc_store_extra
    lea     rax, [szEmptyStr]
.hhc_store_extra:
    mov     rdx, [rsp + 96]
    mov     [_pyfasm_http_param_vals + rdx * 8], rax
    mov     rcx, [rsp + 88]
    inc     rdx
    jmp     .hhc_fill_extra_params

.hhc_conv_types:
    mov     r8, [r12 + 40]          ; param_int_mask
    xor     edx, edx
.hhc_conv_loop:
    cmp     rdx, [r12 + 32]
    jge     .hhc_call_handler
    cmp     rdx, 16
    jge     .hhc_call_handler
    bt      r8, rdx
    jnc     .hhc_conv_next
    mov     rcx, [_pyfasm_http_param_vals + rdx * 8]
    test    rcx, rcx
    jz      .hhc_conv_zero
    mov     [rsp + 96], rdx
    mov     [rsp + 104], r8
    call    _pyfasm_str_to_int
    mov     rdx, [rsp + 96]
    mov     r8, [rsp + 104]
    mov     [_pyfasm_http_param_vals + rdx * 8], rax
    jmp     .hhc_conv_next
.hhc_conv_zero:
    mov     qword [_pyfasm_http_param_vals + rdx * 8], 0
.hhc_conv_next:
    inc     rdx
    jmp     .hhc_conv_loop

.hhc_call_handler:
    mov     rax, [r12 + 16]         ; handler_ptr
    mov     rcx, [_pyfasm_http_param_vals]
    mov     rdx, [_pyfasm_http_param_vals + 8]
    mov     r8, [_pyfasm_http_param_vals + 16]
    mov     r9, [_pyfasm_http_param_vals + 24]
    mov     r10, [_pyfasm_http_param_vals + 32]
    mov     [rsp + 32], r10
    mov     r10, [_pyfasm_http_param_vals + 40]
    mov     [rsp + 40], r10
    call    rax

    ; Serialize response rax according to return_kind [r12 + 24]
    mov     r13, [r12 + 24]
    cmp     r13, 7                  ; html
    je      .hhc_raw_body
    cmp     r13, 8                  ; text
    je      .hhc_raw_body

    lea     rdi, [_pyfasm_http_json_buf]
    mov     rcx, rax
    mov     rdx, r13
    call    _pyfasm_json_write_auto
    mov     rdi, rax
    mov     byte [rdi], 0
    lea     r14, [_pyfasm_http_json_buf]
    sub     rdi, r14                ; body_len
    lea     r15, [szHttp200Json]
    jmp     .hhc_send_200

.hhc_raw_body:
    mov     r14, rax
    test    r14, r14
    jnz     .hhc_raw_len
    lea     r14, [szJsonNull]
.hhc_raw_len:
    xor     edi, edi
.hhc_raw_l:
    cmp     byte [r14 + rdi], 0
    je      .hhc_raw_hdr
    inc     rdi
    jmp     .hhc_raw_l
.hhc_raw_hdr:
    lea     r15, [szHttp200Html]
    cmp     r13, 7
    je      .hhc_send_200
    lea     r15, [szHttp200Text]

.hhc_send_200:
    ; r14 = body_ptr, rdi = body_len, r15 = header prefix
    mov     [rsp + 112], rdi
    lea     rdi, [_pyfasm_http_resp_hdr]
    mov     rcx, r15
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    mov     rcx, [rsp + 112]
    call    _pyfasm_int_to_str
    mov     rcx, rax
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    lea     rcx, [szHttpConnClose]
    call    _pyfasm_json_copy_cstr
    mov     rdi, rax
    lea     rdx, [_pyfasm_http_resp_hdr]
    mov     r8, rdi
    sub     r8, rdx
    mov     rcx, rbx
    call    _pyfasm_http_send_all

    mov     rcx, rbx
    mov     rdx, r14
    mov     r8, [rsp + 112]
    call    _pyfasm_http_send_all
    jmp     .hhc_close

.hhc_route_next:
    inc     rsi
    jmp     .hhc_route_loop

.hhc_send_404:
    mov     rcx, rbx
    lea     rdx, [szHttp404Resp]
    mov     r8d, 119                ; exact byte length of szHttp404Resp
    call    _pyfasm_http_send_all

.hhc_close:
    mov     rcx, rbx
    call    [closesocket]

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

_pyfasm_http_server_run:
    ; RCX = host_str (or 0 -> 127.0.0.1), RDX = port (default 8000)
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    rsi
    push    rdi
    sub     rsp, 48
    and     rsp, -16

    mov     rsi, rcx
    mov     rdi, rdx
    test    rdi, rdi
    jg      .hsr_port_ok
    mov     rdi, 8000
.hsr_port_ok:
    mov     ecx, 0202h              ; MAKEWORD(2, 2)
    lea     rdx, [_pyfasm_wsadata]
    call    [WSAStartup]
    test    eax, eax
    jnz     .hsr_exit

    mov     ecx, 2                  ; AF_INET
    mov     edx, 1                  ; SOCK_STREAM
    mov     r8d, 6                  ; IPPROTO_TCP
    call    [socket]
    cmp     rax, -1
    je      .hsr_cleanup
    mov     rbx, rax
    mov     [_pyfasm_http_listen_sock], rbx

    ; SO_REUSEADDR
    mov     dword [_pyfasm_sock_opt_one], 1
    mov     rcx, rbx
    mov     edx, 0FFFFh             ; SOL_SOCKET
    mov     r8d, 4                  ; SO_REUSEADDR
    lea     r9, [_pyfasm_sock_opt_one]
    mov     qword [rsp + 32], 4
    call    [setsockopt]

    ; Zero sockaddr_in (16 bytes)
    mov     qword [_pyfasm_sockaddr], 0
    mov     qword [_pyfasm_sockaddr + 8], 0
    mov     word [_pyfasm_sockaddr], 2 ; AF_INET
    mov     ecx, edi
    call    [htons]
    mov     word [_pyfasm_sockaddr + 2], ax

    mov     rcx, rsi
    test    rcx, rcx
    jnz     .hsr_host_given
    lea     rcx, [szDefHost]
.hsr_host_given:
    call    [inet_addr]
    cmp     eax, -1
    jne     .hsr_addr_ok
    xor     eax, eax                ; INADDR_ANY for 0.0.0.0 / localhost fallback
.hsr_addr_ok:
    mov     dword [_pyfasm_sockaddr + 4], eax

    mov     rcx, rbx
    lea     rdx, [_pyfasm_sockaddr]
    mov     r8d, 16
    call    [bind]
    test    eax, eax
    jnz     .hsr_close_sock

    mov     rcx, rbx
    mov     edx, 16
    call    [listen]
    test    eax, eax
    jnz     .hsr_close_sock

.hsr_accept_loop:
    mov     rcx, rbx
    xor     edx, edx
    xor     r8d, r8d
    call    [accept]
    cmp     rax, -1
    je      .hsr_close_sock
    mov     rcx, rax
    call    _pyfasm_http_handle_client
    jmp     .hsr_accept_loop

.hsr_close_sock:
    mov     rcx, rbx
    call    [closesocket]
.hsr_cleanup:
    call    [WSACleanup]
.hsr_exit:
    xor     eax, eax
    lea     rsp, [rbp - 24]
    pop     rdi
    pop     rsi
    pop     rbx
    mov     rsp, rbp
    pop     rbp
    ret
"""
