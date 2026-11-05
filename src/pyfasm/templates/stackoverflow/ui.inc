; ==============================================================================
; Stack Overflow Search Pro (FASM x64) - UI, Controls & Rendering Engine
; Modular component: ui.inc
; ==============================================================================

; ------------------------------------------------------------------------------
; Main Window Procedure
; ------------------------------------------------------------------------------
proc WindowProc uses rbx rsi rdi, hwnd, wmsg, wparam, lparam
        mov     [hwnd], rcx
        mov     [wparam], r8
        mov     [lparam], r9

        cmp     edx, WM_CREATE
        je      .wm_create
        cmp     edx, WM_PAINT
        je      .wm_paint
        cmp     edx, 0014h              ; WM_ERASEBKGND
        je      .wm_erasebkgnd
        cmp     edx, 002Ch              ; WM_MEASUREITEM
        je      .wm_measureitem
        cmp     edx, WM_DRAWITEM
        je      .wm_drawitem
        cmp     edx, WM_COMMAND
        je      .wm_command
        cmp     edx, WM_SIZE
        je      .wm_size
        cmp     edx, WM_CTLCOLORSTATIC
        je      .wm_ctl_static
        cmp     edx, WM_CTLCOLOREDIT
        je      .wm_ctl_edit
        cmp     edx, WM_CTLCOLORLISTBOX
        je      .wm_ctl_list
        cmp     edx, WM_DESTROY
        je      .wm_destroy

.defwndproc:
        invoke  DefWindowProc, rcx, rdx, r8, r9
        jmp     .finish

.wm_paint:
        lea     rdx, [psPaint]
        invoke  BeginPaint, [hwnd], rdx
        mov     rbx, rax                ; HDC
        lea     rdx, [rcClient]
        invoke  GetClientRect, [hwnd], rdx
        lea     rdx, [rcClient]
        invoke  FillRect, rbx, rdx, [hBrushWin]
        lea     rdx, [psPaint]
        invoke  EndPaint, [hwnd], rdx
        xor     eax, eax
        jmp     .finish

.wm_measureitem:
        mov     rax, [lparam]
        mov     dword [rax + 16], 78    ; itemHeight = 78 pixels!
        mov     eax, 1
        jmp     .finish

.wm_erasebkgnd:
        mov     rbx, r8                 ; Save HDC safely in rbx
        lea     rdx, [rcClient]
        invoke  GetClientRect, [hwnd], rdx
        lea     rdx, [rcClient]
        invoke  FillRect, rbx, rdx, [hBrushWin]
        mov     eax, 1
        jmp     .finish

.wm_create:
        mov     [hMainWnd], rcx
        mov     [currentTab], 1
        call    CreateAppControls
        call    ExecuteOfflineSearch
        xor     eax, eax
        jmp     .finish

.wm_drawitem:
        mov     rcx, [lparam]
        mov     eax, dword [rcx + 4]    ; CtlID
        cmp     eax, IDC_LIST_QUESTIONS
        je      .draw_qcard
        call    DrawModernButton
        mov     eax, 1
        jmp     .finish

.draw_qcard:
        mov     rcx, [lparam]
        call    DrawQuestionCard
        mov     eax, 1
        jmp     .finish

.wm_command:
        mov     rax, [wparam]
        mov     edx, eax
        shr     edx, 16                 ; notification code
        and     eax, 0FFFFh             ; control ID

        ; Buttons
        cmp     eax, IDC_BTN_SEARCH
        je      .do_search
        cmp     eax, IDC_BTN_CLEAR
        je      .do_clear
        cmp     eax, IDC_BTN_COPY_Q
        je      .do_copy_question
        cmp     eax, IDC_BTN_COPY_A
        je      .do_copy_answer
        cmp     eax, IDC_BTN_BROWSER
        je      .do_open_browser
        cmp     eax, IDC_BTN_BOOKMARK
        je      .do_save_bookmark
        cmp     eax, IDC_BTN_LIVE_API
        je      .do_live_search

        ; Modern Tab Buttons
        cmp     eax, IDC_TAB_EN
        je      .tab_click_en
        cmp     eax, IDC_TAB_RU
        je      .tab_click_ru
        cmp     eax, IDC_TAB_BM
        je      .tab_click_bm
        cmp     eax, IDC_TAB_INFO
        je      .tab_click_info

        ; Quick Chips
        cmp     eax, IDC_CHIP_PYTHON
        je      .chip_python
        cmp     eax, IDC_CHIP_JS
        je      .chip_js
        cmp     eax, IDC_CHIP_ASYNCIO
        je      .chip_asyncio
        cmp     eax, IDC_CHIP_FASTAPI
        je      .chip_fastapi
        cmp     eax, IDC_CHIP_RUST
        je      .chip_rust
        cmp     eax, IDC_CHIP_CPP
        je      .chip_cpp
        cmp     eax, IDC_CHIP_DOCKER
        je      .chip_docker
        cmp     eax, IDC_CHIP_REACT
        je      .chip_react
        cmp     eax, IDC_CHIP_PANDAS
        je      .chip_pandas

        ; ListBox Selection Change
        cmp     eax, IDC_LIST_QUESTIONS
        jne     .cmd_done
        cmp     edx, LBN_SELCHANGE
        jne     .cmd_done
        call    OnQuestionSelected
        jmp     .cmd_done

.tab_click_en:
        mov     [currentTab], 0
        call    InvalidateAllTabs
        call    PerformLiveSearch
        jmp     .cmd_done

.tab_click_ru:
        mov     [currentTab], 1
        call    InvalidateAllTabs
        call    PerformLiveSearch
        jmp     .cmd_done

.tab_click_bm:
        mov     [currentTab], 2
        call    InvalidateAllTabs
        call    ShowBookmarksTab
        jmp     .cmd_done

.tab_click_info:
        mov     [currentTab], 3
        call    InvalidateAllTabs
        call    ShowAboutTab
        jmp     .cmd_done

.chip_python:
        invoke  SetWindowText, [hEditSearch], szChipPy
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_js:
        invoke  SetWindowText, [hEditSearch], szChipJs
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_asyncio:
        invoke  SetWindowText, [hEditSearch], szChipAsync
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_fastapi:
        invoke  SetWindowText, [hEditSearch], szChipFast
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_rust:
        invoke  SetWindowText, [hEditSearch], szChipRs
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_cpp:
        invoke  SetWindowText, [hEditSearch], szChipCpp
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_docker:
        invoke  SetWindowText, [hEditSearch], szChipDock
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_react:
        invoke  SetWindowText, [hEditSearch], szChipReact
        call    PerformLiveSearch
        jmp     .cmd_done
.chip_pandas:
        invoke  SetWindowText, [hEditSearch], szChipPandas
        call    PerformLiveSearch
        jmp     .cmd_done

.do_search:
        call    PerformLiveSearch
        jmp     .cmd_done
.do_live_search:
        call    PerformLiveSearch
        jmp     .cmd_done
.do_clear:
        invoke  SetWindowText, [hEditSearch], szEmpty
        call    ExecuteOfflineSearch
        jmp     .cmd_done
.do_copy_question:
        call    CopyQuestionToClipboard
        jmp     .cmd_done
.do_copy_answer:
        call    CopyAnswerToClipboard
        jmp     .cmd_done
.do_open_browser:
        call    OpenInBrowser
        jmp     .cmd_done
.do_save_bookmark:
        call    SaveBookmark
        jmp     .cmd_done

.cmd_done:
        xor     eax, eax
        jmp     .finish

.wm_size:
        call    LayoutControls
        invoke  InvalidateRect, [hMainWnd], NULL, 1
        invoke  InvalidateRect, [hListQuestions], NULL, 1
        xor     eax, eax
        jmp     .finish

.wm_ctl_static:
        mov     rbx, r8                 ; Save HDC safely in rbx
        mov     rax, r9                 ; lparam = control HWND
        cmp     rax, [hEditDetails]
        je      .details_edit_color
        cmp     rax, [hStatusBar]
        je      .status_bar_color

        ; Brand Title and Labels - Crisp Radiant White!
        invoke  SetBkMode, rbx, 1       ; TRANSPARENT
        invoke  SetTextColor, rbx, 00FFFFFFh ; #FFFFFF
        mov     rax, [hBrushWin]
        jmp     .finish

.status_bar_color:
        invoke  SetBkMode, rbx, 1       ; TRANSPARENT
        invoke  SetTextColor, rbx, 0094A3B8h ; #94A3B8 Slate Gray
        mov     rax, [hBrushWin]
        jmp     .finish

.details_edit_color:
        ; Crystal-clear high-contrast dark code surface
        invoke  SetBkMode, rbx, 2       ; OPAQUE
        invoke  SetBkColor, rbx, 00221611h ; #111622 deep dark
        invoke  SetTextColor, rbx, 00FCF8F8h ; #F8FAFC crisp white
        mov     rax, [hBrushInput]
        jmp     .finish

.wm_ctl_edit:
        ; Search input field
        mov     rbx, r8
        invoke  SetBkMode, rbx, 2       ; OPAQUE
        invoke  SetBkColor, rbx, 00221611h ; #111622
        invoke  SetTextColor, rbx, 00FCF8F8h
        mov     rax, [hBrushInput]
        jmp     .finish

.wm_ctl_list:
        ; Left questions listbox
        mov     rbx, r8
        invoke  SetBkMode, rbx, 2       ; OPAQUE
        invoke  SetBkColor, rbx, 00261B16h ; #161B26
        invoke  SetTextColor, rbx, 00FCF8F8h
        mov     rax, [hBrushPanel]
        jmp     .finish

.wm_destroy:
        invoke  DeleteObject, [hBrushWin]
        invoke  DeleteObject, [hBrushPanel]
        invoke  DeleteObject, [hBrushCard]
        invoke  DeleteObject, [hBrushInput]
        invoke  DeleteObject, [hFontUI]
        invoke  DeleteObject, [hFontBold]
        invoke  DeleteObject, [hFontTitle]
        invoke  DeleteObject, [hFontMono]

        invoke  PostQuitMessage, 0
        xor     eax, eax

.finish:
        ret
endp

; ------------------------------------------------------------------------------
; Custom Owner-Drawn Modern Button Renderer (WM_DRAWITEM)
; Styled after copyprintwindows & screenvideo Fluent Design engine
; ------------------------------------------------------------------------------
proc DrawModernButton uses rbx rsi rdi, pDIS:QWORD
        local hDC:QWORD
        local itemState:DWORD
        local rcLeft:DWORD
        local rcTop:DWORD
        local rcRight:DWORD
        local rcBottom:DWORD
        local fillClr:DWORD
        local borderClr:DWORD
        local textClr:DWORD
        local pText:QWORD
        local hFontUse:QWORD
        local radius:DWORD
        local hBrush:QWORD
        local hOldBrush:QWORD
        local hPen:QWORD
        local hOldPen:QWORD
        local rcBox:rb 16

        mov     rsi, rcx                ; rsi = pDIS

        mov     eax, dword [rsi + 16]   ; itemState
        mov     [itemState], eax
        mov     rax, qword [rsi + 32]   ; hDC
        mov     [hDC], rax

        mov     eax, dword [rsi + 40]
        mov     [rcLeft], eax
        mov     eax, dword [rsi + 44]
        mov     [rcTop], eax
        mov     eax, dword [rsi + 48]
        mov     [rcRight], eax
        mov     eax, dword [rsi + 52]
        mov     [rcBottom], eax

        ; Default settings
        mov     [radius], 8
        mov     rax, [hFontBold]
        mov     [hFontUse], rax
        mov     [textClr], 00FFFFFFh

        ; Check selection / pressed state
        test    [itemState], ODS_SELECTED
        jz      .check_handles
        inc     [rcLeft]
        inc     [rcTop]

.check_handles:
        mov     rax, qword [rsi + 24]   ; hwndItem

        ; 1. Brand Logo Badge "[ SO ]"
        cmp     rax, [hLogoBadge]
        jne     @f
        mov     [fillClr], COLOR_SO_ORANGE
        mov     [borderClr], COLOR_SO_ORANGE_BRD
        lea     rax, [szBrandLogoText]
        mov     [pText], rax
        mov     [radius], 6
        mov     rax, [hFontTitle]
        mov     [hFontUse], rax
        jmp     .do_draw

@@:     ; 2. Search Button (Vibrant Orange)
        cmp     rax, [hBtnSearch]
        jne     @f
        mov     [fillClr], COLOR_SO_ORANGE
        mov     [borderClr], COLOR_SO_ORANGE_BRD
        lea     rax, [szBtnSearchText]
        mov     [pText], rax
        jmp     .do_draw

@@:     ; 3. Clear Button (Dark Slate)
        cmp     rax, [hBtnClear]
        jne     @f
        mov     [fillClr], 003B291Eh    ; #1E293B
        mov     [borderClr], 00554133h  ; #334155
        mov     [textClr], 00B8A394h    ; #94A3B8
        mov     rax, [hFontUI]
        mov     [hFontUse], rax
        lea     rax, [szBtnClearText]
        mov     [pText], rax
        jmp     .do_draw

@@:     ; 4. Live API Button (Royal Purple)
        cmp     rax, [hBtnLiveApi]
        jne     @f
        mov     [fillClr], 00ED3A7Ch    ; #7C3AED
        mov     [borderClr], 00F65C8Bh  ; #8B5CF6
        lea     rax, [szBtnLiveApiText]
        mov     [pText], rax
        jmp     .do_draw

@@:     ; 5. Modern Tab Buttons
        cmp     rax, [hTabEN]
        jne     .chk_tab_ru
        lea     rax, [szTabEN]
        mov     [pText], rax
        cmp     [currentTab], 0
        je      .tab_active
        jmp     .tab_inactive

.chk_tab_ru:
        cmp     rax, [hTabRU]
        jne     .chk_tab_bm
        lea     rax, [szTabRU]
        mov     [pText], rax
        cmp     [currentTab], 1
        je      .tab_active
        jmp     .tab_inactive

.chk_tab_bm:
        cmp     rax, [hTabBM]
        jne     .chk_tab_info
        lea     rax, [szTabBM]
        mov     [pText], rax
        cmp     [currentTab], 2
        je      .tab_active
        jmp     .tab_inactive

.chk_tab_info:
        cmp     rax, [hTabInfo]
        jne     .chk_chips
        lea     rax, [szTabInfo]
        mov     [pText], rax
        cmp     [currentTab], 3
        je      .tab_active
        jmp     .tab_inactive

.tab_active:
        mov     [fillClr], COLOR_SO_ORANGE
        mov     [borderClr], COLOR_SO_ORANGE_BRD
        mov     [textClr], 00FFFFFFh
        mov     rax, [hFontBold]
        mov     [hFontUse], rax
        mov     [radius], 6
        jmp     .do_draw

.tab_inactive:
        mov     [fillClr], 00261B16h    ; #161B26
        mov     [borderClr], 0048372Dh  ; #2D3748
        mov     [textClr], 0094A3B8h    ; #B8A394
        mov     rax, [hFontUI]
        mov     [hFontUse], rax
        mov     [radius], 6
        jmp     .do_draw

.chk_chips:
        ; 6. Quick Chips
        cmp     rax, [hChipPy]
        jne     @f
        lea     rax, [szChipPy]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipJs]
        jne     @f
        lea     rax, [szChipJs]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipAsync]
        jne     @f
        lea     rax, [szChipAsync]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipFast]
        jne     @f
        lea     rax, [szChipFast]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipRs]
        jne     @f
        lea     rax, [szChipRs]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipCpp]
        jne     @f
        lea     rax, [szChipCpp]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipDock]
        jne     @f
        lea     rax, [szChipDock]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipReact]
        jne     @f
        lea     rax, [szChipReact]
        mov     [pText], rax
        jmp     .chip_style
@@:     cmp     rax, [hChipPandas]
        jne     .chk_actions
        lea     rax, [szChipPandas]
        mov     [pText], rax

.chip_style:
        mov     [fillClr], 002C201Ah    ; #1A202C
        mov     [borderClr], 00554133h  ; #334155
        mov     [textClr], 00F0E8E2h    ; #E2E8F0
        mov     rax, [hFontUI]
        mov     [hFontUse], rax
        mov     [radius], 6
        jmp     .do_draw

.chk_actions:
        ; 7. Action Buttons Toolbar
        cmp     rax, [hBtnCopyQ]
        jne     @f
        mov     [fillClr], COLOR_BLUE_BTN
        mov     [borderClr], COLOR_BLUE_BORDER
        lea     rax, [szBtnCopyQText]
        mov     [pText], rax
        jmp     .do_draw

@@:     cmp     rax, [hBtnCopyA]
        jne     @f
        mov     [fillClr], COLOR_EMERALD_BTN
        mov     [borderClr], COLOR_EMERALD_BORDER
        lea     rax, [szBtnCopyAText]
        mov     [pText], rax
        jmp     .do_draw

@@:     cmp     rax, [hBtnBookmark]
        jne     @f
        mov     [fillClr], COLOR_AMBER_BTN
        mov     [borderClr], COLOR_AMBER_BORDER
        lea     rax, [szBtnBookmarkText]
        mov     [pText], rax
        jmp     .do_draw

@@:     cmp     rax, [hBtnBrowser]
        jne     .fallback_btn
        mov     [fillClr], COLOR_INDIGO_BTN
        mov     [borderClr], COLOR_INDIGO_BORDER
        lea     rax, [szBtnBrowserText]
        mov     [pText], rax
        jmp     .do_draw

.fallback_btn:
        mov     [fillClr], 002C201Ah
        mov     [borderClr], 0048372Dh
        lea     rax, [szEmpty]
        mov     [pText], rax

.do_draw:
        ; Clear behind button to avoid corner artifacts
        mov     eax, [rcLeft]
        mov     dword [rcBox], eax
        mov     eax, [rcTop]
        mov     dword [rcBox + 4], eax
        mov     eax, [rcRight]
        mov     dword [rcBox + 8], eax
        mov     eax, [rcBottom]
        mov     dword [rcBox + 12], eax
        invoke  FillRect, [hDC], addr rcBox, [hBrushWin]

        ; Fill Rounded Rectangle
        invoke  CreateSolidBrush, [fillClr]
        mov     [hBrush], rax
        invoke  SelectObject, [hDC], [hBrush]
        mov     [hOldBrush], rax

        invoke  CreatePen, 0, 1, [borderClr]
        mov     [hPen], rax
        invoke  SelectObject, [hDC], [hPen]
        mov     [hOldPen], rax

        invoke  RoundRect, [hDC], [rcLeft], [rcTop], [rcRight], [rcBottom], [radius], [radius]

        invoke  SelectObject, [hDC], [hOldPen]
        invoke  SelectObject, [hDC], [hOldBrush]
        invoke  DeleteObject, [hPen]
        invoke  DeleteObject, [hBrush]

        ; Draw Button Text Centered
        invoke  SetBkMode, [hDC], 1     ; TRANSPARENT
        invoke  SetTextColor, [hDC], [textClr]
        invoke  SelectObject, [hDC], [hFontUse]

        mov     eax, [rcLeft]
        mov     dword [rcBox], eax
        mov     eax, [rcTop]
        mov     dword [rcBox + 4], eax
        mov     eax, [rcRight]
        mov     dword [rcBox + 8], eax
        mov     eax, [rcBottom]
        mov     dword [rcBox + 12], eax

        invoke  DrawText, [hDC], [pText], -1, addr rcBox, DT_CENTER or DT_VCENTER or DT_SINGLELINE or DT_NOPREFIX

.draw_done:
        ret
endp

; ------------------------------------------------------------------------------
; Number Format Helpers for Question Cards
; ------------------------------------------------------------------------------
proc FormatScore uses rbx rsi rdi
        ; rcx = dwScoreVal, rdx = pOutBuf
        mov     rdi, rdx
        mov     eax, ecx
        test    eax, eax
        js      .fs_neg

        mov     byte [rdi], '+'
        mov     byte [rdi + 1], 0
        mov     eax, ecx
        call    AppendNumber
        ret

.fs_neg:
        mov     byte [rdi], '-'
        mov     byte [rdi + 1], 0
        mov     eax, ecx
        neg     eax
        call    AppendNumber
        ret
endp

proc FormatAnsPill uses rbx rsi rdi
        ; rcx = dwAnsVal, edx = isAnswered, r8 = pOutBuf
        mov     rdi, r8
        mov     byte [rdi], 0

        cmp     edx, 1
        jne     .ans_not_acc

        mov     byte [rdi], 'v'
        mov     byte [rdi + 1], ' '
        mov     byte [rdi + 2], 0

.ans_not_acc:
        mov     eax, ecx
        call    AppendNumber
        lea     rsi, [szAnsPillSuffix]
        call    StrCat
        ret
endp

proc FormatNumberViews uses rbx rsi rdi
        ; rcx = dwViewsVal, rdx = pOutBuf
        mov     rdi, rdx
        mov     byte [rdi], 0

        mov     eax, ecx
        cmp     eax, 1000000
        jge     .fnv_mil
        cmp     eax, 1000
        jge     .fnv_k

        ; Less than 1000
        call    AppendNumber
        lea     rsi, [szViewsSuffix]
        call    StrCat
        ret

.fnv_mil:
        ; Millions: e.g. 4200000 -> 4.2M views
        xor     edx, edx
        mov     ebx, 100000
        div     ebx             ; eax = 42
        xor     edx, edx
        mov     ebx, 10
        div     ebx             ; eax = 4, edx = 2
        push    rdx
        call    AppendNumber
        pop     rdx

@@:     cmp     byte [rdi], 0
        je      @f
        inc     rdi
        jmp     @b
@@:     mov     byte [rdi], '.'
        add     dl, '0'
        mov     byte [rdi + 1], dl
        mov     byte [rdi + 2], 'M'
        mov     byte [rdi + 3], 0

        lea     rsi, [szViewsSuffix]
        call    StrCat
        ret

.fnv_k:
        ; Thousands: e.g. 320000 -> 320k views
        xor     edx, edx
        mov     ebx, 1000
        div     ebx
        call    AppendNumber

@@:     cmp     byte [rdi], 0
        je      @f
        inc     rdi
        jmp     @b
@@:     mov     byte [rdi], 'k'
        mov     byte [rdi + 1], 0

        lea     rsi, [szViewsSuffix]
        call    StrCat
        ret
endp

; ------------------------------------------------------------------------------
; Draw Modern Rounded Question Card (Owner-Drawn ListBox)
; ------------------------------------------------------------------------------
proc DrawQuestionCard uses rbx rsi rdi
        local   cardLeft:DWORD
        local   cardTop:DWORD
        local   cardRight:DWORD
        local   cardBottom:DWORD
        local   isSelected:DWORD
        local   itemID:DWORD
        local   hDC:QWORD
        local   hBrushCard:QWORD
        local   hPenBorder:QWORD
        local   hOldBrush:QWORD
        local   hOldPen:QWORD
        local   fillClr:DWORD
        local   borderClr:DWORD
        local   penWidth:DWORD
        local   numScore:DWORD
        local   numAns:DWORD
        local   numViews:DWORD
        local   isAnswered:DWORD
        local   pTitleStr:QWORD
        local   pAuthorStr:QWORD
        local   rcBox:RECT
        local   bufScore:rb 32
        local   bufAns:rb 32
        local   bufViews:rb 32

        mov     rsi, rcx                ; rsi = pDIS directly from rcx
        mov     eax, dword [rsi + 8]    ; itemID
        mov     [itemID], eax
        cmp     eax, -1
        je      .card_exit

        mov     eax, dword [rsi + 16]   ; itemState
        and     eax, 1                  ; ODS_SELECTED
        mov     [isSelected], eax

        mov     rax, qword [rsi + 32]   ; hDC
        mov     [hDC], rax

        mov     eax, dword [rsi + 40]   ; rcItem.left
        mov     [cardLeft], eax
        mov     eax, dword [rsi + 44]   ; rcItem.top
        mov     [cardTop], eax
        mov     eax, dword [rsi + 48]   ; rcItem.right
        mov     [cardRight], eax
        mov     eax, dword [rsi + 52]   ; rcItem.bottom
        mov     [cardBottom], eax

        ; 1. Clear background behind card with hBrushWin
        mov     eax, [cardLeft]
        mov     dword [rcBox.left], eax
        mov     eax, [cardTop]
        mov     dword [rcBox.top], eax
        mov     eax, [cardRight]
        mov     dword [rcBox.right], eax
        mov     eax, [cardBottom]
        mov     dword [rcBox.bottom], eax
        lea     rdx, [rcBox]
        invoke  FillRect, [hDC], rdx, [hBrushWin]

        ; 2. Card margins
        add     [cardLeft], 4
        add     [cardTop], 2
        sub     [cardRight], 6
        sub     [cardBottom], 3

        ; 3. Card colors
        cmp     [isSelected], 1
        jne     .card_normal

        ; Selected card: Elevated Dark Slate (#141B26) + Glowing Orange Outline (#FF7A00, 2px)
        mov     [fillClr], 00261B14h
        mov     [borderClr], 00007AFFh
        mov     [penWidth], 2
        jmp     .draw_shape

.card_normal:
        ; Normal card: Deep Dark Surface (#10141C) + Subtle Border (#1C222E, 1px)
        mov     [fillClr], 001C1410h
        mov     [borderClr], 002E221Ch
        mov     [penWidth], 1

.draw_shape:
        invoke  CreateSolidBrush, [fillClr]
        mov     [hBrushCard], rax
        invoke  SelectObject, [hDC], [hBrushCard]
        mov     [hOldBrush], rax

        invoke  CreatePen, 0, [penWidth], [borderClr]
        mov     [hPenBorder], rax
        invoke  SelectObject, [hDC], [hPenBorder]
        mov     [hOldPen], rax

        invoke  RoundRect, [hDC], [cardLeft], [cardTop], [cardRight], [cardBottom], 8, 8

        invoke  SelectObject, [hDC], [hOldPen]
        invoke  SelectObject, [hDC], [hOldBrush]
        invoke  DeleteObject, [hPenBorder]
        invoke  DeleteObject, [hBrushCard]

        ; 4. Retrieve Question Details
        cmp     [isLiveMode], 1
        jne     .get_offline_data

        mov     eax, [itemID]
        cmp     eax, MAX_LIVE_ITEMS
        jge     .card_exit
        imul    rax, sizeof.LIVE_QUESTION
        lea     rbx, [liveDb + rax]

        mov     eax, [rbx + LIVE_QUESTION.dwScore]
        mov     [numScore], eax
        mov     eax, [rbx + LIVE_QUESTION.dwAnswers]
        mov     [numAns], eax
        mov     eax, [rbx + LIVE_QUESTION.dwViews]
        mov     [numViews], eax
        mov     eax, [rbx + LIVE_QUESTION.bAnswered]
        mov     [isAnswered], eax
        lea     rax, [rbx + LIVE_QUESTION.szTitle]
        mov     [pTitleStr], rax
        lea     rax, [rbx + LIVE_QUESTION.szAuthor]
        mov     [pAuthorStr], rax
        jmp     .have_card_data

.get_offline_data:
        invoke  SendMessage, [hListQuestions], LB_GETITEMDATA, [itemID], 0
        cmp     rax, -1
        je      .card_exit
        cmp     rax, TOTAL_QUESTIONS
        jge     .card_exit
        imul    rax, sizeof.QUESTION_ITEM
        lea     rbx, [qDatabase + rax]

        mov     eax, [rbx + QUESTION_ITEM.dwScore]
        mov     [numScore], eax
        mov     eax, [rbx + QUESTION_ITEM.dwAnswers]
        mov     [numAns], eax
        mov     eax, [rbx + QUESTION_ITEM.dwViews]
        mov     [numViews], eax
        mov     eax, [rbx + QUESTION_ITEM.bAccepted]
        mov     [isAnswered], eax
        mov     rax, [rbx + QUESTION_ITEM.pszTitle]
        mov     [pTitleStr], rax
        mov     rax, [rbx + QUESTION_ITEM.pszAuthor]
        mov     [pAuthorStr], rax

.have_card_data:
        invoke  SetBkMode, [hDC], 1     ; TRANSPARENT

        ; 5. Draw Row 1: Score Badge (Green Bold)
        mov     ecx, [numScore]
        lea     rdx, [bufScore]
        call    FormatScore

        invoke  SelectObject, [hDC], [hFontBold]
        invoke  SetTextColor, [hDC], 0081B910h ; #10B981 Emerald Green

        mov     eax, [cardLeft]
        add     eax, 10
        mov     dword [rcBox.left], eax
        mov     eax, [cardTop]
        add     eax, 6
        mov     dword [rcBox.top], eax
        mov     eax, [cardLeft]
        add     eax, 62
        mov     dword [rcBox.right], eax
        mov     eax, [cardTop]
        add     eax, 24
        mov     dword [rcBox.bottom], eax
        lea     r9, [rcBox]
        lea     rdx, [bufScore]
        invoke  DrawText, [hDC], rdx, -1, r9, DT_LEFT or DT_VCENTER or DT_SINGLELINE

        ; 6. Draw Row 1: Answers Pill
        mov     ecx, [numAns]
        mov     edx, [isAnswered]
        lea     r8, [bufAns]
        call    FormatAnsPill

        mov     eax, [cardLeft]
        add     eax, 64
        mov     dword [rcBox.left], eax
        mov     eax, [cardTop]
        add     eax, 5
        mov     dword [rcBox.top], eax
        mov     eax, [cardLeft]
        add     eax, 126
        mov     dword [rcBox.right], eax
        mov     eax, [cardTop]
        add     eax, 23
        mov     dword [rcBox.bottom], eax

        cmp     [numAns], 0
        jle     .pill_zero

        cmp     [isAnswered], 1
        jne     .pill_norm

        ; Solved: #065F46 bg, #10B981 border, #34D399 text
        mov     [fillClr], 00465F06h
        mov     [borderClr], 0081B910h
        mov     eax, 0099D334h
        jmp     .render_pill

.pill_norm:
        ; Active answers: #1E293B bg, #334155 border, #94A3B8 text
        mov     [fillClr], 003B291Eh
        mov     [borderClr], 00554133h
        mov     eax, 00B8A394h
        jmp     .render_pill

.pill_zero:
        ; 0 answers: subtle muted
        mov     [fillClr], 00221B16h
        mov     [borderClr], 00332820h
        mov     eax, 008B7464h

.render_pill:
        push    rax                     ; Save pill text color
        invoke  CreateSolidBrush, [fillClr]
        mov     [hBrushCard], rax
        invoke  SelectObject, [hDC], [hBrushCard]
        mov     [hOldBrush], rax

        invoke  CreatePen, 0, 1, [borderClr]
        mov     [hPenBorder], rax
        invoke  SelectObject, [hDC], [hPenBorder]
        mov     [hOldPen], rax

        invoke  RoundRect, [hDC], [rcBox.left], [rcBox.top], [rcBox.right], [rcBox.bottom], 6, 6

        invoke  SelectObject, [hDC], [hOldPen]
        invoke  SelectObject, [hDC], [hOldBrush]
        invoke  DeleteObject, [hPenBorder]
        invoke  DeleteObject, [hBrushCard]

        pop     rax                     ; Restore pill text color
        invoke  SetTextColor, [hDC], rax
        invoke  SelectObject, [hDC], [hFontBadge]
        lea     r9, [rcBox]
        lea     rdx, [bufAns]
        invoke  DrawText, [hDC], rdx, -1, r9, DT_CENTER or DT_VCENTER or DT_SINGLELINE or DT_NOPREFIX

        ; 7. Draw Row 1: Views
        mov     ecx, [numViews]
        lea     rdx, [bufViews]
        call    FormatNumberViews

        invoke  SelectObject, [hDC], [hFontUI]
        invoke  SetTextColor, [hDC], 008B7464h ; #64748B Slate Gray

        mov     eax, [cardLeft]
        add     eax, 134
        mov     dword [rcBox.left], eax
        mov     eax, [cardTop]
        add     eax, 6
        mov     dword [rcBox.top], eax
        mov     eax, [cardLeft]
        add     eax, 215
        mov     dword [rcBox.right], eax
        mov     eax, [cardTop]
        add     eax, 24
        mov     dword [rcBox.bottom], eax
        lea     r9, [rcBox]
        lea     rdx, [bufViews]
        invoke  DrawText, [hDC], rdx, -1, r9, DT_LEFT or DT_VCENTER or DT_SINGLELINE

        ; 8. Draw Row 1: Author (Right Aligned)
        mov     eax, [cardLeft]
        add     eax, 210
        mov     dword [rcBox.left], eax
        mov     eax, [cardTop]
        add     eax, 6
        mov     dword [rcBox.top], eax
        mov     eax, [cardRight]
        sub     eax, 10
        mov     dword [rcBox.right], eax
        mov     eax, [cardTop]
        add     eax, 24
        mov     dword [rcBox.bottom], eax
        lea     r9, [rcBox]
        invoke  DrawText, [hDC], [pAuthorStr], -1, r9, DT_RIGHT or DT_VCENTER or DT_SINGLELINE or DT_END_ELLIPSIS

        ; 9. Draw Row 2 & 3: Multi-Line Bold Question Title
        invoke  SelectObject, [hDC], [hFontBold]
        cmp     [isSelected], 1
        jne     @f
        invoke  SetTextColor, [hDC], 00FFFFFFh ; Bright Pure White
        jmp     .do_draw_title
@@:
        invoke  SetTextColor, [hDC], 00F1F5F9h ; Crisp Off-White

.do_draw_title:
        mov     eax, [cardLeft]
        add     eax, 10
        mov     dword [rcBox.left], eax
        mov     eax, [cardTop]
        add     eax, 26
        mov     dword [rcBox.top], eax
        mov     eax, [cardRight]
        sub     eax, 10
        mov     dword [rcBox.right], eax
        mov     eax, [cardBottom]
        sub     eax, 4
        mov     dword [rcBox.bottom], eax
        lea     r9, [rcBox]
        invoke  DrawText, [hDC], [pTitleStr], -1, r9, DT_LEFT or DT_WORDBREAK or DT_END_ELLIPSIS or DT_NOPREFIX

.card_exit:
        ret
endp

; ------------------------------------------------------------------------------
; Invalidate All Modern Tab Buttons for Refresh
; ------------------------------------------------------------------------------
proc InvalidateAllTabs
        invoke  InvalidateRect, [hTabEN], NULL, 1
        invoke  InvalidateRect, [hTabRU], NULL, 1
        invoke  InvalidateRect, [hTabBM], NULL, 1
        invoke  InvalidateRect, [hTabInfo], NULL, 1
        ret
endp

; ------------------------------------------------------------------------------
; Create Application Controls
; ------------------------------------------------------------------------------
proc CreateAppControls
        ; Top Brand Badge "[ SO ]" (Owner-drawn rounded orange badge)
        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                16, 14, 48, 30, [hMainWnd], IDC_BADGE_LOGO, [hInstance], NULL
        mov     [hLogoBadge], rax

        ; App Title "Search Pro"
        invoke  CreateWindowEx, 0, szStaticClass, szAppTitleLabel,\
                WS_CHILD or WS_VISIBLE,\
                70, 16, 200, 26, [hMainWnd], 0, [hInstance], NULL
        mov     [hLblLogo], rax
        invoke  SendMessage, rax, WM_SETFONT, [hFontTitle], 1

        ; Search Input Box
        invoke  CreateWindowEx, WS_EX_CLIENTEDGE, szEditClass, szDefSearch,\
                WS_CHILD or WS_VISIBLE or WS_TABSTOP or ES_AUTOHSCROLL,\
                275, 14, 425, 30, [hMainWnd], IDC_EDIT_SEARCH, [hInstance], NULL
        mov     [hEditSearch], rax
        invoke  SendMessage, rax, WM_SETFONT, [hFontUI], 1

        ; Search Button (Owner-drawn)
        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or WS_TABSTOP or BS_OWNERDRAW,\
                708, 14, 90, 30, [hMainWnd], IDC_BTN_SEARCH, [hInstance], NULL
        mov     [hBtnSearch], rax

        ; Clear Button (Owner-drawn)
        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or WS_TABSTOP or BS_OWNERDRAW,\
                806, 14, 65, 30, [hMainWnd], IDC_BTN_CLEAR, [hInstance], NULL
        mov     [hBtnClear], rax

        ; Live API Button (Owner-drawn)
        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or WS_TABSTOP or BS_OWNERDRAW,\
                879, 14, 120, 30, [hMainWnd], IDC_BTN_LIVE_API, [hInstance], NULL
        mov     [hBtnLiveApi], rax

        ; Quick Chips Row
        invoke  CreateWindowEx, 0, szStaticClass, szQuickChipsLabel,\
                WS_CHILD or WS_VISIBLE,\
                16, 56, 85, 20, [hMainWnd], 0, [hInstance], NULL
        invoke  SendMessage, rax, WM_SETFONT, [hFontUI], 1

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                105, 54, 65, 24, [hMainWnd], IDC_CHIP_PYTHON, [hInstance], NULL
        mov     [hChipPy], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                176, 54, 80, 24, [hMainWnd], IDC_CHIP_JS, [hInstance], NULL
        mov     [hChipJs], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                262, 54, 65, 24, [hMainWnd], IDC_CHIP_ASYNCIO, [hInstance], NULL
        mov     [hChipAsync], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                333, 54, 65, 24, [hMainWnd], IDC_CHIP_FASTAPI, [hInstance], NULL
        mov     [hChipFast], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                404, 54, 55, 24, [hMainWnd], IDC_CHIP_RUST, [hInstance], NULL
        mov     [hChipRs], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                465, 54, 50, 24, [hMainWnd], IDC_CHIP_CPP, [hInstance], NULL
        mov     [hChipCpp], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                521, 54, 65, 24, [hMainWnd], IDC_CHIP_DOCKER, [hInstance], NULL
        mov     [hChipDock], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                592, 54, 55, 24, [hMainWnd], IDC_CHIP_REACT, [hInstance], NULL
        mov     [hChipReact], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                653, 54, 65, 24, [hMainWnd], IDC_CHIP_PANDAS, [hInstance], NULL
        mov     [hChipPandas], rax

        ; Modern Segmented Tab Buttons
        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                16, 88, 105, 28, [hMainWnd], IDC_TAB_EN, [hInstance], NULL
        mov     [hTabEN], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                126, 88, 105, 28, [hMainWnd], IDC_TAB_RU, [hInstance], NULL
        mov     [hTabRU], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                236, 88, 105, 28, [hMainWnd], IDC_TAB_BM, [hInstance], NULL
        mov     [hTabBM], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                346, 88, 115, 28, [hMainWnd], IDC_TAB_INFO, [hInstance], NULL
        mov     [hTabInfo], rax

        ; Left Questions ListBox (Owner-drawn cards, 78px card height)
        invoke  CreateWindowEx, WS_EX_CLIENTEDGE, szListBoxClass, NULL,\
                WS_CHILD or WS_VISIBLE or WS_VSCROLL or LBS_NOTIFY or LBS_OWNERDRAWFIXED or LBS_HASSTRINGS or LBS_NOINTEGRALHEIGHT,\
                16, 122, 445, 532, [hMainWnd], IDC_LIST_QUESTIONS, [hInstance], NULL
        mov     [hListQuestions], rax
        invoke  SendMessage, rax, WM_SETFONT, [hFontUI], 1
        invoke  SendMessage, rax, LB_SETITEMHEIGHT, 0, 78

        ; Right Action Toolbar (positioned dynamically by LayoutControls)
        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                0, 0, 0, 0, [hMainWnd], IDC_BTN_COPY_Q, [hInstance], NULL
        mov     [hBtnCopyQ], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                0, 0, 0, 0, [hMainWnd], IDC_BTN_COPY_A, [hInstance], NULL
        mov     [hBtnCopyA], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                0, 0, 0, 0, [hMainWnd], IDC_BTN_BOOKMARK, [hInstance], NULL
        mov     [hBtnBookmark], rax

        invoke  CreateWindowEx, 0, szBtnClass, NULL,\
                WS_CHILD or WS_VISIBLE or BS_OWNERDRAW,\
                0, 0, 0, 0, [hMainWnd], IDC_BTN_BROWSER, [hInstance], NULL
        mov     [hBtnBrowser], rax

        ; Load RichEdit library msftedit.dll
        invoke  LoadLibrary, szMsfteditDll
        mov     [hMsfteditDll], rax

        ; Right Details Multi-Line RichEdit Control (positioned dynamically by LayoutControls)
        invoke  CreateWindowExW, 0, szRichEditClass, NULL,\
                WS_CHILD or WS_VISIBLE or WS_VSCROLL or ES_MULTILINE or ES_AUTOVSCROLL or ES_READONLY,\
                0, 0, 0, 0, [hMainWnd], IDC_EDIT_DETAILS, [hInstance], NULL
        mov     [hEditDetails], rax

        ; Set RichEdit background color
        invoke  SendMessageW, [hEditDetails], EM_SETBKGNDCOLOR, 0, COLOR_RICH_BG

        ; Bottom Status Bar
        invoke  CreateWindowEx, 0, szStaticClass, szStatusReady,\
                WS_CHILD or WS_VISIBLE,\
                16, 662, 1100, 20, [hMainWnd], IDC_STATUS_BAR, [hInstance], NULL
        mov     [hStatusBar], rax
        invoke  SendMessage, rax, WM_SETFONT, [hFontUI], 1

        ; Initial layout pass
        call    LayoutControls
        ret
endp

; ------------------------------------------------------------------------------
; Dynamic Window Layout & Sizing
; ------------------------------------------------------------------------------
proc LayoutControls
        lea     rdx, [rcClient]
        invoke  GetClientRect, [hMainWnd], rdx

        mov     eax, [rcClient.right]
        sub     eax, [rcClient.left]
        mov     [winW], eax

        mov     eax, [rcClient.bottom]
        sub     eax, [rcClient.top]
        mov     [winH], eax

        ; Responsive Search Input Box & Buttons
        mov     eax, [winW]
        sub     eax, 190                ; X offset for search edit is 190
        sub     eax, 260                ; space for Search, Clear, Live buttons
        cmp     eax, 200
        jge     @f
        mov     eax, 200
@@:     invoke  MoveWindow, [hEditSearch], 190, 14, eax, 30, 1

        mov     eax, [winW]
        sub     eax, 255
        invoke  MoveWindow, [hBtnSearch], eax, 14, 80, 30, 1

        mov     eax, [winW]
        sub     eax, 170
        invoke  MoveWindow, [hBtnClear], eax, 14, 65, 30, 1

        mov     eax, [winW]
        sub     eax, 100
        invoke  MoveWindow, [hBtnLiveApi], eax, 14, 84, 30, 1

        ; Compute List Width (38% of window width, clamped 360..600)
        mov     eax, [winW]
        imul    eax, 38
        cdq
        mov     ecx, 100
        idiv    ecx
        cmp     eax, 360
        jge     @f
        mov     eax, 360
@@:     cmp     eax, 600
        jle     @f
        mov     eax, 600
@@:     mov     [listW], eax

        ; Compute Details Width
        mov     eax, [winW]
        sub     eax, [listW]
        sub     eax, 44
        mov     [detailsW], eax

        ; Compute Height
        mov     eax, [winH]
        sub     eax, 155
        mov     [panelH], eax

        ; Move ListBox
        invoke  MoveWindow, [hListQuestions], 16, 122, [listW], [panelH], 1

        ; Move Details Edit
        mov     eax, [listW]
        add     eax, 28
        mov     [detailsX], eax

        invoke  MoveWindow, [hEditDetails], [detailsX], 122, [detailsW], [panelH], 1

        ; Invalidate toolbar strip to erase previous button positions
        mov     dword [rcClient.left], 0
        mov     dword [rcClient.top], 80
        mov     eax, [winW]
        mov     dword [rcClient.right], eax
        mov     dword [rcClient.bottom], 120
        lea     rdx, [rcClient]
        invoke  InvalidateRect, [hMainWnd], rdx, 1

        ; Move Action Buttons
        invoke  MoveWindow, [hBtnCopyQ], [detailsX], 88, 120, 28, 1
        mov     eax, [detailsX]
        add     eax, 126
        invoke  MoveWindow, [hBtnCopyA], eax, 88, 120, 28, 1
        mov     eax, [detailsX]
        add     eax, 252
        invoke  MoveWindow, [hBtnBookmark], eax, 88, 125, 28, 1

        ; Dock Browser button to the right edge of the details panel
        mov     eax, [detailsX]
        add     eax, [detailsW]
        sub     eax, 105
        invoke  MoveWindow, [hBtnBrowser], eax, 88, 105, 28, 1

        ; Move Status Bar
        mov     eax, [winH]
        sub     eax, 26
        mov     ecx, [winW]
        sub     ecx, 32
        invoke  MoveWindow, [hStatusBar], 16, eax, ecx, 20, 1

.done:
        ret
endp

; ------------------------------------------------------------------------------
; Show Bookmarks Tab
; ------------------------------------------------------------------------------
proc ShowBookmarksTab
        invoke  SendMessage, [hListQuestions], LB_RESETCONTENT, 0, 0
        mov     [matchCount], 0
        mov     [isLiveMode], 0

        ; Try to read bookmarks.txt
        invoke  CreateFile, szBookmarkFile, 80000000h, 1, NULL, 3, 80h, NULL
        cmp     rax, -1
        je      .no_bookmarks
        mov     [hBmFile], rax

        invoke  ReadFile, [hBmFile], netBuffer, 16384, bytesRead, NULL
        invoke  CloseHandle, [hBmFile]

        cmp     [bytesRead], 0
        jle     .no_bookmarks

        ; Add items from bookmarks.txt
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szBookmarkHeader
        invoke  SendMessage, [hListQuestions], LB_SETITEMDATA, 0, 0
        inc     [matchCount]

        invoke  SetWindowText, [hEditDetails], szBookmarkDetails
        invoke  SetWindowText, [hStatusBar], szStatusSavedBm
        ret

.no_bookmarks:
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szNoBookmarksItem
        invoke  SetWindowText, [hEditDetails], szNoBookmarksDetails
        invoke  SetWindowText, [hStatusBar], szStatusNoBookmarks
        ret
endp

; ------------------------------------------------------------------------------
; Show About & Guide Tab
; ------------------------------------------------------------------------------
proc ShowAboutTab
        mov     [isLiveMode], 0
        invoke  SendMessage, [hListQuestions], LB_RESETCONTENT, 0, 0
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szAboutList1
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szAboutList2
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szAboutList3
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szAboutList4
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, szAboutList5
        lea     rcx, [szAboutBody]
        call    RenderDetailsRich
        invoke  SetWindowText, [hStatusBar], szStatusAbout
        ret
endp

; ------------------------------------------------------------------------------
; RichEdit Formatter: Appends styled wide text to RichEdit
; ------------------------------------------------------------------------------
proc RichAppendText uses rbx rsi rdi r12
        local   crLocal:CHARRANGE
        local   pTxt:QWORD
        local   tColor:DWORD
        local   bColor:DWORD
        local   pFt:QWORD
        local   pSize:DWORD
        local   bBold:DWORD
        local   dummy:QWORD

        mov     [pTxt], rcx
        mov     [tColor], edx
        mov     [bColor], r8d
        mov     [pFt], r9
        mov     [pSize], r10d
        mov     [bBold], r11d

        ; Move caret to end
        mov     [crLocal.cpMin], -1
        mov     [crLocal.cpMax], -1
        lea     r9, [crLocal]
        invoke  SendMessageW, [hEditDetails], EM_EXSETSEL, 0, r9

        ; Configure CHARFORMAT2W
        mov     [cf.cbSize], sizeof.CHARFORMAT2W
        mov     [cf.dwMask], CFM_COLOR or CFM_FACE or CFM_SIZE or CFM_BACKCOLOR
        mov     eax, [tColor]
        mov     [cf.crTextColor], eax
        mov     eax, [pSize]
        imul    eax, 20
        mov     [cf.yHeight], eax

        mov     eax, [bColor]
        test    eax, eax
        jz      .default_bg
        mov     [cf.crBackColor], eax
        mov     [cf.dwEffects], 0
        jmp     .check_bold

.default_bg:
        mov     [cf.crBackColor], COLOR_RICH_BG
        mov     [cf.dwEffects], CFE_AUTOBACKCOLOR

.check_bold:
        cmp     [bBold], 1
        jne     .not_bold
        or      [cf.dwMask], CFM_BOLD or CFM_WEIGHT
        or      [cf.dwEffects], CFE_BOLD
        mov     [cf.wWeight], 700
        jmp     .copy_font

.not_bold:
        mov     [cf.wWeight], 400

.copy_font:
        mov     rsi, [pFt]
        lea     rdi, [cf.szFaceName]
        mov     ecx, 32
        rep     movsw

        invoke  SendMessageW, [hEditDetails], EM_SETCHARFORMAT, SCF_SELECTION, addr cf
        invoke  SendMessageW, [hEditDetails], EM_REPLACESEL, 0, [pTxt]
        ret
endp

; ------------------------------------------------------------------------------
; RichEdit Helper: Convert ANSI (CP1251) to UTF-16 and Append
; ------------------------------------------------------------------------------
proc RichAppendAnsi uses rbx rsi rdi r12
        local   pAnsi:QWORD
        local   tColor:DWORD
        local   bColor:DWORD
        local   pFt:QWORD
        local   pSize:DWORD
        local   bBold:DWORD
        local   dummy:QWORD
        local   padAnsi:QWORD

        mov     [pAnsi], rcx
        mov     [tColor], edx
        mov     [bColor], r8d
        mov     [pFt], r9
        mov     [pSize], r10d
        mov     [bBold], r11d

        invoke  MultiByteToWideChar, 1251, 0, [pAnsi], -1, wstrBuf, 16384

        lea     rcx, [wstrBuf]
        mov     edx, [tColor]
        mov     r8d, [bColor]
        mov     r9,  [pFt]
        mov     r10d, [pSize]
        mov     r11d, [bBold]
        call    RichAppendText
        ret
endp

proc RichAppendNewline uses rbx rsi rdi r12
        lea     rcx, [wszCRLF]
        mov     edx, COLOR_TEXT_NORMAL
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendText
        ret
endp

proc RichAppendTwoNewlines uses rbx rsi rdi r12
        lea     rcx, [wszTwoCRLF]
        mov     edx, COLOR_TEXT_NORMAL
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendText
        ret
endp

; ------------------------------------------------------------------------------
; Full Question & Answer Rich Renderer for RichEdit
; Formats Title (15pt Bold), Metadata, Code Blocks (Consolas 10pt with Navy BG),
; and Accepted Solution Banner (Emerald Green BG)
; ------------------------------------------------------------------------------
proc RenderDetailsRich uses rbx rsi rdi r12 r13 r14 r15, pDetails:QWORD
        local   bFirstLine:DWORD
        local   dummy:QWORD
        local   alignPad:QWORD

        mov     r15, rcx                ; r15 = preserved cursor into pDetails
        test    r15, r15
        jz      .done

        ; Clear RichEdit control
        invoke  SetWindowTextW, [hEditDetails], wszEmpty
        mov     [inCodeBlock], 0
        mov     [bFirstLine], 1
        mov     [hasCodeSnippet], 0
        lea     rax, [codeSnippetBuf]
        mov     [pCodeSnippetCur], rax
        mov     byte [codeSnippetBuf], 0

.line_loop:
        cmp     byte [r15], 0
        je      .done

        ; Extract one line from r15 into statusBuf
        mov     rsi, r15
        lea     rdi, [statusBuf]
        xor     ecx, ecx
.get_char:
        lodsb
        test    al, al
        jz      .line_done_null
        cmp     al, 13
        je      .skip_cr
        cmp     al, 10
        je      .line_done
        cmp     ecx, 480
        jge     .get_char
        stosb
        inc     ecx
        jmp     .get_char

.skip_cr:
        cmp     byte [rsi], 10
        jne     .line_done
        inc     rsi
        jmp     .line_done

.line_done_null:
        dec     rsi
.line_done:
        mov     byte [rdi], 0
        mov     r15, rsi                ; Save cursor into r15!

        ; Check if empty line
        cmp     byte [statusBuf], 0
        jne     @f
        cmp     [inCodeBlock], 1
        jne     .empty_norm

        ; Blank line inside code block: render as 68-char dark navy line!
        lea     rcx, [wszCodeBar]
        mov     edx, COLOR_CODE_BORDER
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        mov     r11d, 1
        call    RichAppendText

        lea     rdi, [padBuf]
        mov     ecx, 63
        mov     al, ' '
        rep     stosb
        mov     byte [rdi], 0

        lea     rcx, [padBuf]
        mov     edx, COLOR_TEXT_NORMAL
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendAnsi

        lea     rcx, [wszCRLF]
        mov     edx, COLOR_TEXT_NORMAL
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendText

        ; Also add newline to code snippet
        mov     rdi, [pCodeSnippetCur]
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        mov     byte [rdi], 0
        mov     [pCodeSnippetCur], rdi
        jmp     .line_loop

.empty_norm:
        call    RichAppendNewline
        jmp     .line_loop

@@:     ; Skip divider lines
        cmp     word [statusBuf], '=='
        je      .line_loop
        cmp     word [statusBuf], '--'
        je      .line_loop
        cmp     byte [statusBuf], '+'
        je      .line_loop

        ; Check if this is the Question Title (first non-divider line)
        cmp     [bFirstLine], 1
        jne     .not_title

        mov     [bFirstLine], 0
        lea     rcx, [statusBuf]
        mov     edx, COLOR_TEXT_WHITE
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 15
        mov     r11d, 1
        call    RichAppendAnsi
        call    RichAppendTwoNewlines
        jmp     .line_loop

.not_title:
        ; Strip leading spaces and '|' into r14
        lea     r14, [statusBuf]
.strip_start:
        cmp     byte [r14], ' '
        jne     @f
        inc     r14
        jmp     .strip_start
@@:     cmp     byte [r14], '|'
        jne     @f
        inc     r14
        jmp     .strip_start
@@:
        ; Check Accepted Solution Banner
        mov     rsi, r14
        lea     rdi, [szAcceptedBadgeSub]
        call    FindSubStr
        test    rax, rax
        jz      .chk_section_headers

        cmp     [inCodeBlock], 1
        jne     @f
        mov     [inCodeBlock], 0
        lea     rcx, [wszCodeBottom]
        mov     edx, COLOR_CODE_LINE
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendText
        call    RichAppendNewline

@@:     lea     rcx, [wszAcceptedBanner]
        mov     edx, COLOR_ACC_TEXT
        mov     r8d, COLOR_ACC_BG
        lea     r9, [wszFontUI]
        mov     r10d, 10
        mov     r11d, 1
        call    RichAppendText
        call    RichAppendNewline
        jmp     .line_loop

.chk_section_headers:
        cmp     dword [r14], 'QUES'
        jne     @f
        mov     [inCodeBlock], 0
        mov     rcx, r14
        mov     edx, COLOR_TEXT_WHITE
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 13
        mov     r11d, 1
        call    RichAppendAnsi
        call    RichAppendTwoNewlines
        jmp     .line_loop

@@:     cmp     dword [r14], 'ANSW'
        jne     @f
        mov     [inCodeBlock], 0
        mov     rcx, r14
        mov     edx, COLOR_TEXT_WHITE
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 13
        mov     r11d, 1
        call    RichAppendAnsi
        call    RichAppendNewline
        jmp     .line_loop

@@:     cmp     dword [r14], 'Answ'
        jne     @f
        mov     [inCodeBlock], 0
        mov     rcx, r14
        mov     edx, COLOR_KEYWORD
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 11
        mov     r11d, 1
        call    RichAppendAnsi
        call    RichAppendNewline
        jmp     .line_loop

@@:     cmp     word [r14], 'Sc'
        je      .meta_line
        cmp     byte [r14], '+'
        je      .meta_line
        cmp     word [r14], 'UR'
        je      .url_line
        cmp     word [r14], 'Ta'
        je      .tags_line

        ; 3. Ignore ASCII borders (+---)
        cmp     byte [statusBuf], '+'
        jne     @f
        cmp     byte [statusBuf + 1], '-'
        je      .line_loop
@@:

        ; 4. Check for Code Header ([CODE])
        mov     rsi, r14
        lea     rdi, [szCodeBoxSub]
        call    FindSubStr
        test    rax, rax
        jz      .chk_code_line

        ; Render Slate Code Header
        mov     [inCodeBlock], 1
        lea     rcx, [wszCodeHeaderTop]
        mov     edx, COLOR_IDENTIFIER
        mov     r8d, COLOR_CODE_HDR_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        mov     r11d, 1
        call    RichAppendText
        jmp     .line_loop

.chk_code_line:
        ; 5. Check if line belongs to code block
        cmp     [inCodeBlock], 1
        je      .verify_code_line
        cmp     byte [statusBuf], '|'
        jne     .norm_para

.verify_code_line:
        ; Check if first char is Cyrillic (0xC0..0xFF)
        cmp     byte [r14], 0C0h
        jae     .exit_code_block

        ; It's a code line!
        mov     [inCodeBlock], 1
        jmp     .code_line_ready

.exit_code_block:
        cmp     [inCodeBlock], 1
        jne     .norm_para
        mov     [inCodeBlock], 0
        lea     rcx, [wszCodeBottom]
        mov     edx, COLOR_CODE_LINE
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendText
        call    RichAppendNewline
        jmp     .norm_para

.code_line_ready:
        mov     r12d, COLOR_TEXT_NORMAL
        mov     r13d, 0

        cmp     dword [r14], 'impo'
        je      .kw_blue
        cmp     dword [r14], 'from'
        je      .kw_blue
        cmp     dword [r14], 'def '
        je      .kw_blue
        cmp     dword [r14], 'retu'
        je      .kw_blue
        cmp     byte [r14], '#'
        je      .kw_comment
        jmp     .render_code

.kw_blue:
        mov     r12d, COLOR_KEYWORD
        mov     r13d, 1
        jmp     .render_code

.kw_comment:
        mov     r12d, COLOR_COMMENT
        jmp     .render_code

.render_code:
        ; Append code line to codeSnippetBuf
        mov     rsi, r14
        mov     rdi, [pCodeSnippetCur]
.copy_snip:
        lodsb
        test    al, al
        jz      .snip_eol
        stosb
        jmp     .copy_snip
.snip_eol:
        mov     al, 13
        stosb
        mov     al, 10
        stosb
        mov     byte [rdi], 0
        mov     [pCodeSnippetCur], rdi
        mov     [hasCodeSnippet], 1

        ; 1. Left vertical accent bar '  |  ' (5 chars)
        lea     rcx, [wszCodeBar]
        mov     edx, COLOR_CODE_BORDER
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        mov     r11d, 1
        call    RichAppendText

        ; 2. Append code text with syntax color in r12d
        mov     rcx, r14
        mov     edx, r12d
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        mov     r11d, r13d
        call    RichAppendAnsi

        ; 3. Pad to 68 chars so the navy background is full width!
        mov     rsi, r14
        xor     ecx, ecx
.count_code_len:
        cmp     byte [rsi + rcx], 0
        je      .calc_pad
        inc     ecx
        cmp     ecx, 63
        jl      .count_code_len

.calc_pad:
        mov     eax, 63
        sub     eax, ecx
        jle     .code_line_break
        mov     ecx, eax
        lea     rdi, [padBuf]
        mov     al, ' '
        rep     stosb
        mov     byte [rdi], 0

        lea     rcx, [padBuf]
        mov     edx, COLOR_TEXT_NORMAL
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendAnsi

.code_line_break:
        lea     rcx, [wszCRLF]
        mov     edx, COLOR_TEXT_NORMAL
        mov     r8d, COLOR_CODE_BG
        lea     r9, [wszFontMono]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendText
        jmp     .line_loop

.chk_headers:
        ; Check Section Headers
        cmp     dword [statusBuf], 'QUES'
        jne     @f
        lea     rcx, [statusBuf]
        mov     edx, COLOR_TEXT_WHITE
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 13
        mov     r11d, 1
        call    RichAppendAnsi
        call    RichAppendTwoNewlines
        jmp     .line_loop

@@:     cmp     dword [statusBuf], 'ANSW'
        jne     @f
        lea     rcx, [statusBuf]
        mov     edx, COLOR_TEXT_WHITE
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 13
        mov     r11d, 1
        call    RichAppendAnsi
        call    RichAppendNewline
        jmp     .line_loop

@@:     cmp     word [statusBuf], 'Sc'
        je      .meta_line
        cmp     byte [statusBuf], '+'
        je      .meta_line
        cmp     word [statusBuf], 'UR'
        je      .url_line
        cmp     word [statusBuf], 'Ta'
        je      .tags_line

        ; Normal paragraph line: strip leading '| ' if present
.norm_para:
        lea     rcx, [statusBuf]
.strip_para_pipe:
        cmp     byte [rcx], ' '
        jne     @f
        inc     rcx
        jmp     .strip_para_pipe
@@:     cmp     byte [rcx], '|'
        jne     .para_ready
        inc     rcx
        cmp     byte [rcx], ' '
        jne     .para_ready
        inc     rcx
.para_ready:
        mov     edx, COLOR_TEXT_NORMAL
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 11
        xor     r11d, r11d
        call    RichAppendAnsi
        call    RichAppendNewline
        jmp     .line_loop

.meta_line:
        lea     rcx, [statusBuf]
        mov     edx, COLOR_TEXT_MUTED
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendAnsi
        call    RichAppendNewline
        jmp     .line_loop

.url_line:
        lea     rcx, [statusBuf]
        mov     edx, COLOR_IDENTIFIER
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendAnsi
        call    RichAppendNewline
        jmp     .line_loop

.tags_line:
        lea     rcx, [statusBuf]
        mov     edx, COLOR_KEYWORD
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 10
        xor     r11d, r11d
        call    RichAppendAnsi
        call    RichAppendTwoNewlines
        jmp     .line_loop

.done:
        ret
endp

; ------------------------------------------------------------------------------
; Question Selected in ListBox
; ------------------------------------------------------------------------------
proc OnQuestionSelected
        invoke  SendMessage, [hListQuestions], LB_GETCURSEL, 0, 0
        cmp     eax, -1
        je      .done

        invoke  SendMessage, [hListQuestions], LB_GETITEMDATA, rax, 0
        cmp     rax, -1
        je      .done
        mov     [selectedQIndex], rax

        cmp     [isLiveMode], 1
        jne     .offline_selected

        ; Live database item
        imul    rax, sizeof.LIVE_QUESTION
        lea     rsi, [liveDb + rax]

        lea     rax, [rsi + LIVE_QUESTION.szLink]
        mov     [currentLinkPtr], rax

        ; Display question details immediately with rich formatting
        lea     rcx, [rsi + LIVE_QUESTION.szDetails]
        call    RenderDetailsRich

        ; Check if answers should be fetched
        cmp     dword [rsi + LIVE_QUESTION.bAnsLoaded], 1
        je      .ans_already_loaded
        cmp     dword [rsi + LIVE_QUESTION.dwAnswers], 0
        jle     .ans_already_loaded

        mov     edx, [rsi + LIVE_QUESTION.dwId]
        test    edx, edx
        jz      .ans_already_loaded

        ; Call FetchLiveAnswer with shadow space for x64 ABI
        sub     rsp, 32
        mov     ecx, edx
        lea     rdx, [rsi + LIVE_QUESTION.szDetails]
        call    FetchLiveAnswer
        add     rsp, 32

        mov     rax, [selectedQIndex]
        imul    rax, sizeof.LIVE_QUESTION
        lea     rsi, [liveDb + rax]
        mov     dword [rsi + LIVE_QUESTION.bAnsLoaded], 1

        ; Update Details with Question + Answers in RichEdit
        lea     rcx, [rsi + LIVE_QUESTION.szDetails]
        call    RenderDetailsRich

.ans_already_loaded:
        invoke  SetWindowText, [hStatusBar], szStatusLoaded
        ret

.offline_selected:
        imul    rax, sizeof.QUESTION_ITEM
        lea     rsi, [qDatabase + rax]

        mov     rcx, [rsi + QUESTION_ITEM.pszDetails]
        call    RenderDetailsRich

        mov     rax, [rsi + QUESTION_ITEM.pszLink]
        mov     [currentLinkPtr], rax

        invoke  SetWindowText, [hStatusBar], szStatusLoaded
.done:
        ret
endp

; ------------------------------------------------------------------------------
; Offline Curated Database Search (Case-Insensitive across Title, Tags, Details)
; ------------------------------------------------------------------------------
proc ExecuteOfflineSearch uses rbx rsi rdi r12 r13 r14
        mov     [isLiveMode], 0
        invoke  SendMessage, [hListQuestions], LB_RESETCONTENT, 0, 0
        mov     [matchCount], 0

        mov     eax, [currentTab]
        mov     [targetLang], eax

        ; 1. Get search query string from edit box
        lea     rdx, [szSearchBuf]
        invoke  GetWindowText, [hEditSearch], rdx, 256

        ; Trim leading spaces
        lea     rsi, [szSearchBuf]
.trim_leading:
        cmp     byte [rsi], ' '
        jne     @f
        inc     rsi
        jmp     .trim_leading
@@:
        mov     r12, rsi                ; r12 = trimmed search query
        cmp     byte [r12], 0
        sete    r13b                    ; r13b = 1 if empty query

        xor     ebx, ebx

.loop_offline:
        cmp     ebx, TOTAL_QUESTIONS
        jge     .offline_done

        mov     rax, rbx
        imul    rax, sizeof.QUESTION_ITEM
        lea     r14, [qDatabase + rax]

        ; Check language tab
        mov     edx, [r14 + QUESTION_ITEM.dwLang]
        cmp     edx, [targetLang]
        jne     .next_offline

        ; If empty query, match all
        test    r13b, r13b
        jnz     .add_match

        ; Search in Title
        mov     rsi, [r14 + QUESTION_ITEM.pszTitle]
        mov     rdi, r12
        call    FindSubStrI
        test    rax, rax
        jnz     .add_match

        ; Search in Tags
        mov     rsi, [r14 + QUESTION_ITEM.pszTags]
        mov     rdi, r12
        call    FindSubStrI
        test    rax, rax
        jnz     .add_match

        ; Search in Details
        mov     rsi, [r14 + QUESTION_ITEM.pszDetails]
        mov     rdi, r12
        call    FindSubStrI
        test    rax, rax
        jnz     .add_match

        jmp     .next_offline

.add_match:
        mov     rax, [r14 + QUESTION_ITEM.pszTitle]
        invoke  SendMessage, [hListQuestions], LB_ADDSTRING, 0, rax
        mov     rdi, rax

        invoke  SendMessage, [hListQuestions], LB_SETITEMDATA, rdi, rbx
        inc     [matchCount]

.next_offline:
        inc     ebx
        jmp     .loop_offline

.offline_done:
        cmp     [matchCount], 0
        jle     .none

        invoke  SendMessage, [hListQuestions], LB_SETCURSEL, 0, 0
        call    OnQuestionSelected
        call    UpdateOfflineStatus
        ret

.none:
        mov     [selectedQIndex], -1
        invoke  SetWindowTextW, [hEditDetails], wszEmpty
        lea     rcx, [szNoMatchesDetails]
        mov     edx, COLOR_TEXT_MUTED
        xor     r8d, r8d
        lea     r9, [wszFontUI]
        mov     r10d, 12
        xor     r11d, r11d
        call    RichAppendAnsi
        invoke  SetWindowText, [hStatusBar], szStatusNoMatches
        ret
endp

; ------------------------------------------------------------------------------
; Update Offline Status Bar Result Count
; ------------------------------------------------------------------------------
proc UpdateOfflineStatus uses rsi rdi
        lea     rsi, [szSearchBuf]
.check_q:
        cmp     byte [rsi], ' '
        jne     @f
        inc     rsi
        jmp     .check_q
@@:     cmp     byte [rsi], 0
        jne     .show_match_count

        invoke  SetWindowText, [hStatusBar], szOfflineAllLoaded
        ret

.show_match_count:
        lea     rdi, [statusBuf]
        lea     rsi, [szOfflineStatusPrefix]
        call    StrCopy

        mov     eax, [matchCount]
        call    AppendNumber

        lea     rsi, [szOfflineStatusMid]
        call    StrCat

        lea     rsi, [szSearchBuf]
        call    StrCat

        lea     rsi, [szOfflineStatusEnd]
        call    StrCat

        lea     rdx, [statusBuf]
        invoke  SetWindowText, [hStatusBar], rdx
        ret
endp

; ------------------------------------------------------------------------------
; Update Status Bar Result Count & API Quota
; ------------------------------------------------------------------------------
proc UpdateStatusCount
        lea     rdi, [statusBuf]
        lea     rsi, [szFoundPrefix]
        call    StrCopy

        mov     eax, [matchCount]
        call    AppendNumber

        lea     rsi, [szFoundMid]
        call    StrCat

        lea     rsi, [szSearchBuf]
        call    StrCat

        lea     rsi, [szQuotaPrefix]
        call    StrCat

        mov     eax, [quotaRemaining]
        call    AppendNumber

        lea     rsi, [szQuotaSuffix]
        call    StrCat

        invoke  SetWindowText, [hStatusBar], statusBuf
        ret
endp
