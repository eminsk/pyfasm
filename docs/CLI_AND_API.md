# CLI & Python API Reference

---

## 1. Command-Line Interface (`pyfasm64` / `pyfasm`)

Both `pyfasm64` and `pyfasm` (or `python -m pyfasm64` / `python -m pyfasm`) invoke the same CLI entrypoint.

### Global Flags

* `-V`, `--version`: Prints `<prog> 0.4.0` and exits.

### `compile` — Compile Python file or project directory to a native binary

```bash
pyfasm64 compile <source> [OPTIONS]
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `source` | required | Path to a `.py` file or project directory |
| `-o`, `--output` | `<stem>.<ext>` | Output binary path (`.exe`, `.dll`, `.elf`, `.macho`, `.bin`) |
| `--target` | `win64` | Target platform: `win64`, `dll`, `linux`, `macos`, `apple`, `myos` |
| `--run` | `False` | Execute the compiled binary immediately after compilation |
| `--no-asm` | `False` | Do not keep the intermediate `asm/` directory |
| `--export-fasm`, `-f` | `None` | Export self-contained compilable FASM folder with build scripts (default folder name: `FASM`) |
| `--icon` | `None` | Path to `.ico` file for Win64/DLL `.rsrc` icon embedding (auto-detects `<project_dir>/icon.ico` if present) |
| `--strict` | `False` | Promote warnings (`W2004`, `W2005`, `W2006`, `W3001`) to hard errors |

### `check` — Validate compatibility and diagnostics without assembling

```bash
pyfasm64 check <source> [--target win64] [--strict]
```

Runs `AstAnalyzer` (including multi-file dependency resolution and syntax checks) and `X64CodeGen` without creating `asm/` outputs or running FASM. Exits `0` if no errors (or prints warnings to `stderr`), exits `1` on errors (or warnings when `--strict` is set).

### `emit-asm` — Emit FASM x86-64 assembly to stdout or file

```bash
pyfasm64 emit-asm <source> [-o out.asm] [--target win64] [--icon app.ico] [--strict]
```

Prints formatted diagnostics to `stderr` and exits `1` if errors are present (honoring `--strict`). Otherwise writes or prints complete FASM x64 assembly.

### `bundle` — Bundle a full Python project with a native FASM launcher

```bash
pyfasm64 bundle <project_dir> [OPTIONS]
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `project_dir` | required | Root directory of the Python project |
| `-e`, `--entry` | auto-detected | Path to entry script |
| `-o`, `--output` | `<project_name><ext>` | Output launcher executable |
| `--console` | `False` | Use console subsystem instead of Win32 GUI |
| `--target` | `win64` | `win64`, `linux`, `macos`, `apple` |
| `--include-bin` | `[]` | Repeatable path to extra binary tools (e.g. `ffmpeg.exe`) |
| `--include-venv` | `False` | Pack `.venv` into the self-extracting bundle |
| `--dir-mode` | `False` | Build a directory-wrapper launcher instead of single-file zip payload |
| `--export-fasm`, `-f` | `None` | Export standalone FASM launcher project |
| `--icon` | `None` | Path to `.ico` icon file |

### `clean` — Remove compiler & unpacked runtime caches

```bash
pyfasm64 clean [path] [--all | -a] [--apps] [--dry-run | -n]
```

### `docs` — Display or open built-in README documentation

```bash
pyfasm64 docs [--ru | --russian] [--open]
```

---

## 2. Python API (`import pyfasm64` or `import pyfasm`)

All public symbols are exported from both `pyfasm64` and `pyfasm`:

```python
from pyfasm64 import (
    __version__,
    PyFasmCompiler,
    ProjectBundler,
    CompilerDiagnostic,
    DiagnosticReport,
    PyFasmCompileError,
    FasmExporter,
    PeepholeOptimizer,
    optimize_fasm_code,
    main,
)
```

### `PyFasmCompiler`

```python
compiler = PyFasmCompiler(fasm_path=None, include_path=None)
```

* **`check_file(source_path, target="win64", strict=False) -> Tuple[bool, DiagnosticReport]`**
  Validates a file or project directory without invoking FASM. Updates `compiler.last_diagnostics`.
* **`compile_file(source_path, output_binary=None, target="win64", keep_asm=True, export_fasm_dir=None, icon_path=None, strict=False) -> Tuple[bool, str, str]`**
  Compiles a file or project directory. When compilation fails, returns `(False, "", formatted_diagnostics)` and populates `compiler.last_diagnostics`.
* **`compile_source_to_asm(source_code, target="win64", project_dir=None, icon_path=None, strict=False) -> str`**
  Compiles in-memory Python source to FASM assembly. Raises `PyFasmCompileError` on syntax errors, unsupported constructs, or strict-mode warnings.
* **`clean_cache(project_dir=None, clean_apps=False, clean_all=False, dry_run=False) -> Tuple[int, int, List[str]]`**
  Cleans generated caches and unpacked bundle directories.

### Diagnostics API (`pyfasm.diagnostics`)

* `CompilerDiagnostic(severity, code, message, file_path=None, lineno=None, col_offset=None, end_col_offset=None, source_line=None, hint=None)`
  Call `.format()` (or `str(diag)`) to render rustc/clang-style output with `--> file:line:col`, source excerpt, caret markers (`^` / `^^^`), and `= hint: ...`.
* `DiagnosticReport`: holds deduplicated diagnostics, with `.errors`, `.warnings`, `.has_errors`, `.has_warnings`, `.promote_warnings_to_errors()`, and `.format_all()`.
* `PyFasmCompileError`: exception carrying `.report` and `.diagnostics`.
