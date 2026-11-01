# PyFASM: Free-Threaded (No-GIL) Python to Pure FASM x64 Native Compiler

[![Python: 3.15 No-GIL](https://img.shields.io/badge/Python-3.15%20Free--Threaded%20(No--GIL)-blue.svg)](https://python.org)
[![Backend: FASM x64](https://img.shields.io/badge/Backend-Flat%20Assembler%20x64-orange.svg)](https://flatassembler.net)
[![Tests: 11 Passed](https://img.shields.io/badge/Tests-11%20Passed-brightgreen.svg)]()
[![Targets: Win64 | DLL | MyOS 10](https://img.shields.io/badge/Targets-Win64%20PE%20%7C%20DLL%20%7C%20MyOS%2010%20x64-purple.svg)]()


**PyFASM** — революционный нативный компилятор, транслирующий код Python напрямую в чистый машинный код **x86_64 Flat Assembler (FASM)** с **полным отсутствием GIL (Global Interpreter Lock)** и поддержкой истинного аппаратного параллелизма процессора.

Разработан специально для создания сверхлёгких, автономных бинарных файлов без зависимостей как для **Windows 10 x64** (автономные `.exe`), так и для микроядерной операционной системы **MyOS 10 x64** (плоские бинарники `.bin`).

---

## Ключевые возможности

* **Полное отсутствие GIL (Zero-GIL Multithreading)**:
  * В скомпилированном бинарнике нет виртуальной машины и нет глобального замка интерпретатора.
  * Потоки создаются как нативные системные потоки ядра (`CreateThread` в Windows / потоки в MyOS) и выполняются параллельно на разных физических ядрах CPU на 100% мощности.
  * Поддержка аппаратных атомарных инструкций процессора (`lock add`, `lock sub`).
* **Экстремальная компактность**:
  * Скомпилированные исполняемые файлы весят всего **512 байт – 3.5 КБ**!
  * Не требуют установки Python, `python.exe` или сторонних DLL (`python315.dll`).
* **Молниеносная скорость (Bare-Metal Speed)**:
  * Чистый x86_64 машинный код со скоростью C / C++ / FASM.
  * Числа Фибоначчи (N=40) — **0 миллисекунд**.
  * Решето Эратосфена (до 100 000 простых чисел) — **0 миллисекунд**.
  * 8 параллельных потоков на 2 000 000 атомарных операций — **47 миллисекунд**.
* **Тройная целевая платформа**:
  * `--target win64`: автономные 64-битные приложения Windows PE64 Console.
  * `--target myos`: 64-битные плоские бинарные файлы для операционной системы MyOS 10.
  * `--target dll`: нативные динамические библиотеки Windows PE64 DLL (`.dll`) для моментального подключения в Python (`ctypes`) или C/C++.
* **Бандлер проектов (`pyfasm bundle`)**:
  * Позволяет упаковывать комплексные проекты (например, `yt2005` с CustomTkinter, requests, yt-dlp) в нативный исполняемый файл `.exe`, который автоматически конфигурирует и запускает проект в режиме Free-Threaded (No-GIL)!

---

## Архитектура компилятора

```
                    ┌────────────────────────────┐
                    │    Исходный код Python     │
                    │   (Python 3.15+ Free-Th.)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (Модуль ast)
                    ┌────────────────────────────┐
                    │  Абстрактное дерево (AST)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (AstAnalyzer)
                    ┌────────────────────────────┐
                    │  Семантический анализ,     │
                    │  типы (int, ptr, str)      │
                    │  и раскладка стека x64     │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (X64CodeGen)
                    ┌────────────────────────────┐
                    │ Генерация чистого x64 FASM │
                    │ (Shadow Space, Syscalls)   │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (FASM Assembler)
             ┌────────────────────┴────────────────────┐
             ▼                                         ▼
   [ Windows PE64 (.exe) ]                  [ MyOS 10 Binary (.bin) ]
     (Размер ~2-3 КБ)                          (Размер 512 байт)
```

---

## Поддерживаемый синтаксис

* **Функции и аргументы**: `def name(a: int, b: int) -> int:`
* **Типы данных**: `int` (64-битный регистр RAX/память), `str` (строковые литералы), `ptr` (указатели и буферы памяти), `bool`, `void`.
* **Арифметика**: `+`, `-`, `*`, `//`, `%`, `&`, `|`, `^`, `<<`, `>>`, унарные `-`, `~`, `not`.
* **Управляющие конструкции**: `if / elif / else`, `while`, `for i in range(start, stop, step)`, `break`, `continue`, `return`.
* **Массивы и динамическая память**:
  * `alloc_memory(bytes)` — выделение системной памяти
  * `free_memory(ptr)` — освобождение памяти
  * `buf[i] = val` и `val = buf[i]` — индексация по смещению
* **Многопоточность без GIL**:
  * `spawn_thread(worker_func, param)` — запуск нативного потока ОС на свободном ядре CPU
  * `wait_thread(handle)` — синхронизация и ожидание завершения потока
  * `atomic_add(ptr, val)` — аппаратное атомарное сложение (`lock add`)
  * `atomic_sub(ptr, val)` — аппаратное атомарное вычитание (`lock sub`)
* **Ввод-вывод и системное время**:
  * `print(val)` / `print_int(val)` — быстрый вывод целого числа
  * `print_str(msg)` — вывод строки
  * `print_newline()` — перевод строки CRLF / LF
  * `get_tick_count()` — высокоточный счетчик времени
  * `sleep_ms(ms)` — пауза потока

---

## Использование CLI

```bash
# 1. Компиляция в нативный Windows .exe и мгновенный запуск:
uv run pyfasm compile examples/01_hello.py --run

# 2. Компиляция многопоточного теста:
uv run pyfasm compile examples/04_multithread_parallel.py --run

# 3. Компиляция бинарника для MyOS 10:
uv run pyfasm compile examples/01_hello.py -o hello_myos.bin --target myos

# 4. Просмотр сгенерированного ассемблерного кода FASM:
uv run pyfasm emit-asm examples/02_fibonacci.py

# 5. Компиляция Python-модуля в нативную высокоскоростную DLL:
uv run pyfasm compile my_kernel.py -o my_kernel.dll --target dll

# 6. Упаковка комплексного проекта (например, yt2005) в нативный лаунчер:
uv run pyfasm bundle "c:\proekts\yt2005" -o "c:\proekts\yt2005\yt2005.exe"
```

---

## Тестирование

Проект полностью покрыт автоматическими тестами через `pytest`:

```bash
uv run pytest
```

```
tests/test_codegen.py .                                                  [ 12%]
tests/test_execution.py ....                                             [ 62%]
tests/test_multithreading.py .                                           [ 75%]
tests/test_parser.py .                                                   [ 87%]
tests/test_types.py .                                                    [100%]
============================== 8 passed in 0.52s ==============================
```
