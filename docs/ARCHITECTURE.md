# Compiler Architecture & Native ABI Internals

---

## 1. Compilation Pipeline

```text
  Python Source / Project Dir
              │
              ▼
  ┌───────────────────────┐
  │ AstAnalyzer           │  Recursive project & .venv/site-packages discovery
  │ (ast_parser.py)       │  Topological module init order + AST validation (E1xxx/E2xxx/W2xxx)
  │                       │  Preprocessing: ConstantFolder, GeneratorExpLifter, LambdaLifter, ...
  └───────────┬───────────┘
              │ ParsedModule (functions, classes, globals, literals, diagnostics)
              ▼
  ┌───────────────────────┐
  │ X64CodeGen            │  Win64 & System V x86-64 lowering
  │ (codegen_x64.py)      │  Automatic callee-saved register scanning & frame preservation
  │                       │  Inline PE64 .rsrc icons (icon_resource.py) + DLL .reloc section
  │                       │  Modular output: main.asm, constants.inc, runtime.inc, functions.inc, imports.inc
  └───────────┬───────────┘
              │ FASM Assembly + W3001 diagnostics
              ▼
  ┌───────────────────────┐
  │ PeepholeOptimizer     │  Safe push/pop collapse, redundant reload & dead-store elimination
  │ (optimizer.py)        │
  └───────────┬───────────┘
              │
              ▼
  ┌───────────────────────┐
  │ FasmRunner / Exporter │  Host FASM execution (win64, dll, linux, macos, myos)
  │ (fasm_runner.py)      │  Or standalone FASM project export (build.bat / build.sh)
  └───────────────────────┘
```

---

## 2. Runtime Object Layouts (64-bit)

* **`int` / `bool`**: raw signed 64-bit value in a register or `[rbp - offset]`.
* **`float`**: 64-bit IEEE-754 double stored either in SSE `xmm*` registers or as bit patterns in `.data` / 8-byte stack slots.
* **`str`**: pointer to null-terminated UTF-8/ASCII C-string in `.data` or heap (`_pyfasm_alloc`). Operations check for `NULL` pointers before dereferencing.
* **`list` / `tuple`**: heap block `[qword length, qword item0, qword item1, ...]`. All elements live at `[ptr + 8 + idx*8]`.
* **`dict` / `set`**: open-addressing hash table with power-of-two capacity (`cap >= 256`):
  * Header: `[qword capacity, qword count]` (16 bytes)
  * Each slot (24 bytes): `[qword hash, qword key, qword value]`
  * Hash markers: `0` = empty slot, `-1` = tombstone (safely skipped during probes, reused on insert); real hashes are shifted away from `0` and `-1`.
  * Integer keys (including negative keys like `-1`) are distinguished from C-string pointers before calling `_pyfasm_str_cmp`.

---

## 3. x86-64 Calling Convention & ABI Safety

* **Windows PE64 / DLL**: Microsoft x64 calling convention (`RCX, RDX, R8, R9` + stack arguments from `[rbp + 48]`), mandatory 32-byte shadow space, 16-byte stack alignment before every `call`.
* **Automatic Callee-Saved Preservation**: `_generate_function()` scans generated function assembly lines for any writes/uses of `rbx, rsi, rdi, r12, r13, r14, r15` and allocates preservation slots *above* locals/shadow space and *below* `[rbp]` so stack-passed parameters `[rbp + 48 + ...]` never shift.
* **Dynamic Stack-Aligning Runtime Routines**: runtime functions that perform `and rsp, -16` allocate `rbp`-relative restore epilogues (`lea rsp, [rbp - N*8]`) before popping callee-saved registers, guaranteeing `rsp` and `rbx..r15` are never corrupted across calls.

---

## 4. Portable PE64 Resources & DLL Relocations

* **Inline Icon Embedding (`src/pyfasm/icon_resource.py`)**: parses multi-resolution `.ico` containers in Python and emits `RT_ICON` and `RT_GROUP_ICON` bytes directly via FASM `db`/`dw`/`dd`, avoiding FASM assembly-time `file icon_file:offset,size` reads that fail on cross-platform macOS FASM builds.
* **PE64 DLL `.reloc`**: emits a non-empty fixup section (`if $=$$ / dd 0, 8 / end if`) in both `generate()` and `generate_modular()` so Windows `LoadLibrary` / Python `ctypes` can relocate and load multiple PyFASM64 DLLs simultaneously in one process.
