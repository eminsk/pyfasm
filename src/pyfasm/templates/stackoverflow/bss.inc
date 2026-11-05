; ==============================================================================
; Stack Overflow Search Pro (FASM x64) - Uninitialized Variables & Buffers
; Modular component: bss.inc
; ==============================================================================

  align 16
  hInstance       dq ?
  hMainWnd        dq ?

  hBrushWin       dq ?
  hBrushPanel     dq ?
  hBrushCard      dq ?
  hBrushInput     dq ?

  hFontUI         dq ?
  hFontBold       dq ?
  hFontBadge      dq ?
  hFontTitle      dq ?
  hFontMono       dq ?

  hLogoBadge      dq ?
  hLblLogo        dq ?
  hEditSearch     dq ?
  hBtnSearch      dq ?
  hBtnClear       dq ?
  hBtnLiveApi     dq ?
  hListQuestions  dq ?
  hEditDetails    dq ?
  hMsfteditDll    dq ?

  align 16
  cf              CHARFORMAT2W
  cr              CHARRANGE
  wstrBuf         rw 32768
  wWordBuf        rw 512

  ; Chips Handles
  hChipPy         dq ?
  hChipJs         dq ?
  hChipAsync      dq ?
  hChipFast       dq ?
  hChipRs         dq ?
  hChipCpp        dq ?
  hChipDock       dq ?
  hChipReact      dq ?
  hChipPandas     dq ?

  dwDarkVal       dd 1

  ; Modern Tab Button Handles
  hTabEN          dq ?
  hTabRU          dq ?
  hTabBM          dq ?
  hTabInfo        dq ?

  ; Action Buttons
  hBtnCopyQ       dq ?
  hBtnCopyA       dq ?
  hBtnBookmark    dq ?
  hBtnBrowser     dq ?
  hStatusBar      dq ?

  hClipboardMem   dq ?
  hBmFile         dq ?
  bytesWritten    dd ?
  dwLength        dd ?

  currentTab      dd 1          ; Start on Russian tab (matches user screenshot)
  targetLang      dd 1
  matchCount      dd 0
  isLiveMode      dd 1
  quotaRemaining  dd 280
  selectedQIndex  dq -1
  currentLinkPtr  dq 0

  winW            dd ?
  winH            dd ?
  listW           dd ?
  detailsW        dd ?
  detailsX        dd ?
  panelH          dd ?

  msg             MSG
  wc              WNDCLASSEX sizeof.WNDCLASSEX, 0, WindowProc, 0, 0, NULL, NULL, NULL, COLOR_BTNFACE + 1, NULL, szClassName, NULL
  icc             INITCOMMONCONTROLSEX
  rcClient        RECT
  psPaint         rb 72

  ; Network buffers
  align 16
  hInternet       dq ?
  hUrl            dq ?
  bytesRead       dd ?
  itemIdx         dd ?
  pItem           dq ?
  pTitleKey       dq ?
  pItemStart      dq ?
  pItemEnd        dq ?
  pAfterTitle     dq ?
  savedChar       db ?

  szSearchBuf     rb 256
  apiUrlBuf       rb 1024
  statusBuf       rb 512
  numBuf          rb 32
  ansAuthorBuf    rb 128
  itemDisplayBuf  rb 512
  utf8Tmp         rb 32768
  wideTmp         rw 32768

  ; 128 KB Net Buffer for JSON response
  align 16
  netBuffer       rb 131072
  ansNetBuf       rb 65536
  bodyTmp         rb 32768
  ansTmp          rb 32768

  pBodyKey        dq ?
  pQIdKey         dq ?
  currQId         dd ?
  currAnsCount    dd ?
  currScore       dd ?
  inCodeBlock     dd ?

  ; Array of 30 LIVE_QUESTION structures
  align 16
  liveDb          rb sizeof.LIVE_QUESTION * MAX_LIVE_ITEMS

  ; Code Snippet extraction buffers for 1-click clipboard copy
  align 16
  codeSnippetBuf  rb 65536
  hasCodeSnippet  dd ?
  pCodeSnippetCur dq ?
  padBuf          rb 128
