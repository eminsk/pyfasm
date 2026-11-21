# Полное профессиональное руководство по PyFASM64

**PyFASM64** (пакет `pyfasm64` на PyPI, модули `pyfasm64` и `pyfasm`) — это AOT-компилятор (Ahead-of-Time) и бандлер для Python 3.8–3.16 (CPython, No-GIL `3.13t`–`3.16t`, PyPy `3.8`–`3.12`), который транслирует Python напрямую в чистый ассемблер **Flat Assembler (FASM) x86-64** и собирает нативные бинарники без GIL для Windows (`.exe`, `.dll`), Linux (ELF64), Apple macOS (Mach-O 64) и MyOS.

---

## 1. Установка и проверка окружения

```bash
# Через uv (рекомендуется)
uv tool install pyfasm64
# или в проект:
uv add pyfasm64

# Через pip
pip install pyfasm64

pyfasm64 --version
```

Внутри пакета уже поставляются бинарники FASM (`FASM.EXE`, `fasm.x64`, `fasm.darwin`) и заголовочные файлы. При необходимости использовать свой бинарник FASM можно через переменные окружения `PYFASM_FASM_PATH` (или `FASM_PATH`) и `PYFASM_INCLUDE_PATH`.

---

## 2. Проверка кода до компиляции (`pyfasm64 check` и `--strict`)

Компилятор оснащён структурированной системой диагностики в стиле `rustc`/`clang` с указанием файла, строки, колонки, фрагмента кода и подсказки (`hint`):

```bash
# Статическая проверка файла или всего проекта без запуска ассемблера
pyfasm64 check my_project/

# Строгий режим: превращает предупреждения (внешние C-модули, неразрешённые вызовы, неподдерживаемые dunder'ы) в ошибки
pyfasm64 check my_project/ --strict
pyfasm64 compile my_project/ --strict
```

Пример вывода при синтаксической или семантической ошибке:

```text
error[E1001]: Python syntax error: expected ':'
 --> core/math_engine.py:4:14
  |
4 | def solve(n)
  |              ^
  = hint: Fix the Python syntax error before compiling with PyFASM64.
```

---

## 3. Структура компилируемого проекта (один файл или сложный пакет)

Компилятор принимает **как один `.py`-файл, так и целую директорию проекта**:

```text
my_project/
├── icon.ico               # Подхватится автоматически и встроится в .rsrc
├── main.py                # Точка входа (def main() -> int:)
├── config.py              # Глобальные настройки и константы
├── core/
│   ├── __init__.py
│   ├── models.py          # Классы, наследование, super(), @property, магические методы
│   └── algorithms.py      # Списки, словари, множества, генераторы (yield), math/heapq/bisect
└── services/
    ├── __init__.py
    └── pipeline.py        # Импортирует core.models и config
```

* Автопоиск точки входа при передаче папки `pyfasm64 compile my_project/`: `main.py` -> `app.py` -> `bot.py` -> `run.py` -> `index.py` -> первый `.py` файл.
* Все локальные модули и подпакеты разрешаются рекурсивно, а их код верхнего уровня инициализируется в **топологическом порядке зависимостей** до вызова `main()`.

---

## 4. Что поддерживается компилятором: классы, магические методы и импорты

### Типы, конструкции и ООП
* **Типы**: 64-битные целые `int` (с корректным Python-делением `//` и `%` для отрицательных чисел), `float` (IEEE-754 double, вкл. `-0.0`, `NaN`/`Inf`), `bool`, `str` (полная UTF-8 длина по символам `len()`, индексация `s[i]`, срезы `s[a:b:c]`, регистр кириллицы `.upper()`/`.lower()` вкл. `Ё`/`ё`, f-строки, конкатенация), `list`, `tuple`, `dict` (ключи `int`, `str`, `tuple`, включая отрицательные int-ключи и `pop(k[, default])`), `set`, `ptr` (`alloc_memory`/`free_memory`).
* **Конструкции и идентификаторы**: русские/Unicode идентификаторы для функций, классов и переменных (без коллизий меток), функции с дефолтами и `kwargs`, реальные лексические замыкания (захватывающие `lambda` и вложенные `def`, в т.ч. для `map`/`filter`), списочные/словарные/множественные включения, генераторы (`yield`, `yield from`, generator expressions), `try`/`except`/`finally`/`raise StopIteration`, `match`/`case`, `with open(...)` и пользовательские менеджеры контекста (`__enter__`/`__exit__`), нативные потоки без GIL (`spawn_thread`, `wait_thread`, `atomic_add`, `atomic_sub`).
* **Классы и ООП**: наследование и полиморфная диспетчеризация методов (`_pyfasm_vcall_*`), `isinstance()` / `issubclass()`, `super().__init__()` / `super().method()`, `@staticmethod`, `@classmethod` (включая `cls(...)`), `@property` и `@prop.setter`, автосинтез `__init__` из аннотированных полей класса.
* **Поддерживаемые магические методы**: `__init__`, `__new__`, `__call__`, `__bool__`, `__enter__`, `__exit__`, `__iter__`, `__next__`, `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__floordiv__`, `__mod__`, `__pow__`, `__and__`, `__or__`, `__xor__`, `__lshift__`, `__rshift__`, `__neg__`, `__pos__`, `__invert__`, `__iadd__`..`__ixor__`, `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`, `__len__`, `__getitem__`, `__setitem__`, `__contains__`, `__str__`, `__repr__`.

### Импорты и зависимости
1. **Локальные модули и пакеты проекта**: компилируются полностью в единый бинарник.
2. **Pure-Python пакеты из `.venv/site-packages`**: находятся и подключаются автоматически, если не содержат бинарных C-расширений (`.pyd`/`.so`).
3. **Встроенный stdlib и адаптеры**: `math` (`gcd`, `lcm`, `isqrt`, `factorial`), `json.loads`, `bisect`, `heapq`, `itertools` (`chain`, `accumulate`, `pairwise`), `functools.reduce`, `open()`, нативные адаптеры под `requests`, `darkdetect`, `numpy` (NanoGEMM SIMD), Win32 GUI/tray (`tkinter`, `customtkinter`, `pystray`).
4. **Тяжёлые внешние библиотеки с C-расширениями** (`asyncio`, `pandas`, `torch`, `matplotlib`, `sqlite3`, `playwright`, `aiohttp`, и т.д.): в режиме `compile` выдаётся диагностика **`W2005`** (или **`E2005`** с `--strict`). Для таких проектов используйте:
   * **`pyfasm64 bundle ./my_project -e ./my_project/main.py --include-venv`** — упаковка всего проекта с окружением в нативный exe-лаунчер;
   * либо **`pyfasm64 compile fast_kernel.py --target dll`** — вынос горячих вычислений в сверхбыструю нативную DLL без GIL и вызов через `ctypes` из обычного Python.

---

## 5. Коды ошибок и предупреждений (краткий справочник)

| Код | Значение | Что делать |
| :--- | :--- | :--- |
| **`E1001`** | Синтаксическая ошибка Python | Исправить синтаксис по указанному файлу и строке |
| **`E1002`** | Файл не найден / папка пуста | Проверить путь или наличие `.py`-файлов |
| **`E1003`** | Неизвестная платформа `--target` | Выбрать `win64`, `dll`, `linux`, `macos`, `apple` или `myos` |
| **`E2001`** | `async`/`await` в AOT `compile` | Использовать `spawn_thread()` или `pyfasm64 bundle` |
| **`E2002`** | Использование `metaclass=` | Заменить на наследование / `@property` / фабрики |
| **`E2003`** | Использование `nonlocal` | Передавать состояние через объект класса, список или `global` |
| **`W2004`** / **`E2004`** | `with` для объекта без `__enter__`/`__exit__` и не `open()` | Реализовать `__enter__`/`__exit__` или заменить на `try ... finally` / `bundle` |
| **`W2005`** / **`E2005`** | Внешний/C-модуль (`pandas`, `asyncio`...) | Использовать `pyfasm64 bundle` или `--target dll` |
| **`W2006`** / **`E2006`** | Неподключённый dunder (`__getattr__`, `__hash__`, `__del__`...) | Вызывать явные методы класса или поддерживаемые операторы |
| **`W3001`** / **`E3001`** | Неразрешённый внешний символ (stub -> 0) | Проверить имя/импорт; с `--strict` сборка сразу остановится |
| **`E4001`** / **`E4002`** | Ошибка ассемблирования FASM | См. выведенную строку `.asm` или проверьте `PYFASM_FASM_PATH` |

---

## 6. Полезные ссылки на остальные разделы

* [Индекс документации (EN / RU)](INDEX.md)
* [Getting Started](GETTING_STARTED.md)
* [Language & Compatibility Reference](LANGUAGE_REFERENCE.md)
* [CLI & Python API Reference](CLI_AND_API.md)
* [Compiler Diagnostics & Error Codes](ERRORS.md)
* [Architecture & ABI Internals](ARCHITECTURE.md)
