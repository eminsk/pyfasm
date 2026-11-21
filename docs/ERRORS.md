# Compiler Diagnostics & Error Code Catalog

PyFASM64 formats all compile-time diagnostics in **rustc/clang style**, showing the diagnostic code, exact `file:line:col` location, source snippet with caret underline (`^`), and an actionable hint.

Warnings (`Wxxxx`) still allow compilation to succeed in default mode (emitting safe compatibility behavior such as fallback stubs), whereas **`--strict`** (or `strict=True` in the Python API) promotes all `Wxxxx` warnings into hard `Exxxx` errors and fails the build cleanly.

---

## Diagnostic Index

| Code | Severity | Phase | Summary |
| :--- | :--- | :--- | :--- |
| **`E1001`** | `error` | Parsing | Python syntax error (`SyntaxError`) in entry or imported file |
| **`E1002`** | `error` | Input Resolution | Missing source file, unreadable file, or directory contains no `.py` files |
| **`E1003`** | `error` | Configuration | Invalid target platform (not one of `win64`, `dll`, `linux`, `macos`, `apple`, `myos`) |
| **`E2000`** | `error` | AST Lowering | AST preprocessing failure |
| **`E2001`** | `error` | Semantic Check | Asyncio construct (`async def`, `await`, `async for`, `async with`) in AOT compile mode |
| **`E2002`** | `error` | Semantic Check | Metaclass (`class X(metaclass=...)`) in AOT compile mode |
| **`E2003`** | `error` | Semantic Check | `nonlocal` statement inside nested closure |
| **`W2004`** / **`E2004`** | `warning` (strict -> `error`) | Semantic Check | `with <expr>:` where `<expr>` is not `open(...)` or a class defining `__enter__`/`__exit__` |
| **`W2005`** / **`E2005`** | `warning` (strict -> `error`) | Import Check | Unsupported external or binary C-extension module import (`pandas`, `asyncio`, `torch`, etc.) |
| **`W2006`** / **`E2006`** | `warning` (strict -> `error`) | OOP Check | Class defines a magic method not wired for automatic dispatch (`__getattr__`, `__hash__`, `__del__`, etc.) |
| **`W3001`** / **`E3001`** | `warning` (strict -> `error`) | Codegen | Unresolved external symbol (fallback stub returning `0` emitted) |
| **`E4001`** | `error` | Assembler | FASM assembly error (includes `.asm` file, line number, instruction, and hint) |
| **`E4002`** | `error` | Assembler | FASM assembler binary missing or failed to execute |

---

## Examples & How to Fix Each Diagnostic

### `E1001` — Python syntax error

```text
error[E1001]: Python syntax error: expected ':'
 --> app.py:2:12
  |
2 | def calc(x)
  |            ^
  = hint: Fix the Python syntax error before compiling with PyFASM64.
```

Reported for **both** the entry script and any imported module in the project. Fix the Python syntax error and re-run `pyfasm64 check`.

---

### `E1002` — Source path not found / empty directory

Ensure the passed path exists and, if pointing to a directory, contains at least one `.py` file.

---

### `E1003` — Unsupported target platform

Valid `--target` values are: `win64`, `dll`, `linux`, `macos`, `apple`, `myos`.

---

### `E2001` — `async` / `await` not supported in AOT compile

```text
error[E2001]: Asyncio construct 'async FunctionDef' is not supported in AOT native compilation
 --> worker.py:4:1
  |
4 | async def fetch():
  | ^
  = hint: Use OS threads (`spawn_thread()` / `wait_thread()`) for native concurrency, or package async code with `pyfasm64 bundle`.
```

**Fix:** For CPU-parallel native code without GIL, use `spawn_thread()` / `wait_thread()`. For `asyncio` I/O apps, use `pyfasm64 bundle`.

---

### `E2002` — Metaclasses not supported

**Fix:** Replace metaclasses with standard single inheritance, class helpers, `@property`, or factory functions.

---

### `E2003` — `nonlocal` not supported

**Fix:** Store mutable shared state on a class instance (`self.count`), pass a 1-element list/box, or use module globals.

---

### `W2004` (`E2004` with `--strict`) — Unmanaged `with` context expression

`with open(...) as f:` and classes defining `__enter__` / `__exit__` compile natively. Any other `with <expr>:` expression emits `W2004`.

**Fix:** Implement `__enter__`/`__exit__` on the context class, use explicit cleanup in `try: ... finally:`, or package with `pyfasm64 bundle`.

---

### `W2005` (`E2005` with `--strict`) — Unsupported external / C-extension import

```text
warning[W2005]: External or C-extension module 'pandas' is not natively compiled by PyFASM64 in standalone compile mode
 --> pipeline.py:1:1
  |
1 | import pandas as pd
  | ^^^^^^^^^^^^^^^^^^^
  = hint: Use `pyfasm64 bundle` to package apps with external/C-extension dependencies, or compile pure compute hotspots as `--target dll`.
```

**Fix:** Either compile only pure compute kernels as `--target dll` and invoke them from your Python script via `ctypes`, or package the full project with `pyfasm64 bundle --include-venv`.

---

### `W2006` (`E2006` with `--strict`) — Unwired magic method

Dunders such as `__getattr__`, `__getattribute__`, `__setattr__`, `__delattr__`, `__del__`, `__hash__`, `__format__`, and reflected `__r*__` operators are flagged because native dispatch does not synthesize attribute traps or CPython destructors automatically.

**Fix:** Call named methods explicitly (e.g. `obj.apply(...)`, `obj.to_list()`) or use the wired operators, callables, iterators, and context managers (`__init__`, `__call__`, `__bool__`, `__enter__`/`__exit__`, `__iter__`/`__next__`, `__add__`..`__xor__`, `__iadd__`..`__ixor__`, `__neg__`/`__pos__`/`__invert__`, `__eq__`..`__ge__`, `__len__`, `__getitem__`, `__setitem__`, `__contains__`, `__str__`, `__repr__`).

---

### `W3001` (`E3001` with `--strict`) — Unresolved external symbol

```text
warning[W3001]: Unresolved external symbol 'missing_helper' (emitted fallback stub returning 0)
 --> app.py:6:12
  |
6 |     return missing_helper(x)
  |            ^^^^^^^^^^^^^^^^^
  = hint: Define 'missing_helper', import its pure-Python module, or compile with `--strict` to treat unresolved symbols as errors.
```

In default mode, PyFASM64 emits a safe `xor eax, eax` stub so compilation completes (for instance when external adapter names are referenced). Enable `--strict` in CI/production builds to catch typos and missing imports immediately.

---

### `E4001` & `E4002` — FASM Assembler Diagnostics

When the backend assembler reports an error, PyFASM64 extracts the `.asm` file path, line number, offending instruction, and FASM error message (e.g., `undefined symbol`, `invalid operand`, `error reading file`), and provides a targeted hint. If FASM itself fails to launch (`E4002`), check executable permissions and `PYFASM_FASM_PATH` / `PYFASM_INCLUDE_PATH`.
