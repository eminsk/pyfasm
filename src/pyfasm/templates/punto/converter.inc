;============================================================================;
;                   PUNTO SWITCHER x64 — CONVERTER & RULES                   ;
;============================================================================;

include 'words.inc'

; Convert UTF-16 character from EN to RU
; RCX = character, Returns RAX = converted
CharToRu:
    cmp     rcx, 127
    ja      .keep
    movzx   rax, word [table_en_to_ru + rcx*2]
    test    rax, rax
    jz      .keep
    ret
.keep:
    mov     rax, rcx
    ret

; Convert UTF-16 character from RU to EN
; RCX = character, Returns RAX = converted
CharToEn:
    cmp     rcx, 0x0400
    jb      .check_special
    cmp     rcx, 0x045F
    ja      .keep
    sub     rcx, 0x0400
    movzx   rax, word [table_ru_to_en + rcx*2]
    test    rax, rax
    jz      .keep
    ret
.check_special:
    cmp     rcx, 0x2116     ; № -> #
    jne     .keep
    mov     rax, '#'
    ret
.keep:
    mov     rax, rcx
    ret

; Convert buffer of UTF-16 characters from EN to RU
; RCX = p_src, RDX = p_dst, R8 = count
ConvertBufferToRu:
    push    rbx
    push    rsi
    push    rdi
    mov     rsi, rcx
    mov     rdi, rdx
    mov     rbx, r8
.loop:
    test    rbx, rbx
    jz      .done
    movzx   rcx, word [rsi]
    call    CharToRu
    mov     word [rdi], ax
    add     rsi, 2
    add     rdi, 2
    dec     rbx
    jmp     .loop
.done:
    mov     word [rdi], 0
    pop     rdi
    pop     rsi
    pop     rbx
    ret

; Convert buffer of UTF-16 characters from RU to EN
; RCX = p_src, RDX = p_dst, R8 = count
ConvertBufferToEn:
    push    rbx
    push    rsi
    push    rdi
    mov     rsi, rcx
    mov     rdi, rdx
    mov     rbx, r8
.loop:
    test    rbx, rbx
    jz      .done
    movzx   rcx, word [rsi]
    call    CharToEn
    mov     word [rdi], ax
    add     rsi, 2
    add     rdi, 2
    dec     rbx
    jmp     .loop
.done:
    mov     word [rdi], 0
    pop     rdi
    pop     rsi
    pop     rbx
    ret

; Convert UTF-16 character to lowercase
; RCX = character, Returns RAX = lowercase
CharToLower:
    mov     rax, rcx
    cmp     rax, 'A'
    jb      .check_ru
    cmp     rax, 'Z'
    ja      .check_ru
    add     rax, 32
    ret
.check_ru:
    cmp     rax, 0x0410
    jb      .check_yo
    cmp     rax, 0x042F
    ja      .check_yo
    add     rax, 32
    ret
.check_yo:
    cmp     rax, 0x0401     ; Ё -> ё
    jne     .done
    mov     rax, 0x0451
.done:
    ret

; Convert buffer of UTF-16 characters to lowercase
; RCX = p_src, RDX = p_dst, R8 = count
ConvertBufferToLower:
    push    rbx
    push    rsi
    push    rdi
    mov     rsi, rcx
    mov     rdi, rdx
    mov     rbx, r8
.loop:
    test    rbx, rbx
    jz      .done
    movzx   rcx, word [rsi]
    call    CharToLower
    mov     word [rdi], ax
    add     rsi, 2
    add     rdi, 2
    dec     rbx
    jmp     .loop
.done:
    mov     word [rdi], 0
    pop     rdi
    pop     rsi
    pop     rbx
    ret

; Check if character is a Russian vowel (аеёиоуыэюя)
; RCX = character, Returns RAX = 1/0
IsRuVowel:
    cmp     rcx, 0x0430     ; а
    je      .yes
    cmp     rcx, 0x0435     ; е
    je      .yes
    cmp     rcx, 0x0451     ; ё
    je      .yes
    cmp     rcx, 0x0438     ; и
    je      .yes
    cmp     rcx, 0x043E     ; о
    je      .yes
    cmp     rcx, 0x0443     ; у
    je      .yes
    cmp     rcx, 0x044B     ; ы
    je      .yes
    cmp     rcx, 0x044D     ; э
    je      .yes
    cmp     rcx, 0x044E     ; ю
    je      .yes
    cmp     rcx, 0x044F     ; я
    je      .yes
    xor     eax, eax
    ret
.yes:
    mov     eax, 1
    ret

; Check if character is an English vowel (aeiouy)
; RCX = character, Returns RAX = 1/0
IsEnVowel:
    cmp     rcx, 'a'
    je      .yes
    cmp     rcx, 'e'
    je      .yes
    cmp     rcx, 'i'
    je      .yes
    cmp     rcx, 'o'
    je      .yes
    cmp     rcx, 'u'
    je      .yes
    cmp     rcx, 'y'
    je      .yes
    xor     eax, eax
    ret
.yes:
    mov     eax, 1
    ret

; Check if null-terminated lowercase UTF-16 word matches any entry in dict_ptr
; RCX = p_str, RDX = dict_ptr
; Returns RAX = 1 if found, 0 if not
IsInDictionary:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13

    mov     r12, rcx
    mov     r13, rdx

.word_loop:
    cmp     word [r13], 0xFFFF
    je      .not_found

    mov     rsi, r12
    mov     rdi, r13
.char_loop:
    movzx   eax, word [rsi]
    movzx   ebx, word [rdi]
    cmp     eax, ebx
    jne     .next_word
    test    eax, eax
    jz      .found              ; Match!
    add     rsi, 2
    add     rdi, 2
    jmp     .char_loop

.next_word:
.skip_loop:
    cmp     word [r13], 0
    jz      .past_null
    add     r13, 2
    jmp     .skip_loop
.past_null:
    add     r13, 2
    jmp     .word_loop

.found:
    mov     eax, 1
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret

.not_found:
    xor     eax, eax
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Check if Russian word is impossible according to Russian phonotactics
; RCX = p_chars, RDX = count
; Returns RAX = 1 if impossible, 0 if valid
IsImpossibleRussian:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13

    mov     rsi, rcx
    mov     r12, rdx
    test    r12, r12
    jz      .valid

    ; 1. Cannot start with ь (0x044C), ъ (0x044A), ы (0x044B)
    movzx   rcx, word [rsi]
    call    CharToLower
    cmp     rax, 0x044C     ; ь
    je      .impossible
    cmp     rax, 0x044A     ; ъ
    je      .impossible
    cmp     rax, 0x044B     ; ы
    je      .impossible

    ; Loop through characters
    xor     rbx, rbx
.loop:
    cmp     rbx, r12
    jae     .valid

    movzx   rcx, word [rsi + rbx*2]
    call    CharToLower
    mov     r13, rax        ; current char

    ; Check 'ъ': only allowed before е, ё, ю, я
    cmp     r13, 0x044A     ; ъ
    jne     .check_y
    lea     rax, [rbx + 1]
    cmp     rax, r12
    jae     .impossible     ; ъ at end of word
    movzx   rcx, word [rsi + rax*2]
    call    CharToLower
    cmp     rax, 0x0435     ; е
    je      .next
    cmp     rax, 0x0451     ; ё
    je      .next
    cmp     rax, 0x044E     ; ю
    je      .next
    cmp     rax, 0x044F     ; я
    je      .next
    jmp     .impossible

.check_y:
    ; Check 'ы': cannot follow another vowel or precede another vowel
    cmp     r13, 0x044B     ; ы
    jne     .check_soft
    test    rbx, rbx
    jz      .impossible
    movzx   rcx, word [rsi + (rbx-1)*2]
    call    CharToLower
    mov     rcx, rax
    call    IsRuVowel
    test    eax, eax
    jnz     .impossible

    lea     rax, [rbx + 1]
    cmp     rax, r12
    jae     .check_soft
    movzx   rcx, word [rsi + rax*2]
    call    CharToLower
    mov     rcx, rax
    call    IsRuVowel
    test    eax, eax
    jnz     .impossible

.check_soft:
    ; Check 'ь': cannot precede forbidden vowels (ы, э, у)
    cmp     r13, 0x044C     ; ь
    jne     .check_shch
    lea     rax, [rbx + 1]
    cmp     rax, r12
    jae     .next
    movzx   rcx, word [rsi + rax*2]
    call    CharToLower
    cmp     rax, 0x044B     ; ы
    je      .impossible
    cmp     rax, 0x044D     ; э
    je      .impossible
    cmp     rax, 0x0443     ; у
    je      .impossible

.check_shch:
    ; Check 'щ': cannot precede forbidden consonants (г, к, д, т, м, п, в, с, б, ж, з, х, ц, ч, ш)
    cmp     r13, 0x0449     ; щ
    jne     .check_f
    lea     rax, [rbx + 1]
    cmp     rax, r12
    jae     .next
    movzx   rcx, word [rsi + rax*2]
    call    CharToLower
    cmp     rax, 0x0433     ; г
    je      .impossible
    cmp     rax, 0x043A     ; к
    je      .impossible
    cmp     rax, 0x0434     ; д
    je      .impossible
    cmp     rax, 0x0442     ; т
    je      .impossible
    cmp     rax, 0x043C     ; м
    je      .impossible
    cmp     rax, 0x043F     ; п
    je      .impossible
    cmp     rax, 0x0432     ; в
    je      .impossible
    cmp     rax, 0x0441     ; с
    je      .impossible

.check_f:
    ; Check 'ф' before k, t, d, m, l, s, p, b
    cmp     r13, 0x0444     ; ф
    jne     .check_bigrams
    lea     rax, [rbx + 1]
    cmp     rax, r12
    jae     .next
    movzx   rcx, word [rsi + rax*2]
    call    CharToLower
    cmp     rax, 0x043A     ; к (фк)
    je      .impossible
    cmp     rax, 0x0442     ; т (фт)
    je      .impossible
    cmp     rax, 0x0434     ; д (фд)
    je      .impossible
    cmp     rax, 0x043C     ; м (фм)
    je      .impossible
    cmp     rax, 0x043B     ; л (фл)
    je      .impossible
    cmp     rax, 0x0441     ; с (фс)
    je      .impossible

.check_bigrams:
    ; Impossible Russian bigrams: цщ, щц, дш, цш, чщ, щч, жш, шж, цг
    lea     rax, [rbx + 1]
    cmp     rax, r12
    jae     .check_triple
    movzx   rcx, word [rsi + rax*2]
    call    CharToLower
    mov     rdi, rax        ; next char

    cmp     r13, 0x0446     ; ц
    jne     .bg_shch
    cmp     rdi, 0x0449     ; цщ
    je      .impossible
    cmp     rdi, 0x0448     ; цш
    je      .impossible
    cmp     rdi, 0x0433     ; цг
    je      .impossible

.bg_shch:
    cmp     r13, 0x0449     ; щ
    jne     .bg_d
    cmp     rdi, 0x0446     ; щц
    je      .impossible
    cmp     rdi, 0x0447     ; щч
    je      .impossible

.bg_d:
    cmp     r13, 0x0434     ; д
    jne     .check_triple
    cmp     rdi, 0x0448     ; дш
    je      .impossible

.check_triple:
    lea     rax, [rbx + 2]
    cmp     rax, r12
    jae     .next
    movzx   rcx, word [rsi + (rbx+1)*2]
    call    CharToLower
    cmp     rax, r13
    jne     .next
    movzx   rcx, word [rsi + (rbx+2)*2]
    call    CharToLower
    cmp     rax, r13
    je      .impossible

.next:
    inc     rbx
    jmp     .loop

.impossible:
    mov     eax, 1
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret

.valid:
    xor     eax, eax
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; Check if English word is impossible according to English phonotactics
; RCX = p_chars, RDX = count
; Returns RAX = 1 if impossible, 0 if valid
IsImpossibleEnglish:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13

    mov     rsi, rcx
    mov     r12, rdx
    cmp     r12, 2
    jb      .valid

    ; Get first and second char
    movzx   rcx, word [rsi]
    call    CharToLower
    mov     r13, rax        ; char 0
    movzx   rcx, word [rsi + 2]
    call    CharToLower
    mov     rdi, rax        ; char 1

    ; 1. Impossible start with 'j' preceded by consonant
    cmp     rdi, 'j'
    jne     .check_starts
    cmp     r13, 'a'
    jb      .check_starts
    cmp     r13, 'z'
    ja      .check_starts
    cmp     r13, 'a'
    je      .check_starts
    cmp     r13, 'e'
    je      .check_starts
    cmp     r13, 'i'
    je      .check_starts
    cmp     r13, 'o'
    je      .check_starts
    cmp     r13, 'u'
    je      .check_starts
    jmp     .impossible

.check_starts:
    ; Impossible Russian-typed starts in English:
    ; xn, xt, xe, xh, xf, xb (чт, чт, че, чер, час, чи)
    cmp     r13, 'x'
    jne     .check_dc
    cmp     rdi, 'n'
    je      .impossible
    cmp     rdi, 't'
    je      .impossible
    cmp     rdi, 'e'
    je      .impossible
    cmp     rdi, 'h'
    je      .impossible
    cmp     rdi, 'f'
    je      .impossible
    cmp     rdi, 'b'
    je      .impossible

.check_dc:
    ; dc (все), yt (нет), rf (как), lt (дел), cg (сп)
    cmp     r13, 'd'
    jne     .check_yt
    cmp     rdi, 'c'
    je      .impossible
    cmp     rdi, 't'
    je      .impossible
    cmp     rdi, 'f'
    je      .impossible

.check_yt:
    cmp     r13, 'y'
    jne     .check_rf
    cmp     rdi, 't'
    je      .impossible
    cmp     rdi, 'f'
    je      .impossible
    cmp     rdi, 'b'
    je      .impossible

.check_rf:
    cmp     r13, 'r'
    jne     .check_lt
    cmp     rdi, 'f'
    je      .impossible
    cmp     rdi, 'n'
    je      .impossible

.check_lt:
    cmp     r13, 'l'
    jne     .check_cg
    cmp     rdi, 't'
    je      .impossible
    cmp     rdi, 'd'
    je      .impossible

.check_cg:
    cmp     r13, 'c'
    jne     .check_bk
    cmp     rdi, 'g'
    je      .impossible
    cmp     rdi, 'f'
    je      .impossible
    cmp     rdi, 'b'
    je      .impossible
    cmp     rdi, 'd'
    je      .impossible

.check_bk:
    ; bk, dk, fk, gk, hk, jk, pk, tk, vk, zk
    cmp     rdi, 'k'
    jne     .check_q_start
    cmp     r13, 'b'
    je      .impossible
    cmp     r13, 'd'
    je      .impossible
    cmp     r13, 'f'
    je      .impossible
    cmp     r13, 'g'
    je      .impossible
    cmp     r13, 'h'
    je      .impossible
    cmp     r13, 'j'
    je      .impossible
    cmp     r13, 'p'
    je      .impossible
    cmp     r13, 't'
    je      .impossible
    cmp     r13, 'v'
    je      .impossible
    cmp     r13, 'z'
    je      .impossible

.check_q_start:
    ; 'q' not followed by 'u'
    cmp     r13, 'q'
    jne     .check_gh
    cmp     rdi, 'u'
    jne     .impossible

.check_gh:
    ; 'gh' followed by b, j, f, y, z, u, w, k, l, v, d, s
    cmp     r13, 'g'
    jne     .check_vowels
    cmp     rdi, 'h'
    jne     .check_vowels
    cmp     r12, 3
    jb      .check_vowels
    movzx   rcx, word [rsi + 4]
    call    CharToLower
    cmp     rax, 'b'
    je      .impossible
    cmp     rax, 'j'
    je      .impossible
    cmp     rax, 'f'
    je      .impossible
    cmp     rax, 'd'
    je      .impossible
    cmp     rax, 's'
    je      .impossible
    cmp     rax, 'v'
    je      .impossible

.check_vowels:
    ; If word >= 3 letters and has 0 vowels (aeiouy) -> impossible
    cmp     r12, 3
    jb      .valid
    xor     rbx, rbx
    xor     edi, edi        ; vowel count
.vowel_loop:
    cmp     rbx, r12
    jae     .vowel_done
    movzx   rcx, word [rsi + rbx*2]
    call    CharToLower
    mov     rcx, rax
    call    IsEnVowel
    add     edi, eax
    inc     rbx
    jmp     .vowel_loop
.vowel_done:
    test    edi, edi
    jz      .impossible

.valid:
    xor     eax, eax
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret

.impossible:
    mov     eax, 1
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret


; High-level word analyzer
; RCX = p_chars, RDX = count, R8 = cur_layout (0=EN, 1=RU)
; Returns RAX = 1 (convert) / 0 (no convert)
AnalyzeWord:
    push    rbx
    push    rsi
    push    rdi
    push    r12
    push    r13

    mov     rsi, rcx        ; p_chars
    mov     r12, rdx        ; count
    mov     r13, r8         ; cur_layout
    cmp     r12, 2
    jb      .no_convert

    cmp     r13, 0
    jne     .ru_mode

    ; ---------------- EN MODE ----------------
    ; 1. Convert input to lowercase in temp_norm_buf
    mov     rcx, rsi
    lea     rdx, [temp_norm_buf]
    mov     r8, r12
    call    ConvertBufferToLower

    ; 2. If it is already in English dictionary -> DO NOT CONVERT
    lea     rcx, [temp_norm_buf]
    lea     rdx, [dict_en_words]
    call    IsInDictionary
    test    eax, eax
    jnz     .no_convert

    ; 3. Convert lowercase to Russian in temp_word_buf
    lea     rcx, [temp_norm_buf]
    lea     rdx, [temp_word_buf]
    mov     r8, r12
    call    ConvertBufferToRu

    ; 4. If Russian version is in Russian dictionary -> CONVERT!
    lea     rcx, [temp_word_buf]
    lea     rdx, [dict_ru_words]
    call    IsInDictionary
    test    eax, eax
    jnz     .convert_yes

    ; 5. Check if English string is impossible English
    lea     rcx, [temp_norm_buf]
    mov     rdx, r12
    call    IsImpossibleEnglish
    test    eax, eax
    jz      .en_check_special

    ; If impossible English, ensure RU version is not impossible Russian
    lea     rcx, [temp_word_buf]
    mov     rdx, r12
    call    IsImpossibleRussian
    test    eax, eax
    jnz     .no_convert
    jmp     .convert_yes

.en_check_special:
    ; Check if word contains special layout keys ([, ], ;, ', ,, ., `)
    xor     rbx, rbx
.spec_loop:
    cmp     rbx, r12
    jae     .no_convert
    movzx   eax, word [rsi + rbx*2]
    cmp     eax, '['
    je      .spec_found
    cmp     eax, ']'
    je      .spec_found
    cmp     eax, ';'
    je      .spec_found
    cmp     eax, "'"
    je      .spec_found
    cmp     eax, ','
    je      .spec_found
    cmp     eax, '.'
    je      .spec_found
    cmp     eax, '`'
    je      .spec_found
    inc     rbx
    jmp     .spec_loop
.spec_found:
    lea     rcx, [temp_word_buf]
    mov     rdx, r12
    call    IsImpossibleRussian
    test    eax, eax
    jnz     .no_convert
    jmp     .convert_yes

    ; ---------------- RU MODE ----------------
.ru_mode:
    ; 1. Convert input to lowercase in temp_norm_buf
    mov     rcx, rsi
    lea     rdx, [temp_norm_buf]
    mov     r8, r12
    call    ConvertBufferToLower

    ; 2. If it is already in Russian dictionary -> DO NOT CONVERT
    lea     rcx, [temp_norm_buf]
    lea     rdx, [dict_ru_words]
    call    IsInDictionary
    test    eax, eax
    jnz     .no_convert

    ; 3. Convert lowercase to English in temp_word_buf
    lea     rcx, [temp_norm_buf]
    lea     rdx, [temp_word_buf]
    mov     r8, r12
    call    ConvertBufferToEn

    ; 4. If English version is in English dictionary -> CONVERT!
    lea     rcx, [temp_word_buf]
    lea     rdx, [dict_en_words]
    call    IsInDictionary
    test    eax, eax
    jnz     .convert_yes

    ; 5. Check if Russian string is impossible Russian
    lea     rcx, [temp_norm_buf]
    mov     rdx, r12
    call    IsImpossibleRussian
    test    eax, eax
    jz      .no_convert

    ; Ensure EN version is not impossible English
    lea     rcx, [temp_word_buf]
    mov     rdx, r12
    call    IsImpossibleEnglish
    test    eax, eax
    jnz     .no_convert
    jmp     .convert_yes

.convert_yes:
    mov     eax, 1
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret

.no_convert:
    xor     eax, eax
    pop     r13
    pop     r12
    pop     rdi
    pop     rsi
    pop     rbx
    ret
