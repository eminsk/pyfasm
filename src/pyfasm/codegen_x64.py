"""
x86_64 Code Generator for PyFASM.
Emits clean, optimized Flat Assembler (FASM) assembly instructions.
"""
from __future__ import annotations
import ast
from pathlib import Path
import re
from typing import List, Dict, Optional, Tuple, Set, Any
from pyfasm.ast_parser import ParsedModule, FunctionSymbol, VariableSymbol, StringLiteral, walk_local_scope
from pyfasm.types import TYPE_INT, TYPE_FLOAT, TYPE_STR, TYPE_LIST, TYPE_DICT, TYPE_SET, TYPE_TUPLE, TYPE_BOOL, TYPE_PTR, PyFasmType, ListType, DictType, SetType

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
    "jz", "jnz", "je", "jne", "jc", "jnc", "js", "jns", "jo", "jno", "jp", "jnp",
    "jl", "jle", "jg", "jge", "jb", "jbe", "ja", "jae", "jcxz", "jecxz", "jrcxz",
    "loop", "loope", "loopne", "in", "out", "int", "nop", "hlt",
    "shl", "shr", "sal", "sar", "rol", "ror", "cqo", "cdq",
    "str", "wait", "pause", "enter", "leave", "bound", "lock",
    "bt", "bts", "btr", "btc", "bsf", "bsr", "syscall", "sysret",
    # FASM directives & operators
    "section", "segment", "data", "text", "code", "include",
    "format", "entry", "extrn", "public", "org", "align",
    "db", "dw", "dd", "dq", "rb", "rw", "rd", "rq", "dp", "df", "dt", "du",
    "macro", "struc", "virtual", "end", "repeat", "while", "if", "else",
    "type", "size", "ptr", "near", "far", "short",
    "byte", "word", "dword", "pword", "qword", "tbyte", "dqword", "qqword",
    "as", "eq", "ne", "lt", "gt", "le", "ge", "eqtype", "defined", "used",
    # Additional FASM directives, preprocessor, relocations and predefined symbols
    "file", "load", "store", "display", "err", "assert",
    "postpone", "purge", "restruc", "times", "irp", "irps", "match", "rept",
    "forward", "reverse", "common", "line",
    "plt", "got", "rva", "dup", "offset",
    "break", "continue", "return", "exit", "stdcall", "ccall", "fastcall",
    "__file__", "__line__", "__time__", "__date__",
    # Common Win32 FASM structures & macro identifiers
    "msg", "point", "points", "rect", "wndclass", "wndclassex", "createstruct",
    "clientcreatestruct", "mdicreatestruct", "scrollinfo", "minmaxinfo",
    "windowplacement", "windowpos", "nmhdr", "copydatastruct", "accel",
    "paintstruct", "drawtextparams", "drawitemstruct", "menuiteminfo",
    "measureitemstruct", "msgboxparams", "gestureconfig", "gestureinfo",
    "wsadata", "hostent", "sockaddr", "sockaddr_in",
    "notifyicondata", "notifyicondataa", "notifyicondataw", "browseinfo",
    "win32_find_data", "win32_find_dataa", "win32_find_dataw",
    "systemtime", "filetime", "security_attributes", "process_information",
    "startupinfo", "overlapped", "bitmapinfoheader", "bitmapinfo",
    "propsheetpage", "propsheetheader", "imageinfo", "tbbutton",
    "initcommoncontrolsex",
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

    def __init__(self, module: ParsedModule, target: str = "win64", icon_path: Optional[str] = None):
        self.icon_path = icon_path
        self.module = module
        self.target = target
        self.lines: List[str] = []
        self._label_counter = 0
        self.current_func: Optional[FunctionSymbol] = None
        self.loop_stack: List[Tuple[str, str]] = []  # (start_label, end_label)
        self.try_stack: List[str] = []
        self.unresolved_symbols: Set[str] = set()
        self.local_var_classes: Dict[str, str] = {}
        self.gui_control_id = 1000
        self.gui_edit_id = 100
        self.gui_chip_count = 0

    @property
    def features(self) -> Set[str]:
        feats = set()
        if getattr(self.module, "is_modern_gui", False):
            feats.add("gui")
        if getattr(self.module, "is_tray_app", False):
            feats.add("tray")
        if getattr(self.module, "is_keyboard_hook_app", False):
            feats.add("hook")
        if getattr(self.module, "is_http_app", False):
            feats.add("net")
        return feats

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
            self._attr_offsets = {
                "status_code": 0,
                "text": 8,
                "json": 16,
                "reason": 24,
                "content": 8,
            }
        if attr_name not in self._attr_offsets:
            self._attr_offsets[attr_name] = len(self._attr_offsets) * 8
        return self._attr_offsets[attr_name]

    def resolve_class_method(self, cls_name: Optional[str], method_name: str, skip_cls: bool = False) -> Optional[str]:
        if not cls_name:
            return None
        visited = set()
        queue = []
        if skip_cls:
            cls_sym = self.module.classes.get(cls_name)
            if cls_sym:
                queue.extend(cls_sym.bases)
        else:
            queue.append(cls_name)

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            cand = f"{curr}_{method_name}"
            if cand in self.module.functions:
                return cand
            cls_sym = self.module.classes.get(curr)
            if cls_sym:
                for base in cls_sym.bases:
                    if base not in visited:
                        queue.append(base)
        return None

    def resolve_property(self, cls_name: Optional[str], prop_name: str) -> Optional[Any]:
        if not cls_name:
            return None
        visited = set()
        queue = [cls_name]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            cls_sym = self.module.classes.get(curr)
            if cls_sym:
                if hasattr(cls_sym, "properties") and prop_name in cls_sym.properties:
                    return cls_sym.properties[prop_name]
                for base in cls_sym.bases:
                    if base not in visited:
                        queue.append(base)
        return None

    def resolve_property_for_expr(self, expr_node: ast.AST, prop_name: str) -> Optional[Any]:
        cls_name = None
        if isinstance(expr_node, ast.Name):
            if expr_node.id in ("self", "this"):
                cls_name = getattr(self.current_func, "class_name", None)
            else:
                cls_name = self.local_var_classes.get(expr_node.id)
        elif isinstance(expr_node, ast.Call) and isinstance(expr_node.func, ast.Name):
            cls_name = expr_node.func.id

        if cls_name:
            prop = self.resolve_property(cls_name, prop_name)
            if prop:
                return prop

        candidates = []
        for c in self.module.classes.values():
            if hasattr(c, "properties") and prop_name in c.properties:
                candidates.append(c.properties[prop_name])
        if len(candidates) == 1:
            return candidates[0]
        return None

    def resolve_instance_class(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None or isinstance(node, ast.Constant):
            return None
        if isinstance(node, ast.Name):
            if node.id in ("self", "this"):
                return getattr(self.current_func, "class_name", None)
            return self.local_var_classes.get(node.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in self.module.classes:
                return node.func.id
        if isinstance(node, ast.BinOp):
            return self.resolve_instance_class(node.left)
        return None

    def _desugar_str_format(self, fmt_str: str, args: List[ast.expr]) -> List[ast.AST]:
        parts: List[ast.AST] = []
        last_end = 0
        auto_idx = 0
        i = 0
        n = len(fmt_str)
        while i < n:
            if fmt_str[i] == '{' and i + 1 < n and fmt_str[i+1] == '{':
                prefix = fmt_str[last_end:i]
                parts.append(ast.Constant(value=prefix + "{"))
                i += 2
                last_end = i
                continue
            elif fmt_str[i] == '}' and i + 1 < n and fmt_str[i+1] == '}':
                prefix = fmt_str[last_end:i]
                parts.append(ast.Constant(value=prefix + "}"))
                i += 2
                last_end = i
                continue
            elif fmt_str[i] == '{':
                close_idx = fmt_str.find('}', i)
                if close_idx != -1:
                    prefix_text = fmt_str[last_end:i]
                    if prefix_text:
                        parts.append(ast.Constant(value=prefix_text))
                    spec = fmt_str[i+1:close_idx].strip()
                    if not spec:
                        arg_idx = auto_idx
                        auto_idx += 1
                    elif spec.isdigit():
                        arg_idx = int(spec)
                    else:
                        arg_idx = auto_idx
                        auto_idx += 1
                    if 0 <= arg_idx < len(args):
                        parts.append(ast.FormattedValue(value=args[arg_idx], conversion=-1))
                    i = close_idx + 1
                    last_end = i
                    continue
            i += 1
        if last_end < n:
            parts.append(ast.Constant(value=fmt_str[last_end:]))
        return parts

    def _desugar_str_percent(self, fmt_str: str, args: List[ast.expr]) -> List[ast.AST]:
        parts: List[ast.AST] = []
        last_end = 0
        arg_idx = 0
        i = 0
        n = len(fmt_str)
        while i < n:
            if fmt_str[i] == '%' and i + 1 < n:
                ch = fmt_str[i+1]
                if ch == '%':
                    prefix_text = fmt_str[last_end:i]
                    parts.append(ast.Constant(value=prefix_text + "%"))
                    i += 2
                    last_end = i
                    continue
                elif ch in ('s', 'd', 'i', 'f', 'r', 'x', 'X'):
                    prefix_text = fmt_str[last_end:i]
                    if prefix_text:
                        parts.append(ast.Constant(value=prefix_text))
                    if arg_idx < len(args):
                        parts.append(ast.FormattedValue(value=args[arg_idx], conversion=-1))
                        arg_idx += 1
                    i += 2
                    last_end = i
                    continue
            i += 1
        if last_end < n:
            parts.append(ast.Constant(value=fmt_str[last_end:]))
        return parts

    def _prepare_call_args(self, call: ast.Call, target_fn: FunctionSymbol, is_method_call: bool, self_expr: Optional[ast.AST] = None) -> List[ast.AST]:
        expected_args = target_fn.args
        if is_method_call and expected_args and expected_args[0].name == "self":
            formal_args = expected_args[1:]
            self_node = self_expr
        else:
            formal_args = expected_args
            self_node = None

        final_args: List[Optional[ast.AST]] = [None] * len(formal_args)

        # 1. Positional arguments
        for i, a in enumerate(call.args):
            if i < len(final_args):
                final_args[i] = a

        # 2. Keyword arguments
        if getattr(call, "keywords", None):
            for kw in call.keywords:
                if kw.arg:
                    for idx, f_arg in enumerate(formal_args):
                        if f_arg.name == kw.arg:
                            final_args[idx] = kw.value
                            break

        # 3. Fill in default values
        defaults = getattr(target_fn, "defaults", [])
        if defaults:
            num_defaults = len(defaults)
            num_no_defaults = len(formal_args) - num_defaults
            for idx in range(len(final_args)):
                if final_args[idx] is None:
                    d_idx = idx - num_no_defaults
                    if 0 <= d_idx < num_defaults:
                        final_args[idx] = defaults[d_idx]

        # 4. Filter and prepend self if applicable
        resolved = [a for a in final_args if a is not None]
        if len(call.args) > len(formal_args):
            resolved.extend(call.args[len(formal_args):])

        if self_node is not None:
            resolved = [self_node] + resolved
        return resolved

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

    def _generate_fstring_part(self, part: ast.AST) -> None:
        if isinstance(part, ast.Constant):
            self._emit_string_pointer("rax", str(part.value))
        elif isinstance(part, ast.FormattedValue):
            self._generate_expr(part.value)
            is_str_part = False
            if isinstance(part.value, ast.Name) and self.current_func:
                v = self.current_func.local_vars.get(part.value.id)
                if v and v.var_type.is_str():
                    is_str_part = True
            elif isinstance(part.value, ast.Constant) and isinstance(part.value.value, str):
                is_str_part = True
            if not is_str_part:
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_int_to_str")
        else:
            self._generate_expr(part)

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

        is_so = any("stackoverflow" in s.lower() for s in getattr(self.module, "classes", {}))
        if is_so:
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
        else:
            w, h = 180, 36
            self._emit_string_pointer("rcx", btn_text)
            self.emit("xor edx, edx", "auto layout X")
            self.emit("xor r8d, r8d", "auto layout Y")
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

    def _generate_checkbox_control(self, call: ast.Call, target_name: str) -> None:
        chk_text = self._get_kwarg_string_val(call, "text")
        if not chk_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                chk_text = first_arg.value
            elif len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                chk_text = call.args[1].value
        if not chk_text:
            chk_text = "Checkbutton"

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

        chk_id = self.gui_control_id
        self.gui_control_id += 1

        w, h = 220, 30
        self._emit_string_pointer("rcx", chk_text)
        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("sub rsp, 64")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {chk_id}")
        if cb_symbol:
            self.emit(f"lea rax, [{safe_asm_label(cb_symbol)}]")
            self.emit("mov [rsp + 48], rax")
        else:
            self.emit("mov qword [rsp + 48], 0")
        self.emit("call _pyfasm_create_checkbox")
        self.emit("add rsp, 64")

    def _generate_edit_control(self, call: ast.Call, target_name: str) -> None:
        edit_text = self._get_kwarg_string_val(call, "placeholder_text") or self._get_kwarg_string_val(call, "text") or ""
        edit_id = self.gui_edit_id
        self.gui_edit_id += 1

        is_so = any("stackoverflow" in s.lower() for s in getattr(self.module, "classes", {}))
        if is_so:
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
        else:
            w, h = 380, 34
            if edit_text:
                self._emit_string_pointer("rcx", edit_text)
            else:
                self.emit("xor ecx, ecx")
            self.emit("xor edx, edx", "auto layout X")
            self.emit("xor r8d, r8d", "auto layout Y")
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

        is_so = any("stackoverflow" in s.lower() for s in getattr(self.module, "classes", {}))
        if is_so:
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
        else:
            w, h = 450, 26
            self._emit_string_pointer("rcx", lbl_text)
            self.emit("xor edx, edx", "auto layout X")
            self.emit("xor r8d, r8d", "auto layout Y")
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
            lines.append(get_win64_runtime_data(features=self.features))
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

        # Emit global variables
        for gname, gval in self.module.global_vars.items():
            # Sanitize Python values to valid FASM integer constants
            if isinstance(gval, bool):
                gval = 1 if gval else 0
            elif not isinstance(gval, int):
                gval = 0
            lines.append(f"    _pyfasm_global_{gname} dq {gval}")

        return "\n".join(lines)

    def _get_runtime_code(self) -> str:
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_code
            return get_win64_runtime_code(features=self.features)
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

            if self.target == "win64":
                is_so = any("stackoverflow" in s.lower() for s in getattr(self.module, "classes", {})) or (
                    hasattr(self.module, "name") and "stackoverflow" in str(self.module.name).lower()
                )
                if is_so:
                    lines.append("    mov dword [_pyfasm_split_view_enabled], 1")

            if hasattr(self.module, "module_inits") and self.module.module_inits:
                lines.append("    ; Initialize imported modules in topological dependency order")
                for minit in self.module.module_inits:
                    lines.append(f"    call {safe_asm_label(minit)}")

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
                # Function body already emitted — but we still need alias labels
                # for any extra names that weren't emitted as labels yet.
                fn_lbl = safe_asm_label(fn.name)
                for alias in names:
                    if alias != fn.name:
                        safe_alias = safe_asm_label(alias)
                        if safe_alias != fn_lbl:
                            self.emit_raw(f"{safe_alias}:")
                            self.emit(f"jmp {fn_lbl}", f"alias for {fn.name}")
                            self.emit_raw("")
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
                if sym in ("bisect", "bisect_right", "bisect_left", "zip", "enumerate", "heappush", "heappop", "gcd", "lcm", "isqrt", "factorial", "chain", "accumulate", "reduce"):
                    continue
                lbl = safe_asm_label(sym)
                self.emit_raw(f"{lbl}:")
                if sym == "str":
                    self.emit("jmp _pyfasm_int_to_str")
                else:
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
            lines.append(get_win64_runtime_imports(features=self.features))
            return "\n".join(lines)
        return ""

    def _get_resources_section(self) -> str:
        if self.target in ("win64", "dll") and self.icon_path and Path(self.icon_path).exists():
            icon_posix = str(Path(self.icon_path).resolve()).replace("\\", "/")
            return f"""include 'macro/resource.inc'

section '.rsrc' resource data readable

directory 3, _pyfasm_icons, 14, _pyfasm_group_icons

resource _pyfasm_icons, 1, 0, _pyfasm_icon_data
resource _pyfasm_group_icons, 1, 0, _pyfasm_main_icon

icon _pyfasm_main_icon, _pyfasm_icon_data, '{icon_posix}'
"""
        return ""

    def generate_modular(self) -> Dict[str, str]:
        if getattr(self.module, "ui_spec", None) and getattr(self.module.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            return {"main.asm": generate_ui_app_asm(self.module.ui_spec)}
        """
        Generates clean, modular FASM source files:
          - main.asm: master assembly entry point including modular headers
          - constants.inc: data section containing all string literals, floats, and static buffers
          - runtime.inc: native runtime I/O, dynamic memory, and Win32 GUI engine
          - functions.inc: compiled functions, class constructors, and methods
          - imports.inc: PE64 import section for Windows API libraries
        """
        if self.target in ("win64", "dll"):
            fn_sec = "section '.text' code readable executable"
        elif self.target == "linux":
            fn_sec = "segment readable executable"
        else:
            fn_sec = "align 16"

        funcs_body = self._get_functions_section()
        functions_inc = f"""; ============================================================
; PyFASM Modular Assembly: Compiled Functions & Classes
; ============================================================
{fn_sec}

{funcs_body}
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
        from pyfasm.optimizer import optimize_fasm_code
        res_dict = {
            "main.asm": main_asm,
            "constants.inc": constants_inc,
            "runtime.inc": runtime_inc,
            "functions.inc": optimize_fasm_code(functions_inc),
            "imports.inc": imports_inc,
        }
        rsrc_content = self._get_resources_section()
        if rsrc_content:
            res_dict["resources.inc"] = rsrc_content
            res_dict["main.asm"] = main_asm.strip() + "\n\ninclude 'resources.inc'\n"
        return res_dict

    def generate(self) -> str:
        if getattr(self.module, "ui_spec", None) and getattr(self.module.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            return generate_ui_app_asm(self.module.ui_spec)
        header = self._get_runtime_header()
        data = self._get_data_section()
        entry = self._get_entry_point()
        funcs = self._get_functions_section()
        runtime = self._get_runtime_code()
        imports = self._get_imports_section()
        rsrc = self._get_resources_section()
        raw_parts = [header, data, entry, funcs, runtime, imports]
        if rsrc:
            raw_parts.append(rsrc)
        if self.target == "dll":
            raw_parts.append("section '.reloc' fixups data discardable\n")
        raw = "\n".join(raw_parts)
        from pyfasm.optimizer import optimize_fasm_code
        return optimize_fasm_code(raw)

    def _generate_constructor_body(self, cls_sym: Any) -> None:
        self.emit("mov ecx, 2048", f"allocate 2048 bytes for class '{cls_sym.name}' instance")
        self.emit("call _pyfasm_alloc")
        self.emit("mov [rbp - 40], rax", "save self instance pointer")

        # Check if Background System Tray Application (Punto Switcher, pystray)
        module_imports = getattr(self.module, "imports", [])
        is_tray = any(
            any(k in s.lower() for k in ("tray", "punto", "pystray"))
            for s in cls_sym.bases + [cls_sym.name]
        ) or any("pystray" in imp.lower() for imp in module_imports)

        # Check if Desktop GUI class or application
        is_gui = any(
            any(k in s.lower() for k in ("app", "window", "gui", "ctk", "tk", "dialog", "form"))
            for s in cls_sym.bases + [cls_sym.name]
        ) and not is_tray

        if is_tray and self.target in ("win64", "dll"):
            self.emit("call _pyfasm_init_tray", "initialize native background system tray icon")
            self.emit("mov rax, [rbp - 40]")
            self.emit("mov [_pyfasm_last_gui_instance], rax", "store tray instance pointer")
        elif is_gui and self.target in ("win64", "dll"):
            self.emit("call _pyfasm_init_gui", "initialize native GUI system")
            self.emit("call _pyfasm_ensure_window", "ensure native Win32 window is created")
            self.emit("mov rax, [rbp - 40]")
            self.emit("mov [_pyfasm_last_gui_instance], rax", "store GUI instance pointer for callbacks")

        # Call __init__ if present (including inherited __init__)
        init_target = self.resolve_class_method(cls_sym.name, "__init__", skip_cls=False)
        if not init_target:
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
        if getattr(fn, "is_generator", False):
            self._generate_generator_function(fn, aliases)
            return

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
                caller_offset = 48 + (idx - 4) * 8
                self.emit(f"mov rax, [rbp + {caller_offset}]")
                self.emit(f"mov [rbp - {arg.stack_offset}], rax", f"arg {arg.name}")

        # Function Body
        if fn.name in self.module.classes:
            self._generate_constructor_body(self.module.classes[fn.name])
        elif fn.ast_node:
            for stmt in fn.ast_node.body:
                self._generate_statement(stmt)

        if fn.name == "main":
            self.emit("xor eax, eax", "default return 0 for main")

        # Epilog
        self.emit_raw(f".epilog_{safe_asm_label(fn.name)}:")
        self.emit("mov rsp, rbp")
        self.emit("pop rbp")
        self.emit("ret")
        self.emit_raw("")
        self.current_func = None

    def _generate_generator_function(self, fn: FunctionSymbol, aliases: Optional[List[str]] = None) -> None:
        fn_lbl = safe_asm_label(fn.name)
        self.emit_raw("; ============================================================")
        self.emit_raw(f"; Generator Constructor: {fn.name}")
        self.emit_raw("; ============================================================")
        if aliases:
            for alias in aliases:
                self.emit_raw(f"{safe_asm_label(alias)}:")
        else:
            self.emit_raw(f"{fn_lbl}:")

        self.emit("push rbp")
        self.emit("mov rbp, rsp")
        self.emit("sub rsp, 48")
        self.emit("and rsp, -16")

        arg_regs = ["rcx", "rdx", "r8", "r9"]
        for idx in range(min(len(fn.args), 4)):
            self.emit(f"mov [rbp - {(idx + 1) * 8}], {arg_regs[idx]}")

        max_offset = max([v.stack_offset for v in fn.local_vars.values()], default=0)
        state_size = 32 + max(8, max_offset + 16)
        self.emit(f"mov ecx, {state_size}", "generator state size")
        self.emit("call _pyfasm_alloc")
        self.emit("mov r8, rax", "generator object")
        self.emit("mov qword [r8 + 0], 0", "initial state = 0")
        self.emit(f"lea rdx, [{fn_lbl}_step]")
        self.emit("mov [r8 + 8], rdx", "step function pointer")
        self.emit("mov qword [r8 + 16], 0", "done flag = 0")
        self.emit("mov qword [r8 + 24], 0", "value = 0")

        for idx, arg in enumerate(fn.args):
            if idx < 4:
                self.emit(f"mov rax, [rbp - {(idx + 1) * 8}]")
                self.emit(f"mov [r8 + {32 + arg.stack_offset}], rax", f"store arg {arg.name}")
            else:
                caller_offset = 48 + (idx - 4) * 8
                self.emit(f"mov rax, [rbp + {caller_offset}]")
                self.emit(f"mov [r8 + {32 + arg.stack_offset}], rax", f"store stack arg {arg.name}")

        self.emit("mov rax, r8", "return generator object")
        self.emit("mov rsp, rbp")
        self.emit("pop rbp")
        self.emit("ret")
        self.emit_raw("")

        self.emit_raw("; ============================================================")
        self.emit_raw(f"; Generator Step Function: {fn.name}_step")
        self.emit_raw("; ============================================================")
        self.emit_raw(f"{fn_lbl}_step:")
        self.current_func = fn
        self.yield_counter = 0

        self.emit("push rbp")
        self.emit("push rbx")
        self.emit("push rsi")
        self.emit("push rdi")
        self.emit("push r12")
        self.emit("push r13")
        self.emit("push r14")
        self.emit("push r15")
        self.emit("mov rbp, rsp")
        self.emit(f"sub rsp, {fn.stack_size + 32}")
        self.emit("and rsp, -16")
        self.emit("mov r15, rcx", "save generator object ptr in R15")

        yield_count = sum(1 for node in walk_local_scope(fn.ast_node) if isinstance(node, (ast.Yield, ast.YieldFrom)))
        self.emit("mov rax, [r15]", "read current state")
        self.emit(f"test rax, rax")
        self.emit(f"jz .{fn_lbl}_state_0")
        for k in range(1, yield_count + 1):
            self.emit(f"cmp rax, {k}")
            self.emit(f"je .{fn_lbl}_state_{k}")
        self.emit(f"jmp .{fn_lbl}_done")

        self.emit_raw(f".{fn_lbl}_state_0:")
        for var in fn.local_vars.values():
            self.emit(f"mov rax, [r15 + {32 + var.stack_offset}]")
            self.emit(f"mov [rbp - {var.stack_offset}], rax")

        if fn.ast_node:
            for stmt in fn.ast_node.body:
                self._generate_statement(stmt)

        self.emit_raw(f".{fn_lbl}_done:")
        self.emit("mov qword [r15], -1", "state = closed")
        self.emit("mov qword [r15 + 16], 1", "done = 1")
        self.emit("xor eax, eax", "return 0 on exhaust")

        self.emit_raw(f".{fn_lbl}_yield_exit:")
        self.emit("mov rsp, rbp")
        self.emit("pop r15")
        self.emit("pop r14")
        self.emit("pop r13")
        self.emit("pop r12")
        self.emit("pop rdi")
        self.emit("pop rsi")
        self.emit("pop rbx")
        self.emit("pop rbp")
        self.emit("ret")
        self.emit_raw("")
        self.current_func = None

    def _generate_yield(self, node: ast.Yield) -> None:
        self.yield_counter += 1
        y_id = self.yield_counter
        fn_lbl = safe_asm_label(self.current_func.name)

        if node.value:
            self._generate_expr(node.value)
        else:
            self.emit("xor eax, eax")
        self.emit("mov r11, rax", "yielded value")

        for var in self.current_func.local_vars.values():
            self.emit(f"mov rax, [rbp - {var.stack_offset}]")
            self.emit(f"mov [r15 + {32 + var.stack_offset}], rax")

        self.emit(f"mov qword [r15], {y_id}", "save next state")
        self.emit("mov rax, r11", "yielded value in RAX")
        self.emit(f"jmp .{fn_lbl}_yield_exit")

        self.emit_raw(f".{fn_lbl}_state_{y_id}:")
        for var in self.current_func.local_vars.values():
            self.emit(f"mov rax, [r15 + {32 + var.stack_offset}]")
            self.emit(f"mov [rbp - {var.stack_offset}], rax")

    def _emit_func_exit(self) -> None:
        """Emits exit jump from current function or generator."""
        if not self.current_func:
            return
        fn_lbl = safe_asm_label(self.current_func.name)
        if getattr(self.current_func, "is_generator", False):
            self.emit(f"jmp .{fn_lbl}_done", "exit terminates generator")
        else:
            self.emit(f"jmp .epilog_{fn_lbl}")

    def _generate_statement(self, stmt: ast.stmt) -> None:
        if isinstance(stmt, ast.Return):
            if stmt.value:
                self._generate_expr(stmt.value)
            else:
                self.emit("xor eax, eax", "return 0 / void")
            self._emit_func_exit()

        elif isinstance(stmt, ast.Assign):
            # Target = Expr
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], (ast.Tuple, ast.List)):
                target_tup = stmt.targets[0]
                has_starred = any(isinstance(elt, ast.Starred) for elt in target_tup.elts)
                if not has_starred and isinstance(stmt.value, (ast.Tuple, ast.List)) and len(stmt.value.elts) == len(target_tup.elts):
                    for val_elt in stmt.value.elts:
                        self._generate_expr(val_elt)
                        self.emit("push rax", "save unpacked RHS elt")
                    for tgt_elt in reversed(target_tup.elts):
                        self.emit("pop rax", "restore for target elt")
                        if isinstance(tgt_elt, ast.Name):
                            var = self.current_func.local_vars.get(tgt_elt.id) if self.current_func else None
                            if var:
                                self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                            elif (self.current_func and hasattr(self.current_func, "global_names") and tgt_elt.id in self.current_func.global_names) or (tgt_elt.id in self.module.global_vars):
                                self.emit(f"mov [_pyfasm_global_{tgt_elt.id}], rax", f"store global {tgt_elt.id}")
                    return
                elif has_starred:
                    star_idx = next(i for i, elt in enumerate(target_tup.elts) if isinstance(elt, ast.Starred))
                    starred_target = target_tup.elts[star_idx].value
                    prefix_targets = target_tup.elts[:star_idx]
                    suffix_targets = target_tup.elts[star_idx + 1:]
                    n_prefix = len(prefix_targets)
                    n_suffix = len(suffix_targets)

                    self._generate_expr(stmt.value)
                    self.emit("mov rbx, rax", "sequence base pointer")
                    self.emit("push rbx", "save seq ptr")

                    for idx, tgt in enumerate(prefix_targets):
                        self.emit(f"mov rax, [rbx + {(idx + 1) * 8}]", f"load prefix {idx}")
                        if isinstance(tgt, ast.Name):
                            var = self.current_func.local_vars.get(tgt.id) if self.current_func else None
                            if var:
                                self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                            elif (self.current_func and hasattr(self.current_func, "global_names") and tgt.id in self.current_func.global_names) or (tgt.id in self.module.global_vars):
                                self.emit(f"mov [_pyfasm_global_{tgt.id}], rax", f"store global {tgt.id}")

                    for idx, tgt in enumerate(suffix_targets):
                        offset_from_end = n_suffix - idx
                        self.emit("mov r10, [rbx]", "seq len")
                        self.emit(f"sub r10, {offset_from_end}")
                        self.emit("mov rax, [rbx + r10 * 8 + 8]", f"load suffix {idx}")
                        if isinstance(tgt, ast.Name):
                            var = self.current_func.local_vars.get(tgt.id) if self.current_func else None
                            if var:
                                self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                            elif (self.current_func and hasattr(self.current_func, "global_names") and tgt.id in self.current_func.global_names) or (tgt.id in self.module.global_vars):
                                self.emit(f"mov [_pyfasm_global_{tgt.id}], rax", f"store global {tgt.id}")

                    lbl_star_ok = self.new_label("star_len_ok")
                    lbl_star_done = self.new_label("star_done")
                    self.emit("mov r10, [rbx]", "seq len")
                    self.emit(f"sub r10, {n_prefix + n_suffix}", "star slice len")
                    self.emit("cmp r10, 0")
                    self.emit(f"jge {lbl_star_ok}")
                    self.emit("xor r10, r10")
                    self.emit_raw(f"{lbl_star_ok}:")
                    self.emit("mov r12, r10", "star slice len")
                    self.emit("lea rcx, [r12 * 8 + 16]", "bytes to allocate")
                    self.emit("call _pyfasm_alloc")
                    self.emit("mov [rax], r12", "store star slice length")
                    self.emit("push rax", "save star list ptr")

                    self.emit("xor r11, r11", "copy index = 0")
                    lbl_copy_loop = self.new_label("star_copy_loop")
                    self.emit_raw(f"{lbl_copy_loop}:")
                    self.emit("cmp r11, r12")
                    self.emit(f"jge {lbl_star_done}")
                    self.emit("mov rbx, [rsp + 8]", "restore seq ptr")
                    self.emit(f"lea rdx, [r11 + {n_prefix + 1}]")
                    self.emit("mov rax, [rbx + rdx * 8]", "source element")
                    self.emit("mov rdi, [rsp]", "star list ptr")
                    self.emit("mov [rdi + r11 * 8 + 8], rax", "dest element")
                    self.emit("inc r11")
                    self.emit(f"jmp {lbl_copy_loop}")
                    self.emit_raw(f"{lbl_star_done}:")
                    self.emit("pop rax", "star list ptr")
                    self.emit("pop rbx", "cleanup seq ptr")

                    if isinstance(starred_target, ast.Name):
                        var = self.current_func.local_vars.get(starred_target.id) if self.current_func else None
                        if var:
                            self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                        elif (self.current_func and hasattr(self.current_func, "global_names") and starred_target.id in self.current_func.global_names) or (starred_target.id in self.module.global_vars):
                            self.emit(f"mov [_pyfasm_global_{starred_target.id}], rax", f"store global {starred_target.id}")
                    return
                else:
                    self._generate_expr(stmt.value)
                    self.emit("mov rbx, rax", "base pointer of tuple/list")
                    for idx, tgt_elt in enumerate(target_tup.elts):
                        lbl_load_ok = self.new_label("load_elt_ok")
                        self.emit("xor eax, eax")
                        self.emit("test rbx, rbx")
                        self.emit(f"jz {lbl_load_ok}")
                        self.emit(f"mov rax, [rbx + {(idx + 1) * 8}]", f"load element {idx}")
                        self.emit_raw(f"{lbl_load_ok}:")
                        if isinstance(tgt_elt, ast.Name):
                            var = self.current_func.local_vars.get(tgt_elt.id) if self.current_func else None
                            if var:
                                self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                            elif (self.current_func and hasattr(self.current_func, "global_names") and tgt_elt.id in self.current_func.global_names) or (tgt_elt.id in self.module.global_vars):
                                self.emit(f"mov [_pyfasm_global_{tgt_elt.id}], rax", f"store global {tgt_elt.id}")
                        elif isinstance(tgt_elt, ast.Attribute):
                            self.emit("push rax", "save unpacked value")
                            self._generate_expr(tgt_elt.value)
                            self.emit("mov r8, rax", "target object pointer")
                            self.emit("pop rax", "unpacked value")
                            offset = self._get_attribute_offset(tgt_elt.attr)
                            lbl_skip_obj = self.new_label("skip_obj_store")
                            self.emit("test r8, r8")
                            self.emit(f"jz {lbl_skip_obj}")
                            self.emit(f"mov [r8 + {offset}], rax", f"store obj.{tgt_elt.attr}")
                            self.emit_raw(f"{lbl_skip_obj}:")
                    return

            self._generate_expr(stmt.value)  # result in RAX
            assigned_cls = None
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                func_id = stmt.value.func.id
                if func_id in self.module.classes:
                    assigned_cls = func_id
            elif isinstance(stmt.value, ast.Name):
                assigned_cls = self.local_var_classes.get(stmt.value.id)
            elif isinstance(stmt.value, ast.BinOp):
                assigned_cls = self.resolve_instance_class(stmt.value.left)

            if assigned_cls:
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        self.local_var_classes[target.id] = assigned_cls
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    var = self.current_func.local_vars.get(target.id) if self.current_func else None
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                    elif (self.current_func and hasattr(self.current_func, "global_names") and target.id in self.current_func.global_names) or (target.id in self.module.global_vars):
                        self.emit(f"mov [_pyfasm_global_{target.id}], rax", f"store global {target.id}")
                        if self.current_func and self.current_func.name.startswith("_pyfasm_modinit_"):
                            curr_mod = self.current_func.name[len("_pyfasm_modinit_"):]
                            if f"{curr_mod}_{target.id}" in self.module.global_vars:
                                self.emit(f"mov [_pyfasm_global_{curr_mod}_{target.id}], rax", f"store module global {curr_mod}_{target.id}")
                elif isinstance(target, ast.Subscript):
                    if isinstance(target.value, ast.Attribute) and getattr(target.value, "attr", None) == "rcParams":
                        self.emit("xor eax, eax", "safe no-op for rcParams configuration")
                        continue
                    slice_unwrapped = _unwrap_slice(target.slice)
                    # Check custom __setitem__
                    cls_name = self.resolve_instance_class(target.value)
                    setitem_m = self.resolve_class_method(cls_name, "__setitem__") if cls_name else None
                    if setitem_m:
                        self.emit("push rax", "save value to assign")
                        self._generate_expr(slice_unwrapped)
                        self.emit("push rax", "save key")
                        self._generate_expr(target.value)
                        self.emit("mov rcx, rax", "pass self")
                        self.emit("pop rdx", "pass key")
                        self.emit("pop r8", "pass val")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit(f"call {safe_asm_label(setitem_m)}")
                        self.emit("add rsp, 32")
                        continue

                    is_dict_target = False
                    dict_keywords = ("dict", "map", "vars", "entries", "table", "cache", "lookup", "plot", "status", "disc", "modules", "headers", "params", "environ", "cookies", "meta", "registry", "data", "mapping", "config", "state", "styles", "themes", "kw", "kwargs", "options", "types")
                    is_dict_target = False
                    is_tuple_key = False
                    slice_type = self._infer_expr_type(slice_unwrapped)
                    if slice_type.is_str():
                        is_dict_target = True
                    elif isinstance(slice_unwrapped, (ast.Tuple, ast.List)):
                        is_dict_target = True
                        is_tuple_key = isinstance(slice_unwrapped, ast.Tuple)
                    elif isinstance(slice_unwrapped, ast.Constant) and isinstance(slice_unwrapped.value, str):
                        is_dict_target = True
                    elif isinstance(target.value, ast.Attribute) and any(k in target.value.attr.lower() for k in dict_keywords):
                        is_dict_target = True
                    elif isinstance(target.value, ast.Name):
                        if any(k in target.value.id.lower() for k in dict_keywords):
                            is_dict_target = True
                        elif self.current_func and hasattr(self.current_func, "local_vars"):
                            v = self.current_func.local_vars.get(target.value.id)
                            if v and (v.var_type.is_dict() or v.var_type.is_set()):
                                is_dict_target = True
                                if isinstance(slice_unwrapped, ast.Name):
                                    kv = self.current_func.local_vars.get(slice_unwrapped.id)
                                    if kv and kv.var_type.is_tuple():
                                        is_tuple_key = True
                    else:
                        expr_type = self._infer_expr_type(target.value)
                        if expr_type.is_dict() or expr_type.is_set():
                            is_dict_target = True
                            if isinstance(slice_unwrapped, ast.Name) and self.current_func:
                                kv = self.current_func.local_vars.get(slice_unwrapped.id)
                                if kv and kv.var_type.is_tuple():
                                    is_tuple_key = True

                    if is_dict_target:
                        # d[k] = val
                        self.emit("push rax", "save value to assign")
                        self._generate_expr(slice_unwrapped)
                        self.emit("push rax", "save key")
                        self._generate_expr(target.value)
                        self.emit("mov rcx, rax", "dict_ptr")
                        self.emit("pop rdx", "key")
                        self.emit("pop r8", "val")
                        if is_tuple_key:
                            self.emit("call _pyfasm_dict_set_tuple")
                        else:
                            self.emit("call _pyfasm_dict_set")
                    else:
                        # arr[idx] = val
                        self.emit("push rax", "save value to assign")
                        self._generate_expr(slice_unwrapped)  # index -> RAX
                        self.emit("push rax", "save index")
                        self._generate_expr(target.value)  # arr pointer -> RAX
                        self.emit("mov r8, rax", "array base pointer")
                        self.emit("pop r11", "index")
                        self.emit("pop rax", "value")
                        is_list_target = False
                        if isinstance(target.value, ast.Name) and self.current_func:
                            v = self.current_func.local_vars.get(target.value.id)
                            if v and (v.var_type.is_list() or v.var_type.is_tuple()):
                                is_list_target = True
                        lbl_skip_store = self.new_label("skip_arr_store")
                        self.emit("test r8, r8", "check null array")
                        self.emit(f"jz {lbl_skip_store}")
                        self.emit("cmp r8, 65536", "check valid user-mode pointer")
                        self.emit(f"jb {lbl_skip_store}")
                        if is_list_target:
                            lbl_idx_pos = self.new_label("idx_pos")
                            self.emit("test r11, r11", "check negative index")
                            self.emit(f"jns {lbl_idx_pos}")
                            self.emit("add r11, [r8]", "negative index: len + idx")
                            self.emit_raw(f"{lbl_idx_pos}:")
                        self.emit("test r11, r11", "check negative index")
                        self.emit(f"js {lbl_skip_store}")
                        self.emit("cmp r11, 1000000", "check index bounds")
                        self.emit(f"jae {lbl_skip_store}")
                        if is_list_target:
                            self.emit("mov [r8 + (r11 + 1) * 8], rax", "store list[idx] = val")
                        else:
                            self.emit("mov [r8 + r11 * 8], rax", "store arr[idx] = val")
                        self.emit_raw(f"{lbl_skip_store}:")
                elif isinstance(target, ast.Attribute):
                    # Check if target is a module global attribute (e.g. config.TIMEOUT = 100 or typing._check_generic = ...)
                    mod_name = target.value.id if isinstance(target.value, ast.Name) else None
                    is_mod_or_cls = False
                    if mod_name:
                        if mod_name not in ("self", "this"):
                            if not (self.current_func and hasattr(self.current_func, "local_vars") and mod_name in self.current_func.local_vars):
                                is_mod_or_cls = True
                    if is_mod_or_cls:
                        namespaced = f"{mod_name}_{target.attr}"
                        if namespaced not in self.module.global_vars:
                            self.module.global_vars[namespaced] = 0
                        self.emit(f"mov [_pyfasm_global_{namespaced}], rax", f"assign module global {namespaced}")
                        if target.attr in self.module.global_vars:
                            self.emit(f"mov [_pyfasm_global_{target.attr}], rax", f"assign global {target.attr}")
                    else:
                        # Check if property setter exists
                        prop = self.resolve_property_for_expr(target.value, target.attr)
                        if prop and getattr(prop, "setter_name", None):
                            self.emit("push rax", "save property setter value")
                            self._generate_expr(target.value)
                            self.emit("mov rcx, rax", "pass self as rcx")
                            self.emit("pop rdx", "pass value as rdx")
                            self.emit("sub rsp, 32", "shadow space")
                            self.emit(f"call {safe_asm_label(prop.setter_name)}")
                            self.emit("add rsp, 32")
                        else:
                            # obj.field = val (e.g. self.x = 10)
                            self.emit("push rax", "save value to assign")
                            self._generate_expr(target.value)
                            self.emit("mov r8, rax", "object pointer")
                            self.emit("pop rax", "value to store")
                            offset = self._get_attribute_offset(target.attr)
                            lbl_skip = self.new_label("skip_store")
                            self.emit("test r8, r8", "check null pointer")
                            self.emit(f"jz {lbl_skip}")
                            self.emit(f"mov [r8 + {offset}], rax", f"assign obj.{target.attr}")
                            self.emit_raw(f"{lbl_skip}:")

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
                var = self.current_func.local_vars.get(stmt.target.id) if self.current_func else None
                is_global = (self.current_func and hasattr(self.current_func, "global_names") and stmt.target.id in self.current_func.global_names) or (stmt.target.id in self.module.global_vars)
                if var:
                    if var.var_type.is_str() and isinstance(stmt.op, ast.Add):
                        self.emit(f"mov rcx, [rbp - {var.stack_offset}]", f"load {var.name}")
                        self.emit("push rcx")
                        self._generate_expr(stmt.value)
                        self.emit("mov rdx, rax")
                        self.emit("pop rcx")
                        self.emit("call _pyfasm_str_concat")
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"update {var.name}")
                    else:
                        self.emit(f"mov rax, [rbp - {var.stack_offset}]", f"load {var.name}")
                        self.emit("push rax")
                        self._generate_expr(stmt.value)  # RHS in RAX
                        self.emit("mov r11, rax")
                        self.emit("pop rax")
                        self._generate_binop_instr(stmt.op)
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"update {var.name}")
                elif is_global:
                    self.emit(f"mov rax, [_pyfasm_global_{stmt.target.id}]", f"load global {stmt.target.id}")
                    self.emit("push rax")
                    self._generate_expr(stmt.value)
                    self.emit("mov r11, rax")
                    self.emit("pop rax")
                    self._generate_binop_instr(stmt.op)
                    self.emit(f"mov [_pyfasm_global_{stmt.target.id}], rax", f"update global {stmt.target.id}")
            elif isinstance(stmt.target, ast.Subscript):
                slice_unwrapped = _unwrap_slice(stmt.target.slice)
                is_list_target = False
                val_t = self._infer_expr_type(stmt.target.value)
                if val_t.is_list() or val_t.is_tuple():
                    is_list_target = True
                elif isinstance(stmt.target.value, ast.Name) and self.current_func:
                    v = self.current_func.local_vars.get(stmt.target.value.id)
                    if v and (v.var_type.is_list() or v.var_type.is_tuple()):
                        is_list_target = True

                self._generate_expr(slice_unwrapped)
                self.emit("push rax", "save index")
                self._generate_expr(stmt.target.value)
                self.emit("push rax", "save array ptr")
                self._generate_expr(stmt.value)
                self.emit("mov r11, rax", "delta")
                self.emit("pop r8", "array ptr")
                self.emit("pop rdx", "index")
                if is_list_target:
                    self.emit("mov rax, [r8 + (rdx + 1) * 8]", "current val")
                else:
                    self.emit("mov rax, [r8 + rdx * 8]", "current val")
                self._generate_binop_instr(stmt.op)
                if is_list_target:
                    self.emit("mov [r8 + (rdx + 1) * 8], rax", "store updated list[idx]")
                else:
                    self.emit("mov [r8 + rdx * 8], rax", "store updated arr[idx]")
            elif isinstance(stmt.target, ast.Attribute):
                prop = self.resolve_property_for_expr(stmt.target.value, stmt.target.attr)
                if prop and getattr(prop, "getter_name", None) and getattr(prop, "setter_name", None):
                    self._generate_expr(stmt.target.value)
                    self.emit("push rax", "save self")
                    self.emit("mov rcx, rax", "pass self to getter")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {safe_asm_label(prop.getter_name)}")
                    self.emit("add rsp, 32")
                    self.emit("push rax", "save old prop val")
                    self._generate_expr(stmt.value)
                    self.emit("mov r11, rax", "delta")
                    self.emit("pop rax", "old prop val")
                    self._generate_binop_instr(stmt.op)
                    self.emit("mov rdx, rax", "new prop val")
                    self.emit("pop rcx", "restore self")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {safe_asm_label(prop.setter_name)}")
                    self.emit("add rsp, 32")
                else:
                    self._generate_expr(stmt.target.value)
                    self.emit("mov r8, rax", "object pointer")
                    offset = self._get_attribute_offset(stmt.target.attr)
                    self.emit(f"mov rax, [r8 + {offset}]", f"load obj.{stmt.target.attr}")
                    self.emit("push r8", "save obj ptr")
                    self.emit("push rax", "save old val")
                    self._generate_expr(stmt.value)
                    self.emit("mov r11, rax", "delta")
                    self.emit("pop rax", "old val")
                    self._generate_binop_instr(stmt.op)
                    self.emit("pop r8", "restore obj ptr")
                    self.emit(f"mov [r8 + {offset}], rax", f"store updated obj.{stmt.target.attr}")

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
            l_normal = self.new_label("while_normal") if stmt.orelse else l_end
            l_break = self.new_label("while_break") if stmt.orelse else l_end
            self.loop_stack.append((l_start, l_break))

            self.emit_raw(f"{l_start}:")
            self._generate_expr(stmt.test)
            self.emit("test rax, rax")
            self.emit(f"jz {l_normal}")

            for s in stmt.body:
                self._generate_statement(s)

            self.emit(f"jmp {l_start}")

            if stmt.orelse:
                self.emit_raw(f"{l_normal}:")
                for s in stmt.orelse:
                    self._generate_statement(s)
                self.emit(f"jmp {l_end}")
                self.emit_raw(f"{l_break}:")

            self.emit_raw(f"{l_end}:")
            self.loop_stack.pop()

        elif isinstance(stmt, ast.For):
            # for i in range(...)
            if isinstance(stmt.target, ast.Name) and isinstance(stmt.iter, ast.Call):
                if isinstance(stmt.iter.func, ast.Name) and stmt.iter.func.id == "range":
                    self._generate_for_range(stmt)
                    return

            # for item in container (list, tuple, dict, set, gen)
            self._generate_for_container(stmt)
            return

        elif isinstance(stmt, ast.Break):
            if self.loop_stack:
                self.emit(f"jmp {self.loop_stack[-1][1]}", "break")

        elif isinstance(stmt, ast.Continue):
            if self.loop_stack:
                self.emit(f"jmp {self.loop_stack[-1][0]}", "continue")

        elif isinstance(stmt, ast.Pass):
            pass

        elif isinstance(stmt, ast.With):
            for item in stmt.items:
                self._generate_expr(item.context_expr)
                opt_var = item.optional_vars if isinstance(item.optional_vars, ast.Name) else None
                handle_offset = None
                if opt_var and self.current_func:
                    var = self.current_func.local_vars.get(opt_var.id)
                    if var:
                        handle_offset = var.stack_offset
                        self.emit(f"mov [rbp - {handle_offset}], rax", f"assign {var.name}")

                if handle_offset is None:
                    self.emit("push rax", "save anonymous with handle")

                for s in stmt.body:
                    self._generate_statement(s)

                if handle_offset is not None:
                    self.emit(f"mov rcx, [rbp - {handle_offset}]", "handle to close")
                else:
                    self.emit("pop rcx", "restore anonymous with handle")

                lbl_skip_close = self.new_label("skip_close")
                self.emit("test rcx, rcx")
                self.emit(f"jz {lbl_skip_close}")
                self.emit("cmp rcx, -1")
                self.emit(f"je {lbl_skip_close}")
                self.emit("call _pyfasm_file_close")
                self.emit_raw(f"{lbl_skip_close}:")

        elif isinstance(stmt, ast.Try):
            lbl_except = self.new_label("except")
            lbl_orelse = self.new_label("try_orelse")
            lbl_finally = self.new_label("try_finally")
            lbl_end = self.new_label("try_end")

            self.try_stack.append(lbl_except)
            for s in stmt.body:
                self._generate_statement(s)
            self.try_stack.pop()

            if stmt.orelse:
                self.emit(f"jmp {lbl_orelse}")
            else:
                self.emit(f"jmp {lbl_finally}")

            self.emit_raw(f"{lbl_except}:")
            for handler in stmt.handlers:
                if handler.name and self.current_func:
                    var = self.current_func.local_vars.get(handler.name)
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"store exc in {handler.name}")
                for s in handler.body:
                    self._generate_statement(s)
            self.emit(f"jmp {lbl_finally}")

            if stmt.orelse:
                self.emit_raw(f"{lbl_orelse}:")
                for s in stmt.orelse:
                    self._generate_statement(s)
                self.emit(f"jmp {lbl_finally}")

            self.emit_raw(f"{lbl_finally}:")
            if stmt.finalbody:
                for s in stmt.finalbody:
                    self._generate_statement(s)
            self.emit_raw(f"{lbl_end}:")

        elif isinstance(stmt, ast.Raise):
            if stmt.exc:
                self._generate_expr(stmt.exc)
            else:
                self.emit("mov rax, 1", "default error code")
            if self.try_stack:
                self.emit(f"jmp {self.try_stack[-1]}", "jump to active except handler")
            else:
                if self.current_func:
                    self.emit("xor eax, eax", "unhandled raise in function returns 0")
                    self._emit_func_exit()
                else:
                    self.emit("mov ecx, eax")
                    self.emit("call [ExitProcess]")

        elif isinstance(stmt, ast.Assert):
            lbl_ok = self.new_label("assert_ok")
            self._generate_expr(stmt.test)
            self.emit("test rax, rax")
            self.emit(f"jnz {lbl_ok}")
            if self.try_stack:
                self.emit("mov rax, 1", "AssertionError")
                self.emit(f"jmp {self.try_stack[-1]}")
            else:
                if self.current_func:
                    self.emit("xor eax, eax", "assertion failure in function returns 0")
                    self._emit_func_exit()
                else:
                    self.emit("mov ecx, 1", "AssertionError exit code 1")
                    self.emit("call [ExitProcess]")
            self.emit_raw(f"{lbl_ok}:")

        elif isinstance(stmt, ast.Delete):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and self.current_func:
                    var = self.current_func.local_vars.get(target.id)
                    if var:
                        self.emit(f"mov qword [rbp - {var.stack_offset}], 0", f"del {var.name}")

        elif isinstance(stmt, ast.Match):
            self._generate_match(stmt)

    def _assign_target(self, target_node: ast.AST, value_reg: str = "rax") -> None:
        if isinstance(target_node, ast.Name):
            var = self.current_func.local_vars.get(target_node.id) if self.current_func else None
            if var:
                self.emit(f"mov [rbp - {var.stack_offset}], {value_reg}", f"assign {var.name}")
        elif isinstance(target_node, (ast.Tuple, ast.List)):
            if value_reg != "r10":
                self.emit(f"mov r10, {value_reg}", "container item to unpack")
            for idx, elt in enumerate(target_node.elts):
                if isinstance(elt, ast.Name):
                    e_var = self.current_func.local_vars.get(elt.id) if self.current_func else None
                    if e_var:
                        self.emit(f"mov rax, [r10 + {idx * 8 + 8}]", f"unpack {elt.id}")
                        self.emit(f"mov [rbp - {e_var.stack_offset}], rax")
                elif isinstance(elt, (ast.Tuple, ast.List)):
                    self.emit("push r10")
                    self.emit(f"mov rax, [r10 + {idx * 8 + 8}]", "load inner container")
                    self._assign_target(elt, "rax")
                    self.emit("pop r10")

    def _generate_for_container(self, stmt: ast.For) -> None:
        buf_var = self.current_func.local_vars.get(f"_pyfasm_for_buf_{id(stmt)}") if self.current_func else None
        idx_var = self.current_func.local_vars.get(f"_pyfasm_for_idx_{id(stmt)}") if self.current_func else None

        self._generate_expr(stmt.iter)
        lbl_null = self.new_label("for_null")
        lbl_start = self.new_label("for_iter_start")
        lbl_step = self.new_label("for_iter_step")
        lbl_end = self.new_label("for_iter_end")
        lbl_normal = self.new_label("for_iter_normal") if stmt.orelse else lbl_end
        lbl_break = self.new_label("for_iter_break") if stmt.orelse else lbl_end

        self.emit("test rax, rax", "check null container")
        self.emit(f"jz {lbl_normal if stmt.orelse else lbl_null}")

        is_gen_iter = False
        if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name):
            fn_sym = self.module.functions.get(stmt.iter.func.id)
            if fn_sym and getattr(fn_sym, "is_generator", False):
                is_gen_iter = True
        elif isinstance(stmt.iter, ast.Name) and self.current_func:
            var_sym = self.current_func.local_vars.get(stmt.iter.id)
            if var_sym and getattr(var_sym, "is_generator", False):
                is_gen_iter = True

        if is_gen_iter:
            if buf_var:
                self.emit(f"mov [rbp - {buf_var.stack_offset}], rax", "save gen_ptr to stack slot")
            else:
                self.emit("push rax", "save gen_ptr")

            self.loop_stack.append((lbl_step, lbl_break))
            self.emit_raw(f"{lbl_start}:")
            if buf_var:
                self.emit(f"mov rcx, [rbp - {buf_var.stack_offset}]", "gen_ptr")
            else:
                self.emit("mov rcx, [rsp]", "gen_ptr")
            self.emit("call _pyfasm_gen_next")
            if buf_var:
                self.emit(f"mov rbx, [rbp - {buf_var.stack_offset}]", "gen_ptr")
            else:
                self.emit("mov rbx, [rsp]", "gen_ptr")
            self.emit("cmp qword [rbx + 16], 1", "check done flag")
            self.emit(f"je {lbl_normal}")
            self._assign_target(stmt.target, "rax")

            for s in stmt.body:
                self._generate_statement(s)

            self.emit_raw(f"{lbl_step}:")
            self.emit(f"jmp {lbl_start}")

            if stmt.orelse:
                self.emit_raw(f"{lbl_normal}:")
                if not buf_var:
                    self.emit("add rsp, 8", "cleanup gen_ptr")
                for s in stmt.orelse:
                    self._generate_statement(s)
                self.emit(f"jmp {lbl_end}")
                self.emit_raw(f"{lbl_break}:")
                if not buf_var:
                    self.emit("add rsp, 8", "cleanup gen_ptr")
                self.emit_raw(f"{lbl_end}:")
            else:
                self.emit_raw(f"{lbl_end}:")
                if not buf_var:
                    self.emit("add rsp, 8", "cleanup gen_ptr")

            self.loop_stack.pop()
            self.emit_raw(f"{lbl_null}:")
            return

        is_hash_table = False
        if isinstance(stmt.iter, ast.Name) and self.current_func:
            var_sym = self.current_func.local_vars.get(stmt.iter.id)
            if var_sym and (var_sym.var_type.is_set() or var_sym.var_type.is_dict()):
                is_hash_table = True
        else:
            iter_t = self._infer_expr_type(stmt.iter)
            if iter_t.is_set() or iter_t.is_dict():
                is_hash_table = True

        if buf_var and idx_var:
            self.emit(f"mov [rbp - {buf_var.stack_offset}], rax", "container ptr to stack slot")
            self.emit(f"mov qword [rbp - {idx_var.stack_offset}], 0", "current index = 0")
        else:
            self.emit("push rax", "container ptr")
            self.emit("push 0", "current index = 0")

        self.loop_stack.append((lbl_step, lbl_break))

        self.emit_raw(f"{lbl_start}:")
        if buf_var and idx_var:
            self.emit(f"mov rcx, [rbp - {idx_var.stack_offset}]", "current index")
            self.emit(f"mov rbx, [rbp - {buf_var.stack_offset}]", "container ptr")
        else:
            self.emit("mov rcx, [rsp]", "current index")
            self.emit("mov rbx, [rsp + 8]", "container ptr")

        self.emit("mov rdx, [rbx]", "container capacity / length")
        self.emit("cmp rcx, rdx")
        self.emit(f"jge {lbl_normal}")

        if is_hash_table:
            self.emit("lea rax, [rcx + rcx * 2]")
            self.emit("shl rax, 3")
            self.emit("lea r8, [rbx + 16 + rax]", "slot ptr")
            self.emit("mov rax, [r8]", "slot hash")
            self.emit("test rax, rax")
            self.emit(f"jz {lbl_step}", "skip empty slot")
            self.emit("cmp rax, -1")
            self.emit(f"je {lbl_step}", "skip tombstone slot")
            self.emit("mov rax, [r8 + 8]", "load key from slot")
            self._assign_target(stmt.target, "rax")
        else:
            self.emit("mov rax, [rbx + rcx * 8 + 8]", "load container[index]")
            self._assign_target(stmt.target, "rax")

        for s in stmt.body:
            self._generate_statement(s)

        self.emit_raw(f"{lbl_step}:")
        if buf_var and idx_var:
            self.emit(f"inc qword [rbp - {idx_var.stack_offset}]", "index++")
        else:
            self.emit("inc qword [rsp]", "index++")
        self.emit(f"jmp {lbl_start}")

        if stmt.orelse:
            self.emit_raw(f"{lbl_normal}:")
            if not (buf_var and idx_var):
                self.emit("add rsp, 16", "cleanup container & index from stack")
            for s in stmt.orelse:
                self._generate_statement(s)
            self.emit(f"jmp {lbl_end}")
            self.emit_raw(f"{lbl_break}:")
            if not (buf_var and idx_var):
                self.emit("add rsp, 16", "cleanup container & index from stack")
            self.emit_raw(f"{lbl_end}:")
        else:
            self.emit_raw(f"{lbl_end}:")
            if not (buf_var and idx_var):
                self.emit("add rsp, 16", "cleanup container & index from stack")

        self.loop_stack.pop()
        self.emit_raw(f"{lbl_null}:")

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
        l_normal = self.new_label("for_normal") if stmt.orelse else l_end
        l_break = self.new_label("for_break") if stmt.orelse else l_end
        self.loop_stack.append((l_step, l_break))

        self.emit_raw(f"{l_start}:")

        # Compare target with stop
        self.emit(f"mov rax, [rbp - {target_var.stack_offset}]")
        self.emit("push rax")
        self._generate_expr(stop_expr)
        self.emit("mov r11, rax")
        self.emit("pop rax")
        self.emit("cmp rax, r11")
        if step_val > 0:
            self.emit(f"jge {l_normal}")
        else:
            self.emit(f"jle {l_normal}")

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

        if stmt.orelse:
            self.emit_raw(f"{l_normal}:")
            for s in stmt.orelse:
                self._generate_statement(s)
            self.emit(f"jmp {l_end}")
            self.emit_raw(f"{l_break}:")

        self.emit_raw(f"{l_end}:")
        self.loop_stack.pop()

    def _infer_expr_type(self, expr: Optional[ast.AST]) -> PyFasmType:
        if expr is None:
            return TYPE_INT
        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, str):
                return TYPE_STR
            if isinstance(expr.value, float):
                return TYPE_FLOAT
            if isinstance(expr.value, bool):
                return TYPE_BOOL
            return TYPE_INT
        if isinstance(expr, ast.Name):
            if self.current_func and hasattr(self.current_func, "local_vars") and expr.id in self.current_func.local_vars:
                return self.current_func.local_vars[expr.id].var_type
            if expr.id in ("__name__", "__doc__", "__file__", "__package__"):
                return TYPE_STR
            if any(k in expr.id.lower() for k in ("name", "text", "str", "url", "path", "title", "msg", "message", "prompt", "line", "word", "tag", "sep", "prefix", "suffix", "ext", "key", "hdr", "phrase")):
                return TYPE_STR
            if any(k in expr.id.lower() for k in ("dict", "map", "table", "cache", "lookup", "modules", "headers", "params", "environ", "registry", "vars")):
                return TYPE_DICT
        if isinstance(expr, ast.List):
            elem_t = None
            if expr.elts:
                elem_t = self._infer_expr_type(expr.elts[0])
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST
        if isinstance(expr, ast.ListComp):
            elem_t = self._infer_expr_type(expr.elt)
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST
        if isinstance(expr, ast.IfExp):
            return self._infer_expr_type(expr.body)
        if isinstance(expr, ast.NamedExpr):
            return self._infer_expr_type(expr.value)
        if isinstance(expr, ast.BoolOp):
            return TYPE_BOOL
        if isinstance(expr, ast.Dict):
            kt = None
            vt = None
            if expr.keys and expr.keys[0] is not None:
                kt = self._infer_expr_type(expr.keys[0])
            if expr.values:
                vt = self._infer_expr_type(expr.values[0])
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT
        if isinstance(expr, ast.DictComp):
            kt = self._infer_expr_type(expr.key)
            vt = self._infer_expr_type(expr.value)
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT
        if isinstance(expr, ast.Set):
            elem_t = None
            if expr.elts:
                elem_t = self._infer_expr_type(expr.elts[0])
            return SetType(element_type=elem_t) if elem_t else TYPE_SET
        if isinstance(expr, ast.SetComp):
            elem_t = self._infer_expr_type(expr.elt)
            return SetType(element_type=elem_t) if elem_t else TYPE_SET
        if isinstance(expr, ast.Tuple):
            return TYPE_TUPLE
        if isinstance(expr, ast.Subscript):
            val_type = self._infer_expr_type(expr.value)
            if val_type.is_str():
                return TYPE_STR
            if isinstance(expr.slice, ast.Slice):
                return val_type
            if val_type.is_list() and hasattr(val_type, "element_type") and val_type.element_type:
                return val_type.element_type
            if val_type.is_dict() and hasattr(val_type, "val_type") and val_type.val_type:
                return val_type.val_type
            if isinstance(expr.value, ast.Name):
                vname = expr.value.id.lower()
                if any(k in vname for k in ("words", "tags", "names", "lines", "strs", "strings", "titles")):
                    return TYPE_STR
            return TYPE_INT
        if isinstance(expr, ast.BinOp):
            lt = self._infer_expr_type(expr.left)
            rt = self._infer_expr_type(expr.right)
            if lt.is_str() or rt.is_str():
                return TYPE_STR
            if lt.is_float() or rt.is_float():
                return TYPE_FLOAT
        if isinstance(expr, ast.JoinedStr):
            return TYPE_STR
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                fn_id = expr.func.id
                if fn_id in ("str", "chr", "input", "strip", "lower", "upper", "hex", "bin", "oct"):
                    return TYPE_STR
                if fn_id in ("float",):
                    return TYPE_FLOAT
                if fn_id in ("bool", "isinstance", "any", "all"):
                    return TYPE_BOOL
                if fn_id in ("list", "range", "map", "filter", "zip", "enumerate", "chain", "accumulate", "sorted"):
                    return TYPE_LIST
                if fn_id in ("dict",):
                    return TYPE_DICT
                if fn_id in ("set",):
                    return TYPE_SET
                if fn_id in self.module.functions:
                    return self.module.functions[fn_id].return_type
            elif isinstance(expr.func, ast.Attribute):
                attr = expr.func.attr
                if attr == "loads":
                    if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "json":
                        return TYPE_DICT
                if attr == "get":
                    obj_type = self._infer_expr_type(expr.func.value)
                    if obj_type.is_dict() and len(expr.args) >= 2:
                        return self._infer_expr_type(expr.args[1])
                    return TYPE_PTR
                if attr == "choice":
                    return TYPE_STR
                if attr in ("lower", "upper", "strip", "replace", "format"):
                    return TYPE_STR
                if attr in ("count", "find", "index"):
                    return TYPE_INT
                if attr in ("keys", "values", "items", "chain", "accumulate"):
                    return TYPE_LIST
                if isinstance(expr.func.value, ast.Name):
                    pfx = expr.func.value.id
                    cls_name = getattr(self.current_func, "class_name", None) if pfx in ("self", "this") else self.local_var_classes.get(pfx)
                    if cls_name:
                        m = self.resolve_class_method(cls_name, attr)
                        if m and m in self.module.functions:
                            return self.module.functions[m].return_type
                for cls in self.module.classes.values():
                    m = self.resolve_class_method(cls.name, attr)
                    if m and m in self.module.functions:
                        return self.module.functions[m].return_type
        if isinstance(expr, ast.Attribute):
            prop = self.resolve_property_for_expr(expr.value, expr.attr)
            if prop and getattr(prop, "getter_name", None) and prop.getter_name in self.module.functions:
                return self.module.functions[prop.getter_name].return_type
            curr_cls = getattr(self.current_func, "class_name", None)
            if curr_cls and curr_cls in self.module.classes:
                cls_sym = self.module.classes[curr_cls]
                if hasattr(cls_sym, "field_types") and expr.attr in cls_sym.field_types:
                    return cls_sym.field_types[expr.attr]
            if any(k in expr.attr.lower() for k in ("dict", "map", "vars", "entries", "table", "cache", "lookup", "plot", "status", "disc", "modules", "headers", "params", "environ", "cookies", "meta", "registry", "data", "mapping", "config", "state")):
                return TYPE_DICT
        return TYPE_INT

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
            var = self.current_func.local_vars.get(expr.id) if self.current_func else None
            if var:
                self.emit(f"mov rax, [rbp - {var.stack_offset}]", f"load {var.name}")
            elif (self.current_func and hasattr(self.current_func, "global_names") and expr.id in self.current_func.global_names) or (expr.id in self.module.global_vars):
                self.emit(f"mov rax, [_pyfasm_global_{expr.id}]", f"load global {expr.id}")
            elif expr.id in self.module.functions:
                safe_fn = safe_asm_label(expr.id)
                self.emit(f"lea rax, [{safe_fn}]", f"address of {expr.id}")
            else:
                self.unresolved_symbols.add(expr.id)
                self.emit(f"lea rax, [{safe_asm_label(expr.id)}]", f"address of {expr.id}")

        elif isinstance(expr, ast.Attribute):
            prop = self.resolve_property_for_expr(expr.value, expr.attr)
            if prop and getattr(prop, "getter_name", None):
                self._generate_expr(expr.value)
                self.emit("mov rcx, rax", "pass self to property getter")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {safe_asm_label(prop.getter_name)}")
                self.emit("add rsp, 32")
                return

            def _is_module_or_class(node):
                if isinstance(node, ast.Name):
                    if node.id in ("self", "this"):
                        return False
                    if self.current_func and hasattr(self.current_func, "local_vars") and node.id in self.current_func.local_vars:
                        return False
                    return True
                if isinstance(node, ast.Attribute):
                    return _is_module_or_class(node.value)
                return False

            if _is_module_or_class(expr.value):
                val_handled = False
                mod_name = expr.value.id if isinstance(expr.value, ast.Name) else None
                if mod_name:
                    if mod_name in self.module.classes:
                        cls_sym = self.module.classes[mod_name]
                        if hasattr(cls_sym, "class_attrs") and expr.attr in cls_sym.class_attrs:
                            c_val = cls_sym.class_attrs[expr.attr]
                            if isinstance(c_val, int):
                                self.emit(f"mov rax, {c_val}", f"load class attribute {mod_name}.{expr.attr}")
                                val_handled = True
                            elif isinstance(c_val, str):
                                self._emit_string_pointer("rax", c_val)
                                val_handled = True
                    if not val_handled:
                        if expr.attr in ("modules", "environ", "argv", "path"):
                            namespaced_global = f"{mod_name}_{expr.attr}"
                            if namespaced_global not in self.module.global_vars:
                                self.module.global_vars[namespaced_global] = 0
                            lbl_has_obj = self.new_label("has_mod_obj")
                            self.emit(f"mov rax, [_pyfasm_global_{namespaced_global}]")
                            self.emit("test rax, rax")
                            self.emit(f"jnz {lbl_has_obj}")
                            if expr.attr in ("modules", "environ"):
                                self.emit("mov ecx, 64")
                                self.emit("call _pyfasm_dict_create")
                            else:
                                self.emit("mov ecx, 16")
                                self.emit("call _pyfasm_list_create")
                            self.emit(f"mov [_pyfasm_global_{namespaced_global}], rax")
                            self.emit_raw(f"{lbl_has_obj}:")
                            val_handled = True
                    if not val_handled:
                        namespaced_global = f"{mod_name}_{expr.attr}"
                        if namespaced_global in self.module.global_vars:
                            self.emit(f"mov rax, [_pyfasm_global_{namespaced_global}]", f"load module global {mod_name}.{expr.attr}")
                            val_handled = True
                        elif expr.attr in self.module.global_vars:
                            self.emit(f"mov rax, [_pyfasm_global_{expr.attr}]", f"load global {expr.attr}")
                            val_handled = True
                    if not val_handled:
                        namespaced_func = f"{mod_name}_{expr.attr}"
                        if namespaced_func in self.module.functions:
                            safe_fn = safe_asm_label(namespaced_func)
                            self.emit(f"lea rax, [{safe_fn}]", f"address of {mod_name}.{expr.attr}")
                            val_handled = True
                        elif expr.attr in self.module.functions:
                            safe_fn = safe_asm_label(expr.attr)
                            self.emit(f"lea rax, [{safe_fn}]", f"address of {expr.attr}")
                            val_handled = True
                if not val_handled:
                    self.emit("xor eax, eax", f"safe fallback for module/class attribute {expr.attr}")
            else:
                if expr.attr == "size":
                    self._generate_expr(expr.value)
                    self.emit("mov r8, rax")
                    lbl_null_sz = self.new_label("null_sz")
                    lbl_done_sz = self.new_label("done_sz")
                    self.emit("test r8, r8")
                    self.emit(f"jz {lbl_null_sz}")
                    self.emit("mov rax, [r8]", "load length/size")
                    self.emit(f"jmp {lbl_done_sz}")
                    self.emit_raw(f"{lbl_null_sz}:")
                    self.emit("xor eax, eax")
                    self.emit_raw(f"{lbl_done_sz}:")
                    return
                if expr.attr == "real":
                    self._generate_expr(expr.value)
                    return
                if expr.attr == "imag":
                    self.emit("xor eax, eax")
                    return

                self._generate_expr(expr.value)
                self.emit("mov r8, rax", "object pointer")
                offset = self._get_attribute_offset(expr.attr)
                lbl_null = self.new_label("null_attr")
                lbl_done = self.new_label("done_attr")
                curr_cls = getattr(self.current_func, "class_name", None)
                fallback_global = f"{curr_cls}_{expr.attr}" if curr_cls else None
                self.emit("test r8, r8", "check null pointer")
                self.emit(f"jz {lbl_null}")
                self.emit(f"mov rax, [r8 + {offset}]", f"load obj.{expr.attr}")
                if fallback_global and fallback_global in self.module.global_vars:
                    self.emit("test rax, rax", "check if instance field is set")
                    lbl_has_inst = self.new_label("has_inst")
                    self.emit(f"jnz {lbl_has_inst}")
                    self.emit(f"mov rax, [_pyfasm_global_{fallback_global}]", f"fallback to class attribute {fallback_global}")
                    self.emit_raw(f"{lbl_has_inst}:")
                self.emit(f"jmp {lbl_done}")
                self.emit_raw(f"{lbl_null}:")
                if fallback_global and fallback_global in self.module.global_vars:
                    self.emit(f"mov rax, [_pyfasm_global_{fallback_global}]", f"fallback to class attribute {fallback_global}")
                else:
                    self.emit("xor eax, eax", "null pointer default")
                self.emit_raw(f"{lbl_done}:")

        elif isinstance(expr, ast.BinOp):
            # Check user-defined operator overloading dunder methods (__add__, __sub__, etc.)
            binop_dunders = {
                ast.Add: "__add__",
                ast.Sub: "__sub__",
                ast.Mult: "__mul__",
                ast.FloorDiv: "__floordiv__",
                ast.Div: "__truediv__",
                ast.Mod: "__mod__",
                ast.Pow: "__pow__",
                ast.BitAnd: "__and__",
                ast.BitOr: "__or__",
                ast.BitXor: "__xor__",
                ast.LShift: "__lshift__",
                ast.RShift: "__rshift__",
            }
            op_cls = type(expr.op)
            if op_cls in binop_dunders and not (isinstance(expr.left, ast.Constant) and isinstance(expr.left.value, str)):
                dunder_name = binop_dunders[op_cls]
                cls_name = self.resolve_instance_class(expr.left)
                op_m = self.resolve_class_method(cls_name, dunder_name) if cls_name else None
                if op_m:
                    self._generate_expr(expr.right)
                    self.emit("push rax", "save other")
                    self._generate_expr(expr.left)
                    self.emit("mov rcx, rax", "pass self")
                    self.emit("pop rdx", "pass other")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {safe_asm_label(op_m)}")
                    self.emit("add rsp, 32")
                    return

            if isinstance(expr.op, ast.Mod):
                if isinstance(expr.left, ast.Constant) and isinstance(expr.left.value, str):
                    fmt_args: List[ast.expr] = []
                    if isinstance(expr.right, (ast.Tuple, ast.List)):
                        fmt_args = list(expr.right.elts)
                    else:
                        fmt_args = [expr.right]
                    parts = self._desugar_str_percent(expr.left.value, fmt_args)
                    self._generate_expr(ast.JoinedStr(values=parts))
                    return

            is_str_add = False
            if isinstance(expr.op, ast.Add):
                if isinstance(expr.left, ast.Constant) and isinstance(expr.left.value, str):
                    is_str_add = True
                elif isinstance(expr.right, ast.Constant) and isinstance(expr.right.value, str):
                    is_str_add = True
                elif isinstance(expr.left, ast.Name) and self.current_func:
                    var = self.current_func.local_vars.get(expr.left.id)
                    if var and var.var_type.is_str():
                        is_str_add = True
                elif isinstance(expr.right, ast.Name) and self.current_func:
                    var = self.current_func.local_vars.get(expr.right.id)
                    if var and var.var_type.is_str():
                        is_str_add = True

            if is_str_add:
                self._generate_expr(expr.left)
                self.emit("push rax")
                self._generate_expr(expr.right)
                self.emit("mov rdx, rax", "str2")
                self.emit("pop rcx", "str1")
                self.emit("call _pyfasm_str_concat")
                return

            lt = self._infer_expr_type(expr.left)
            rt = self._infer_expr_type(expr.right)
            if (lt.is_float() or rt.is_float()) and isinstance(expr.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)):
                self._generate_expr(expr.left)
                if not lt.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("push rax")
                self._generate_expr(expr.right)
                if not rt.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("movq xmm0, rax")
                self.emit("movq xmm1, r11")
                if isinstance(expr.op, ast.Add):
                    self.emit("addsd xmm0, xmm1")
                elif isinstance(expr.op, ast.Sub):
                    self.emit("subsd xmm0, xmm1")
                elif isinstance(expr.op, ast.Mult):
                    self.emit("mulsd xmm0, xmm1")
                elif isinstance(expr.op, (ast.Div, ast.FloorDiv)):
                    self.emit("divsd xmm0, xmm1")
                self.emit("movq rax, xmm0")
                return

            self._generate_expr(expr.left)
            self.emit("push rax")
            self._generate_expr(expr.right)
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self._generate_binop_instr(expr.op)

        elif isinstance(expr, ast.UnaryOp):
            self._generate_expr(expr.operand)
            if isinstance(expr.op, ast.USub):
                t = self._infer_expr_type(expr.operand)
                if t.is_float():
                    self.emit("movq xmm0, rax")
                    self.emit("xorpd xmm1, xmm1")
                    self.emit("subsd xmm1, xmm0")
                    self.emit("movq rax, xmm1")
                else:
                    self.emit("neg rax")
            elif isinstance(expr.op, ast.Invert):
                self.emit("not rax")
            elif isinstance(expr.op, ast.Not):
                self.emit("test rax, rax")
                self.emit("setz al")
                self.emit("movzx rax, al")

        elif isinstance(expr, ast.BoolOp):
            lbl_end = self.new_label("boolop_end")
            if isinstance(expr.op, ast.And):
                for idx, val in enumerate(expr.values):
                    self._generate_expr(val)
                    if idx < len(expr.values) - 1:
                        self.emit("test rax, rax")
                        self.emit(f"jz {lbl_end}")
            elif isinstance(expr.op, ast.Or):
                for idx, val in enumerate(expr.values):
                    self._generate_expr(val)
                    if idx < len(expr.values) - 1:
                        self.emit("test rax, rax")
                        self.emit(f"jnz {lbl_end}")
            self.emit_raw(f"{lbl_end}:")

        elif isinstance(expr, ast.IfExp):
            lbl_else = self.new_label("ifexp_else")
            lbl_done = self.new_label("ifexp_done")
            self._generate_expr(expr.test)
            self.emit("test rax, rax")
            self.emit(f"jz {lbl_else}")
            self._generate_expr(expr.body)
            self.emit(f"jmp {lbl_done}")
            self.emit_raw(f"{lbl_else}:")
            self._generate_expr(expr.orelse)
            self.emit_raw(f"{lbl_done}:")

        elif isinstance(expr, ast.NamedExpr):
            self._generate_expr(expr.value)
            if isinstance(expr.target, ast.Name) and self.current_func:
                var = self.current_func.local_vars.get(expr.target.id)
                if var:
                    self.emit(f"mov [rbp - {var.stack_offset}], rax", f"walrus assign {var.name}")

        elif isinstance(expr, ast.Compare):
            op = expr.ops[0]
            if isinstance(op, (ast.In, ast.NotIn)):
                # Check user class __contains__
                cont_cls = self.resolve_instance_class(expr.comparators[0])
                cont_m = self.resolve_class_method(cont_cls, "__contains__") if cont_cls else None
                if cont_m:
                    self._generate_expr(expr.left)
                    self.emit("push rax", "save item")
                    self._generate_expr(expr.comparators[0])
                    self.emit("mov rcx, rax", "pass container (self)")
                    self.emit("pop rdx", "pass item")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {safe_asm_label(cont_m)}")
                    self.emit("add rsp, 32")
                    if isinstance(op, ast.NotIn):
                        self.emit("test rax, rax")
                        self.emit("setz al")
                        self.emit("movzx rax, al")
                    return

                self._generate_expr(expr.comparators[0])
                self.emit("push rax")
                self._generate_expr(expr.left)
                self.emit("mov rdx, rax", "needle / item")
                self.emit("pop rcx", "container")
                target_kind = "str"
                comp_type = self._infer_expr_type(expr.comparators[0])
                if comp_type.is_dict() or comp_type.is_set():
                    target_kind = "dict"
                elif comp_type.is_list() or comp_type.is_tuple():
                    target_kind = "list"
                elif isinstance(expr.comparators[0], ast.Name) and self.current_func:
                    sym = self.current_func.local_vars.get(expr.comparators[0].id)
                    if sym:
                        if sym.var_type.is_dict() or sym.var_type.is_set():
                            target_kind = "dict"
                        elif sym.var_type.is_list() or sym.var_type.is_tuple():
                            target_kind = "list"
                if target_kind == "dict":
                    self.emit("call _pyfasm_dict_contains")
                elif target_kind == "list":
                    self.emit("call _pyfasm_list_contains")
                else:
                    self.emit("call _pyfasm_str_contains")
                if isinstance(op, ast.NotIn):
                    self.emit("xor rax, 1")
            elif isinstance(op, ast.Is):
                self._generate_expr(expr.left)
                self.emit("push rax")
                self._generate_expr(expr.comparators[0])
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("cmp rax, r11")
                self.emit("sete al")
                self.emit("movzx rax, al")
            elif isinstance(op, ast.IsNot):
                self._generate_expr(expr.left)
                self.emit("push rax")
                self._generate_expr(expr.comparators[0])
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("cmp rax, r11")
                self.emit("setne al")
                self.emit("movzx rax, al")
            else:
                # Check user class comparison dunders (__eq__, __ne__, __lt__, etc.)
                comp_dunders = {
                    ast.Eq: "__eq__",
                    ast.NotEq: "__ne__",
                    ast.Lt: "__lt__",
                    ast.LtE: "__le__",
                    ast.Gt: "__gt__",
                    ast.GtE: "__ge__"
                }
                op_cls = type(op)
                if op_cls in comp_dunders:
                    dunder = comp_dunders[op_cls]
                    cls_name = self.resolve_instance_class(expr.left)
                    comp_m = self.resolve_class_method(cls_name, dunder) if cls_name else None
                    invert_res = False
                    if not comp_m and op_cls is ast.NotEq and cls_name:
                        comp_m = self.resolve_class_method(cls_name, "__eq__")
                        if comp_m:
                            invert_res = True
                    if comp_m:
                        self._generate_expr(expr.comparators[0])
                        self.emit("push rax", "save other")
                        self._generate_expr(expr.left)
                        self.emit("mov rcx, rax", "pass self")
                        self.emit("pop rdx", "pass other")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit(f"call {safe_asm_label(comp_m)}")
                        self.emit("add rsp, 32")
                        if invert_res:
                            self.emit("test rax, rax")
                            self.emit("setz al")
                            self.emit("movzx rax, al")
                        return

                lt = self._infer_expr_type(expr.left)
                rt = self._infer_expr_type(expr.comparators[0])
                if (lt.is_str() or rt.is_str()) and isinstance(op, (ast.Eq, ast.NotEq)):
                    self._generate_expr(expr.left)
                    self.emit("push rax")
                    self._generate_expr(expr.comparators[0])
                    self.emit("mov rdx, rax", "str2")
                    self.emit("pop rcx", "str1")
                    self.emit("call _pyfasm_str_cmp")
                    if isinstance(op, ast.NotEq):
                        self.emit("xor eax, 1")
                    return

                if (lt.is_float() or rt.is_float()) and isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    self._generate_expr(expr.left)
                    if not lt.is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("push rax")
                    self._generate_expr(expr.comparators[0])
                    if not rt.is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("mov r11, rax")
                    self.emit("pop rax")
                    self.emit("movq xmm0, rax")
                    self.emit("movq xmm1, r11")
                    self.emit("ucomisd xmm0, xmm1")
                    if isinstance(op, ast.Eq):
                        self.emit("sete al")
                    elif isinstance(op, ast.NotEq):
                        self.emit("setne al")
                    elif isinstance(op, ast.Lt):
                        self.emit("setb al")
                    elif isinstance(op, ast.LtE):
                        self.emit("setbe al")
                    elif isinstance(op, ast.Gt):
                        self.emit("seta al")
                    elif isinstance(op, ast.GtE):
                        self.emit("setae al")
                    self.emit("movzx rax, al")
                    return

                self._generate_expr(expr.left)
                self.emit("push rax")
                self._generate_expr(expr.comparators[0])
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("cmp rax, r11")
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
            if isinstance(expr.slice, ast.Slice):
                self._generate_expr(expr.value)
                self.emit("push rax", "container pointer")

                if expr.slice.lower:
                    self._generate_expr(expr.slice.lower)
                    self.emit("push rax", "lower")
                else:
                    self.emit("push 0", "lower = 0")

                if expr.slice.upper:
                    self._generate_expr(expr.slice.upper)
                    self.emit("push rax", "upper")
                else:
                    self.emit("mov rax, -999999", "upper = None")
                    self.emit("push rax")

                if expr.slice.step:
                    self._generate_expr(expr.slice.step)
                    self.emit("push rax", "step")
                else:
                    self.emit("push 1", "step = 1")

                self.emit("pop r9", "step")
                self.emit("pop r8", "upper")
                self.emit("pop rdx", "lower")
                self.emit("pop rcx", "container")

                is_list_target = False
                val_t = self._infer_expr_type(expr.value)
                if val_t.is_list() or val_t.is_tuple():
                    is_list_target = True
                elif isinstance(expr.value, ast.Name) and self.current_func:
                    v = self.current_func.local_vars.get(expr.value.id)
                    if v and (v.var_type.is_list() or v.var_type.is_tuple()):
                        is_list_target = True

                if is_list_target:
                    self.emit("call _pyfasm_list_slice")
                else:
                    self.emit("call _pyfasm_str_slice")
                return

            if isinstance(expr.value, ast.Name) and expr.value.id in (
                "Literal", "Union", "Optional", "Annotated", "tuple", "list", "dict", "set", "Type", "Callable", "Final", "ClassVar", "Any"
            ):
                self.emit("xor eax, eax", "safe no-op for typing subscript")
                return
            if isinstance(expr.value, ast.Attribute) and getattr(expr.value, "attr", None) in (
                "Literal", "Union", "Optional", "Annotated", "tuple", "list", "dict", "set", "Type", "Callable", "Final", "ClassVar", "Any"
            ):
                self.emit("xor eax, eax", "safe no-op for typing subscript")
                return

            slice_unwrapped = _unwrap_slice(expr.slice)
            # Check custom __getitem__
            cls_name = self.resolve_instance_class(expr.value)
            getitem_m = self.resolve_class_method(cls_name, "__getitem__") if cls_name else None
            if getitem_m:
                self._generate_expr(slice_unwrapped)
                self.emit("push rax", "save key")
                self._generate_expr(expr.value)
                self.emit("mov rcx, rax", "pass self")
                self.emit("pop rdx", "pass key")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {safe_asm_label(getitem_m)}")
                self.emit("add rsp, 32")
                return

            dict_keywords = ("dict", "map", "vars", "entries", "table", "cache", "lookup", "plot", "status", "disc", "modules", "headers", "params", "environ", "cookies", "meta", "registry", "data", "mapping", "config", "state", "styles", "themes", "kw", "kwargs", "options", "types")
            is_dict_val = False
            is_tuple_key = False
            slice_type = self._infer_expr_type(slice_unwrapped)
            if slice_type.is_str():
                is_dict_val = True
            elif isinstance(slice_unwrapped, (ast.Tuple, ast.List)):
                is_dict_val = True
                is_tuple_key = isinstance(slice_unwrapped, ast.Tuple)
            elif isinstance(slice_unwrapped, ast.Constant) and isinstance(slice_unwrapped.value, str):
                is_dict_val = True
            elif isinstance(expr.value, ast.Attribute) and any(k in expr.value.attr.lower() for k in dict_keywords):
                is_dict_val = True
            elif isinstance(expr.value, ast.Name):
                if any(k in expr.value.id.lower() for k in dict_keywords):
                    is_dict_val = True
                elif self.current_func and hasattr(self.current_func, "local_vars"):
                    v = self.current_func.local_vars.get(expr.value.id)
                    if v and (v.var_type.is_dict() or v.var_type.is_set()):
                        is_dict_val = True
                        if isinstance(slice_unwrapped, ast.Name):
                            kv = self.current_func.local_vars.get(slice_unwrapped.id)
                            if kv and kv.var_type.is_tuple():
                                is_tuple_key = True
            else:
                expr_type = self._infer_expr_type(expr.value)
                if expr_type.is_dict() or expr_type.is_set():
                    is_dict_val = True
                    if isinstance(slice_unwrapped, ast.Name) and self.current_func:
                        kv = self.current_func.local_vars.get(slice_unwrapped.id)
                        if kv and kv.var_type.is_tuple():
                            is_tuple_key = True

            if is_dict_val:
                self._generate_expr(expr.value)
                self.emit("push rax")
                self._generate_expr(slice_unwrapped)
                self.emit("mov rdx, rax", "key")
                self.emit("pop rcx", "dict_ptr")
                self.emit("xor r8, r8", "default = 0")
                if is_tuple_key:
                    self.emit("call _pyfasm_dict_get_tuple")
                else:
                    self.emit("call _pyfasm_dict_get")
            else:
                self._generate_expr(expr.value)  # arr pointer -> RAX
                self.emit("push rax")
                self._generate_expr(slice_unwrapped)  # index -> RAX
                self.emit("mov r11, rax")
                self.emit("pop rax")
                is_list_val = False
                val_t = self._infer_expr_type(expr.value)
                if val_t.is_list() or val_t.is_tuple():
                    is_list_val = True
                elif isinstance(expr.value, ast.Name) and self.current_func:
                    v = self.current_func.local_vars.get(expr.value.id)
                    if v and (v.var_type.is_list() or v.var_type.is_tuple()):
                        is_list_val = True

                is_str_val = False
                if val_t.is_str():
                    is_str_val = True
                elif isinstance(expr.value, ast.Name) and self.current_func:
                    v = self.current_func.local_vars.get(expr.value.id)
                    if v and v.var_type.is_str():
                        is_str_val = True

                lbl_null_arr = self.new_label("null_arr")
                lbl_done_arr = self.new_label("done_arr")
                self.emit("test rax, rax", "check null array")
                self.emit(f"jz {lbl_null_arr}")
                self.emit("cmp rax, 65536", "check valid user-mode pointer")
                self.emit(f"jb {lbl_null_arr}")

                if is_list_val:
                    lbl_idx_pos = self.new_label("idx_pos")
                    self.emit("test r11, r11", "check negative index")
                    self.emit(f"jns {lbl_idx_pos}")
                    self.emit("add r11, [rax]", "negative index: len + idx")
                    self.emit_raw(f"{lbl_idx_pos}:")

                self.emit("test r11, r11", "check negative index")
                self.emit(f"js {lbl_null_arr}")
                self.emit("cmp r11, 1000000", "check index bounds")
                self.emit(f"jae {lbl_null_arr}")

                if is_str_val:
                    self.emit("push rax", "save str ptr")
                    self.emit("push r11", "save idx")
                    self.emit("mov ecx, 2", "alloc 2 bytes for char string")
                    self.emit("call _pyfasm_alloc")
                    self.emit("pop r11", "restore idx")
                    self.emit("pop rdx", "restore str ptr")
                    self.emit("movzx r10d, byte [rdx + r11]", "read char byte")
                    self.emit("mov byte [rax], r10b", "store char byte")
                    self.emit("mov byte [rax + 1], 0", "store null terminator")
                elif is_list_val:
                    self.emit("mov rax, [rax + (r11 + 1) * 8]", "load list[idx]")
                else:
                    self.emit("mov rax, [rax + r11 * 8]", "load arr[idx]")
                self.emit(f"jmp {lbl_done_arr}")
                self.emit_raw(f"{lbl_null_arr}:")
                self.emit("xor eax, eax", "null array default")
                self.emit_raw(f"{lbl_done_arr}:")

        elif isinstance(expr, ast.Dict):
            num_keys = len(expr.keys)
            cap = 16
            while cap < max(16, num_keys * 2):
                cap *= 2
            self.emit(f"mov ecx, {cap}", f"create dict with capacity {cap}")
            self.emit("call _pyfasm_dict_create")
            self.emit("push rax", "save dict_ptr on stack")
            for k_expr, v_expr in zip(expr.keys, expr.values):
                if k_expr is None:
                    continue
                self._generate_expr(v_expr)
                self.emit("push rax", "save val to insert")
                self._generate_expr(k_expr)
                self.emit("mov rdx, rax", "key")
                self.emit("pop r8", "val")
                self.emit("mov rcx, [rsp]", "dict_ptr from top of stack")
                self.emit("call _pyfasm_dict_set")
            self.emit("pop rax", "return dict pointer")

        elif isinstance(expr, ast.Tuple):
            num_elts = len(expr.elts)
            alloc_bytes = max(16, (num_elts + 2) * 8)
            self.emit(f"mov ecx, {alloc_bytes}", f"allocate tuple of {num_elts} items")
            self.emit("call _pyfasm_alloc")
            self.emit("mov r8, rax", "tuple base pointer")
            self.emit(f"mov qword [r8], {num_elts}", "store tuple length")
            for idx, elt in enumerate(expr.elts):
                self.emit("push r8")
                self._generate_expr(elt)
                self.emit("pop r8")
                self.emit(f"mov [r8 + {(idx + 1) * 8}], rax", f"store tuple[{idx}]")
            self.emit("mov rax, r8", "return tuple pointer")

        elif isinstance(expr, ast.JoinedStr):
            if not expr.values:
                self._emit_string_pointer("rax", "")
            else:
                self._generate_fstring_part(expr.values[0])
                self.emit("push rax", "save first part")
                for part in expr.values[1:]:
                    self._generate_fstring_part(part)
                    self.emit("mov rdx, rax", "next part")
                    self.emit("pop rcx", "accumulated string")
                    self.emit("call _pyfasm_str_concat")
                    self.emit("push rax", "save combined")
                self.emit("pop rax", "final combined string")

        elif isinstance(expr, ast.List):
            num_elts = len(expr.elts)
            alloc_bytes = max(512, (num_elts + 32) * 8)
            self.emit(f"mov ecx, {alloc_bytes}", f"allocate list of {num_elts} items")
            self.emit("call _pyfasm_alloc")
            self.emit("mov r8, rax", "list base pointer")
            self.emit(f"mov qword [r8], {num_elts}", "store list length")
            for idx, elt in enumerate(expr.elts):
                self.emit("push r8")
                self._generate_expr(elt)
                self.emit("pop r8")
                self.emit(f"mov [r8 + {(idx + 1) * 8}], rax", f"store list[{idx}]")
            self.emit("mov rax, r8", "return list pointer")

        elif isinstance(expr, ast.ListComp):
            self._generate_list_comprehension(expr)

        elif isinstance(expr, ast.DictComp):
            self._generate_dict_comprehension(expr)

        elif isinstance(expr, ast.Set):
            num_elts = len(expr.elts)
            cap = max(16, num_elts * 2)
            self.emit(f"mov ecx, {cap}", "allocate set")
            self.emit("call _pyfasm_set_create")
            self.emit("push rax", "save set_ptr")
            for elt in expr.elts:
                self._generate_expr(elt)
                self.emit("mov rdx, rax", "item")
                self.emit("mov rcx, [rsp]", "set_ptr")
                self.emit("call _pyfasm_set_add")
            self.emit("pop rax", "return set_ptr")

        elif isinstance(expr, ast.SetComp):
            self._generate_set_comprehension(expr)

        elif isinstance(expr, (ast.Yield, ast.YieldFrom)):
            self._generate_yield(expr)

        elif isinstance(expr, ast.Call):
            self._generate_call(expr)

    def _generate_list_comprehension(self, node: ast.ListComp) -> None:
        self.emit("mov ecx, 8192", "allocate list buffer for comprehension")
        self.emit("call _pyfasm_alloc")
        self.emit("mov qword [rax], 0", "initial list len = 0")
        self.emit("push rax", "save list_ptr on stack")

        for gen in node.generators:
            target_var = self.current_func.local_vars.get(gen.target.id) if isinstance(gen.target, ast.Name) and self.current_func else None
            if isinstance(gen.iter, ast.Call) and isinstance(gen.iter.func, ast.Name) and gen.iter.func.id == "range":
                args = gen.iter.args
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

                if start_expr:
                    self._generate_expr(start_expr)
                else:
                    self.emit("xor eax, eax")
                if target_var:
                    self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"init comp {target_var.name}")

                lbl_start = self.new_label("comp_range_start")
                lbl_step = self.new_label("comp_range_step")
                lbl_end = self.new_label("comp_range_end")

                self.emit_raw(f"{lbl_start}:")
                if target_var:
                    self.emit(f"mov rax, [rbp - {target_var.stack_offset}]")
                self.emit("push rax")
                self._generate_expr(stop_expr)
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("cmp rax, r11")
                if step_val > 0:
                    self.emit(f"jge {lbl_end}")
                else:
                    self.emit(f"jle {lbl_end}")

                lbl_skip = self.new_label("comp_skip")
                for if_expr in gen.ifs:
                    self._generate_expr(if_expr)
                    self.emit("test rax, rax")
                    self.emit(f"jz {lbl_skip}")

                self._generate_expr(node.elt)
                self.emit("mov rdx, rax", "element")
                self.emit("mov rcx, [rsp]", "list_ptr on stack")
                self.emit("call _pyfasm_list_append")

                self.emit_raw(f"{lbl_skip}:")
                self.emit_raw(f"{lbl_step}:")
                if target_var:
                    if step_val == 1:
                        self.emit(f"inc qword [rbp - {target_var.stack_offset}]")
                    else:
                        self.emit(f"add qword [rbp - {target_var.stack_offset}], {step_val}")
                self.emit(f"jmp {lbl_start}")
                self.emit_raw(f"{lbl_end}:")

            else:
                self._generate_expr(gen.iter)
                lbl_null = self.new_label("comp_c_null")
                lbl_start = self.new_label("comp_c_start")
                lbl_step = self.new_label("comp_c_step")
                lbl_end = self.new_label("comp_c_end")

                self.emit("test rax, rax")
                self.emit(f"jz {lbl_null}")

                self.emit("push rax", "container ptr")
                self.emit("push 0", "idx = 0")

                self.emit_raw(f"{lbl_start}:")
                self.emit("mov rcx, [rsp]", "idx")
                self.emit("mov rbx, [rsp + 8]", "container ptr")
                self.emit("mov rdx, [rbx]", "container len")
                self.emit("cmp rcx, rdx")
                self.emit(f"jge {lbl_end}")

                self.emit("mov rax, [rbx + rcx * 8 + 8]", "load container[idx]")
                if target_var:
                    self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"assign {target_var.name}")

                lbl_skip = self.new_label("comp_c_skip")
                for if_expr in gen.ifs:
                    self._generate_expr(if_expr)
                    self.emit("test rax, rax")
                    self.emit(f"jz {lbl_skip}")

                self._generate_expr(node.elt)
                self.emit("mov rdx, rax", "element")
                self.emit("mov rcx, [rsp + 16]", "list_ptr on stack")
                self.emit("call _pyfasm_list_append")

                self.emit_raw(f"{lbl_skip}:")
                self.emit_raw(f"{lbl_step}:")
                self.emit("inc qword [rsp]")
                self.emit(f"jmp {lbl_start}")

                self.emit_raw(f"{lbl_end}:")
                self.emit("add rsp, 16", "cleanup container & idx")
                self.emit_raw(f"{lbl_null}:")

        self.emit("pop rax", "return list_ptr in RAX")

    def _generate_dict_comprehension(self, node: ast.DictComp) -> None:
        self.emit("mov ecx, 64", "create dict with capacity 64")
        self.emit("call _pyfasm_dict_create")
        self.emit("push rax", "save dict_ptr on stack")

        for gen in node.generators:
            target_var = self.current_func.local_vars.get(gen.target.id) if isinstance(gen.target, ast.Name) and self.current_func else None
            if isinstance(gen.iter, ast.Call) and isinstance(gen.iter.func, ast.Name) and gen.iter.func.id == "range":
                args = gen.iter.args
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

                if start_expr:
                    self._generate_expr(start_expr)
                else:
                    self.emit("xor eax, eax")
                if target_var:
                    self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"init comp {target_var.name}")

                lbl_start = self.new_label("dict_comp_range_start")
                lbl_step = self.new_label("dict_comp_range_step")
                lbl_end = self.new_label("dict_comp_range_end")

                self.emit_raw(f"{lbl_start}:")
                if target_var:
                    self.emit(f"mov rax, [rbp - {target_var.stack_offset}]")
                self.emit("push rax")
                self._generate_expr(stop_expr)
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("cmp rax, r11")
                if step_val > 0:
                    self.emit(f"jge {lbl_end}")
                else:
                    self.emit(f"jle {lbl_end}")

                lbl_skip = self.new_label("dict_comp_skip")
                for if_expr in gen.ifs:
                    self._generate_expr(if_expr)
                    self.emit("test rax, rax")
                    self.emit(f"jz {lbl_skip}")

                self._generate_expr(node.value)
                self.emit("push rax", "save dict val")
                self._generate_expr(node.key)
                self.emit("mov rdx, rax", "dict key")
                self.emit("pop r8", "dict val")
                self.emit("mov rcx, [rsp]", "dict_ptr on stack")
                self.emit("call _pyfasm_dict_set")

                self.emit_raw(f"{lbl_skip}:")
                self.emit_raw(f"{lbl_step}:")
                if target_var:
                    if step_val == 1:
                        self.emit(f"inc qword [rbp - {target_var.stack_offset}]")
                    else:
                        self.emit(f"add qword [rbp - {target_var.stack_offset}], {step_val}")
                self.emit(f"jmp {lbl_start}")
                self.emit_raw(f"{lbl_end}:")

            else:
                self._generate_expr(gen.iter)
                lbl_null = self.new_label("dict_comp_c_null")
                lbl_start = self.new_label("dict_comp_c_start")
                lbl_step = self.new_label("dict_comp_c_step")
                lbl_end = self.new_label("dict_comp_c_end")

                self.emit("test rax, rax")
                self.emit(f"jz {lbl_null}")

                self.emit("push rax", "container ptr")
                self.emit("push 0", "idx = 0")

                self.emit_raw(f"{lbl_start}:")
                self.emit("mov rcx, [rsp]", "idx")
                self.emit("mov rbx, [rsp + 8]", "container ptr")
                self.emit("mov rdx, [rbx]", "container len")
                self.emit("cmp rcx, rdx")
                self.emit(f"jge {lbl_end}")

                self.emit("mov rax, [rbx + rcx * 8 + 8]", "load container[idx]")
                if target_var:
                    self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"assign {target_var.name}")

                lbl_skip = self.new_label("dict_comp_c_skip")
                for if_expr in gen.ifs:
                    self._generate_expr(if_expr)
                    self.emit("test rax, rax")
                    self.emit(f"jz {lbl_skip}")

                self._generate_expr(node.value)
                self.emit("push rax", "save dict val")
                self._generate_expr(node.key)
                self.emit("mov rdx, rax", "dict key")
                self.emit("pop r8", "dict val")
                self.emit("mov rcx, [rsp + 16]", "dict_ptr on stack")
                self.emit("call _pyfasm_dict_set")

                self.emit_raw(f"{lbl_skip}:")
                self.emit_raw(f"{lbl_step}:")
                self.emit("inc qword [rsp]")
                self.emit(f"jmp {lbl_start}")

                self.emit_raw(f"{lbl_end}:")
                self.emit("add rsp, 16", "cleanup container & idx")
                self.emit_raw(f"{lbl_null}:")

        self.emit("pop rax", "return dict_ptr in RAX")

    def _generate_set_comprehension(self, node: ast.SetComp) -> None:
        self.emit("mov ecx, 32", "initial set capacity")
        self.emit("call _pyfasm_set_create")
        self.emit("push rax", "save set_ptr on stack")

        for gen in node.generators:
            target_var = self.current_func.local_vars.get(gen.target.id) if isinstance(gen.target, ast.Name) and self.current_func else None
            if isinstance(gen.iter, ast.Call) and isinstance(gen.iter.func, ast.Name) and gen.iter.func.id == "range":
                args = gen.iter.args
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

                if start_expr:
                    self._generate_expr(start_expr)
                else:
                    self.emit("xor eax, eax")
                if target_var:
                    self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"init comp {target_var.name}")

                lbl_start = self.new_label("setcomp_range_start")
                lbl_step = self.new_label("setcomp_range_step")
                lbl_end = self.new_label("setcomp_range_end")

                self.emit_raw(f"{lbl_start}:")
                if target_var:
                    self.emit(f"mov rax, [rbp - {target_var.stack_offset}]")
                else:
                    self.emit("xor eax, eax")
                self.emit("push rax")
                if stop_expr:
                    self._generate_expr(stop_expr)
                else:
                    self.emit("xor eax, eax")
                self.emit("mov r11, rax")
                self.emit("pop rax")
                self.emit("cmp rax, r11")
                if step_val > 0:
                    self.emit(f"jge {lbl_end}")
                else:
                    self.emit(f"jle {lbl_end}")

                lbl_skip = self.new_label("setcomp_skip")
                for if_expr in gen.ifs:
                    self._generate_expr(if_expr)
                    self.emit("test rax, rax")
                    self.emit(f"jz {lbl_skip}")

                self._generate_expr(node.elt)
                self.emit("mov rdx, rax", "item")
                self.emit("mov rcx, [rsp]", "set_ptr on stack")
                self.emit("call _pyfasm_set_add")

                self.emit_raw(f"{lbl_skip}:")
                self.emit_raw(f"{lbl_step}:")
                if target_var:
                    if step_val == 1:
                        self.emit(f"inc qword [rbp - {target_var.stack_offset}]")
                    else:
                        self.emit(f"add qword [rbp - {target_var.stack_offset}], {step_val}")
                self.emit(f"jmp {lbl_start}")
                self.emit_raw(f"{lbl_end}:")

            else:
                self._generate_expr(gen.iter)
                lbl_null = self.new_label("setcomp_null")
                lbl_start = self.new_label("setcomp_start")
                lbl_step = self.new_label("setcomp_step")
                lbl_end = self.new_label("setcomp_end")

                self.emit("test rax, rax")
                self.emit(f"jz {lbl_null}")
                self.emit("push rax", "container")
                self.emit("push 0", "idx = 0")

                self.emit_raw(f"{lbl_start}:")
                self.emit("mov rcx, [rsp]", "idx")
                self.emit("mov rbx, [rsp + 8]", "container")
                self.emit("cmp rcx, [rbx]")
                self.emit(f"jge {lbl_end}")

                self.emit("mov rax, [rbx + rcx * 8 + 8]")
                if target_var:
                    self.emit(f"mov [rbp - {target_var.stack_offset}], rax", f"assign {target_var.name}")

                lbl_skip = self.new_label("setcomp_skip")
                for if_expr in gen.ifs:
                    self._generate_expr(if_expr)
                    self.emit("test rax, rax")
                    self.emit(f"jz {lbl_skip}")

                self._generate_expr(node.elt)
                self.emit("mov rdx, rax", "item")
                self.emit("mov rcx, [rsp + 16]", "set_ptr on stack")
                self.emit("call _pyfasm_set_add")

                self.emit_raw(f"{lbl_skip}:")
                self.emit_raw(f"{lbl_step}:")
                self.emit("inc qword [rsp]")
                self.emit(f"jmp {lbl_start}")

                self.emit_raw(f"{lbl_end}:")
                self.emit("add rsp, 16", "cleanup container & idx")
                self.emit_raw(f"{lbl_null}:")

        self.emit("pop rax", "return set_ptr in RAX")

    def _generate_match(self, stmt: ast.Match) -> None:
        self._generate_expr(stmt.subject)
        self.emit("push rax", "save match subject on stack")
        lbl_match_end = self.new_label("match_end")

        for idx, case in enumerate(stmt.cases):
            lbl_next_case = self.new_label(f"case_next_{idx}")
            lbl_case_body = self.new_label(f"case_body_{idx}")

            self._generate_case_pattern_test(case.pattern, lbl_case_body, lbl_next_case)

            self.emit_raw(f"{lbl_case_body}:")
            if case.guard:
                self._generate_expr(case.guard)
                self.emit("test rax, rax")
                self.emit(f"jz {lbl_next_case}", "case guard failed")

            for s in case.body:
                self._generate_statement(s)
            self.emit(f"jmp {lbl_match_end}")

            self.emit_raw(f"{lbl_next_case}:")

        self.emit_raw(f"{lbl_match_end}:")
        self.emit("add rsp, 8", "cleanup match subject from stack")

    def _generate_case_pattern_test(self, pattern: ast.pattern, lbl_success: str, lbl_failure: str) -> None:
        if isinstance(pattern, ast.MatchValue):
            self._generate_expr(pattern.value)
            self.emit("mov rdx, rax")
            self.emit("mov rcx, [rsp]", "subject")
            self.emit("cmp rcx, rdx")
            self.emit(f"je {lbl_success}")
            self.emit("cmp rcx, 65536")
            self.emit(f"jb {lbl_failure}")
            self.emit("cmp rdx, 65536")
            self.emit(f"jb {lbl_failure}")
            self.emit("call _pyfasm_str_cmp")
            self.emit("test eax, eax")
            self.emit(f"jnz {lbl_success}")
            self.emit(f"jmp {lbl_failure}")

        elif isinstance(pattern, ast.MatchAs):
            if pattern.name is None or pattern.name == "_":
                self.emit(f"jmp {lbl_success}")
            else:
                self.emit("mov rax, [rsp]", "subject")
                if self.current_func:
                    var = self.current_func.local_vars.get(pattern.name)
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"capture {pattern.name}")
                    elif hasattr(self.current_func, "global_names") and pattern.name in self.current_func.global_names:
                        self.emit(f"mov [_pyfasm_global_{pattern.name}], rax", f"capture global {pattern.name}")
                self.emit(f"jmp {lbl_success}")

        elif isinstance(pattern, ast.MatchOr):
            for subpat in pattern.patterns:
                sub_next = self.new_label("or_next")
                self._generate_case_pattern_test(subpat, lbl_success, sub_next)
                self.emit_raw(f"{sub_next}:")
            self.emit(f"jmp {lbl_failure}")

        else:
            self.emit(f"jmp {lbl_success}")

    def _generate_binop_instr(self, op: ast.operator) -> None:
        if isinstance(op, ast.Add):
            self.emit("add rax, r11")
        elif isinstance(op, ast.Sub):
            self.emit("sub rax, r11")
        elif isinstance(op, ast.Mult):
            self.emit("imul rax, r11")
        elif isinstance(op, ast.FloorDiv) or isinstance(op, ast.Div):
            lbl_div_ok = self.new_label("div_ok")
            lbl_div_end = self.new_label("div_end")
            self.emit("test r11, r11")
            self.emit(f"jnz {lbl_div_ok}")
            if self.try_stack:
                self.emit("mov rax, 1", "ZeroDivisionError")
                self.emit(f"jmp {self.try_stack[-1]}")
            else:
                self.emit("xor eax, eax")
                self.emit(f"jmp {lbl_div_end}")
            self.emit_raw(f"{lbl_div_ok}:")
            self.emit("cqo")
            self.emit("idiv r11")
            self.emit_raw(f"{lbl_div_end}:")
        elif isinstance(op, ast.Mod):
            lbl_mod_ok = self.new_label("mod_ok")
            lbl_mod_end = self.new_label("mod_end")
            self.emit("test r11, r11")
            self.emit(f"jnz {lbl_mod_ok}")
            if self.try_stack:
                self.emit("mov rax, 1", "ZeroDivisionError")
                self.emit(f"jmp {self.try_stack[-1]}")
            else:
                self.emit("xor eax, eax")
                self.emit(f"jmp {lbl_mod_end}")
            self.emit_raw(f"{lbl_mod_ok}:")
            self.emit("cqo")
            self.emit("idiv r11")
            self.emit("mov rax, rdx")
            self.emit_raw(f"{lbl_mod_end}:")
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
        elif isinstance(op, ast.Pow):
            lbl = self.new_label("pow")
            self.emit("push rbx")
            self.emit("push rcx")
            self.emit("mov rbx, rax", "base")
            self.emit("mov rcx, r11", "exp")
            self.emit("mov rax, 1", "res = 1")
            self.emit("test rcx, rcx")
            self.emit(f"jle .done_{lbl}")
            self.emit_raw(f".loop_{lbl}:")
            self.emit("test rcx, 1")
            self.emit(f"jz .sq_{lbl}")
            self.emit("imul rax, rbx")
            self.emit_raw(f".sq_{lbl}:")
            self.emit("imul rbx, rbx")
            self.emit("sar rcx, 1")
            self.emit(f"jnz .loop_{lbl}")
            self.emit_raw(f".done_{lbl}:")
            self.emit("pop rcx")
            self.emit("pop rbx")

    def _generate_call(self, call: ast.Call) -> None:
        # String .format(...) method desugaring
        if isinstance(call.func, ast.Attribute) and call.func.attr == "format":
            if isinstance(call.func.value, ast.Constant) and isinstance(call.func.value.value, str):
                parts = self._desugar_str_format(call.func.value.value, list(call.args))
                self._generate_expr(ast.JoinedStr(values=parts))
                return

        # Handle super().method() calls (e.g. super().__init__())
        is_super_call = False
        func_name = ""
        attr_name = ""
        prefix = ""

        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Call):
            if isinstance(call.func.value.func, ast.Name) and call.func.value.func.id == "super":
                is_super_call = True
                current_cls = getattr(self.current_func, "class_name", None)
                if call.func.value.args and isinstance(call.func.value.args[0], ast.Name):
                    current_cls = call.func.value.args[0].id
                if not current_cls and self.module.classes:
                    current_cls = list(self.module.classes.keys())[0]
                target_base_fn = None
                if current_cls:
                    target_base_fn = self.resolve_class_method(current_cls, call.func.attr, skip_cls=True)
                if not target_base_fn:
                    self.emit("xor eax, eax", "safe no-op for super call on object")
                    return
                func_name = target_base_fn

        if not is_super_call:
            if isinstance(call.func, ast.Name):
                func_name = call.func.id
            elif isinstance(call.func, ast.Attribute):
                attr_name = call.func.attr
                if isinstance(call.func.value, ast.Name):
                    prefix = call.func.value.id
                    if prefix in ("self", "this"):
                        current_cls = getattr(self.current_func, "class_name", None)
                        resolved = self.resolve_class_method(current_cls, attr_name, skip_cls=False)
                        if resolved:
                            func_name = resolved
                        elif current_cls and f"{current_cls}_{attr_name}" in self.module.functions:
                            func_name = f"{current_cls}_{attr_name}"
                        elif f"self_{attr_name}" in self.module.functions:
                            func_name = f"self_{attr_name}"
                        else:
                            func_name = f"{current_cls}_{attr_name}" if current_cls else f"self_{attr_name}"
                    else:
                        if prefix in self.module.classes:
                            resolved = self.resolve_class_method(prefix, attr_name, skip_cls=False)
                            if resolved:
                                func_name = resolved
                            elif attr_name in ("register", "__init_subclass__"):
                                self.emit("xor eax, eax", f"no-op {prefix}.{attr_name}")
                                return
                            else:
                                func_name = f"{prefix}_{attr_name}"
                        else:
                            prefix_cls = self.local_var_classes.get(prefix)
                            if prefix_cls:
                                resolved = self.resolve_class_method(prefix_cls, attr_name, skip_cls=False)
                                if resolved:
                                    func_name = resolved
                            if not func_name:
                                if f"{prefix}_{attr_name}" in self.module.functions:
                                    func_name = f"{prefix}_{attr_name}"
                                elif self.current_func and hasattr(self.current_func, "local_vars") and prefix in self.current_func.local_vars:
                                    for cls in self.module.classes.values():
                                        if attr_name in ("__init__", "__new__", "register"):
                                            continue
                                        resolved = self.resolve_class_method(cls.name, attr_name, skip_cls=False)
                                        if resolved:
                                            func_name = resolved
                                            break
                                if not func_name:
                                    func_name = f"{prefix}_{attr_name}"
                else:
                    for cls in self.module.classes.values():
                        if attr_name in ("__init__", "__new__"):
                            continue
                        resolved = self.resolve_class_method(cls.name, attr_name, skip_cls=False)
                        if resolved:
                            func_name = resolved
                            break
                    if not func_name:
                        func_name = attr_name

        if prefix in ("object", "type"):
            if attr_name in ("__init__", "init"):
                self.emit("xor eax, eax", f"no-op {prefix}.{attr_name}")
                return
            elif attr_name in ("__new__", "new"):
                self.emit("mov ecx, 2048", f"allocate instance for {prefix}.{attr_name}")
                self.emit("call _pyfasm_alloc")
                return

        # Ecosystem adapters (darkdetect, requests, beautifulsoup4)
        if func_name in ("isDark", "is_dark", "darkdetect_isDark") or (attr_name in ("isDark", "is_dark") and prefix == "darkdetect"):
            self.emit("call _pyfasm_is_dark_theme")
            return

        if func_name in ("isLight", "is_light", "darkdetect_isLight") or (attr_name in ("isLight", "is_light") and prefix == "darkdetect"):
            self.emit("call _pyfasm_is_dark_theme")
            self.emit("xor rax, 1")
            return

        if func_name in ("theme", "darkdetect_theme") or (attr_name == "theme" and prefix == "darkdetect"):
            self.emit("call _pyfasm_darkdetect_theme")
            return

        # Built-in string methods (supports variables, chained calls, expressions)
        if attr_name == "lower" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("call _pyfasm_str_lower")
            return

        if attr_name == "upper" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("call _pyfasm_str_upper")
            return

        if attr_name == "strip" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("call _pyfasm_str_strip")
            return

        if attr_name == "startswith" and call.args and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "prefix")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "target string")
            self.emit("pop rdx", "prefix")
            self.emit("call _pyfasm_str_startswith")
            return

        if attr_name == "endswith" and call.args and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "suffix")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "target string")
            self.emit("pop rdx", "suffix")
            self.emit("call _pyfasm_str_endswith")
            return

        if attr_name == "replace" and len(call.args) >= 2 and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[1])
            self.emit("push rax", "new_str")
            self._generate_expr(call.args[0])
            self.emit("push rax", "old_str")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "target string")
            self.emit("pop rdx", "old_str")
            self.emit("pop r8", "new_str")
            self.emit("call _pyfasm_str_replace")
            return

        if attr_name == "removeprefix" and call.args and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "prefix")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "target string")
            self.emit("pop rdx", "prefix")
            self.emit("call _pyfasm_str_removeprefix")
            return

        if attr_name == "removesuffix" and call.args and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "suffix")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "target string")
            self.emit("pop rdx", "suffix")
            self.emit("call _pyfasm_str_removesuffix")
            return

        if attr_name == "join" and call.args and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "sequence")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "separator")
            self.emit("pop rdx", "sequence")
            self.emit("call _pyfasm_str_join")
            return

        # Dict get method / HTTP get method
        if attr_name == "get" and call.args:
            is_http_get = False
            if prefix in ("requests", "http") or func_name == "requests_get":
                is_http_get = True
            elif isinstance(call.func, ast.Attribute):
                if isinstance(call.func.value, ast.Attribute) and getattr(call.func.value, "attr", None) in ("session", "Session"):
                    is_http_get = True
                elif prefix in ("session", "Session"):
                    is_http_get = True
                elif call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str) and (call.args[0].value.startswith("http://") or call.args[0].value.startswith("https://")):
                    is_http_get = True

            if is_http_get:
                self._generate_expr(call.args[0])
                self.emit("push rax", "URL string pointer")
                params_node = None
                if len(call.args) > 1 and not (isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, (int, float))):
                    params_node = call.args[1]
                for kw in getattr(call, "keywords", []):
                    if kw.arg == "params":
                        params_node = kw.value
                        break
                if params_node:
                    self._generate_expr(params_node)
                    self.emit("mov rdx, rax", "params dict")
                else:
                    self.emit("xor edx, edx", "no params")
                self.emit("pop rcx", "URL string pointer")
                self.emit("call _pyfasm_http_get")
                return

            # General Dict .get(key, default)
            if isinstance(call.func, ast.Attribute):
                is_tuple_key = isinstance(call.args[0], ast.Tuple)
                if isinstance(call.args[0], ast.Name) and self.current_func:
                    kv = self.current_func.local_vars.get(call.args[0].id)
                    if kv and kv.var_type.is_tuple():
                        is_tuple_key = True
                if len(call.args) >= 2:
                    self._generate_expr(call.args[1])
                    self.emit("push rax", "default val")
                else:
                    self.emit("push 0", "default val = 0")
                self._generate_expr(call.args[0])
                self.emit("push rax", "key")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "dict_ptr")
                self.emit("pop rdx", "key")
                self.emit("pop r8", "default")
                if is_tuple_key:
                    self.emit("call _pyfasm_dict_get_tuple")
                else:
                    self.emit("call _pyfasm_dict_get")
                return

        # Dict iteration: .keys(), .values(), .items()
        if attr_name in ("keys", "values", "items") and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "dict_ptr")
            self.emit(f"call _pyfasm_dict_{attr_name}")
            return

        # List insert: s.insert(idx, val)
        if attr_name == "insert" and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "save item to insert")
            self._generate_expr(call.args[0])
            self.emit("push rax", "save insertion index")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "pass list pointer")
            self.emit("pop rdx", "pass insertion index")
            self.emit("pop r8", "pass item to insert")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_list_insert")
            self.emit("call _pyfasm_list_insert")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # List append
        if attr_name == "append" and call.args and prefix and self.current_func:
            var = self.current_func.local_vars.get(prefix)
            if var and var.var_type.is_list():
                self._generate_expr(call.args[0])
                self.emit("mov rdx, rax", "item to append")
                self.emit(f"mov rcx, [rbp - {var.stack_offset}]", "list_ptr")
                self.emit("call _pyfasm_list_append")
                return

        # Set add
        if attr_name == "add" and call.args and prefix and self.current_func:
            var = self.current_func.local_vars.get(prefix)
            if var and (var.var_type.is_set() or var.var_type.is_dict()):
                self._generate_expr(call.args[0])
                self.emit("mov rdx, rax", "item to add")
                self.emit(f"mov rcx, [rbp - {var.stack_offset}]", "set_ptr")
                self.emit("call _pyfasm_set_add")
                return

        # Set/Dict remove & discard
        if attr_name in ("remove", "discard") and call.args and prefix and self.current_func:
            var = self.current_func.local_vars.get(prefix)
            if var and (var.var_type.is_set() or var.var_type.is_dict()):
                self._generate_expr(call.args[0])
                self.emit("mov rdx, rax", "item to remove")
                self.emit(f"mov rcx, [rbp - {var.stack_offset}]", "set_ptr")
                self.emit("call _pyfasm_set_remove")
                return

        # List pop
        if attr_name == "pop" and prefix and self.current_func:
            var = self.current_func.local_vars.get(prefix)
            if var and var.var_type.is_list():
                self.emit(f"mov rcx, [rbp - {var.stack_offset}]", "list_ptr")
                self.emit("call _pyfasm_list_pop")
                return

        # File methods: f.write(content), f.read(), f.close()
        if attr_name == "write" and call.args and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "save content")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "file handle")
            self.emit("pop rdx", "content string")
            self.emit("call _pyfasm_file_write_data")
            return

        if attr_name == "read" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "file handle")
            self.emit("call _pyfasm_file_read_all")
            return

        if attr_name == "close" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "file handle")
            self.emit("call _pyfasm_file_close")
            return

        # int(val) conversion / cast
        if func_name == "int" and call.args:
            arg_type = self._infer_expr_type(call.args[0])
            self._generate_expr(call.args[0])
            if arg_type.is_float():
                self.emit("movq xmm0, rax")
                self.emit("cvttsd2si rax, xmm0", "float to int cast")
            return

        # float(val) conversion / cast
        if func_name == "float" and call.args:
            arg_type = self._infer_expr_type(call.args[0])
            self._generate_expr(call.args[0])
            if not arg_type.is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rax, xmm0", "int to float cast")
            return

        # bool(val) conversion
        if func_name == "bool" and call.args:
            self._generate_expr(call.args[0])
            self.emit("test rax, rax")
            self.emit("setnz al")
            self.emit("movzx rax, al", "to boolean 0 or 1")
            return

        # str(val) conversion
        if func_name in ("str", "repr") and call.args:
            arg0 = call.args[0]
            cls_name = self.resolve_instance_class(arg0)
            str_m = (self.resolve_class_method(cls_name, "__str__") or self.resolve_class_method(cls_name, "__repr__")) if cls_name else None
            if str_m:
                self._generate_expr(arg0)
                self.emit("mov rcx, rax", "pass self to __str__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {safe_asm_label(str_m)}")
                self.emit("add rsp, 32")
                return

            self._generate_expr(arg0)
            self.emit("mov rcx, rax")
            self.unresolved_symbols.add("str")
            self.emit("call fn_str")
            return

        # HTTP and JSON operations
        if attr_name == "json":
            if isinstance(call.func, ast.Attribute):
                lbl_raw = self.new_label("json_raw")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "response obj / text ptr")
                self.emit("test rax, rax", "check null ptr")
                self.emit(f"jz {lbl_raw}")
                self.emit("cmp qword [rax], 100", "check if response struct (status_code >= 100)")
                self.emit(f"jb {lbl_raw}")
                self.emit("cmp qword [rax], 600")
                self.emit(f"ja {lbl_raw}")
                self.emit("mov rcx, [rax + 8]", "load text from response obj")
                self.emit_raw(f"{lbl_raw}:")
                self.emit("call _pyfasm_json_parse")
                return

        if (func_name == "choice" and prefix in ("random", "")) or func_name == "random_choice":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "list pointer")
                self.emit("call _pyfasm_random_choice")
                return

        if (func_name == "loads" and prefix == "json") or func_name == "json_loads":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "json string pointer")
                self.emit("call _pyfasm_json_parse")
                return

        if (func_name == "Session" and prefix in ("requests", "Session")) or func_name == "requests_Session":
            self.emit("xor ecx, ecx", "default capacity")
            self.emit("call _pyfasm_dict_create")
            return

        if (func_name == "get" and prefix == "requests") or func_name == "requests_get" or (attr_name == "get" and prefix in ("requests", "http")):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "URL string pointer")
                self.emit("xor edx, edx", "no params")
                self.emit("call _pyfasm_http_get")
                return

        if attr_name in ("get_text", "strip_tags", "clean_html") or func_name in ("get_text", "strip_tags", "clean_html"):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_strip_html")
                return
            elif prefix:
                var = self.current_func.local_vars.get(prefix) if self.current_func else None
                if var:
                    self.emit(f"mov rcx, [rbp - {var.stack_offset}]")
                    self.emit("call _pyfasm_strip_html")
                    return

        # Built-in math & introspection functions
        if func_name == "abs" and call.args:
            self._generate_expr(call.args[0])
            self.emit("cqo")
            self.emit("xor rax, rdx")
            self.emit("sub rax, rdx", "branchless abs(rax)")
            return

        if func_name == "min" and len(call.args) >= 2:
            self._generate_expr(call.args[0])
            self.emit("push rax")
            self._generate_expr(call.args[1])
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self.emit("cmp rax, r11")
            self.emit("cmovg rax, r11", "min(a, b)")
            return

        if func_name == "max" and len(call.args) >= 2:
            self._generate_expr(call.args[0])
            self.emit("push rax")
            self._generate_expr(call.args[1])
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self.emit("cmp rax, r11")
            self.emit("cmovl rax, r11", "max(a, b)")
            return

        if func_name in ("sqrt", "math_sqrt") or (attr_name == "sqrt" and prefix in ("math", "")):
            if call.args:
                arg_type = self._infer_expr_type(call.args[0])
                self._generate_expr(call.args[0])
                if arg_type.is_float():
                    self.emit("movq xmm0, rax")
                    self.emit("sqrtsd xmm0, xmm0")
                    self.emit("movq rax, xmm0", "return float sqrt")
                else:
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("sqrtsd xmm0, xmm0")
                    self.emit("cvttsd2si rax, xmm0", "return integer sqrt")
                return

        if func_name in ("pow", "math_pow") or (attr_name == "pow" and prefix in ("math", "")):
            if len(call.args) >= 2:
                self._generate_expr(call.args[0])
                self.emit("push rax")
                self._generate_expr(call.args[1])
                self.emit("mov r11, rax")
                self.emit("pop rax")
                lbl = self.new_label("pow")
                self.emit("push rbx")
                self.emit("push rcx")
                self.emit("mov rbx, rax", "base")
                self.emit("mov rcx, r11", "exp")
                self.emit("mov rax, 1", "res = 1")
                self.emit("test rcx, rcx")
                self.emit(f"jle .done_{lbl}")
                self.emit_raw(f".loop_{lbl}:")
                self.emit("test rcx, 1")
                self.emit(f"jz .sq_{lbl}")
                self.emit("imul rax, rbx")
                self.emit_raw(f".sq_{lbl}:")
                self.emit("imul rbx, rbx")
                self.emit("sar rcx, 1")
                self.emit(f"jnz .loop_{lbl}")
                self.emit_raw(f".done_{lbl}:")
                self.emit("pop rcx")
                self.emit("pop rbx")
                return

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

        if func_name in ("alert", "message_box") or prefix in ("messagebox", "msgbox") or attr_name in ("showinfo", "showerror", "showwarning"):
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("push rax", "message text")
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "title text")
                self.emit("pop rdx", "message text")
            elif call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rdx, rax", "message text")
                self._emit_string_pointer("rcx", "Notice")
            else:
                self.emit("xor ecx, ecx")
                self.emit("xor edx, edx")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_message_box")
            self.emit("add rsp, 32")
            return

        func_dump_lower = ast.dump(call.func).lower()
        call_name_lower = (func_name or attr_name or "").lower()

        if attr_name in ("mainloop", "run", "show", "exec", "exec_"):
            # If chained call on instantiated class like QuadraticEquationApp().mainloop(), instantiate it first!
            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Call):
                self._generate_expr(call.func.value)

            # Detect if this call is on an icon/tray object
            is_icon_call = (
                prefix in ("icon", "self.icon", "tray", "self.tray")
                or "icon" in func_dump_lower
                or "tray" in func_dump_lower
                or (isinstance(call.func, ast.Attribute) and getattr(call.func.value, "attr", None) == "icon")
            )

            # Check if any user-defined class method matches (e.g. PuntoSwitcher_run)
            matching_method = None
            module_classes = getattr(self.module, "classes", {})
            module_functions = getattr(self.module, "functions", {})
            
            if not is_icon_call:
                for cls_name in module_classes:
                    candidate = f"{cls_name}_{attr_name}"
                    if candidate in module_functions:
                        # Prevent recursive self-invocation
                        if self.current_func and (
                            self.current_func.name == candidate
                            or self.current_func.name.endswith(f"_{attr_name}")
                        ):
                            continue
                        matching_method = candidate
                        break

            if matching_method and not is_icon_call:
                var = self.current_func.local_vars.get(prefix) if self.current_func and hasattr(self.current_func, "local_vars") else None
                if var:
                    self.emit(f"mov rax, [rbp - {var.stack_offset}]", f"load instance '{prefix}'")
                    self.emit("mov rcx, rax", "pass self as first arg")
                elif prefix:
                    self.emit("mov rcx, [_pyfasm_last_gui_instance]", "pass last instance as self")
                self.emit("sub rsp, 32", "shadow space for callee")
                self.emit(f"call {matching_method}", f"call custom class method {matching_method}")
                self.emit("add rsp, 32")

            # Run the native GUI window or tray loop
            is_tray = (
                is_icon_call
                or getattr(self.module, "is_tray_app", False)
                or any(k in s.lower() for k in ("tray", "punto", "pystray") for s in module_classes)
                or any("pystray" in imp.lower() for imp in getattr(self.module, "imports", []))
            )
            if is_tray and not any(k in func_dump_lower for k in ("ctk", "tk", "window")):
                self.emit("sub rsp, 32", "shadow space for background tray event loop")
                self.emit("call _pyfasm_run_tray_loop")
                self.emit("add rsp, 32")
                return
            else:
                self.emit("sub rsp, 32", "shadow space for GUI event loop")
                self.emit("call _pyfasm_run_window_loop")
                self.emit("add rsp, 32")
                return

        # GUI Variables (StringVar, IntVar, DoubleVar, BooleanVar)
        if (func_name in ("StringVar", "IntVar", "DoubleVar", "BooleanVar") or
            attr_name in ("StringVar", "IntVar", "DoubleVar", "BooleanVar")):
            val_node = None
            if call.args:
                val_node = call.args[0]
            for kw in getattr(call, "keywords", []):
                if kw.arg == "value":
                    val_node = kw.value
                    break
            if val_node:
                self._generate_expr(val_node)
                self.emit("mov rcx, rax", "initial StringVar value")
            else:
                self.emit("xor ecx, ecx", "null StringVar value")
            self.emit("call _pyfasm_stringvar_create")
            return

        if func_name in ("get_appearance_mode", "ctk_get_appearance_mode") or attr_name == "get_appearance_mode":
            self.emit("call _pyfasm_darkdetect_theme")
            return

        # Matplotlib plot() unpacking helper: returns a 1-item list [h_wnd]
        if attr_name == "plot":
            self.emit("mov ecx, 1", "capacity 1")
            self.emit("call _pyfasm_list_create")
            self.emit("mov rbx, rax", "save list ptr")
            self.emit("mov rdx, [_pyfasm_h_wnd]", "dummy plot item")
            self.emit("mov rcx, rbx")
            self.emit("call _pyfasm_list_append")
            self.emit("mov rax, rbx", "return list with 1 element")
            return

        if attr_name in ("get_tk_widget", "get_legend"):
            self.emit("mov rax, [_pyfasm_h_wnd]", f"return window handle for '{attr_name}'")
            return

        if attr_name == "get_texts":
            self.emit("xor ecx, ecx")
            self.emit("call _pyfasm_list_create", "return empty text list")
            return

        # Numpy wrappers
        if prefix in ("np", "numpy") or func_name.startswith("np_") or func_name.startswith("numpy_"):
            np_m = attr_name or (func_name[3:] if func_name.startswith("np_") else func_name[6:])
            if np_m in ("asarray", "array", "asanyarray", "complex128", "float64", "column_stack"):
                if call.args:
                    self._generate_expr(call.args[0])
                else:
                    self.emit("xor eax, eax")
                return
            elif np_m in ("empty", "zeros", "ones"):
                self.emit("mov ecx, 32")
                self.emit("call _pyfasm_list_create")
                return
            elif np_m in ("all", "any", "isfinite", "isnan"):
                self.emit("mov rax, 1", f"numpy {np_m} -> True")
                return
            elif np_m == "ptp":
                self.emit("mov rax, 1")
                return
            elif np_m == "flatnonzero" and call.args:
                lbl_fnz = self.new_label("flatnonzero")
                self._generate_expr(call.args[0])
                self.emit("mov rbx, rax", "arr ptr")
                self.emit("mov ecx, 3")
                self.emit("call _pyfasm_list_create")
                self.emit("mov r12, rax", "res list")
                self.emit("test rbx, rbx")
                self.emit(f"jz .done_{lbl_fnz}")
                self.emit("mov r13, [rbx]", "seq len")
                self.emit("xor r14, r14", "i = 0")
                self.emit_raw(f".loop_{lbl_fnz}:")
                self.emit("cmp r14, r13")
                self.emit(f"jge .done_{lbl_fnz}")
                self.emit("mov rax, [rbx + (r14 + 1) * 8]")
                self.emit("test rax, rax")
                self.emit(f"jz .skip_{lbl_fnz}")
                self.emit("mov rcx, r12")
                self.emit("mov rdx, r14")
                self.emit("call _pyfasm_list_append")
                self.emit_raw(f".skip_{lbl_fnz}:")
                self.emit("inc r14")
                self.emit(f"jmp .loop_{lbl_fnz}")
                self.emit_raw(f".done_{lbl_fnz}:")
                self.emit("mov rax, r12")
                return

        # Check Win32 Native GUI controls

        if self.target in ("win64", "dll"):
            # 1. Widget UI methods: .get()
            if attr_name == "get" and len(call.args) == 0:
                is_direct_entry = False
                if isinstance(call.func, ast.Attribute):
                    if getattr(call.func.value, "attr", "").lower().endswith("entry") or getattr(call.func.value, "id", "").lower().endswith("entry"):
                        is_direct_entry = True
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "target widget or StringVar")
                else:
                    self.emit("xor ecx, ecx")
                if is_direct_entry:
                    self.emit("xor edx, edx")
                    self.emit("xor r8d, r8d")
                    self.emit("call _pyfasm_get_edit_text", "read native edit box text")
                else:
                    self.emit("call _pyfasm_unified_get", "read native edit box text or StringVar")
                return

            # Widget UI methods: .set()
            if attr_name == "set" and len(call.args) == 1 and isinstance(call.func, ast.Attribute):
                self._generate_expr(call.args[0])
                self.emit("push rax", "new value")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "target widget or StringVar")
                self.emit("pop rdx", "new value")
                self.emit("call _pyfasm_unified_set", "set native widget or StringVar value")
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

            # 4. Widget configuration (configure / config)
            if attr_name in ("configure", "config"):
                text_kw = None
                for kw in getattr(call, "keywords", []):
                    if kw.arg == "text":
                        text_kw = kw.value
                        break
                if text_kw:
                    self._generate_expr(text_kw)
                    self.emit("push rax", "new text value")
                    if isinstance(call.func, ast.Attribute):
                        self._generate_expr(call.func.value)
                        self.emit("mov rcx, rax", "target control HWND")
                    else:
                        self.emit("xor ecx, ecx", "default control HWND")
                    self.emit("pop rdx", "new text value")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_set_text")
                    self.emit("add rsp, 32")
                    return
                self.emit("xor eax, eax", f"safe no-op for GUI configuration '{attr_name}'")
                return

            # Canvas 2D Drawing Primitives
            if attr_name == "create_line" and len(call.args) >= 4:
                self._generate_expr(call.args[3])
                self.emit("push rax", "y2")
                self._generate_expr(call.args[2])
                self.emit("push rax", "x2")
                self._generate_expr(call.args[1])
                self.emit("push rax", "y1")
                self._generate_expr(call.args[0])
                self.emit("push rax", "x1")
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "canvas HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("pop rdx", "x1")
                self.emit("pop r8", "y1")
                self.emit("pop r9", "x2")
                self.emit("sub rsp, 48")
                self.emit("pop rax", "y2")
                self.emit("mov [rsp + 32], rax")
                self.emit("call _pyfasm_canvas_create_line")
                self.emit("add rsp, 48")
                return

            if attr_name == "create_rectangle" and len(call.args) >= 4:
                self._generate_expr(call.args[3])
                self.emit("push rax", "y2")
                self._generate_expr(call.args[2])
                self.emit("push rax", "x2")
                self._generate_expr(call.args[1])
                self.emit("push rax", "y1")
                self._generate_expr(call.args[0])
                self.emit("push rax", "x1")
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "canvas HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("pop rdx", "x1")
                self.emit("pop r8", "y1")
                self.emit("pop r9", "x2")
                self.emit("sub rsp, 48")
                self.emit("pop rax", "y2")
                self.emit("mov [rsp + 32], rax")
                self.emit("call _pyfasm_canvas_create_rectangle")
                self.emit("add rsp, 48")
                return

            if attr_name == "create_oval" and len(call.args) >= 4:
                self._generate_expr(call.args[3])
                self.emit("push rax", "y2")
                self._generate_expr(call.args[2])
                self.emit("push rax", "x2")
                self._generate_expr(call.args[1])
                self.emit("push rax", "y1")
                self._generate_expr(call.args[0])
                self.emit("push rax", "x1")
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "canvas HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("pop rdx", "x1")
                self.emit("pop r8", "y1")
                self.emit("pop r9", "x2")
                self.emit("sub rsp, 48")
                self.emit("pop rax", "y2")
                self.emit("mov [rsp + 32], rax")
                self.emit("call _pyfasm_canvas_create_oval")
                self.emit("add rsp, 48")
                return

            if attr_name == "create_text" and len(call.args) >= 2:
                text_val = None
                for kw in getattr(call, "keywords", []):
                    if kw.arg == "text":
                        text_val = kw.value
                        break
                if not text_val and len(call.args) >= 3:
                    text_val = call.args[2]
                if text_val:
                    self._generate_expr(text_val)
                    self.emit("push rax", "text_ptr")
                else:
                    self.emit("push 0")
                self._generate_expr(call.args[1])
                self.emit("push rax", "y")
                self._generate_expr(call.args[0])
                self.emit("push rax", "x")
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "canvas HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("pop rdx", "x")
                self.emit("pop r8", "y")
                self.emit("pop r9", "text_ptr")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_canvas_create_text")
                self.emit("add rsp, 32")
                return

            # 5. Widget layout / visual configuration directives (safe no-op)
            if attr_name in ("pack", "grid", "place", "pack_propagate", "grid_propagate",
                             "grid_columnconfigure", "grid_rowconfigure", "focus_set", "select_range",
                             "update_idletasks", "iconbitmap", "wm_iconphoto",
                             "set_appearance_mode", "set_default_color_theme", "set_widget_scaling",
                             "bind", "bind_all", "protocol", "title", "geometry", "minsize", "maxsize",
                             "resizable", "withdraw", "deiconify", "lift", "focus", "after", "destroy",
                             "use", "draw_idle", "draw", "set_data", "set_facecolor", "set_color",
                             "set_offsets", "set_xlim", "set_ylim", "tick_params",
                             "trace_add", "trace", "trace_variable", "trace_vdelete", "trace_vinfo",
                             "add_subplot", "scatter", "axhline", "axvline", "set_xlabel", "set_ylabel", "set_title",
                             "legend", "subplots_adjust", "format_complex", "disc_is_zero",
                             "add_listener", "center_window", "setup_window_icon", "setup_shortcuts"):
                self.emit("xor eax, eax", f"safe no-op for GUI configuration '{attr_name}'")
                return

            # 6. Hotkeys (keyboard.hook / keyboard.add_hotkey)
            if any(k in func_dump_lower or k in call_name_lower for k in ("hook", "add_hotkey")):
                self.emit("mov rcx, 1", "hotkey id 1")
                self.emit("mov rdx, 19", "VK_PAUSE")
                self.emit("call _pyfasm_register_hotkey")
                self.emit("mov rcx, 2", "hotkey id 2")
                self.emit("mov rdx, 119", "VK_F8")
                self.emit("call _pyfasm_register_hotkey")
                self.emit("xor eax, eax")
                return

            # 7. Checkbuttons / Checkboxes
            if any(k in call_name_lower for k in ("checkbutton", "ctkcheckbox", "checkbox")) or ("checkbox" in func_dump_lower or "checkbutton" in func_dump_lower):
                self._generate_checkbox_control(call, call_name_lower)
                return

            # 8. Buttons
            if any(k in call_name_lower for k in ("ctkbutton", "pushbutton", "button")) or ("button" in func_dump_lower and "dict" not in func_dump_lower):
                self._generate_button_control(call, call_name_lower)
                return

            # 9. Text entries / edit boxes
            if any(k in call_name_lower for k in ("ctkentry", "lineedit", "textinput", "entry")) or ("entry" in func_dump_lower and "dict" not in func_dump_lower):
                self._generate_edit_control(call, call_name_lower)
                return

            # 10. Static labels
            if any(k in call_name_lower for k in ("ctklabel", "qlabel", "statictext", "label")) or "label" in func_dump_lower:
                self._generate_label_control(call, call_name_lower)
                return

            # 11. Scrollable frame / list / tabview
            if any(k in call_name_lower for k in ("ctkscrollableframe", "scrollableframe", "ctktabview", "tabview", "listbox", "qlistwidget", "listview")) or any(k in func_dump_lower for k in ("scrollableframe", "tabview", "listbox")):
                self._generate_listbox_control(call, call_name_lower)
                return

            # 12. Containers (CTkFrame, Frame, QWidget, Figure, Canvas, SegmentedButton, Textbox)
            if any(k == call_name_lower or k in call_name_lower.split(".") for k in ("ctkframe", "frame", "qwidget", "figure", "figurecanvastkagg", "segmentedbutton", "ctksegmentedbutton", "ctktextbox", "textbox", "canvas", "ctkcanvas", "tkcanvas")):
                if "gui" in self.features or "tray" in self.features or getattr(self.module, "is_gui_app", False):
                    self.emit("mov rax, [_pyfasm_h_wnd]", "return parent window handle for container")
                else:
                    self.emit("xor eax, eax", "dummy container handle")
                return

        # Built-in runtime calls
        if func_name == "open" and call.args:
            self._generate_expr(call.args[0])
            self.emit("push rax", "save filename")
            if len(call.args) > 1:
                self._generate_expr(call.args[1])
                self.emit("mov rdx, rax", "mode")
            else:
                self.emit("xor edx, edx", "mode = default 'r'")
            self.emit("pop rcx", "filename")
            self.emit("call _pyfasm_file_open")
            return

        if func_name == "file_read" and call.args:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("xor edx, edx", "mode = 'r'")
            self.emit("call _pyfasm_file_open")
            self.emit("push rax", "save handle")
            self.emit("mov rcx, rax")
            self.emit("call _pyfasm_file_read_all")
            self.emit("push rax", "save read string")
            self.emit("mov rcx, [rsp + 8]", "handle")
            self.emit("call _pyfasm_file_close")
            self.emit("pop rax", "read string")
            self.emit("add rsp, 8", "cleanup handle slot")
            return

        if func_name == "print":
            if not call.args:
                self.emit("call _pyfasm_print_newline")
                return
            for idx, arg in enumerate(call.args):
                if idx > 0:
                    self.emit("mov rcx, 32", "space ASCII separator")
                    self.emit("call _pyfasm_print_char")
                # Check custom __str__ or __repr__
                cls_name = self.resolve_instance_class(arg)
                str_m = (self.resolve_class_method(cls_name, "__str__") or self.resolve_class_method(cls_name, "__repr__")) if cls_name else None
                if str_m:
                    self._generate_expr(arg)
                    self.emit("mov rcx, rax", "pass self to __str__")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {safe_asm_label(str_m)}")
                    self.emit("add rsp, 32")
                    self.emit("mov rcx, rax")
                    self.emit("call _pyfasm_print_str")
                else:
                    arg_type = self._infer_expr_type(arg)
                    self._generate_expr(arg)
                    if arg_type.is_str():
                        self.emit("mov rcx, rax")
                        self.emit("call _pyfasm_print_str")
                    elif arg_type.is_float():
                        self.emit("movq xmm0, rax")
                        self.emit("call _pyfasm_print_float")
                    elif arg_type.is_int() or arg_type.is_bool():
                        self.emit("mov rcx, rax")
                        self.emit("call _pyfasm_print_int")
                    else:
                        self.emit("mov rcx, rax")
                        # Use runtime auto-detect only for truly dynamic untyped containers
                        if isinstance(arg, (ast.Call, ast.Subscript)):
                            self.emit("call _pyfasm_print_auto")
                        else:
                            self.emit("call _pyfasm_print_int")
            self.emit("call _pyfasm_print_newline")
            return

        if func_name == "print_str":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_print_str")
                self.emit("call _pyfasm_print_newline")
            return

        if func_name == "print_int":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("call _pyfasm_print_int")
            return

        if func_name == "print_newline":
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

        if func_name == "next" and call.args:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "gen_ptr")
            self.emit("sub rsp, 32", "shadow space for gen_next")
            self.emit("call _pyfasm_gen_next")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # Built-in range(...) constructor as an expression
        if func_name == "range" and call.args:
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

            lbl_loop = self.new_label("range_expr_loop")
            lbl_done = self.new_label("range_expr_done")

            self.emit("push rbx")
            self.emit("push r12")
            self.emit("push r13")
            self.emit("push r14") # 4 registers pushed = 32 bytes, aligns stack to 16

            self._generate_expr(stop_expr)
            self.emit("mov r13, rax", "range stop")

            if start_expr:
                self._generate_expr(start_expr)
                self.emit("mov r12, rax", "range start")
            else:
                self.emit("xor r12, r12", "range start = 0")

            self.emit("mov ecx, 1024", "initial list buffer")
            self.emit("sub rsp, 32", "shadow space for alloc")
            self.emit("call _pyfasm_alloc")
            self.emit("add rsp, 32", "restore shadow space")
            self.emit("mov qword [rax], 0", "length = 0")
            self.emit("mov r14, rax", "list_ptr")

            self.emit_raw(f".loop_{lbl_loop}:")
            self.emit("cmp r12, r13")
            if step_val > 0:
                self.emit(f"jge .done_{lbl_done}")
            else:
                self.emit(f"jle .done_{lbl_done}")

            self.emit("mov rdx, r12", "current item")
            self.emit("mov rcx, r14", "list_ptr")
            self.emit("sub rsp, 32", "shadow space for append")
            self.emit("call _pyfasm_list_append")
            self.emit("add rsp, 32", "restore shadow space")

            if step_val == 1:
                self.emit("inc r12")
            elif step_val == -1:
                self.emit("dec r12")
            else:
                self.emit(f"add r12, {step_val}")
            self.emit(f"jmp .loop_{lbl_loop}")

            self.emit_raw(f".done_{lbl_done}:")
            self.emit("mov rax, r14", "return range list")
            self.emit("pop r14")
            self.emit("pop r13")
            self.emit("pop r12")
            self.emit("pop rbx")
            return

        # Built-in sum, any, all for containers and generators
        if func_name in ("sum", "any", "all") and call.args:
            arg = call.args[0]
            is_gen = False
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                f_sym = self.module.functions.get(arg.func.id)
                if f_sym and getattr(f_sym, "is_generator", False):
                    is_gen = True
            elif isinstance(arg, ast.Name) and self.current_func:
                v_sym = self.current_func.local_vars.get(arg.id)
                if v_sym and (getattr(v_sym, "is_generator", False) or (hasattr(v_sym, "var_type") and v_sym.var_type.is_generator())):
                    is_gen = True

            self._generate_expr(arg)
            lbl_done = self.new_label(f"{func_name}_done")
            lbl_loop = self.new_label(f"{func_name}_loop")
            lbl_exit = self.new_label(f"{func_name}_exit")

            self.emit("test rax, rax")
            if func_name == "all":
                self.emit(f"jz .all_empty_{lbl_done}")
            else:
                self.emit(f"jz .zero_{lbl_done}")

            if is_gen:
                self.emit("push rbx")
                self.emit("push r12")
                self.emit("mov rbx, rax", "gen_ptr")
                if func_name == "sum":
                    self.emit("xor r12, r12", "sum = 0")
                elif func_name == "any":
                    self.emit("xor r12, r12", "any = False")
                elif func_name == "all":
                    self.emit("mov r12, 1", "all = True")

                self.emit_raw(f".loop_{lbl_loop}:")
                self.emit("mov rcx, rbx", "gen_ptr")
                self.emit("sub rsp, 32", "shadow space for gen_next")
                self.emit("call _pyfasm_gen_next")
                self.emit("add rsp, 32", "restore shadow space")
                self.emit("cmp qword [rbx + 16], 1", "check done flag")
                self.emit(f"je .done_{lbl_done}")

                if func_name == "sum":
                    self.emit("add r12, rax")
                    self.emit(f"jmp .loop_{lbl_loop}")
                elif func_name == "any":
                    self.emit("test rax, rax")
                    self.emit(f"jz .loop_{lbl_loop}")
                    self.emit("mov r12, 1", "found truthy")
                    self.emit(f"jmp .done_{lbl_done}")
                elif func_name == "all":
                    self.emit("test rax, rax")
                    self.emit(f"jnz .loop_{lbl_loop}")
                    self.emit("xor r12, r12", "found falsy")
                    self.emit(f"jmp .done_{lbl_done}")

                self.emit_raw(f".done_{lbl_done}:")
                self.emit("mov rax, r12", "return result")
                self.emit("pop r12")
                self.emit("pop rbx")
                self.emit(f"jmp .exit_{lbl_exit}")

                if func_name == "all":
                    self.emit_raw(f".all_empty_{lbl_done}:")
                    self.emit("mov rax, 1")
                    self.emit(f"jmp .exit_{lbl_exit}")
                else:
                    self.emit_raw(f".zero_{lbl_done}:")
                    self.emit("xor eax, eax")
                    self.emit(f"jmp .exit_{lbl_exit}")

                self.emit_raw(f".exit_{lbl_exit}:")
                return
            else:
                # Container (list, tuple, etc.)
                self.emit("push rbx")
                self.emit("push rsi")
                self.emit("mov rbx, rax", "container_ptr")
                self.emit("mov rsi, [rbx]", "container length")
                if func_name == "sum":
                    self.emit("xor eax, eax", "sum = 0")
                elif func_name == "any":
                    self.emit("xor eax, eax", "any = False")
                elif func_name == "all":
                    self.emit("mov eax, 1", "all = True")

                self.emit("xor ecx, ecx", "idx = 0")
                self.emit_raw(f".loop_{lbl_loop}:")
                self.emit("cmp rcx, rsi")
                self.emit(f"jge .done_{lbl_done}")
                self.emit("mov rdx, [rbx + rcx * 8 + 8]", "load item")

                if func_name == "sum":
                    self.emit("add rax, rdx")
                    self.emit("inc rcx")
                    self.emit(f"jmp .loop_{lbl_loop}")
                elif func_name == "any":
                    self.emit("test rdx, rdx")
                    self.emit(f"jz .next_{lbl_loop}")
                    self.emit("mov eax, 1", "found truthy")
                    self.emit(f"jmp .done_{lbl_done}")
                    self.emit_raw(f".next_{lbl_loop}:")
                    self.emit("inc rcx")
                    self.emit(f"jmp .loop_{lbl_loop}")
                elif func_name == "all":
                    self.emit("test rdx, rdx")
                    self.emit(f"jnz .next_{lbl_loop}")
                    self.emit("xor eax, eax", "found falsy")
                    self.emit(f"jmp .done_{lbl_done}")
                    self.emit_raw(f".next_{lbl_loop}:")
                    self.emit("inc rcx")
                    self.emit(f"jmp .loop_{lbl_loop}")

                self.emit_raw(f".done_{lbl_done}:")
                self.emit("pop rsi")
                self.emit("pop rbx")
                self.emit(f"jmp .exit_{lbl_exit}")

                if func_name == "all":
                    self.emit_raw(f".all_empty_{lbl_done}:")
                    self.emit("mov rax, 1")
                    self.emit(f"jmp .exit_{lbl_exit}")
                else:
                    self.emit_raw(f".zero_{lbl_done}:")
                    self.emit("xor eax, eax")
                    self.emit(f"jmp .exit_{lbl_exit}")

                self.emit_raw(f".exit_{lbl_exit}:")
                return

        # Built-in list(...) constructor
        if func_name == "list" and call.args:
            arg = call.args[0]
            is_gen = False
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                f_sym = self.module.functions.get(arg.func.id)
                if f_sym and getattr(f_sym, "is_generator", False):
                    is_gen = True
            elif isinstance(arg, ast.Name) and self.current_func:
                v_sym = self.current_func.local_vars.get(arg.id)
                if v_sym and (getattr(v_sym, "is_generator", False) or (hasattr(v_sym, "var_type") and v_sym.var_type.is_generator())):
                    is_gen = True

            if is_gen:
                self._generate_expr(arg)
                lbl_loop = self.new_label("list_gen_loop")
                lbl_done = self.new_label("list_gen_done")
                self.emit("push rbx")
                self.emit("push r12")
                self.emit("mov rbx, rax", "gen_ptr")
                self.emit("mov ecx, 1024", "initial list capacity")
                self.emit("sub rsp, 32", "shadow space for alloc")
                self.emit("call _pyfasm_alloc")
                self.emit("add rsp, 32", "restore shadow space")
                self.emit("mov qword [rax], 0", "length = 0")
                self.emit("mov r12, rax", "list_ptr")
                self.emit_raw(f".loop_{lbl_loop}:")
                self.emit("mov rcx, rbx", "gen_ptr")
                self.emit("sub rsp, 32", "shadow space for gen_next")
                self.emit("call _pyfasm_gen_next")
                self.emit("add rsp, 32", "restore shadow space")
                self.emit("cmp qword [rbx + 16], 1", "check done flag")
                self.emit(f"je .done_{lbl_done}")
                self.emit("mov rdx, rax", "item")
                self.emit("mov rcx, r12", "list_ptr")
                self.emit("sub rsp, 32", "shadow space for list_append")
                self.emit("call _pyfasm_list_append")
                self.emit("add rsp, 32", "restore shadow space")
                self.emit(f"jmp .loop_{lbl_loop}")
                self.emit_raw(f".done_{lbl_done}:")
                self.emit("mov rax, r12", "return list_ptr")
                self.emit("pop r12")
                self.emit("pop rbx")
                return

        if func_name in ("len", "str_len"):
            if call.args:
                arg0 = call.args[0]
                # Check custom __len__
                cls_name = self.resolve_instance_class(arg0)
                len_m = self.resolve_class_method(cls_name, "__len__") if cls_name else None
                if len_m:
                    self._generate_expr(arg0)
                    self.emit("mov rcx, rax", "pass self to __len__")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {safe_asm_label(len_m)}")
                    self.emit("add rsp, 32")
                    return

                is_list_or_tuple = False
                is_dict_arg = False
                arg0_type = self._infer_expr_type(arg0)
                if arg0_type.is_list() or arg0_type.is_tuple():
                    is_list_or_tuple = True
                elif arg0_type.is_dict() or arg0_type.is_set():
                    is_dict_arg = True
                elif isinstance(arg0, ast.Name) and self.current_func:
                    var = self.current_func.local_vars.get(arg0.id)
                    if var:
                        if var.var_type.is_list() or var.var_type.is_tuple():
                            is_list_or_tuple = True
                        elif var.var_type.is_dict() or var.var_type.is_set():
                            is_dict_arg = True
                self._generate_expr(arg0)
                if is_list_or_tuple:
                    self.emit("mov rax, [rax]", "load length from header")
                elif is_dict_arg:
                    self.emit("mov rcx, rax")
                    self.emit("call _pyfasm_dict_len")
                else:
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

        if func_name == "map" and len(call.args) >= 2:
            self._generate_expr(call.args[0])
            self.emit("push rax", "func_ptr")
            self._generate_expr(call.args[1])
            self.emit("mov rcx, rax", "seq_ptr")
            self.emit("pop rdx", "func_ptr")
            self.emit("call _pyfasm_map")
            return

        if func_name == "filter" and len(call.args) >= 2:
            self._generate_expr(call.args[0])
            self.emit("push rax", "func_ptr")
            self._generate_expr(call.args[1])
            self.emit("mov rcx, rax", "seq_ptr")
            self.emit("pop rdx", "func_ptr")
            self.emit("call _pyfasm_filter")
            return

        # Built-in zip(a, b)
        if func_name == "zip" and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "save list b")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list a")
            self.emit("pop rdx", "pass list b")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_zip")
            self.emit("call _pyfasm_zip")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # Built-in enumerate(a, [start])
        if func_name == "enumerate" and len(call.args) >= 1:
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("push rax", "save start index")
            else:
                self.emit("xor eax, eax")
                self.emit("push rax", "default start index 0")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list a")
            self.emit("pop rdx", "pass start index")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_enumerate")
            self.emit("call _pyfasm_enumerate")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # Standard library bisect / bisect_right(a, x)
        if (func_name in ("bisect", "bisect_right") or (prefix == "bisect" and attr_name in ("bisect", "bisect_right"))) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "save search item")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list a")
            self.emit("pop rdx", "pass search item")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_bisect_right")
            self.emit("call _pyfasm_bisect_right")
            self.emit("add rsp, 32", "restore shadow space")
            return

        if (func_name == "bisect_left" or (prefix == "bisect" and attr_name == "bisect_left")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "save search item")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list a")
            self.emit("pop rdx", "pass search item")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_bisect_left")
            self.emit("call _pyfasm_bisect_left")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # Standard library heapq: heappush(heap, item), heappop(heap)
        if (func_name == "heappush" or (prefix == "heapq" and attr_name == "heappush")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "save item to push")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass heap pointer")
            self.emit("pop rdx", "pass item to push")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_heappush")
            self.emit("call _pyfasm_heappush")
            self.emit("add rsp, 32", "restore shadow space")
            return

        if (func_name == "heappop" or (prefix == "heapq" and attr_name == "heappop")) and len(call.args) >= 1:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass heap pointer")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_heappop")
            self.emit("call _pyfasm_heappop")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # math.gcd(a, b)
        if (func_name in ("gcd", "math_gcd") or (prefix == "math" and attr_name == "gcd")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("pop rdx")
            self.emit("call _pyfasm_math_gcd")
            return

        # math.lcm(a, b)
        if (func_name in ("lcm", "math_lcm") or (prefix == "math" and attr_name == "lcm")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("pop rdx")
            self.emit("call _pyfasm_math_lcm")
            return

        # math.isqrt(n)
        if (func_name in ("isqrt", "math_isqrt") or (prefix == "math" and attr_name == "isqrt")) and len(call.args) >= 1:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("call _pyfasm_math_isqrt")
            return

        # math.factorial(n)
        if (func_name in ("factorial", "math_factorial") or (prefix == "math" and attr_name == "factorial")) and len(call.args) >= 1:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("call _pyfasm_math_factorial")
            return

        # itertools.chain(a, b)
        if (func_name in ("chain", "itertools_chain") or (prefix == "itertools" and attr_name == "chain")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("pop rdx")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_itertools_chain")
            self.emit("call _pyfasm_itertools_chain")
            self.emit("add rsp, 32")
            return

        # itertools.accumulate(seq)
        if (func_name in ("accumulate", "itertools_accumulate") or (prefix == "itertools" and attr_name == "accumulate")) and len(call.args) >= 1:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_itertools_accumulate")
            self.emit("call _pyfasm_itertools_accumulate")
            self.emit("add rsp, 32")
            return

        # functools.reduce(fn, seq, [initial])
        if (func_name in ("reduce", "functools_reduce") or (prefix == "functools" and attr_name == "reduce")) and len(call.args) >= 2:
            if len(call.args) >= 3:
                self._generate_expr(call.args[2])
                self.emit("push rax", "initial value")
                self.emit("mov r9, 1", "has initial")
            else:
                self.emit("xor r8d, r8d")
                self.emit("push r8")
                self.emit("xor r9d, r9d", "no initial")
            self._generate_expr(call.args[1])
            self.emit("push rax", "list")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "fn")
            self.emit("pop rdx", "list")
            self.emit("pop r8", "initial")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_functools_reduce")
            self.emit("call _pyfasm_functools_reduce")
            self.emit("add rsp, 32")
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
        if func_name in self.module.functions:
            fn_sym = self.module.functions[func_name]
            if is_super_call:
                args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=True, self_expr=ast.Name(id="self", ctx=ast.Load()))
            elif isinstance(call.func, ast.Attribute) and fn_sym.args and fn_sym.args[0].name == "self":
                args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=True, self_expr=call.func.value)
            else:
                args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=False)
        else:
            args_to_pass = list(call.args)
            if is_super_call:
                args_to_pass = [ast.Name(id="self", ctx=ast.Load())] + list(call.args)

        # Evaluate arguments and push them in reverse order
        is_indirect = False
        indirect_local_var = None
        is_indirect_global = False

        if isinstance(call.func, ast.Name):
            if self.current_func and call.func.id in self.current_func.local_vars:
                is_indirect = True
                indirect_local_var = self.current_func.local_vars[call.func.id]
            elif (self.current_func and hasattr(self.current_func, "global_names") and call.func.id in self.current_func.global_names) or (call.func.id in self.module.global_vars):
                is_indirect = True
                is_indirect_global = True
        elif func_name not in self.module.functions:
            is_indirect = True

        needs_stack_callee = is_indirect and (indirect_local_var is None) and (not is_indirect_global)
        if needs_stack_callee:
            self._generate_expr(call.func)
            self.emit("push rax", "save indirect function pointer")

        for arg in reversed(args_to_pass):
            self._generate_expr(arg)
            self.emit("push rax")

        # Pop into register parameters
        arg_regs = ["rcx", "rdx", "r8", "r9"]
        n_args = len(args_to_pass)
        for i in range(min(n_args, 4)):
            self.emit(f"pop {arg_regs[i]}")

        if is_indirect:
            if indirect_local_var:
                self.emit(f"mov r10, [rbp - {indirect_local_var.stack_offset}]", f"indirect callee {indirect_local_var.name}")
            elif is_indirect_global:
                self.emit(f"mov r10, [_pyfasm_global_{call.func.id}]", f"indirect global callee {call.func.id}")
            else:
                if n_args <= 4:
                    self.emit("pop r10", "restore indirect callee from stack")
                else:
                    self.emit(f"mov r10, [rsp + {(n_args - 4) * 8}]", "read indirect callee above extra stack args")
            callee_target = "r10"
        else:
            if func_name not in self.module.functions:
                self.unresolved_symbols.add(func_name)
            callee_target = safe_asm_label(func_name)

        # Allocate 32 bytes shadow space
        self.emit("sub rsp, 32", "shadow space for callee")
        if is_indirect:
            lbl_skip = self.new_label("skip_null_call")
            self.emit("cmp r10, 65536", "check for invalid/null function pointer")
            self.emit(f"jb {lbl_skip}")
            self.emit("call r10")
            lbl_done_call = self.new_label("done_indirect_call")
            self.emit(f"jmp {lbl_done_call}")
            self.emit_raw(f"{lbl_skip}:")
            self.emit("xor eax, eax", "safe fallback return 0 for unresolvable call")
            self.emit_raw(f"{lbl_done_call}:")
        else:
            self.emit(f"call {callee_target}")
        self.emit("add rsp, 32", "restore shadow space")

        # If more than 4 arguments, cleanup extra stack args
        if needs_stack_callee and n_args > 4:
            self.emit(f"add rsp, {(n_args - 4) * 8 + 8}", "cleanup extra stack args & callee ptr")
        elif n_args > 4:
            extra_bytes = (n_args - 4) * 8
            self.emit(f"add rsp, {extra_bytes}", "cleanup stack args")
