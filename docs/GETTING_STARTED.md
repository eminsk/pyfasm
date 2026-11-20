# Getting Started with PyFASM64

PyFASM64 compiles Python code directly into x86-64 machine code using Flat Assembler (**FASM**) with zero runtime dependency on CPython for native `compile` targets, or packages full Python environments via a native FASM bootstrapper in `bundle` mode.

---

## 1. Installation

The package is published on PyPI as **`pyfasm64`** and installs both **`pyfasm64`** and **`pyfasm`** console commands (as well as `python -m pyfasm64` / `python -m pyfasm`).

```bash
# Recommended with uv (global CLI tool)
uv tool install pyfasm64

# Or add to a project managed with uv
uv add pyfasm64

# Or install with pip
pip install pyfasm64

# Verify installation
pyfasm64 --version
```

Supported Python versions: **Python 3.8 – 3.16** (CPython, Free-Threaded/No-GIL `3.13t`–`3.16t`, and PyPy `3.8`–`3.12`).

---

## 2. FASM Assembler & Environment Overrides

`pyfasm64` ships with bundled FASM binaries (`FASM.EXE`, `fasm.x64`, `fasm.darwin`) and Windows/macro `include/` headers inside the package. If you want to point PyFASM64 to a custom FASM binary or include tree, use the standard environment variables:

| Variable | Purpose |
| :--- | :--- |
| `PYFASM_FASM_PATH` or `FASM_PATH` | Explicit path to custom FASM executable |
| `PYFASM_INCLUDE_PATH` | Explicit path to FASM `INCLUDE` directory |

On Linux and macOS, if the bundled `include` directory lives in a read-only site-packages location, PyFASM64 automatically mirrors lowercase include symlinks into `~/.cache/pyfasm/include` so case-insensitive FASM includes resolve cleanly.

---

## 3. Compiling a Single File

Create `hello.py`:

```python
def fib(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def main() -> int:
    print("Fib(30):", fib(30))
    return 0
```

Validate and compile:

```bash
# Check for errors or unsupported constructs first
pyfasm64 check hello.py --strict

# Compile and run immediately
pyfasm64 compile hello.py --run
```

If `def main()` is omitted, top-level statements become the entry point automatically; if both exist, top-level globals/statements execute first (via `_pyfasm_top_level_init`) and then `main()` runs.

---

## 4. Multi-File & Package Project Structure

PyFASM64 is designed for **multi-module projects**, not just single `main.py` scripts. When given a directory or an entry script, `AstAnalyzer` recursively resolves local imports and subpackages, initializes module-level state in topological dependency order, and merges everything into a single self-contained native binary.

```text
my_app/
├── icon.ico               # Automatically embedded into PE64 .rsrc section if present
├── main.py                # Auto-detected entry point
├── config.py              # Module-level constants & shared global state
├── core/
│   ├── __init__.py
│   ├── models.py          # Classes, inheritance, super(), @property, magic methods
│   └── solver.py          # Algorithms, generators (yield), math/heapq/bisect
└── services/
    ├── __init__.py
    └── reporter.py        # Calls core.models and config
```

Entry point auto-detection order when passing a directory (`pyfasm64 compile my_app/`):
1. `main.py`
2. `app.py`
3. `bot.py`
4. `run.py`
5. `index.py`
6. First `.py` file alphabetically if none of the above exists

If your entry script has a custom name inside a subfolder (e.g. `my_app/src/cli.py`), pass the file path explicitly:

```bash
pyfasm64 compile my_app/src/cli.py -o my_app.exe
```

---

## 5. Building Native DLLs for CPython / C / C# (`--target dll`)

Compile high-throughput kernels to a Windows x64 `.dll` and call them from standard Python via `ctypes` without GIL overhead:

```python
# fast_math.py
def sum_squares(n: int) -> int:
    total = 0
    for i in range(n):
        total += i * i
    return total
```

```bash
pyfasm64 compile fast_math.py --target dll -o fast_math.dll
```

Call from standard Python:

```python
import ctypes

lib = ctypes.CDLL("./fast_math.dll")
lib.sum_squares.argtypes = [ctypes.c_int64]
lib.sum_squares.restype = ctypes.c_int64
print(lib.sum_squares(1_000_000))
```

PyFASM64 emits a valid `.reloc` fixup section on DLLs so multiple compiled DLLs can be loaded simultaneously in the same process.

---

## 6. Cross-Compilation & Custom Icons

Any host OS (Windows, Linux, macOS) can target any supported executable format:

```bash
# Windows PE64 EXE with custom icon (embedded inline, works on macOS/Linux hosts too)
pyfasm64 compile my_app/ --target win64 --icon my_app/icon.ico -o dist/my_app.exe

# Linux ELF64 executable
pyfasm64 compile my_app/ --target linux -o dist/my_app.elf

# Apple macOS Mach-O 64 executable
pyfasm64 compile my_app/ --target macos -o dist/my_app.macho

# Bare-metal x64 binary (MyOS)
pyfasm64 compile kernel.py --target myos -o dist/kernel.bin

# Export self-contained FASM source folder + build.bat / build.sh
pyfasm64 compile my_app/ --export-fasm FASM_OUT/
```

---

## 7. Bundling Full Python Applications (`bundle`)

When your application depends on C-extension packages (`pandas`, `torch`, `playwright`, `aiohttp`, `sqlite3`, etc.), use **`pyfasm64 bundle`**:

```bash
pyfasm64 bundle ./my_project \
  -e ./my_project/main.py \
  --include-venv \
  --icon ./my_project/icon.ico \
  -o ./dist/my_project.exe
```

Add `--console` for CLI apps that should keep an attached terminal window, `--dir-mode` for directory-wrapper deployment instead of single-file extraction, or `--include-bin path/to/ffmpeg.exe` to bundle external tools.
