; ==============================================================================
; FASM Modern SDK - Native HTTPS / TLS REST Client (x86-64)
; File: include/net_https.inc
; High-performance HTTPS GET/POST client via WININET.DLL with TLS 1.3
; ==============================================================================

proc HttpsGet uses rbx rsi rdi r12, pUrl, pUserAgent, pOutBuf, maxBytes
        ; RCX = pUrl (e.g. "https://api.stackexchange.com/2.3/...")
        ; RDX = pUserAgent
        ; R8  = pOutBuf (allocated buffer for response)
        ; R9  = maxBytes (buffer size)
        ; Returns RAX = bytes read (0 on error)
        mov     rsi, rcx
        mov     rbx, rdx
        mov     rdi, r8
        mov     r12, r9

        test    rsi, rsi
        jz      .net_err
        test    rdi, rdi
        jz      .net_err

        ; 1. InternetOpen
        invoke  InternetOpen, rbx, 1, 0, 0, 0 ; INTERNET_OPEN_TYPE_DIRECT
        test    rax, rax
        jz      .net_err
        mov     rbx, rax                ; rbx = hInternet

        ; 2. InternetOpenUrl (HTTPS + Reload + NoCache)
        ; INTERNET_FLAG_RELOAD(0x80000000) | INTERNET_FLAG_SECURE(0x00800000) | INTERNET_FLAG_NO_CACHE_WRITE(0x04000000) = 0x84800000
        mov     rax, 84800000h
        invoke  InternetOpenUrl, rbx, rsi, 0, 0, rax, 0
        test    rax, rax
        jz      .close_internet
        mov     rsi, rax                ; rsi = hUrl

        ; 3. InternetReadFile
        sub     rsp, 16
        mov     qword [rsp], 0
        lea     r9, [rsp]               ; &bytesRead
        invoke  InternetReadFile, rsi, rdi, r12, r9
        mov     rax, [rsp]              ; bytes read
        add     rsp, 16

        ; Null-terminate response
        mov     byte [rdi + rax], 0
        push    rax                     ; save total bytes read

        ; Close handles
        invoke  InternetCloseHandle, rsi
        invoke  InternetCloseHandle, rbx

        pop     rax
        ret

.close_internet:
        invoke  InternetCloseHandle, rbx
.net_err:
        xor     eax, eax
        ret
endp
