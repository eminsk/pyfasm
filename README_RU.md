# PyFASM64: Универсальный нативный компилятор Python в чистый машинный код FASM x86_64

> 🌐 **Язык / Language:** [🇬🇧 English](https://github.com/eminsk/pyfasm/blob/main/README.md) | **Русский (Russian Documentation)**

[![PyPI - Version](https://img.shields.io/pypi/v/pyfasm64?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/pyfasm64/)
[![GitHub Release](https://img.shields.io/github/v/release/eminsk/pyfasm?style=flat&logo=github&logoColor=white&color=blue)](https://github.com/eminsk/pyfasm/releases)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pyfasm64?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/pyfasm64/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyfasm64?style=flat&logo=python&logoColor=white)](https://pypi.org/project/pyfasm64/)
[![CI](https://github.com/eminsk/pyfasm/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/eminsk/pyfasm/actions/workflows/ci.yml)
[![Conda-Forge](https://img.shields.io/conda/vn/conda-forge/pyfasm64.svg?style=flat&logo=condaforge)](https://anaconda.org/conda-forge/pyfasm64)
[![Debian Package](https://img.shields.io/github/v/release/eminsk/pyfasm?include_prereleases&label=Debian%20.deb&logo=debian)](https://github.com/eminsk/pyfasm/releases)
[![Python: 3.8 - 3.16](https://img.shields.io/badge/Python-3.8%20--%203.16-blue.svg?style=flat)](https://python.org)
[![No-GIL: 3.13t - 3.16t](https://img.shields.io/badge/No--GIL-3.13t%20--%203.16t-success.svg?style=flat)](https://peps.python.org/pep-0703/)
[![Targets: Windows | Linux | macOS | DLL](https://img.shields.io/badge/Targets-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20DLL-purple.svg?style=flat)]()
[![Backend: Flat Assembler x64](https://img.shields.io/badge/Backend-FASM%20x64%20v1.73.36-red.svg?style=flat)](https://flatassembler.net)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat)](https://github.com/eminsk/pyfasm/blob/main/LICENSE)

---

**PyFASM64** (пакет: `pyfasm64`, алиас: `pyfasm`) — высокопроизводительный кроссплатформенный компилятор, транслирующий код Python напрямую в чистый машинный код **x86_64 Flat Assembler (FASM)**. Компилятор создаёт сверхкомпактные автономные исполняемые файлы и библиотеки с **нулевым оверхедом рантайма**, **без виртуальной машины Python** и с **полным устранением Global Interpreter Lock (Zero-GIL)**.

```
Исходный код Python (3.8 – 3.16t)
        │
        ▼ (Синтаксический анализ AST и вывод типов)
Семантическое промежуточное представление
        │
        ▼ (Выбор целевой платформы: Windows / Linux / macOS)
Чистый x86_64 ассемблер FASM (без libc и без VM)
        │
        ▼ (Встроенный ассемблер FASM Modern SDK)
Автономный нативный бинарник (.exe / .elf / .macho / .dll) [~2.5 КБ]
```

---

## Главные новшества в v1.1.0

* **Поддержка возможностей Python 3.14 и 3.15**:
  * Псевдонимы типов PEP 695 (`type Vector = list[int]`) и обобщенные функции/классы (`def f[T](x: T):`, `class Box[T]:`).
  * Высокоскоростное SIMD/скалярное скалярное произведение `math.sumprod(p, q)`, пакетирование `itertools.batched(seq, n)` и определение ядер `os.cpu_count()`.
  * Сворачивание условий версии во время компиляции: конструкции вида `sys.version_info >= (3, 14)` разрешаются на этапе сборки, исключая мертвые ветки кода.
* **Динамическое определение версии установленного Python**:
  * Компилятор автоматически определяет версию хостового окружения (например, Python 3.15.2 Free-Threaded) и генерирует точные константы для `sys.version`, `sys.version_info`, `sys.platform` и `sys.byteorder`.
  * Функция `sys._is_gil_enabled()` в скомпилированном бинарнике возвращает `0`.
* **Полное исключение жестко зашитых шаблонов**:
  * Никаких шаблонов или заглушек для графики или вычислений: весь код (включая сложные интерфейсы CustomTkinter, Flet, Tkinter и PyQt) компилируется строго и аутентично из пользовательского AST.
* **Расширенные флаги командной строки**:
  * Добавлены флаги `--gui` / `-w` (подсистема Win32 GUI без консольного окна), `--console` / `-c` (консольная подсистема), `--python-version` / `--py-ver`, `--optimize` / `-O` и `--verbose` / `-v`.
* **Полная история изменений**: доступна в файле [CHANGELOG.md](https://github.com/eminsk/pyfasm/blob/main/CHANGELOG.md).

---

## Что нового в v0.1.14: Интеграция с FASM Modern SDK

Начиная с версии **v0.1.14**, PyFASM64 включает в себя и глубоко интегрирует **FASM Modern SDK** (`fasm-modern-sdk v1.73.36` и `fasmg v0.0.26`):

1. **Автономный компилятор и заголовочные файлы**:
   - Официальные wheel-пакеты содержат все необходимые бинарники компилятора FASM (`FASM.EXE`, `fasmg.exe`, `fasm.x64`, `fasm.darwin`, `fasm`) и стандартные include-файлы Win64/Win32 (`win64a.inc`, `win32a.inc`).
   - Настройка переменной `INCLUDE` не требуется.
2. **Модули Modern SDK**:
   - `ui_fluent.inc`: Стилизация темной темы Fluent UI, owner-drawn элементы и скругленные карточки.
   - `json_fast.inc`: Высокоскоростной SIMD JSON-парсер.
   - `net_https.inc`: Нативный HTTPS/TLS клиент без внешних зависимостей.
   - `data_structures.inc`: Динамические массивы, строковые буферы и хэш-таблицы.
   - `syntax_color.inc`: Токенизация и подсветка синтаксиса в реальном времени.
3. **Движок Unicode и UTF-8 / UTF-16LE**:
   - Встроенная нативная конвертация (`_pyfasm_utf8_to_wide`), исключающая кракозябры в элементах интерфейса.
   - Защита от коллизий элементов GUI: повторное использование дескрипторов окон.
4. **Встроенная интерактивная документация**:
   - Просмотр документации на английском: `pyfasm docs`
   - Просмотр документации на русском: `pyfasm docs --ru`
   - Открытие документации в браузере: `pyfasm docs --open`

---

## Быстрый старт

### 1. Установка

```bash
# Рекомендуемый способ с помощью uv:
uv add pyfasm64

# Либо через стандартный pip:
pip install pyfasm64
```

### 2. Компиляция за 5 секунд

Создайте файл `hello.py`:

```python
def main() -> int:
    name: str = "Мир"
    print(f"Привет, {name}! Скомпилировано с помощью PyFASM64.")
    return 0
```

Скомпилируйте и запустите нативный бинарник размером 2.5 КБ:

```bash
uv run pyfasm64 compile hello.py --run
```

---

## Интерфейс командной строки (`pyfasm64` / `pyfasm`)

Доступны обе команды (`pyfasm64` и `pyfasm`), обладающие полностью идентичным синтаксисом:

### `pyfasm64 compile`

```bash
pyfasm64 compile <source> [ПАРАМЕТРЫ]
```

| Параметр | Флаг | По умолчанию | Описание |
| :--- | :--- | :--- | :--- |
| `<source>` | | *обязательный* | Путь к файлу `.py` или папке проекта |
| `--output` | `-o` | `<stem>.<ext>` | Путь к выходному файлу (`.exe`, `.dll`, `.elf`, `.macho`) |
| `--target` | | `win64` | Целевая платформа: `win64`, `dll`, `linux`, `macos` |
| `--gui` | `-w`, `--windowed` | *авто* | Оконная подсистема Win32 GUI (без консольного окна) |
| `--console` | `-c` | *авто* | Консольная подсистема со стандартными потоками ввода/вывода |
| `--python-version`| `--py-ver` | *версия хоста* | Целевая версия Python (например, `3.14`, `3.15`) |
| `--optimize` | `-O` | `False` | Включить peephole-оптимизацию ассемблерного кода |
| `--verbose` | `-v` | `False` | Подробный вывод сообщений процесса сборки |
| `--run` | | `False` | Автоматически запустить бинарник сразу после сборки |
| `--icon` | | `None` | Путь к `.ico` для встраивания иконки в PE-ресурсы (`.rsrc`) |
| `--strict` | | `False` | Переводить предупреждения компилятора (`W2004`–`W3001`) в ошибки |
| `--export-fasm` | `-f` | `None` | Экспортировать автономную папку FASM со скриптами сборки |
| `--no-asm` | | `False` | Удалять промежуточные ассемблерные файлы после сборки |

### Дополнительные команды

* **`pyfasm64 check <source> [--strict]`**: Проверка синтаксиса, типов и совместимости без генерации машинного кода.
* **`pyfasm64 emit-asm <source> [-o out.asm]`**: Генерация читаемого x86-64 FASM ассемблерного кода в терминал или файл.
* **`pyfasm64 bundle <папка_проекта> -o App.exe`**: Упаковка многофайлового проекта в единый запускаемый нативный файл.
* **`pyfasm64 clean [--apps | --all]`**: Очистка временных файлов сборки и глобальных кэшей.
* **`pyfasm64 docs [--ru] [--open]`**: Интерактивный просмотр документации в консоли или браузере.

---

## Поддерживаемая экосистема и возможности

| Область | Поддерживаемые библиотеки | Нативная реализация |
| :--- | :--- | :--- |
| **Графический интерфейс** | `tkinter`, `customtkinter`, `PyQt5`, `PyQt6`, `flet` | Нативные Win32 GDI элементы, темная тема Fluent, динамическая разметка, маршрутизация сообщений ввода |
| **2D-игры** | `pygame` (`display`, `event`, `draw`, `Rect`, `Clock`, `font`) | Двойная буферизация GDI без внешних библиотек и зависимостей |
| **Веб и REST API** | `fastapi`, `uvicorn` (`@app.get`, `@app.post`, обработка JSON) | Высокопроизводительный сервер HTTP/1.1 на Winsock2, встроенный парсер RFC-8259 JSON |
| **Python 3.14 / 3.15** | `TypeAlias`, `def f[T]()`, `sumprod`, `batched`, `cpu_count` | Разрешение условий на этапе сборки, SIMD скалярное умножение, системный PEB-запрос процессоров |
| **Параллелизм Zero-GIL** | `spawn_thread`, `wait_thread`, `atomic_add`, `atomic_sub` | Настоящие потоки ОС (`CreateThread` / `sys_clone`), аппаратные CPU-инструкции `lock` |
| **Объектно-ориентированное**| `class`, `super()`, `@property`, `@staticmethod`, `@classmethod` | Таблицы виртуальных методов, идентификаторы классов, отраженные дандеры (`__radd__` и др.) |
| **Память и буферы** | `alloc_memory`, `free_memory`, `buf[i]` | Прямое выделение страниц ОС (`VirtualAlloc` / `sys_mmap`), индексация по сырым указателям |

---

## Сравнение целевых платформ

| Архитектурный аспект | Windows x86-64 | Linux x86-64 | Apple macOS x86-64 |
| :--- | :--- | :--- | :--- |
| **Формат файла** | PE32+ (PE64) Console / GUI / DLL | Исполняемый ELF64 (Тип 3) | Mach-O 64 (`MH_MAGIC_64`) |
| **Соглашение о вызовах** | Microsoft x64 ABI (Shadow Space) | System V AMD64 ABI | System V AMD64 ABI |
| **Системный интерфейс** | Win32 API (`kernel32.dll`, `user32.dll`) | Прямые сисколы ядра Linux | Прямые сисколы Darwin BSD |
| **Внешние зависимости** | Нет (только системные библиотеки ОС) | **0% libc / 0% glibc** | **0% libSystem / 0% dyld** |
| **Типичный размер файла** | **~2.5 КБ** | **~1.8 КБ** | **~2.4 КБ** |

---

## Тесты производительности

Тестирование на процессорах AMD Ryzen / Intel Core x86_64:

| Тест | CPython 3.12 | PyPy 3.10 (JIT) | PyFASM64 Native x64 | Ускорение относительно CPython |
| :--- | :--- | :--- | :--- | :--- |
| **Числа Фибоначчи ($N=40$)** | 12 450 мс | 620 мс | **< 1 мс** | **> 12 000x** |
| **Решето Эратосфена (100k)** | 185 мс | 18 мс | **< 1 мс** | **> 180x** |
| **Параллельный счётчик (8 потоков)** | 4 210 мс (борьба за GIL) | 1 840 мс | **47 мс (Zero-GIL)** | **> 89x** |
| **Размер исполняемого файла** | ~35 МБ (PyInstaller) | N/A | **2.5 КБ** | **> 14 000x меньше** |

---

## Тестирование и верификация

Каждый коммит и релиз автоматически тестируется во всех поддерживаемых средах:

```bash
uv run pytest
```

* **Матрица совместимости**: CPython 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16.
* **Матрица No-GIL**: Free-Threaded Python 3.13t, 3.14t, 3.15t, 3.16t.
* **Матрица PyPy**: PyPy 3.8 – 3.12.
* **Статус тестового набора**: 100% тестов успешно пройдено (154/154).

---

## Документация

Подробные руководства по языку, архитектуре и CLI находятся в каталоге [`docs/`](https://github.com/eminsk/pyfasm/blob/main/docs/INDEX.md):

* 📘 [Главный хаб документации](https://github.com/eminsk/pyfasm/blob/main/docs/INDEX.md) — Основной индекс и навигация.
* 🚀 [Руководство по началу работы](https://github.com/eminsk/pyfasm/blob/main/docs/GETTING_STARTED.md) — Установка, сборка и структура проектов.
* 📖 [Справочник по языку](https://github.com/eminsk/pyfasm/blob/main/docs/LANGUAGE_REFERENCE.md) — Синтаксис, типы и поддерживаемая стандартная библиотека.
* ⚙️ [Интерфейс CLI и программный API](https://github.com/eminsk/pyfasm/blob/main/docs/CLI_AND_API.md) — Полный справочник параметров и вызовов.
* 🔍 [Диагностика и каталог ошибок](https://github.com/eminsk/pyfasm/blob/main/docs/ERRORS.md) — Коды ошибок компилятора (`E1001`–`E4002`) и способы исправления.
* 🏗️ [Внутреннее устройство и ABI](https://github.com/eminsk/pyfasm/blob/main/docs/ARCHITECTURE.md) — Генерация FASM, структуры памяти и соглашения вызовов.
* 🇷🇺 [Полное руководство на русском языке](https://github.com/eminsk/pyfasm/blob/main/docs/GUIDE_RU.md) — Исчерпывающее руководство на русском языке.

---

## Сообщество и поддержка

* 🐛 **Сообщения об ошибках и багрепорты:** [GitHub Issues](https://github.com/eminsk/pyfasm/issues)
* 💬 **Обсуждения сообщества:** [GitHub Discussions](https://github.com/eminsk/pyfasm/discussions)
* 🏛️ **Официальная тема на форуме FASM:** [Flat Assembler Board](https://board.flatassembler.net/topic.php?t=24431)
* ☕ **Поддержка разработки (USDT TRC-20):** `TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P` ([Проверить на TronScan](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P))

---

## Лицензия

Проект распространяется под открытой лицензией [MIT License](https://github.com/eminsk/pyfasm/blob/main/LICENSE).
