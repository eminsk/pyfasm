# Changelog

All notable changes to the **PyFASM64** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-11-21

### Added
- **Python 3.14 and 3.15 Language Features**:
  - Support for PEP 695 `type` statement type aliases (`type Vector = list[int]`).
  - Generic type parameters in function definitions (`def f[T](x: T) -> T:`) and class definitions (`class Box[T]:`).
  - Native x86-64 SIMD/scalar implementation of `math.sumprod(p, q)` for high-performance vectorized dot products.
  - Native x86-64 batch chunking with `itertools.batched(iterable, n)`.
  - Zero-overhead `os.cpu_count()` via direct Windows PEB `gs:[0x60] + 0xB8` query with scalar fallback.
  - Compile-time constant folding for `sys.version_info` comparison checks (e.g. `sys.version_info >= (3, 14)`), optimizing out unsupported version branches automatically at compile time.
- **Dynamic Python Version Detection**:
  - The compiler now automatically discovers the exact host Python version (major, minor, micro) and targets it dynamically (`sys.version`, `sys.version_info`, `sys.hexversion`, `sys.platform`, `sys.byteorder`, `sys.maxsize`, `sys.argv`).
  - Added support for `sys._is_gil_enabled()` returning `0` in native compiled binaries.
- **Enhanced CLI Options**:
  - `--gui`, `-w`, `--windowed`: Force compilation as a Win32 GUI windowed subsystem executable (suppress console window).
  - `--console`, `-c`: Force compilation with standard console subsystem (standard I/O enabled).
  - `--python-version`, `--py-ver`: Explicitly select target Python version (`3.14`, `3.15`, etc.).
  - `--optimize`, `-O`: Enable assembly peephole optimizations.
  - `--verbose`, `-v`: Enable verbose compilation diagnostics.
  - Enhanced `pyfasm64 -V` / `--version` to display compiler version along with host Python version (e.g., `pyfasm64 1.1.0 (Host Python: 3.15.2)`).
- **Modernized & Expanded Examples**:
  - `examples/01_hello.py`: Modernized with idiomatic f-strings and type annotations.
  - `examples/02_fibonacci.py`: Benchmarking iterative and recursive Fibonacci calculations.
  - `examples/03_prime_sieve.py`: Native Sieve of Eratosthenes algorithm.
  - `examples/04_multithread_parallel.py`: Zero-GIL multi-threaded atomic counter with `spawn_thread` and `atomic_add`.
  - `examples/05_mandelbrot_ascii.py`: High-speed ASCII Mandelbrot fractal rendering.
  - `examples/06_classes_oop.py`: OOP, inheritance, polymorphic virtual method dispatch, and magic methods.
  - `examples/07_tkinter_gui.py`: Native Win32 desktop application with buttons, labels, and event handlers.
  - `examples/08_data_structures.py`: Hash dicts, lists, sets, string manipulation, and comprehensions.
  - `examples/09_customtkinter_app.py`: Modern dark-theme desktop UI application.
  - `examples/10_fastapi_server.py`: Standalone Winsock2 HTTP REST API server with JSON parsing.
  - `examples/11_python314_315_features.py`: Demonstration of Python 3.14/3.15 dynamic version detection, `TypeAlias`, `sumprod`, `batched`, and `cpu_count`.

### Changed
- **Elimination of Legacy Template Overrides**:
  - Completely removed hardcoded canvas and quadratic equation template fallback routines. All GUI, graphics, plotting, and general algorithms now compile strictly and authentically from user AST directly into native x86-64 machine code.
- **CustomTkinter & Flet Deep Native Parity**:
  - Added support for `CTkFont` and `CTkImage` constructors.
  - Routed `entry.insert(0, val)` and `entry.delete(0, "end")` safely through Win32 Edit control messages (`EM_SETSEL`, `EM_REPLACESEL`), preventing memory access violations (0xC0000005) caused by list operations.
  - Added `widget.cget(...)` property inspection via unified Win32 runtime (`_pyfasm_unified_get`).
  - Added Flet lifecycle methods and window management: `page.clean()`, `page.add(...)`, `page.window_width`, `page.window_height` (routed to `_pyfasm_resize_window`), and safe no-ops for theme styling.
  - Event dispatch: added resolution for `e.control` and `control.value`.
  - Registered modern UI container components (`Container`, `Card`, `Row`, `Column`, `Stack`, `Divider`, `AppBar`, `Slider`, `ProgressBar`, `Tabs`, `Tab`, `ComboBox`, `OptionMenu`, `ScrollableFrame`).

### Fixed
- Fixed critical register clobber bug in `_pyfasm_auto_to_str`: `call _pyfasm_is_utf8_str_ptr` had its return register `rax` immediately clobbered by `mov rax, rbx`, which caused any non-zero integer to be misidentified as a string pointer and threw 0xC0000005 in `_pyfasm_str_concat`.
- Fixed raw memory indexing for `alloc_memory`, `malloc`, and `VirtualAlloc` by correctly typing returns as `TYPE_PTR` (`mov [r8 + r11 * 8], rax` instead of Python list header offset `(r11 + 1) * 8`).
- Fixed `ParsedModule.is_modern_gui` missing setter when overriding subsystem in `compiler.py`.

---

## [1.0.0] - 2026-11-20

### Added
- **Native Python GUI Ecosystem Parity**:
  - Direct native Win64 compilation for `tkinter`, `customtkinter`, `PyQt5`, `PyQt6` / `PySide6`, and `flet`.
  - Native Windows GDI controls (labels, buttons, entry inputs, checkboxes, sliders, canvases), dark-mode styling, dynamic geometry / layout management, window resize/show/destroy lifecycle, and event callbacks.
  - Native `StringVar` data binding and Canvas vector drawing (`create_line`, `create_rectangle`, `create_oval`, `create_text`).
- **Native 2D Game Engine (`pygame`)**:
  - Full native x86-64 GDI double-buffered backbuffer rendering with zero external DLLs or heavyweight runtime engines.
  - `pygame.display` (`set_mode`, `set_caption`, `flip`, `update`), `pygame.event` (`get`, `poll`, `QUIT`, `KEYDOWN`, `KEYUP`, `MOUSEBUTTONDOWN`, `MOUSEBUTTONUP`), and `pygame.key` (`get_pressed`, arrow keys, space, escape, WASD).
  - High-performance `pygame.Rect` geometry and collision engine (`colliderect`, `collidepoint`, `contains`, `clamp`, `inflate`, `x`, `y`, `w`, `h`, `centerx`, `centery`, `right`, `bottom`).
  - Native `pygame.draw` (antialiased/solid `rect`, `circle`, `line`, `polygon`), `pygame.time.Clock` (`tick` with microsecond-accurate Win32 timer pacing), and `pygame.font` raster text blitting.
- **Native Async Web APIs (`FastAPI` & `uvicorn`)**:
  - Direct native compilation of FastAPI applications (`FastAPI()`, `@app.get(...)`, `@app.post(...)`, `@app.put(...)`, `@app.delete(...)`, `uvicorn.run(app, host=..., port=...)`).
  - High-throughput native Win64 Winsock2 non-blocking/threaded HTTP/1.1 server.
  - Native RFC-8259 JSON parser & serializer for complex request bodies and responses (dictionaries, lists, floats, ints, booleans, nulls, and nested structures) with automated memory inspection and Content-Length multi-chunk streaming.
- **Recursive Nested Closures & Function Aliases**:
  - Support for recursive nested functions (`def _fib(n): ... _fib(n-1)`), mutually-recursive sibling functions (`is_even` / `is_odd`), and capturing closures without `W3001` / `E3001` unresolved symbol diagnostics.
  - Function-alias type propagation across variable assignments (`fn = my_func; res = fn(...)`).
- **Reflected Binary Magic Methods & Advanced F-String Format Specifiers**:
  - Full support for reflected dunders (`__radd__`, `__rsub__`, `__rmul__`, `__rtruediv__`, `__rfloordiv__`, `__rmod__`) and `__abs__`.
  - Comprehensive f-string format specifications (`:.Nf`, `:N.Mf`, `:x`, `:X`, `:b`, `:o`, `:0Nd`, `:Nd`) and `!r` `repr()` conversions.

---

## [0.4.0] - 2026-11-15

### Added
- **Full UTF-8/Cyrillic Identifiers & Strings**:
  - Collision-free Cyrillic/Unicode identifiers for classes, functions, and variables, plus UTF-8 codepoint `len()`, indexing `s[i]` (including negative indices), slicing `s[start:stop:step]`, and Cyrillic `.upper()`/`.lower()` (including `Ё`/`ё`).
  - Memory-address-free printing and formatting across typed/heterogeneous lists, 2D lists, tuples, dicts, sets, loops, f-strings, `str()`/`int()`/`float()` casts, and `.split()`.
- **Production OOP & Polymorphic Dispatch**:
  - Runtime class tags (`PYFCLSTG`), polymorphic virtual method dispatch (`_pyfasm_vcall_*`), `@staticmethod`, `@classmethod` (with dynamic `cls(...)`), `isinstance()`/`issubclass()`, and wired dunders (`__call__`, `__bool__`, `__neg__`/`__pos__`/`__invert__`, `__iadd__`..`__ixor__`, `__enter__`/`__exit__`, `__iter__`/`__next__` + `StopIteration`).
- **Lexical Closures**:
  - Dynamic closures (`PYFCLOSU`) for capturing `lambda` and nested `def` functions across direct calls, higher-order indirect calls, `map()`, and `filter()`.
- **NanoGEMM & SIMD Engine**:
  - Built-in AVX2/FMA native matrix multiplication (`@` / `matmul`) and NumPy-compatible helpers (`zeros`, `ones`, `asarray`, `flatnonzero`).

---

## [0.3.4] - 2026-11-10

### Added
- Automatic Windows console UTF-8 (`CP_UTF8` / `WriteConsoleW` / `ReadConsoleW`) with pipe-safe `WriteFile` / `ReadFile` fallback so Cyrillic and Unicode `input()` / `print()` render cleanly without mojibake.
- Proper `TYPE_STR` inference for `input()`, full `+` string concatenation for `ast.JoinedStr` f-strings, and native `float` (`_pyfasm_float_to_str`) / `__str__` formatting inside f-strings.

---

## [0.3.3] - 2026-11-05

### Added
- Full Microsoft x64 callee-saved register preservation in generated functions and Win64/Linux/macOS runtime routines.
- Dummy-safe PE64 `.reloc` sections for ASLR and simultaneous multi-DLL loading via `ctypes`.
- Exact Python floor division (`//`) and modulo (`%`) sign semantics, exact IEEE-754 float literal pooling, zero-padded `print_float`, thread-safe heap-allocated `str(int)`, and bounded dictionary/set probing with tombstone reuse.
- Structured compiler diagnostics (`error[E1001]`–`E4002`, `warning[W2004]`–`W3001`), pre-flight validation command `pyfasm64 check`, and `--strict` mode.
- PEP 561 `py.typed` markers, `python -m pyfasm64` / `python -m pyfasm` execution, and reliable `--no-asm` / `--dir-mode` builds.

---

## [0.1.14] - 2026-10-20

### Added
- Bundled and integrated FASM Modern SDK (`fasm-modern-sdk v1.73.36` and `fasmg v0.0.26`).
- Pre-packaged standalone compiler binaries (`FASM.EXE`, `fasmg.exe`, `fasm.x64`, `fasm.darwin`, `fasm`) and standard Win64/Win32 includes (`win64a.inc`, `win32a.inc`).
- Modern SDK include modules: `ui_fluent.inc`, `json_fast.inc`, `net_https.inc`, `data_structures.inc`, `syntax_color.inc`.
- Integrated native runtime conversion (`_pyfasm_utf8_to_wide`), eliminating Windows Mojibake.
- Built-in interactive documentation CLI: `pyfasm docs`, `pyfasm docs --ru`, `pyfasm docs --open`.
