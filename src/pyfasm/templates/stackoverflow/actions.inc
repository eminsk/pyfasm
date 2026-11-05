; ==============================================================================
; Stack Overflow Search Pro (FASM x64) - Actions, Clipboard & Bookmarks
; Modular component: actions.inc
; ==============================================================================

; ------------------------------------------------------------------------------
; Clipboard Helper: Copy Question Details to Windows Clipboard
; ------------------------------------------------------------------------------
proc CopyQuestionToClipboard
        mov     rax, [selectedQIndex]
        cmp     rax, -1
        je      .done

        cmp     [isLiveMode], 1
        jne     .offline_copy

        imul    rax, sizeof.LIVE_QUESTION
        lea     rsi, [liveDb + rax]
        lea     rcx, [rsi + LIVE_QUESTION.szDetails]
        call    CopyToClipboardText
        invoke  SetWindowText, [hStatusBar], szStatusCopiedQ
        ret

.offline_copy:
        imul    rax, sizeof.QUESTION_ITEM
        lea     rsi, [qDatabase + rax]
        mov     rcx, [rsi + QUESTION_ITEM.pszDetails]
        call    CopyToClipboardText
        invoke  SetWindowText, [hStatusBar], szStatusCopiedQ
.done:
        ret
endp

; ------------------------------------------------------------------------------
; Clipboard Helper: Copy Solution Code / Link
; ------------------------------------------------------------------------------
proc CopyAnswerToClipboard
        ; 1. If we have an extracted code snippet for the current question, copy IT!
        cmp     [hasCodeSnippet], 1
        jne     .fallback_full_solution

        lea     rcx, [codeSnippetBuf]
        cmp     byte [rcx], 0
        je      .fallback_full_solution

        call    CopyToClipboardText
        invoke  SetWindowText, [hStatusBar], szStatusCodeCopied
        ret

.fallback_full_solution:
        ; 2. Fallback: Copy answer text or details
        mov     rax, [selectedQIndex]
        cmp     rax, -1
        je      .done

        cmp     [isLiveMode], 1
        jne     .offline_copy

        imul    rax, sizeof.LIVE_QUESTION
        lea     rsi, [liveDb + rax]
        lea     rcx, [rsi + LIVE_QUESTION.szDetails]
        call    CopyToClipboardText
        invoke  SetWindowText, [hStatusBar], szStatusCopiedA
        ret

.offline_copy:
        imul    rax, sizeof.QUESTION_ITEM
        lea     rsi, [qDatabase + rax]
        mov     rcx, [rsi + QUESTION_ITEM.pszDetails]
        call    CopyToClipboardText
        invoke  SetWindowText, [hStatusBar], szStatusCopiedA
.done:
        ret
endp

; ------------------------------------------------------------------------------
; Universal Clipboard Text Copy Function (rcx = string pointer)
; ------------------------------------------------------------------------------
proc CopyToClipboardText
        push    rbx rsi rdi
        mov     rsi, rcx
        test    rsi, rsi
        jz      .exit_clip

        ; Calculate string length
        xor     ecx, ecx
.count_len:
        cmp     byte [rsi + rcx], 0
        je      .len_done
        inc     rcx
        jmp     .count_len
.len_done:
        inc     rcx                     ; include null terminator
        mov     ebx, ecx

        ; Allocate global memory for clipboard data
        invoke  GlobalAlloc, GMEM_MOVEABLE, rbx
        test    rax, rax
        jz      .exit_clip
        mov     [hClipboardMem], rax

        invoke  GlobalLock, [hClipboardMem]
        test    rax, rax
        jz      .exit_clip
        mov     rdi, rax

        ; Copy string to locked memory
        mov     rcx, rbx
        rep     movsb

        invoke  GlobalUnlock, [hClipboardMem]

        ; Open clipboard and store data
        invoke  OpenClipboard, [hMainWnd]
        test    eax, eax
        jz      .exit_clip

        invoke  EmptyClipboard
        invoke  SetClipboardData, CF_TEXT, [hClipboardMem]
        invoke  CloseClipboard

.exit_clip:
        pop     rdi rsi rbx
        ret
endp

; ------------------------------------------------------------------------------
; Action: Open in Web Browser
; ------------------------------------------------------------------------------
proc OpenInBrowser
        mov     rax, [currentLinkPtr]
        test    rax, rax
        jz      .done
        invoke  ShellExecute, [hMainWnd], NULL, rax, NULL, NULL, 1
        invoke  SetWindowText, [hStatusBar], szStatusBrowserOpened
.done:
        ret
endp

; ------------------------------------------------------------------------------
; Action: Save Selected Question to bookmarks.txt
; ------------------------------------------------------------------------------
proc SaveBookmark
        mov     rax, [selectedQIndex]
        cmp     rax, -1
        je      .done

        ; Open or append to bookmarks.txt
        invoke  CreateFile, szBookmarkFile, 40000000h, 0, NULL, 4, 80h, NULL
        cmp     rax, -1
        je      .error
        mov     [hBmFile], rax

        invoke  SetFilePointer, [hBmFile], 0, NULL, 2 ; FILE_END

        ; Get details pointer
        cmp     [isLiveMode], 1
        jne     .off_bm

        mov     rax, [selectedQIndex]
        imul    rax, sizeof.LIVE_QUESTION
        lea     rsi, [liveDb + rax + LIVE_QUESTION.szDetails]
        jmp     .write_bm

.off_bm:
        mov     rax, [selectedQIndex]
        imul    rax, sizeof.QUESTION_ITEM
        mov     rsi, [qDatabase + rax + QUESTION_ITEM.pszDetails]

.write_bm:
        ; Calculate string length
        xor     edx, edx
.calc_bmlen:
        cmp     byte [rsi + rdx], 0
        je      .write_now
        inc     edx
        jmp     .calc_bmlen

.write_now:
        mov     [dwLength], edx
        invoke  WriteFile, [hBmFile], rsi, [dwLength], bytesWritten, NULL
        invoke  WriteFile, [hBmFile], szCRLF, 2, bytesWritten, NULL

        invoke  CloseHandle, [hBmFile]
        invoke  SetWindowText, [hStatusBar], szStatusSavedBm
        ret

.error:
        invoke  SetWindowText, [hStatusBar], szStatusBmErr
.done:
        ret
endp
