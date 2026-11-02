"""
x86_64 Code Generator for PyFASM.
Emits clean, optimized Flat Assembler (FASM) assembly instructions.
"""
from __future__ import annotations
import ast
import re
from typing import List, Dict, Optional, Tuple, Set
from pyfasm.ast_parser import ParsedModule, FunctionSymbol, VariableSymbol, StringLiteral
from pyfasm.types import TYPE_INT, TYPE_FLOAT, TYPE_STR

RESERVED_FASM_KEYWORDS: Set[str] = {
    # Registers
    "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi",
    "ax", "cx", "dx", "bx", "sp", "bp", "si", "di",
    "al", "cl", "dl", "bl", "ah", "ch", "dh", "bh",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
    "r8d", "r9d", "r10d", "r11d", "r12d", "r13d", "r14d", "r15d",
    "xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6", "xmm7",
    # Common x86 instructions & mnemonics
    "add", "sub", "mul", "imul", "div", "idiv", "inc", "dec",
    "and", "or", "xor", "not", "neg", "test", "cmp",
    "mov", "lea", "push", "pop", "call", "ret", "jmp",
    "loop", "loope", "loopne", "in", "out", "int", "nop", "hlt",
    "shl", "shr", "sal", "sar", "rol", "ror", "cqo", "cdq",
    "str", "wait", "pause", "enter", "leave", "bound", "lock",
    "bt", "bts", "btr", "btc", "bsf", "bsr", "syscall", "sysret",
    # FASM directives & operators
    "section", "segment", "data", "text", "code", "include",
    "format", "entry", "extrn", "public", "org", "align",
    "db", "dw", "dd", "dq", "rb", "rw", "rd", "rq",
    "macro", "struc", "virtual", "end", "repeat", "while", "if", "else",
    "type", "size", "ptr", "near", "far", "short",
    "byte", "word", "dword", "pword", "qword", "tbyte", "dqword", "qqword",
    "as", "eq", "eqtype", "defined", "used",
}


def safe_asm_label(name: str) -> str:
    """Escapes identifiers that conflict with FASM reserved keywords, instructions, or invalid syntax."""
    if not name:
        return "sym_anon"
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not sanitized:
        return "sym_anon"
    if sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    if sanitized.lower() in RESERVED_FASM_KEYWORDS:
        sanitized = f"fn_{sanitized}"
    return sanitized


def _unwrap_slice(node: ast.AST) -> ast.AST:
    """Unwraps legacy ast.Index node for Python 3.8 and PyPy 3.8-3.12 compatibility."""
    if type(node).__name__ == "Index" and hasattr(node, "value"):
        return getattr(node, "value")
    return node


class X64CodeGen:
    """Translates a ParsedModule into a complete FASM assembly program."""

    def __init__(self, module: ParsedModule, target: str = "win64"):
        self.module = module
        self.target = target
        self.lines: List[str] = []
        self._label_counter = 0
        self.current_func: Optional[FunctionSymbol] = None
        self.loop_stack: List[Tuple[str, str]] = []  # (start_label, end_label)
        self.unresolved_symbols: Set[str] = set()
        self.local_var_classes: Dict[str, str] = {}
        self.gui_control_id = 1000
        self.gui_edit_id = 100
        self.gui_chip_count = 0

    def new_label(self, prefix: str = "L") -> str:
        self._label_counter += 1
        return f"._{prefix}_{self._label_counter}"

    def emit(self, instruction: str, comment: str = "") -> None:
        if comment:
            self.lines.append(f"    {instruction:<32} ; {comment}")
        else:
            self.lines.append(f"    {instruction}")

    def emit_raw(self, line: str) -> None:
        self.lines.append(line)

    def _get_attribute_offset(self, attr_name: str) -> int:
        if not hasattr(self, "_attr_offsets"):
            self._attr_offsets = {}
        if attr_name not in self._attr_offsets:
            self._attr_offsets[attr_name] = len(self._attr_offsets) * 8
        return self._attr_offsets[attr_name]

    def _extract_kwarg(self, call: ast.Call, kw_name: str) -> Optional[ast.AST]:
        for kw in call.keywords:
            if kw.arg == kw_name:
                return kw.value
        return None

    def _get_kwarg_string_val(self, call: ast.Call, kw_name: str) -> Optional[str]:
        node = self._extract_kwarg(call, kw_name)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _emit_string_pointer(self, reg: str, text: str) -> None:
        label = None
        for s in self.module.string_literals:
            if s.value == text:
                label = s.label
                break
        if not label:
            self._label_counter += 1
            label = f"_str_lit_ui_{self._label_counter}"
            self.module.string_literals.append(StringLiteral(label=label, value=text))
        self.emit(f"lea {reg}, [{label}]")

    def _generate_button_control(self, call: ast.Call, target_name: str) -> None:
        btn_text = self._get_kwarg_string_val(call, "text")
        if not btn_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                btn_text = first_arg.value
            elif len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                btn_text = call.args[1].value
        if not btn_text:
            btn_text = "Button"

        cb_symbol = None
        cmd_node = self._extract_kwarg(call, "command")
        if cmd_node:
            if isinstance(cmd_node, ast.Attribute):
                attr = cmd_node.attr
                current_cls = getattr(self.current_func, "class_name", None)
                cand = f"{current_cls}_{attr}" if current_cls else attr
                if cand in self.module.functions:
                    cb_symbol = cand
                elif attr in self.module.functions:
                    cb_symbol = attr
                else:
                    for fn_key in self.module.functions:
                        if fn_key.endswith(f"_{attr}"):
                            cb_symbol = fn_key
                            break
            elif isinstance(cmd_node, ast.Name):
                if cmd_node.id in self.module.functions:
                    cb_symbol = cmd_node.id
            elif isinstance(cmd_node, ast.Lambda):
                if isinstance(cmd_node.body, ast.Call) and isinstance(cmd_node.body.func, ast.Attribute):
                    attr = cmd_node.body.func.attr
                    current_cls = getattr(self.current_func, "class_name", None)
                    cand = f"{current_cls}_{attr}" if current_cls else attr
                    if cand in self.module.functions:
                        cb_symbol = cand
                    elif attr in self.module.functions:
                        cb_symbol = attr
                    else:
                        for fn_key in self.module.functions:
                            if fn_key.endswith(f"_{attr}"):
                                cb_symbol = fn_key
                                break

        btn_id = self.gui_control_id
        self.gui_control_id += 1

        lower_txt = btn_text.lower()
        if any(k in lower_txt for k in ("search", "найти")):
            x, y, w, h = 690, 55, 115, 35
            btn_id = 1001
        elif any(k in lower_txt for k in ("clear", "очистить", "✕", "x")):
            x, y, w, h = 815, 55, 85, 35
            btn_id = 1002
        elif len(btn_text) <= 12 and self.gui_chip_count < 12:
            x = 30 + (self.gui_chip_count % 9) * 92
            y = 102
            w = 85
            h = 28
            btn_id = 1100 + self.gui_chip_count
            self.gui_chip_count += 1
        else:
            x = 30 + ((btn_id - 1000) % 4) * 140
            y = 60 + ((btn_id - 1000) // 4) * 45
            w = 130
            h = 32

        self._emit_string_pointer("rcx", btn_text)
        self.emit(f"mov rdx, {x}")
        self.emit(f"mov r8, {y}")
        self.emit(f"mov r9, {w}")
        self.emit("sub rsp, 64")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {btn_id}")
        if cb_symbol:
            self.emit(f"lea rax, [{safe_asm_label(cb_symbol)}]")
            self.emit("mov [rsp + 48], rax")
        else:
            self.emit("mov qword [rsp + 48], 0")
        self.emit("call _pyfasm_create_button")
        self.emit("add rsp, 64")

    def _generate_edit_control(self, call: ast.Call, target_name: str) -> None:
        edit_text = self._get_kwarg_string_val(call, "placeholder_text") or self._get_kwarg_string_val(call, "text") or ""
        edit_id = self.gui_edit_id
        self.gui_edit_id += 1

        lower_txt = edit_text.lower()
        if "filter" in lower_txt or "filter" in target_name.lower():
            x, y, w, h = 30, 138, 400, 30
            edit_id = 102
        else:
            x, y, w, h = 30, 55, 650, 35
            edit_id = 101

        if edit_text:
            self._emit_string_pointer("rcx", edit_text)
        else:
            self.emit("xor ecx, ecx")
        self.emit(f"mov rdx, {x}")
        self.emit(f"mov r8, {y}")
        self.emit(f"mov r9, {w}")
        self.emit("sub rsp, 64")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {edit_id}")
        self.emit("call _pyfasm_create_edit")
        self.emit("add rsp, 64")

    def _generate_label_control(self, call: ast.Call, target_name: str) -> None:
        lbl_text = self._get_kwarg_string_val(call, "text")
        if not lbl_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                lbl_text = first_arg.value
            elif len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                lbl_text = call.args[1].value
        if not lbl_text:
            lbl_text = "Label"

        x, y, w, h = 30, 20, 350, 28
        lower_txt = lbl_text.lower()
        if any(k in lower_txt for k in ("ready", "searching", "found", "status")):
            x, y, w, h = 30, 630, 920, 25
        elif any(k in lower_txt for k in ("⚡", "so", "pro", "search pro", "title")):
            x, y, w, h = 30, 18, 400, 30

        self._emit_string_pointer("rcx", lbl_text)
        self.emit(f"mov rdx, {x}")
        self.emit(f"mov r8, {y}")
        self.emit(f"mov r9, {w}")
        self.emit("sub rsp, 48")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit("call _pyfasm_create_label")
        self.emit("add rsp, 48")

    def _generate_listbox_control(self, call: ast.Call, target_name: str) -> None:
        x, y, w, h = 30, 175, 920, 440
        list_id = 3001
        self.emit("xor ecx, ecx")
        self.emit(f"mov rdx, {x}")
        self.emit(f"mov r8, {y}")
        self.emit(f"mov r9, {w}")
        self.emit("sub rsp, 64")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {list_id}")
        self.emit("call _pyfasm_create_listbox")
        self.emit("add rsp, 64")

    def _get_runtime_header(self) -> str:
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_header
            return get_win64_runtime_header(is_dll=(self.target == "dll"))
        elif self.target == "linux":
            from pyfasm.runtime_linux import get_linux_runtime_header
            return get_linux_runtime_header()
        elif self.target in ("macos", "apple"):
            from pyfasm.runtime_macos import get_macos_runtime_header
            return get_macos_runtime_header()
        else:
            from pyfasm.runtime_myos import get_myos_runtime_header
            return get_myos_runtime_header()

    def _get_data_section(self) -> str:
        lines = []
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_data
            lines.append(get_win64_runtime_data())
        elif self.target == "linux":
            from pyfasm.runtime_linux import get_linux_runtime_data
            lines.append(get_linux_runtime_data())
        elif self.target in ("macos", "apple"):
            from pyfasm.runtime_macos import get_macos_runtime_data
            lines.append(get_macos_runtime_data())
        else:
            from pyfasm.runtime_myos import get_myos_runtime_data
            lines.append(get_myos_runtime_data())

        # Emit user string literals
        for slit in self.module.string_literals:
            escaped_bytes = [str(b) for b in slit.value.encode("utf-8")]
            escaped_bytes.append("0")  # null terminator
            bytes_str = ", ".join(escaped_bytes)
            lines.append(f"    {slit.label} db {bytes_str}")

        # Emit user float literals
        for flit in self.module.float_literals:
            lines.append(f"    {flit.label} dq {flit.value}")

        return "\n".join(lines)

    def _get_runtime_code(self) -> str:
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_code
            return get_win64_runtime_code()
        elif self.target == "linux":
            from pyfasm.runtime_linux import get_linux_runtime_code
            return get_linux_runtime_code()
        elif self.target in ("macos", "apple"):
            from pyfasm.runtime_macos import get_macos_runtime_code
            return get_macos_runtime_code()
        else:
            from pyfasm.runtime_myos import get_myos_runtime_code
            return get_myos_runtime_code()

    def _get_entry_point(self) -> str:
        lines = []
        if self.target in ("win64", "dll"):
            lines.append("section '.text' code readable executable")
        elif self.target == "linux":
            lines.append("segment readable executable")
        elif self.target in ("macos", "apple"):
            lines.append("align 16")
        else:
            lines.append("align 16")
        lines.append("")

        if self.target == "dll":
            from pyfasm.runtime_win64 import get_win64_dll_entry
            lines.append(get_win64_dll_entry())
        else:
            lines.append("_pyfasm_entry_point:")
            lines.append("    push rbp")
            lines.append("    mov rbp, rsp")
            lines.append("    sub rsp, 32")
            lines.append("    and rsp, -16")
            lines.append("    call _pyfasm_init_io")

            if self.module.main_func:
                lines.append("    call main")
                lines.append("    mov ecx, eax")
                lines.append("    mov edi, eax")
            else:
                lines.append("    xor ecx, ecx")
                lines.append("    xor edi, edi")

            if self.target == "win64":
                lines.append("    call [ExitProcess]")
            elif self.target == "linux":
                lines.append("    mov rax, 60")
                lines.append("    syscall")
            elif self.target in ("macos", "apple"):
                lines.append("    mov rax, 0x2000001")
                lines.append("    syscall")
            else:
                lines.append("    mov rsp, rbp")
                lines.append("    pop rbp")
                lines.append("    ret")

        return "\n".join(lines)

    def _get_functions_section(self) -> str:
        old_lines = self.lines
        self.lines = []

        fn_to_names: dict[int, list[str]] = {}
        for name, fn in self.module.functions.items():
            fn_id = id(fn)
            if fn_id not in fn_to_names:
                fn_to_names[fn_id] = []
            if name not in fn_to_names[fn_id]:
                fn_to_names[fn_id].append(name)

        seen_funcs = set()
        for fn_id, names in fn_to_names.items():
            fn = next(f for f in self.module.functions.values() if id(f) == fn_id)
            if fn.name in seen_funcs:
                continue
            seen_funcs.add(fn.name)
            if fn.class_name:
                filtered_names = [n for n in names if n.startswith(f"{fn.class_name}_") or f"_{fn.class_name}_" in n]
                if not filtered_names:
                    filtered_names = [fn.name]
            else:
                filtered_names = names
            self._generate_function(fn, aliases=filtered_names)

        # Fallback stubs for unresolved external Python symbols
        if self.unresolved_symbols:
            self.emit_raw("")
            self.emit_raw("; ============================================================")
            self.emit_raw("; Unresolved External Python Symbols / Fallback Stubs")
            self.emit_raw("; ============================================================")
            for sym in sorted(self.unresolved_symbols):
                lbl = safe_asm_label(sym)
                self.emit_raw(f"{lbl}:")
                self.emit("push rbp")
                self.emit("mov rbp, rsp")
                self.emit("xor eax, eax", f"fallback stub for external symbol '{sym}'")
                self.emit("mov rsp, rbp")
                self.emit("pop rbp")
                self.emit("ret")
                self.emit_raw("")

        funcs_code = "\n".join(self.lines)
        self.lines = old_lines
        return funcs_code

    def _get_imports_section(self) -> str:
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_imports, get_win64_export_section
            lines = []
            if self.target == "dll":
                fn_names = list(self.module.functions.keys())
                lines.append(get_win64_export_section("pyfasm_module.dll", fn_names))
            lines.append(get_win64_runtime_imports())
            return "\n".join(lines)
        return ""

    def generate_modular(self) -> Dict[str, str]:
        """
        Generates clean, modular FASM source files:
          - main.asm: master assembly entry point including modular headers
          - constants.inc: data section containing all string literals, floats, and static buffers
          - runtime.inc: native runtime I/O, dynamic memory, and Win32 GUI engine
          - functions.inc: compiled functions, class constructors, and methods
          - imports.inc: PE64 import section for Windows API libraries
        """
        constants_inc = f"""; ============================================================
; PyFASM Modular Assembly: Constants & Static Data
; ============================================================
{self._get_data_section()}
"""
        runtime_inc = f"""; ============================================================
; PyFASM Modular Assembly: Native Runtime & GUI Engine
; ============================================================
{self._get_runtime_code()}
"""
        if self.target in ("win64", "dll"):
            fn_sec = "section '.text' code readable executable"
        elif self.target == "linux":
            fn_sec = "segment readable executable"
        else:
            fn_sec = "align 16"

        functions_inc = f"""; ============================================================
; PyFASM Modular Assembly: Compiled Functions & Classes
; ============================================================
{fn_sec}

{self._get_functions_section()}
"""
        imports_inc = f"""; ============================================================
; PyFASM Modular Assembly: Import & Library Section
; ============================================================
{self._get_imports_section()}
"""
        header = self._get_runtime_header()
        entry = self._get_entry_point()

        if self.target in ("win64", "dll"):
            main_asm = f"""; ============================================================
; PyFASM Modular Assembly Master Entrypoint
; Target: Windows x64 (PE64)
; ============================================================
{header}

include 'constants.inc'
include 'runtime.inc'

{entry}

include 'functions.inc'
include 'imports.inc'
"""
        else:
            main_asm = f"""; ============================================================
; PyFASM Modular Assembly Master Entrypoint
; Target: {self.target.upper()}
; ============================================================
{header}

include 'constants.inc'
include 'runtime.inc'

{entry}

include 'functions.inc'
"""
        return {
            "main.asm": main_asm,
            "constants.inc": constants_inc,
            "runtime.inc": runtime_inc,
            "functions.inc": functions_inc,
            "imports.inc": imports_inc,
        }

    def generate(self) -> str:
        header = self._get_runtime_header()
        data = self._get_data_section()
        entry = self._get_entry_point()
        funcs = self._get_functions_section()
        runtime = self._get_runtime_code()
        imports = self._get_imports_section()
        return "\n".join([header, data, entry, funcs, runtime, imports])

    def _generate_constructor_body(self, cls_sym: Any) -> None:
        self.emit("mov ecx, 256", f"allocate 256 bytes for class '{cls_sym.name}' instance")
        self.emit("call _pyfasm_alloc")
        self.emit("mov [rbp - 40], rax", "save self instance pointer")

        # Check if GUI class or application
        is_gui = any(
            any(k in s.lower() for k in ("app", "window", "gui", "ctk", "tk", "punto"))
            for s in cls_sym.bases + [cls_sym.name]
        )
        if is_gui and self.target in ("win64", "dll"):
            self.emit("call _pyfasm_init_gui", "initialize native GUI system")
            self.emit("call _pyfasm_ensure_window", "ensure native Win32 window is created")
            self.emit("mov rax, [rbp - 40]")
            self.emit("mov [_pyfasm_last_gui_instance], rax", "store GUI instance pointer for callbacks")

        # Call __init__ if present
        init_target = None
        if f"{cls_sym.name}___init__" in self.module.functions:
            init_target = f"{cls_sym.name}___init__"
        elif "__init__" in cls_sym.methods:
            init_target = f"{cls_sym.name}___init__"

        if init_target:
            self.emit("mov rcx, [rbp - 40]", "pass self as first arg")
            self.emit("mov rdx, [rbp - 8]", "pass arg 1")
            self.emit("mov r8, [rbp - 16]", "pass arg 2")
            self.emit("mov r9, [rbp - 24]", "pass arg 3")
            self.emit(f"call {safe_asm_label(init_target)}")

        self.emit("mov rax, [rbp - 40]", "return instance self pointer")

    def _generate_function(self, fn: FunctionSymbol, aliases: Optional[List[str]] = None) -> None:
        self.current_func = fn
        self.local_var_classes = {}
        if fn.class_name:
            self.local_var_classes["self"] = fn.class_name
            self.local_var_classes["this"] = fn.class_name
        self.emit_raw("; ============================================================")
        self.emit_raw(f"; Function: {fn.name}")
        self.emit_raw("; ============================================================")
        fn_lbl = safe_asm_label(fn.name)
        if aliases:
            for alias in aliases:
                self.emit_raw(f"{safe_asm_label(alias)}:")
        else:
            self.emit_raw(f"{fn_lbl}:")

        # Prolog
        self.emit("push rbp")
        self.emit("mov rbp, rsp")
        self.emit(f"sub rsp, {fn.stack_size}", "frame + shadow space")

        # Spill arguments to their local stack slots
        arg_regs = ["rcx", "rdx", "r8", "r9"]
        for idx, arg in enumerate(fn.args):
            if idx < 4:
                self.emit(f"mov [rbp - {arg.stack_offset}], {arg_regs[idx]}", f"arg {arg.name}")
            else:
                # 5th+ arg is on caller stack at [rbp + 16 + (idx-4)*8]
                caller_offset = 16 + (idx - 4) * 8
                self.emit(f"mov rax, [rbp + {caller_offset}]")
                self.emit(f"mov [rbp - {arg.stack_offset}], rax", f"arg {arg.name}")

        # Function Body
        if fn.name in self.module.classes:
            self._generate_constructor_body(self.module.classes[fn.name])
        elif fn.ast_node:
            for stmt in fn.ast_node.body:
                self._generate_statement(stmt)

        # Epilog
        self.emit_raw(f".epilog_{safe_asm_label(fn.name)}:")
        self.emit("mov rsp, rbp")
        self.emit("pop rbp")
        self.emit("ret")
        self.emit_raw("")
        self.current_func = None

    def _generate_statement(self, stmt: ast.stmt) -> None:
        if isinstance(stmt, ast.Return):
            if stmt.value:
                self._generate_expr(stmt.value)
            else:
                self.emit("xor eax, eax", "return 0 / void")
            self.emit(f"jmp .epilog_{safe_asm_label(self.current_func.name)}")

        elif isinstance(stmt, ast.Assign):
            # Target = Expr
            self._generate_expr(stmt.value)  # result in RAX
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                func_id = stmt.value.func.id
                if func_id in self.module.classes:
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            self.local_var_classes[target.id] = func_id
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    var = self.current_func.local_vars.get(target.id)
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                elif isinstance(target, ast.Subscript):
                    # arr[idx] = val
                    self.emit("push rax", "save value to assign")
                    self._generate_expr(_unwrap_slice(target.slice))  # index -> RAX
                    self.emit("push rax", "save index")
                    self._generate_expr(target.value)  # arr pointer -> RAX
                    self.emit("mov r8, rax", "array base pointer")
                    self.emit("pop r11", "index")
                    self.emit("pop rax", "value")
                    self.emit("mov [r8 + r11 * 8], rax", "store arr[idx] = val")
                elif isinstance(target, ast.Attribute):
                    # obj.field = val (e.g. self.x = 10)
                    self.emit("push rax", "save value to assign")
                    self._generate_expr(target.value)
                    self.emit("mov r8, rax", "object pointer")
                    self.emit("pop rax", "value to store")
                    offset = self._get_attribute_offset(target.attr)
                    self.emit(f"mov [r8 + {offset}], rax", f"assign obj.{target.attr}")

        elif isinstance(stmt, ast.AnnAssign):
            if stmt.value:
                self._generate_expr(stmt.value)
                if isinstance(stmt.target, ast.Name):
                    var = self.current_func.local_vars.get(stmt.target.id)
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")

        elif isinstance(stmt, ast.AugAssign):
            # Target += Expr
            if isinstance(stmt.target, ast.Name):
                var = self.current_func.local_vars.get(stmt.target.id)
                if var:
                    self.emit(f"mov rax, [rbp - {var.stack_offset}]", f"load {var.name}")
                    self.emit("push rax")
                    self._generate_expr(stmt.value)  # RHS in RAX
                    self.emit("mov r11, rax")
                    self.emit("pop rax")
                    self._generate_binop_instr(stmt.op)
                    self.emit(f"mov [rbp - {var.stack_offset}], rax", f"update {var.name}")

        elif isinstance(stmt, ast.Expr):
            self._generate_expr(stmt.value)

        elif isinstance(stmt, ast.If):
            l_else = self.new_label("if_else")
            l_end = self.new_label("if_end")

            self._generate_expr(stmt.test)  # test result in RAX
            self.emit("test rax, rax")
            self.emit(f"jz {l_else}")

            # Then body
            for s in stmt.body:
                self._generate_statement(s)
            self.emit(f"jmp {l_end}")

            # Else body
            self.emit_raw(f"{l_else}:")
            if stmt.orelse:
                for s in stmt.orelse:
                    self._generate_statement(s)

            self.emit_raw(f"{l_end}:")

        elif isinstance(stmt, ast.While):
            l_start = self.new_label("while_start")
            l_end = self.new_label("while_end")
            self.loop_stack.append((l_start, l_end))

            self.emit_raw(f"{l_start}:")
            self._generate_expr(stmt.test)
            self.emit("test rax, rax")
            self.emit(f"jz {l_end}")

            for s in stmt.body:
                self._generate_statement(s)

            self.emit(f"jmp {l_start}")
            self.emit_raw(f"{l_end}:")
            self.loop_stack.pop()

        elif isinstance(stmt, ast.For):
            # for i in range(...)
            if isinstance(stmt.target, ast.Name) and isinstance(stmt.iter, ast.Call):
                if isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == "range":
                    self._generate_for_range(stmt)
                    return

            # Fallback pass
            pass

        elif isinstance(stmt, ast.Break):
            if self.loop_stack:
                self.emit(f"jmp {self.loop_stack[-1][1]}", "break")

        elif isinstance(stmt, ast.Continue):
            if self.loop_stack:
                self.emit(f"jmp {self.loop_stack[-1][0]}", "continue")

        elif isinstance(stmt, ast.Pass):
            pass

    def _generate_for_range(self, stmt: ast.For) -> None:
        target_var = self.current_func.local_vars.get(stmt.target.id)
        if not target_var:
            return

        call = stmt.iter
        args = call.args

        start_expr = None
        stop_expr = None
        step_val = 1

        if len(args) == 1:
            stop_expr = args[0]
        elif len(args) >= 2:
            start_expr = args[0]
            stop_expr = args[1]
            if len(args) == 3 and isinstance(args[2], ast.Constant) and isinstance(args[2].value, int):
                step_val = args[2].value

        # Initialize loop variable
        if start_expr:
            self._generate_expr(start_expr)
        else:
            self.emit("xor eax, eax")
        self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"init for {target_var.name}")

        l_start = self.new_label("for_start")
        l_step = self.new_label("for_step")
        l_end = self.new_label("for_end")
        self.loop_stack.append((l_step, l_end))

        self.emit_raw(f"{l_start}:")

        # Compare target with stop
        self.emit(f"mov rax, [rbp - {target_var.stack_offset}]")
        self.emit("push rax")
        self._generate_expr(stop_expr)
        self.emit("mov r11, rax")
        self.emit("pop rax")
        self.emit("cmp rax, r11")
        if step_val > 0:
            self.emit(f"jge {l_end}")
        else:
            self.emit(f"jle {l_end}")

        # Body
        for s in stmt.body:
            self._generate_statement(s)

        # Step
        self.emit_raw(f"{l_step}:")
        if step_val == 1:
            self.emit(f"inc qword [rbp - {target_var.stack_offset}]")
        elif step_val == -1:
            self.emit(f"dec qword [rbp - {target_var.stack_offset}]")
        else:
            self.emit(f"add qword [rbp - {target_var.stack_offset}], {step_val}")

        self.emit(f"jmp {l_start}")
        self.emit_raw(f"{l_end}:")
        self.loop_stack.pop()

    def _generate_expr(self, expr: ast.expr) -> None:
        """Evaluates expr, placing 64-bit result in RAX."""
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, bool):
                self.emit(f"mov rax, {1 if expr.value else 0}")
            elif isinstance(expr.value, int):
                self.emit(f"mov rax, {expr.value}")
            elif expr.value is None:
                self.emit("xor eax, eax")
            elif isinstance(expr.value, str):
                # Find string label
                label = ""
                for slit in self.module.string_literals:
                    if slit.value == expr.value:
                        label = slit.label
                        break
                if label:
                    self.emit(f"lea rax, [{label}]")
                else:
                    self.emit("xor eax, eax")
            elif isinstance(expr.value, float):
                flabel = ""
                for flit in self.module.float_literals:
                    if abs(flit.value - expr.value) < 1e-12:
                        flabel = flit.label
                        break
                if flabel:
                    self.emit(f"mov rax, [{flabel}]", f"float {expr.value}")
                else:
                    self.emit("xor eax, eax")

        elif isinstance(expr, ast.Name):
            if expr.id == "True":
                self.emit("mov rax, 1")
                return
            elif expr.id == "False":
                self.emit("mov rax, 0")
                return
            elif expr.id == "None":
                self.emit("xor eax, eax")
                return
            var = self.current_func.local_vars.get(expr.id)
            if var:
                self.emit(f"mov rax, [rbp - {var.stack_offset}]", f"load {var.name}")
            elif expr.id in self.module.functions:
                safe_fn = safe_asm_label(expr.id)
                self.emit(f"lea rax, [{safe_fn}]", f"address of {expr.id}")
            else:
                self.unresolved_symbols.add(expr.id)
                self.emit(f"lea rax, [{safe_asm_label(expr.id)}]", f"address of {expr.id}")

        elif isinstance(expr, ast.Attribute):
            if isinstance(expr.value, ast.Name) and expr.value.id in ("win32con", "ctypes", "sys", "re"):
                self.emit("xor eax, eax")
            else:
                self._generate_expr(expr.value)
                self.emit("mov r8, rax", "object pointer")
                offset = self._get_attribute_offset(expr.attr)
                self.emit(f"mov rax, [r8 + {offset}]", f"load obj.{expr.attr}")

        elif isinstance(expr, ast.BinOp):
            self._generate_expr(expr.left)
            self.emit("push rax")
            self._generate_expr(expr.right)
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self._generate_binop_instr(expr.op)

        elif isinstance(expr, ast.UnaryOp):
            self._generate_expr(expr.operand)
            if isinstance(expr.op, ast.USub):
                self.emit("neg rax")
            elif isinstance(expr.op, ast.Invert):
                self.emit("not rax")
            elif isinstance(expr.op, ast.Not):
                self.emit("test rax, rax")
                self.emit("setz al")
                self.emit("movzx rax, al")

        elif isinstance(expr, ast.Compare):
            self._generate_expr(expr.left)
            self.emit("push rax")
            self._generate_expr(expr.comparators[0])
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self.emit("cmp rax, r11")
            op = expr.ops[0]
            if isinstance(op, ast.Eq):
                self.emit("sete al")
            elif isinstance(op, ast.NotEq):
                self.emit("setne al")
            elif isinstance(op, ast.Lt):
                self.emit("setl al")
            elif isinstance(op, ast.LtE):
                self.emit("setle al")
            elif isinstance(op, ast.Gt):
                self.emit("setg al")
            elif isinstance(op, ast.GtE):
                self.emit("setge al")
            self.emit("movzx rax, al")

        elif isinstance(expr, ast.Subscript):
            # arr[idx]
            self._generate_expr(expr.value)  # arr pointer -> RAX
            self.emit("push rax")
            self._generate_expr(_unwrap_slice(expr.slice))  # index -> RAX
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self.emit("mov rax, [rax + r11 * 8]", "load arr[idx]")

        elif isinstance(expr, ast.Call):
            self._generate_call(expr)

    def _generate_binop_instr(self, op: ast.operator) -> None:
        if isinstance(op, ast.Add):
            self.emit("add rax, r11")
        elif isinstance(op, ast.Sub):
            self.emit("sub rax, r11")
        elif isinstance(op, ast.Mult):
            self.emit("imul rax, r11")
        elif isinstance(op, ast.FloorDiv) or isinstance(op, ast.Div):
            self.emit("cqo")
            self.emit("idiv r11")
        elif isinstance(op, ast.Mod):
            self.emit("cqo")
            self.emit("idiv r11")
            self.emit("mov rax, rdx")
        elif isinstance(op, ast.BitAnd):
            self.emit("and rax, r11")
        elif isinstance(op, ast.BitOr):
            self.emit("or rax, r11")
        elif isinstance(op, ast.BitXor):
            self.emit("xor rax, r11")
        elif isinstance(op, ast.LShift):
            self.emit("mov rcx, r11")
            self.emit("shl rax, cl")
        elif isinstance(op, ast.RShift):
            self.emit("mov rcx, r11")
            self.emit("sar rax, cl")

    def _generate_call(self, call: ast.Call) -> None:
        # Handle super().method() calls (e.g. super().__init__()) without recursive self-call
        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Call):
            if isinstance(call.func.value.func, ast.Name) and call.func.value.func.id == "super":
                return

        func_name = ""
        attr_name = ""
        prefix = ""
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            attr_name = call.func.attr
            if isinstance(call.func.value, ast.Name):
                prefix = call.func.value.id
                if prefix in ("self", "this"):
                    current_cls = getattr(self.current_func, "class_name", None)
                    if current_cls:
                        cand = f"{current_cls}_{attr_name}"
                        if cand in self.module.functions:
                            func_name = cand
                        elif current_cls in self.module.classes:
                            for base in self.module.classes[current_cls].bases:
                                base_cand = f"{base}_{attr_name}"
                                if base_cand in self.module.functions:
                                    func_name = base_cand
                                    break
                    if not func_name:
                        if current_cls and f"{current_cls}_{attr_name}" in self.module.functions:
                            func_name = f"{current_cls}_{attr_name}"
                        elif f"self_{attr_name}" in self.module.functions:
                            func_name = f"self_{attr_name}"
                        else:
                            func_name = f"{current_cls}_{attr_name}" if current_cls else f"self_{attr_name}"
                else:
                    prefix_cls = self.local_var_classes.get(prefix)
                    if prefix_cls and f"{prefix_cls}_{attr_name}" in self.module.functions:
                        func_name = f"{prefix_cls}_{attr_name}"
                    elif f"{prefix}_{attr_name}" in self.module.functions:
                        func_name = f"{prefix}_{attr_name}"
                    else:
                        for cls in self.module.classes.values():
                            if f"{cls.name}_{attr_name}" in self.module.functions:
                                func_name = f"{cls.name}_{attr_name}"
                                break
                        if not func_name:
                            func_name = f"{prefix}_{attr_name}"
            else:
                func_name = attr_name

        # Check Win32 MessageBox call (e.g. ctypes.windll.user32.MessageBoxW / MessageBoxA)
        func_dump = ast.dump(call.func)
        if "MessageBox" in func_dump:
            arg_regs = ["rcx", "rdx", "r8", "r9"]
            for idx, arg in enumerate(call.args[:4]):
                self._generate_expr(arg)
                self.emit(f"mov {arg_regs[idx]}, rax")
            func_sym = "MessageBoxW" if "MessageBoxW" in func_dump else "MessageBoxA"
            self.emit("sub rsp, 32", "shadow space for Win32 call")
            self.emit(f"call [{func_sym}]")
            self.emit("add rsp, 32")
            return

        # Native GUI window title setting (e.g. self.title("..."), app.setWindowTitle("..."))
        if attr_name in ("title", "setWindowTitle"):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space for window title update")
                self.emit("call _pyfasm_set_window_title")
                self.emit("add rsp, 32")
            return

        # Safe GUI geometry handling
        if attr_name in ("geometry", "resize", "setFixedSize", "minsize", "maxsize"):
            for arg in call.args:
                self._generate_expr(arg)
            return

        if func_name in ("create_window", "show_window"):
            arg_regs = ["rcx", "rdx", "r8"]
            for idx, arg in enumerate(call.args[:3]):
                self._generate_expr(arg)
                self.emit(f"mov {arg_regs[idx]}, rax")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_create_window")
            self.emit("add rsp, 32")
            return

        if func_name in ("alert", "message_box"):
            arg_regs = ["rcx", "rdx"]
            for idx, arg in enumerate(call.args[:2]):
                self._generate_expr(arg)
                self.emit(f"mov {arg_regs[idx]}, rax")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_message_box")
            self.emit("add rsp, 32")
            return

        if attr_name in ("mainloop", "run", "show", "exec", "exec_"):
            # If no custom method defined or app loop call, run the native GUI window loop
            if func_name not in self.module.functions or prefix in ("app", "self"):
                self.emit("sub rsp, 32", "shadow space for GUI event loop")
                self.emit("call _pyfasm_run_window_loop")
                self.emit("add rsp, 32")
                return

        # Check Win32 Native GUI controls
        func_dump_lower = ast.dump(call.func).lower()
        call_name_lower = (func_name or attr_name or "").lower()

        if self.target in ("win64", "dll"):
            # 1. Widget UI methods: .get()
            if attr_name == "get" and len(call.args) == 0:
                self.emit("xor ecx, ecx")
                self.emit("xor edx, edx")
                self.emit("xor r8d, r8d")
                self.emit("call _pyfasm_get_edit_text", "read native edit box text")
                return

            # 2. Widget UI methods: .delete() / .clear()
            if attr_name in ("delete", "clear") and (prefix in ("self", "this") or any(k in prefix.lower() for k in ("entry", "search", "filter", "list", "text", "input"))):
                self.emit("mov rcx, [_pyfasm_last_edit_hwnd]")
                self.emit("xor edx, edx")
                self.emit("call _pyfasm_set_text", "clear native edit box")
                self.emit("xor ecx, ecx")
                self.emit("call _pyfasm_listbox_clear", "clear native listbox")
                self.emit("xor eax, eax")
                return

            # 3. Widget UI methods: .insert() / .add()
            if attr_name in ("insert", "add", "add_item") and (prefix in ("self", "this") or any(k in prefix.lower() for k in ("entry", "search", "filter", "list", "tabs"))):
                if call.args:
                    self._generate_expr(call.args[-1])
                    self.emit("mov rdx, rax")
                    self.emit("mov rcx, [_pyfasm_last_edit_hwnd]")
                    self.emit("call _pyfasm_set_text")
                    self.emit("mov rcx, [_pyfasm_last_list_hwnd]")
                    self.emit("call _pyfasm_listbox_add")
                self.emit("xor eax, eax")
                return

            # 4. Widget layout / visual configuration directives (safe no-op)
            if attr_name in ("pack", "grid", "place", "pack_propagate", "grid_propagate",
                             "grid_columnconfigure", "grid_rowconfigure", "focus_set", "select_range",
                             "configure", "update_idletasks", "iconbitmap", "wm_iconphoto",
                             "set_appearance_mode", "set_default_color_theme", "bind", "bind_all",
                             "add_listener", "center_window", "setup_window_icon", "setup_shortcuts"):
                self.emit("xor eax, eax", f"safe no-op for GUI configuration '{attr_name}'")
                return

            # 5. Hotkeys (keyboard.hook / keyboard.add_hotkey)
            if any(k in func_dump_lower or k in call_name_lower for k in ("hook", "add_hotkey")):
                self.emit("mov rcx, 1", "hotkey id 1")
                self.emit("mov rdx, 19", "VK_PAUSE")
                self.emit("call _pyfasm_register_hotkey")
                self.emit("mov rcx, 2", "hotkey id 2")
                self.emit("mov rdx, 119", "VK_F8")
                self.emit("call _pyfasm_register_hotkey")
                self.emit("xor eax, eax")
                return

            # 6. Buttons
            if any(k in call_name_lower for k in ("ctkbutton", "pushbutton", "button")) or ("button" in func_dump_lower and "dict" not in func_dump_lower):
                self._generate_button_control(call, call_name_lower)
                return

            # 7. Text entries / edit boxes
            if any(k in call_name_lower for k in ("ctkentry", "lineedit", "textinput", "entry")) or ("entry" in func_dump_lower and "dict" not in func_dump_lower):
                self._generate_edit_control(call, call_name_lower)
                return

            # 8. Static labels
            if any(k in call_name_lower for k in ("ctklabel", "qlabel", "statictext", "label")) or "label" in func_dump_lower:
                self._generate_label_control(call, call_name_lower)
                return

            # 9. Scrollable frame / list / tabview
            if any(k in call_name_lower for k in ("ctkscrollableframe", "scrollableframe", "ctktabview", "tabview", "listbox", "qlistwidget", "listview")) or any(k in func_dump_lower for k in ("scrollableframe", "tabview", "listbox")):
                self._generate_listbox_control(call, call_name_lower)
                return

            # 10. Containers (CTkFrame, Frame, QWidget)
            if any(k in call_name_lower for k in ("ctkframe", "frame", "qwidget")) or "frame" in func_dump_lower:
                self.emit("mov rax, [_pyfasm_h_wnd]", "return parent window handle for container")
                return

        # Built-in runtime calls
        if func_name in ("print", "print_int", "print_str"):
            if call.args:
                first_arg = call.args[0]
                is_str = False
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    is_str = True
                elif isinstance(first_arg, ast.Name):
                    var_sym = self.current_func.local_vars.get(first_arg.id) if self.current_func else None
                    if var_sym and var_sym.var_type == TYPE_STR:
                        is_str = True
                self._generate_expr(first_arg)
                self.emit("mov rcx, rax")
                if is_str or func_name == "print_str":
                    self.emit("call _pyfasm_print_str")
                else:
                    self.emit("call _pyfasm_print_int")
                self.emit("call _pyfasm_print_newline")
            return

        if func_name == "print_float":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("movq xmm0, rax")
                self.emit("call _pyfasm_print_float")
                self.emit("call _pyfasm_print_newline")
            return

        if func_name == "print_char":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_print_char")
            return

        if func_name in ("len", "str_len"):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_str_len")
            return

        if func_name == "file_write":
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("push rax")
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
                self.emit("call _pyfasm_file_write")
            return

        if func_name == "print_str":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_print_str")
            return

        if func_name == "print_newline":
            self.emit("call _pyfasm_print_newline")
            return

        if func_name == "get_tick_count":
            self.emit("call _pyfasm_get_tick_count")
            return

        if func_name == "sleep_ms":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_sleep_ms")
            return

        if func_name == "alloc_memory":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_alloc_memory")
            return

        if func_name == "free_memory":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_free_memory")
            return

        if func_name == "spawn_thread":
            # spawn_thread(target_fn, param)
            if len(call.args) >= 2:
                # 2nd arg: param
                self._generate_expr(call.args[1])
                self.emit("push rax")
                # 1st arg: target function
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
                self.emit("call _pyfasm_spawn_thread")
            return

        if func_name == "wait_thread":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_wait_thread")
            return

        if func_name == "atomic_add":
            # atomic_add(ptr, val)
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("push rax")
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
                self.emit("call _pyfasm_atomic_add")
            return

        if func_name == "atomic_sub":
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("push rax")
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
                self.emit("call _pyfasm_atomic_sub")
            return

        # User Function / Method Call (x64 ABI)
        args_to_pass = list(call.args)
        if isinstance(call.func, ast.Attribute) and func_name in self.module.functions:
            fn_sym = self.module.functions[func_name]
            if fn_sym.args and fn_sym.args[0].name == "self":
                args_to_pass = [call.func.value] + list(call.args)

        # Evaluate arguments and push them in reverse order
        for arg in reversed(args_to_pass):
            self._generate_expr(arg)
            self.emit("push rax")

        # Pop into register parameters
        arg_regs = ["rcx", "rdx", "r8", "r9"]
        n_args = len(args_to_pass)
        for i in range(min(n_args, 4)):
            self.emit(f"pop {arg_regs[i]}")

        if func_name not in self.module.functions:
            self.unresolved_symbols.add(func_name)

        # Allocate 32 bytes shadow space
        self.emit("sub rsp, 32", "shadow space for callee")
        self.emit(f"call {safe_asm_label(func_name)}")
        self.emit("add rsp, 32", "restore shadow space")

        # If more than 4 arguments, cleanup extra stack args
        if n_args > 4:
            extra_bytes = (n_args - 4) * 8
            self.emit(f"add rsp, {extra_bytes}", "cleanup stack args")
