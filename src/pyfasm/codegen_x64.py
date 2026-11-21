"""
x86_64 Code Generator for PyFASM.
Emits clean, optimized Flat Assembler (FASM) assembly instructions.
"""
from __future__ import annotations
import ast
import math
from pathlib import Path
import re
import struct
from typing import List, Dict, Optional, Tuple, Set, Any
_AST_MATCH = getattr(ast, 'Match', ())
_AST_MATCH_AS = getattr(ast, 'MatchAs', ())
_AST_MATCH_VALUE = getattr(ast, 'MatchValue', ())
_AST_MATCH_OR = getattr(ast, 'MatchOr', ())
from pyfasm.ast_parser import ParsedModule, FunctionSymbol, VariableSymbol, StringLiteral, walk_local_scope
from pyfasm.diagnostics import CompilerDiagnostic, extract_source_line
from pyfasm.types import (
    TYPE_INT, TYPE_FLOAT, TYPE_STR, TYPE_LIST, TYPE_DICT, TYPE_SET,
    TYPE_TUPLE, TYPE_BOOL, TYPE_PTR, TYPE_VOID, PyFasmType,
    ListType, DictType, SetType, TupleType, InstanceType,
)

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


_CALLEE_REG_PATTERNS = [
    ("rbx", re.compile(r'\b(rbx|ebx|bx|bl|bh)\b', re.I)),
    ("rsi", re.compile(r'\b(rsi|esi|si|sil)\b', re.I)),
    ("rdi", re.compile(r'\b(rdi|edi|di|dil)\b', re.I)),
    ("r12", re.compile(r'\b(r12|r12d|r12w|r12b)\b', re.I)),
    ("r13", re.compile(r'\b(r13|r13d|r13w|r13b)\b', re.I)),
    ("r14", re.compile(r'\b(r14|r14d|r14w|r14b)\b', re.I)),
    ("r15", re.compile(r'\b(r15|r15d|r15w|r15b)\b', re.I)),
]


_ASCII_IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")


def safe_asm_label(name: str) -> str:
    """Escapes identifiers that conflict with FASM reserved keywords, instructions, or invalid syntax."""
    if not name:
        return "sym_anon"
    if not name.isascii():
        parts = []
        for ch in name:
            if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("0" <= ch <= "9"):
                parts.append(ch)
            elif ch == "_":
                parts.append("__")
            else:
                parts.append(f"_u{ord(ch):04x}_")
        return "u_" + "".join(parts)
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not sanitized:
        return "sym_anon"
    if sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    if sanitized.lower() in RESERVED_FASM_KEYWORDS:
        sanitized = f"fn_{sanitized}"
    return sanitized


def safe_global_label(name: str) -> str:
    """Return a valid FASM label for a module or class global variable without ASCII collisions."""
    if name and name.isascii() and _ASCII_IDENT_RE.match(name):
        return f"_pyfasm_global_{name}"
    return f"_pyfasm_global_{safe_asm_label(name)}"


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
        self.unresolved_locations: Dict[str, Tuple[Optional[str], Optional[int], Optional[int], Optional[int]]] = {}
        self.diagnostics: List[CompilerDiagnostic] = list(getattr(module, "diagnostics", []))
        self.local_var_classes: Dict[str, str] = {}
        self._class_ids: Dict[str, int] = {
            cname: idx for idx, cname in enumerate(sorted(module.classes.keys()), start=1)
        }
        self._used_vcalls: Set[str] = set()
        self.gui_control_id = 1000
        self.gui_edit_id = 100
        self.gui_chip_count = 0

    def _record_unresolved(self, sym: str, node: Optional[ast.AST] = None) -> None:
        self.unresolved_symbols.add(sym)
        if sym not in self.unresolved_locations:
            src_file = getattr(self.current_func, "source_file", None) if self.current_func else None
            ln = getattr(node, "lineno", None) if node is not None else None
            col0 = getattr(node, "col_offset", None) if node is not None else None
            col = (col0 + 1) if isinstance(col0, int) else None
            end_col0 = getattr(node, "end_col_offset", None) if node is not None else None
            end_ln = getattr(node, "end_lineno", ln) if node is not None else ln
            end_col = (end_col0 + 1) if (isinstance(end_col0, int) and end_ln == ln) else None
            self.unresolved_locations[sym] = (src_file, ln, col, end_col)

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
        cls_name = self.resolve_instance_class(expr_node)
        if not cls_name and isinstance(expr_node, ast.Call) and isinstance(expr_node.func, ast.Name):
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

    def _resolve_field_class(self, cls_name: Optional[str], field_name: str) -> Optional[str]:
        if not cls_name:
            return None
        visited: Set[str] = set()
        queue = [cls_name]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            cs = self.module.classes.get(curr)
            if not cs:
                continue
            if hasattr(cs, "properties") and field_name in cs.properties:
                prop = cs.properties[field_name]
                gname = getattr(prop, "getter_name", None)
                if gname and gname in self.module.functions:
                    rt = self.module.functions[gname].return_type
                    if isinstance(rt, InstanceType):
                        return rt.class_name
            if hasattr(cs, "field_classes") and field_name in cs.field_classes:
                return cs.field_classes[field_name]
            if hasattr(cs, "field_types") and field_name in cs.field_types:
                ft = cs.field_types[field_name]
                if isinstance(ft, InstanceType):
                    return ft.class_name
            for b in cs.bases:
                if b not in visited:
                    queue.append(b)
        return None

    def resolve_instance_class(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None or isinstance(node, ast.Constant):
            return None
        if isinstance(node, ast.Name):
            if node.id in ("self", "this"):
                return getattr(self.current_func, "class_name", None)
            if node.id in self.local_var_classes:
                return self.local_var_classes[node.id]
            if self.current_func and node.id in self.current_func.local_vars:
                vt = self.current_func.local_vars[node.id].var_type
                if isinstance(vt, InstanceType):
                    return vt.class_name
            gvt = getattr(self.module, "global_var_types", {}).get(node.id)
            if isinstance(gvt, InstanceType):
                return gvt.class_name
            return None
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fid = node.func.id
                if fid in self.module.classes:
                    return fid
                if getattr(self.current_func, "is_classmethod", False) and self.current_func and self.current_func.args:
                    if fid == self.current_func.args[0].name:
                        return self.current_func.class_name
                if fid in self.module.functions:
                    rt = self.module.functions[fid].return_type
                    if isinstance(rt, InstanceType):
                        return rt.class_name
            elif isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                if isinstance(node.func.value, ast.Name) and node.func.value.id in self.module.classes:
                    target_cls = node.func.value.id
                    m = self.resolve_class_method(target_cls, attr)
                    if m and m in self.module.functions:
                        fn_sym = self.module.functions[m]
                        if getattr(fn_sym, "is_classmethod", False) and (
                            isinstance(fn_sym.return_type, InstanceType) or fn_sym.return_type == TYPE_VOID
                        ):
                            return target_cls
                        if isinstance(fn_sym.return_type, InstanceType):
                            return fn_sym.return_type.class_name
                else:
                    recv_cls = self.resolve_instance_class(node.func.value)
                    if not recv_cls and isinstance(node.func.value, ast.Name) and node.func.value.id == "cls":
                        if getattr(self.current_func, "is_classmethod", False):
                            recv_cls = self.current_func.class_name
                    if recv_cls:
                        m = self.resolve_class_method(recv_cls, attr)
                        if m and m in self.module.functions:
                            rt = self.module.functions[m].return_type
                            if isinstance(rt, InstanceType):
                                return rt.class_name
            return None
        if isinstance(node, ast.Attribute):
            owner_cls = self.resolve_instance_class(node.value)
            if not owner_cls and isinstance(node.value, ast.Name) and node.value.id in self.module.classes:
                owner_cls = node.value.id
            if owner_cls:
                fc = self._resolve_field_class(owner_cls, node.attr)
                if fc:
                    return fc
            return None
        if isinstance(node, ast.Subscript) and not isinstance(node.slice, ast.Slice):
            vt = self._infer_expr_type(node.value)
            if isinstance(vt, InstanceType):
                return vt.class_name
            if vt.is_list() or vt.is_tuple() or vt.is_set():
                et = getattr(vt, "element_type", None)
                if isinstance(et, InstanceType):
                    return et.class_name
            elif vt.is_dict():
                dvt = getattr(vt, "val_type", None)
                if isinstance(dvt, InstanceType):
                    return dvt.class_name
            return None
        if isinstance(node, ast.BinOp):
            return self.resolve_instance_class(node.left)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Invert)):
            return self.resolve_instance_class(node.operand)
        return None

    def _class_hierarchy_includes(self, sub_cls: Optional[str], base_cls: str) -> bool:
        if not sub_cls or not base_cls:
            return False
        if sub_cls == base_cls:
            return True
        visited: Set[str] = set()
        queue = [sub_cls]
        while queue:
            curr = queue.pop(0)
            if curr == base_cls:
                return True
            if curr in visited:
                continue
            visited.add(curr)
            cs = self.module.classes.get(curr)
            if cs:
                for b in cs.bases:
                    if b not in visited:
                        queue.append(b)
        return False

    def _all_subclasses(self, base_cls: Optional[str]) -> List[str]:
        if not base_cls:
            return sorted(self.module.classes.keys())
        return [
            cname for cname in sorted(self.module.classes.keys())
            if self._class_hierarchy_includes(cname, base_cls)
        ]

    def _method_has_polymorphic_impls(self, cls_name: Optional[str], method_name: str) -> bool:
        candidates = self._all_subclasses(cls_name) if cls_name else sorted(self.module.classes.keys())
        if len(candidates) <= 1 and cls_name is not None:
            return False
        targets: Set[Optional[str]] = set()
        for cname in candidates:
            cs = self.module.classes.get(cname)
            if cs and method_name in getattr(cs, "static_methods", set()):
                continue
            if method_name == "__str__":
                m = self.resolve_class_method(cname, "__str__") or self.resolve_class_method(cname, "__repr__")
            elif method_name == "__repr__":
                m = self.resolve_class_method(cname, "__repr__") or self.resolve_class_method(cname, "__str__")
            elif method_name == "__bool__":
                m = self.resolve_class_method(cname, "__bool__") or self.resolve_class_method(cname, "__len__")
            else:
                m = self.resolve_class_method(cname, method_name)
            targets.add(m)
        non_none = {t for t in targets if t is not None}
        if method_name == "__bool__":
            return len(non_none) > 1 or (len(non_none) == 1 and None in targets)
        return len(non_none) > 1

    def _vcall_label(self, method_name: str) -> str:
        return f"_pyfasm_vcall_{safe_asm_label(method_name)}"

    def _emit_vcall_trampolines(self) -> None:
        if not self._used_vcalls:
            return
        self.emit_raw("; ============================================================")
        self.emit_raw("; Polymorphic Class VCall Trampolines")
        self.emit_raw("; ============================================================")
        for method_name in sorted(self._used_vcalls):
            lbl = self._vcall_label(method_name)
            lbl_ret0 = f".vcall_ret0_{safe_asm_label(method_name)}"
            lbl_true = f".vcall_true_{safe_asm_label(method_name)}"
            self.emit_raw(f"{lbl}:")
            self.emit("test rcx, rcx", f"polymorphic dispatch for {method_name}")
            self.emit(f"jz {lbl_ret0}")
            self.emit("cmp rcx, 65536")
            self.emit(f"jb {lbl_ret0}")
            self.emit("mov r10, 505946434C535447h", "PYFCLSTG")
            self.emit("cmp [rcx + 2032], r10")
            self.emit(f"jne {lbl_ret0}")
            self.emit("mov r10, [rcx + 2040]", "load runtime class_id")

            if method_name == "__bool__":
                len_thunks: List[Tuple[str, str]] = []
                for cname in sorted(self.module.classes.keys()):
                    cid = self._class_ids.get(cname, 0)
                    if not cid:
                        continue
                    bm = self.resolve_class_method(cname, "__bool__")
                    if bm:
                        self.emit(f"cmp r10, {cid}")
                        self.emit(f"je {safe_asm_label(bm)}")
                    else:
                        lm = self.resolve_class_method(cname, "__len__")
                        if lm:
                            t_lbl = f".vcall_bool_len_{safe_asm_label(cname)}"
                            self.emit(f"cmp r10, {cid}")
                            self.emit(f"je {t_lbl}")
                            len_thunks.append((t_lbl, lm))
                self.emit_raw(f"{lbl_true}:")
                self.emit("mov rax, 1", "default truthiness for instance without __bool__/__len__")
                self.emit("ret")
                for t_lbl, lm in len_thunks:
                    self.emit_raw(f"{t_lbl}:")
                    self.emit("sub rsp, 40")
                    self.emit(f"call {safe_asm_label(lm)}")
                    self.emit("add rsp, 40")
                    self.emit("test rax, rax")
                    self.emit("setnz al")
                    self.emit("movzx rax, al")
                    self.emit("ret")
            else:
                for cname in sorted(self.module.classes.keys()):
                    cid = self._class_ids.get(cname, 0)
                    if not cid:
                        continue
                    cs = self.module.classes[cname]
                    if method_name in getattr(cs, "static_methods", set()):
                        continue
                    if method_name == "__str__":
                        m = self.resolve_class_method(cname, "__str__") or self.resolve_class_method(cname, "__repr__")
                    elif method_name == "__repr__":
                        m = self.resolve_class_method(cname, "__repr__") or self.resolve_class_method(cname, "__str__")
                    else:
                        m = self.resolve_class_method(cname, method_name)
                    if m:
                        self.emit(f"cmp r10, {cid}")
                        self.emit(f"je {safe_asm_label(m)}")
            self.emit_raw(f"{lbl_ret0}:")
            self.emit("xor eax, eax")
            self.emit("ret")
            self.emit_raw("")

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
        if is_method_call and expected_args and (expected_args[0].name == "self" or getattr(target_fn, "is_classmethod", False)):
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

    def _is_ambiguous_dynamic_expr(self, expr: Optional[ast.AST]) -> bool:
        """True when an expression has dynamically typed (int vs str pointer) representation at runtime."""
        if expr is None or isinstance(expr, ast.Constant):
            return False
        if isinstance(expr, ast.Name):
            if self.current_func and hasattr(self.current_func, "local_vars") and expr.id in self.current_func.local_vars:
                sym = self.current_func.local_vars[expr.id]
                return bool(getattr(sym, "is_dynamic", False) and sym.var_type == TYPE_INT)
            return False
        if isinstance(expr, ast.Subscript) and not isinstance(expr.slice, ast.Slice):
            ct = self._infer_expr_type(expr.value)
            if ct.is_list() and getattr(ct, "element_type", None) is None:
                return True
            if ct.is_tuple() and getattr(ct, "element_type", None) is None and getattr(ct, "element_types", None) is None:
                return True
            if ct.is_dict() and getattr(ct, "val_type", None) is None:
                return True
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Attribute) and expr.func.attr in ("pop", "get"):
                ct = self._infer_expr_type(expr.func.value)
                if ct.is_list() and getattr(ct, "element_type", None) is None:
                    return True
                if ct.is_dict() and getattr(ct, "val_type", None) is None and len(expr.args) < 2:
                    return True
            if isinstance(expr.func, ast.Name):
                if expr.func.id in self.module.functions:
                    if getattr(self.module.functions[expr.func.id], "is_dynamic_return", False):
                        return True
                else:
                    inst_cls = self.resolve_instance_class(expr.func)
                    if not (inst_cls and self.resolve_class_method(inst_cls, "__call__")):
                        if self._infer_expr_type(expr) == TYPE_INT:
                            return True
            elif isinstance(expr.func, ast.Subscript) and self._infer_expr_type(expr) == TYPE_INT:
                return True
        return self._infer_expr_type(expr) == TYPE_PTR

    def _method_call_target(self, cls_name: Optional[str], vcall_key: str, concrete_target: str) -> str:
        if cls_name and self._method_has_polymorphic_impls(cls_name, vcall_key):
            self._used_vcalls.add(vcall_key)
            return self._vcall_label(vcall_key)
        return safe_asm_label(concrete_target)

    def _emit_truthy_check(self, expr: ast.AST, lbl_false: str) -> None:
        """Evaluate `expr` and jump to `lbl_false` when falsy per Python semantics."""
        cls_name = self.resolve_instance_class(expr)
        if cls_name:
            bool_m = self.resolve_class_method(cls_name, "__bool__")
            len_m = self.resolve_class_method(cls_name, "__len__")
            poly_bool = self._method_has_polymorphic_impls(cls_name, "__bool__")
            self._generate_expr(expr)
            self.emit("test rax, rax")
            self.emit(f"jz {lbl_false}")
            if poly_bool:
                self._used_vcalls.add("__bool__")
                self.emit("mov rcx, rax", "pass self to polymorphic __bool__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._vcall_label('__bool__')}")
                self.emit("add rsp, 32")
                self.emit("test rax, rax")
                self.emit(f"jz {lbl_false}")
            elif bool_m or len_m:
                target_fn = bool_m or len_m
                self.emit("mov rcx, rax", f"pass self to {'__bool__' if bool_m else '__len__'}")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {safe_asm_label(target_fn)}")
                self.emit("add rsp, 32")
                self.emit("test rax, rax")
                self.emit(f"jz {lbl_false}")
            return

        vt = self._infer_expr_type(expr)
        is_seq = False
        is_str = False
        if vt.is_list() or vt.is_tuple() or vt.is_dict() or vt.is_set():
            is_seq = True
        elif vt.is_str():
            is_str = True
        elif isinstance(expr, ast.Name) and self.current_func:
            v = self.current_func.local_vars.get(expr.id)
            if v:
                if v.var_type.is_list() or v.var_type.is_tuple() or v.var_type.is_dict() or v.var_type.is_set():
                    is_seq = True
                elif v.var_type.is_str():
                    is_str = True

        self._generate_expr(expr)
        self.emit("test rax, rax")
        self.emit(f"jz {lbl_false}")
        if is_seq:
            self.emit("cmp qword [rax], 0", "check empty container")
            self.emit(f"jz {lbl_false}")
        elif is_str:
            self.emit("cmp byte [rax], 0", "check empty string")
            self.emit(f"jz {lbl_false}")

    def _emit_to_bool(self, expr: ast.AST, negate: bool = False) -> None:
        lbl_false = self.new_label("tobool_false")
        lbl_done = self.new_label("tobool_done")
        self._emit_truthy_check(expr, lbl_false)
        self.emit(f"mov rax, {0 if negate else 1}")
        self.emit(f"jmp {lbl_done}")
        self.emit_raw(f"{lbl_false}:")
        self.emit(f"mov rax, {1 if negate else 0}")
        self.emit_raw(f"{lbl_done}:")

    def _select_win64_elem_printer(self, elem_t: Optional[PyFasmType]) -> str:
        if elem_t is None:
            return "_pyfasm_print_auto_repr"
        if elem_t.is_str():
            return "_pyfasm_print_str_repr"
        if elem_t.is_float():
            return "_pyfasm_print_float_bits"
        if elem_t.is_int() or elem_t.is_bool():
            return "_pyfasm_print_int"
        if elem_t.is_list():
            return self._select_win64_list_printer(elem_t)
        if elem_t.is_tuple():
            return self._select_win64_tuple_printer(elem_t)
        return "_pyfasm_print_auto_repr"

    def _select_win64_list_printer(self, list_t: PyFasmType) -> str:
        elem_t = getattr(list_t, "element_type", None)
        if elem_t is None:
            return "_pyfasm_print_list"
        if elem_t.is_str():
            return "_pyfasm_print_list_str"
        if elem_t.is_float():
            return "_pyfasm_print_list_float"
        if elem_t.is_int() or elem_t.is_bool():
            return "_pyfasm_print_list_int"
        if elem_t.is_list():
            inner = getattr(elem_t, "element_type", None)
            if inner is None:
                return "_pyfasm_print_list_2d_auto"
            if inner.is_str():
                return "_pyfasm_print_list_2d_str"
            if inner.is_float():
                return "_pyfasm_print_list_2d_float"
            if inner.is_int() or inner.is_bool():
                return "_pyfasm_print_list_2d_int"
            if inner.is_list():
                return "_pyfasm_print_list_3d_int"
            return "_pyfasm_print_list_2d_auto"
        return "_pyfasm_print_list"

    def _select_win64_tuple_printer(self, tup_t: PyFasmType) -> str:
        elem_t = getattr(tup_t, "element_type", None)
        if elem_t is None:
            return "_pyfasm_print_tuple"
        if elem_t.is_str():
            return "_pyfasm_print_tuple_str"
        if elem_t.is_float():
            return "_pyfasm_print_tuple_float"
        if elem_t.is_int() or elem_t.is_bool():
            return "_pyfasm_print_tuple_int"
        if elem_t.is_list():
            return "_pyfasm_print_tuple_list"
        return "_pyfasm_print_tuple"

    def _select_win64_elem_to_str(self, elem_t: Optional[PyFasmType]) -> str:
        if elem_t is None:
            return "_pyfasm_auto_to_repr"
        if elem_t.is_str():
            return "_pyfasm_str_to_repr"
        if elem_t.is_float():
            return "_pyfasm_float_to_str"
        if elem_t.is_int() or elem_t.is_bool():
            return "_pyfasm_int_to_str"
        if elem_t.is_list():
            return self._select_win64_list_to_str(elem_t)
        if elem_t.is_tuple():
            return self._select_win64_tuple_to_str(elem_t)
        return "_pyfasm_auto_to_repr"

    def _select_win64_list_to_str(self, list_t: PyFasmType) -> str:
        elem_t = getattr(list_t, "element_type", None)
        if elem_t is None:
            return "_pyfasm_list_to_str"
        if elem_t.is_str():
            return "_pyfasm_list_str_to_str"
        if elem_t.is_float():
            return "_pyfasm_list_float_to_str"
        if elem_t.is_int() or elem_t.is_bool():
            return "_pyfasm_list_int_to_str"
        if elem_t.is_list():
            inner = getattr(elem_t, "element_type", None)
            if inner is None:
                return "_pyfasm_list_2d_auto_to_str"
            if inner.is_str():
                return "_pyfasm_list_2d_str_to_str"
            if inner.is_float():
                return "_pyfasm_list_2d_float_to_str"
            if inner.is_int() or inner.is_bool():
                return "_pyfasm_list_2d_int_to_str"
            if inner.is_list():
                return "_pyfasm_list_3d_int_to_str"
            return "_pyfasm_list_2d_auto_to_str"
        return "_pyfasm_list_to_str"

    def _select_win64_tuple_to_str(self, tup_t: PyFasmType) -> str:
        elem_t = getattr(tup_t, "element_type", None)
        if elem_t is None:
            return "_pyfasm_tuple_to_str"
        if elem_t.is_str():
            return "_pyfasm_tuple_str_to_str"
        if elem_t.is_float():
            return "_pyfasm_tuple_float_to_str"
        if elem_t.is_int() or elem_t.is_bool():
            return "_pyfasm_tuple_int_to_str"
        if elem_t.is_list():
            return "_pyfasm_tuple_list_to_str"
        return "_pyfasm_tuple_to_str"

    def _emit_win64_to_str(
        self,
        expr: ast.AST,
        is_repr: bool = False,
        call_node: Optional[ast.Call] = None,
    ) -> None:
        """Convert `expr` to a null-terminated UTF-8 string pointer in RAX."""
        cls_name = self.resolve_instance_class(expr)
        vkey = "__repr__" if is_repr else "__str__"
        if is_repr:
            str_m = (self.resolve_class_method(cls_name, "__repr__") or self.resolve_class_method(cls_name, "__str__")) if cls_name else None
        else:
            str_m = (self.resolve_class_method(cls_name, "__str__") or self.resolve_class_method(cls_name, "__repr__")) if cls_name else None
        if str_m:
            self._generate_expr(expr)
            self.emit("mov rcx, rax", "pass self to __str__")
            self.emit("sub rsp, 32", "shadow space")
            self.emit(f"call {self._method_call_target(cls_name, vkey, str_m)}")
            self.emit("add rsp, 32")
            return

        if isinstance(expr, ast.Constant) and expr.value is None:
            self.emit("lea rax, [none_str]")
            return

        part_type = self._infer_expr_type(expr)
        self._generate_expr(expr)
        if (
            part_type.is_str()
            or isinstance(expr, ast.JoinedStr)
            or (isinstance(expr, ast.Constant) and isinstance(expr.value, str))
        ):
            if is_repr:
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_str_to_repr")
                self.emit("add rsp, 32")
            return
        if part_type.is_float():
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_float_to_str")
            self.emit("add rsp, 32")
            return
        if part_type.is_list():
            helper = self._select_win64_list_to_str(part_type)
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit(f"call {helper}")
            self.emit("add rsp, 32")
            return
        if part_type.is_tuple():
            helper = self._select_win64_tuple_to_str(part_type)
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit(f"call {helper}")
            self.emit("add rsp, 32")
            return
        if part_type.is_dict():
            kt = getattr(part_type, "key_type", None)
            vt = getattr(part_type, "val_type", None)
            k_fn = self._select_win64_elem_to_str(kt)
            v_fn = self._select_win64_elem_to_str(vt)
            self.emit("mov rcx, rax")
            self.emit(f"lea rdx, [{k_fn}]")
            self.emit(f"lea r8, [{v_fn}]")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_dict_to_str_with")
            self.emit("add rsp, 32")
            return
        if part_type.is_set():
            et = getattr(part_type, "element_type", None)
            e_fn = self._select_win64_elem_to_str(et)
            self.emit("mov rcx, rax")
            self.emit(f"lea rdx, [{e_fn}]")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_set_to_str_with")
            self.emit("add rsp, 32")
            return
        if not part_type.is_bool() and self._is_ambiguous_dynamic_expr(expr):
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit(f"call {'_pyfasm_auto_to_repr' if is_repr else '_pyfasm_auto_to_str'}")
            self.emit("add rsp, 32")
            return

        if call_node is not None and not is_repr:
            self.emit("mov rcx, rax")
            self._record_unresolved("str", call_node)
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call fn_str")
            self.emit("add rsp, 32")
            return

        self.emit("mov rcx, rax")
        self.emit("sub rsp, 32", "shadow space")
        self.emit("call _pyfasm_int_to_str")
        self.emit("add rsp, 32")

    def _generate_fstring_part(self, part: ast.AST) -> None:
        if isinstance(part, ast.Constant):
            self._emit_string_pointer("rax", str(part.value))
        elif isinstance(part, ast.FormattedValue):
            if self.target in ("win64", "dll"):
                self._emit_win64_to_str(part.value, is_repr=False)
                return
            cls_name = self.resolve_instance_class(part.value)
            str_m = (
                self.resolve_class_method(cls_name, "__str__")
                or self.resolve_class_method(cls_name, "__repr__")
            ) if cls_name else None
            if str_m:
                self._generate_expr(part.value)
                self.emit("mov rcx, rax", "pass self to __str__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(cls_name, '__str__', str_m)}")
                self.emit("add rsp, 32")
                return

            part_type = self._infer_expr_type(part.value)
            self._generate_expr(part.value)
            if (
                part_type.is_str()
                or isinstance(part.value, ast.JoinedStr)
                or (isinstance(part.value, ast.Constant) and isinstance(part.value.value, str))
            ):
                return
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_int_to_str")
            self.emit("add rsp, 32")
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
            val = flit.value
            is_neg_zero = (val == 0.0 and math.copysign(1.0, val) < 0.0)
            if math.isfinite(val) and not is_neg_zero:
                lines.append(f"    {flit.label} dq {repr(val)}")
            else:
                bits = struct.unpack("<Q", struct.pack("<d", val))[0]
                lines.append(f"    {flit.label} dq 0x{bits:016X}")

        # Emit global variables
        for gname, gval in self.module.global_vars.items():
            # Sanitize Python values to valid FASM integer constants
            if isinstance(gval, bool):
                gval = 1 if gval else 0
            elif not isinstance(gval, int):
                gval = 0
            lines.append(f"    {safe_global_label(gname)} dq {gval}")

        lines.append("    _pyfasm_stop_iter dq 0")
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
        self.emit_raw("_pyfasm_funcs_start:")

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

        self._emit_vcall_trampolines()
        self.emit_raw("_pyfasm_funcs_end:")

        # Fallback stubs for unresolved external Python symbols
        if self.unresolved_symbols:
            self.emit_raw("")
            self.emit_raw("; ============================================================")
            self.emit_raw("; Unresolved External Python Symbols / Fallback Stubs")
            self.emit_raw("; ============================================================")
            for sym in sorted(self.unresolved_symbols):
                if sym in ("bisect", "bisect_right", "bisect_left", "zip", "enumerate", "heappush", "heappop", "heapify", "heapreplace", "sorted", "sort", "list_sort", "matmul", "nanogemm_matmul", "nanogemm_simd_isa", "get_simd_isa", "zeros", "ones", "gcd", "lcm", "isqrt", "factorial", "chain", "accumulate", "reduce", "set", "count", "math_gcd", "_pyfasm_closure_new", "_pyfasm_closure_get", "StopIteration"):
                    continue
                lbl = safe_asm_label(sym)
                self.emit_raw(f"{lbl}:")
                if sym == "str":
                    self.emit("jmp _pyfasm_int_to_str")
                else:
                    loc = self.unresolved_locations.get(sym, (None, None, None, None))
                    src_file, ln, col, end_col = loc
                    src_line = extract_source_line(
                        src_file, ln, getattr(self.module, "source_files", None)
                    )
                    self.diagnostics.append(
                        CompilerDiagnostic(
                            severity="warning",
                            code="W3001",
                            message=f"Unresolved external symbol '{sym}' (emitted fallback stub returning 0)",
                            file_path=src_file,
                            lineno=ln,
                            col_offset=col,
                            end_col_offset=end_col,
                            source_line=src_line,
                            hint=(
                                f"Define '{sym}', import its pure-Python module, or compile "
                                "with `--strict` to treat unresolved symbols as errors."
                            ),
                        )
                    )
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

    def _get_resources_section(self, use_relative_icon: bool = True) -> str:
        # The icon is embedded inline (see pyfasm.icon_resource), so the generated
        # assembly never depends on the .ico location; ``use_relative_icon`` is kept
        # for backwards API compatibility only.
        if self.target in ("win64", "dll") and self.icon_path and Path(self.icon_path).exists():
            from pyfasm.icon_resource import build_icon_rsrc_section
            return build_icon_rsrc_section(self.icon_path)
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
        rsrc_content = self._get_resources_section(use_relative_icon=True)
        if rsrc_content:
            res_dict["resources.inc"] = rsrc_content
            res_dict["main.asm"] = res_dict["main.asm"].strip() + "\n\ninclude 'resources.inc'\n"
        if self.target == "dll":
            res_dict["reloc.inc"] = (
                "section '.reloc' fixups data readable discardable\n"
                "if $=$$\n"
                "    dd 0, 8\n"
                "end if\n"
            )
            res_dict["main.asm"] = res_dict["main.asm"].strip() + "\n\ninclude 'reloc.inc'\n"
        return res_dict

    def generate(self, relative_icon: bool = False) -> str:
        if getattr(self.module, "ui_spec", None) and getattr(self.module.ui_spec, "has_canvas", False):
            from pyfasm.ui_codegen import generate_ui_app_asm
            return generate_ui_app_asm(self.module.ui_spec)
        header = self._get_runtime_header()
        data = self._get_data_section()
        entry = self._get_entry_point()
        funcs = self._get_functions_section()
        runtime = self._get_runtime_code()
        imports = self._get_imports_section()
        rsrc = self._get_resources_section(use_relative_icon=relative_icon)
        raw_parts = [header, data, entry, funcs, runtime, imports]
        if rsrc:
            raw_parts.append(rsrc)
        if self.target == "dll":
            raw_parts.append(
                "section '.reloc' fixups data readable discardable\n"
                "if $=$$\n"
                "    dd 0, 8\n"
                "end if\n"
            )
        raw = "\n".join(raw_parts)
        from pyfasm.optimizer import optimize_fasm_code
        return optimize_fasm_code(raw)

    def _generate_constructor_body(self, cls_sym: Any) -> None:
        n_ctor_args = len(self.current_func.args) if self.current_func else 0
        self_slot = max(40, (n_ctor_args + 1) * 8)
        self.emit("mov ecx, 2048", f"allocate 2048 bytes for class '{cls_sym.name}' instance")
        self.emit("call _pyfasm_alloc")
        self.emit(f"mov [rbp - {self_slot}], rax", "save self instance pointer")
        cid = self._class_ids.get(cls_sym.name, 0)
        if cid:
            self.emit("mov r10, 505946434C535447h", f"class tag PYFCLSTG for '{cls_sym.name}'")
            self.emit("mov [rax + 2032], r10")
            self.emit(f"mov qword [rax + 2040], {cid}", f"class_id = {cid}")

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
            self.emit(f"mov rax, [rbp - {self_slot}]")
            self.emit("mov [_pyfasm_last_gui_instance], rax", "store tray instance pointer")
        elif is_gui and self.target in ("win64", "dll"):
            self.emit("call _pyfasm_init_gui", "initialize native GUI system")
            self.emit("call _pyfasm_ensure_window", "ensure native Win32 window is created")
            self.emit(f"mov rax, [rbp - {self_slot}]")
            self.emit("mov [_pyfasm_last_gui_instance], rax", "store GUI instance pointer for callbacks")

        # Call __init__ if present (including inherited __init__)
        init_target = self.resolve_class_method(cls_sym.name, "__init__", skip_cls=False)
        if not init_target:
            if f"{cls_sym.name}___init__" in self.module.functions:
                init_target = f"{cls_sym.name}___init__"
            elif "__init__" in cls_sym.methods:
                init_target = f"{cls_sym.name}___init__"

        if init_target:
            extra_args = list(self.current_func.args[3:]) if (self.current_func and len(self.current_func.args) > 3) else []
            pad = 8 if (len(extra_args) % 2 == 1) else 0
            if pad:
                self.emit(f"sub rsp, {pad}", "align stack for extra __init__ args")
            for extra_arg in reversed(extra_args):
                self.emit(f"mov rax, [rbp - {extra_arg.stack_offset}]")
                self.emit("push rax", f"forward ctor arg {extra_arg.name}")
            self.emit(f"mov rcx, [rbp - {self_slot}]", "pass self as first arg")
            self.emit("mov rdx, [rbp - 8]", "pass arg 1")
            self.emit("mov r8, [rbp - 16]", "pass arg 2")
            self.emit("mov r9, [rbp - 24]", "pass arg 3")
            self.emit("sub rsp, 32", "shadow space for __init__")
            self.emit(f"call {safe_asm_label(init_target)}")
            self.emit(f"add rsp, {32 + len(extra_args) * 8 + pad}", "cleanup __init__ call")

        self.emit(f"mov rax, [rbp - {self_slot}]", "return instance self pointer")

    def _generate_function(self, fn: FunctionSymbol, aliases: Optional[List[str]] = None) -> None:
        if getattr(fn, "is_generator", False):
            self._generate_generator_function(fn, aliases)
            return

        self.current_func = fn
        self.local_var_classes = {}
        if fn.class_name:
            self.local_var_classes["self"] = fn.class_name
            self.local_var_classes["this"] = fn.class_name
        for vname, vsym in fn.local_vars.items():
            if isinstance(vsym.var_type, InstanceType):
                self.local_var_classes[vname] = vsym.var_type.class_name
        for asym in fn.args:
            if isinstance(asym.var_type, InstanceType):
                self.local_var_classes[asym.name] = asym.var_type.class_name
        self.emit_raw("; ============================================================")
        self.emit_raw(f"; Function: {fn.name}")
        self.emit_raw("; ============================================================")
        fn_lbl = safe_asm_label(fn.name)
        if aliases:
            for alias in aliases:
                self.emit_raw(f"{safe_asm_label(alias)}:")
        else:
            self.emit_raw(f"{fn_lbl}:")

        # Generate Function Body into temporary buffer to detect modified callee-saved registers
        saved_lines = self.lines
        self.lines = []
        if fn.name in self.module.classes:
            self._generate_constructor_body(self.module.classes[fn.name])
        elif fn.ast_node:
            for stmt in fn.ast_node.body:
                self._generate_statement(stmt)

        if fn.name == "main":
            self.emit("xor eax, eax", "default return 0 for main")
        body_lines = self.lines
        self.lines = saved_lines

        used_callee: List[str] = []
        non_save_ops = {
            "push", "cmp", "test", "call", "jmp", "jz", "jnz", "je", "jne",
            "jl", "jle", "jg", "jge", "jb", "jbe", "ja", "jae", "js", "jns", "ret",
        }
        str_ops = {"scasb", "scasw", "scasd", "scasq", "stosb", "stosw", "stosd", "stosq", "repne", "repe", "rep"}
        for reg_name, pat in _CALLEE_REG_PATTERNS:
            modified = False
            for raw_l in body_lines:
                stmt_txt = raw_l.split(";", 1)[0].strip()
                if not stmt_txt or stmt_txt.endswith(":"):
                    continue
                op_parts = stmt_txt.split(None, 1)
                op_kw = op_parts[0].lower()
                if op_kw in non_save_ops:
                    continue
                if op_kw in str_ops:
                    if reg_name == "rdi" or (reg_name == "rsi" and "movs" in stmt_txt.lower()):
                        modified = True
                        break
                    continue
                if len(op_parts) > 1:
                    dst_op = op_parts[1].split(",", 1)[0].strip()
                    if not dst_op.startswith("[") and pat.search(dst_op):
                        modified = True
                        break
            if modified:
                used_callee.append(reg_name)

        used_local_end = max(
            [v.stack_offset for v in fn.local_vars.values()]
            + [a.stack_offset for a in fn.args]
            + ([max(40, (len(fn.args) + 1) * 8)] if fn.name in self.module.classes else [])
            + [0]
        )
        save_base = ((used_local_end + 7) // 8) * 8
        save_offsets = [(reg, save_base + (i + 1) * 8) for i, reg in enumerate(used_callee)]
        total_local_bytes = save_base + len(save_offsets) * 8
        total_stack = max(fn.stack_size, ((total_local_bytes + 15) // 16) * 16 + 32)
        if total_stack % 16 != 0:
            total_stack = ((total_stack + 15) // 16) * 16

        # Prolog
        self.emit("push rbp")
        self.emit("mov rbp, rsp")
        self.emit(f"sub rsp, {total_stack}", "frame + shadow space")
        for reg, off in save_offsets:
            self.emit(f"mov [rbp - {off}], {reg}", f"save callee-saved {reg}")

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

        self.lines.extend(body_lines)

        # Epilog
        self.emit_raw(f".epilog_{safe_asm_label(fn.name)}:")
        for reg, off in reversed(save_offsets):
            self.emit(f"mov {reg}, [rbp - {off}]", f"restore callee-saved {reg}")
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
                                self.emit(f"mov [{safe_global_label(tgt_elt.id)}], rax", f"store global {tgt_elt.id}")
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
                                self.emit(f"mov [{safe_global_label(tgt.id)}], rax", f"store global {tgt.id}")

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
                                self.emit(f"mov [{safe_global_label(tgt.id)}], rax", f"store global {tgt.id}")

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
                            self.emit(f"mov [{safe_global_label(starred_target.id)}], rax", f"store global {starred_target.id}")
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
                                self.emit(f"mov [{safe_global_label(tgt_elt.id)}], rax", f"store global {tgt_elt.id}")
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
            assigned_cls = self.resolve_instance_class(stmt.value)

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
                        self.emit(f"mov [{safe_global_label(target.id)}], rax", f"store global {target.id}")
                        if self.current_func and self.current_func.name.startswith("_pyfasm_modinit_"):
                            curr_mod = self.current_func.name[len("_pyfasm_modinit_"):]
                            if f"{curr_mod}_{target.id}" in self.module.global_vars:
                                self.emit(f"mov [{safe_global_label(f'{curr_mod}_{target.id}')}], rax", f"store module global {curr_mod}_{target.id}")
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
                        is_ptr_target = False
                        if isinstance(target.value, ast.Name) and self.current_func:
                            v = self.current_func.local_vars.get(target.value.id)
                            if v and (v.var_type == TYPE_PTR or any(k in v.name.lower() for k in ("mem", "ptr", "buffer"))):
                                is_ptr_target = True
                        elif self._infer_expr_type(target.value) == TYPE_PTR:
                            is_ptr_target = True

                        lbl_skip_store = self.new_label("skip_arr_store")
                        self.emit("test r8, r8", "check null array")
                        self.emit(f"jz {lbl_skip_store}")
                        self.emit("cmp r8, 65536", "check valid user-mode pointer")
                        self.emit(f"jb {lbl_skip_store}")
                        if not is_ptr_target:
                            lbl_idx_pos = self.new_label("idx_pos")
                            self.emit("test r11, r11", "check negative index")
                            self.emit(f"jns {lbl_idx_pos}")
                            self.emit("add r11, [r8]", "negative index: len + idx")
                            self.emit_raw(f"{lbl_idx_pos}:")
                        self.emit("test r11, r11", "check negative index")
                        self.emit(f"js {lbl_skip_store}")
                        self.emit("cmp r11, 1000000", "check index bounds")
                        self.emit(f"jae {lbl_skip_store}")
                        if is_ptr_target:
                            self.emit("mov [r8 + r11 * 8], rax", "store mem[idx] = val")
                        else:
                            self.emit("mov [r8 + (r11 + 1) * 8], rax", "store list[idx] = val")
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
                        self.emit(f"mov [{safe_global_label(namespaced)}], rax", f"assign module global {namespaced}")
                        if target.attr in self.module.global_vars:
                            self.emit(f"mov [{safe_global_label(target.attr)}], rax", f"assign global {target.attr}")
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
                    assigned_cls = self.resolve_instance_class(stmt.value)
                    if assigned_cls:
                        self.local_var_classes[stmt.target.id] = assigned_cls
                    var = self.current_func.local_vars.get(stmt.target.id) if self.current_func else None
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"assign {var.name}")
                    elif (self.current_func and hasattr(self.current_func, "global_names") and stmt.target.id in self.current_func.global_names) or (stmt.target.id in self.module.global_vars):
                        self.emit(f"mov [{safe_global_label(stmt.target.id)}], rax", f"store global {stmt.target.id}")

        elif isinstance(stmt, ast.AugAssign):
            # Target += Expr
            if isinstance(stmt.target, ast.Name):
                var = self.current_func.local_vars.get(stmt.target.id) if self.current_func else None
                is_global = (self.current_func and hasattr(self.current_func, "global_names") and stmt.target.id in self.current_func.global_names) or (stmt.target.id in self.module.global_vars)
                aug_dunder_map = {
                    ast.Add: ("__iadd__", "__add__"),
                    ast.Sub: ("__isub__", "__sub__"),
                    ast.Mult: ("__imul__", "__mul__"),
                    ast.FloorDiv: ("__ifloordiv__", "__floordiv__"),
                    ast.Div: ("__itruediv__", "__truediv__"),
                    ast.Mod: ("__imod__", "__mod__"),
                    ast.Pow: ("__ipow__", "__pow__"),
                    ast.BitAnd: ("__iand__", "__and__"),
                    ast.BitOr: ("__ior__", "__or__"),
                    ast.BitXor: ("__ixor__", "__xor__"),
                    ast.LShift: ("__ilshift__", "__lshift__"),
                    ast.RShift: ("__irshift__", "__rshift__"),
                }
                tgt_cls = self.resolve_instance_class(stmt.target)
                aug_m = None
                aug_key = None
                if tgt_cls and type(stmt.op) in aug_dunder_map:
                    inplace_d, fallback_d = aug_dunder_map[type(stmt.op)]
                    aug_m = self.resolve_class_method(tgt_cls, inplace_d)
                    if aug_m:
                        aug_key = inplace_d
                    else:
                        aug_m = self.resolve_class_method(tgt_cls, fallback_d)
                        if aug_m:
                            aug_key = fallback_d
                if aug_m and aug_key and (var or is_global):
                    self._generate_expr(stmt.value)
                    self.emit("push rax", "save augassign rhs")
                    if var:
                        self.emit(f"mov rcx, [rbp - {var.stack_offset}]", f"load {var.name}")
                    else:
                        self.emit(f"mov rcx, [{safe_global_label(stmt.target.id)}]", f"load global {stmt.target.id}")
                    self.emit("pop rdx", "restore rhs")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {self._method_call_target(tgt_cls, aug_key, aug_m)}")
                    self.emit("add rsp, 32")
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"update {var.name}")
                    else:
                        self.emit(f"mov [{safe_global_label(stmt.target.id)}], rax", f"update global {stmt.target.id}")
                elif var:
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
                    self.emit(f"mov rax, [{safe_global_label(stmt.target.id)}]", f"load global {stmt.target.id}")
                    self.emit("push rax")
                    self._generate_expr(stmt.value)
                    self.emit("mov r11, rax")
                    self.emit("pop rax")
                    self._generate_binop_instr(stmt.op)
                    self.emit(f"mov [{safe_global_label(stmt.target.id)}], rax", f"update global {stmt.target.id}")
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

            self._emit_truthy_check(stmt.test, l_else)

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
            self._emit_truthy_check(stmt.test, l_normal)

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
            self._emit_with_items(list(stmt.items), list(stmt.body))

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
            is_stop_iter = False
            if isinstance(stmt.exc, ast.Name) and stmt.exc.id == "StopIteration":
                is_stop_iter = True
            elif isinstance(stmt.exc, ast.Call) and isinstance(stmt.exc.func, ast.Name) and stmt.exc.func.id == "StopIteration":
                is_stop_iter = True

            if is_stop_iter:
                self.emit("mov qword [_pyfasm_stop_iter], 1", "signal StopIteration")
                self.emit("mov rax, 1")
                if self.try_stack:
                    self.emit(f"jmp {self.try_stack[-1]}", "jump to active except handler")
                elif self.current_func:
                    self.emit("xor eax, eax", "return from __next__ on StopIteration")
                    self._emit_func_exit()
                else:
                    self.emit("xor ecx, ecx")
                    self.emit("sub rsp, 40")
                    self.emit("call [ExitProcess]")
            else:
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
                        self.emit("sub rsp, 40")
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
                if self.current_func and self.current_func.name != "main":
                    self.emit("xor eax, eax", "assertion failure in function returns 0")
                    self._emit_func_exit()
                else:
                    self.emit("mov ecx, 1", "AssertionError exit code 1")
                    self.emit("sub rsp, 40")
                    self.emit("call [ExitProcess]")
            self.emit_raw(f"{lbl_ok}:")

        elif isinstance(stmt, ast.Delete):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and self.current_func:
                    var = self.current_func.local_vars.get(target.id)
                    if var:
                        self.emit(f"mov qword [rbp - {var.stack_offset}], 0", f"del {var.name}")

        elif isinstance(stmt, _AST_MATCH):
            self._generate_match(stmt)

    def _emit_with_items(self, items: List[ast.withitem], body: List[ast.stmt]) -> None:
        if not items:
            for s in body:
                self._generate_statement(s)
            return

        item = items[0]
        rest = items[1:]
        ctx_cls = self.resolve_instance_class(item.context_expr)
        enter_m = self.resolve_class_method(ctx_cls, "__enter__") if ctx_cls else None
        exit_m = self.resolve_class_method(ctx_cls, "__exit__") if ctx_cls else None

        if enter_m or exit_m:
            self._generate_expr(item.context_expr)
            self.emit("sub rsp, 16", "aligned slot for with context manager")
            self.emit("mov [rsp], rax", "save context object")

            if enter_m:
                lbl_skip_enter = self.new_label("skip_enter")
                self.emit("test rax, rax")
                self.emit(f"jz {lbl_skip_enter}")
                self.emit("mov rcx, [rsp]", "pass self to __enter__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(ctx_cls, '__enter__', enter_m)}")
                self.emit("add rsp, 32")
                self.emit_raw(f"{lbl_skip_enter}:")

            if item.optional_vars is not None:
                if isinstance(item.optional_vars, ast.Name):
                    enter_cls = ctx_cls
                    if enter_m and enter_m in self.module.functions:
                        rt = self.module.functions[enter_m].return_type
                        if isinstance(rt, InstanceType):
                            enter_cls = rt.class_name
                        elif rt != TYPE_VOID:
                            enter_cls = None
                    if enter_cls:
                        self.local_var_classes[item.optional_vars.id] = enter_cls
                self._assign_target(item.optional_vars, "rax")

            self._emit_with_items(rest, body)

            if exit_m:
                lbl_skip_exit = self.new_label("skip_exit")
                self.emit("mov rcx, [rsp]", "pass self to __exit__")
                self.emit("test rcx, rcx")
                self.emit(f"jz {lbl_skip_exit}")
                self.emit("xor edx, edx", "exc_type = None")
                self.emit("xor r8d, r8d", "exc_val = None")
                self.emit("xor r9d, r9d", "exc_tb = None")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(ctx_cls, '__exit__', exit_m)}")
                self.emit("add rsp, 32")
                self.emit_raw(f"{lbl_skip_exit}:")

            self.emit("add rsp, 16", "release with context slot")
            return

        # Default Win32 / file handle context manager (e.g. with open(...) as f:)
        self._generate_expr(item.context_expr)
        opt_var = item.optional_vars if isinstance(item.optional_vars, ast.Name) else None
        handle_offset = None
        if opt_var and self.current_func:
            var = self.current_func.local_vars.get(opt_var.id)
            if var:
                handle_offset = var.stack_offset
                self.emit(f"mov [rbp - {handle_offset}], rax", f"assign {var.name}")
        if handle_offset is None and item.optional_vars is not None:
            self._assign_target(item.optional_vars, "rax")
        if handle_offset is None:
            self.emit("sub rsp, 16", "aligned slot for anonymous with handle")
            self.emit("mov [rsp], rax", "save anonymous with handle")

        self._emit_with_items(rest, body)

        if handle_offset is not None:
            self.emit(f"mov rcx, [rbp - {handle_offset}]", "handle to close")
        else:
            self.emit("mov rcx, [rsp]", "restore anonymous with handle")
            self.emit("add rsp, 16", "release anonymous with handle slot")

        lbl_skip_close = self.new_label("skip_close")
        self.emit("test rcx, rcx")
        self.emit(f"jz {lbl_skip_close}")
        self.emit("cmp rcx, -1")
        self.emit(f"je {lbl_skip_close}")
        self.emit("call _pyfasm_file_close")
        self.emit_raw(f"{lbl_skip_close}:")

    def _assign_target(self, target_node: ast.AST, value_reg: str = "rax") -> None:
        if isinstance(target_node, ast.Name):
            var = self.current_func.local_vars.get(target_node.id) if self.current_func else None
            if var:
                self.emit(f"mov [rbp - {var.stack_offset}], {value_reg}", f"assign {var.name}")
            elif target_node.id in self.module.global_vars:
                self.emit(f"mov [{safe_global_label(target_node.id)}], {value_reg}", f"assign global {target_node.id}")
        elif isinstance(target_node, (ast.Tuple, ast.List)):
            if value_reg != "r10":
                self.emit(f"mov r10, {value_reg}", "container item to unpack")
            for idx, elt in enumerate(target_node.elts):
                if isinstance(elt, ast.Name):
                    if elt.id == "_":
                        continue
                    e_var = self.current_func.local_vars.get(elt.id) if self.current_func else None
                    if e_var:
                        self.emit(f"mov rax, [r10 + {idx * 8 + 8}]", f"unpack {elt.id}")
                        self.emit(f"mov [rbp - {e_var.stack_offset}], rax")
                    elif elt.id in self.module.global_vars:
                        self.emit(f"mov rax, [r10 + {idx * 8 + 8}]", f"unpack global {elt.id}")
                        self.emit(f"mov [{safe_global_label(elt.id)}], rax")
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

        iter_cls = self.resolve_instance_class(stmt.iter)
        if iter_cls:
            iter_m = self.resolve_class_method(iter_cls, "__iter__")
            eff_iter_cls = iter_cls
            if iter_m and iter_m in self.module.functions:
                it_rt = self.module.functions[iter_m].return_type
                if isinstance(it_rt, InstanceType):
                    eff_iter_cls = it_rt.class_name
            next_m = self.resolve_class_method(eff_iter_cls, "__next__")
            if next_m:
                if iter_m:
                    self.emit("mov rcx, rax", "pass self to __iter__")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {self._method_call_target(iter_cls, '__iter__', iter_m)}")
                    self.emit("add rsp, 32")
                    self.emit("test rax, rax", "check null iterator")
                    self.emit(f"jz {lbl_normal if stmt.orelse else lbl_null}")

                if buf_var:
                    self.emit(f"mov [rbp - {buf_var.stack_offset}], rax", "save custom iter_ptr")
                else:
                    self.emit("sub rsp, 16", "aligned slot for custom iter_ptr")
                    self.emit("mov [rsp], rax", "save custom iter_ptr")

                if isinstance(stmt.target, ast.Name) and next_m in self.module.functions:
                    nt = self.module.functions[next_m].return_type
                    if isinstance(nt, InstanceType):
                        self.local_var_classes[stmt.target.id] = nt.class_name

                self.loop_stack.append((lbl_step, lbl_break))
                self.emit_raw(f"{lbl_start}:")
                if buf_var:
                    self.emit(f"mov rcx, [rbp - {buf_var.stack_offset}]", "custom iter_ptr")
                else:
                    self.emit("mov rcx, [rsp]", "custom iter_ptr")
                self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration flag")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(eff_iter_cls, '__next__', next_m)}")
                self.emit("add rsp, 32")
                self.emit("cmp qword [_pyfasm_stop_iter], 0", "check StopIteration")
                self.emit(f"jne {lbl_normal}")
                self._assign_target(stmt.target, "rax")

                for s in stmt.body:
                    self._generate_statement(s)

                self.emit_raw(f"{lbl_step}:")
                self.emit(f"jmp {lbl_start}")

                if stmt.orelse:
                    self.emit_raw(f"{lbl_normal}:")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration")
                    if not buf_var:
                        self.emit("add rsp, 16", "cleanup custom iter_ptr")
                    for s in stmt.orelse:
                        self._generate_statement(s)
                    self.emit(f"jmp {lbl_end}")
                    self.emit_raw(f"{lbl_break}:")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration")
                    if not buf_var:
                        self.emit("add rsp, 16", "cleanup custom iter_ptr")
                    self.emit_raw(f"{lbl_end}:")
                else:
                    self.emit_raw(f"{lbl_end}:")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration")
                    if not buf_var:
                        self.emit("add rsp, 16", "cleanup custom iter_ptr")

                self.loop_stack.pop()
                self.emit_raw(f"{lbl_null}:")
                return

        iter_t = self._infer_expr_type(stmt.iter)
        if isinstance(stmt.target, ast.Name):
            elt_t = None
            if iter_t.is_list() or iter_t.is_tuple() or iter_t.is_set():
                elt_t = getattr(iter_t, "element_type", None)
            elif iter_t.is_dict():
                elt_t = getattr(iter_t, "key_type", None)
            if isinstance(elt_t, InstanceType):
                self.local_var_classes[stmt.target.id] = elt_t.class_name
        if iter_t.is_str() and self.target in ("win64", "dll"):
            if buf_var and idx_var:
                self.emit(f"mov [rbp - {buf_var.stack_offset}], rax", "str ptr to stack slot")
                self.emit(f"mov qword [rbp - {idx_var.stack_offset}], 0", "utf8 byte offset = 0")
            else:
                self.emit("push rax", "str ptr")
                self.emit("push 0", "utf8 byte offset = 0")

            self.loop_stack.append((lbl_step, lbl_break))
            self.emit_raw(f"{lbl_start}:")
            if buf_var and idx_var:
                self.emit(f"mov rcx, [rbp - {buf_var.stack_offset}]", "str ptr")
                self.emit(f"mov rdx, [rbp - {idx_var.stack_offset}]", "byte offset")
            else:
                self.emit("mov rdx, [rsp]", "byte offset")
                self.emit("mov rcx, [rsp + 8]", "str ptr")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_utf8_next_char")
            self.emit("add rsp, 32")
            self.emit("test rax, rax")
            self.emit(f"jz {lbl_normal}")
            if buf_var and idx_var:
                self.emit(f"mov [rbp - {idx_var.stack_offset}], rdx", "advance utf8 offset")
            else:
                self.emit("mov [rsp], rdx", "advance utf8 offset")
            self._assign_target(stmt.target, "rax")

            for s in stmt.body:
                self._generate_statement(s)

            self.emit_raw(f"{lbl_step}:")
            self.emit(f"jmp {lbl_start}")

            if stmt.orelse:
                self.emit_raw(f"{lbl_normal}:")
                if not (buf_var and idx_var):
                    self.emit("add rsp, 16", "cleanup str & offset from stack")
                for s in stmt.orelse:
                    self._generate_statement(s)
                self.emit(f"jmp {lbl_end}")
                self.emit_raw(f"{lbl_break}:")
                if not (buf_var and idx_var):
                    self.emit("add rsp, 16", "cleanup str & offset from stack")
                self.emit_raw(f"{lbl_end}:")
            else:
                self.emit_raw(f"{lbl_end}:")
                if not (buf_var and idx_var):
                    self.emit("add rsp, 16", "cleanup str & offset from stack")

            self.loop_stack.pop()
            self.emit_raw(f"{lbl_null}:")
            return

        is_hash_table = False
        if isinstance(stmt.iter, ast.Name) and self.current_func:
            var_sym = self.current_func.local_vars.get(stmt.iter.id)
            if var_sym and (var_sym.var_type.is_set() or var_sym.var_type.is_dict()):
                is_hash_table = True
        if not is_hash_table and (iter_t.is_set() or iter_t.is_dict()):
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

    def _merge_expr_element_types(self, types: List[Optional[PyFasmType]]) -> Optional[PyFasmType]:
        """Return common element type across elements or None if heterogeneous."""
        concrete = [t for t in types if t is not None]
        if not concrete:
            return None
        first = concrete[0]
        if all(t == first for t in concrete):
            return first
        if all(isinstance(t, InstanceType) for t in concrete):
            def _ancestors(cname: str) -> List[str]:
                res: List[str] = []
                q = [cname]
                while q:
                    cur = q.pop(0)
                    if cur not in res:
                        res.append(cur)
                        cs = self.module.classes.get(cur)
                        if cs:
                            q.extend(cs.bases)
                return res

            base_ancestors = _ancestors(concrete[0].class_name)
            other_sets = [set(_ancestors(t.class_name)) for t in concrete[1:]]
            for anc in base_ancestors:
                if all(anc in s for s in other_sets):
                    return InstanceType(class_name=anc)
            return None
        if all(t.is_list() for t in concrete):
            inner = [getattr(t, "element_type", None) for t in concrete if getattr(t, "element_type", None) is not None]
            if inner:
                merged_inner = self._merge_expr_element_types(inner)
                if merged_inner is not None:
                    return ListType(element_type=merged_inner)
            return TYPE_LIST
        if all(t.is_dict() for t in concrete):
            return TYPE_DICT
        if all(t.is_set() for t in concrete):
            return TYPE_SET
        if all(t.is_tuple() for t in concrete):
            return TYPE_TUPLE
        return None

    def _infer_expr_type(self, expr: Optional[ast.AST]) -> PyFasmType:
        if expr is None:
            return TYPE_INT
        if hasattr(ast, "Index") and isinstance(expr, ast.Index):
            return self._infer_expr_type(expr.value)
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
            gvt = getattr(self.module, "global_var_types", None)
            if gvt and expr.id in gvt:
                return gvt[expr.id]
            if expr.id in ("__name__", "__doc__", "__file__", "__package__"):
                return TYPE_STR
            if any(k in expr.id.lower() for k in ("name", "text", "str", "url", "path", "title", "msg", "message", "prompt", "line", "word", "tag", "sep", "prefix", "suffix", "ext", "key", "hdr", "phrase")):
                return TYPE_STR
            if any(k in expr.id.lower() for k in ("dict", "map", "table", "cache", "lookup", "modules", "headers", "params", "environ", "registry", "vars")):
                return TYPE_DICT
        if isinstance(expr, ast.List):
            elem_t = self._merge_expr_element_types([self._infer_expr_type(e) for e in expr.elts]) if expr.elts else None
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST
        if isinstance(expr, ast.ListComp):
            elem_t = self._infer_expr_type(expr.elt)
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST
        if isinstance(expr, ast.IfExp):
            return self._infer_expr_type(expr.body)
        if isinstance(expr, ast.NamedExpr):
            return self._infer_expr_type(expr.value)
        if isinstance(expr, ast.BoolOp):
            if expr.values:
                return self._infer_expr_type(expr.values[-1])
            return TYPE_BOOL
        if isinstance(expr, ast.Dict):
            kt = self._merge_expr_element_types([self._infer_expr_type(k) for k in expr.keys if k is not None])
            vt = self._merge_expr_element_types([self._infer_expr_type(v) for v in expr.values])
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT
        if isinstance(expr, ast.DictComp):
            kt = self._infer_expr_type(expr.key)
            vt = self._infer_expr_type(expr.value)
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT
        if isinstance(expr, ast.Set):
            elem_t = self._merge_expr_element_types([self._infer_expr_type(e) for e in expr.elts]) if expr.elts else None
            return SetType(element_type=elem_t) if elem_t else TYPE_SET
        if isinstance(expr, ast.SetComp):
            elem_t = self._infer_expr_type(expr.elt)
            return SetType(element_type=elem_t) if elem_t else TYPE_SET
        if isinstance(expr, ast.Tuple):
            if not expr.elts:
                return TYPE_TUPLE
            elt_ts = tuple(self._infer_expr_type(e) for e in expr.elts)
            elem_t = self._merge_expr_element_types(list(elt_ts))
            return TupleType(element_type=elem_t, element_types=elt_ts)
        if isinstance(expr, ast.Subscript):
            val_type = self._infer_expr_type(expr.value)
            sub_slice = expr.slice.value if (hasattr(ast, "Index") and isinstance(expr.slice, ast.Index)) else expr.slice
            if val_type.is_str():
                return TYPE_STR
            if isinstance(sub_slice, ast.Slice):
                return val_type
            if val_type.is_list():
                if hasattr(val_type, "element_type") and val_type.element_type:
                    return val_type.element_type
                return TYPE_INT
            if val_type.is_tuple():
                if (
                    isinstance(sub_slice, ast.Constant)
                    and isinstance(sub_slice.value, int)
                    and getattr(val_type, "element_types", None)
                ):
                    idx = sub_slice.value
                    ets = val_type.element_types
                    if -len(ets) <= idx < len(ets):
                        return ets[idx]
                if getattr(val_type, "element_type", None):
                    return val_type.element_type
                return TYPE_INT
            if val_type.is_dict() and hasattr(val_type, "val_type") and val_type.val_type:
                return val_type.val_type
            if isinstance(expr.value, ast.Name):
                vname = expr.value.id.lower()
                if any(k in vname for k in ("words", "tags", "names", "lines", "strs", "strings", "titles")):
                    return TYPE_STR
                if any(k in vname for k in ("matrix", "mat", "grid", "board", "table", "rows", "cols")) or expr.value.id in ("A", "B", "C", "D", "M"):
                    return ListType(element_type=TYPE_INT)
            return TYPE_INT
        if isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.MatMult):
                return ListType(element_type=TYPE_LIST)
            binop_dunders = {
                ast.Add: "__add__", ast.Sub: "__sub__", ast.Mult: "__mul__",
                ast.FloorDiv: "__floordiv__", ast.Div: "__truediv__", ast.Mod: "__mod__",
                ast.Pow: "__pow__", ast.BitAnd: "__and__", ast.BitOr: "__or__",
                ast.BitXor: "__xor__", ast.LShift: "__lshift__", ast.RShift: "__rshift__",
            }
            if type(expr.op) in binop_dunders:
                lcls = self.resolve_instance_class(expr.left)
                if lcls:
                    op_m = self.resolve_class_method(lcls, binop_dunders[type(expr.op)])
                    if op_m and op_m in self.module.functions and self.module.functions[op_m].return_type != TYPE_VOID:
                        return self.module.functions[op_m].return_type
            lt = self._infer_expr_type(expr.left)
            rt = self._infer_expr_type(expr.right)
            if isinstance(expr.op, ast.Mult) and (lt.is_list() or rt.is_list() or isinstance(expr.left, (ast.List, ast.Tuple)) or isinstance(expr.right, (ast.List, ast.Tuple))):
                return lt if (lt.is_list() or lt.is_tuple() or isinstance(expr.left, (ast.List, ast.Tuple))) else rt
            if isinstance(expr.op, ast.Add) and (lt.is_list() or rt.is_list() or isinstance(expr.left, (ast.List, ast.Tuple)) or isinstance(expr.right, (ast.List, ast.Tuple))):
                return lt if (lt.is_list() or lt.is_tuple() or isinstance(expr.left, (ast.List, ast.Tuple))) else rt
            if lt.is_str() or rt.is_str():
                return TYPE_STR
            if lt.is_float() or rt.is_float():
                return TYPE_FLOAT
        if isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.Not):
                return TYPE_BOOL
            u_map = {ast.USub: "__neg__", ast.UAdd: "__pos__", ast.Invert: "__invert__"}
            if type(expr.op) in u_map:
                ocls = self.resolve_instance_class(expr.operand)
                if ocls:
                    um = self.resolve_class_method(ocls, u_map[type(expr.op)])
                    if um and um in self.module.functions and self.module.functions[um].return_type != TYPE_VOID:
                        return self.module.functions[um].return_type
            if isinstance(expr.op, (ast.USub, ast.UAdd)):
                ot = self._infer_expr_type(expr.operand)
                if ot.is_float():
                    return TYPE_FLOAT
        if isinstance(expr, ast.JoinedStr):
            return TYPE_STR
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                fn_id = expr.func.id
                if fn_id in ("str", "repr", "chr", "input", "strip", "lower", "upper", "hex", "bin", "oct", "get_simd_isa"):
                    return TYPE_STR
                if fn_id in ("float",):
                    return TYPE_FLOAT
                if fn_id in ("bool", "isinstance", "issubclass", "any", "all", "isdigit", "isascii"):
                    return TYPE_BOOL
                if fn_id in self.module.classes:
                    return InstanceType(class_name=fn_id)
                if getattr(self.current_func, "is_classmethod", False) and self.current_func and self.current_func.args:
                    if fn_id == self.current_func.args[0].name and self.current_func.class_name:
                        return InstanceType(class_name=self.current_func.class_name)
                if fn_id == "next" and expr.args:
                    it_cls = self.resolve_instance_class(expr.args[0])
                    if it_cls:
                        nm = self.resolve_class_method(it_cls, "__next__")
                        if nm and nm in self.module.functions and self.module.functions[nm].return_type != TYPE_VOID:
                            return self.module.functions[nm].return_type
                inst_cls = self.resolve_instance_class(expr.func)
                if inst_cls:
                    cm = self.resolve_class_method(inst_cls, "__call__")
                    if cm and cm in self.module.functions and self.module.functions[cm].return_type != TYPE_VOID:
                        return self.module.functions[cm].return_type
                if fn_id == "range":
                    return ListType(element_type=TYPE_INT)
                if fn_id in ("list", "sorted", "reversed"):
                    if expr.args:
                        a0 = expr.args[0]
                        a0_t = self._infer_expr_type(a0)
                        if a0_t.is_str():
                            return ListType(element_type=TYPE_STR)
                        if a0_t.is_list() or a0_t.is_set():
                            inner = getattr(a0_t, "element_type", None)
                            if inner is not None:
                                return ListType(element_type=inner)
                        elif a0_t.is_tuple():
                            inner = getattr(a0_t, "element_type", None)
                            if inner is None and getattr(a0_t, "element_types", None):
                                inner = self._merge_expr_element_types(list(a0_t.element_types))
                            if inner is not None:
                                return ListType(element_type=inner)
                        elif a0_t.is_dict():
                            kt = getattr(a0_t, "key_type", None)
                            if kt is not None:
                                return ListType(element_type=kt)
                        elif isinstance(a0, ast.Call) and isinstance(a0.func, ast.Name) and a0.func.id == "range":
                            return ListType(element_type=TYPE_INT)
                    return TYPE_LIST
                if fn_id == "map" and len(expr.args) >= 2 and isinstance(expr.args[0], ast.Name):
                    m_fn = expr.args[0].id
                    if m_fn == "str":
                        return ListType(element_type=TYPE_STR)
                    if m_fn == "float":
                        return ListType(element_type=TYPE_FLOAT)
                    if m_fn == "int":
                        return ListType(element_type=TYPE_INT)
                    if m_fn == "bool":
                        return ListType(element_type=TYPE_BOOL)
                    if m_fn in self.module.functions and self.module.functions[m_fn].return_type != TYPE_VOID:
                        return ListType(element_type=self.module.functions[m_fn].return_type)
                    return TYPE_LIST
                if fn_id in ("filter", "zip", "enumerate", "chain", "accumulate", "matmul", "zeros", "ones", "array", "asarray", "arange", "pairwise"):
                    if fn_id in ("matmul",):
                        return ListType(element_type=TYPE_LIST)
                    return TYPE_LIST
                if fn_id in ("dict",):
                    return TYPE_DICT
                if fn_id in ("set",):
                    if expr.args:
                        a0_t = self._infer_expr_type(expr.args[0])
                        if a0_t.is_str():
                            return SetType(element_type=TYPE_STR)
                        if (a0_t.is_list() or a0_t.is_set() or a0_t.is_tuple()) and getattr(a0_t, "element_type", None):
                            return SetType(element_type=a0_t.element_type)
                    return TYPE_SET
                if fn_id in ("tuple",):
                    if expr.args:
                        a0_t = self._infer_expr_type(expr.args[0])
                        if a0_t.is_str():
                            return TupleType(element_type=TYPE_STR)
                        if a0_t.is_list() or a0_t.is_set() or a0_t.is_tuple():
                            return TupleType(
                                element_type=getattr(a0_t, "element_type", None),
                                element_types=getattr(a0_t, "element_types", None),
                            )
                    return TYPE_TUPLE
                if fn_id in self.module.functions:
                    return self.module.functions[fn_id].return_type
            elif isinstance(expr.func, ast.Attribute):
                attr = expr.func.attr
                if attr in ("split", "splitlines"):
                    return ListType(element_type=TYPE_STR)
                if attr in ("matmul", "zeros", "ones", "array", "asarray", "arange", "pairwise", "findall"):
                    if attr in ("matmul",):
                        return ListType(element_type=TYPE_LIST)
                    return TYPE_LIST
                if attr == "keys":
                    recv_t = self._infer_expr_type(expr.func.value)
                    kt = getattr(recv_t, "key_type", None) if recv_t.is_dict() else None
                    return ListType(element_type=kt) if kt else TYPE_LIST
                if attr == "values":
                    recv_t = self._infer_expr_type(expr.func.value)
                    vt = getattr(recv_t, "val_type", None) if recv_t.is_dict() else None
                    return ListType(element_type=vt) if vt else TYPE_LIST
                if attr == "items":
                    recv_t = self._infer_expr_type(expr.func.value)
                    if recv_t.is_dict():
                        kt = getattr(recv_t, "key_type", None) or TYPE_INT
                        vt = getattr(recv_t, "val_type", None) or TYPE_INT
                        return ListType(element_type=TupleType(element_types=(kt, vt)))
                    return TYPE_LIST
                if attr == "copy":
                    recv_t = self._infer_expr_type(expr.func.value)
                    if recv_t.is_list() or recv_t.is_dict() or recv_t.is_set():
                        return recv_t
                if attr in ("isdigit", "isascii"):
                    return TYPE_BOOL
                if attr in ("bit_length", "count", "find", "index"):
                    return TYPE_INT
                if attr in ("get_simd_isa",):
                    return TYPE_STR
                if attr == "loads":
                    if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "json":
                        return TYPE_DICT
                if attr in ("get", "pop"):
                    obj_type = self._infer_expr_type(expr.func.value)
                    if attr == "pop" and obj_type.is_list() and getattr(obj_type, "element_type", None):
                        return obj_type.element_type
                    if obj_type.is_dict() and getattr(obj_type, "val_type", None):
                        return obj_type.val_type
                    if len(expr.args) >= 2:
                        return self._infer_expr_type(expr.args[1])
                    return TYPE_INT
                if attr == "choice":
                    return TYPE_STR
                if attr in ("lower", "upper", "strip", "lstrip", "rstrip", "title", "capitalize", "replace", "format", "join", "removeprefix", "removesuffix"):
                    return TYPE_STR
                if attr in ("chain", "accumulate"):
                    return TYPE_LIST
                if isinstance(expr.func.value, ast.Name) and expr.func.value.id in self.module.classes:
                    c_name = expr.func.value.id
                    m = self.resolve_class_method(c_name, attr)
                    if m and m in self.module.functions:
                        fn_sym = self.module.functions[m]
                        if getattr(fn_sym, "is_classmethod", False) and (
                            isinstance(fn_sym.return_type, InstanceType) or fn_sym.return_type == TYPE_VOID
                        ):
                            return InstanceType(class_name=c_name)
                        if fn_sym.return_type != TYPE_VOID:
                            return fn_sym.return_type
                recv_cls = self.resolve_instance_class(expr.func.value)
                if not recv_cls and isinstance(expr.func.value, ast.Name) and expr.func.value.id == "cls":
                    if getattr(self.current_func, "is_classmethod", False):
                        recv_cls = self.current_func.class_name
                if recv_cls:
                    m = self.resolve_class_method(recv_cls, attr)
                    if m and m in self.module.functions and self.module.functions[m].return_type != TYPE_VOID:
                        return self.module.functions[m].return_type
                if isinstance(expr.func.value, ast.Name):
                    pfx = expr.func.value.id
                    pref = f"{pfx}_{attr}"
                    if pref in self.module.functions and self.module.functions[pref].return_type != TYPE_VOID:
                        return self.module.functions[pref].return_type
                for cls in self.module.classes.values():
                    m = self.resolve_class_method(cls.name, attr)
                    if m and m in self.module.functions:
                        return self.module.functions[m].return_type
        if isinstance(expr, ast.Attribute):
            prop = self.resolve_property_for_expr(expr.value, expr.attr)
            if prop and getattr(prop, "getter_name", None) and prop.getter_name in self.module.functions:
                return self.module.functions[prop.getter_name].return_type
            owner_cls = self.resolve_instance_class(expr.value)
            if not owner_cls and isinstance(expr.value, ast.Name) and expr.value.id in self.module.classes:
                owner_cls = expr.value.id
            if not owner_cls:
                owner_cls = getattr(self.current_func, "class_name", None)
            if owner_cls:
                seen_f: Set[str] = set()
                fq = [owner_cls]
                while fq:
                    cn = fq.pop(0)
                    if cn in seen_f:
                        continue
                    seen_f.add(cn)
                    cs = self.module.classes.get(cn)
                    if cs:
                        if hasattr(cs, "field_types") and expr.attr in cs.field_types:
                            return cs.field_types[expr.attr]
                        fq.extend(cs.bases)
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
                target_bits = struct.pack("<d", expr.value)
                for flit in self.module.float_literals:
                    if struct.pack("<d", flit.value) == target_bits:
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
                self.emit(f"mov rax, [{safe_global_label(expr.id)}]", f"load global {expr.id}")
            elif expr.id in self.module.functions:
                safe_fn = safe_asm_label(expr.id)
                self.emit(f"lea rax, [{safe_fn}]", f"address of {expr.id}")
            else:
                self._record_unresolved(expr.id, expr)
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
                    if getattr(self.current_func, "is_classmethod", False) and self.current_func and self.current_func.args:
                        if node.id == self.current_func.args[0].name:
                            return True
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
                    cls_lookup = mod_name
                    if getattr(self.current_func, "is_classmethod", False) and self.current_func and self.current_func.args:
                        if mod_name == self.current_func.args[0].name and self.current_func.class_name:
                            cls_lookup = self.current_func.class_name
                    if cls_lookup in self.module.classes:
                        seen_c: Set[str] = set()
                        cq = [cls_lookup]
                        while cq and not val_handled:
                            curr_c = cq.pop(0)
                            if curr_c in seen_c:
                                continue
                            seen_c.add(curr_c)
                            cls_sym = self.module.classes.get(curr_c)
                            if not cls_sym:
                                continue
                            if hasattr(cls_sym, "class_attrs") and expr.attr in cls_sym.class_attrs:
                                c_val = cls_sym.class_attrs[expr.attr]
                                if isinstance(c_val, bool):
                                    self.emit(f"mov rax, {1 if c_val else 0}", f"load class attribute {curr_c}.{expr.attr}")
                                    val_handled = True
                                elif isinstance(c_val, int):
                                    self.emit(f"mov rax, {c_val}", f"load class attribute {curr_c}.{expr.attr}")
                                    val_handled = True
                                elif isinstance(c_val, str):
                                    self._emit_string_pointer("rax", c_val)
                                    val_handled = True
                            if not val_handled:
                                for b in cls_sym.bases:
                                    if b not in seen_c:
                                        cq.append(b)
                        if not val_handled:
                            cq2 = [cls_lookup]
                            seen_c2: Set[str] = set()
                            while cq2:
                                curr_c = cq2.pop(0)
                                if curr_c in seen_c2:
                                    continue
                                seen_c2.add(curr_c)
                                cand_g = f"{curr_c}_{expr.attr}"
                                if cand_g in self.module.global_vars:
                                    self.emit(f"mov rax, [{safe_global_label(cand_g)}]", f"load class global {cand_g}")
                                    val_handled = True
                                    break
                                cs2 = self.module.classes.get(curr_c)
                                if cs2:
                                    cq2.extend(cs2.bases)
                    if not val_handled:
                        if expr.attr in ("modules", "environ", "argv", "path"):
                            namespaced_global = f"{mod_name}_{expr.attr}"
                            if namespaced_global not in self.module.global_vars:
                                self.module.global_vars[namespaced_global] = 0
                            lbl_has_obj = self.new_label("has_mod_obj")
                            self.emit(f"mov rax, [{safe_global_label(namespaced_global)}]")
                            self.emit("test rax, rax")
                            self.emit(f"jnz {lbl_has_obj}")
                            if expr.attr in ("modules", "environ"):
                                self.emit("mov ecx, 64")
                                self.emit("call _pyfasm_dict_create")
                            else:
                                self.emit("mov ecx, 16")
                                self.emit("call _pyfasm_list_create")
                            self.emit(f"mov [{safe_global_label(namespaced_global)}], rax")
                            self.emit_raw(f"{lbl_has_obj}:")
                            val_handled = True
                    if not val_handled:
                        namespaced_global = f"{mod_name}_{expr.attr}"
                        if namespaced_global in self.module.global_vars:
                            self.emit(f"mov rax, [{safe_global_label(namespaced_global)}]", f"load module global {mod_name}.{expr.attr}")
                            val_handled = True
                        elif expr.attr in self.module.global_vars:
                            self.emit(f"mov rax, [{safe_global_label(expr.attr)}]", f"load global {expr.attr}")
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
                        elif mod_name == "math" and expr.attr in ("gcd", "lcm", "isqrt", "factorial", "sin", "cos", "sqrt"):
                            self.emit(f"lea rax, [_pyfasm_math_{expr.attr}]", f"address of math.{expr.attr}")
                            val_handled = True
                        elif expr.attr in ("gcd", "lcm", "isqrt", "factorial"):
                            self.emit(f"lea rax, [_pyfasm_math_{expr.attr}]", f"address of {expr.attr}")
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
                curr_cls = self.resolve_instance_class(expr.value) or getattr(self.current_func, "class_name", None)
                fallback_global = None
                if curr_cls:
                    seen_fg: Set[str] = set()
                    fq = [curr_cls]
                    while fq:
                        fc = fq.pop(0)
                        if fc in seen_fg:
                            continue
                        seen_fg.add(fc)
                        cand_fg = f"{fc}_{expr.attr}"
                        if cand_fg in self.module.global_vars:
                            fallback_global = cand_fg
                            break
                        fcs = self.module.classes.get(fc)
                        if fcs:
                            fq.extend(fcs.bases)
                self.emit("test r8, r8", "check null pointer")
                self.emit(f"jz {lbl_null}")
                self.emit(f"mov rax, [r8 + {offset}]", f"load obj.{expr.attr}")
                if fallback_global:
                    self.emit("test rax, rax", "check if instance field is set")
                    lbl_has_inst = self.new_label("has_inst")
                    self.emit(f"jnz {lbl_has_inst}")
                    self.emit(f"mov rax, [{safe_global_label(fallback_global)}]", f"fallback to class attribute {fallback_global}")
                    self.emit_raw(f"{lbl_has_inst}:")
                self.emit(f"jmp {lbl_done}")
                self.emit_raw(f"{lbl_null}:")
                if fallback_global:
                    self.emit(f"mov rax, [{safe_global_label(fallback_global)}]", f"fallback to class attribute {fallback_global}")
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
                    self.emit(f"call {self._method_call_target(cls_name, dunder_name, op_m)}")
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

            lt = self._infer_expr_type(expr.left)
            rt = self._infer_expr_type(expr.right)

            is_str_add = False
            if isinstance(expr.op, ast.Add):
                if (
                    lt.is_str()
                    or rt.is_str()
                    or isinstance(expr.left, ast.JoinedStr)
                    or isinstance(expr.right, ast.JoinedStr)
                    or (isinstance(expr.left, ast.Constant) and isinstance(expr.left.value, str))
                    or (isinstance(expr.right, ast.Constant) and isinstance(expr.right.value, str))
                ):
                    is_str_add = True

            if is_str_add:
                self._generate_expr(expr.left)
                self.emit("sub rsp, 16", "spill str1 (16-byte aligned)")
                self.emit("mov [rsp], rax")
                self._generate_expr(expr.right)
                self.emit("mov rdx, rax", "str2")
                self.emit("mov rcx, [rsp]", "str1")
                self.emit("add rsp, 16")
                self.emit("sub rsp, 32", "shadow space for _pyfasm_str_concat")
                self.emit("call _pyfasm_str_concat")
                self.emit("add rsp, 32")
                return

            # List repetition (Mult) or concatenation (Add)
            is_left_list = lt.is_list() or lt.is_tuple() or isinstance(expr.left, (ast.List, ast.Tuple))
            is_right_list = rt.is_list() or rt.is_tuple() or isinstance(expr.right, (ast.List, ast.Tuple))
            if isinstance(expr.op, ast.Mult) and (is_left_list or is_right_list):
                if is_left_list:
                    self._generate_expr(expr.left)
                    self.emit("push rax", "list_ptr")
                    self._generate_expr(expr.right)
                    self.emit("mov rdx, rax", "count")
                    self.emit("pop rcx", "list_ptr")
                else:
                    self._generate_expr(expr.right)
                    self.emit("push rax", "list_ptr")
                    self._generate_expr(expr.left)
                    self.emit("mov rdx, rax", "count")
                    self.emit("pop rcx", "list_ptr")
                self.emit("call _pyfasm_list_repeat")
                return

            if isinstance(expr.op, ast.Add) and (is_left_list or is_right_list):
                self._generate_expr(expr.left)
                self.emit("push rax", "list1")
                self._generate_expr(expr.right)
                self.emit("mov rdx, rax", "list2")
                self.emit("pop rcx", "list1")
                self.emit("call _pyfasm_list_concat")
                return
            if (lt.is_float() or rt.is_float()) and isinstance(expr.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Pow)):
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
                elif isinstance(expr.op, ast.Pow):
                    lbl_pow_sqrt = self.new_label("pow_sqrt")
                    lbl_pow_end = self.new_label("pow_end")
                    lbl_pow_neg = self.new_label("pow_neg")
                    lbl_pow_pos = self.new_label("pow_pos")
                    lbl_pow_neg_loop = self.new_label("pow_neg_loop")
                    # Check if exponent == 0.5 (0x3FE0000000000000)
                    self.emit("mov r10, 0x3FE0000000000000")
                    self.emit("cmp r11, r10")
                    self.emit(f"je {lbl_pow_sqrt}")
                    # General integer power on float base:
                    self.emit("cvttsd2si rcx, xmm1")
                    self.emit("movq xmm2, xmm0", "base")
                    self.emit("mov rax, 0x3FF0000000000000", "1.0")
                    self.emit("movq xmm0, rax")
                    self.emit("test rcx, rcx")
                    self.emit(f"js {lbl_pow_neg}")
                    self.emit_raw(f"{lbl_pow_pos}:")
                    self.emit("test rcx, rcx")
                    self.emit(f"jz {lbl_pow_end}")
                    self.emit("mulsd xmm0, xmm2")
                    self.emit("dec rcx")
                    self.emit(f"jmp {lbl_pow_pos}")
                    self.emit_raw(f"{lbl_pow_neg}:")
                    self.emit("neg rcx")
                    self.emit_raw(f"{lbl_pow_neg_loop}:")
                    self.emit("test rcx, rcx")
                    self.emit(f"jz {lbl_pow_end}")
                    self.emit("divsd xmm0, xmm2")
                    self.emit("dec rcx")
                    self.emit(f"jmp {lbl_pow_neg_loop}")
                    self.emit_raw(f"{lbl_pow_sqrt}:")
                    self.emit("sqrtsd xmm0, xmm0")
                    self.emit_raw(f"{lbl_pow_end}:")
                self.emit("movq rax, xmm0")
                return

            self._generate_expr(expr.left)
            self.emit("push rax")
            self._generate_expr(expr.right)
            self.emit("mov r11, rax")
            self.emit("pop rax")
            self._generate_binop_instr(expr.op)

        elif isinstance(expr, ast.UnaryOp):
            u_dunders = {
                ast.USub: "__neg__",
                ast.UAdd: "__pos__",
                ast.Invert: "__invert__",
            }
            if type(expr.op) in u_dunders:
                d_name = u_dunders[type(expr.op)]
                ocls = self.resolve_instance_class(expr.operand)
                um = self.resolve_class_method(ocls, d_name) if ocls else None
                if um:
                    self._generate_expr(expr.operand)
                    self.emit("mov rcx, rax", f"pass self to {d_name}")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {self._method_call_target(ocls, d_name, um)}")
                    self.emit("add rsp, 32")
                    return
            if isinstance(expr.op, ast.Not):
                self._emit_to_bool(expr.operand, negate=True)
                return
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

        elif isinstance(expr, ast.BoolOp):
            lbl_end = self.new_label("boolop_end")
            if isinstance(expr.op, ast.And):
                for idx, val in enumerate(expr.values):
                    self._generate_expr(val)
                    if idx < len(expr.values) - 1:
                        is_seq = False
                        vt = self._infer_expr_type(val)
                        if vt.is_list() or vt.is_tuple() or vt.is_dict() or vt.is_set():
                            is_seq = True
                        elif isinstance(val, ast.Name) and self.current_func:
                            v = self.current_func.local_vars.get(val.id)
                            if v and (v.var_type.is_list() or v.var_type.is_tuple() or v.var_type.is_dict() or v.var_type.is_set()):
                                is_seq = True
                        self.emit("test rax, rax")
                        self.emit(f"jz {lbl_end}")
                        if is_seq:
                            lbl_cont = self.new_label("seq_nonempty")
                            self.emit("cmp qword [rax], 0", "check empty container")
                            self.emit(f"jnz {lbl_cont}")
                            self.emit("xor eax, eax")
                            self.emit(f"jmp {lbl_end}")
                            self.emit_raw(f"{lbl_cont}:")
            elif isinstance(expr.op, ast.Or):
                for idx, val in enumerate(expr.values):
                    self._generate_expr(val)
                    if idx < len(expr.values) - 1:
                        is_seq = False
                        vt = self._infer_expr_type(val)
                        if vt.is_list() or vt.is_tuple() or vt.is_dict() or vt.is_set():
                            is_seq = True
                        elif isinstance(val, ast.Name) and self.current_func:
                            v = self.current_func.local_vars.get(val.id)
                            if v and (v.var_type.is_list() or v.var_type.is_tuple() or v.var_type.is_dict() or v.var_type.is_set()):
                                is_seq = True
                        if is_seq:
                            lbl_next = self.new_label("boolop_next")
                            self.emit("test rax, rax")
                            self.emit(f"jz {lbl_next}")
                            self.emit("cmp qword [rax], 0", "check non-empty container")
                            self.emit(f"jnz {lbl_end}")
                            self.emit_raw(f"{lbl_next}:")
                        else:
                            self.emit("test rax, rax")
                            self.emit(f"jnz {lbl_end}")
            self.emit_raw(f"{lbl_end}:")

        elif isinstance(expr, ast.IfExp):
            lbl_else = self.new_label("ifexp_else")
            lbl_done = self.new_label("ifexp_done")
            self._generate_expr(expr.test)
            is_seq = False
            vt = self._infer_expr_type(expr.test)
            if vt.is_list() or vt.is_tuple() or vt.is_dict() or vt.is_set():
                is_seq = True
            elif isinstance(expr.test, ast.Name) and self.current_func:
                v = self.current_func.local_vars.get(expr.test.id)
                if v and (v.var_type.is_list() or v.var_type.is_tuple() or v.var_type.is_dict() or v.var_type.is_set()):
                    is_seq = True
            self.emit("test rax, rax")
            self.emit(f"jz {lbl_else}")
            if is_seq:
                self.emit("cmp qword [rax], 0", "check empty container")
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

                is_left_seq = lt.is_list() or lt.is_tuple() or isinstance(expr.left, (ast.List, ast.Tuple))
                is_right_seq = rt.is_list() or rt.is_tuple() or isinstance(expr.comparators[0], (ast.List, ast.Tuple))
                if (is_left_seq or is_right_seq) and isinstance(op, (ast.Eq, ast.NotEq)):
                    is_2d = False
                    if hasattr(lt, "element_type") and lt.element_type and (lt.element_type.is_list() or lt.element_type.is_tuple()):
                        is_2d = True
                    if hasattr(rt, "element_type") and rt.element_type and (rt.element_type.is_list() or rt.element_type.is_tuple()):
                        is_2d = True
                    if isinstance(expr.comparators[0], ast.List) and expr.comparators[0].elts and isinstance(expr.comparators[0].elts[0], (ast.List, ast.Tuple)):
                        is_2d = True
                    if isinstance(expr.left, ast.List) and expr.left.elts and isinstance(expr.left.elts[0], (ast.List, ast.Tuple)):
                        is_2d = True

                    self._generate_expr(expr.left)
                    self.emit("push rax")
                    self._generate_expr(expr.comparators[0])
                    self.emit("mov rdx, rax", "list2")
                    self.emit("pop rcx", "list1")
                    cmp_fn = "_pyfasm_list2d_eq" if is_2d else "_pyfasm_list_eq"
                    self.emit(f"call {cmp_fn}")
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
                self.emit(f"call {self._method_call_target(cls_name, '__getitem__', getitem_m)}")
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

                is_ptr_val = False
                if val_t == TYPE_PTR:
                    is_ptr_val = True
                elif isinstance(expr.value, ast.Name) and self.current_func:
                    v = self.current_func.local_vars.get(expr.value.id)
                    if v and (v.var_type == TYPE_PTR or any(k in v.name.lower() for k in ("mem", "ptr", "buffer"))):
                        is_ptr_val = True
                elif isinstance(expr.value, ast.Call) and isinstance(expr.value.func, ast.Name) and expr.value.func.id in ("alloc_memory", "malloc"):
                    is_ptr_val = True

                lbl_null_arr = self.new_label("null_arr")
                lbl_done_arr = self.new_label("done_arr")
                self.emit("test rax, rax", "check null array")
                self.emit(f"jz {lbl_null_arr}")
                self.emit("cmp rax, 65536", "check valid user-mode pointer")
                self.emit(f"jb {lbl_null_arr}")

                if is_str_val and self.target in ("win64", "dll"):
                    self.emit("mov rcx, rax", "utf8 string pointer")
                    self.emit("mov rdx, r11", "codepoint index")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_utf8_getitem")
                    self.emit("add rsp, 32")
                else:
                    if not is_str_val and not is_ptr_val:
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
                    elif is_ptr_val:
                        self.emit("mov rax, [rax + r11 * 8]", "load mem[idx]")
                    else:
                        self.emit("mov rax, [rax + (r11 + 1) * 8]", "load list[idx]")
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
            elif len(expr.values) == 1:
                self._generate_fstring_part(expr.values[0])
            else:
                self._generate_fstring_part(expr.values[0])
                self.emit("sub rsp, 16", "spill accumulated f-string (16-byte aligned)")
                self.emit("mov [rsp], rax", "save first part")
                for part in expr.values[1:]:
                    self._generate_fstring_part(part)
                    self.emit("mov rdx, rax", "next part")
                    self.emit("mov rcx, [rsp]", "accumulated string")
                    self.emit("sub rsp, 32", "shadow space for _pyfasm_str_concat")
                    self.emit("call _pyfasm_str_concat")
                    self.emit("add rsp, 32")
                    self.emit("mov [rsp], rax", "save combined")
                self.emit("mov rax, [rsp]", "final combined string")
                self.emit("add rsp, 16")

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
                self._assign_target(gen.target, "rax")

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
                self._assign_target(gen.target, "rax")

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

    def _generate_match(self, stmt: Any) -> None:
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

    def _generate_case_pattern_test(self, pattern: Any, lbl_success: str, lbl_failure: str) -> None:
        if isinstance(pattern, _AST_MATCH_VALUE):
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

        elif isinstance(pattern, _AST_MATCH_AS):
            if pattern.name is None or pattern.name == "_":
                self.emit(f"jmp {lbl_success}")
            else:
                self.emit("mov rax, [rsp]", "subject")
                if self.current_func:
                    var = self.current_func.local_vars.get(pattern.name)
                    if var:
                        self.emit(f"mov [rbp - {var.stack_offset}], rax", f"capture {pattern.name}")
                    elif hasattr(self.current_func, "global_names") and pattern.name in self.current_func.global_names:
                        self.emit(f"mov [{safe_global_label(pattern.name)}], rax", f"capture global {pattern.name}")
                self.emit(f"jmp {lbl_success}")

        elif isinstance(pattern, _AST_MATCH_OR):
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
        elif isinstance(op, ast.MatMult):
            self.emit("mov rcx, rax", "left matrix")
            self.emit("mov rdx, r11", "right matrix")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_nanogemm_matmul")
            self.emit("add rsp, 32")
        elif isinstance(op, (ast.FloorDiv, ast.Div)):
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
            self.emit("test rdx, rdx", "check remainder for Python floor rounding")
            self.emit(f"jz {lbl_div_end}")
            self.emit("mov r10, rdx")
            self.emit("xor r10, r11")
            self.emit(f"jns {lbl_div_end}")
            self.emit("dec rax", "floor toward -infinity")
            self.emit_raw(f"{lbl_div_end}:")
        elif isinstance(op, ast.Mod):
            lbl_mod_ok = self.new_label("mod_ok")
            lbl_mod_store = self.new_label("mod_store")
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
            self.emit("test rdx, rdx", "adjust remainder sign to match divisor")
            self.emit(f"jz {lbl_mod_store}")
            self.emit("mov r10, rdx")
            self.emit("xor r10, r11")
            self.emit(f"jns {lbl_mod_store}")
            self.emit("add rdx, r11")
            self.emit_raw(f"{lbl_mod_store}:")
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
        recv_cls_hint: Optional[str] = None

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
                if isinstance(call.func.value, ast.Call) and isinstance(call.func.value.func, ast.Name) and call.func.value.func.id == "__import__":
                    if call.func.value.args and isinstance(call.func.value.args[0], ast.Constant) and isinstance(call.func.value.args[0].value, str):
                        prefix = call.func.value.args[0].value
                        func_name = f"{prefix}_{attr_name}"
                elif isinstance(call.func.value, ast.Name):
                    prefix = call.func.value.id
                    if prefix in ("self", "this"):
                        current_cls = getattr(self.current_func, "class_name", None)
                        recv_cls_hint = current_cls
                        resolved = self.resolve_class_method(current_cls, attr_name, skip_cls=False)
                        if resolved:
                            func_name = resolved
                        elif current_cls and f"{current_cls}_{attr_name}" in self.module.functions:
                            func_name = f"{current_cls}_{attr_name}"
                        elif f"self_{attr_name}" in self.module.functions:
                            func_name = f"self_{attr_name}"
                        else:
                            func_name = f"{current_cls}_{attr_name}" if current_cls else f"self_{attr_name}"
                    elif getattr(self.current_func, "is_classmethod", False) and self.current_func and self.current_func.args and prefix == self.current_func.args[0].name:
                        recv_cls_hint = self.current_func.class_name
                        resolved = self.resolve_class_method(recv_cls_hint, attr_name, skip_cls=False)
                        if resolved:
                            func_name = resolved
                        else:
                            func_name = f"{recv_cls_hint}_{attr_name}" if recv_cls_hint else f"{prefix}_{attr_name}"
                    else:
                        if prefix in self.module.classes:
                            recv_cls_hint = prefix
                            resolved = self.resolve_class_method(prefix, attr_name, skip_cls=False)
                            if resolved:
                                func_name = resolved
                            elif attr_name in ("register", "__init_subclass__"):
                                self.emit("xor eax, eax", f"no-op {prefix}.{attr_name}")
                                return
                            else:
                                func_name = f"{prefix}_{attr_name}"
                        else:
                            prefix_cls = self.resolve_instance_class(call.func.value)
                            if prefix_cls:
                                recv_cls_hint = prefix_cls
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
                    expr_cls = self.resolve_instance_class(call.func.value)
                    if expr_cls:
                        recv_cls_hint = expr_cls
                        resolved = self.resolve_class_method(expr_cls, attr_name, skip_cls=False)
                        if resolved:
                            func_name = resolved
                    if not func_name:
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

        if func_name == "_pyfasm_closure_new" and call.args:
            n_caps = len(call.args) - 1
            size_bytes = (2 + n_caps) * 8
            self.emit(f"mov ecx, {size_bytes}", "allocate closure object")
            self.emit("call _pyfasm_alloc")
            self.emit("sub rsp, 16", "aligned slot for closure ptr")
            self.emit("mov [rsp], rax", "save closure ptr")
            self.emit("mov r10, 505946434C4F5355h", "PYFCLOSU tag")
            self.emit("mov [rax], r10")
            self._generate_expr(call.args[0])
            self.emit("mov r10, [rsp]", "restore closure ptr")
            self.emit("mov [r10 + 8], rax", "store closure fn ptr")
            for idx, cap_arg in enumerate(call.args[1:]):
                self._generate_expr(cap_arg)
                self.emit("mov r10, [rsp]", "restore closure ptr")
                self.emit(f"mov [r10 + {(idx + 2) * 8}], rax", f"store captured var {idx}")
            self.emit("mov rax, [rsp]", "return closure ptr")
            self.emit("add rsp, 16", "release closure slot")
            return

        if func_name == "_pyfasm_closure_get" and len(call.args) >= 2:
            cap_idx = call.args[1].value if isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, int) else 0
            self._generate_expr(call.args[0])
            self.emit(f"mov rax, [rax + {(cap_idx + 2) * 8}]", f"load closure capture {cap_idx}")
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

        if attr_name == "split" and isinstance(call.func, ast.Attribute) and self.target in ("win64", "dll"):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("push rax", "sep")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "target string")
                self.emit("pop rdx", "sep")
            else:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "target string")
                self.emit("xor edx, edx", "whitespace split")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_str_split")
            self.emit("add rsp, 32")
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

        # List / Dict pop
        if attr_name == "pop" and isinstance(call.func, ast.Attribute):
            var = self.current_func.local_vars.get(prefix) if (prefix and self.current_func) else None
            val_type = (
                var.var_type
                if (var and (var.var_type.is_list() or var.var_type.is_dict()))
                else self._infer_expr_type(call.func.value)
            )
            if val_type.is_list():
                if var:
                    self.emit(f"mov rcx, [rbp - {var.stack_offset}]", "list_ptr")
                else:
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "list_ptr")
                self.emit("call _pyfasm_list_pop")
                return
            if val_type.is_dict() and call.args:
                is_tuple_key = isinstance(call.args[0], ast.Tuple)
                if isinstance(call.args[0], ast.Name) and self.current_func:
                    kv = self.current_func.local_vars.get(call.args[0].id)
                    if kv and kv.var_type.is_tuple():
                        is_tuple_key = True
                self.emit("sub rsp, 32", "spill [dict_ptr, key, popped_val]")
                self._generate_expr(call.func.value)
                self.emit("mov [rsp], rax", "save dict_ptr")
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 8], rax", "save key")
                if len(call.args) >= 2:
                    self._generate_expr(call.args[1])
                    self.emit("mov r8, rax", "default val")
                else:
                    self.emit("xor r8d, r8d", "default val = 0")
                self.emit("mov rcx, [rsp]", "dict_ptr")
                self.emit("mov rdx, [rsp + 8]", "key")
                self.emit("sub rsp, 32", "shadow space")
                if is_tuple_key:
                    self.emit("call _pyfasm_dict_get_tuple")
                else:
                    self.emit("call _pyfasm_dict_get")
                self.emit("add rsp, 32")
                self.emit("mov [rsp + 16], rax", "save popped value")
                self.emit("mov rcx, [rsp]", "dict_ptr")
                self.emit("mov rdx, [rsp + 8]", "key")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_dict_remove")
                self.emit("add rsp, 32")
                self.emit("mov rax, [rsp + 16]", "return popped value")
                self.emit("add rsp, 32")
                return

        # List / Container __setitem__(idx, val)
        if attr_name == "__setitem__" and len(call.args) >= 2 and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[1])
            self.emit("push rax", "val")
            self._generate_expr(call.args[0])
            self.emit("push rax", "idx")
            self._generate_expr(call.func.value)
            self.emit("mov r8, rax", "container_ptr")
            self.emit("pop rdx", "idx")
            self.emit("pop rax", "val")
            self.emit("mov [r8 + rdx * 8 + 8], rax", "store list[idx] = val")
            self.emit("xor eax, eax", "return None")
            return

        # int.bit_length()
        if attr_name == "bit_length" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            lbl_uid = getattr(self, "_lbl_cnt", 0) + 1
            setattr(self, "_lbl_cnt", lbl_uid)
            self.emit("test rax, rax")
            self.emit(f"jz .bl_zero_{lbl_uid}")
            self.emit("bsr rax, rax", "bit scan reverse")
            self.emit("inc rax")
            self.emit(f"jmp .bl_done_{lbl_uid}")
            self.emit(f".bl_zero_{lbl_uid}:")
            self.emit("xor eax, eax")
            self.emit(f".bl_done_{lbl_uid}:")
            return

        # str.isdigit()
        if attr_name == "isdigit" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "str_ptr")
            self.emit("call _pyfasm_str_isdigit")
            return

        # str.isascii()
        if attr_name == "isascii" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "str_ptr")
            self.emit("call _pyfasm_str_isascii")
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
            arg0 = call.args[0]
            arg_type = self._infer_expr_type(arg0)
            self._generate_expr(arg0)
            if arg_type.is_float():
                self.emit("movq xmm0, rax")
                self.emit("cvttsd2si rax, xmm0", "float to int cast")
            elif (arg_type.is_str() or self._is_ambiguous_dynamic_expr(arg0)) and self.target in ("win64", "dll"):
                self.emit("mov rcx, rax", "string ptr or int")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_str_to_int")
                self.emit("add rsp, 32")
            return

        # float(val) conversion / cast
        if func_name == "float" and call.args:
            arg0 = call.args[0]
            arg_type = self._infer_expr_type(arg0)
            self._generate_expr(arg0)
            if not arg_type.is_float():
                if (arg_type.is_str() or self._is_ambiguous_dynamic_expr(arg0)) and self.target in ("win64", "dll"):
                    self.emit("mov rcx, rax", "string ptr or int")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_str_to_float")
                    self.emit("add rsp, 32")
                else:
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0", "int to float cast")
            return

        # bool(val) conversion
        if func_name == "bool" and call.args:
            self._emit_to_bool(call.args[0], negate=False)
            return

        # isinstance(obj, class_or_tuple) & issubclass(cls, class_or_tuple)
        if func_name in ("isinstance", "issubclass") and len(call.args) >= 2:
            def _extract_t_names(node: ast.AST) -> List[str]:
                if isinstance(node, ast.Name):
                    return [node.id]
                if isinstance(node, ast.Tuple):
                    out: List[str] = []
                    for elt in node.elts:
                        out.extend(_extract_t_names(elt))
                    return out
                return []

            t_names = _extract_t_names(call.args[1])
            user_targets = [t for t in t_names if t in self.module.classes]
            matching_subs: List[str] = []
            seen_subs: Set[str] = set()
            for tgt in user_targets:
                for sub in self._all_subclasses(tgt):
                    if sub not in seen_subs:
                        seen_subs.add(sub)
                        matching_subs.append(sub)

            if func_name == "issubclass":
                c0 = call.args[0]
                if isinstance(c0, ast.Name) and c0.id in self.module.classes:
                    res = 1 if ("object" in t_names or c0.id in seen_subs) else 0
                    self.emit(f"mov rax, {res}", f"issubclass({c0.id}, ...)")
                    return
                self._generate_expr(c0)
                lbl_true = self.new_label("issub_true")
                lbl_done = self.new_label("issub_done")
                cands = sorted(self.module.classes.keys()) if "object" in t_names else matching_subs
                for sub in cands:
                    self.emit(f"lea r10, [{safe_asm_label(sub)}]")
                    self.emit("cmp rax, r10")
                    self.emit(f"je {lbl_true}")
                self.emit("xor eax, eax")
                self.emit(f"jmp {lbl_done}")
                self.emit_raw(f"{lbl_true}:")
                self.emit("mov rax, 1")
                self.emit_raw(f"{lbl_done}:")
                return

            # isinstance(obj, ...)
            builtin_targets = [t for t in t_names if t not in self.module.classes]
            arg0 = call.args[0]
            arg0_cls = self.resolve_instance_class(arg0)
            arg0_t = self._infer_expr_type(arg0)
            if not user_targets:
                static_match = False
                if arg0_cls:
                    static_match = "object" in builtin_targets
                else:
                    if "object" in builtin_targets:
                        static_match = True
                    elif "int" in builtin_targets and (arg0_t.is_int() or arg0_t.is_bool()):
                        static_match = True
                    elif "bool" in builtin_targets and arg0_t.is_bool():
                        static_match = True
                    elif "float" in builtin_targets and arg0_t.is_float():
                        static_match = True
                    elif "str" in builtin_targets and arg0_t.is_str():
                        static_match = True
                    elif "list" in builtin_targets and arg0_t.is_list():
                        static_match = True
                    elif "dict" in builtin_targets and arg0_t.is_dict():
                        static_match = True
                    elif "set" in builtin_targets and arg0_t.is_set():
                        static_match = True
                    elif "tuple" in builtin_targets and arg0_t.is_tuple():
                        static_match = True
                if self.target in ("win64", "dll") and self._is_ambiguous_dynamic_expr(arg0) and ("str" in builtin_targets or "int" in builtin_targets):
                    self._generate_expr(arg0)
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_is_utf8_str_ptr")
                    self.emit("add rsp, 32")
                    if "str" not in builtin_targets:
                        self.emit("xor rax, 1")
                    return
                self._generate_expr(arg0)
                self.emit(f"mov rax, {1 if static_match else 0}", "isinstance builtin result")
                return

            matching_ids = [self._class_ids[sub] for sub in matching_subs if sub in self._class_ids]
            self._generate_expr(arg0)
            lbl_false = self.new_label("isinst_false")
            lbl_true = self.new_label("isinst_true")
            lbl_done = self.new_label("isinst_done")
            self.emit("cmp rax, 65536", "check heap instance pointer")
            self.emit(f"jb {lbl_false}")
            self.emit("mov r10, 505946434C535447h", "PYFCLSTG")
            self.emit("cmp [rax + 2032], r10")
            self.emit(f"jne {lbl_false}")
            self.emit("mov r10, [rax + 2040]", "load class_id")
            for cid in matching_ids:
                self.emit(f"cmp r10, {cid}")
                self.emit(f"je {lbl_true}")
            self.emit_raw(f"{lbl_false}:")
            self.emit("xor eax, eax")
            self.emit(f"jmp {lbl_done}")
            self.emit_raw(f"{lbl_true}:")
            self.emit("mov rax, 1")
            self.emit_raw(f"{lbl_done}:")
            return

        # str(val) / repr(val) conversion
        if func_name in ("str", "repr") and call.args:
            arg0 = call.args[0]
            if self.target in ("win64", "dll"):
                self._emit_win64_to_str(arg0, is_repr=(func_name == "repr"), call_node=call)
                return
            cls_name = self.resolve_instance_class(arg0)
            vkey = "__repr__" if func_name == "repr" else "__str__"
            str_m = (self.resolve_class_method(cls_name, "__str__") or self.resolve_class_method(cls_name, "__repr__")) if cls_name else None
            if str_m:
                self._generate_expr(arg0)
                self.emit("mov rcx, rax", "pass self to __str__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(cls_name, vkey, str_m)}")
                self.emit("add rsp, 32")
                return

            self._generate_expr(arg0)
            self.emit("mov rcx, rax")
            self._record_unresolved("str", call)
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
            elif np_m in ("empty",):
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
                self.emit("mov rax, [rbx + r14 * 8 + 8]")
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
                    self.emit(f"call {self._method_call_target(cls_name, '__str__', str_m)}")
                    self.emit("add rsp, 32")
                    self.emit("mov rcx, rax")
                    self.emit("call _pyfasm_print_str")
                else:
                    if isinstance(arg, ast.Constant) and arg.value is None:
                        self.emit("lea rcx, [none_str]")
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
                        elif arg_type.is_list():
                            self.emit("mov rcx, rax")
                            if self.target in ("win64", "dll"):
                                helper = self._select_win64_list_printer(arg_type)
                                self.emit("sub rsp, 32", "shadow space")
                                self.emit(f"call {helper}")
                                self.emit("add rsp, 32")
                            else:
                                self.emit("call _pyfasm_print_list")
                        elif arg_type.is_tuple():
                            self.emit("mov rcx, rax")
                            if self.target in ("win64", "dll"):
                                helper = self._select_win64_tuple_printer(arg_type)
                                self.emit("sub rsp, 32", "shadow space")
                                self.emit(f"call {helper}")
                                self.emit("add rsp, 32")
                            else:
                                self.emit("call _pyfasm_print_list")
                        elif arg_type.is_dict() and self.target in ("win64", "dll"):
                            kt = getattr(arg_type, "key_type", None)
                            vt = getattr(arg_type, "val_type", None)
                            k_fn = self._select_win64_elem_printer(kt)
                            v_fn = self._select_win64_elem_printer(vt)
                            self.emit("mov rcx, rax")
                            self.emit(f"lea rdx, [{k_fn}]")
                            self.emit(f"lea r8, [{v_fn}]")
                            self.emit("sub rsp, 32", "shadow space")
                            self.emit("call _pyfasm_print_dict_with")
                            self.emit("add rsp, 32")
                        elif arg_type.is_set() and self.target in ("win64", "dll"):
                            et = getattr(arg_type, "element_type", None)
                            e_fn = self._select_win64_elem_printer(et)
                            self.emit("mov rcx, rax")
                            self.emit(f"lea rdx, [{e_fn}]")
                            self.emit("sub rsp, 32", "shadow space")
                            self.emit("call _pyfasm_print_set_with")
                            self.emit("add rsp, 32")
                        elif arg_type.is_bool():
                            self.emit("mov rcx, rax")
                            self.emit("call _pyfasm_print_int")
                        elif arg_type.is_int():
                            if self.target in ("win64", "dll") and self._is_ambiguous_dynamic_expr(arg):
                                self.emit("mov rcx, rax")
                                self.emit("sub rsp, 32", "shadow space")
                                self.emit("call _pyfasm_print_auto")
                                self.emit("add rsp, 32")
                            else:
                                self.emit("mov rcx, rax")
                                self.emit("call _pyfasm_print_int")
                        else:
                            self.emit("mov rcx, rax")
                            if self.target in ("win64", "dll"):
                                self.emit("sub rsp, 32", "shadow space")
                                self.emit("call _pyfasm_print_auto")
                                self.emit("add rsp, 32")
                            else:
                                self.emit("call _pyfasm_print_auto")
            self.emit("call _pyfasm_print_newline")
            return

        if func_name == "input":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "prompt string")
                self.emit("call _pyfasm_print_str")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_input")
            self.emit("call _pyfasm_input")
            self.emit("add rsp, 32", "restore shadow space")
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
            it_cls = self.resolve_instance_class(call.args[0])
            next_m = self.resolve_class_method(it_cls, "__next__") if it_cls else None
            if next_m:
                if len(call.args) == 1:
                    self._generate_expr(call.args[0])
                    self.emit("mov rcx, rax", "pass self to __next__")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration flag")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {self._method_call_target(it_cls, '__next__', next_m)}")
                    self.emit("add rsp, 32")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration flag")
                    return
                else:
                    lbl_ok = self.new_label("next_inst_ok")
                    self._generate_expr(call.args[0])
                    self.emit("sub rsp, 16", "aligned slot for custom next()")
                    self.emit("mov [rsp], rax", "save iterator")
                    self._generate_expr(call.args[1])
                    self.emit("mov [rsp + 8], rax", "save default value")
                    self.emit("mov rcx, [rsp]", "pass self to __next__")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration flag")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {self._method_call_target(it_cls, '__next__', next_m)}")
                    self.emit("add rsp, 32")
                    self.emit("cmp qword [_pyfasm_stop_iter], 0", "check StopIteration")
                    self.emit(f"je {lbl_ok}")
                    self.emit("mov qword [_pyfasm_stop_iter], 0", "clear StopIteration flag")
                    self.emit("mov rax, [rsp + 8]", "use default value")
                    self.emit_raw(f"{lbl_ok}:")
                    self.emit("add rsp, 16", "cleanup custom next() slot")
                    return
            if len(call.args) == 1:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "gen_ptr")
                self.emit("sub rsp, 32", "shadow space for gen_next")
                self.emit("call _pyfasm_gen_next")
                self.emit("add rsp, 32", "restore shadow space")
                return
            else:
                self._generate_expr(call.args[0])
                self.emit("push rax", "gen_ptr")
                self._generate_expr(call.args[1])
                self.emit("push rax", "default_val")
                self.emit("mov rcx, [rsp + 8]", "gen_ptr")
                self.emit("sub rsp, 32", "shadow space for gen_next")
                self.emit("call _pyfasm_gen_next")
                self.emit("add rsp, 32", "restore shadow space")
                lbl_check_exhausted = self.new_label("next_check_exhausted")
                lbl_done = self.new_label("next_done")
                self.emit("mov r10, [rsp + 8]", "gen_ptr")
                self.emit("test r10, r10")
                self.emit(f"jz {lbl_check_exhausted}")
                self.emit("cmp qword [r10 + 16], 1", "check done flag")
                self.emit(f"jne {lbl_done}")
                self.emit_raw(f"{lbl_check_exhausted}:")
                self.emit("mov rax, [rsp]", "use default value")
                self.emit_raw(f"{lbl_done}:")
                self.emit("add rsp, 16", "cleanup default_val + gen_ptr")
                return

        # Built-in range(...) constructor as an expression
        if func_name == "range" and call.args:
            args = call.args
            start_expr = None
            stop_expr = None
            const_step: Optional[int] = 1
            step_expr: Optional[ast.expr] = None
            if len(args) == 1:
                stop_expr = args[0]
            elif len(args) >= 2:
                start_expr = args[0]
                stop_expr = args[1]
                if len(args) >= 3:
                    if isinstance(args[2], ast.Constant) and isinstance(args[2].value, int):
                        const_step = args[2].value
                    elif isinstance(args[2], ast.UnaryOp) and isinstance(args[2].op, ast.USub) and isinstance(args[2].operand, ast.Constant) and isinstance(args[2].operand.value, int):
                        const_step = -args[2].operand.value
                    else:
                        const_step = None
                        step_expr = args[2]

            lbl_loop = self.new_label("range_expr_loop")
            lbl_done = self.new_label("range_expr_done")
            lbl_alloc_ok = self.new_label("range_alloc_ok")
            lbl_alloc_min = self.new_label("range_alloc_min")

            self.emit("push rbx")
            self.emit("push r12")
            self.emit("push r13")
            self.emit("push r14")
            if step_expr is not None:
                self.emit("push r15")
                self.emit("sub rsp, 8", "keep 16-byte alignment")

            self._generate_expr(stop_expr)
            self.emit("mov r13, rax", "range stop")

            if start_expr:
                self._generate_expr(start_expr)
                self.emit("mov r12, rax", "range start")
            else:
                self.emit("xor r12, r12", "range start = 0")

            if step_expr is not None:
                self._generate_expr(step_expr)
                self.emit("mov r15, rax", "range step")

            if const_step == 0:
                self.emit("mov ecx, 1024", "empty range buffer")
            elif const_step is not None:
                if const_step > 0:
                    self.emit("mov rax, r13")
                    self.emit("sub rax, r12")
                else:
                    self.emit("mov rax, r12")
                    self.emit("sub rax, r13")
                self.emit("cmp rax, 0")
                self.emit(f"jle {lbl_alloc_min}")
                abs_step = abs(const_step)
                if abs_step > 1:
                    self.emit("cqo")
                    self.emit(f"mov rcx, {abs_step}")
                    self.emit("idiv rcx")
                self.emit("lea rcx, [rax * 8 + 32]")
                self.emit("cmp rcx, 1024")
                self.emit(f"jae {lbl_alloc_ok}")
                self.emit_raw(f"{lbl_alloc_min}:")
                self.emit("mov ecx, 1024", "initial list buffer")
                self.emit_raw(f"{lbl_alloc_ok}:")
            else:
                lbl_dyn_pos = self.new_label("range_dyn_pos")
                lbl_dyn_calc = self.new_label("range_dyn_calc")
                self.emit("mov rax, r13")
                self.emit("sub rax, r12")
                self.emit("test r15, r15")
                self.emit(f"jz {lbl_alloc_min}")
                self.emit(f"jg {lbl_dyn_pos}")
                self.emit("neg rax")
                self.emit("mov rcx, r15")
                self.emit("neg rcx")
                self.emit(f"jmp {lbl_dyn_calc}")
                self.emit_raw(f"{lbl_dyn_pos}:")
                self.emit("mov rcx, r15")
                self.emit_raw(f"{lbl_dyn_calc}:")
                self.emit("cmp rax, 0")
                self.emit(f"jle {lbl_alloc_min}")
                self.emit("cqo")
                self.emit("idiv rcx")
                self.emit("lea rcx, [rax * 8 + 32]")
                self.emit("cmp rcx, 1024")
                self.emit(f"jae {lbl_alloc_ok}")
                self.emit_raw(f"{lbl_alloc_min}:")
                self.emit("mov ecx, 1024", "initial list buffer")
                self.emit_raw(f"{lbl_alloc_ok}:")

            self.emit("sub rsp, 32", "shadow space for alloc")
            self.emit("call _pyfasm_alloc")
            self.emit("add rsp, 32", "restore shadow space")
            self.emit("mov qword [rax], 0", "length = 0")
            self.emit("mov r14, rax", "list_ptr")

            if const_step == 0:
                self.emit(f"jmp .done_{lbl_done}")
            else:
                self.emit_raw(f".loop_{lbl_loop}:")
                if const_step is not None:
                    self.emit("cmp r12, r13")
                    if const_step > 0:
                        self.emit(f"jge .done_{lbl_done}")
                    else:
                        self.emit(f"jle .done_{lbl_done}")
                else:
                    lbl_step_pos = self.new_label("range_step_pos")
                    lbl_step_body = self.new_label("range_step_body")
                    self.emit("test r15, r15")
                    self.emit(f"jz .done_{lbl_done}")
                    self.emit(f"jg {lbl_step_pos}")
                    self.emit("cmp r12, r13")
                    self.emit(f"jle .done_{lbl_done}")
                    self.emit(f"jmp {lbl_step_body}")
                    self.emit_raw(f"{lbl_step_pos}:")
                    self.emit("cmp r12, r13")
                    self.emit(f"jge .done_{lbl_done}")
                    self.emit_raw(f"{lbl_step_body}:")

                self.emit("mov rdx, r12", "current item")
                self.emit("mov rcx, r14", "list_ptr")
                self.emit("sub rsp, 32", "shadow space for append")
                self.emit("call _pyfasm_list_append")
                self.emit("add rsp, 32", "restore shadow space")

                if const_step is None:
                    self.emit("add r12, r15")
                elif const_step == 1:
                    self.emit("inc r12")
                elif const_step == -1:
                    self.emit("dec r12")
                else:
                    self.emit(f"add r12, {const_step}")
                self.emit(f"jmp .loop_{lbl_loop}")

            self.emit_raw(f".done_{lbl_done}:")
            self.emit("mov rax, r14", "return range list")
            if step_expr is not None:
                self.emit("add rsp, 8")
                self.emit("pop r15")
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
        if func_name == "list":
            if not call.args:
                self.emit("mov ecx, 1024", "empty list buffer")
                self.emit("sub rsp, 32", "shadow space for alloc")
                self.emit("call _pyfasm_alloc")
                self.emit("add rsp, 32", "restore shadow space")
                self.emit("mov qword [rax], 0", "length = 0")
                return
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
                self.emit("mov ecx, 65536", "initial list capacity")
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

            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "range":
                self._generate_expr(arg)
                return

            arg_type = self._infer_expr_type(arg)
            self._generate_expr(arg)
            if (
                self.target == "win64"
                and not arg_type.is_str()
                and not arg_type.is_dict()
                and not arg_type.is_set()
            ):
                self.emit("mov rcx, rax", "sequence pointer")
                self.emit("xor edx, edx", "start = 0")
                self.emit("mov r8, -999999", "end sentinel")
                self.emit("mov r9, 1", "step = 1")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_list_slice")
                self.emit("add rsp, 32", "restore shadow space")
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
                    self.emit(f"call {self._method_call_target(cls_name, '__len__', len_m)}")
                    self.emit("add rsp, 32")
                    return

                is_dict_arg = False
                is_str_arg = False
                arg0_type = self._infer_expr_type(arg0)
                if arg0_type.is_str():
                    is_str_arg = True
                elif arg0_type.is_dict() or arg0_type.is_set():
                    is_dict_arg = True
                elif isinstance(arg0, ast.Name) and self.current_func:
                    var = self.current_func.local_vars.get(arg0.id)
                    if var:
                        if var.var_type.is_str():
                            is_str_arg = True
                        elif var.var_type.is_dict() or var.var_type.is_set():
                            is_dict_arg = True
                self._generate_expr(arg0)
                if is_str_arg:
                    self.emit("mov rcx, rax")
                    if func_name == "len" and self.target in ("win64", "dll"):
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit("call _pyfasm_utf8_len")
                        self.emit("add rsp, 32")
                    else:
                        self.emit("call _pyfasm_str_len")
                elif is_dict_arg:
                    self.emit("mov rcx, rax")
                    self.emit("call _pyfasm_dict_len")
                else:
                    self.emit("mov rax, [rax]", "load length from header")
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

        # Method .count(needle) on strings and lists
        if attr_name == "count" and len(call.args) >= 1 and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.args[0])
            self.emit("push rax", "needle")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "haystack")
            self.emit("pop rdx", "needle")
            caller_type = self._infer_expr_type(call.func.value)
            if caller_type.is_list():
                self.emit("call _pyfasm_list_count")
            else:
                self.emit("call _pyfasm_str_count")
            return

        # Built-in set(...) constructor
        if func_name == "set":
            if not call.args:
                self.emit("mov ecx, 16")
                self.emit("call _pyfasm_set_create")
                return
            arg = call.args[0]
            caller_type = self._infer_expr_type(arg)
            self._generate_expr(arg)
            self.emit("mov rcx, rax", "argument to set")
            if caller_type.is_str():
                self.emit("call _pyfasm_set_from_str")
            elif caller_type.is_list():
                self.emit("call _pyfasm_set_from_list")
            else:
                self.emit("call _pyfasm_set_from_iterable")
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

        # Standard library bisect / bisect_right(a, x, [lo=0])
        if (func_name in ("bisect", "bisect_right") or (prefix == "bisect" and attr_name in ("bisect", "bisect_right"))) and len(call.args) >= 2:
            if len(call.args) >= 3:
                self._generate_expr(call.args[2])
                self.emit("push rax", "lo")
            else:
                self.emit("push 0", "default lo = 0")
            self._generate_expr(call.args[1])
            self.emit("push rax", "save search item")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list a")
            self.emit("pop rdx", "pass search item")
            self.emit("pop r8", "pass lo")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_bisect_right")
            self.emit("call _pyfasm_bisect_right")
            self.emit("add rsp, 32", "restore shadow space")
            return

        if (func_name == "bisect_left" or (prefix == "bisect" and attr_name == "bisect_left")) and len(call.args) >= 2:
            if len(call.args) >= 3:
                self._generate_expr(call.args[2])
                self.emit("push rax", "lo")
            else:
                self.emit("push 0", "default lo = 0")
            self._generate_expr(call.args[1])
            self.emit("push rax", "save search item")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list a")
            self.emit("pop rdx", "pass search item")
            self.emit("pop r8", "pass lo")
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

        # heapq.heapreplace(heap, item)
        if (func_name in ("heapreplace", "heapq_heapreplace") or (prefix == "heapq" and attr_name == "heapreplace")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "save new item")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass heap pointer")
            self.emit("pop rdx", "pass new item")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_heapreplace")
            self.emit("call _pyfasm_heapreplace")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # heapq.heapify(heap)
        if (func_name in ("heapify", "heapq_heapify") or (prefix == "heapq" and attr_name == "heapify")) and len(call.args) >= 1:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass heap pointer")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_heapify")
            self.emit("call _pyfasm_heapify")
            self.emit("add rsp, 32", "restore shadow space")
            return

        # Built-in sorted(iterable) or list.sort()
        if func_name == "sorted" and len(call.args) >= 1:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list to sort")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_sorted")
            self.emit("call _pyfasm_sorted")
            self.emit("add rsp, 32", "restore shadow space")
            return

        if (func_name == "sort" or attr_name == "sort") and (isinstance(call.func, ast.Attribute) or len(call.args) >= 1):
            if isinstance(call.func, ast.Attribute):
                self._generate_expr(call.func.value)
            else:
                self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "pass list to sort")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_list_sort")
            self.emit("call _pyfasm_list_sort")
            self.emit("add rsp, 32", "restore shadow space")
            self.emit("xor eax, eax", "sort() returns None")
            return

        # NanoGEMM / NumPy matmul and dot product
        if (func_name in ("matmul", "nanogemm_matmul", "np_matmul", "np_dot") or (prefix in ("nanogemm", "np", "numpy") and attr_name in ("matmul", "dot"))) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "right matrix/vector")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "left matrix/vector")
            self.emit("pop rdx", "right matrix/vector")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_nanogemm_matmul")
            self.emit("add rsp, 32")
            return

        if (func_name in ("get_simd_isa", "nanogemm_simd_isa") or (prefix == "nanogemm" and attr_name == "get_simd_isa")):
            self.emit("call _pyfasm_nanogemm_simd_isa")
            return

        # NumPy zeros: np.zeros(shape)
        if (func_name == "zeros" or (prefix in ("np", "numpy") and attr_name == "zeros")) and call.args:
            if isinstance(call.args[0], (ast.Tuple, ast.List)) and len(call.args[0].elts) == 2:
                self._generate_expr(call.args[0].elts[1])
                self.emit("push rax", "cols")
                self._generate_expr(call.args[0].elts[0])
                self.emit("mov rcx, rax", "rows")
                self.emit("pop rdx", "cols")
            else:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "n")
                self.emit("xor edx, edx", "1D zeros")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_np_zeros")
            self.emit("add rsp, 32")
            return

        # NumPy ones: np.ones(shape)
        if (func_name == "ones" or (prefix in ("np", "numpy") and attr_name == "ones")) and call.args:
            if isinstance(call.args[0], (ast.Tuple, ast.List)) and len(call.args[0].elts) == 2:
                self._generate_expr(call.args[0].elts[1])
                self.emit("push rax", "cols")
                self._generate_expr(call.args[0].elts[0])
                self.emit("mov rcx, rax", "rows")
                self.emit("pop rdx", "cols")
            else:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "n")
                self.emit("xor edx, edx", "1D ones")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_np_ones")
            self.emit("add rsp, 32")
            return

        # NumPy array / asarray: np.array(x)
        if (func_name in ("array", "asarray") or (prefix in ("np", "numpy") and attr_name in ("array", "asarray"))) and call.args:
            self._generate_expr(call.args[0])
            return

        # math.gcd(a, b) and multi-arg / starred gcd(*seq)
        is_gcd_call = (func_name in ("gcd", "math_gcd") or (prefix == "math" and attr_name == "gcd"))
        if not is_gcd_call and self.current_func and func_name:
            for idx, f_arg in enumerate(self.current_func.args):
                if f_arg.name == func_name:
                    defaults = getattr(self.current_func, "defaults", [])
                    num_defaults = len(defaults)
                    num_no_defaults = len(self.current_func.args) - num_defaults
                    d_idx = idx - num_no_defaults
                    if 0 <= d_idx < num_defaults:
                        d_val = defaults[d_idx]
                        if (isinstance(d_val, ast.Attribute) and d_val.attr == "gcd") or (isinstance(d_val, ast.Name) and d_val.id in ("gcd", "math_gcd")):
                            is_gcd_call = True
                    break

        if is_gcd_call:
            if len(call.args) == 1 and isinstance(call.args[0], ast.Starred):
                self._generate_expr(call.args[0].value)
                self.emit("mov rcx, rax", "list of numbers for gcd")
                self.emit("call _pyfasm_math_gcd_list")
                return
            elif len(call.args) == 1:
                self._generate_expr(call.args[0])
                lbl_pos = self.new_label("gcd_pos")
                self.emit("test rax, rax")
                self.emit(f"jns {lbl_pos}")
                self.emit("neg rax", "math.gcd(x) = abs(x)")
                self.emit_raw(f"{lbl_pos}:")
                return
            elif len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("push rax")
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
                self.emit("call _pyfasm_math_gcd")
                for extra_arg in call.args[2:]:
                    self.emit("push rax")
                    self._generate_expr(extra_arg)
                    self.emit("mov rdx, rax")
                    self.emit("pop rcx")
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
            has_init = 1 if len(call.args) >= 3 else 0
            if has_init:
                self._generate_expr(call.args[2])
                self.emit("push rax", "initial value")
            else:
                self.emit("xor eax, eax")
                self.emit("push rax", "dummy initial value")
            self._generate_expr(call.args[1])
            self.emit("push rax", "list")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "fn")
            self.emit("pop rdx", "list")
            self.emit("pop r8", "initial")
            self.emit(f"mov r9d, {has_init}", "has initial flag")
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

        # Check callable class instance obj(...) via __call__
        is_callable_inst = False
        if not is_super_call and func_name not in self.module.functions:
            callable_cls = self.resolve_instance_class(call.func)
            if callable_cls:
                call_dunder = self.resolve_class_method(callable_cls, "__call__", skip_cls=False)
                if call_dunder and call_dunder in self.module.functions:
                    func_name = call_dunder
                    recv_cls_hint = callable_cls
                    is_callable_inst = True

        # User Function / Method Call (x64 ABI)
        is_bound_method = False
        if func_name in self.module.functions:
            fn_sym = self.module.functions[func_name]
            if is_callable_inst:
                args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=True, self_expr=call.func)
            elif is_super_call:
                args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=True, self_expr=ast.Name(id="self", ctx=ast.Load()))
            elif isinstance(call.func, ast.Attribute):
                if getattr(fn_sym, "is_staticmethod", False):
                    args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=False)
                elif getattr(fn_sym, "is_classmethod", False):
                    if isinstance(call.func.value, ast.Name) and call.func.value.id in self.module.classes:
                        cls_arg_expr: ast.AST = ast.Name(id=call.func.value.id, ctx=ast.Load())
                    elif getattr(self.current_func, "is_classmethod", False) and self.current_func and self.current_func.args and isinstance(call.func.value, ast.Name) and call.func.value.id == self.current_func.args[0].name:
                        cls_arg_expr = ast.Name(id=call.func.value.id, ctx=ast.Load())
                    else:
                        cls_arg_expr = ast.Name(id=(recv_cls_hint or fn_sym.class_name or prefix), ctx=ast.Load())
                    args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=True, self_expr=cls_arg_expr)
                elif fn_sym.args and fn_sym.args[0].name == "self" and not (isinstance(call.func.value, ast.Name) and call.func.value.id in self.module.classes):
                    is_bound_method = True
                    args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=True, self_expr=call.func.value)
                else:
                    args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=False)
            else:
                args_to_pass = self._prepare_call_args(call, fn_sym, is_method_call=False)
        else:
            if (
                getattr(self.current_func, "is_classmethod", False)
                and self.current_func
                and self.current_func.args
                and isinstance(call.func, ast.Name)
                and call.func.id == self.current_func.args[0].name
                and self.current_func.class_name in self.module.functions
            ):
                args_to_pass = self._prepare_call_args(call, self.module.functions[self.current_func.class_name], is_method_call=False)
            else:
                args_to_pass = list(call.args)
                if is_super_call:
                    args_to_pass = [ast.Name(id="self", ctx=ast.Load())] + list(call.args)

        # Evaluate arguments and push them in reverse order
        is_indirect = False
        indirect_local_var = None
        is_indirect_global = False

        if is_callable_inst:
            is_indirect = False
        elif isinstance(call.func, ast.Name):
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
                self.emit(f"mov r10, [{safe_global_label(call.func.id)}]", f"indirect global callee {call.func.id}")
            else:
                if n_args <= 4:
                    self.emit("pop r10", "restore indirect callee from stack")
                else:
                    self.emit(f"mov r10, [rsp + {(n_args - 4) * 8}]", "read indirect callee above extra stack args")

            has_any_call_dunder = any(
                self.resolve_class_method(cname, "__call__") for cname in self.module.classes
            )
            lbl_skip = self.new_label("skip_null_call")
            lbl_normal_call = self.new_label("indirect_normal")
            lbl_check_obj = self.new_label("indirect_check_obj")
            lbl_closure_call = self.new_label("indirect_closure")
            lbl_dunder_call = self.new_label("indirect_dunder_call") if has_any_call_dunder else ""
            lbl_done_call = self.new_label("done_indirect_call")

            self.emit("cmp r10, 65536", "check for invalid/null function pointer")
            self.emit(f"jb {lbl_skip}")
            self.emit("lea r11, [_pyfasm_funcs_start]")
            self.emit("cmp r10, r11")
            self.emit(f"jb {lbl_check_obj}")
            self.emit("lea r11, [_pyfasm_funcs_end]")
            self.emit("cmp r10, r11")
            self.emit(f"jb {lbl_normal_call}")
            self.emit_raw(f"{lbl_check_obj}:")
            self.emit("mov r11, 505946434C4F5355h", "PYFCLOSU")
            self.emit("cmp [r10], r11")
            self.emit(f"je {lbl_closure_call}")
            if has_any_call_dunder:
                self.emit("mov r11, 505946434C535447h", "PYFCLSTG")
                self.emit("cmp [r10 + 2032], r11")
                self.emit(f"je {lbl_dunder_call}")

            self.emit_raw(f"{lbl_normal_call}:")
            for unused_reg in ["ecx", "edx", "r8d", "r9d"][n_args:]:
                self.emit(f"xor {unused_reg}, {unused_reg}", "zero unused indirect arg reg")
            self.emit("sub rsp, 32", "shadow space for callee")
            self.emit("call r10")
            self.emit("add rsp, 32", "restore shadow space")
            self.emit(f"jmp {lbl_done_call}")

            def _emit_env_self_call(is_dunder: bool) -> None:
                # Prepends r10 (closure env or instance self) before the n_args user arguments.
                if n_args == 0:
                    self.emit("mov rcx, r10", "pass env/self")
                    self.emit("xor edx, edx")
                    self.emit("xor r8d, r8d")
                    self.emit("xor r9d, r9d")
                    if is_dunder:
                        self._used_vcalls.add("__call__")
                        self.emit(f"lea r10, [{self._vcall_label('__call__')}]")
                    else:
                        self.emit("mov r10, [r10 + 8]", "load closure fn ptr")
                    self.emit("sub rsp, 32")
                    self.emit("call r10")
                    self.emit("add rsp, 32")
                elif n_args == 1:
                    self.emit("mov rdx, rcx")
                    self.emit("mov rcx, r10")
                    self.emit("xor r8d, r8d")
                    self.emit("xor r9d, r9d")
                    if is_dunder:
                        self._used_vcalls.add("__call__")
                        self.emit(f"lea r10, [{self._vcall_label('__call__')}]")
                    else:
                        self.emit("mov r10, [r10 + 8]")
                    self.emit("sub rsp, 32")
                    self.emit("call r10")
                    self.emit("add rsp, 32")
                elif n_args == 2:
                    self.emit("mov r8, rdx")
                    self.emit("mov rdx, rcx")
                    self.emit("mov rcx, r10")
                    self.emit("xor r9d, r9d")
                    if is_dunder:
                        self._used_vcalls.add("__call__")
                        self.emit(f"lea r10, [{self._vcall_label('__call__')}]")
                    else:
                        self.emit("mov r10, [r10 + 8]")
                    self.emit("sub rsp, 32")
                    self.emit("call r10")
                    self.emit("add rsp, 32")
                elif n_args == 3:
                    self.emit("mov r9, r8")
                    self.emit("mov r8, rdx")
                    self.emit("mov rdx, rcx")
                    self.emit("mov rcx, r10")
                    if is_dunder:
                        self._used_vcalls.add("__call__")
                        self.emit(f"lea r10, [{self._vcall_label('__call__')}]")
                    else:
                        self.emit("mov r10, [r10 + 8]")
                    self.emit("sub rsp, 32")
                    self.emit("call r10")
                    self.emit("add rsp, 32")
                elif n_args == 4:
                    self.emit("sub rsp, 8", "align stack before 5th arg push")
                    self.emit("push r9", "shift 4th arg to stack")
                    self.emit("mov r9, r8")
                    self.emit("mov r8, rdx")
                    self.emit("mov rdx, rcx")
                    self.emit("mov rcx, r10")
                    if is_dunder:
                        self._used_vcalls.add("__call__")
                        self.emit(f"lea r10, [{self._vcall_label('__call__')}]")
                    else:
                        self.emit("mov r10, [r10 + 8]")
                    self.emit("sub rsp, 32")
                    self.emit("call r10")
                    self.emit("add rsp, 48", "cleanup shadow + 5th arg + align pad")
                else:
                    m_extra = n_args - 4
                    c_callee = 1 if needs_stack_callee else 0
                    pad = 8 if ((c_callee + m_extra + 1) % 2 == 1) else 0
                    self.emit(f"sub rsp, {8 + pad}", "make room for shifted 5th arg")
                    if pad > 0:
                        for i_ex in range(m_extra):
                            self.emit(f"mov rax, [rsp + {8 + pad + i_ex * 8}]")
                            self.emit(f"mov [rsp + {8 + i_ex * 8}], rax")
                    self.emit("mov [rsp], r9", "place shifted 5th arg")
                    self.emit("mov r9, r8")
                    self.emit("mov r8, rdx")
                    self.emit("mov rdx, rcx")
                    self.emit("mov rcx, r10")
                    if is_dunder:
                        self._used_vcalls.add("__call__")
                        self.emit(f"lea r10, [{self._vcall_label('__call__')}]")
                    else:
                        self.emit("mov r10, [r10 + 8]")
                    self.emit("sub rsp, 32")
                    self.emit("call r10")
                    self.emit(f"add rsp, {32 + 8 + pad}")

            self.emit_raw(f"{lbl_closure_call}:")
            _emit_env_self_call(is_dunder=False)
            self.emit(f"jmp {lbl_done_call}")

            if has_any_call_dunder:
                self.emit_raw(f"{lbl_dunder_call}:")
                _emit_env_self_call(is_dunder=True)
                self.emit(f"jmp {lbl_done_call}")

            self.emit_raw(f"{lbl_skip}:")
            self.emit("xor eax, eax", "safe fallback return 0 for unresolvable call")
            self.emit_raw(f"{lbl_done_call}:")
        else:
            if is_callable_inst:
                callee_target = self._method_call_target(recv_cls_hint, "__call__", func_name)
            elif is_bound_method and self._method_has_polymorphic_impls(recv_cls_hint, attr_name):
                self._used_vcalls.add(attr_name)
                callee_target = self._vcall_label(attr_name)
            else:
                if func_name not in self.module.functions:
                    self._record_unresolved(func_name, call)
                callee_target = safe_asm_label(func_name)
            self.emit("sub rsp, 32", "shadow space for callee")
            self.emit(f"call {callee_target}")
            self.emit("add rsp, 32", "restore shadow space")

        # If more than 4 arguments, cleanup extra stack args
        if needs_stack_callee and n_args > 4:
            self.emit(f"add rsp, {(n_args - 4) * 8 + 8}", "cleanup extra stack args & callee ptr")
        elif n_args > 4:
            extra_bytes = (n_args - 4) * 8
            self.emit(f"add rsp, {extra_bytes}", "cleanup stack args")
