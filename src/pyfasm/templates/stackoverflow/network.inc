; ==============================================================================
; Stack Overflow Search Pro (FASM x64) - Network Engine & HTML/JSON Formatter
; Modular component: network.inc
; ==============================================================================

; ------------------------------------------------------------------------------
; REAL LIVE API SEARCH via HTTPS (WININET.DLL)
; Connects to https://api.stackexchange.com/2.3/search/advanced
; Automatically switches between Stack Overflow and ru.stackoverflow
; Retrieves Questions with full body HTML (filter=withbody)
; ------------------------------------------------------------------------------
proc PerformLiveSearch uses rbx rsi rdi
        ; 1. Get search query string from edit box
        lea     rdx, [szSearchBuf]
        invoke  GetWindowText, [hEditSearch], rdx, 256

        ; If query is empty, do offline search directly without network lag
        lea     rsi, [szSearchBuf]
.check_empty_q:
        cmp     byte [rsi], ' '
        jne     @f
        inc     rsi
        jmp     .check_empty_q
@@:     cmp     byte [rsi], 0
        jne     .has_live_q
        call    ExecuteOfflineSearch
        ret

.has_live_q:
        ; 2. Build Request URL with proper UTF-8 percent-encoding
        lea     rdi, [apiUrlBuf]
        lea     rsi, [szApiBaseUrl]
        call    StrCopy

        ; Check active tab (0 = English, 1 = Russian)
        cmp     [currentTab], 1
        jne     .url_english

        ; Russian site
        lea     rsi, [szSiteRuParam]
        call    StrCat
        jmp     .url_query

.url_english:
        lea     rsi, [szSiteEnParam]
        call    StrCat

.url_query:
        lea     rsi, [szQueryPrefix]
        call    StrCat

        ; Convert szSearchBuf from ANSI to UTF-8
        invoke  MultiByteToWideChar, 0, 0, szSearchBuf, -1, wideTmp, 512
        invoke  WideCharToMultiByte, 65001, 0, wideTmp, -1, utf8Tmp, 1024, NULL, NULL

        ; Scan utf8Tmp and URL-encode into [rdi]
        lea     rsi, [utf8Tmp]
.url_enc_loop:
        lodsb
        test    al, al
        jz      .url_enc_done
        cmp     al, ' '
        jne     @f
        mov     al, '+'
        stosb
        jmp     .url_enc_loop
@@:     cmp     al, '0'
        jb      .url_percent
        cmp     al, '9'
        jbe     .url_pass
        cmp     al, 'A'
        jb      .url_percent
        cmp     al, 'Z'
        jbe     .url_pass
        cmp     al, 'a'
        jb      .url_percent
        cmp     al, 'z'
        jbe     .url_pass
        cmp     al, '-'
        je      .url_pass
        cmp     al, '_'
        je      .url_pass
        cmp     al, '.'
        je      .url_pass
.url_percent:
        mov     dl, al
        mov     al, '%'
        stosb
        mov     al, dl
        shr     al, 4
        call    HexDigit
        stosb
        mov     al, dl
        and     al, 0Fh
        call    HexDigit
        stosb
        jmp     .url_enc_loop
.url_pass:
        stosb
        jmp     .url_enc_loop
.url_enc_done:
        mov     byte [rdi], 0

        ; Append filter & pagesize (&pagesize=20&filter=withbody)
        lea     rsi, [szApiSuffix]
        call    StrCat

        ; 3. Update status to "Connecting..."
        invoke  SetWindowText, [hStatusBar], szStatusConnecting

        ; 4. WinINet HTTP GET Request
        invoke  InternetOpen, szUserAgent, 1, NULL, NULL, 0
        test    rax, rax
        jz      .fallback_offline
        mov     [hInternet], rax

        invoke  InternetOpenUrl, [hInternet], apiUrlBuf, NULL, 0, 84800000h, 0
        test    rax, rax
        jz      .net_error
        mov     [hUrl], rax

        ; Read response loop
        xor     ebx, ebx        ; totalBytes = 0

.read_chunk:
        lea     rax, [netBuffer + rbx]
        invoke  InternetReadFile, [hUrl], rax, 4096, addr bytesRead
        test    eax, eax
        jz      .read_done

        mov     eax, [bytesRead]
        test    eax, eax
        jz      .read_done

        add     ebx, eax
        cmp     ebx, 125000
        jge     .read_done
        jmp     .read_chunk

.read_done:
        mov     byte [netBuffer + rbx], 0

        ; Close WinINet handles
        invoke  InternetCloseHandle, [hUrl]
        invoke  InternetCloseHandle, [hInternet]

        cmp     ebx, 50
        jl      .fallback_offline

        ; 5. Parse Live Questions from JSON response
        call    ParseLiveJsonResponse
        ret

.net_error:
        invoke  InternetCloseHandle, [hInternet]

.fallback_offline:
        ; Fallback to Curated Offline Questions
        call    ExecuteOfflineSearch
        ret
endp

; ------------------------------------------------------------------------------
; Helper: Convert 4-bit nibble in AL to Hex ASCII Character ('0'-'9', 'A'-'F')
; ------------------------------------------------------------------------------
HexDigit:
        cmp     al, 10
        jb      @f
        add     al, 'A' - 10
        ret
@@:     add     al, '0'
        ret

; ------------------------------------------------------------------------------
; Fast JSON Parser for Stack Overflow API responses
; ------------------------------------------------------------------------------
proc ParseLiveJsonResponse uses rbx rsi rdi
        invoke  SendMessage, [hListQuestions], LB_RESETCONTENT, 0, 0
        mov     [matchCount], 0
        mov     [isLiveMode], 1

        ; Find "quota_remaining":
        lea     rsi, [netBuffer]
        lea     rdi, [szKeyQuota]
        call    FindSubStr
        test    rax, rax
        jz      @f
        add     rax, 18
        mov     rsi, rax
        call    ParseIntNumber
        mov     [quotaRemaining], eax

@@:     ; Locate start of items: "items":[
        lea     rsi, [netBuffer]
        lea     rdi, [szKeyItems]
        call    FindSubStr
        test    rax, rax
        jz      .no_results
        add     rax, 8
        mov     rsi, rax

        mov     [itemIdx], 0

.loop_items:
        cmp     [itemIdx], MAX_LIVE_ITEMS
        jge     .parse_done

        ; Skip whitespace, newlines, commas until '{' or ']'
.skip_ws_loop:
        lodsb
        test    al, al
        jz      .parse_done
        cmp     al, ']'
        je      .parse_done
        cmp     al, '{'
        je      .found_item_start
        jmp     .skip_ws_loop

.found_item_start:
        dec     rsi                     ; rsi points at '{'
        mov     [pItemStart], rsi
        inc     rsi                     ; past '{'

        ; Scan forward with depth counter to find matching closing '}'
        mov     ebx, 1                  ; depth = 1
        xor     edx, edx                ; in_str flag (0 = false, 1 = true)

.scan_depth_loop:
        lodsb
        test    al, al
        jz      .found_item_end
        test    edx, edx
        jnz     .in_str_mode

        ; Not in string
        cmp     al, '"'
        jne     @f
        mov     edx, 1                  ; enter string mode
        jmp     .scan_depth_loop
@@:     cmp     al, '{'
        jne     @f
        inc     ebx                     ; depth++
        jmp     .scan_depth_loop
@@:     cmp     al, '}'
        jne     .scan_depth_loop
        dec     ebx                     ; depth--
        jz      .found_item_end         ; depth == 0 -> matching end of item!
        jmp     .scan_depth_loop

.in_str_mode:
        cmp     al, '\'
        jne     @f
        lodsb                           ; skip escaped char after backslash
        jmp     .scan_depth_loop
@@:     cmp     al, '"'
        jne     .scan_depth_loop
        xor     edx, edx                ; exit string mode
        jmp     .scan_depth_loop

.found_item_end:
        ; Null-terminate this individual item object temporarily
        mov     [pItemEnd], rsi
        mov     al, [rsi]
        mov     [savedChar], al
        mov     byte [rsi], 0

        ; Calculate pointer to current liveQuestion struct
        mov     eax, [itemIdx]
        imul    rax, sizeof.LIVE_QUESTION
        lea     rbx, [liveDb + rax]
        mov     [pItem], rbx
        mov     dword [rbx + LIVE_QUESTION.bAnsLoaded], 0

        ; 1. Question ID
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyQId]
        call    FindSubStr
        test    rax, rax
        jz      .no_qid
        add     rax, 14
        mov     rsi, rax
        call    ParseIntNumber
        mov     rbx, [pItem]
        mov     [rbx + LIVE_QUESTION.dwId], eax
        jmp     .chk_score
.no_qid:
        mov     rbx, [pItem]
        mov     dword [rbx + LIVE_QUESTION.dwId], 0

.chk_score:
        ; 2. Score
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyScore]
        call    FindSubStr
        test    rax, rax
        jz      .no_score
        add     rax, 8
        mov     rsi, rax
        call    ParseIntNumber
        mov     rbx, [pItem]
        mov     [rbx + LIVE_QUESTION.dwScore], eax
        jmp     .chk_ans
.no_score:
        mov     rbx, [pItem]
        mov     dword [rbx + LIVE_QUESTION.dwScore], 0

.chk_ans:
        ; 3. Answers
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyAnswers]
        call    FindSubStr
        test    rax, rax
        jz      .no_ans
        add     rax, 15
        mov     rsi, rax
        call    ParseIntNumber
        mov     rbx, [pItem]
        mov     [rbx + LIVE_QUESTION.dwAnswers], eax
        jmp     .chk_views
.no_ans:
        mov     rbx, [pItem]
        mov     dword [rbx + LIVE_QUESTION.dwAnswers], 0

.chk_views:
        ; 4. Views
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyViews]
        call    FindSubStr
        test    rax, rax
        jz      .no_views
        add     rax, 13
        mov     rsi, rax
        call    ParseIntNumber
        mov     rbx, [pItem]
        mov     [rbx + LIVE_QUESTION.dwViews], eax
        jmp     .chk_answered
.no_views:
        mov     rbx, [pItem]
        mov     dword [rbx + LIVE_QUESTION.dwViews], 0

.chk_answered:
        ; 5. is_answered
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyAnswered]
        call    FindSubStr
        test    rax, rax
        jz      .no_answered
        add     rax, 14
        cmp     byte [rax], 't'
        sete    al
        movzx   eax, al
        mov     rbx, [pItem]
        mov     [rbx + LIVE_QUESTION.bAnswered], eax
        jmp     .chk_author
.no_answered:
        mov     rbx, [pItem]
        mov     dword [rbx + LIVE_QUESTION.bAnswered], 0

.chk_author:
        ; 6. Author
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyAuthor]
        call    FindSubStr
        test    rax, rax
        jz      .no_author
        add     rax, 16
        mov     rsi, rax
        lea     rdi, [utf8Tmp]
        xor     ecx, ecx
.a_loop:
        lodsb
        cmp     al, '"'
        je      .a_end
        test    al, al
        jz      .a_end
        cmp     ecx, 100
        jge     .a_loop
        stosb
        inc     ecx
        jmp     .a_loop
.a_end:
        mov     byte [rdi], 0
        invoke  MultiByteToWideChar, 65001, 0, utf8Tmp, -1, wideTmp, 512
        mov     rbx, [pItem]
        lea     rax, [rbx + LIVE_QUESTION.szAuthor]
        invoke  WideCharToMultiByte, 0, 0, wideTmp, -1, rax, 120, NULL, NULL
        mov     rbx, [pItem]
        cmp     byte [rbx + LIVE_QUESTION.szAuthor], 0
        jne     .chk_link
.no_author:
        mov     rbx, [pItem]
        lea     rdi, [rbx + LIVE_QUESTION.szAuthor]
        lea     rsi, [szAuthorCommunity]
        call    StrCopy

.chk_link:
        ; 7. Link
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyLink]
        call    FindSubStr
        test    rax, rax
        jz      .no_link
        add     rax, 8
        mov     rsi, rax
        mov     rbx, [pItem]
        lea     rdi, [rbx + LIVE_QUESTION.szLink]
        xor     ecx, ecx
.l_loop:
        lodsb
        cmp     al, '"'
        je      .l_end
        test    al, al
        jz      .l_end
        cmp     ecx, 800
        jge     .l_loop
        stosb
        inc     ecx
        jmp     .l_loop
.l_end:
        mov     byte [rdi], 0
        jmp     .chk_title
.no_link:
        mov     rbx, [pItem]
        mov     byte [rbx + LIVE_QUESTION.szLink], 0

.chk_title:
        ; 8. Title
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyTitle]
        call    FindSubStr
        test    rax, rax
        jz      .no_title
        add     rax, 9
        mov     rsi, rax
        lea     rdi, [utf8Tmp]
        xor     ecx, ecx
.t_loop:
        lodsb
        cmp     al, '"'
        je      .t_end
        test    al, al
        jz      .t_end
        cmp     ecx, 500
        jge     .t_loop
        stosb
        inc     ecx
        jmp     .t_loop
.t_end:
        mov     byte [rdi], 0
        lea     rsi, [utf8Tmp]
        call    DecodeHtmlEntities
        invoke  MultiByteToWideChar, 65001, 0, utf8Tmp, -1, wideTmp, 512
        mov     rbx, [pItem]
        lea     rax, [rbx + LIVE_QUESTION.szTitle]
        invoke  WideCharToMultiByte, 0, 0, wideTmp, -1, rax, 500, NULL, NULL
        jmp     .chk_body
.no_title:
        mov     rbx, [pItem]
        mov     byte [rbx + LIVE_QUESTION.szTitle], 0

.chk_body:
        ; 9. Body HTML
        mov     rsi, [pItemStart]
        lea     rdi, [szKeyBody]
        call    FindSubStr
        test    rax, rax
        jz      .no_body
        add     rax, 8
        mov     rsi, rax
        lea     rdi, [utf8Tmp]
        xor     ecx, ecx
.b_loop:
        lodsb
        cmp     al, '"'
        jne     @f
        cmp     byte [rsi - 2], '\'
        je      @f
        jmp     .b_end
@@:     test    al, al
        jz      .b_end
        cmp     ecx, 28000
        jge     .b_loop
        stosb
        inc     ecx
        jmp     .b_loop
.b_end:
        mov     byte [rdi], 0
        invoke  MultiByteToWideChar, 65001, 0, utf8Tmp, -1, wideTmp, 16384
        invoke  WideCharToMultiByte, 0, 0, wideTmp, -1, bodyTmp, 32000, NULL, NULL

        ; Convert HTML to styled terminal containers in ansTmp
        lea     rsi, [bodyTmp]
        lea     rdi, [ansTmp]
        call    FormatHtmlToDetails
        jmp     .build_item

.no_body:
        lea     rdi, [ansTmp]
        lea     rsi, [szLiveDetailBody]
        call    StrCopy

.build_item:
        mov     rbx, [pItem]

        ; Format listbox display entry:
        ; "▲ {score} | {answers} ans | {title}"
        lea     rdi, [itemDisplayBuf]
        lea     rsi, [szScorePrefix]
        call    StrCopy

        mov     eax, [rbx + LIVE_QUESTION.dwScore]
        call    AppendNumber

        lea     rsi, [szAnsMidPrefix]
        call    StrCat

        cmp     [rbx + LIVE_QUESTION.bAnswered], 1
        jne     @f
        lea     rsi, [szSolvedBadge]
        call    StrCat

@@:     mov     eax, [rbx + LIVE_QUESTION.dwAnswers]
        call    AppendNumber

        lea     rsi, [szAnsSuffix]
        call    StrCat

        lea     rsi, [rbx + LIVE_QUESTION.szTitle]
        call    StrCat

        ; Add to listbox
        lea     rax, [itemDisplayBuf]
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, rax
        mov     rdi, rax

        mov     eax, [itemIdx]
        invoke  SendMessage, [hListQuestions], LB_SETITEMDATA, rdi, rax

        ; Format full details text
        mov     rbx, [pItem]
        lea     rdi, [rbx + LIVE_QUESTION.szDetails]
        lea     rsi, [szDividerLine]
        call    StrCopy

        lea     rsi, [rbx + LIVE_QUESTION.szTitle]
        call    StrCat

        lea     rsi, [szCRLF]
        call    StrCat

        lea     rsi, [szDividerLine]
        call    StrCat

        lea     rsi, [szScorePrefix]
        call    StrCat
        mov     eax, [rbx + LIVE_QUESTION.dwScore]
        call    AppendNumber

        lea     rsi, [szMetaAnswers]
        call    StrCat
        mov     eax, [rbx + LIVE_QUESTION.dwAnswers]
        call    AppendNumber

        lea     rsi, [szMetaViews]
        call    StrCat
        mov     eax, [rbx + LIVE_QUESTION.dwViews]
        call    AppendNumber

        lea     rsi, [szMetaAuthor]
        call    StrCat
        lea     rsi, [rbx + LIVE_QUESTION.szAuthor]
        call    StrCat

        lea     rsi, [szCRLF]
        call    StrCat

        lea     rsi, [szMetaUrl]
        call    StrCat
        lea     rsi, [rbx + LIVE_QUESTION.szLink]
        call    StrCat

        lea     rsi, [szCRLF]
        call    StrCat
        lea     rsi, [szThinDivider]
        call    StrCat

        lea     rsi, [szSectionQuestion]
        call    StrCat

        lea     rsi, [ansTmp]
        call    StrCat

        inc     [matchCount]
        inc     [itemIdx]

        ; Restore temporarily nulled character at pItemEnd and advance
        mov     rsi, [pItemEnd]
        mov     al, [savedChar]
        mov     [rsi], al
        jmp     .loop_items

.parse_done:
        cmp     [matchCount], 0
        jle     .no_results

        ; Select first item
        invoke  SendMessage, [hListQuestions], LB_SETCURSEL, 0, 0
        call    OnQuestionSelected

        ; Update Status Bar with count and quota
        call    UpdateStatusCount
        ret

.no_results:
        invoke  SetWindowText, [hEditDetails], szNoMatchesDetails
        invoke  SetWindowText, [hStatusBar], szStatusNoMatches
        ret
endp

; ------------------------------------------------------------------------------
; Live Answer Fetcher & Appender for Selected Question
; ------------------------------------------------------------------------------
proc FetchLiveAnswer uses rbx rsi rdi r12
        local   qid:QWORD
        local   pDest:QWORD

        mov     [qid], rcx
        mov     [pDest], rdx

        ; Build Answer URL:
        ; https://api.stackexchange.com/2.3/questions/{qid}/answers?site=...&filter=withbody&order=desc&sort=votes&pagesize=1
        lea     rdi, [apiUrlBuf]
        lea     rsi, [szApiAnsBase]
        call    StrCopy

        mov     rax, [qid]
        call    AppendNumber

        lea     rsi, [szApiAnsPath]
        call    StrCat

        cmp     [currentTab], 1
        jne     .ans_en
        lea     rsi, [szSiteRuOnly]
        call    StrCat
        jmp     .ans_filter
.ans_en:
        lea     rsi, [szSiteEnOnly]
        call    StrCat
.ans_filter:
        lea     rsi, [szApiAnsFilter]
        call    StrCat

        ; WinINet Request
        invoke  InternetOpen, szUserAgent, 1, NULL, NULL, 0
        test    rax, rax
        jz      .exit_err
        mov     [hInternet], rax

        invoke  InternetOpenUrl, [hInternet], apiUrlBuf, NULL, 0, 84800000h, 0
        test    rax, rax
        jz      .net_err
        mov     [hUrl], rax

        xor     ebx, ebx
.read_ans:
        lea     rax, [ansNetBuf + rbx]
        invoke  InternetReadFile, [hUrl], rax, 4096, addr bytesRead
        test    eax, eax
        jz      .read_done
        mov     eax, [bytesRead]
        test    eax, eax
        jz      .read_done
        add     ebx, eax
        cmp     ebx, 60000
        jge     .read_done
        jmp     .read_ans

.read_done:
        mov     byte [ansNetBuf + rbx], 0
        invoke  InternetCloseHandle, [hUrl]
        invoke  InternetCloseHandle, [hInternet]

        cmp     ebx, 30
        jl      .exit_err

        ; Locate "items":[
        lea     rsi, [ansNetBuf]
        lea     rdi, [szKeyItems]
        call    FindSubStr
        test    rax, rax
        jz      .no_ans_items
        add     rax, 8
        mov     rsi, rax

        ; Check if items array is empty "[]"
        cmp     byte [rsi], ']'
        je      .no_ans_items

        ; Extract answer author
        lea     rdi, [szKeyAuthor]
        call    FindSubStr
        test    rax, rax
        jz      .default_ans_author
        add     rax, 16
        mov     rsi, rax
        lea     rdi, [utf8Tmp]
        xor     ecx, ecx
.ans_a_loop:
        lodsb
        cmp     al, '"'
        je      .ans_a_end
        test    al, al
        jz      .ans_a_end
        cmp     ecx, 100
        jge     .ans_a_loop
        stosb
        inc     ecx
        jmp     .ans_a_loop
.ans_a_end:
        mov     byte [rdi], 0
        invoke  MultiByteToWideChar, 65001, 0, utf8Tmp, -1, wideTmp, 512
        lea     rax, [ansAuthorBuf]
        invoke  WideCharToMultiByte, 0, 0, wideTmp, -1, rax, 120, NULL, NULL
        jmp     .have_ans_author
.default_ans_author:
        lea     rdi, [ansAuthorBuf]
        lea     rsi, [szAuthorCommunity]
        call    StrCopy

.have_ans_author:
        ; Extract answer score
        lea     rsi, [ansNetBuf]
        lea     rdi, [szKeyScore]
        call    FindSubStr
        test    rax, rax
        jz      .zero_ans_score
        add     rax, 8
        mov     rsi, rax
        call    ParseIntNumber
        mov     [currScore], eax
        jmp     .check_accepted
.zero_ans_score:
        mov     [currScore], 0

.check_accepted:
        ; Extract is_accepted
        lea     rsi, [ansNetBuf]
        lea     rdi, [szKeyIsAccepted]
        call    FindSubStr
        xor     ebx, ebx
        test    rax, rax
        jz      .not_acc
        add     rax, 14
        cmp     byte [rax], 't'
        jne     .not_acc
        mov     ebx, 1
.not_acc:

        ; Extract answer body: "body":"
        lea     rsi, [ansNetBuf]
        lea     rdi, [szKeyBody]
        call    FindSubStr
        test    rax, rax
        jz      .no_ans_body
        add     rax, 8
        mov     rsi, rax

        ; Convert UTF-8 answer HTML into ANSI in bodyTmp
        lea     rdi, [utf8Tmp]
        xor     ecx, ecx
.ans_b_loop:
        lodsb
        cmp     al, '"'
        jne     @f
        cmp     byte [rsi - 2], '\'
        je      @f
        jmp     .ans_b_end
@@:     test    al, al
        jz      .ans_b_end
        cmp     ecx, 15000
        jge     .ans_b_loop
        stosb
        inc     ecx
        jmp     .ans_b_loop
.ans_b_end:
        mov     byte [rdi], 0

        invoke  MultiByteToWideChar, 65001, 0, utf8Tmp, -1, wideTmp, 16384
        invoke  WideCharToMultiByte, 0, 0, wideTmp, -1, bodyTmp, 32000, NULL, NULL

        ; Format answer HTML to styled text in ansTmp
        lea     rsi, [bodyTmp]
        lea     rdi, [ansTmp]
        call    FormatHtmlToDetails

        ; Append Answers Section to pDest
        mov     rdi, [pDest]
@@:     cmp     byte [rdi], 0
        je      @f
        inc     rdi
        jmp     @b
@@:     lea     rsi, [szSectionAnswers]
        call    StrCatRdi

        ; If accepted, append accepted banner
        test    ebx, ebx
        jz      .no_acc_banner
        lea     rsi, [szAcceptedBanner]
        call    StrCatRdi
.no_acc_banner:
        ; Append Answer Header
        lea     rsi, [szAnsHdrP1]
        call    StrCatRdi
        mov     eax, [currScore]
        call    AppendNumberRdi
        lea     rsi, [szAnsHdrP2]
        call    StrCatRdi
        lea     rsi, [ansAuthorBuf]
        call    StrCatRdi
        lea     rsi, [szAnsHdrP3]
        call    StrCatRdi

        ; Append formatted answer body
        lea     rsi, [ansTmp]
        call    StrCatRdi

        ; Append actions help
        lea     rsi, [szActionsHelp]
        call    StrCatRdi
        ret

.no_ans_body:
.no_ans_items:
        ret
.net_err:
        invoke  InternetCloseHandle, [hInternet]
.exit_err:
        ret
endp

; ------------------------------------------------------------------------------
; Convert Stack Overflow HTML into Styled ASCII Terminal Containers
; Handles <pre><code>...</code></pre>, <code>, <p>, <br>, <li>, and HTML entities
; ------------------------------------------------------------------------------
FormatHtmlToDetails:
        push    rbx rcx rdx rsi rdi
        mov     [inCodeBlock], 0

.loop:
        lodsb
        test    al, al
        jz      .done

        ; Check escape sequences from JSON: \" or \n
        cmp     al, '\'
        jne     .check_tag
        mov     al, [rsi]
        cmp     al, '"'
        jne     @f
        inc     rsi
        mov     al, '"'
        stosb
        jmp     .loop
@@:     cmp     al, 'n'
        jne     @f
        inc     rsi
        cmp     [inCodeBlock], 1
        jne     .json_nl_norm
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        mov     al, '|'
        stosb
        mov     al, ' '
        stosb
        jmp     .loop
.json_nl_norm:
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        jmp     .loop
@@:     cmp     al, 'r'
        jne     .put_char
        inc     rsi
        jmp     .loop

.check_tag:
        cmp     al, '<'
        jne     .check_entity

        ; Check <pre><code>
        cmp     dword [rsi], 'pre>'
        jne     .chk_end_pre
        cmp     dword [rsi + 4], '<cod'
        jne     .chk_end_pre
        cmp     word [rsi + 8], 'e>'
        jne     .chk_end_pre
        add     rsi, 10
        mov     [inCodeBlock], 1

        push    rsi
        lea     rsi, [szCodeBoxTop]
        call    StrCatRdi
        pop     rsi
        jmp     .loop

.chk_end_pre:
        ; Check </code></pre>
        cmp     dword [rsi], '/cod'
        jne     .chk_code_inline
        cmp     dword [rsi + 4], 'e></'
        jne     .chk_code_inline
        cmp     dword [rsi + 8], 'pre>'
        jne     .chk_code_inline
        add     rsi, 12
        mov     [inCodeBlock], 0

        push    rsi
        lea     rsi, [szCodeBoxBottom]
        call    StrCatRdi
        pop     rsi
        jmp     .loop

.chk_code_inline:
        ; Check <code> (inline code)
        cmp     dword [rsi], 'code'
        jne     .chk_end_code
        cmp     byte [rsi + 4], '>'
        jne     .chk_end_code
        add     rsi, 5
        mov     al, '['
        stosb
        jmp     .loop

.chk_end_code:
        ; Check </code>
        cmp     dword [rsi], '/cod'
        jne     .chk_br
        cmp     word [rsi + 4], 'e>'
        jne     .chk_br
        add     rsi, 6
        mov     al, ']'
        stosb
        jmp     .loop

.chk_br:
        cmp     word [rsi], 'br'
        jne     .chk_p
.skip_br:
        lodsb
        cmp     al, '>'
        jne     .skip_br
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        jmp     .loop

.chk_p:
        cmp     byte [rsi], 'p'
        je      .emit_p
        cmp     word [rsi], '/p'
        je      .emit_p
        jmp     .chk_li
.emit_p:
        lodsb
        cmp     al, '>'
        jne     .emit_p
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        jmp     .loop

.chk_li:
        cmp     word [rsi], 'li'
        jne     .skip_generic_tag
        add     rsi, 3
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        mov     al, ' '
        stosb
        mov     al, ' '
        stosb
        mov     al, '*'
        stosb
        mov     al, ' '
        stosb
        jmp     .loop

.skip_generic_tag:
.skip_tag_loop:
        lodsb
        test    al, al
        jz      .done
        cmp     al, '>'
        jne     .skip_tag_loop
        jmp     .loop

.check_entity:
        cmp     al, '&'
        jne     .check_newline

        ; Check &quot;
        cmp     dword [rsi], 'quot'
        jne     .chk_apos_ent
        cmp     byte [rsi + 4], ';'
        jne     .put_char
        add     rsi, 5
        mov     al, '"'
        stosb
        jmp     .loop

.chk_apos_ent:
        ; Check &#39;
        cmp     dword [rsi], '#39;'
        jne     .chk_amp_ent
        add     rsi, 4
        mov     al, "'"
        stosb
        jmp     .loop

.chk_amp_ent:
        ; Check &amp;
        cmp     dword [rsi], 'amp;'
        jne     .chk_lt_ent
        add     rsi, 4
        mov     al, '&'
        stosb
        jmp     .loop

.chk_lt_ent:
        ; Check &lt;
        cmp     word [rsi], 'lt'
        jne     .chk_gt_ent
        cmp     byte [rsi + 2], ';'
        jne     .chk_gt_ent
        add     rsi, 3
        mov     al, '<'
        stosb
        jmp     .loop

.chk_gt_ent:
        ; Check &gt;
        cmp     word [rsi], 'gt'
        jne     .put_char
        cmp     byte [rsi + 2], ';'
        jne     .put_char
        add     rsi, 3
        mov     al, '>'
        stosb
        jmp     .loop

.check_newline:
        cmp     al, 10
        jne     .put_char
        cmp     [inCodeBlock], 1
        jne     .norm_nl
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        mov     al, '|'
        stosb
        mov     al, ' '
        stosb
        jmp     .loop
.norm_nl:
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        jmp     .loop

.put_char:
        stosb
        jmp     .loop

.done:
        mov     byte [rdi], 0
        pop     rdi rsi rdx rcx rbx
        ret

; ------------------------------------------------------------------------------
; JSON Helper: Find Substring (rsi = haystack, rdi = needle), returns rax = ptr
; ------------------------------------------------------------------------------
FindSubStr:
        push    rbx rdx
        mov     rax, rsi
.outer:
        cmp     byte [rax], 0
        je      .not_found
        mov     rbx, rax
        mov     rdx, rdi
.inner:
        mov     cl, [rdx]
        test    cl, cl
        jz      .found
        cmp     cl, [rbx]
        jne     .next_char
        inc     rbx
        inc     rdx
        jmp     .inner
.next_char:
        inc     rax
        jmp     .outer
.found:
        pop     rdx rbx
        ret
.not_found:
        xor     rax, rax
        pop     rdx rbx
        ret

; ------------------------------------------------------------------------------
; Case-Insensitive Substring Search (rsi = haystack, rdi = needle)
; Supports English ASCII and Russian CP1251!
; Returns: rax = match pointer, or 0 if not found
; ------------------------------------------------------------------------------
FindSubStrI:
        push    rbx rdx r8 r9
        mov     rax, rsi
.outer:
        cmp     byte [rax], 0
        je      .not_found
        mov     rbx, rax
        mov     rdx, rdi
.inner:
        movzx   r8d, byte [rdx]
        test    r8b, r8b
        jz      .found
        movzx   r9d, byte [rbx]
        test    r9b, r9b
        jz      .not_found

        cmp     r8b, 'A'
        jb      @f
        cmp     r8b, 'Z'
        jbe     .fold_r8
@@:     cmp     r8b, 0C0h
        jb      @f
        cmp     r8b, 0DFh
        jbe     .fold_r8
@@:     cmp     r8b, 0A8h
        jne     .check_r9
        mov     r8b, 0B8h
        jmp     .check_r9
.fold_r8:
        add     r8b, 20h

.check_r9:
        cmp     r9b, 'A'
        jb      @f
        cmp     r9b, 'Z'
        jbe     .fold_r9
@@:     cmp     r9b, 0C0h
        jb      @f
        cmp     r9b, 0DFh
        jbe     .fold_r9
@@:     cmp     r9b, 0A8h
        jne     .compare
        mov     r9b, 0B8h
        jmp     .compare
.fold_r9:
        add     r9b, 20h

.compare:
        cmp     r8b, r9b
        jne     .next_char
        inc     rbx
        inc     rdx
        jmp     .inner

.next_char:
        inc     rax
        jmp     .outer

.found:
        pop     r9 r8 rdx rbx
        ret

.not_found:
        xor     rax, rax
        pop     r9 r8 rdx rbx
        ret

; ------------------------------------------------------------------------------
; JSON Helper: Parse Integer Number from rsi into eax (supports negative numbers)
; ------------------------------------------------------------------------------
ParseIntNumber:
        push    rbx
        xor     eax, eax
        xor     ebx, ebx
.skip_ws:
        cmp     byte [rsi], ' '
        jne     .chk_neg
        inc     rsi
        jmp     .skip_ws
.chk_neg:
        cmp     byte [rsi], '-'
        jne     .read_digits
        mov     ebx, 1
        inc     rsi
.read_digits:
        movzx   edx, byte [rsi]
        cmp     dl, '0'
        jb      .done_digits
        cmp     dl, '9'
        ja      .done_digits
        sub     dl, '0'
        imul    eax, 10
        add     eax, edx
        inc     rsi
        jmp     .read_digits
.done_digits:
        test    ebx, ebx
        jz      .num_ret
        neg     eax
.num_ret:
        pop     rbx
        ret

; ------------------------------------------------------------------------------
; Decode HTML entities
; ------------------------------------------------------------------------------
DecodeHtmlEntities:
        push    rsi rdi rax
        mov     rdi, rsi
.scan:
        lodsb
        test    al, al
        jz      .done
        cmp     al, '&'
        jne     .put

        cmp     dword [rsi], 'quot'
        jne     .chk_apos
        cmp     byte [rsi + 4], ';'
        jne     .put
        add     rsi, 5
        mov     al, '"'
        jmp     .put

.chk_apos:
        cmp     dword [rsi], 'apos'
        jne     .chk_39
        cmp     byte [rsi + 4], ';'
        jne     .put
        add     rsi, 5
        mov     al, "'"
        jmp     .put

.chk_39:
        cmp     dword [rsi], '#39;'
        jne     .chk_amp
        add     rsi, 4
        mov     al, "'"
        jmp     .put

.chk_amp:
        cmp     dword [rsi], 'amp;'
        jne     .chk_lt
        add     rsi, 4
        mov     al, '&'
        jmp     .put

.chk_lt:
        cmp     word [rsi], 'lt'
        jne     .chk_gt
        cmp     byte [rsi + 2], ';'
        jne     .chk_gt
        add     rsi, 3
        mov     al, '<'
        jmp     .put

.chk_gt:
        cmp     word [rsi], 'gt'
        jne     .put
        cmp     byte [rsi + 2], ';'
        jne     .put
        add     rsi, 3
        mov     al, '>'

.put:
        stosb
        jmp     .scan
.done:
        stosb
        pop     rax rdi rsi
        ret

; ------------------------------------------------------------------------------
; String Utilities
; ------------------------------------------------------------------------------
StrCopy:
        push    rax
.loop:  lodsb
        stosb
        test    al, al
        jnz     .loop
        dec     rdi
        pop     rax
        ret

StrCat:
        push    rax
.find_end:
        cmp     byte [rdi], 0
        je      .copy
        inc     rdi
        jmp     .find_end
.copy:  lodsb
        stosb
        test    al, al
        jnz     .copy
        dec     rdi
        pop     rax
        ret

StrCatRdi:
        push    rax
.loop:  lodsb
        stosb
        test    al, al
        jnz     .loop
        dec     rdi
        pop     rax
        ret

AppendNumber:
        push    rax rbx rcx rdx rsi rdi
        lea     rdi, [numBuf]
        mov     ebx, 10
        xor     ecx, ecx

        test    eax, eax
        jns     .loop_div
        mov     byte [rdi], '-'
        inc     rdi
        neg     eax

.loop_div:
        xor     edx, edx
        div     ebx
        push    rdx
        inc     ecx
        test    eax, eax
        jnz     .loop_div
.loop_pop:
        pop     rdx
        add     dl, '0'
        mov     [rdi], dl
        inc     rdi
        loop    .loop_pop
        mov     byte [rdi], 0
        pop     rdi rsi rdx rcx rbx rax

        push    rsi
        lea     rsi, [numBuf]
        call    StrCat
        pop     rsi
        ret

AppendNumberRdi:
        push    rax rbx rcx rdx rsi
        push    rdi
        lea     rdi, [numBuf]
        mov     ebx, 10
        xor     ecx, ecx

        test    eax, eax
        jns     .loop_div
        mov     byte [rdi], '-'
        inc     rdi
        neg     eax

.loop_div:
        xor     edx, edx
        div     ebx
        push    rdx
        inc     ecx
        test    eax, eax
        jnz     .loop_div
.loop_pop:
        pop     rdx
        add     dl, '0'
        mov     [rdi], dl
        inc     rdi
        loop    .loop_pop
        mov     byte [rdi], 0

        pop     rdi
        push    rsi
        lea     rsi, [numBuf]
        call    StrCatRdi
        pop     rsi
        pop     rsi rdx rcx rbx rax
        ret
