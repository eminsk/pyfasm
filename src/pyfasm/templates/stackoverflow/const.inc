; ==============================================================================
; Stack Overflow Search Pro (FASM x64) - Constants & Definitions
; Modular component: const.inc
; ==============================================================================

RT_ICON             = 3
RT_GROUP_ICON       = 14
RT_MANIFEST         = 24
LANG_NEUTRAL        = 0

WM_SETICON          = 0080h
ICON_SMALL          = 0
ICON_BIG            = 1
IMAGE_ICON          = 1
LR_DEFAULTSIZE      = 0040h
LR_SHARED           = 8000h

WM_CTLCOLORMSGBOX   = 0132h
WM_CTLCOLOREDIT     = 0133h
WM_CTLCOLORLISTBOX  = 0134h
WM_CTLCOLORBTN      = 0135h
WM_CTLCOLORDLG      = 0136h
WM_CTLCOLORSTATIC   = 0138h
WM_DRAWITEM         = 002Bh
WM_SETFONT          = 0030h

ODS_SELECTED        = 0001h
ODS_DISABLED        = 0004h
ODS_FOCUS           = 0010h

LBN_SELCHANGE       = 1
LB_ADDSTRING        = 0180h
LB_RESETCONTENT     = 0184h
LB_GETCURSEL        = 0188h
LB_SETCURSEL        = 0186h
LB_GETTEXT          = 0189h
LB_GETITEMDATA      = 0199h
LB_SETITEMDATA      = 019Ah
LB_SETITEMHEIGHT    = 01A0h

LBS_NOTIFY          = 0001h
LBS_OWNERDRAWFIXED  = 0010h
LBS_HASSTRINGS      = 0040h
LBS_NOINTEGRALHEIGHT= 0100h

DT_LEFT             = 0000h
DT_CENTER           = 0001h
DT_RIGHT            = 0002h
DT_VCENTER          = 0004h
DT_WORDBREAK        = 0010h
DT_SINGLELINE       = 0020h
DT_NOPREFIX         = 0800h
DT_END_ELLIPSIS     = 8000h

DWMWA_USE_IMMERSIVE_DARK_MODE    = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_10 = 19

CF_TEXT             = 1
GMEM_MOVEABLE       = 2

; ------------------------------------------------------------------------------
; Control IDs
; ------------------------------------------------------------------------------
IDC_BADGE_LOGO      = 2001
IDC_EDIT_SEARCH     = 2002
IDC_BTN_SEARCH      = 2003
IDC_BTN_CLEAR       = 2004
IDC_BTN_LIVE_API    = 2011

; Quick Topic Chips (9 Chips)
IDC_CHIP_PYTHON     = 2101
IDC_CHIP_JS         = 2102
IDC_CHIP_ASYNCIO    = 2103
IDC_CHIP_FASTAPI    = 2104
IDC_CHIP_RUST       = 2105
IDC_CHIP_CPP        = 2106
IDC_CHIP_DOCKER     = 2107
IDC_CHIP_REACT      = 2108
IDC_CHIP_PANDAS     = 2109

; Modern Segmented Tab Buttons
IDC_TAB_EN          = 2201
IDC_TAB_RU          = 2202
IDC_TAB_BM          = 2203
IDC_TAB_INFO        = 2204

; Action Buttons Toolbar
IDC_BTN_COPY_Q      = 2007
IDC_BTN_COPY_A      = 2008
IDC_BTN_BOOKMARK    = 2010
IDC_BTN_BROWSER     = 2009

; Content Controls
IDC_LIST_QUESTIONS  = 2005
IDC_EDIT_DETAILS    = 2006
IDC_STATUS_BAR      = 2012

; ------------------------------------------------------------------------------
; Color Palette Constants (BGR format for Win32 GDI)
; ------------------------------------------------------------------------------
COLOR_DEEP_DARK_BG  = 0017110Eh     ; #0E1117
COLOR_PANEL_SURFACE = 00261B16h     ; #161B26
COLOR_CARD_BG       = 002C201Ah     ; #1A202C
COLOR_INPUT_BG      = 00221611h     ; #111622
COLOR_SO_ORANGE     = 002480F4h     ; #F48024 Stack Overflow Orange
COLOR_SO_ORANGE_BRD = 003C92FBh
COLOR_BLUE_BTN      = 00EB6325h     ; #2563EB
COLOR_BLUE_BORDER   = 00F6823Bh
COLOR_EMERALD_BTN   = 00699605h     ; #059669
COLOR_EMERALD_BORDER= 0081B910h
COLOR_AMBER_BTN     = 000677D9h     ; #D97706
COLOR_AMBER_BORDER  = 000B9EF5h
COLOR_INDIGO_BTN    = 00E5464Fh     ; #4F46E5
COLOR_INDIGO_BORDER = 00F16663h

; ------------------------------------------------------------------------------
; Structures
; ------------------------------------------------------------------------------
struct QUESTION_ITEM
  dwId        dd ?
  dwLang      dd ?          ; 0 = English, 1 = Russian
  dwScore     dd ?
  dwAnswers   dd ?
  bAccepted   dd ?          ; 1 = Accepted solution exists
  dwViews     dd ?
  pszTitle    dq ?          ; Pointer to title string
  pszTags     dq ?          ; Pointer to tags string
  pszAuthor   dq ?          ; Pointer to author string
  pszLink     dq ?          ; Pointer to URL string
  pszDetails  dq ?          ; Pointer to formatted full question & answer body
ends

MAX_LIVE_ITEMS = 30
struct LIVE_QUESTION
  dwId        dd ?
  dwScore     dd ?
  dwAnswers   dd ?
  dwViews     dd ?
  bAnswered   dd ?
  bAnsLoaded  dd ?
  szTitle     rb 512
  szTags      rb 256
  szAuthor    rb 128
  szLink      rb 1024
  szDetails   rb 16384
ends

; ------------------------------------------------------------------------------
; RichEdit 4.1 / 5.0 Equates & Constants
; ------------------------------------------------------------------------------
EM_SETBKGNDCOLOR    = 0443h
EM_EXSETSEL         = 0437h
EM_SETCHARFORMAT    = 0444h
EM_REPLACESEL       = 00C2h
SCF_SELECTION       = 0001h

CFM_BOLD            = 00000001h
CFM_WEIGHT          = 00400000h
CFM_SIZE            = 80000000h
CFM_COLOR           = 40000000h
CFM_FACE            = 20000000h
CFM_BACKCOLOR       = 04000000h

CFE_BOLD            = 00000001h
CFE_AUTOBACKCOLOR   = 04000000h

COLOR_RICH_BG       = 00190F0Bh   ; #0B0F19 Dark background
COLOR_CODE_BG       = 002B1B13h   ; #131B2B Dark navy code block background
COLOR_CODE_HDR_BG   = 003B291Eh   ; #1E293B Slate header background
COLOR_ACC_BG        = 003B4E06h   ; #064E3B Emerald green accepted solution background
COLOR_CODE_BORDER   = 00F8BD38h   ; #38BDF8 Sky blue accent bar
COLOR_CODE_LINE     = 0064748Bh   ; #64748B Slate muted line
COLOR_KEYWORD       = 00FAA560h   ; #60A5FA Keyword blue
COLOR_STRING        = 0024BFFBh   ; #FBBF24 String amber/yellow
COLOR_COMMENT       = 00B7E76Eh   ; #6EE7B7 Comment emerald
COLOR_IDENTIFIER    = 00F8BD38h   ; #38BDF8 Cyan
COLOR_TEXT_WHITE    = 00FFFFFFh
COLOR_TEXT_NORMAL   = 00F0E8E2h   ; #E2E8F0
COLOR_TEXT_MUTED    = 00B8A394h   ; #94A3B8
COLOR_ACC_TEXT      = 0099D334h   ; #34D399

struct CHARRANGE
  cpMin       dd ?
  cpMax       dd ?
ends

struct CHARFORMAT2W
  cbSize          dd ?
  dwMask          dd ?
  dwEffects       dd ?
  yHeight         dd ?
  yOffset         dd ?
  crTextColor     dd ?
  bCharSet        db ?
  bPitchAndFamily db ?
  szFaceName      rw 32
  wWeight         dw ?
  sSpacing        dw ?
  wPad1           dw ?
  crBackColor     dd ?
  lcid            dd ?
  dwCookie        dd ?
  sStyle          dw ?
  wKerning        dw ?
  bUnderlineType  db ?
  bAnimation      db ?
  bRevAuthor      db ?
  bReserved1      db ?
ends

