# Language & Compatibility Reference

This document gives an exact, engineering-accurate specification of what **PyFASM64** compiles natively in AOT `compile` / `emit-asm` mode, how imports and OOP work, and where you should use `--strict` or `bundle` instead.

---

## 1. Primitive & Container Types

PyFASM64 runs static type inference (`AstAnalyzer` + `X64CodeGen`), defaulting unannotated integers to 64-bit signed integers (`int64`). Adding standard Python type annotations improves precision across method calls and expressions.

| Python Type | Native Representation | Notes & Guarantees |
| :--- | :--- | :--- |
| `int` | Signed 64-bit integer (`int64`) | Floor division (`//`) and modulo (`%`) follow Python sign semantics, not C truncation |
| `float` | IEEE-754 double (`float64`, SSE2) | Exact bit representation including `-0.0`, `inf`, `-inf`, `nan`; leading fraction zeros preserved in `print()` |
| `bool` | 64-bit integer (`0` / `1`) | Short-circuiting `and` / `or` and ternary expressions supported |
| `str` | Null-terminated UTF-8/ASCII buffer pointer | UTF-8 codepoint `len()`, indexing `s[i]`, slicing `s[start:stop:step]`, `+` concatenation, f-strings (with `!r` and `:.Nf`/`:N.Mf`/`:x`/`:X`/`:b`/`:o`/`:0Nd`/`:Nd` specifiers on Win64), Cyrillic/ASCII `.lower()`, `.upper()` (including `Ё`/`ё`), `.strip()`, `.split()`, `.join()`, `.replace()`, `.startswith()`, `.endswith()`, `.count()`, `.removeprefix()`, `.removesuffix()` |
| `list` | Heap buffer `[length, item0, item1, ...]` | Negative indexing, slicing with step, comprehensions, `.append()`, `.insert()`, `.pop()`, `.sort()`, `.count()`, `+`, `*`, `in` |
| `tuple` | Heap buffer `[length, item0, item1, ...]` | Tuple unpacking, swap `a, b = b, a`, nested unpacking, tuple keys in `dict` |
| `dict` | Open-addressing hash table (pow2 slots, tombstones `-1`) | `int` (including negative keys like `-1`), `str`, and `tuple` keys; `.get()`, `.pop(k[, default])`, `.keys()`, `.values()`, `.items()`, `in`, `len()`, comprehensions |
| `set` | Hash-table set (tombstones supported) | Negative integers, `.add()`, `.remove()`, `.discard()`, `in`, `len()`, set comprehensions, set operations |
| `ptr` | Raw 64-bit pointer | `alloc_memory(bytes)`, `free_memory(ptr)`, `buf[i]` indexed access |

---

## 2. Functions, Control Flow & Modern Python Syntax

* **Identifiers & Encoding**: Full UTF-8 / Cyrillic / Unicode identifiers for functions, classes, and local/global variables via collision-free hex-encoded FASM labels.
* **Functions & Closures**: defaults, keyword arguments, recursion (16-byte stack aligned), 0–20+ arguments, real lexical closures (capturing lambdas and nested `def` functions including recursive and mutually-recursive nested `def`s, capturing recursive closures, and function-alias type inference, usable directly, indirectly, and with `map()`/`filter()`), first-class functions & lambdas.
* **Control Flow**: `if`/`elif`/`else`, `while`/`for ... else`, `break`, `continue`, chained comparisons (`0 <= x < 10`), walrus operator (`:=`), `assert`, structural pattern matching (`match`/`case`), `try`/`except`/`finally`/`raise`.
* **Generators & Comprehensions**: `yield`, `yield from`, generator expressions `(x * 2 for x in seq if ...)`, list/dict/set comprehensions.
* **No-GIL Multithreading**: `spawn_thread(worker, param)`, `wait_thread(handle)`, `atomic_add(ptr, val)`, `atomic_sub(ptr, val)`, `get_tick_count()`, `sleep_ms(ms)`.

---

## 3. Object-Oriented Programming & Magic Methods

### Classes, Inheritance & Polymorphism
* Instance allocation with runtime class tags, inheritance (single & multi-level), `super().__init__(...)` and `super().method(...)`, polymorphic virtual dispatch across base/subclass hierarchies, `isinstance(obj, T)`, and `issubclass(C, T)`.
* Decorators: `@property` / `@name.setter`, `@staticmethod`, and `@classmethod` (including dynamic `cls(...)` constructors and `issubclass(cls, Base)`).
* Automatic `__init__` synthesis when a class defines annotated attributes (`x: int`) without an explicit `__init__`.

### Magic Methods (Dunders) Matrix

| Category | Supported in Native Codegen | Not Wired (`W2006` warning / `E2006` in `--strict`) |
| :--- | :--- | :--- |
| Lifecycle & Contexts | `__init__`, `__new__`, `__enter__`, `__exit__` | `__del__` |
| Operators (Binary, Unary & In-Place) | `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__floordiv__`, `__mod__`, `__pow__`, `__radd__`, `__rsub__`, `__rmul__`, `__rtruediv__`, `__rfloordiv__`, `__rmod__`, `__and__`, `__or__`, `__xor__`, `__lshift__`, `__rshift__`, `__neg__`, `__pos__`, `__invert__`, `__abs__`, `__iadd__`..`__ixor__` | `__rpow__`, `__rand__`, `__ror__`, `__rxor__` |
| Comparisons & Truthiness | `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`, `__bool__` | — |
| Containers, Iteration, Callables & Formatting | `__len__`, `__getitem__`, `__setitem__`, `__contains__`, `__str__`, `__repr__`, `__call__`, `__iter__`, `__next__` (with `StopIteration`) | `__hash__`, `__format__`, `__getattr__`, `__getattribute__`, `__setattr__`, `__delattr__` |

> **Tip:** Annotate variables holding custom class instances (`v: Vector` or assign directly from `Vector(...)`) so static dispatch always finds dunder methods and properties cleanly.

---

## 4. Imports, Stdlib & External Libraries

### How `AstAnalyzer` Resolves Imports

1. **Local project modules & packages** (`utils.py`, `pkg/sub/mod.py`, `from mod import fn as alias`):
   Discovered recursively relative to both the importing file and `project_root`. Module top-level initializers run in **topological order** (dependencies before dependents), before `main()`. Cross-module attribute reads and writes (`config.TIMEOUT = 10`) are compiled into shared global symbols.
2. **Pure-Python packages in `.venv/site-packages`**:
   Discovered automatically when they contain pure `.py` modules without compiled `.pyd`/`.so` extensions and use supported Python constructs.
3. **Built-in / Natively Adapted Modules**:
   * **Stdlib subset**: `math` (`gcd`, `lcm`, `isqrt`, `factorial`), `json` (`json.loads`), `bisect` (`bisect`, `bisect_left`, `bisect_right`), `heapq` (`heappush`, `heappop`, `heapify`, `heapreplace`), `itertools` (`chain`, `accumulate`, `pairwise`), `functools` (`reduce`), `re` (basic match helpers), `with open(...)` file I/O.
   * **Ecosystem adapters**: `requests.get(...).json()`, `bs4.BeautifulSoup`, `darkdetect` (`isDark()`, `isLight()`, `theme()`), `numpy` (`zeros`, `ones`, `matmul`, `flatnonzero` / NanoGEMM SIMD), native Win32 GUI/tray backends (`tkinter`, `customtkinter`, `PyQt5`, `PyQt6`, `PySide6`, `flet`, `pystray`), native Win32 GDI 2D engine (`pygame`), and native Winsock2 HTTP/1.1 + JSON server (`fastapi`, `uvicorn` with `APIRouter`, path/query/body parameters, await-free `async def` routes, `HTMLResponse`/`PlainTextResponse`/`JSONResponse`, and `/openapi.json`).
4. **Unsupported External / C-Extension Libraries (`W2005` / `E2005` in `--strict`)**:
   Frameworks such as `asyncio`, `pandas`, `torch`, `tensorflow`, `scipy`, `matplotlib`, `cv2`, `sqlite3`, `flask`, `django`, `aiohttp`, `playwright`, `selenium`, `cryptography`, `pydantic`, `multiprocessing`, `subprocess`, `socket`, `datetime`, `decimal`, etc. cannot be AOT-compiled directly into FASM in standalone `compile` mode.

---

## 5. Unsupported Language Constructs

Running `pyfasm64 check` or `pyfasm64 compile` flags these immediately instead of silently miscompiling:

* **Hard Errors**:
  * `E2001`: `async def`, `await`, `async for`, `async with` (use `spawn_thread()` or `pyfasm64 bundle`)
  * `E2002`: `class X(metaclass=...)`
  * `E2003`: Unbound `nonlocal` statements (valid `nonlocal` bindings in enclosing function scopes compile natively)
* **Warnings (promoted to errors under `--strict`)**:
  * `W2004`: `with <expr>:` where `<expr>` is neither `open(...)` nor a class instance defining `__enter__`/`__exit__`
  * `W2005`: Imports of known unsupported/binary C-extension packages
  * `W2006`: Unsupported magic methods on classes (`__getattr__`, `__hash__`, `__del__`, etc.)
  * `W3001`: Unresolved external function or symbol calls (default mode emits a `xor eax, eax` stub for compatibility; `--strict` rejects them cleanly)

---

## 6. Choosing the Right Build Mode

| Use Case | Recommended Mode |
| :--- | :--- |
| Native CLI, math/algo engine, No-GIL threads, bare-metal, minimal binary (few KB) | `pyfasm64 compile app/ --strict` |
| Accelerating hotspots for an existing CPython/PyTorch/FastAPI backend | `pyfasm64 compile kernel.py --target dll` + `ctypes.CDLL(...)` |
| Full Python GUI/web/automation project using C-extensions & full stdlib | `pyfasm64 bundle app/ -e app/main.py --include-venv` |
