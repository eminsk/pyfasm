; ==============================================================================
; FASM Modern SDK - Syntax Highlighter Engine (x86-64)
; File: include/syntax_color.inc
; Multi-language keyword tokenizer & syntax colorizer for Rich Edit & GDI text
; ==============================================================================

TOKEN_KEYWORD           = 1
TOKEN_STRING            = 2
TOKEN_NUMBER            = 3
TOKEN_COMMENT           = 4
TOKEN_OPERATOR          = 5
TOKEN_IDENTIFIER        = 6

COLOR_SYNTAX_KEYWORD    = 00F7A6CBh     ; Mauve / Purple (#CBA6F7)
COLOR_SYNTAX_STRING     = 00A1E3A6h     ; Emerald Green (#A6E3A1)
COLOR_SYNTAX_NUMBER     = 0087B3FAh     ; Peach (#FAB387)
COLOR_SYNTAX_COMMENT    = 009C847Fh     ; Slate Gray (#7F849C)
COLOR_SYNTAX_DEFAULT    = 00F4D6CDh     ; Light Text (#CDD6F4)
