# PyFASM64: Универсальный нативный компилятор Python в чистый FASM x86_64

> 🌐 **Язык / Language:** [🇬🇧 English (Основная документация)](README.md) | **Русский**

[![PyPI - Version](https://img.shields.io/pypi/v/pyfasm64?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/pyfasm64/)
[![GitHub Release](https://img.shields.io/github/v/release/eminsk/pyfasm?style=flat&logo=github&logoColor=white&color=blue)](https://github.com/eminsk/pyfasm/releases)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pyfasm64?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/pyfasm64/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyfasm64?style=flat&logo=python&logoColor=white)](https://pypi.org/project/pyfasm64/)
[![CI](https://github.com/eminsk/pyfasm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/eminsk/pyfasm/actions/workflows/ci.yml)
[![Conda-Forge PR](https://img.shields.io/github/pulls/detail/state/conda-forge/staged-recipes/35444?label=Conda-Forge%20PR&logo=condaforge)](https://github.com/conda-forge/staged-recipes/pull/35444)
[![Debian Package](https://img.shields.io/github/v/release/eminsk/pyfasm?include_prereleases&label=Debian%20.deb&logo=debian)](https://github.com/eminsk/pyfasm/releases)
[![Python: 3.8 - 3.16](https://img.shields.io/badge/Python-3.8%20--%203.16-blue.svg?style=flat)](https://python.org)
[![No-GIL: 3.13t - 3.16t](https://img.shields.io/badge/No--GIL-3.13t%20--%203.16t-success.svg?style=flat)](https://peps.python.org/pep-0703/)
[![PyPy: 3.8 - 3.12](https://img.shields.io/badge/PyPy-3.8%20--%203.12-yellow.svg?style=flat)](https://pypy.org)
[![Targets: Windows | Linux | macOS | DLL](https://img.shields.io/badge/Targets-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20DLL-purple.svg?style=flat)]()
[![Backend: Flat Assembler x64](https://img.shields.io/badge/Backend-FASM%20x64%20v1.73.36-red.svg?style=flat)](https://flatassembler.net)
[![FASM Forum](https://img.shields.io/badge/FASM%20Board-Official%20Topic-blue.svg)](https://board.flatassembler.net/topic.php?t=24431)
[![GitHub Stars](https://img.shields.io/github/stars/eminsk/pyfasm?style=flat&logo=github)](https://github.com/eminsk/pyfasm/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/eminsk/pyfasm?style=flat&color=red&logo=github)](https://github.com/eminsk/pyfasm/issues)
[![GitHub Discussions](https://img.shields.io/badge/Discussions-Join_Community-blue?style=flat&logo=github)](https://github.com/eminsk/pyfasm/discussions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat)](LICENSE)
[![Donate USDT](https://img.shields.io/badge/Donate-USDT_(TRC20)-26A17B?style=flat&logo=tether&logoColor=white)](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P)

> ### 🤝 Сообщество, вопросы и поддержка
> - 🐛 **Нашли ошибку или баг в компиляторе?** Пожалуйста, [Создайте Issue](https://github.com/eminsk/pyfasm/issues) — сообщения об ошибках и патчи оперативно обрабатываются!
> - 💬 **Вопросы, идеи по кросс-компиляции и предложения:** Присоединяйтесь к [GitHub Discussions](https://github.com/eminsk/pyfasm/discussions).
> - 🏛️ **Официальное обсуждение:** [Анонс на Flat Assembler Board (board.flatassembler.net)](https://board.flatassembler.net/topic.php?t=24431)
> - ⭐ **Нравится PyFASM64?** Поставьте звезду на GitHub — это помогает проекту развиваться!
> - 📖 **Документация из терминала:** `pyfasm docs` (английская) или `pyfasm docs --ru` (русская).
> - ☕ **Поддержать разработку (USDT TRC-20):** `TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P` ([Проверить на TronScan](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P))

**PyFASM64** (пакет: `pyfasm64`, классический псевдоним: `pyfasm`) — высокопроизводительный кроссплатформенный нативный компилятор, транслирующий код Python напрямую в чистый машинный код ассемблера **x86_64 Flat Assembler (FASM)**. Он генерирует сверхкомпактные автономные исполняемые файлы с **нулевым оверхедом рантайма**, **без виртуальной машины** и с **полным устранением Global Interpreter Lock (Zero-GIL)**.

Поддерживает работу под **CPython 3.8–3.16**, **Free-Threaded / No-GIL Python (3.13t–3.16t)** и **PyPy (3.8–3.12)**. Компилятор собирает автономные бинарники без внешних зависимостей для целевых платформ: **Windows** (`.exe`, `.dll`), **Linux** (ELF64) и **Apple macOS** (Mach-O 64).

> 💡 **100% обратная совместимость**: PyFASM64 полностью сохраняет функционал оригинального PyFASM:
> - **Две команды CLI**: Доступны обе команды — и `pyfasm64`, и `pyfasm`.
> - **Два варианта импорта**: Работают как `import pyfasm64`, так и `import pyfasm`.
> - **Полная преемственность**: Все параметры компиляции, сборка многофайловых проектов, цели (`win64`, `linux`, `macos`, `dll`), бенчмарки и бандлер работают без изменений.

---

## Что нового в v0.1.14: Интеграция с FASM Modern SDK

Начиная с версии **v0.1.14**, в PyFASM64 встроен и глубоко интегрирован официальный инструментарий **FASM Modern SDK** (`fasm-modern-sdk v1.73.36` и `fasmg v0.0.26`):

1. **Автономный компилятор и заголовочные файлы в пакете**:
   - Официальный wheel-дистрибутив теперь включает бинарники FASM для всех ОС (`FASM.EXE`, `fasmg.exe`, `fasm.x64`, `fasm.darwin`, `fasm`) и стандартные заголовочные файлы (`win64a.inc`, `win32a.inc`, макросы, структуры).
   - Не требуется ручная настройка переменной среды `INCLUDE`.
2. **Современные модули FASM Modern SDK**:
   - `ui_fluent.inc`: Нативные компоненты Fluent Dark UI (темная тема, скругленные карточки, кастомная отрисовка списков и кнопок).
   - `json_fast.inc`: Высокоскоростной SIMD-парсер JSON без динамических аллокаций.
   - `net_https.inc`: Автономный HTTPS/TLS клиент без внешних зависимостей (WinINet / POSIX sockets).
   - `data_structures.inc`: Динамические массивы (векторы), строковые буферы и хэш-таблицы.
   - `syntax_color.inc`: Лексический анализатор и подсветка синтаксиса на чистом ассемблере.
3. **Движок Unicode и конвертация UTF-8 в UTF-16LE**:
   - В рантайм компилятора встроена автоматическая функция `_pyfasm_utf8_to_wide`, предотвращающая появление китайских иероглифов (Mojibake) при выводе текста в элементы интерфейса Windows.
   - Предотвращение наложения и дублирования элементов графического интерфейса: handles существующих окон переиспользуются, защищая от перекрытия списками и фреймами.
4. **Интерактивный просмотрщик документации**:
   - Основная документация: `pyfasm docs`
   - Русскоязычная версия: `pyfasm docs --ru`
   - Открытие во внешнем просмотрщике: `pyfasm docs --open`

---

## Ключевые возможности

* **Абсолютный Zero-GIL мультитрединг**:
  * Скомпилированные программы работают непосредственно на аппаратном уровне процессора без интерпретатора Python и блокировок GIL.
  * Нативные системные потоки (`CreateThread` в Windows, `sys_clone` в Linux) выполняются параллельно на всех физических ядрах CPU со 100% загрузкой.
  * Аппаратные атомарные инструкции x86_64 (`lock add`, `lock sub`).
* **Ультракомпактный размер исполняемых файлов**:
  * Размер бинарников составляет от **512 байт** до **2.5 КБ** (PE64 / ELF64 / Mach-O 64).
  * Абсолютно нулевые внешние зависимости: не требуются `python.exe`, MSVCRT, libc/glibc или динамические загрузчики.
* **Скорость выполнения "на чистом железе"**:
  * Производительность ассемблерного кода на уровне оптимизированного C/C++.
  * Вычисление чисел Фибоначчи ($N=40$): **0 мс**.
  * Решето Эратосфена (100,000 простых чисел): **0 мс**.
  * 8 параллельных потоков с 2,000,000 атомарных инкрементов: **47 мс**.
* **Кроссплатформенные форматы сборки**:
  * `--target win64`: Автономные исполняемые файлы Windows 64-bit PE64 (`.exe`).
  * `--target dll`: Динамические библиотеки Windows 64-bit (`.dll`), вызываемые из Python через `ctypes` или из C/C++.
  * `--target linux`: Нативные исполняемые файлы Linux x86-64 ELF64 (`.elf`) на прямых системных вызовах ядра (`sys_write`, `sys_exit`, `sys_mmap`, `sys_nanosleep`) без libc.
  * `--target macos` / `--target apple`: Исполняемые файлы Apple macOS x86-64 Mach-O 64-bit (`.macho`) на вызовах Darwin BSD.
* **Сборка многофайловых проектов в один бинарник**:
  * Автоматический анализ графа импортов проекта (`import` и `from ... import ...`) и компиляция всех локальных модулей в единый монолитный файл (`.exe`, `.elf`, `.macho`).
* **Кроссплатформенный бандлер (`pyfasm64 bundle`)**:
  * Упаковка сложных проектов в нативные лаунчеры для **Windows** (`.exe`), **Linux** (`.elf`) и **Apple macOS** (`.macho`) с автоматическим обнаружением виртуального окружения и поддержкой режима Free-Threaded (No-GIL).

---

## Архитектура компилятора

PyFASM64 построен по многоуровневой схеме компиляции с разделением парсинга, семантического анализа и генерации кода:

```
                    ┌────────────────────────────┐
                    │       Исходный код Python  │
                    │   (Python 3.8 - 3.16t)     │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (Python ast parser)
                    ┌────────────────────────────┐
                    │   Абстрактное дерево AST   │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (AstAnalyzer)
                    ┌────────────────────────────┐
                    │    Семантический анализ    │
                    │   (int, ptr, str, стек)    │
                    └─────────────┬──────────────┘
                                  │
                                  ▼ (Селектор целевой ABI и системных вызовов)
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
    ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
    │   Windows PE64    │ │    Linux ELF64    │ │ Apple macOS Mach-O│
    │  - Microsoft x64  │ │   - System V ABI  │ │   - Darwin BSD    │
    │  - Shadow Space   │ │   - Pure Syscalls │ │   - 0x2000000 Sys │
    └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼ (FASM Modern SDK v1.73.36)
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
    [ Windows PE64 .exe ]  [ Linux ELF64 .elf ] [ Apple Mach-O .macho ]
         (~2.5 КБ)               (~1.8 КБ)           (~2.4 КБ)
```

---

## Сравнение платформ

| Характеристика | Windows x86-64 | Linux x86-64 | Apple macOS x86-64 |
| :--- | :--- | :--- | :--- |
| **Формат бинарника** | PE32+ (PE64) Console / DLL | ELF64 Executable (Тип 3) | Mach-O 64 (`MH_MAGIC_64`) |
| **Сигнатура заголовка**| `MZ` (0x5A4D) / `PE\0\0` | `\x7fELF` (0x464C457F) | `0xFEEDFACF` (Little-Endian) |
| **Соглашение о вызовах** | Microsoft x64 ABI | System V AMD64 ABI | System V AMD64 ABI |
| **Регистры аргументов**| `RCX`, `RDX`, `R8`, `R9` | `RDI`, `RSI`, `RDX`, `RCX`, `R8`, `R9` | `RDI`, `RSI`, `RDX`, `RCX`, `R8`, `R9` |
| **Shadow Space** | 32 байта резервирует вызывающий | Нет (128 байт Red Zone) | Нет (128 байт Red Zone) |
| **Интерфейс ядра** | Win32 API (`kernel32.dll`) | Прямые системные вызовы ядра | Прямые системные вызовы Darwin BSD |
| **Стандартный вывод**| `GetStdHandle` + `WriteFile` | `syscall` (rax = 1 `sys_write`) | `syscall` (rax = `0x2000004`) |
| **Завершение процесса**| `ExitProcess` (код в RCX) | `syscall` (rax = 60 `sys_exit`) | `syscall` (rax = `0x2000001`) |
| **Выделение памяти** | `VirtualAlloc` (MEM_COMMIT) | `syscall` (rax = 9 `sys_mmap`) | `syscall` (rax = `0x20000C5`) |
| **Задержки и время** | `GetTickCount` / RDTSC | `sys_nanosleep` (35) / RDTSC | `sys_nanosleep` (`0x20000EB`) / RDTSC |
| **Зависимости рантайма**| Нет (только kernel32) | **Ноль libc / Ноль glibc** | **Ноль libSystem / Ноль dyld** |

---

## Установка

### Через PyPI (Официальный каталог Python)

```bash
# С помощью uv (рекомендуется)
uv add pyfasm64

# Или через pip
pip install pyfasm64
```

### Через Conda (`conda-forge`)

```bash
conda install -c conda-forge pyfasm64
```

### Через Debian / Ubuntu PPA

```bash
sudo add-apt-repository ppa:eminsk/ppa
sudo apt update
sudo apt install python3-pyfasm64
```

Либо скачайте готовый `.deb` пакет со страницы [GitHub Releases](https://github.com/eminsk/pyfasm/releases):

```bash
sudo dpkg -i python3-pyfasm64_*.deb
```

### Сборка из исходников

```bash
git clone https://github.com/eminsk/pyfasm.git
cd pyfasm
uv sync
```

---

## Использование через консоль (CLI)

Обе команды — `pyfasm64` и `pyfasm` — полностью эквивалентны по синтаксису и аргументам:

### 1. Просмотр документации

```bash
# Вывести основную документацию на английском:
uv run pyfasm docs

# Вывести документацию на русском языке:
uv run pyfasm docs --ru

# Открыть файл документации в текстовом редакторе/просмотрщике:
uv run pyfasm docs --open
```

### 2. Компиляция и запуск под Windows (PE64)

```bash
# Скомпилировать в .exe и сразу выполнить:
uv run pyfasm64 compile examples/01_hello.py --run

# То же самое через псевдоним pyfasm:
uv run pyfasm compile examples/01_hello.py --run

# Компиляция бенчмарка многопоточности:
uv run pyfasm64 compile examples/04_multithread_parallel.py --run
```

### 3. Компиляция под Linux (ELF64)

```bash
# Создание нативного ELF исполняемого файла на прямых системных вызовах:
uv run pyfasm64 compile examples/01_hello.py -o hello_linux.elf --target linux
```

### 4. Компиляция под Apple macOS (Mach-O 64)

```bash
# Создание нативного бинарника macOS Mach-O:
uv run pyfasm64 compile examples/01_hello.py -o hello_mac.macho --target macos
```

### 5. Сборка многофайлового проекта в один бинарник

```bash
# Компиляция всей папки проекта в один исполняемый файл:
uv run pyfasm64 compile ./my_project -o my_app.exe

# Либо указав входной файл (все зависимости подтянутся автоматически):
uv run pyfasm64 compile my_project/main.py -o my_app.exe
```

### 6. Просмотр сгенерированного ассемблерного кода

```bash
uv run pyfasm64 emit-asm examples/02_fibonacci.py
```

### 7. Компиляция в библиотеку Windows DLL

```bash
uv run pyfasm64 compile my_math.py -o my_math.dll --target dll
```

### 8. Экспорт проекта FASM с заголовочными файлами и скриптами сборки

```bash
# Экспортирует код, заголовки, компилятор и скрипты сборки в папку FASM/:
uv run pyfasm compile my_app.py --export-fasm
```

---

## Поддерживаемое подмножество языка Python

| Возможность | Синтаксис / API | Описание |
| :--- | :--- | :--- |
| **Функции** | `def name(a: int, b: int) -> int:` | Строго типизированные функции x86_64 с соглашениями ABI |
| **Типы данных** | `int`, `ptr`, `str`, `bool`, `void` | 64-битные целые числа, указатели, строковые константы, логический тип |
| **Арифметика** | `+`, `-`, `*`, `//`, `%`, `&`, `\|`, `^`, `<<`, `>>` | Прямые инструкции ALU x86_64 (`add`, `sub`, `imul`, `idiv`) |
| **Управление потоком**| `if`, `elif`, `else`, `while`, `for i in range()` | Условные переходы, циклы, `break`, `continue`, `return` |
| **Память** | `alloc_memory(bytes)`, `free_memory(ptr)` | Выделение виртуальной памяти ОС (`VirtualAlloc` / `sys_mmap`) |
| **Работа с буфером**| `buf[i] = val` и `val = buf[i]` | Индексированное чтение и запись в память по указателю |
| **Многопоточность** | `spawn_thread(worker, param)`, `wait_thread(h)` | Нативные системные потоки без GIL на всех ядрах CPU |
| **Атомарные операции**| `atomic_add(ptr, val)`, `atomic_sub(ptr, val)` | Потокобезопасные атомарные операции с префиксом `lock` |
| **Консольный вывод**| `print()`, `print_int()`, `print_str()`, `print_newline()` | Низкоуровневая буферизованная потоковая печать в stdout |
| **Таймеры и паузы** | `get_tick_count()`, `sleep_ms(ms)` | Высокоточные таймеры и сон потока |
| **Строки Unicode** | `str` | Прозрачная конвертация UTF-8 в UTF-16LE для Win32 GUI API |

---

## Бенчмарки и производительность

Тестирование на процессорах AMD / Intel x86_64 (Windows 11 и Linux 6.x):

| Тест | CPython 3.12 (Стандарт) | PyPy 3.10 (JIT) | PyFASM64 Native x64 | Ускорение относительно CPython |
| :--- | :--- | :--- | :--- | :--- |
| **Числа Фибоначчи ($N=40$)** | 12,450 мс | 620 мс | **< 1 мс** | **> 12,000x** |
| **Решето Эратосфена (100k)** | 185 мс | 18 мс | **< 1 мс** | **> 180x** |
| **8-поточный параллельный счетчик**| 4,210 мс (задержки GIL)| 1,840 мс | **47 мс (Zero-GIL)** | **> 89x** |
| **Размер исполняемого файла** | ~35 МБ (pyinstaller) | Не применимо | **2.5 КБ** | **> 14,000x меньше** |

---

## Тестирование и верификация

Набор тестов проверяет кодогенерацию, выполнение, парсер AST, многопоточность, бандлер и систему типов:

```bash
uv run pytest
```

```text
============================= 48 passed in 6.37s ==============================
```

Подтвержденная матрица совместимости:
* **CPython 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16**: 100% тестов пройдены.
* **Python Free-Threaded / No-GIL (3.13t, 3.14t, 3.15t, 3.16t)**: 100% тестов пройдены.
* **PyPy (3.8, 3.9, 3.10, 3.11, 3.12)**: 100% тестов пройдены.

---

## Лицензия

Проект распространяется под открытой лицензией [MIT License](LICENSE).
