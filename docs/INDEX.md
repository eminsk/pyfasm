# PyFASM64 Documentation Hub

Welcome to the official documentation for **PyFASM64** (`pyfasm` / `pyfasm64`) — an Ahead-of-Time (AOT) compiler and bundler that compiles Python 3.8–3.16, Free-Threaded No-GIL (3.13t–3.16t), and PyPy source projects directly into standalone **pure x86-64 Flat Assembler (FASM)** binaries (Windows PE64 `.exe`, `.dll`, Linux ELF64, Apple macOS Mach-O 64, and bare-metal MyOS flat binaries).

---

## Documentation Guides

| Guide | Audience | Contents |
| :--- | :--- | :--- |
| [**Getting Started**](GETTING_STARTED.md) | New & existing users | Installation, single-file & multi-package project structure, DLL creation, cross-compilation, and bundling |
| [**Language & Compatibility Reference**](LANGUAGE_REFERENCE.md) | Developers writing native PyFASM64 code | Supported types, OOP, inheritance, `@property`, magic methods (dunders), imports, stdlib, and limits |
| [**CLI & Python API Reference**](CLI_AND_API.md) | Automation, CI & library users | All CLI commands (`compile`, `check`, `emit-asm`, `bundle`, `clean`, `docs`), `--strict`, and Python API |
| [**Compiler Diagnostics & Error Codes**](ERRORS.md) | Troubleshooting & strict builds | Full reference of `E1001`–`E4002` and `W2004`–`W3001` diagnostics with examples and fixes |
| [**Architecture & ABI Internals**](ARCHITECTURE.md) | Contributors & low-level engineers | Pipeline, memory layouts, Win64 / System V ABI, callee-saved preservation, PE64 `.rsrc` & `.reloc` |
| [**Полное руководство на русском языке (RU)**](GUIDE_RU.md) | Русскоязычные пользователи | Полный гайд: установка, структура проекта, классы и импорты, `check --strict` и диагностика ошибок |

---

## Quick Verification Workflow

```bash
# 1. Validate source or multi-file project before building
pyfasm64 check my_project/

# 2. Fail on warnings (external C-extension imports, unsupported dunders, unresolved symbols)
pyfasm64 check my_project/ --strict

# 3. Compile natively (Windows PE64 .exe by default)
pyfasm64 compile my_project/ --strict --run

# 4. Or bundle a full Python app with C-extension dependencies (pandas/torch/playwright/etc.)
pyfasm64 bundle my_project/ -e my_project/main.py --include-venv -o dist/app.exe
```

## Existing RFCs

* [Compiler Verification RFC (v0.2.0)](RFC_v020_COMPILER_VERIFICATION.md)
