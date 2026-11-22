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
import sys
from typing import List, Dict, Optional, Tuple, Set, Any
_AST_MATCH = getattr(ast, 'Match', ())
_AST_MATCH_AS = getattr(ast, 'MatchAs', ())
_AST_MATCH_VALUE = getattr(ast, 'MatchValue', ())
_AST_MATCH_OR = getattr(ast, 'MatchOr', ())
from pyfasm.ast_parser import ParsedModule, FunctionSymbol, VariableSymbol, StringLiteral, FloatLiteral, walk_local_scope
from pyfasm.diagnostics import CompilerDiagnostic, extract_source_line
from pyfasm.types import (
    TYPE_INT, TYPE_FLOAT, TYPE_COMPLEX, TYPE_STR, TYPE_LIST, TYPE_DICT, TYPE_SET,
    TYPE_TUPLE, TYPE_BOOL, TYPE_PTR, TYPE_VOID, PyFasmType,
    FloatType, ListType, DictType, SetType, TupleType, InstanceType,
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


BUILTIN_EXCEPTIONS_AND_SYMBOLS: Set[str] = {
    "BaseException", "Exception", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "NotImplementedError",
    "ZeroDivisionError", "AssertionError", "OverflowError", "StopIteration",
    "DeprecationWarning", "Warning", "LookupError", "NameError", "SyntaxError",
    "FileNotFoundError", "PermissionError", "OSError", "IOError",
    "getattr", "hasattr", "setattr", "delattr", "isinstance", "issubclass",
    "callable", "classmethod", "staticmethod", "property", "super",
    "type", "object", "id", "repr", "dir", "vars", "format", "hash",
    "sorted", "reversed", "slice", "complex", "frozenset", "globals", "locals",
    "bisect", "bisect_right", "bisect_left", "zip", "enumerate",
    "heappush", "heappop", "heapify", "heapreplace", "sort", "list_sort",
    "matmul", "nanogemm_matmul", "nanogemm_simd_isa", "get_simd_isa",
    "zeros", "ones", "gcd", "lcm", "isqrt", "factorial", "chain", "accumulate",
    "reduce", "set", "count", "math_gcd", "_pyfasm_closure_new", "_pyfasm_closure_get",
    "ctk", "np", "math", "sys", "os", "json", "itertools", "time", "re",
}

class X64CodeGen:
    """Translates a ParsedModule into a complete FASM assembly program."""

    def __init__(
        self,
        module: ParsedModule,
        target: str = "win64",
        icon_path: Optional[str] = None,
        py_version: Optional[Tuple[int, int]] = None,
        py_micro: Optional[int] = None,
    ):
        self.icon_path = icon_path
        self.module = module
        self.target = target
        self.py_version = py_version or (sys.version_info.major, sys.version_info.minor)
        self.py_micro = py_micro if py_micro is not None else sys.version_info.micro
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
        self._class_written_attrs: Dict[str, Set[str]] = {}
        self._np_array_vars: Set[str] = set()

    def get_or_create_float(self, val: float) -> str:
        target_bits = struct.pack("<d", float(val))
        for f in self.module.float_literals:
            if struct.pack("<d", f.value) == target_bits:
                return f.label
        self._label_counter += 1
        label = f"_flt_lit_gen_{self._label_counter}"
        self.module.float_literals.append(FloatLiteral(label=label, value=float(val)))
        return label

    def _emit_float_bits(self, reg: str, val: float) -> None:
        lbl = self.get_or_create_float(val)
        self.emit(f"mov {reg}, [{lbl}]", f"float {val}")

    def _record_class_attr(self, cls_name: Optional[str], attr_name: str) -> None:
        if cls_name and attr_name:
            self._class_written_attrs.setdefault(cls_name, set()).add(attr_name)

    def _is_generator_expr(self, expr: ast.AST) -> bool:
        if isinstance(expr, ast.GeneratorExp):
            return True
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
            fn_id = expr.func.id
            if fn_id.startswith("_pyfasm_genexp_"):
                return True
            fn_sym = self.module.functions.get(fn_id)
            if fn_sym and getattr(fn_sym, "is_generator", False):
                return True
        if isinstance(expr, ast.Name) and self.current_func:
            vs = self.current_func.local_vars.get(expr.id)
            if vs and (getattr(vs, "is_generator", False) or (hasattr(vs, "var_type") and vs.var_type.is_generator())):
                return True
        return self._infer_expr_type(expr).is_generator()

    def _is_np_array_expr(self, expr: ast.AST) -> bool:
        if isinstance(expr, ast.Name) and expr.id in self._np_array_vars:
            return True
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Attribute) and isinstance(expr.func.value, ast.Name) and expr.func.value.id in ("np", "numpy"):
                if expr.func.attr in ("linspace", "arange", "empty", "zeros", "ones", "array", "asarray", "asanyarray", "sign", "sqrt", "sin", "cos", "tan", "exp", "log", "log10", "abs", "floor", "ceil", "isfinite", "isnan", "column_stack"):
                    return True
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            return self._is_np_array_expr(expr.left) or self._is_np_array_expr(expr.right)
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
            return self._is_np_array_expr(expr.operand)
        return False

    def get_or_create_string(self, text: str) -> str:
        for s in self.module.string_literals:
            if s.value == text:
                return s.label
        self._label_counter += 1
        label = f"_str_lit_gen_{self._label_counter}"
        self.module.string_literals.append(StringLiteral(label=label, value=text))
        return label

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
        if getattr(self.module, "is_pygame_app", False):
            feats.add("pygame")
            feats.add("gui")
        if self.module.has_library("matplotlib", "pyplot", "pylab"):
            feats.add("matplotlib")
            feats.add("gui")
        if getattr(self.module, "is_http_server_app", False):
            feats.add("http_server")
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
                "type": 32,
                "key": 40,
                "x": 48,
                "left": 48,
                "y": 56,
                "top": 56,
                "w": 64,
                "width": 64,
                "h": 72,
                "height": 72,
            }
            self._next_attr_offset = 80
        if attr_name not in self._attr_offsets:
            self._attr_offsets[attr_name] = self._next_attr_offset
            self._next_attr_offset += 8
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
                        parts.append(ast.FormattedValue(value=args[arg_idx], conversion=-1, format_spec=None))
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
                        parts.append(ast.FormattedValue(value=args[arg_idx], conversion=-1, format_spec=None))
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

        # Expand any ast.Starred positional arguments
        expanded_call_args: List[ast.AST] = []
        for a in call.args:
            if isinstance(a, ast.Starred):
                remaining_needed = len(formal_args) - len(expanded_call_args)
                if remaining_needed > 0:
                    for s_idx in range(remaining_needed):
                        sub_node = ast.Subscript(
                            value=a.value,
                            slice=ast.Constant(value=s_idx),
                            ctx=ast.Load()
                        )
                        expanded_call_args.append(sub_node)
                else:
                    expanded_call_args.append(a.value)
            else:
                expanded_call_args.append(a)

        # 1. Positional arguments
        for i, a in enumerate(expanded_call_args):
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

    def _extract_kwarg_int(self, call: ast.Call, kw_name: str, default: int = 0) -> int:
        node = self._extract_kwarg(call, kw_name)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int):
            return -int(node.operand.value)
        return default

    def _extract_padding(self, call: ast.Call, kw_name: str, default: int = 4) -> int:
        node = self._extract_kwarg(call, kw_name)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        elif isinstance(node, (ast.Tuple, ast.List)) and node.elts:
            vals = [int(e.value) for e in node.elts[:2] if isinstance(e, ast.Constant) and isinstance(e.value, int)]
            if len(vals) == 1:
                return vals[0]
            if len(vals) == 2:
                p1, p2 = vals[0], vals[1]
                if p1 == p2:
                    return p1
                return 0x80000000 | ((p2 & 0x7FFF) << 15) | (p1 & 0x7FFF)
        return default

    @staticmethod
    def _parse_color_literal(s: str) -> int:
        sv = s.strip().lower()
        if not sv:
            return 0
        if sv == "transparent":
            return 0x40000000
        named = {
            "white": (255, 255, 255), "black": (0, 0, 0),
            "red": (220, 38, 38), "green": (22, 163, 74), "blue": (37, 99, 235),
            "gray": (128, 128, 128), "grey": (128, 128, 128),
            "lightgray": (211, 211, 211), "darkgray": (64, 64, 64),
            "orange": (234, 88, 12), "yellow": (234, 179, 8),
            "cyan": (6, 182, 212), "magenta": (217, 70, 239),
            "purple": (147, 51, 234), "pink": (236, 72, 153),
        }
        if sv in named:
            r, g, b = named[sv]
            return 0x01000000 | (b << 16) | (g << 8) | r
        if sv.startswith("#"):
            hx = sv[1:]
            if len(hx) == 3:
                hx = "".join(c * 2 for c in hx)
            if len(hx) >= 6:
                try:
                    r = int(hx[0:2], 16)
                    g = int(hx[2:4], 16)
                    b = int(hx[4:6], 16)
                    return 0x01000000 | (b << 16) | (g << 8) | r
                except ValueError:
                    pass
        return 0

    def _extract_color_packed(self, call: ast.Call, *kw_names: str) -> Optional[int]:
        for kw in kw_names:
            node = self._extract_kwarg(call, kw)
            if node is None:
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                c = self._parse_color_literal(node.value)
                if c:
                    return (1 << 63) | ((c & 0xFFFFFFFF) << 32) | (c & 0xFFFFFFFF)
            elif isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) >= 2:
                e0, e1 = node.elts[0], node.elts[1]
                if (
                    isinstance(e0, ast.Constant) and isinstance(e0.value, str)
                    and isinstance(e1, ast.Constant) and isinstance(e1.value, str)
                ):
                    c0 = self._parse_color_literal(e0.value)
                    c1 = self._parse_color_literal(e1.value)
                    if c0 or c1:
                        return (1 << 63) | ((c1 & 0xFFFFFFFF) << 32) | (c0 & 0xFFFFFFFF)
        return None

    def _emit_post_widget_styling(
        self, call: ast.Call, allow_font: bool = True, allow_colors: bool = True, allow_sv: bool = True
    ) -> None:
        fg_node = self._extract_kwarg(call, "fg_color") or self._extract_kwarg(call, "bg") or self._extract_kwarg(call, "background")
        tc_node = self._extract_kwarg(call, "text_color") or self._extract_kwarg(call, "fg") or self._extract_kwarg(call, "foreground")
        fg_packed = self._extract_color_packed(call, "fg_color", "bg", "background")
        tc_packed = self._extract_color_packed(call, "text_color", "fg", "foreground")
        font_node = self._extract_kwarg(call, "font") if allow_font else None
        sv_node = (self._extract_kwarg(call, "textvariable") or self._extract_kwarg(call, "variable")) if allow_sv else None
        need_any = (
            (allow_colors and (fg_packed is not None or tc_packed is not None or fg_node is not None or tc_node is not None))
            or (font_node is not None)
            or (sv_node is not None)
        )
        if not need_any:
            return
        self.emit("sub rsp, 16", "save widget HWND across styling")
        self.emit("mov [rsp], rax")
        if allow_colors and (fg_packed is not None or tc_packed is not None or fg_node is not None or tc_node is not None):
            if fg_packed is not None:
                self.emit(f"mov rdx, 0x{fg_packed:016X}")
            elif fg_node is not None and not isinstance(fg_node, (ast.Tuple, ast.List)):
                self._generate_expr(fg_node)
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_parse_color")
                self.emit("add rsp, 32")
                self.emit("mov rdx, rax")
            else:
                self.emit("xor edx, edx")
            self.emit("push rdx", "temp fg color")
            if tc_packed is not None:
                self.emit(f"mov r8, 0x{tc_packed:016X}")
            elif tc_node is not None and not isinstance(tc_node, (ast.Tuple, ast.List)):
                self._generate_expr(tc_node)
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_parse_color")
                self.emit("add rsp, 32")
                self.emit("mov r8, rax")
            else:
                self.emit("xor r8d, r8d")
            self.emit("pop rdx")
            self.emit("mov rcx, [rsp]")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_widget_set_colors")
            self.emit("add rsp, 32")
        if font_node is not None:
            if isinstance(font_node, (ast.Tuple, ast.List)):
                fam_node = font_node.elts[0] if len(font_node.elts) >= 1 else None
                sz_val = font_node.elts[1].value if len(font_node.elts) >= 2 and isinstance(font_node.elts[1], ast.Constant) and isinstance(font_node.elts[1].value, int) else 13
                wt_str = " ".join(
                    str(e.value).lower() for e in font_node.elts[2:] if isinstance(e, ast.Constant) and isinstance(e.value, str)
                )
                is_bold = 1 if "bold" in wt_str else 0
                is_ital = 1 if "italic" in wt_str else 0
                if fam_node is not None:
                    self._generate_expr(fam_node)
                    self.emit("mov rcx, rax")
                else:
                    self.emit("xor ecx, ecx")
                self.emit(f"mov rdx, {sz_val}")
                self.emit(f"mov r8d, {is_bold}")
                self.emit(f"mov r9d, {is_ital}")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_create_font")
                self.emit("add rsp, 32")
            else:
                self._generate_expr(font_node)
            self.emit("mov rdx, rax", "HFONT handle")
            self.emit("mov rcx, [rsp]", "widget HWND")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_widget_set_font")
            self.emit("add rsp, 32")
        if sv_node is not None:
            self._generate_expr(sv_node)
            self.emit("mov rcx, rax", "StringVar ptr")
            self.emit("mov rdx, [rsp]", "widget HWND")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_stringvar_bind")
            self.emit("add rsp, 32")
        self.emit("mov rax, [rsp]")
        self.emit("add rsp, 16")

    def _extract_parent_container_node(self, call: ast.Call) -> Optional[ast.AST]:
        master_kw = self._extract_kwarg(call, "master")
        if master_kw is not None:
            return master_kw
        if call.args:
            first = call.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, (str, int, float, bool))):
                return first
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
        if part_type.is_complex():
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_complex_to_str")
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

    def _emit_win64_formatted_value(self, part: ast.FormattedValue) -> None:
        is_repr = getattr(part, "conversion", -1) == 114
        spec: Optional[str] = None
        fmt_spec = getattr(part, "format_spec", None)
        if (
            isinstance(fmt_spec, ast.JoinedStr)
            and len(fmt_spec.values) == 1
            and isinstance(fmt_spec.values[0], ast.Constant)
            and isinstance(fmt_spec.values[0].value, str)
        ):
            spec = fmt_spec.values[0].value

        if spec:
            m_float = re.fullmatch(r"([+ ])?(\d+)?(?:\.(\d+))?([fFeEgG])", spec)
            if m_float:
                sign_ch = m_float.group(1) or ""
                width = int(m_float.group(2)) if m_float.group(2) else 0
                prec = int(m_float.group(3)) if m_float.group(3) is not None else -1
                kind = m_float.group(4)
                part_type = self._infer_expr_type(part.value)
                self._generate_expr(part.value)
                if not part_type.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rcx, xmm0")
                else:
                    self.emit("mov rcx, rax")
                self.emit(f"mov rdx, {prec}")
                self.emit(f"mov r8d, {ord(kind)}")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_float_to_str_fmt")
                self.emit("add rsp, 32")
                if sign_ch:
                    lbl_pos_done = self.new_label("fmt_sign_ok")
                    self.emit("mov r10, rax")
                    self.emit("cmp byte [r10], 45")
                    self.emit(f"je {lbl_pos_done}")
                    self._emit_string_pointer("rcx", sign_ch)
                    self.emit("mov rdx, r10")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_str_concat")
                    self.emit("add rsp, 32")
                    self.emit_raw(f"{lbl_pos_done}:")
                if width > 0:
                    self.emit("mov rcx, rax")
                    self.emit(f"mov rdx, {width}")
                    self.emit("mov r8d, 32")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_str_pad_left")
                    self.emit("add rsp, 32")
                return

            m_int = re.fullmatch(r"(0)?(\d+)?([xXbod])", spec)
            if m_int:
                zero_pad = bool(m_int.group(1))
                width = int(m_int.group(2)) if m_int.group(2) else 0
                kind = m_int.group(3)
                base, upper = {"x": (16, 0), "X": (16, 1), "b": (2, 0), "o": (8, 0), "d": (10, 0)}[kind]
                self._generate_expr(part.value)
                self.emit("mov rcx, rax")
                if base == 10:
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_int_to_str")
                    self.emit("add rsp, 32")
                else:
                    self.emit(f"mov rdx, {base}")
                    self.emit(f"mov r8d, {upper}")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_int_to_base")
                    self.emit("add rsp, 32")
                if width > 0:
                    pad_ord = 48 if zero_pad else 32
                    self.emit("mov rcx, rax")
                    self.emit(f"mov rdx, {width}")
                    self.emit(f"mov r8d, {pad_ord}")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_str_pad_left")
                    self.emit("add rsp, 32")
                return

            m_width = re.fullmatch(r"(0)?(\d+)", spec)
            if m_width:
                zero_pad = bool(m_width.group(1))
                width = int(m_width.group(2))
                part_type = self._infer_expr_type(part.value)
                self._emit_win64_to_str(part.value, is_repr=is_repr)
                pad_ord = 48 if (zero_pad and not part_type.is_str()) else 32
                self.emit("mov rcx, rax")
                self.emit(f"mov rdx, {width}")
                self.emit(f"mov r8d, {pad_ord}")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_str_pad_left")
                self.emit("add rsp, 32")
                return

        self._emit_win64_to_str(part.value, is_repr=is_repr)

    def _generate_fstring_part(self, part: ast.AST) -> None:
        if isinstance(part, ast.Constant):
            self._emit_string_pointer("rax", str(part.value))
        elif isinstance(part, ast.FormattedValue):
            if self.target in ("win64", "dll"):
                self._emit_win64_formatted_value(part)
                return
            is_repr = getattr(part, "conversion", -1) == 114
            cls_name = self.resolve_instance_class(part.value)
            if is_repr:
                str_m = (
                    self.resolve_class_method(cls_name, "__repr__")
                    or self.resolve_class_method(cls_name, "__str__")
                ) if cls_name else None
            else:
                str_m = (
                    self.resolve_class_method(cls_name, "__str__")
                    or self.resolve_class_method(cls_name, "__repr__")
                ) if cls_name else None
            if str_m:
                self._generate_expr(part.value)
                self.emit("mov rcx, rax", "pass self to __str__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(cls_name, '__repr__' if is_repr else '__str__', str_m)}")
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

    def _parse_color_to_bgr(self, node: Optional[ast.AST]) -> Optional[int]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            raw = node.value.strip().lower()
            named = {
                "black": 0x000000,
                "white": 0xFFFFFF,
                "red": 0x0000FF,
                "green": 0x008000,
                "lime": 0x00FF00,
                "blue": 0xFF0000,
                "yellow": 0x00FFFF,
                "cyan": 0xFFFF00,
                "aqua": 0xFFFF00,
                "magenta": 0xFF00FF,
                "orange": 0x00A5FF,
                "purple": 0x800080,
                "gray": 0x808080,
                "grey": 0x808080,
            }
            if raw in named:
                return named[raw]
            if raw.startswith("#"):
                hx = raw[1:]
                if len(hx) == 3:
                    hx = "".join(c * 2 for c in hx)
                if len(hx) == 6:
                    try:
                        r = int(hx[0:2], 16)
                        g = int(hx[2:4], 16)
                        b = int(hx[4:6], 16)
                        return (b << 16) | (g << 8) | r
                    except ValueError:
                        return None
        return None

    def _emit_control_callback_to_rax(self, cmd_node: Optional[ast.AST]) -> bool:
        if cmd_node is None:
            return False
        if isinstance(cmd_node, ast.Attribute):
            attr = cmd_node.attr
            current_cls = getattr(self.current_func, "class_name", None)
            cand = f"{current_cls}_{attr}" if current_cls else attr
            cb_symbol = None
            if cand in self.module.functions:
                cb_symbol = cand
            elif attr in self.module.functions:
                cb_symbol = attr
            else:
                for fn_key in self.module.functions:
                    if fn_key.endswith(f"_{attr}"):
                        cb_symbol = fn_key
                        break
            if cb_symbol:
                self.emit(f"lea rax, [{safe_asm_label(cb_symbol)}]")
                return True
            return False
        if isinstance(cmd_node, ast.Name):
            if self.current_func and hasattr(self.current_func, "local_vars") and cmd_node.id in self.current_func.local_vars:
                self._generate_expr(cmd_node)
                return True
            if cmd_node.id in self.module.functions:
                self.emit(f"lea rax, [{safe_asm_label(cmd_node.id)}]")
                return True
            return False
        self._generate_expr(cmd_node)
        return True

    def _generate_button_control(self, call: ast.Call, target_name: str) -> None:
        btn_text = (
            self._get_kwarg_string_val(call, "text")
            or self._get_kwarg_string_val(call, "label")
        )
        if not btn_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                btn_text = first_arg.value
            elif len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                btn_text = call.args[1].value
        dyn_text_node = None
        if btn_text is None:
            cand = self._extract_kwarg(call, "text") or self._extract_kwarg(call, "label")
            if cand is None and call.args and self._infer_expr_type(call.args[0]).is_str():
                cand = call.args[0]
            if cand is not None:
                dyn_text_node = cand
            else:
                btn_text = "Button"

        cmd_node = self._extract_kwarg(call, "command") or self._extract_kwarg(call, "on_click")
        has_cb = self._emit_control_callback_to_rax(cmd_node)
        if has_cb:
            self.emit("push rax", "save button callback pointer")

        btn_id = self.gui_control_id
        self.gui_control_id += 1

        w = self._extract_kwarg_int(call, "width", 140)
        h = self._extract_kwarg_int(call, "height", 34)

        parent_node = self._extract_parent_container_node(call)
        if parent_node is not None:
            self._generate_expr(parent_node)
            self.emit("push rax", "parent container HWND")
        else:
            self.emit("push qword [_pyfasm_h_wnd]", "parent container HWND")

        if dyn_text_node is not None:
            self._generate_expr(dyn_text_node)
            self.emit("mov rcx, rax", "dynamic button text")
        else:
            self._emit_string_pointer("rcx", btn_text if btn_text is not None else "")

        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("pop r11", "parent HWND")
        if has_cb:
            self.emit("pop r10", "restore button callback pointer")
        self.emit("sub rsp, 80")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {btn_id}")
        if has_cb:
            self.emit("mov [rsp + 48], r10")
        else:
            self.emit("mov qword [rsp + 48], 0")
        self.emit("mov [rsp + 56], r11", "parent container HWND")
        self.emit("call _pyfasm_create_button")
        self.emit("add rsp, 80")
        self._emit_post_widget_styling(call)

    def _generate_checkbox_control(self, call: ast.Call, target_name: str) -> None:
        chk_text = (
            self._get_kwarg_string_val(call, "text")
            or self._get_kwarg_string_val(call, "label")
        )
        if not chk_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                chk_text = first_arg.value
            elif len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                chk_text = call.args[1].value
        if not chk_text:
            chk_text = "Checkbutton"

        cmd_node = (
            self._extract_kwarg(call, "command")
            or self._extract_kwarg(call, "on_change")
            or self._extract_kwarg(call, "on_click")
        )
        has_cb = self._emit_control_callback_to_rax(cmd_node)
        if has_cb:
            self.emit("push rax", "save checkbox callback pointer")

        chk_id = self.gui_control_id
        self.gui_control_id += 1

        w = self._extract_kwarg_int(call, "width", 220)
        h = self._extract_kwarg_int(call, "height", 30)

        parent_node = self._extract_parent_container_node(call)
        if parent_node is not None:
            self._generate_expr(parent_node)
            self.emit("push rax", "parent container HWND")
        else:
            self.emit("push qword [_pyfasm_h_wnd]", "parent container HWND")

        self._emit_string_pointer("rcx", chk_text)
        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("pop r11", "parent HWND")
        if has_cb:
            self.emit("pop r10", "restore checkbox callback pointer")
        self.emit("sub rsp, 80")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {chk_id}")
        if has_cb:
            self.emit("mov [rsp + 48], r10")
        else:
            self.emit("mov qword [rsp + 48], 0")
        self.emit("mov [rsp + 56], r11", "parent container HWND")
        self.emit("call _pyfasm_create_checkbox")
        self.emit("add rsp, 80")
        self._emit_post_widget_styling(call)

        val_node = self._extract_kwarg(call, "value")
        if val_node is not None:
            self.emit("push rax", "save checkbox hwnd")
            self._generate_expr(val_node)
            self.emit("mov rdx, rax", "initial checked state")
            self.emit("mov rcx, [rsp]", "checkbox hwnd")
            self.emit("sub rsp, 40")
            self.emit("call _pyfasm_checkbox_set")
            self.emit("add rsp, 40")
            self.emit("pop rax", "restore checkbox hwnd")

    def _generate_edit_control(self, call: ast.Call, target_name: str) -> None:
        edit_text = (
            self._get_kwarg_string_val(call, "placeholder_text")
            or self._get_kwarg_string_val(call, "label")
            or self._get_kwarg_string_val(call, "text")
            or self._get_kwarg_string_val(call, "value")
            or ""
        )
        if not edit_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                edit_text = first_arg.value
        edit_id = self.gui_edit_id
        self.gui_edit_id += 1

        w = self._extract_kwarg_int(call, "width", 200)
        h = self._extract_kwarg_int(call, "height", 34)

        parent_node = self._extract_parent_container_node(call)
        if parent_node is not None:
            self._generate_expr(parent_node)
            self.emit("push rax", "parent container HWND")
        else:
            self.emit("push qword [_pyfasm_h_wnd]", "parent container HWND")

        if edit_text:
            self._emit_string_pointer("rcx", edit_text)
        else:
            self.emit("xor ecx, ecx")
        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("pop r11", "parent HWND")
        self.emit("sub rsp, 80")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {edit_id}")
        self.emit("mov [rsp + 48], r11", "parent container HWND")
        self.emit("call _pyfasm_create_edit")
        self.emit("add rsp, 80")
        self._emit_post_widget_styling(call)

    def _generate_label_control(self, call: ast.Call, target_name: str) -> None:
        lbl_text = (
            self._get_kwarg_string_val(call, "text")
            or self._get_kwarg_string_val(call, "value")
        )
        if not lbl_text and call.args:
            first_arg = call.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                lbl_text = first_arg.value
            elif len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                lbl_text = call.args[1].value
        dyn_lbl_node = None
        if lbl_text is None:
            cand = self._extract_kwarg(call, "text") or self._extract_kwarg(call, "value")
            if cand is None and call.args and self._infer_expr_type(call.args[0]).is_str():
                cand = call.args[0]
            if cand is not None:
                dyn_lbl_node = cand
            else:
                lbl_text = "" if (self._extract_kwarg(call, "textvariable") is not None) else "Label"

        w = self._extract_kwarg_int(call, "width", 0)
        h = self._extract_kwarg_int(call, "height", 0)

        parent_node = self._extract_parent_container_node(call)
        if parent_node is not None:
            self._generate_expr(parent_node)
            self.emit("push rax", "parent container HWND")
        else:
            self.emit("push qword [_pyfasm_h_wnd]", "parent container HWND")

        if dyn_lbl_node is not None:
            self._generate_expr(dyn_lbl_node)
            self.emit("mov rcx, rax", "dynamic label text")
        else:
            self._emit_string_pointer("rcx", lbl_text if lbl_text is not None else "")
        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("pop r11", "parent HWND")
        self.emit("sub rsp, 64")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit("mov [rsp + 40], r11", "parent container HWND")
        self.emit("call _pyfasm_create_label")
        self.emit("add rsp, 64")
        self._emit_post_widget_styling(call)

    def _generate_listbox_control(self, call: ast.Call, target_name: str) -> None:
        w = self._extract_kwarg_int(call, "width", 450)
        h = self._extract_kwarg_int(call, "height", 240)
        list_id = 3001
        parent_node = self._extract_parent_container_node(call)
        if parent_node is not None:
            self._generate_expr(parent_node)
            self.emit("push rax", "parent container HWND")
        else:
            self.emit("push qword [_pyfasm_h_wnd]", "parent container HWND")
        self.emit("xor ecx, ecx")
        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("pop r11", "parent HWND")
        self.emit("sub rsp, 80")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {list_id}")
        self.emit("mov [rsp + 48], r11", "parent container HWND")
        self.emit("call _pyfasm_create_listbox")
        self.emit("add rsp, 80")
        self._emit_post_widget_styling(call, allow_sv=False)

    def _generate_textbox_control(self, call: ast.Call, target_name: str) -> None:
        w = self._extract_kwarg_int(call, "width", 350)
        h = self._extract_kwarg_int(call, "height", 190)
        edit_id = self.gui_edit_id
        self.gui_edit_id += 1
        parent_node = self._extract_parent_container_node(call)
        if parent_node is not None:
            self._generate_expr(parent_node)
            self.emit("push rax", "parent container HWND")
        else:
            self.emit("push qword [_pyfasm_h_wnd]", "parent container HWND")
        self.emit("xor ecx, ecx")
        self.emit("xor edx, edx", "auto layout X")
        self.emit("xor r8d, r8d", "auto layout Y")
        self.emit(f"mov r9, {w}")
        self.emit("pop r11", "parent HWND")
        self.emit("sub rsp, 80")
        self.emit(f"mov qword [rsp + 32], {h}")
        self.emit(f"mov qword [rsp + 40], {edit_id}")
        self.emit("mov [rsp + 48], r11", "parent container HWND")
        self.emit("call _pyfasm_create_textbox")
        self.emit("add rsp, 80")
        self._emit_post_widget_styling(call, allow_sv=False)

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

        # Prepare dynamic attribute table entries BEFORE emitting string_literals
        attr_rows: List[Tuple[int, str, int]] = []
        attr_offsets = getattr(self, "_attr_offsets", {})
        for cname, cid in sorted(self._class_ids.items(), key=lambda kv: kv[1]):
            c_attrs: Set[str] = set()
            seen_c: Set[str] = set()
            q = [cname]
            while q:
                cn = q.pop(0)
                if cn in seen_c:
                    continue
                seen_c.add(cn)
                c_attrs.update(self._class_written_attrs.get(cn, ()))
                cs = self.module.classes.get(cn)
                if cs:
                    c_attrs.update(getattr(cs, "fields", ()))
                    c_attrs.update(getattr(cs, "field_types", {}).keys())
                    c_attrs.update(getattr(cs, "class_attrs", {}).keys())
                    c_attrs.update(getattr(cs, "properties", {}).keys())
                    q.extend(getattr(cs, "bases", ()))
            for aname in sorted(c_attrs):
                off = self._get_attribute_offset(aname)
                slbl = self.get_or_create_string(aname)
                attr_rows.append((cid, slbl, off))
        for aname, off in sorted(attr_offsets.items()):
            slbl = self.get_or_create_string(aname)
            attr_rows.append((-1, slbl, off))

        # Emit user string literals
        for slit in self.module.string_literals:
            escaped_bytes = [str(b) for b in slit.value.encode("utf-8")]
            escaped_bytes.append("0")  # null terminator
            bytes_str = ", ".join(escaped_bytes)
            lines.append(f"    {slit.label} db {bytes_str} ; {repr(slit.value)}")

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
        lines.append("    align 8")
        lines.append("    _pyfasm_attr_table:")
        for cid_val, slbl, off_val in attr_rows:
            lines.append(f"        dq {cid_val}, {slbl}, {off_val}")
        lines.append("        dq 0, 0, 0")
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
            lines.append("    lea rax, [_pyfasm_attr_table]")
            lines.append("    mov [_pyfasm_attr_table_ptr], rax")

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
                    if sym not in BUILTIN_EXCEPTIONS_AND_SYMBOLS and sym not in getattr(self.module, "imports", []) and sym not in getattr(self.module, "imported_modules", {}):
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
        header = self._get_runtime_header()
        entry = self._get_entry_point()
        funcs = self._get_functions_section()
        data = self._get_data_section()
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

        # Check if Background System Tray Application (pystray / tray)
        module_imports = getattr(self.module, "imports", [])
        is_tray = any(
            any(k in s.lower() for k in ("tray", "pystray"))
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
        elif is_gui and self.target in ("win64", "dll", "linux", "macos", "apple", "myos"):
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
        self._np_array_vars = set()
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
            # Track variables assigned from NumPy arrays
            if self._is_np_array_expr(stmt.value):
                for _t in stmt.targets:
                    if isinstance(_t, ast.Name):
                        self._np_array_vars.add(_t.id)
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
            if isinstance(stmt.value, ast.Call):
                call_txt = ast.dump(stmt.value.func).lower()
                if "checkbox" in call_txt or "checkbutton" in call_txt:
                    if not hasattr(self, "_checkbox_var_names"):
                        self._checkbox_var_names = set()
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            self._checkbox_var_names.add(target.id)
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
                        recv_t = self._infer_expr_type(target.value)
                        if (
                            isinstance(slice_unwrapped, ast.Tuple)
                            and len(slice_unwrapped.elts) == 2
                            and recv_t.is_list()
                            and not any(isinstance(e, ast.Slice) for e in slice_unwrapped.elts)
                        ):
                            target = ast.Subscript(
                                value=ast.Subscript(
                                    value=target.value,
                                    slice=slice_unwrapped.elts[0],
                                    ctx=ast.Load(),
                                ),
                                slice=slice_unwrapped.elts[1],
                                ctx=ast.Store(),
                            )
                            slice_unwrapped = _unwrap_slice(target.slice)
                        else:
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

                    if is_dict_target and not isinstance(slice_unwrapped, ast.Slice):
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
                    elif isinstance(slice_unwrapped, ast.Slice):
                        # arr[:] = rhs
                        self.emit("push rax", "save rhs sequence")
                        self._generate_expr(target.value)
                        self.emit("mov rcx, rax", "dest list")
                        self.emit("pop rdx", "src list")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit("call _pyfasm_list_slice_assign")
                        self.emit("add rsp, 32")
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
                    if (
                        self.target in ("win64", "dll")
                        and "gui" in self.features
                        and self.resolve_instance_class(target.value) is None
                        and not (isinstance(target.value, ast.Name) and target.value.id in ("self", "this"))
                    ):
                        if target.attr == "title":
                            self.emit("mov rcx, rax", "new window title")
                            self.emit("sub rsp, 32", "shadow space")
                            self.emit("call _pyfasm_set_window_title")
                            self.emit("add rsp, 32")
                            continue
                        if target.attr in ("value", "text") and self.module.has_library("flet"):
                            is_chk = (
                                isinstance(target.value, ast.Name)
                                and target.value.id in getattr(self, "_checkbox_var_names", set())
                            )
                            self.emit("push rax", "save new flet control value")
                            self._generate_expr(target.value)
                            self.emit("mov rcx, rax", "flet control HWND")
                            self.emit("pop rdx", "new value")
                            self.emit("sub rsp, 32", "shadow space")
                            self.emit(f"call {'_pyfasm_checkbox_set' if is_chk else '_pyfasm_unified_set'}")
                            self.emit("add rsp, 32")
                            continue
                        if target.attr in ("window_width", "window_height") and self.module.has_library("flet"):
                            self.emit("mov rcx, [_pyfasm_h_wnd]")
                            self.emit("mov rdx, rax", "dimension")
                            self.emit("sub rsp, 32")
                            self.emit("call _pyfasm_resize_window")
                            self.emit("add rsp, 32")
                            continue
                        if target.attr in ("theme_mode", "bgcolor", "padding", "horizontal_alignment", "vertical_alignment", "scroll") and self.module.has_library("flet"):
                            continue

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
                            self._record_class_attr(self.resolve_instance_class(target.value), target.attr)
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
                if isinstance(stmt.target, ast.Name):
                    assigned_cls = self.resolve_instance_class(stmt.value)
                    if assigned_cls:
                        self.local_var_classes[stmt.target.id] = assigned_cls
                equiv_assign = ast.Assign(targets=[stmt.target], value=stmt.value)
                self._generate_statement(equiv_assign)

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
                if isinstance(sub_slice, ast.Tuple) and len(sub_slice.elts) == 2 and not any(isinstance(e, ast.Slice) for e in sub_slice.elts):
                    elem1 = getattr(val_type, "element_type", None)
                    if elem1 and elem1.is_list() and getattr(elem1, "element_type", None):
                        return elem1.element_type
                    return TYPE_INT
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
            rbinop_dunders = {
                ast.Add: "__radd__", ast.Sub: "__rsub__", ast.Mult: "__rmul__",
                ast.FloorDiv: "__rfloordiv__", ast.Div: "__rtruediv__", ast.Mod: "__rmod__",
            }
            if type(expr.op) in binop_dunders:
                lcls = self.resolve_instance_class(expr.left)
                op_m = self.resolve_class_method(lcls, binop_dunders[type(expr.op)]) if lcls else None
                if op_m and op_m in self.module.functions and self.module.functions[op_m].return_type != TYPE_VOID:
                    return self.module.functions[op_m].return_type
                if not op_m and type(expr.op) in rbinop_dunders:
                    rcls = self.resolve_instance_class(expr.right)
                    rop_m = self.resolve_class_method(rcls, rbinop_dunders[type(expr.op)]) if rcls else None
                    if rop_m and rop_m in self.module.functions and self.module.functions[rop_m].return_type != TYPE_VOID:
                        return self.module.functions[rop_m].return_type
            lt = self._infer_expr_type(expr.left)
            rt = self._infer_expr_type(expr.right)
            if lt.is_complex() or rt.is_complex():
                return TYPE_COMPLEX
            if isinstance(expr.op, ast.Mult) and (
                (lt.is_list() and getattr(lt, "element_type", None) != TYPE_FLOAT and not rt.is_float())
                or (rt.is_list() and getattr(rt, "element_type", None) != TYPE_FLOAT and not lt.is_float())
                or isinstance(expr.left, (ast.List, ast.Tuple))
                or isinstance(expr.right, (ast.List, ast.Tuple))
            ):
                if (lt.is_list() or lt.is_tuple() or isinstance(expr.left, (ast.List, ast.Tuple))) and not (lt.is_list() and getattr(lt, "element_type", None) == TYPE_FLOAT and not isinstance(expr.left, ast.List)):
                    return lt
                if rt.is_list() or rt.is_tuple() or isinstance(expr.right, (ast.List, ast.Tuple)):
                    return rt
            if lt.is_list() or rt.is_list():
                lt_elem = getattr(lt, "element_type", None) if lt.is_list() else (TYPE_FLOAT if lt.is_float() else None)
                rt_elem = getattr(rt, "element_type", None) if rt.is_list() else (TYPE_FLOAT if rt.is_float() else None)
                merged = self._merge_expr_element_types([t for t in (lt_elem, rt_elem) if t is not None])
                return ListType(element_type=merged) if merged else TYPE_LIST
            if isinstance(expr.op, ast.Add) and (lt.is_tuple() or rt.is_tuple()):
                return lt if lt.is_tuple() else rt
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
                if ot.is_complex():
                    return TYPE_COMPLEX
                if ot.is_list():
                    return ot
                if ot.is_float():
                    return TYPE_FLOAT
        if isinstance(expr, ast.JoinedStr):
            return TYPE_STR
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                fn_id = expr.func.id
                if fn_id in ("str", "repr", "chr", "input", "strip", "lower", "upper", "hex", "bin", "oct", "get_simd_isa"):
                    return TYPE_STR
                if fn_id in ("alloc_memory", "malloc", "VirtualAlloc", "calloc"):
                    return TYPE_PTR
                if fn_id in ("round",):
                    return TYPE_FLOAT if len(expr.args) >= 2 else TYPE_INT
                if fn_id in ("float",):
                    return TYPE_FLOAT
                if fn_id in ("complex",):
                    return TYPE_COMPLEX
                if fn_id in ("sin", "cos", "tan", "atan2", "exp", "log", "log10", "hypot", "sqrt"):
                    if len(expr.args) >= 1 and self._infer_expr_type(expr.args[0]).is_complex():
                        return TYPE_COMPLEX
                    return TYPE_FLOAT
                if fn_id == "pow":
                    if any(self._infer_expr_type(a).is_complex() for a in expr.args):
                        return TYPE_COMPLEX
                    if any(self._infer_expr_type(a).is_float() for a in expr.args):
                        return TYPE_FLOAT
                    return TYPE_INT
                if fn_id in ("isfinite", "isnan", "isinf", "isclose", "bool", "isinstance", "issubclass", "hasattr", "any", "all", "isdigit", "isascii"):
                    return TYPE_BOOL
                if fn_id == "getattr" and len(expr.args) >= 2:
                    if isinstance(expr.args[1], ast.Constant) and isinstance(expr.args[1].value, str):
                        ocls = self.resolve_instance_class(expr.args[0])
                        if ocls and ocls in self.module.classes:
                            cs = self.module.classes[ocls]
                            if expr.args[1].value in getattr(cs, "field_types", {}):
                                return cs.field_types[expr.args[1].value]
                    if len(expr.args) >= 3:
                        return self._infer_expr_type(expr.args[2])
                    return TYPE_INT
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
                if fn_id in ("sumprod", "math_sumprod", "cpu_count", "process_cpu_count"):
                    return TYPE_INT
                if fn_id in ("filter", "zip", "enumerate", "chain", "accumulate", "batched", "matmul", "zeros", "ones", "array", "asarray", "arange", "pairwise"):
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
                if fn_id == "abs" and expr.args:
                    acls = self.resolve_instance_class(expr.args[0])
                    am = self.resolve_class_method(acls, "__abs__") if acls else None
                    if am and am in self.module.functions and self.module.functions[am].return_type != TYPE_VOID:
                        return self.module.functions[am].return_type
                    if self._infer_expr_type(expr.args[0]).is_complex():
                        return TYPE_FLOAT
                    if self._infer_expr_type(expr.args[0]).is_float():
                        return TYPE_FLOAT
                    return TYPE_INT
                if fn_id in ("min", "max"):
                    if len(expr.args) >= 2 and any(self._infer_expr_type(a).is_float() for a in expr.args):
                        return TYPE_FLOAT
                    if len(expr.args) == 1:
                        a0t = self._infer_expr_type(expr.args[0])
                        if getattr(a0t, "element_type", None) and a0t.element_type.is_float():
                            return TYPE_FLOAT
                if self.current_func and hasattr(self.current_func, "local_vars") and fn_id in self.current_func.local_vars:
                    alias_fn = getattr(self.current_func.local_vars[fn_id], "fn_alias", None)
                    if alias_fn and alias_fn in self.module.functions and self.module.functions[alias_fn].return_type != TYPE_VOID:
                        return self.module.functions[alias_fn].return_type
                if fn_id in self.module.functions:
                    return self.module.functions[fn_id].return_type
            elif isinstance(expr.func, ast.Attribute):
                attr = expr.func.attr
                if attr in ("split", "splitlines"):
                    return ListType(element_type=TYPE_STR)
                if attr in ("text", "toPlainText") and self.module.has_library("pyqt5", "pyqt6", "pyside6", "pyside2", "qt", "tkinter", "customtkinter"):
                    return TYPE_STR
                mod_recv = expr.func.value.id if isinstance(expr.func.value, ast.Name) else ""
                if attr in ("isChecked", "colliderect", "collidepoint"):
                    return TYPE_BOOL
                if mod_recv in ("np", "numpy", "math", "cmath"):
                    if attr in ("isfinite", "isnan", "isinf", "isclose", "all", "any"):
                        return TYPE_BOOL
                    if attr in ("linspace", "arange", "empty", "zeros", "ones", "array", "asarray", "asanyarray", "sign"):
                        if attr == "sign" and expr.args and not self._infer_expr_type(expr.args[0]).is_list():
                            return TYPE_FLOAT
                        if attr in ("zeros", "ones", "empty") and expr.args and isinstance(expr.args[0], (ast.Tuple, ast.List)) and len(expr.args[0].elts) >= 2:
                            return ListType(element_type=ListType(element_type=TYPE_FLOAT))
                        return ListType(element_type=TYPE_FLOAT)
                    if attr == "column_stack":
                        return ListType(element_type=ListType(element_type=TYPE_FLOAT))
                    if attr in ("sin", "cos", "tan", "exp", "log", "log10"):
                        if expr.args and self._infer_expr_type(expr.args[0]).is_list():
                            return ListType(element_type=TYPE_FLOAT)
                        return TYPE_FLOAT
                    if attr in ("ptp", "mean", "sum", "atan2", "hypot", "min", "max", "amin", "amax", "pow"):
                        return TYPE_FLOAT
                    if attr == "sqrt":
                        if mod_recv == "cmath":
                            return TYPE_COMPLEX
                        if expr.args and self._infer_expr_type(expr.args[0]).is_list():
                            return ListType(element_type=TYPE_FLOAT)
                        return TYPE_FLOAT
                if attr in ("get_pressed", "get") and isinstance(expr.func.value, ast.Attribute) and getattr(expr.func.value, "attr", None) in ("event", "key"):
                    return TYPE_LIST
                if attr == "get_pos" and isinstance(expr.func.value, ast.Attribute) and getattr(expr.func.value, "attr", None) == "mouse":
                    return TYPE_TUPLE
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
            if isinstance(expr.value, ast.Name) and expr.value.id == "sys":
                if expr.attr in ("version", "platform", "byteorder"):
                    return TYPE_STR
                if expr.attr in ("maxsize", "hexversion"):
                    return TYPE_INT
                if expr.attr == "version_info":
                    return TupleType(element_types=(TYPE_INT, TYPE_INT, TYPE_INT, TYPE_STR, TYPE_INT))
                if expr.attr == "argv":
                    return ListType(element_type=TYPE_STR)
            if (
                isinstance(expr.value, ast.Attribute)
                and expr.value.attr == "version_info"
                and isinstance(expr.value.value, ast.Name)
                and expr.value.value.id == "sys"
            ):
                if expr.attr in ("major", "minor", "micro"):
                    return TYPE_INT
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
            if (
                isinstance(expr.value, ast.Name)
                and expr.value.id in ("math", "cmath", "np", "numpy")
                and expr.attr in ("pi", "e", "tau", "inf", "nan")
            ):
                return TYPE_FLOAT
            if expr.attr in ("real", "imag"):
                return TYPE_FLOAT
            if expr.attr == "value" and self.module.has_library("flet") and not self.resolve_instance_class(expr.value):
                return TYPE_STR
            if expr.attr in ("right", "bottom", "centerx", "centery", "x", "y", "w", "h", "width", "height", "left", "top", "type", "key"):
                return TYPE_INT
            if any(k in expr.attr.lower() for k in ("dict", "map", "vars", "entries", "table", "cache", "lookup", "modules", "headers", "params", "environ", "cookies", "meta", "registry", "mapping", "config", "state")):
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
            elif "pygame" in self.features and self._pygame_const_value(expr.id) is not None:
                self.emit(f"mov rax, {self._pygame_const_value(expr.id)}", f"pygame constant {expr.id}")
            elif expr.id in BUILTIN_EXCEPTIONS_AND_SYMBOLS or expr.id in getattr(self.module, "imports", []) or expr.id in getattr(self.module, "imported_modules", {}):
                self.emit("xor eax, eax", f"builtin/module reference {expr.id}")
            else:
                self._record_unresolved(expr.id, expr)
                self.emit(f"lea rax, [{safe_asm_label(expr.id)}]", f"address of {expr.id}")

        elif isinstance(expr, ast.Attribute):
            if (
                isinstance(expr.value, ast.Attribute)
                and expr.value.attr == "version_info"
                and isinstance(expr.value.value, ast.Name)
                and expr.value.value.id == "sys"
            ):
                if expr.attr == "major":
                    self.emit(f"mov rax, {self.py_version[0]}", "sys.version_info.major")
                    return
                elif expr.attr == "minor":
                    self.emit(f"mov rax, {self.py_version[1]}", "sys.version_info.minor")
                    return
                elif expr.attr == "micro":
                    self.emit(f"mov rax, {self.py_micro}", "sys.version_info.micro")
                    return

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
                        if mod_name == "sys":
                            if expr.attr == "version":
                                v_str = f"{self.py_version[0]}.{self.py_version[1]}.{self.py_micro} (PyFASM Native x86-64 AOT, Python {self.py_version[0]}.{self.py_version[1]} compatible)"
                                lbl = self.get_or_create_string(v_str)
                                self.emit(f"lea rax, [{lbl}]", "load sys.version")
                                val_handled = True
                            elif expr.attr == "version_info":
                                lbl_final = self.get_or_create_string("final")
                                self.emit("mov ecx, 5", "tuple len 5")
                                self.emit("call _pyfasm_list_create")
                                self.emit(f"mov qword [rax + 8], {self.py_version[0]}", "major")
                                self.emit(f"mov qword [rax + 16], {self.py_version[1]}", "minor")
                                self.emit(f"mov qword [rax + 24], {self.py_micro}", "micro")
                                self.emit(f"lea rdx, [{lbl_final}]")
                                self.emit("mov [rax + 32], rdx", "releaselevel 'final'")
                                self.emit("mov qword [rax + 40], 0", "serial 0")
                                val_handled = True
                            elif expr.attr == "platform":
                                plat_str = "win32" if self.target in ("win64", "dll") else ("darwin" if self.target in ("macos", "apple") else "linux")
                                lbl = self.get_or_create_string(plat_str)
                                self.emit(f"lea rax, [{lbl}]", f"sys.platform -> {plat_str}")
                                val_handled = True
                            elif expr.attr == "byteorder":
                                lbl = self.get_or_create_string("little")
                                self.emit(f"lea rax, [{lbl}]", "sys.byteorder -> little")
                                val_handled = True
                            elif expr.attr == "maxsize":
                                self.emit("mov rax, 9223372036854775807", "sys.maxsize (int64 max)")
                                val_handled = True
                            elif expr.attr == "hexversion":
                                hexv = (self.py_version[0] << 24) | (self.py_version[1] << 16) | (self.py_micro << 8) | 0xF0
                                self.emit(f"mov rax, {hexv}", f"sys.hexversion -> 0x{hexv:08X}")
                                val_handled = True
                            elif expr.attr == "argv":
                                lbl_app = self.get_or_create_string("app.exe")
                                self.emit("mov ecx, 1")
                                self.emit("call _pyfasm_list_create")
                                self.emit(f"lea rdx, [{lbl_app}]")
                                self.emit("mov [rax + 8], rdx")
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
                if not val_handled and "pygame" in self.features:
                    pg_val = self._pygame_const_value(expr.attr)
                    if pg_val is not None:
                        self.emit(f"mov rax, {pg_val}", f"pygame constant {expr.attr}")
                        val_handled = True
                if not val_handled:
                    math_consts = {
                        "pi": 3.141592653589793,
                        "e": 2.718281828459045,
                        "tau": 6.283185307179586,
                        "inf": float("inf"),
                        "nan": float("nan"),
                    }
                    if (
                        isinstance(expr.value, ast.Name)
                        and expr.value.id in ("math", "cmath", "np", "numpy")
                        and expr.attr in math_consts
                    ):
                        self._emit_float_bits("rax", math_consts[expr.attr])
                        return
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
                if (
                    isinstance(expr.value, ast.Attribute)
                    and expr.value.attr == "version_info"
                    and isinstance(expr.value.value, ast.Name)
                    and expr.value.value.id == "sys"
                ):
                    if expr.attr == "major":
                        self.emit(f"mov rax, {self.py_version[0]}", "sys.version_info.major")
                        return
                    elif expr.attr == "minor":
                        self.emit(f"mov rax, {self.py_version[1]}", "sys.version_info.minor")
                        return
                    elif expr.attr == "micro":
                        self.emit(f"mov rax, {self.py_micro}", "sys.version_info.micro")
                        return
                if expr.attr == "real":
                    vt = self._infer_expr_type(expr.value)
                    self._generate_expr(expr.value)
                    if not vt.is_float():
                        self.emit("mov rcx, rax")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit("call _pyfasm_complex_real")
                        self.emit("add rsp, 32")
                    return
                if expr.attr == "imag":
                    vt = self._infer_expr_type(expr.value)
                    if vt.is_float():
                        self.emit("xor eax, eax")
                    else:
                        self._generate_expr(expr.value)
                        self.emit("mov rcx, rax")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit("call _pyfasm_complex_imag")
                        self.emit("add rsp, 32")
                    return
                if (
                    self.target in ("win64", "dll")
                    and expr.attr == "control"
                    and self.module.has_library("flet")
                ):
                    self._generate_expr(expr.value)
                    return
                if (
                    self.target in ("win64", "dll")
                    and expr.attr in ("value", "text")
                    and self.module.has_library("flet")
                    and self.resolve_instance_class(expr.value) is None
                    and not (isinstance(expr.value, ast.Name) and expr.value.id in ("self", "this"))
                ):
                    is_chk = (
                        isinstance(expr.value, ast.Name)
                        and expr.value.id in getattr(self, "_checkbox_var_names", set())
                    )
                    self._generate_expr(expr.value)
                    self.emit("mov rcx, rax", "flet control HWND")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit(f"call {'_pyfasm_checkbox_get' if is_chk else '_pyfasm_unified_get'}")
                    self.emit("add rsp, 32")
                    return
                if (
                    "pygame" in self.features
                    and expr.attr in ("right", "bottom", "centerx", "centery", "center", "topleft", "topright", "bottomleft", "bottomright")
                    and self.resolve_instance_class(expr.value) is None
                ):
                    self._generate_expr(expr.value)
                    self.emit("mov r8, rax", "pygame Rect pointer")
                    lbl_null_r = self.new_label("null_rect")
                    lbl_done_r = self.new_label("done_rect")
                    self.emit("test r8, r8")
                    self.emit(f"jz {lbl_null_r}")
                    if expr.attr in ("center", "topleft", "topright", "bottomleft", "bottomright"):
                        self.emit("sub rsp, 48", "aligned frame + preserve rect ptr")
                        self.emit("mov [rsp + 32], r8")
                        self.emit("mov ecx, 32")
                        self.emit("call _pyfasm_alloc")
                        self.emit("mov r8, [rsp + 32]")
                        self.emit("add rsp, 48")
                        self.emit("mov qword [rax], 2", "2-tuple")
                        if expr.attr == "center":
                            self.emit("mov r9, [r8 + 64]")
                            self.emit("sar r9, 1")
                            self.emit("add r9, [r8 + 48]")
                            self.emit("mov [rax + 8], r9")
                            self.emit("mov r9, [r8 + 72]")
                            self.emit("sar r9, 1")
                            self.emit("add r9, [r8 + 56]")
                            self.emit("mov [rax + 16], r9")
                        elif expr.attr == "topleft":
                            self.emit("mov r9, [r8 + 48]")
                            self.emit("mov [rax + 8], r9")
                            self.emit("mov r9, [r8 + 56]")
                            self.emit("mov [rax + 16], r9")
                        elif expr.attr == "topright":
                            self.emit("mov r9, [r8 + 48]")
                            self.emit("add r9, [r8 + 64]")
                            self.emit("mov [rax + 8], r9")
                            self.emit("mov r9, [r8 + 56]")
                            self.emit("mov [rax + 16], r9")
                        elif expr.attr == "bottomleft":
                            self.emit("mov r9, [r8 + 48]")
                            self.emit("mov [rax + 8], r9")
                            self.emit("mov r9, [r8 + 56]")
                            self.emit("add r9, [r8 + 72]")
                            self.emit("mov [rax + 16], r9")
                        else:  # bottomright
                            self.emit("mov r9, [r8 + 48]")
                            self.emit("add r9, [r8 + 64]")
                            self.emit("mov [rax + 8], r9")
                            self.emit("mov r9, [r8 + 56]")
                            self.emit("add r9, [r8 + 72]")
                            self.emit("mov [rax + 16], r9")
                    elif expr.attr == "right":
                        self.emit("mov rax, [r8 + 48]", "rect.x")
                        self.emit("add rax, [r8 + 64]", "+ rect.w")
                    elif expr.attr == "bottom":
                        self.emit("mov rax, [r8 + 56]", "rect.y")
                        self.emit("add rax, [r8 + 72]", "+ rect.h")
                    elif expr.attr == "centerx":
                        self.emit("mov rax, [r8 + 64]", "rect.w")
                        self.emit("sar rax, 1", "w // 2")
                        self.emit("add rax, [r8 + 48]", "+ rect.x")
                    else:
                        self.emit("mov rax, [r8 + 72]", "rect.h")
                        self.emit("sar rax, 1", "h // 2")
                        self.emit("add rax, [r8 + 56]", "+ rect.y")
                    self.emit(f"jmp {lbl_done_r}")
                    self.emit_raw(f"{lbl_null_r}:")
                    self.emit("xor eax, eax")
                    self.emit_raw(f"{lbl_done_r}:")
                    return

                if (
                    "matplotlib" in self.features
                    and expr.attr in ("patch", "spines")
                    and self.resolve_instance_class(expr.value) is None
                ):
                    self._generate_expr(expr.value)
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
                rdunder_map = {
                    ast.Add: "__radd__",
                    ast.Sub: "__rsub__",
                    ast.Mult: "__rmul__",
                    ast.FloorDiv: "__rfloordiv__",
                    ast.Div: "__rtruediv__",
                    ast.Mod: "__rmod__",
                }
                if op_cls in rdunder_map:
                    r_cls = self.resolve_instance_class(expr.right)
                    r_m = self.resolve_class_method(r_cls, rdunder_map[op_cls]) if r_cls else None
                    if r_m:
                        self._generate_expr(expr.left)
                        self.emit("push rax", "save left as other")
                        self._generate_expr(expr.right)
                        self.emit("mov rcx, rax", "pass right as self")
                        self.emit("pop rdx", "pass left as other")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit(f"call {self._method_call_target(r_cls, rdunder_map[op_cls], r_m)}")
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

            # Complex arithmetic (+, -, *, /)
            if (lt.is_complex() or rt.is_complex()) and isinstance(expr.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                c_fn = {
                    ast.Add: "_pyfasm_complex_add",
                    ast.Sub: "_pyfasm_complex_sub",
                    ast.Mult: "_pyfasm_complex_mul",
                    ast.Div: "_pyfasm_complex_div",
                }[type(expr.op)]
                self._generate_expr(expr.left)
                if not lt.is_complex() and not lt.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("push rax")
                self._generate_expr(expr.right)
                if not rt.is_complex() and not rt.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov rdx, rax")
                self.emit("pop rcx")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {c_fn}")
                self.emit("add rsp, 32")
                return

            # Vectorized NumPy array arithmetic (+, -, *, /, **)
            is_np_l = self._is_np_array_expr(expr.left)
            is_np_r = self._is_np_array_expr(expr.right)
            is_flt_l = lt.is_list() and getattr(lt, "element_type", None) == TYPE_FLOAT and not isinstance(expr.left, ast.List)
            is_flt_r = rt.is_list() and getattr(rt, "element_type", None) == TYPE_FLOAT and not isinstance(expr.right, ast.List)
            should_vec = False
            if isinstance(expr.op, (ast.Sub, ast.Div, ast.Pow)) and (lt.is_list() or rt.is_list()):
                should_vec = True
            elif isinstance(expr.op, ast.Mult) and (
                (is_flt_l and (rt.is_float() or rt.is_list()))
                or (is_flt_r and (lt.is_float() or lt.is_list()))
                or (is_np_l or is_np_r)
            ):
                should_vec = True
            elif isinstance(expr.op, ast.Add) and (
                (is_flt_l and not rt.is_list())
                or (is_flt_r and not lt.is_list())
                or ((is_np_l or is_np_r) and is_flt_l and is_flt_r)
            ):
                should_vec = True

            if should_vec and isinstance(expr.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                op_code = {ast.Add: 0, ast.Sub: 1, ast.Mult: 2, ast.Div: 3, ast.Pow: 4}[type(expr.op)]
                flags = (1 if lt.is_list() else 0) | (2 if rt.is_list() else 0)
                self._generate_expr(expr.left)
                if not lt.is_list() and not lt.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("push rax")
                self._generate_expr(expr.right)
                if not rt.is_list() and not rt.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov rdx, rax")
                self.emit("pop rcx")
                self.emit(f"mov r8d, {op_code}")
                self.emit(f"mov r9d, {flags}")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_vec_op")
                self.emit("add rsp, 32")
                return

            # List repetition (Mult) or concatenation (Add)
            is_left_list = lt.is_list() or lt.is_tuple() or isinstance(expr.left, (ast.List, ast.Tuple))
            is_right_list = rt.is_list() or rt.is_tuple() or isinstance(expr.right, (ast.List, ast.Tuple))
            if isinstance(expr.op, ast.Mult) and (is_left_list or is_right_list) and not (lt.is_float() or rt.is_float()):
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

            if isinstance(expr.op, ast.Add) and (is_left_list and is_right_list):
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
                if t.is_complex():
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_complex_neg")
                    self.emit("add rsp, 32")
                elif t.is_list() and getattr(t, "element_type", None) == TYPE_FLOAT:
                    self.emit("mov rcx, rax")
                    self._emit_float_bits("rdx", -1.0)
                    self.emit("mov r8d, 2")
                    self.emit("mov r9d, 1")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_np_vec_op")
                    self.emit("add rsp, 32")
                elif t.is_float():
                    self.emit("movq xmm0, rax")
                    self.emit("xorpd xmm1, xmm1")
                    self.emit("subsd xmm1, xmm0")
                    self.emit("movq rax, xmm1")
                else:
                    self.emit("neg rax")
            elif isinstance(expr.op, ast.Invert):
                self.emit("not rax")

        elif isinstance(expr, ast.Starred):
            self._generate_expr(expr.value)

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

            if (
                "matplotlib" in self.features
                and isinstance(expr.value, ast.Attribute)
                and expr.value.attr == "spines"
                and self.resolve_instance_class(expr.value.value) is None
            ):
                self._generate_expr(expr.value.value)
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
                recv_t = self._infer_expr_type(expr.value)
                if (
                    isinstance(slice_unwrapped, ast.Tuple)
                    and len(slice_unwrapped.elts) == 2
                    and recv_t.is_list()
                    and not any(isinstance(e, ast.Slice) for e in slice_unwrapped.elts)
                ):
                    row_sub = ast.Subscript(value=expr.value, slice=slice_unwrapped.elts[0], ctx=ast.Load())
                    full_sub = ast.Subscript(value=row_sub, slice=slice_unwrapped.elts[1], ctx=ast.Load())
                    self._generate_expr(full_sub)
                    return
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

        elif isinstance(expr, (ast.Tuple, ast.List)):
            if any(isinstance(e, ast.Starred) for e in expr.elts):
                cap = max(64, len(expr.elts) * 8)
                self.emit(f"mov ecx, {cap}", "allocate dynamic seq for starred literal")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_list_create")
                self.emit("add rsp, 32")
                self.emit("sub rsp, 16")
                self.emit("mov [rsp], rax")
                for elt in expr.elts:
                    if isinstance(elt, ast.Starred):
                        if self._is_generator_expr(elt.value):
                            self._generate_expr(elt.value)
                            self.emit("mov rcx, rax")
                            self.emit("sub rsp, 32")
                            self.emit("call _pyfasm_gen_to_list")
                            self.emit("add rsp, 32")
                        else:
                            self._generate_expr(elt.value)
                        self.emit("mov rdx, rax")
                        self.emit("mov rcx, [rsp]")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_list_extend")
                        self.emit("add rsp, 32")
                    else:
                        self._generate_expr(elt)
                        self.emit("mov rdx, rax")
                        self.emit("mov rcx, [rsp]")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_list_append")
                        self.emit("add rsp, 32")
                self.emit("mov rax, [rsp]")
                self.emit("add rsp, 16")
            else:
                num_elts = len(expr.elts)
                if isinstance(expr, ast.Tuple):
                    alloc_bytes = max(16, (num_elts + 2) * 8)
                else:
                    alloc_bytes = max(512, (num_elts + 32) * 8)
                self.emit(f"mov ecx, {alloc_bytes}", f"allocate seq of {num_elts} items")
                self.emit("call _pyfasm_alloc")
                self.emit("mov r8, rax", "base pointer")
                self.emit(f"mov qword [r8], {num_elts}", "store length")
                for idx, elt in enumerate(expr.elts):
                    self.emit("push r8")
                    self._generate_expr(elt)
                    self.emit("pop r8")
                    self.emit(f"mov [r8 + {(idx + 1) * 8}], rax", f"store item[{idx}]")
                self.emit("mov rax, r8", "return seq pointer")

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

                self.emit("mov rcx, rax")
                self.emit("push rax", "save container ptr")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_is_utf8_str_ptr")
                self.emit("add rsp, 32")
                self.emit("test eax, eax")
                lbl_not_str = self.new_label("list_not_str")
                lbl_got_cont = self.new_label("list_got_cont")
                self.emit(f"jz {lbl_not_str}")
                self.emit("pop rcx", "container str to convert")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_str_to_char_list")
                self.emit("add rsp, 32")
                self.emit(f"jmp {lbl_got_cont}")
                self.emit_raw(f"{lbl_not_str}:")
                self.emit("pop rax", "restore container ptr")
                self.emit_raw(f"{lbl_got_cont}:")

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
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_dict_set")
                self.emit("add rsp, 32")

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

                self.emit("mov rcx, rax")
                self.emit("push rax", "save container ptr")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_is_utf8_str_ptr")
                self.emit("add rsp, 32")
                self.emit("test eax, eax")
                lbl_not_str = self.new_label("dict_not_str")
                lbl_got_cont = self.new_label("dict_got_cont")
                self.emit(f"jz {lbl_not_str}")
                self.emit("pop rcx", "container str to convert")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_str_to_char_list")
                self.emit("add rsp, 32")
                self.emit(f"jmp {lbl_got_cont}")
                self.emit_raw(f"{lbl_not_str}:")
                self.emit("pop rax", "restore container ptr")
                self.emit_raw(f"{lbl_got_cont}:")

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
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_dict_set")
                self.emit("add rsp, 32")

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

    @staticmethod
    def _pygame_const_value(name: str) -> Optional[int]:
        pg_consts = {
            "QUIT": 256,
            "KEYDOWN": 768,
            "KEYUP": 769,
            "MOUSEMOTION": 1024,
            "MOUSEBUTTONDOWN": 1025,
            "MOUSEBUTTONUP": 1026,
            "MOUSEWHEEL": 1027,
            "K_ESCAPE": 27,
            "K_SPACE": 32,
            "K_RETURN": 13,
            "K_TAB": 9,
            "K_BACKSPACE": 8,
            "K_LEFT": 37,
            "K_UP": 38,
            "K_RIGHT": 39,
            "K_DOWN": 40,
            "K_LSHIFT": 160,
            "K_RSHIFT": 161,
            "K_LCTRL": 162,
            "K_RCTRL": 163,
            "K_LALT": 164,
            "K_RALT": 165,
            "K_DELETE": 46,
            "K_HOME": 36,
            "K_END": 35,
            "K_PAGEUP": 33,
            "K_PAGEDOWN": 34,
            "K_MINUS": 45,
            "K_EQUALS": 61,
            "SRCALPHA": 65536,
            "RESIZABLE": 16,
            "FULLSCREEN": -2147483648,
        }
        for fi in range(1, 13):
            pg_consts[f"K_F{fi}"] = 111 + fi
        if name in pg_consts:
            return pg_consts[name]
        if len(name) == 3 and name.startswith("K_"):
            ch = name[2]
            if "a" <= ch <= "z" or "0" <= ch <= "9":
                return ord(ch)
        return None

    def _try_emit_pygame_call(
        self, call: ast.Call, func_name: str, attr_name: str, prefix: str
    ) -> bool:
        func_dump_lower = ast.dump(call.func).lower()

        if (
            (attr_name == "init" and ("pygame" in func_dump_lower or prefix in ("pygame", "pg", "font", "mixer")))
            or func_name in ("pygame_init", "pg_init", "pygame_font_init", "pygame_mixer_init")
        ):
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_init")
            self.emit("add rsp, 32")
            return True

        if (attr_name == "quit" and prefix in ("pygame", "pg")) or func_name in ("pygame_quit", "pg_quit"):
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_quit")
            self.emit("add rsp, 32")
            return True

        if attr_name == "set_mode" or func_name in ("set_mode", "pygame_display_set_mode"):
            if len(call.args) >= 2:
                self.emit("sub rsp, 48", "aligned frame + width slot")
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 32], rax", "save width")
                self._generate_expr(call.args[1])
                self.emit("mov rdx, rax", "height")
                self.emit("mov rcx, [rsp + 32]", "width")
                self.emit("call _pyfasm_pg_set_mode")
                self.emit("add rsp, 48")
            elif len(call.args) == 1:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "size tuple or width")
                self.emit("xor edx, edx")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_pg_set_mode")
                self.emit("add rsp, 32")
            else:
                self.emit("mov rcx, 800")
                self.emit("mov rdx, 600")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_pg_set_mode")
                self.emit("add rsp, 32")
            return True

        if attr_name == "set_caption" or func_name in ("set_caption", "pygame_display_set_caption"):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "window caption")
            else:
                self.emit("xor ecx, ecx")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_set_caption")
            self.emit("add rsp, 32")
            return True

        if (
            (attr_name == "flip" and "transform" not in func_dump_lower and prefix != "transform")
            or (attr_name == "update" and ("display" in func_dump_lower or prefix == "display"))
            or func_name in ("pygame_display_flip", "pygame_display_update")
        ):
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_flip")
            self.emit("add rsp, 32")
            return True

        if (
            attr_name == "fill"
            and call.args
            and isinstance(call.func, ast.Attribute)
            and not self._infer_expr_type(call.func.value).is_dict()
            and not self._infer_expr_type(call.func.value).is_list()
        ):
            self.emit("sub rsp, 48", "aligned frame + color slot")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "save color")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "surface")
            self.emit("mov rdx, [rsp + 32]", "color")
            self.emit("call _pyfasm_pg_fill")
            self.emit("add rsp, 48")
            return True

        if ("draw" in func_dump_lower or prefix == "draw") and attr_name in ("rect", "ellipse", "circle", "line"):
            if attr_name in ("rect", "ellipse") and len(call.args) >= 3:
                w_node = call.args[3] if len(call.args) >= 4 else self._extract_kwarg(call, "width")
                self.emit("sub rsp, 80", "aligned frame for 4 args")
                for i in range(3):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {32 + i * 8}], rax")
                if w_node is not None:
                    self._generate_expr(w_node)
                    self.emit("mov r9, rax", "border width")
                else:
                    self.emit("xor r9d, r9d", "filled shape")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("mov r8, [rsp + 48]")
                fn = "_pyfasm_pg_draw_rect" if attr_name == "rect" else "_pyfasm_pg_draw_ellipse"
                self.emit(f"call {fn}")
                self.emit("add rsp, 80")
                return True
            if attr_name in ("circle", "line") and len(call.args) >= 4:
                default_w = 0 if attr_name == "circle" else 1
                w_node = call.args[4] if len(call.args) >= 5 else self._extract_kwarg(call, "width")
                self.emit("sub rsp, 80", "aligned frame for 5 args")
                if w_node is not None:
                    self._generate_expr(w_node)
                    self.emit("mov [rsp + 32], rax", "width 5th arg")
                else:
                    self.emit(f"mov qword [rsp + 32], {default_w}", "default width")
                for i in range(4):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {40 + i * 8}], rax")
                self.emit("mov rcx, [rsp + 40]")
                self.emit("mov rdx, [rsp + 48]")
                self.emit("mov r8, [rsp + 56]")
                self.emit("mov r9, [rsp + 64]")
                fn = "_pyfasm_pg_draw_circle" if attr_name == "circle" else "_pyfasm_pg_draw_line"
                self.emit(f"call {fn}")
                self.emit("add rsp, 80")
                return True

        if attr_name == "get" and ("event" in func_dump_lower or prefix in ("event", "pygame_event")):
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_poll_events")
            self.emit("add rsp, 32")
            return True

        if attr_name == "pump":
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_pump_messages")
            self.emit("add rsp, 32")
            return True

        if attr_name == "get_pressed":
            self.emit("sub rsp, 32", "shadow space")
            if "mouse" in func_dump_lower:
                self.emit("call _pyfasm_pg_mouse_get_pressed")
            else:
                self.emit("call _pyfasm_pg_get_pressed")
            self.emit("add rsp, 32")
            return True

        if attr_name == "get_pos" and "mouse" in func_dump_lower:
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_mouse_get_pos")
            self.emit("add rsp, 32")
            return True

        if attr_name == "Clock" or func_name == "Clock":
            self.emit("mov rax, 1", "pygame Clock handle")
            return True

        if attr_name == "tick":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rdx, rax", "target FPS")
            else:
                self.emit("mov rdx, 60", "default FPS")
            self.emit("xor ecx, ecx")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_clock_tick")
            self.emit("add rsp, 32")
            return True

        if attr_name == "get_ticks" or func_name == "get_ticks":
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_get_ticks")
            self.emit("add rsp, 32")
            return True

        if attr_name in ("delay", "wait") and ("time" in func_dump_lower or prefix in ("time", "pygame_time")):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "milliseconds")
            else:
                self.emit("xor ecx, ecx")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_pg_delay")
            self.emit("add rsp, 32")
            return True

        if (attr_name == "Rect" or func_name in ("Rect", "pygame_Rect", "pg_Rect")) and "Rect" not in self.module.classes:
            if len(call.args) >= 4:
                self.emit("sub rsp, 80", "aligned frame for Rect(x, y, w, h)")
                for i in range(4):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {32 + i * 8}], rax")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("mov r8, [rsp + 48]")
                self.emit("mov r9, [rsp + 56]")
                self.emit("call _pyfasm_pg_rect_new")
                self.emit("add rsp, 80")
            else:
                self.emit("xor ecx, ecx")
                self.emit("xor edx, edx")
                self.emit("xor r8d, r8d")
                self.emit("xor r9d, r9d")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_pg_rect_new")
                self.emit("add rsp, 32")
            return True

        if attr_name == "colliderect" and call.args and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 48", "aligned frame + other Rect")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "save other Rect")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "self Rect")
            self.emit("mov rdx, [rsp + 32]", "other Rect")
            self.emit("call _pyfasm_pg_rect_colliderect")
            self.emit("add rsp, 48")
            return True

        if attr_name == "collidepoint" and call.args and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 64", "aligned frame + point slots")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "pos or x")
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("mov [rsp + 40], rax", "y")
            else:
                self.emit("mov qword [rsp + 40], 0")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "Rect")
            self.emit("mov rdx, [rsp + 32]", "pos or x")
            self.emit("mov r8, [rsp + 40]", "y")
            self.emit("call _pyfasm_pg_rect_collidepoint")
            self.emit("add rsp, 64")
            return True

        if attr_name in ("SysFont", "Font") or func_name in ("SysFont", "Font"):
            self.emit("sub rsp, 48")
            if call.args and not (isinstance(call.args[0], ast.Constant) and call.args[0].value is None):
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 32], rax", "font name")
            else:
                self.emit("mov qword [rsp + 32], 0")
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("mov rdx, rax", "font size")
            else:
                self.emit("mov edx, 24")
            bold_kw = self._extract_kwarg_int(call, "bold", 0)
            italic_kw = self._extract_kwarg_int(call, "italic", 0)
            self.emit("mov rcx, [rsp + 32]")
            self.emit(f"mov r8d, {bold_kw}")
            self.emit(f"mov r9d, {italic_kw}")
            self.emit("call _pyfasm_pg_font_new")
            self.emit("add rsp, 48")
            return True

        if attr_name == "render" and call.args:
            self.emit("sub rsp, 64", "aligned frame + text/font slots")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "save rendered text")
            if len(call.args) >= 3:
                self._generate_expr(call.args[2])
                self.emit("mov [rsp + 40], rax", "save text color")
            elif len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("mov [rsp + 40], rax", "save text color")
            else:
                self.emit("mov qword [rsp + 40], 00FFFFFFh")
            if isinstance(call.func, ast.Attribute):
                self._generate_expr(call.func.value)
                self.emit("mov r8, rax", "HFONT handle")
            else:
                self.emit("xor r8d, r8d")
            self.emit("mov rcx, [rsp + 32]")
            self.emit("mov rdx, [rsp + 40]")
            self.emit("call _pyfasm_pg_font_render")
            self.emit("add rsp, 64")
            return True

        if attr_name == "size" and len(call.args) == 1 and isinstance(call.func, ast.Attribute):
            vt = self._infer_expr_type(call.func.value)
            if not (vt.is_list() or vt.is_dict() or vt.is_set()) and self.resolve_instance_class(call.func.value) is None:
                self.emit("sub rsp, 48")
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 32], rax")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax")
                self.emit("mov rdx, [rsp + 32]")
                self.emit("call _pyfasm_pg_font_size")
                self.emit("add rsp, 48")
                return True

        if attr_name == "blit" and len(call.args) >= 2 and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 64", "aligned frame + blit args")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "src surface")
            self._generate_expr(call.args[1])
            self.emit("mov [rsp + 40], rax", "dest pos/Rect")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "target surface")
            self.emit("mov rdx, [rsp + 32]", "src")
            self.emit("mov r8, [rsp + 40]", "dest")
            self.emit("call _pyfasm_pg_blit")
            self.emit("add rsp, 64")
            return True

        if (attr_name == "Surface" or func_name in ("Surface", "pygame_Surface")) and "Surface" not in self.module.classes:
            self.emit("sub rsp, 48")
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 100")
            if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, int):
                self._generate_expr(call.args[1])
                self.emit("mov rdx, rax")
            else:
                self.emit("xor edx, edx")
            self.emit("mov rcx, [rsp + 32]")
            self.emit("call _pyfasm_pg_surface_new")
            self.emit("add rsp, 48")
            return True

        if attr_name == "get_surface" and ("display" in func_dump_lower or prefix == "display"):
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_pg_display_get_surface")
            self.emit("add rsp, 32")
            return True

        if attr_name in ("get_size", "get_width", "get_height", "get_rect") and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax", "Surface ptr")
            self.emit("sub rsp, 32")
            self.emit(f"call _pyfasm_pg_surface_{attr_name}")
            self.emit("add rsp, 32")
            return True

        if attr_name in ("convert", "convert_alpha") and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            return True

        if attr_name == "set_alpha" and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 48")
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 255")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("mov rdx, [rsp + 32]")
            self.emit("call _pyfasm_pg_surface_set_alpha")
            self.emit("add rsp, 48")
            return True

        if attr_name == "set_colorkey" and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            self.emit("xor eax, eax")
            return True

        if attr_name == "copy" and not call.args and isinstance(call.func, ast.Attribute):
            vt = self._infer_expr_type(call.func.value)
            if not (vt.is_list() or vt.is_dict() or vt.is_set()) and self.resolve_instance_class(call.func.value) is None:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_pg_surface_copy")
                self.emit("add rsp, 32")
                return True

        if ("draw" in func_dump_lower or prefix == "draw") and attr_name in ("polygon", "lines", "aaline", "arc"):
            if attr_name == "polygon" and len(call.args) >= 3:
                w_node = call.args[3] if len(call.args) >= 4 else self._extract_kwarg(call, "width")
                self.emit("sub rsp, 64")
                for i in range(3):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {32 + i * 8}], rax")
                if w_node is not None:
                    self._generate_expr(w_node)
                    self.emit("mov r9, rax")
                else:
                    self.emit("xor r9d, r9d")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("mov r8, [rsp + 48]")
                self.emit("call _pyfasm_pg_draw_polygon")
                self.emit("add rsp, 64")
                return True
            if attr_name == "lines" and len(call.args) >= 4:
                w_node = call.args[4] if len(call.args) >= 5 else self._extract_kwarg(call, "width")
                self.emit("sub rsp, 80")
                if w_node is not None:
                    self._generate_expr(w_node)
                    self.emit("mov [rsp + 32], rax")
                else:
                    self.emit("mov qword [rsp + 32], 1")
                for i in range(4):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {40 + i * 8}], rax")
                self.emit("mov rcx, [rsp + 40]")
                self.emit("mov rdx, [rsp + 48]")
                self.emit("mov r8, [rsp + 56]")
                self.emit("mov r9, [rsp + 64]")
                self.emit("call _pyfasm_pg_draw_lines")
                self.emit("add rsp, 80")
                return True
            if attr_name == "aaline" and len(call.args) >= 4:
                self.emit("sub rsp, 80")
                self.emit("mov qword [rsp + 32], 1")
                for i in range(4):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {40 + i * 8}], rax")
                self.emit("mov rcx, [rsp + 40]")
                self.emit("mov rdx, [rsp + 48]")
                self.emit("mov r8, [rsp + 56]")
                self.emit("mov r9, [rsp + 64]")
                self.emit("call _pyfasm_pg_draw_line")
                self.emit("add rsp, 80")
                return True
            if attr_name == "arc" and len(call.args) >= 5:
                w_node = call.args[5] if len(call.args) >= 6 else self._extract_kwarg(call, "width")
                self.emit("sub rsp, 96")
                if w_node is not None:
                    self._generate_expr(w_node)
                    self.emit("mov [rsp + 40], rax")
                else:
                    self.emit("mov qword [rsp + 40], 1")
                self._generate_expr(call.args[4])
                self.emit("mov [rsp + 32], rax", "stop angle")
                for i in range(4):
                    self._generate_expr(call.args[i])
                    self.emit(f"mov [rsp + {48 + i * 8}], rax")
                self.emit("mov rcx, [rsp + 48]")
                self.emit("mov rdx, [rsp + 56]")
                self.emit("mov r8, [rsp + 64]")
                self.emit("mov r9, [rsp + 72]")
                self.emit("call _pyfasm_pg_draw_arc")
                self.emit("add rsp, 96")
                return True

        if ("image" in func_dump_lower or prefix == "image") and attr_name == "save" and len(call.args) >= 2:
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "Surface")
            self._generate_expr(call.args[1])
            self.emit("mov rdx, rax", "path")
            self.emit("mov rcx, [rsp + 32]")
            self.emit("call _pyfasm_pg_image_save")
            self.emit("add rsp, 48")
            return True

        if ("image" in func_dump_lower or prefix == "image") and attr_name == "load" and call.args:
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "path")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_pg_image_load")
            self.emit("add rsp, 32")
            return True

        if ("transform" in func_dump_lower or prefix == "transform") and attr_name in ("scale", "smoothscale", "flip") and len(call.args) >= 2:
            self.emit("sub rsp, 64")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax")
            self._generate_expr(call.args[1])
            self.emit("mov [rsp + 40], rax")
            if attr_name == "flip":
                if len(call.args) >= 3:
                    self._generate_expr(call.args[2])
                    self.emit("mov r8, rax")
                else:
                    self.emit("xor r8d, r8d")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("call _pyfasm_pg_transform_flip")
            else:
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("xor r8d, r8d")
                self.emit("call _pyfasm_pg_transform_scale")
            self.emit("add rsp, 64")
            return True

        if attr_name in ("move", "move_ip", "inflate") and len(call.args) >= 2 and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 64")
            self._generate_expr(call.func.value)
            self.emit("mov [rsp + 32], rax")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 40], rax")
            self._generate_expr(call.args[1])
            self.emit("mov r8, rax")
            self.emit("mov rcx, [rsp + 32]")
            self.emit("mov rdx, [rsp + 40]")
            self.emit(f"call _pyfasm_pg_rect_{attr_name}")
            self.emit("add rsp, 64")
            return True

        if attr_name in ("clamp_ip", "collidelist") and call.args and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("mov rdx, [rsp + 32]")
            self.emit(f"call _pyfasm_pg_rect_{attr_name}")
            self.emit("add rsp, 48")
            return True

        if (attr_name == "Color" or func_name == "Color") and "Color" not in self.module.classes and call.args:
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax")
            if len(call.args) >= 2:
                self._generate_expr(call.args[1])
                self.emit("mov [rsp + 40], rax")
            else:
                self.emit("mov qword [rsp + 40], 0")
            if len(call.args) >= 3:
                self._generate_expr(call.args[2])
                self.emit("mov r8, rax")
            else:
                self.emit("xor r8d, r8d")
            self.emit("mov rcx, [rsp + 32]")
            self.emit("mov rdx, [rsp + 40]")
            self.emit("call _pyfasm_pg_color_new")
            self.emit("add rsp, 48")
            return True

        if attr_name == "Group" and ("sprite" in func_dump_lower or prefix == "sprite"):
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_pg_group_new")
            self.emit("add rsp, 32")
            return True

        if "mixer" in func_dump_lower and attr_name in ("init", "Sound", "play", "stop", "load", "set_volume", "get_busy", "fadeout"):
            self.emit("call _pyfasm_pg_mixer_noop")
            return True

        return False

    def _emit_mpl_receiver(self, call: ast.Call) -> None:
        if (
            isinstance(call.func, ast.Attribute)
            and not (
                isinstance(call.func.value, ast.Name)
                and call.func.value.id.lower() in ("plt", "pyplot", "pylab", "matplotlib")
            )
        ):
            self._generate_expr(call.func.value)
        else:
            self.emit("xor eax, eax")

    def _mpl_extract_figsize(self, call: ast.Call) -> tuple[int, int, int]:
        dpi = self._extract_kwarg_int(call, "dpi", 100)
        if dpi <= 0:
            dpi = 100
        w_px, h_px = 640, 480
        fs = self._extract_kwarg(call, "figsize")
        if isinstance(fs, (ast.Tuple, ast.List)) and len(fs.elts) >= 2:
            if isinstance(fs.elts[0], ast.Constant) and isinstance(fs.elts[0].value, (int, float)):
                w_px = max(64, int(float(fs.elts[0].value) * dpi))
            if isinstance(fs.elts[1], ast.Constant) and isinstance(fs.elts[1].value, (int, float)):
                h_px = max(64, int(float(fs.elts[1].value) * dpi))
        return w_px, h_px, dpi

    def _try_emit_matplotlib_call(
        self, call: ast.Call, func_name: str, attr_name: str, prefix: str
    ) -> bool:
        if isinstance(call.func, ast.Name) and (
            func_name in self.module.functions or func_name in self.module.classes
        ):
            return False
        if isinstance(call.func, ast.Attribute):
            rc_cls = self.resolve_instance_class(call.func.value)
            if rc_cls and rc_cls in self.module.classes and self.resolve_class_method(rc_cls, attr_name):
                return False

        is_plt = (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id.lower() in ("plt", "pyplot", "pylab", "matplotlib")
        )
        raw_name = attr_name or func_name

        # Figure(...) or plt.figure(...)
        if raw_name == "Figure" or (raw_name == "figure" and (is_plt or isinstance(call.func, ast.Name))):
            w_px, h_px, dpi = self._mpl_extract_figsize(call)
            bg_kw = self._extract_kwarg(call, "facecolor") or self._extract_kwarg(call, "fc")
            if bg_kw is not None:
                self._generate_expr(bg_kw)
                self.emit("mov r9, rax", "bg color")
            else:
                self.emit("xor r9d, r9d")
            self.emit(f"mov rcx, {w_px}")
            self.emit(f"mov rdx, {h_px}")
            self.emit(f"mov r8, {dpi}")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_figure_new")
            self.emit("add rsp, 32")
            return True

        # plt.subplots(...)
        if raw_name == "subplots" and (is_plt or isinstance(call.func, ast.Name)):
            nrows = 1
            ncols = 1
            if len(call.args) >= 1 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int):
                nrows = max(1, call.args[0].value)
            if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, int):
                ncols = max(1, call.args[1].value)
            nr_kw = self._extract_kwarg_int(call, "nrows", nrows)
            nc_kw = self._extract_kwarg_int(call, "ncols", ncols)
            w_px, h_px, _ = self._mpl_extract_figsize(call)
            self.emit(f"mov rcx, {max(1, nr_kw)}")
            self.emit(f"mov rdx, {max(1, nc_kw)}")
            self.emit(f"mov r8, {w_px}")
            self.emit(f"mov r9, {h_px}")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_plt_subplots")
            self.emit("add rsp, 32")
            return True

        # fig.add_subplot(...) / plt.subplot(...)
        if attr_name == "add_subplot" or (raw_name == "subplot" and (is_plt or isinstance(call.func, ast.Name))):
            nr, nc, idx = 1, 1, 1
            if len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int):
                code = call.args[0].value
                if code >= 100:
                    nr = max(1, code // 100)
                    nc = max(1, (code // 10) % 10)
                    idx = max(1, code % 10)
                else:
                    idx = max(1, code)
            elif len(call.args) >= 3:
                if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int):
                    nr = max(1, call.args[0].value)
                if isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, int):
                    nc = max(1, call.args[1].value)
                if isinstance(call.args[2], ast.Constant) and isinstance(call.args[2].value, int):
                    idx = max(1, call.args[2].value)
            if attr_name == "add_subplot":
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "fig ptr")
            else:
                self.emit("xor ecx, ecx", "gcf")
            self.emit(f"mov rdx, {nr}")
            self.emit(f"mov r8, {nc}")
            self.emit(f"mov r9, {idx}")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_fig_add_subplot")
            self.emit("add rsp, 32")
            return True

        if raw_name == "gca" and (is_plt or isinstance(call.func, ast.Name)):
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_gca")
            self.emit("add rsp, 32")
            return True

        if raw_name == "gcf" and (is_plt or isinstance(call.func, ast.Name)):
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_gcf")
            self.emit("add rsp, 32")
            return True

        if raw_name == "suptitle" and call.args:
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "title")
            self._emit_mpl_receiver(call)
            self.emit("mov rcx, rax", "fig_or_0")
            self.emit("mov rdx, [rsp + 32]")
            self.emit("call _pyfasm_mpl_fig_suptitle")
            self.emit("add rsp, 48")
            return True

        if raw_name in ("clf", "cla", "clear") and len(call.args) == 0:
            if isinstance(call.func, ast.Attribute):
                vt = self._infer_expr_type(call.func.value)
                if vt.is_list() or vt.is_dict() or vt.is_set():
                    return False
            self._emit_mpl_receiver(call)
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32")
            if raw_name == "clf":
                self.emit("call _pyfasm_mpl_fig_clear")
            else:
                self.emit("call _pyfasm_mpl_axes_clear")
            self.emit("add rsp, 32")
            return True

        # ax.plot(...) / plt.plot(...)
        if raw_name == "plot" and call.args and (is_plt or isinstance(call.func, ast.Attribute)):
            x_node: Optional[ast.AST] = None
            y_node: ast.AST = call.args[0]
            fmt_str = ""
            if len(call.args) >= 2:
                if isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                    fmt_str = call.args[1].value
                else:
                    x_node = call.args[0]
                    y_node = call.args[1]
                    if len(call.args) >= 3 and isinstance(call.args[2], ast.Constant) and isinstance(call.args[2].value, str):
                        fmt_str = call.args[2].value

            fmt_color = ""
            style_flags = 0
            if "--" in fmt_str:
                style_flags |= 1
            elif ":" in fmt_str:
                style_flags |= 2
            for ch in fmt_str:
                if ch in ("r", "g", "b", "c", "m", "y", "k", "w"):
                    fmt_color = ch
                elif ch in ("o", "*", ".", "+", "x", "s", "^"):
                    style_flags |= 4

            ls_kw = (self._get_kwarg_string_val(call, "linestyle") or self._get_kwarg_string_val(call, "ls") or "").strip()
            if ls_kw == "--":
                style_flags = (style_flags & ~3) | 1
            elif ls_kw == ":":
                style_flags = (style_flags & ~3) | 2
            if self._extract_kwarg(call, "marker") is not None:
                style_flags |= 4

            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            lw_val = self._extract_kwarg_int(call, "linewidth", 0) or self._extract_kwarg_int(call, "lw", 2)
            label_node = self._extract_kwarg(call, "label")

            self.emit("sub rsp, 96")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 56], rax", "ax_or_0")
            if x_node is not None:
                self._generate_expr(x_node)
                self.emit("mov [rsp + 64], rax", "x_arr")
            else:
                self.emit("mov qword [rsp + 64], 0")
            self._generate_expr(y_node)
            self.emit("mov [rsp + 72], rax", "y_arr")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 80], rax", "color")
            elif fmt_color:
                self._emit_string_pointer("rax", fmt_color)
                self.emit("mov [rsp + 80], rax", "fmt color")
            else:
                self.emit("mov qword [rsp + 80], 0")
            if label_node is not None:
                self._generate_expr(label_node)
                self.emit("mov [rsp + 48], rax", "label")
            else:
                self.emit("mov qword [rsp + 48], 0")
            self.emit(f"mov qword [rsp + 32], {max(1, lw_val)}")
            self.emit(f"mov qword [rsp + 40], {style_flags}")
            self.emit("mov rcx, [rsp + 56]")
            self.emit("mov rdx, [rsp + 64]")
            self.emit("mov r8, [rsp + 72]")
            self.emit("mov r9, [rsp + 80]")
            self.emit("call _pyfasm_mpl_axes_plot")
            self.emit("add rsp, 96")
            return True

        # scatter(x, y, ...)
        if raw_name == "scatter" and len(call.args) >= 2:
            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            label_node = self._extract_kwarg(call, "label")
            sz_val = self._extract_kwarg_int(call, "s", 6)
            self.emit("sub rsp, 96")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 56], rax")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 64], rax")
            self._generate_expr(call.args[1])
            self.emit("mov [rsp + 72], rax")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 80], rax")
            else:
                self.emit("mov qword [rsp + 80], 0")
            if label_node is not None:
                self._generate_expr(label_node)
                self.emit("mov [rsp + 40], rax")
            else:
                self.emit("mov qword [rsp + 40], 0")
            self.emit(f"mov qword [rsp + 32], {max(4, sz_val)}")
            self.emit("mov rcx, [rsp + 56]")
            self.emit("mov rdx, [rsp + 64]")
            self.emit("mov r8, [rsp + 72]")
            self.emit("mov r9, [rsp + 80]")
            self.emit("call _pyfasm_mpl_axes_scatter")
            self.emit("add rsp, 96")
            return True

        # bar(x, height, ...)
        if raw_name == "bar" and len(call.args) >= 2:
            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            label_node = self._extract_kwarg(call, "label")
            self.emit("sub rsp, 80")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 40], rax")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 48], rax")
            self._generate_expr(call.args[1])
            self.emit("mov [rsp + 56], rax")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 64], rax")
            else:
                self.emit("mov qword [rsp + 64], 0")
            if label_node is not None:
                self._generate_expr(label_node)
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 0")
            self.emit("mov rcx, [rsp + 40]")
            self.emit("mov rdx, [rsp + 48]")
            self.emit("mov r8, [rsp + 56]")
            self.emit("mov r9, [rsp + 64]")
            self.emit("call _pyfasm_mpl_axes_bar")
            self.emit("add rsp, 80")
            return True

        # hist(data, bins=10, ...)
        if raw_name == "hist" and call.args:
            bins_node = self._extract_kwarg(call, "bins") or (call.args[1] if len(call.args) >= 2 else None)
            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            label_node = self._extract_kwarg(call, "label")
            self.emit("sub rsp, 80")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 40], rax")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 48], rax")
            if bins_node is not None:
                self._generate_expr(bins_node)
                self.emit("mov [rsp + 56], rax")
            else:
                self.emit("mov qword [rsp + 56], 10")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 64], rax")
            else:
                self.emit("mov qword [rsp + 64], 0")
            if label_node is not None:
                self._generate_expr(label_node)
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 0")
            self.emit("mov rcx, [rsp + 40]")
            self.emit("mov rdx, [rsp + 48]")
            self.emit("mov r8, [rsp + 56]")
            self.emit("mov r9, [rsp + 64]")
            self.emit("call _pyfasm_mpl_axes_hist")
            self.emit("add rsp, 80")
            return True

        # axhline(y, ...) / axvline(x, ...)
        if raw_name in ("axhline", "axvline"):
            val_node = call.args[0] if call.args else (self._extract_kwarg(call, "y") if raw_name == "axhline" else self._extract_kwarg(call, "x"))
            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            label_node = self._extract_kwarg(call, "label")
            ls_kw = (self._get_kwarg_string_val(call, "linestyle") or self._get_kwarg_string_val(call, "ls") or "").strip()
            s_flags = 1 if ls_kw == "--" else (2 if ls_kw == ":" else 0)
            self.emit("sub rsp, 80")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 40], rax")
            if val_node is not None:
                self._generate_expr(val_node)
                self.emit("mov [rsp + 48], rax")
            else:
                self.emit("mov qword [rsp + 48], 0")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 56], rax")
            else:
                self.emit("mov qword [rsp + 56], 0")
            if label_node is not None:
                self._generate_expr(label_node)
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 0")
            self.emit("mov rcx, [rsp + 40]")
            self.emit("mov rdx, [rsp + 48]")
            self.emit("mov r8, [rsp + 56]")
            self.emit(f"mov r9, {s_flags}")
            self.emit("call _pyfasm_mpl_axes_hline" if raw_name == "axhline" else "call _pyfasm_mpl_axes_vline")
            self.emit("add rsp, 80")
            return True

        # fill_between(x, y1, y2=0, ...)
        if raw_name == "fill_between" and len(call.args) >= 2:
            y2_node = call.args[2] if len(call.args) >= 3 else self._extract_kwarg(call, "y2")
            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            label_node = self._extract_kwarg(call, "label")
            self.emit("sub rsp, 96")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 56], rax")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 64], rax")
            self._generate_expr(call.args[1])
            self.emit("mov [rsp + 72], rax")
            if y2_node is not None:
                self._generate_expr(y2_node)
                self.emit("mov [rsp + 80], rax")
            else:
                self.emit("mov qword [rsp + 80], 0")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 0")
            if label_node is not None:
                self._generate_expr(label_node)
                self.emit("mov [rsp + 40], rax")
            else:
                self.emit("mov qword [rsp + 40], 0")
            self.emit("mov rcx, [rsp + 56]")
            self.emit("mov rdx, [rsp + 64]")
            self.emit("mov r8, [rsp + 72]")
            self.emit("mov r9, [rsp + 80]")
            self.emit("call _pyfasm_mpl_axes_fill_between")
            self.emit("add rsp, 96")
            return True

        # text(x, y, s) or annotate(s, xy=(x, y))
        if (raw_name == "text" and len(call.args) >= 3) or (raw_name == "annotate" and call.args):
            if raw_name == "annotate":
                txt_node = call.args[0]
                xy_node = self._extract_kwarg(call, "xy") or (call.args[1] if len(call.args) >= 2 else None)
                x_node = xy_node.elts[0] if isinstance(xy_node, (ast.Tuple, ast.List)) and len(xy_node.elts) >= 2 else ast.Constant(0)
                y_node = xy_node.elts[1] if isinstance(xy_node, (ast.Tuple, ast.List)) and len(xy_node.elts) >= 2 else ast.Constant(0)
            else:
                x_node, y_node, txt_node = call.args[0], call.args[1], call.args[2]
            color_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            self.emit("sub rsp, 80")
            self._emit_mpl_receiver(call)
            self.emit("mov [rsp + 40], rax")
            self._generate_expr(x_node)
            self.emit("mov [rsp + 48], rax")
            self._generate_expr(y_node)
            self.emit("mov [rsp + 56], rax")
            self._generate_expr(txt_node)
            self.emit("mov [rsp + 64], rax")
            if color_node is not None:
                self._generate_expr(color_node)
                self.emit("mov [rsp + 32], rax")
            else:
                self.emit("mov qword [rsp + 32], 0")
            self.emit("mov rcx, [rsp + 40]")
            self.emit("mov rdx, [rsp + 48]")
            self.emit("mov r8, [rsp + 56]")
            self.emit("mov r9, [rsp + 64]")
            self.emit("call _pyfasm_mpl_axes_text")
            self.emit("add rsp, 80")
            return True

        # set_title / plt.title / set_xlabel / plt.xlabel / set_ylabel / plt.ylabel
        if (
            raw_name in ("set_title", "set_xlabel", "set_ylabel")
            or (raw_name in ("title", "xlabel", "ylabel") and (is_plt or isinstance(call.func, ast.Name)))
        ) and call.args:
            fn_map = {
                "set_title": "_pyfasm_mpl_axes_set_title",
                "title": "_pyfasm_mpl_axes_set_title",
                "set_xlabel": "_pyfasm_mpl_axes_set_xlabel",
                "xlabel": "_pyfasm_mpl_axes_set_xlabel",
                "set_ylabel": "_pyfasm_mpl_axes_set_ylabel",
                "ylabel": "_pyfasm_mpl_axes_set_ylabel",
            }
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax")
            self._emit_mpl_receiver(call)
            self.emit("mov rcx, rax")
            self.emit("mov rdx, [rsp + 32]")
            self.emit(f"call {fn_map[raw_name]}")
            self.emit("add rsp, 48")
            return True

        # set_xlim / plt.xlim / set_ylim / plt.ylim
        if raw_name in ("set_xlim", "set_ylim") or (raw_name in ("xlim", "ylim") and (is_plt or isinstance(call.func, ast.Name))):
            fn_lim = "_pyfasm_mpl_axes_set_xlim" if "x" in raw_name else "_pyfasm_mpl_axes_set_ylim"
            lo_node, hi_node = None, None
            if len(call.args) >= 2:
                lo_node, hi_node = call.args[0], call.args[1]
            elif len(call.args) == 1 and isinstance(call.args[0], (ast.Tuple, ast.List)) and len(call.args[0].elts) >= 2:
                lo_node, hi_node = call.args[0].elts[0], call.args[0].elts[1]
            if lo_node is not None and hi_node is not None:
                self.emit("sub rsp, 64")
                self._emit_mpl_receiver(call)
                self.emit("mov [rsp + 32], rax")
                self._generate_expr(lo_node)
                self.emit("mov [rsp + 40], rax")
                self._generate_expr(hi_node)
                self.emit("mov r8, rax")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit(f"call {fn_lim}")
                self.emit("add rsp, 64")
                return True

        if raw_name == "set_facecolor" and call.args and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("mov rdx, [rsp + 32]")
            self.emit("call _pyfasm_mpl_set_facecolor")
            self.emit("add rsp, 48")
            return True

        if raw_name in ("tick_params", "set_tick_params"):
            col_node = self._extract_kwarg(call, "colors") or self._extract_kwarg(call, "color") or self._extract_kwarg(call, "labelcolor")
            if col_node is not None:
                self.emit("sub rsp, 48")
                self._generate_expr(col_node)
                self.emit("mov [rsp + 32], rax")
                self._emit_mpl_receiver(call)
                self.emit("mov rcx, rax")
                self.emit("mov rdx, [rsp + 32]")
                self.emit("call _pyfasm_mpl_axes_set_fgcolor")
                self.emit("add rsp, 48")
            else:
                self.emit("xor eax, eax")
            return True

        if attr_name == "set_color" and call.args and isinstance(call.func, ast.Attribute):
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax")
            self._generate_expr(call.func.value)
            self.emit("mov rcx, rax")
            self.emit("mov rdx, [rsp + 32]")
            self.emit("call _pyfasm_mpl_axes_set_spine_color")
            self.emit("add rsp, 48")
            return True

        if raw_name == "legend":
            self._emit_mpl_receiver(call)
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_axes_legend")
            self.emit("add rsp, 32")
            return True

        if raw_name == "grid" and (is_plt or isinstance(call.func, ast.Name)):
            vis = 0 if (call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value is False) else 1
            col_node = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
            self.emit("xor ecx, ecx")
            self.emit(f"mov edx, {vis}")
            if col_node is not None:
                self._generate_expr(col_node)
                self.emit("mov r8, rax")
            else:
                self.emit("xor r8d, r8d")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_axes_grid")
            self.emit("add rsp, 32")
            return True

        if raw_name in ("tight_layout", "subplots_adjust", "set_xscale", "set_yscale", "set_aspect", "axis", "invert_yaxis", "invert_xaxis", "set_xticks", "set_yticks", "xticks", "yticks", "margins", "set_edgecolor"):
            self.emit("xor eax, eax", f"matplotlib {raw_name}")
            return True

        if raw_name == "savefig" and call.args:
            self.emit("sub rsp, 48")
            self._generate_expr(call.args[0])
            self.emit("mov [rsp + 32], rax", "path str")
            self._emit_mpl_receiver(call)
            self.emit("mov rcx, rax", "fig_or_0")
            self.emit("mov rdx, [rsp + 32]")
            self.emit("call _pyfasm_mpl_fig_savefig")
            self.emit("add rsp, 48")
            return True

        if raw_name in ("draw", "draw_idle") and not call.args:
            self._emit_mpl_receiver(call)
            self.emit("mov rcx, rax")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_canvas_draw")
            self.emit("add rsp, 32")
            return True

        if attr_name == "show" and is_plt:
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_mpl_plt_show")
            self.emit("add rsp, 32")
            return True

        return False

    def _try_emit_http_server_call(
        self, call: ast.Call, func_name: str, attr_name: str, prefix: str
    ) -> bool:
        raw_name = attr_name or func_name
        if raw_name in ("FastAPI", "APIRouter"):
            self.emit("mov rax, 1", f"native {raw_name} app handle")
            return True

        if raw_name in ("include_router", "add_middleware", "on_event", "mount", "HTTPException"):
            self.emit("xor eax, eax", f"native FastAPI setup {raw_name}")
            return True

        if raw_name in ("HTMLResponse", "PlainTextResponse", "JSONResponse"):
            content_node = self._extract_kwarg(call, "content") or (call.args[0] if call.args else None)
            if content_node is not None:
                self._generate_expr(content_node)
            else:
                self.emit("xor eax, eax")
            return True

        if (
            attr_name in ("get", "post", "put", "delete", "patch", "head", "options")
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id in ("app", "router")
            and not self._infer_expr_type(call.func.value).is_dict()
        ):
            self.emit("xor eax, eax", "FastAPI decorator metadata registered statically")
            return True

        if (attr_name == "run" and prefix == "uvicorn") or func_name == "uvicorn_run":
            kind_map = {
                "auto": 0, "dict": 1, "list": 2, "str": 3,
                "int": 4, "float": 5, "bool": 6, "html": 7, "text": 8,
            }
            for route in getattr(self.module, "http_routes", []):
                param_names = list(getattr(route, "param_names", []) or [])
                if param_names:
                    self.emit(f"mov ecx, {len(param_names) * 8}", "allocate param_names ptr array")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_alloc")
                    self.emit("add rsp, 32")
                    self.emit("push rax", "save param_names ptr array")
                    for idx, pname in enumerate(param_names):
                        self._emit_string_pointer("rdx", pname)
                        self.emit("mov rcx, [rsp]", "restore param_names array")
                        self.emit(f"mov [rcx + {idx * 8}], rdx", f"param '{pname}'")
                    self.emit("pop rax", "param_names array")
                    self.emit("sub rsp, 64", "route registration frame")
                    self.emit(f"mov qword [rsp + 32], {len(param_names)}")
                    self.emit(f"mov qword [rsp + 40], {int(getattr(route, 'param_int_mask', 0))}")
                    self.emit("mov [rsp + 48], rax")
                else:
                    self.emit("sub rsp, 64", "route registration frame")
                    self.emit("mov qword [rsp + 32], 0")
                    self.emit("mov qword [rsp + 40], 0")
                    self.emit("mov qword [rsp + 48], 0")
                self._emit_string_pointer("rcx", route.method)
                self._emit_string_pointer("rdx", route.path)
                self.emit(f"lea r8, [{safe_asm_label(route.handler_name)}]", f"route handler {route.handler_name}")
                self.emit(f"mov r9, {kind_map.get(route.return_kind, 0)}", f"return_kind={route.return_kind}")
                self.emit("call _pyfasm_http_register_route")
                self.emit("add rsp, 64")

            host_node = self._extract_kwarg(call, "host")
            port_node = self._extract_kwarg(call, "port")
            self.emit("sub rsp, 48", "aligned frame + port slot")
            if port_node is not None:
                self._generate_expr(port_node)
                self.emit("mov [rsp + 32], rax", "save listen port")
            else:
                self.emit("mov qword [rsp + 32], 8000", "default port 8000")
            if host_node is not None:
                self._generate_expr(host_node)
                self.emit("mov rcx, rax", "host string")
            else:
                self.emit("xor ecx, ecx", "default host 127.0.0.1")
            self.emit("mov rdx, [rsp + 32]", "listen port")
            self.emit("call _pyfasm_http_server_run")
            self.emit("add rsp, 48")
            return True

        return False

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

        if "pygame" in self.features:
            if self._try_emit_pygame_call(call, func_name, attr_name, prefix):
                return

        if "matplotlib" in self.features:
            if self._try_emit_matplotlib_call(call, func_name, attr_name, prefix):
                return

        if "http_server" in self.features and self.target in ("win64", "dll"):
            if self._try_emit_http_server_call(call, func_name, attr_name, prefix):
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

        if attr_name in ("strip", "lstrip", "rstrip") and isinstance(call.func, ast.Attribute):
            mode = {"strip": 0, "lstrip": 1, "rstrip": 2}[attr_name]
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("push rax", "chars")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
            else:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax")
                self.emit("xor edx, edx")
            self.emit(f"mov r8d, {mode}")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_str_strip_chars")
            self.emit("add rsp, 32")
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

        # List insert: s.insert(idx, val) or GUI Entry insert
        if attr_name == "insert" and len(call.args) >= 2:
            target_type = self._infer_expr_type(call.func.value)
            is_gui = "gui" in self.features or getattr(self.module, "is_modern_gui", False)
            is_entry_widget = is_gui and (
                not target_type.is_list()
                or (isinstance(call.func.value, ast.Name) and any(k in call.func.value.id.lower() for k in ("ent", "edit", "txt", "search", "filter")))
                or (isinstance(call.func.value, ast.Attribute) and any(k in call.func.value.attr.lower() for k in ("ent", "edit", "txt", "search", "filter")))
            )
            if is_entry_widget:
                is_end = (
                    isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[0].value, str)
                    and call.args[0].value.lower() == "end"
                ) or (
                    isinstance(call.args[0], ast.Attribute)
                    and call.args[0].attr.lower() == "end"
                )
                self._generate_expr(call.args[1])
                self.emit("push rax", "new text/item")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "target control HWND")
                self.emit("pop rdx", "new text/item")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_textbox_append" if is_end else "call _pyfasm_set_text")
                self.emit("add rsp, 32")
                return

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

        # List tolist / to_list
        if attr_name in ("tolist", "to_list") and isinstance(call.func, ast.Attribute):
            self._generate_expr(call.func.value)
            return

        # List extend
        if attr_name == "extend" and call.args and isinstance(call.func, ast.Attribute):
            ext_arg = call.args[0]
            ext_is_gen = self._is_generator_expr(ext_arg)
            self._generate_expr(call.func.value)
            self.emit("push rax", "dest list")
            self._generate_expr(ext_arg)
            if ext_is_gen:
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_gen_to_list")
                self.emit("add rsp, 32")
            self.emit("mov rdx, rax", "src iterable")
            self.emit("pop rcx", "dest list")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_list_extend")
            self.emit("add rsp, 32")
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
            recv = call.func.value
            recv_name = (getattr(recv, "id", "") or getattr(recv, "attr", "")).lower()
            if (
                self.target in ("win64", "dll")
                and "gui" in self.features
                and recv_name not in ("f", "fp", "fh", "fout", "fin")
                and not any(k in recv_name for k in ("file", "stream", "sock", "conn"))
                and (
                    any(k in recv_name for k in ("win", "window", "root", "app", "dialog", "page", "main", "frame"))
                    or recv_name in ("self", "this")
                )
            ):
                self._generate_expr(recv)
                self.emit("mov rcx, rax", "window handle")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_destroy_window")
                self.emit("add rsp, 32")
                return
            self._generate_expr(recv)
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
                    elif "complex" in builtin_targets and arg0_t.is_complex():
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
                if "complex" in builtin_targets and not arg0_cls and not arg0_t.is_complex():
                    # Dynamic or polymorphic union value (e.g. float | complex)
                    self._generate_expr(arg0)
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_is_complex")
                    self.emit("add rsp, 32")
                    return
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
        if (func_name == "abs" or (prefix in ("np", "numpy") and attr_name == "abs")) and call.args:
            arg0_cls = self.resolve_instance_class(call.args[0])
            abs_m = self.resolve_class_method(arg0_cls, "__abs__") if arg0_cls else None
            if abs_m:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "pass self to __abs__")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call {self._method_call_target(arg0_cls, '__abs__', abs_m)}")
                self.emit("add rsp, 32")
                return
            arg0_t = self._infer_expr_type(call.args[0])
            self._generate_expr(call.args[0])
            if prefix in ("np", "numpy") and arg0_t.is_list():
                self.emit("mov rcx, rax")
                self.emit("mov rdx, 6", "ufunc abs")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_vec_ufunc")
                self.emit("add rsp, 32")
            elif arg0_t.is_complex():
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_complex_abs")
                self.emit("add rsp, 32")
            elif arg0_t.is_float():
                self.emit("mov rdx, 7FFFFFFFFFFFFFFFh")
                self.emit("and rax, rdx", "float abs(rax)")
            else:
                self.emit("cqo")
                self.emit("xor rax, rdx")
                self.emit("sub rax, rdx", "branchless abs(rax)")
            return

        if func_name == "round" and call.args:
            at = self._infer_expr_type(call.args[0])
            self._generate_expr(call.args[0])
            if len(call.args) == 1:
                if at.is_float():
                    self.emit("movq xmm0, rax")
                    self.emit("cvtsd2si rax, xmm0", "round float to nearest-even int")
                return
            # round(x, ndigits) -> float
            if not at.is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rax, xmm0")
            self.emit("push rax")
            self._generate_expr(call.args[1])
            self.emit("cvtsi2sd xmm1, rax")
            self.emit("movq rdx, xmm1")
            self._emit_float_bits("rcx", 10.0)
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_math_pow_f64")
            self.emit("add rsp, 32")
            self.emit("pop rcx", "orig float x")
            self.emit("movq xmm0, rcx")
            self.emit("movq xmm2, rax", "scale = 10^ndigits")
            self.emit("mulsd xmm0, xmm2")
            self.emit("cvtsd2si rax, xmm0")
            self.emit("cvtsi2sd xmm0, rax")
            self.emit("divsd xmm0, xmm2")
            self.emit("movq rax, xmm0")
            return

        if func_name in ("min", "max") and call.args:
            is_max = (func_name == "max")
            if len(call.args) >= 2:
                is_flt = any(self._infer_expr_type(a).is_float() for a in call.args)
                self._generate_expr(call.args[0])
                if is_flt and not self._infer_expr_type(call.args[0]).is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                for a in call.args[1:]:
                    self.emit("push rax")
                    self._generate_expr(a)
                    if is_flt and not self._infer_expr_type(a).is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    if is_flt:
                        self.emit("mov rdx, rax")
                        self.emit("pop rcx")
                        self.emit("sub rsp, 32", "shadow space")
                        self.emit("call _pyfasm_max_f64" if is_max else "call _pyfasm_min_f64")
                        self.emit("add rsp, 32")
                    else:
                        self.emit("mov r11, rax")
                        self.emit("pop rax")
                        self.emit("cmp rax, r11")
                        self.emit("cmovl rax, r11" if is_max else "cmovg rax, r11", f"{func_name}(a, b)")
                return
            elif len(call.args) == 1:
                arg0 = call.args[0]
                is_gen = self._is_generator_expr(arg0)
                arg0_t = self._infer_expr_type(arg0)
                self._generate_expr(arg0)
                if is_gen:
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_gen_to_list")
                    self.emit("add rsp, 32")
                if getattr(arg0_t, "element_type", None) and arg0_t.element_type.is_float():
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_np_max_f64" if is_max else "call _pyfasm_np_min_f64")
                    self.emit("add rsp, 32")
                    return
                lbl_loop = self.new_label(f"{func_name}_loop")
                lbl_done = self.new_label(f"{func_name}_done")
                self.emit("mov rcx, rax", "list/tuple pointer")
                self.emit("xor eax, eax")
                self.emit("test rcx, rcx")
                self.emit(f"jz {lbl_done}")
                self.emit("mov r8, [rcx]", "length")
                self.emit("test r8, r8")
                self.emit(f"jz {lbl_done}")
                self.emit("mov rax, [rcx + 8]", "first element")
                self.emit("mov r9, 1", "index = 1")
                self.emit_raw(f"{lbl_loop}:")
                self.emit("cmp r9, r8")
                self.emit(f"jge {lbl_done}")
                self.emit("mov r10, [rcx + 8 + r9 * 8]")
                self.emit("cmp rax, r10")
                self.emit("cmovl rax, r10" if is_max else "cmovg rax, r10", f"update {func_name}")
                self.emit("inc r9")
                self.emit(f"jmp {lbl_loop}")
                self.emit_raw(f"{lbl_done}:")
                return

        if func_name == "tuple":
            if call.args:
                arg0 = call.args[0]
                if isinstance(arg0, ast.GeneratorExp):
                    list_comp = ast.ListComp(elt=arg0.elt, generators=arg0.generators)
                    self._generate_list_comprehension(list_comp)
                elif self._is_generator_expr(arg0):
                    self._generate_expr(arg0)
                    self.emit("mov rcx, rax", "gen_ptr")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_gen_to_list")
                    self.emit("add rsp, 32")
                else:
                    self._generate_expr(arg0)
            else:
                self.emit("xor ecx, ecx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_list_create")
                self.emit("add rsp, 32")
            return

        if func_name == "complex":
            if not call.args:
                self.emit("xor ecx, ecx")
                self.emit("xor edx, edx")
            else:
                if len(call.args) >= 2:
                    self._generate_expr(call.args[1])
                    if not self._infer_expr_type(call.args[1]).is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("push rax")
                else:
                    self.emit("push 0")
                self._generate_expr(call.args[0])
                if not self._infer_expr_type(call.args[0]).is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov rcx, rax")
                self.emit("pop rdx")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_complex_new")
            self.emit("add rsp, 32")
            return

        if (func_name in ("isfinite", "isnan", "isinf", "math_isfinite", "math_isnan", "math_isinf") or (attr_name in ("isfinite", "isnan", "isinf") and prefix in ("math", ""))) and call.args:
            m_op = attr_name if attr_name in ("isfinite", "isnan", "isinf") else func_name.replace("math_", "")
            at = self._infer_expr_type(call.args[0])
            self._generate_expr(call.args[0])
            if not at.is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rcx, xmm0")
            else:
                self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            self.emit(f"call _pyfasm_math_{m_op}")
            self.emit("add rsp, 32")
            return

        if (func_name in ("isclose", "math_isclose") or (attr_name == "isclose" and prefix in ("math", ""))) and len(call.args) >= 2:
            kw_map = {k.arg: k.value for k in getattr(call, "keywords", []) if k.arg}
            rel_expr = kw_map.get("rel_tol", call.args[2] if len(call.args) >= 3 else None)
            abs_expr = kw_map.get("abs_tol", call.args[3] if len(call.args) >= 4 else None)
            self.emit("sub rsp, 32", "local frame for isclose args")
            self._generate_expr(call.args[0])
            if not self._infer_expr_type(call.args[0]).is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rax, xmm0")
            self.emit("mov [rsp], rax")
            self._generate_expr(call.args[1])
            if not self._infer_expr_type(call.args[1]).is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rax, xmm0")
            self.emit("mov [rsp + 8], rax")
            if rel_expr is not None:
                self._generate_expr(rel_expr)
                if not self._infer_expr_type(rel_expr).is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov [rsp + 16], rax")
            else:
                self._emit_float_bits("rax", 1e-9)
                self.emit("mov [rsp + 16], rax")
            if abs_expr is not None:
                self._generate_expr(abs_expr)
                if not self._infer_expr_type(abs_expr).is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov r9, rax")
            else:
                self.emit("xor r9d, r9d")
            self.emit("mov rcx, [rsp]")
            self.emit("mov rdx, [rsp + 8]")
            self.emit("mov r8, [rsp + 16]")
            self.emit("add rsp, 32")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_math_isclose")
            self.emit("add rsp, 32")
            return

        if func_name == "getattr" and len(call.args) >= 2:
            if len(call.args) >= 3:
                self._generate_expr(call.args[2])
                self.emit("push rax", "default_val")
            else:
                self.emit("push 0", "default_val")
            self._generate_expr(call.args[1])
            self.emit("push rax", "attr_name")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "obj")
            self.emit("pop rdx", "attr_name")
            self.emit("pop r8", "default_val")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_getattr")
            self.emit("add rsp, 32")
            return

        if func_name == "hasattr" and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "attr_name")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "obj")
            self.emit("pop rdx", "attr_name")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_hasattr")
            self.emit("add rsp, 32")
            return

        if func_name == "setattr" and len(call.args) >= 3:
            self._generate_expr(call.args[2])
            self.emit("push rax", "val")
            self._generate_expr(call.args[1])
            self.emit("push rax", "attr_name")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "obj")
            self.emit("pop rdx", "attr_name")
            self.emit("pop r8", "val")
            self.emit("sub rsp, 32", "shadow space")
            self.emit("call _pyfasm_setattr")
            self.emit("add rsp, 32")
            return

        if func_name in ("sqrt", "math_sqrt", "cmath_sqrt") or (attr_name == "sqrt" and prefix in ("math", "cmath", "np", "numpy", "")):
            if call.args:
                arg0 = call.args[0]
                arg_type = self._infer_expr_type(arg0)
                self._generate_expr(arg0)
                if prefix == "cmath" or func_name == "cmath_sqrt" or arg_type.is_complex():
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_complex_sqrt")
                    self.emit("add rsp, 32")
                elif prefix in ("np", "numpy") and arg_type.is_list():
                    self.emit("mov rcx, rax")
                    self.emit("xor edx, edx", "ufunc 0 = sqrt")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_np_vec_ufunc")
                    self.emit("add rsp, 32")
                else:
                    if arg_type.is_float():
                        self.emit("movq xmm0, rax")
                    else:
                        self.emit("cvtsi2sd xmm0, rax")
                    self.emit("sqrtsd xmm0, xmm0")
                    self.emit("movq rax, xmm0", "return float sqrt")
                return

        if (
            func_name in ("sin", "cos", "tan", "exp", "log", "log10", "floor", "ceil", "math_sin", "math_cos", "math_tan", "math_exp", "math_log", "math_log10", "math_floor", "math_ceil")
            or (attr_name in ("sin", "cos", "tan", "exp", "log", "log10", "floor", "ceil") and prefix in ("math", ""))
        ) and call.args:
            m_op = attr_name or func_name.replace("math_", "")
            at = self._infer_expr_type(call.args[0])
            self._generate_expr(call.args[0])
            if not at.is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rcx, xmm0")
            else:
                self.emit("mov rcx, rax")
            self.emit("sub rsp, 32", "shadow space")
            if m_op in ("floor", "ceil"):
                self.emit(f"call _pyfasm_math_{m_op}_f64")
                self.emit("add rsp, 32")
                self.emit("movq xmm0, rax")
                self.emit("cvttsd2si rax, xmm0", f"Python math.{m_op} returns int")
            else:
                self.emit(f"call _pyfasm_math_{m_op}")
                self.emit("add rsp, 32")
            return

        if (func_name in ("atan2", "hypot", "math_atan2", "math_hypot") or (attr_name in ("atan2", "hypot") and prefix in ("math", ""))) and len(call.args) >= 2:
            m_op = attr_name or func_name.replace("math_", "")
            self._generate_expr(call.args[1])
            if not self._infer_expr_type(call.args[1]).is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rax, xmm0")
            self.emit("push rax")
            self._generate_expr(call.args[0])
            if not self._infer_expr_type(call.args[0]).is_float():
                self.emit("cvtsi2sd xmm0, rax")
                self.emit("movq rax, xmm0")
            self.emit("mov rcx, rax")
            self.emit("pop rdx")
            self.emit("sub rsp, 32", "shadow space")
            self.emit(f"call _pyfasm_math_{m_op}")
            self.emit("add rsp, 32")
            return

        if func_name in ("pow", "math_pow") or (attr_name == "pow" and prefix in ("math", "")):
            if len(call.args) >= 2:
                lt_p = self._infer_expr_type(call.args[0])
                rt_p = self._infer_expr_type(call.args[1])
                if prefix == "math" or func_name == "math_pow" or lt_p.is_float() or rt_p.is_float():
                    self._generate_expr(call.args[1])
                    if not rt_p.is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("push rax")
                    self._generate_expr(call.args[0])
                    if not lt_p.is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("mov rcx, rax")
                    self.emit("pop rdx")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_math_pow_f64")
                    self.emit("add rsp, 32")
                    return
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

        # Native GUI window geometry & resize handling
        if attr_name in ("geometry", "resize", "setFixedSize", "minsize", "maxsize"):
            if attr_name in ("resize", "setFixedSize") and len(call.args) >= 2 and self.target in ("win64", "dll", "linux", "macos", "apple", "myos"):
                self._generate_expr(call.args[1])
                self.emit("push rax", "save height")
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax", "width")
                self.emit("pop rdx", "height")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_resize_window")
                self.emit("add rsp, 32")
                return
            if attr_name == "geometry" and call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str) and self.target in ("win64", "dll", "linux", "macos", "apple", "myos"):
                m_geo = re.match(r"^\s*(\d+)\s*x\s*(\d+)", call.args[0].value)
                if m_geo:
                    w, h = int(m_geo.group(1)), int(m_geo.group(2))
                    self.emit(f"mov rcx, {w}")
                    self.emit(f"mov rdx, {h}")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_resize_window")
                    self.emit("add rsp, 32")
                    return
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

        if (
            func_name in ("alert", "message_box")
            or prefix in ("messagebox", "msgbox", "qmessagebox")
            or attr_name in ("showinfo", "showerror", "showwarning", "information", "warning", "critical", "about", "question")
            and (
                prefix in ("messagebox", "msgbox", "qmessagebox")
                or (isinstance(call.func, ast.Attribute) and getattr(call.func.value, "id", "") == "QMessageBox")
                or attr_name in ("showinfo", "showerror", "showwarning")
                or func_name in ("alert", "message_box")
            )
        ):
            is_qmsg = prefix == "qmessagebox" or (isinstance(call.func, ast.Attribute) and getattr(call.func.value, "id", "") == "QMessageBox")
            if is_qmsg and len(call.args) >= 3:
                title_arg, msg_arg = call.args[1], call.args[2]
            elif len(call.args) >= 2:
                title_arg, msg_arg = call.args[0], call.args[1]
            else:
                title_arg, msg_arg = None, (call.args[0] if call.args else None)

            if title_arg is not None and msg_arg is not None:
                self._generate_expr(msg_arg)
                self.emit("push rax", "message text")
                self._generate_expr(title_arg)
                self.emit("mov rcx, rax", "title text")
                self.emit("pop rdx", "message text")
            elif msg_arg is not None:
                self._generate_expr(msg_arg)
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

            # Check if any user-defined class method matches (e.g. AppTray_run)
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

            if (
                attr_name == "show"
                and not is_icon_call
                and self.module.has_library("pyqt5", "pyqt6", "pyside6", "pyside2", "qt")
            ):
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "Qt window HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_show_window")
                self.emit("add rsp, 32")
                return

            # Run the native GUI window or tray loop
            is_tray = (
                is_icon_call
                or getattr(self.module, "is_tray_app", False)
                or any(k in s.lower() for k in ("tray", "pystray") for s in module_classes)
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
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_stringvar_create")
            self.emit("add rsp, 32")
            return

        if func_name in ("get_appearance_mode", "ctk_get_appearance_mode") or attr_name == "get_appearance_mode":
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_darkdetect_theme")
            self.emit("add rsp, 32")
            return

        if func_name in ("set_appearance_mode", "ctk_set_appearance_mode") or attr_name == "set_appearance_mode":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_set_appearance_mode")
                self.emit("add rsp, 32")
            return

        if func_name in ("set_default_color_theme", "ctk_set_default_color_theme") or attr_name == "set_default_color_theme":
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_set_default_color_theme")
                self.emit("add rsp, 32")
            return

        if (
            attr_name in ("askopenfilename", "asksaveasfilename", "getOpenFileName", "getSaveFileName")
            and any(k in prefix.lower() for k in ("filedialog", "qfiledialog", "tk", "qt"))
        ) or (
            attr_name in ("askopenfilename", "asksaveasfilename", "getOpenFileName", "getSaveFileName") and not prefix
        ) or func_name in ("askopenfilename", "asksaveasfilename", "getOpenFileName", "getSaveFileName"):
            is_qt_fd = attr_name in ("getOpenFileName", "getSaveFileName") or func_name in ("getOpenFileName", "getSaveFileName")
            is_save = attr_name in ("asksaveasfilename", "getSaveFileName") or func_name in ("asksaveasfilename", "getSaveFileName")
            title_kw = (
                self._extract_kwarg(call, "caption")
                or self._extract_kwarg(call, "title")
                or (call.args[1] if is_qt_fd and len(call.args) >= 2 else None)
            )
            if is_save:
                defext_kw = self._extract_kwarg(call, "defaultextension")
                initf_kw = self._extract_kwarg(call, "initialfile") or (
                    call.args[2] if is_qt_fd and len(call.args) >= 3 else None
                )
                self.emit("sub rsp, 32")
                if title_kw:
                    self._generate_expr(title_kw)
                    self.emit("mov [rsp], rax")
                else:
                    self.emit("mov qword [rsp], 0")
                if defext_kw:
                    self._generate_expr(defext_kw)
                    self.emit("mov [rsp + 8], rax")
                else:
                    self.emit("mov qword [rsp + 8], 0")
                if initf_kw:
                    self._generate_expr(initf_kw)
                    self.emit("mov [rsp + 16], rax")
                else:
                    self.emit("mov qword [rsp + 16], 0")
                self.emit("mov rcx, [rsp]")
                self.emit("mov rdx, [rsp + 8]")
                self.emit("xor r8d, r8d")
                self.emit("mov r9, [rsp + 16]")
                self.emit("add rsp, 32")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_filedialog_save")
                self.emit("add rsp, 32")
            else:
                if title_kw:
                    self._generate_expr(title_kw)
                    self.emit("mov rcx, rax")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("xor edx, edx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_filedialog_open")
                self.emit("add rsp, 32")
            if is_qt_fd:
                self.emit("push rax", "save selected path")
                self.emit("mov rcx, 32")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_alloc")
                self.emit("add rsp, 32")
                self.emit("mov qword [rax], 2", "Qt (path, filter) 2-tuple")
                self.emit("pop rdx")
                self.emit("mov [rax + 8], rdx")
                self._emit_string_pointer("rdx", "")
                self.emit("mov [rax + 16], rdx")
            return

        if attr_name in ("showinfo", "showwarning", "showerror") and ("messagebox" in prefix.lower() or not prefix):
            flags = 0x10 if attr_name == "showerror" else (0x30 if attr_name == "showwarning" else 0x40)
            t_node = self._extract_kwarg(call, "title") or (call.args[0] if call.args else None)
            m_node = self._extract_kwarg(call, "message") or (call.args[1] if len(call.args) >= 2 else None)
            if m_node:
                self._generate_expr(m_node)
                self.emit("push rax")
            else:
                self.emit("push 0")
            if t_node:
                self._generate_expr(t_node)
                self.emit("mov rcx, rax")
            else:
                self.emit("xor ecx, ecx")
            self.emit("pop rdx")
            self.emit(f"mov r8d, {flags}")
            self.emit("sub rsp, 32")
            self.emit("call _pyfasm_msgbox_info")
            self.emit("add rsp, 32")
            return

        if attr_name in ("trace_add", "trace", "trace_variable") and isinstance(call.func, ast.Attribute) and len(call.args) >= 1:
            cb_arg = call.args[1] if len(call.args) >= 2 else call.args[0]
            mode_arg = call.args[0] if len(call.args) >= 2 else None
            if self._emit_control_callback_to_rax(cb_arg):
                self.emit("push rax", "trace callback")
                if mode_arg is not None:
                    self._generate_expr(mode_arg)
                    self.emit("push rax", "trace mode")
                else:
                    self.emit("push 0")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "StringVar ptr")
                self.emit("pop rdx", "mode")
                self.emit("pop r8", "callback ptr")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_stringvar_trace")
                self.emit("add rsp, 32")
            return

        # Numpy wrappers
        if prefix in ("np", "numpy") or func_name.startswith("np_") or func_name.startswith("numpy_"):
            np_m = attr_name or (func_name[3:] if func_name.startswith("np_") else func_name[6:])
            kw_map = {k.arg: k.value for k in getattr(call, "keywords", []) if k.arg}
            if np_m in ("asarray", "array", "asanyarray", "complex128", "float64"):
                if call.args:
                    if self._is_generator_expr(call.args[0]):
                        self._generate_expr(call.args[0])
                        self.emit("mov rcx, rax")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_gen_to_list")
                        self.emit("add rsp, 32")
                    else:
                        self._generate_expr(call.args[0])
                else:
                    self.emit("xor ecx, ecx")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_list_create")
                    self.emit("add rsp, 32")
                return
            elif np_m == "column_stack" and call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_column_stack")
                self.emit("add rsp, 32")
                return
            elif np_m == "linspace" and len(call.args) >= 2:
                num_node = kw_map.get("num", call.args[2] if len(call.args) >= 3 else None)
                if num_node is not None:
                    self._generate_expr(num_node)
                else:
                    self.emit("mov rax, 50")
                self.emit("push rax", "num")
                self._generate_expr(call.args[1])
                if not self._infer_expr_type(call.args[1]).is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("push rax", "stop")
                self._generate_expr(call.args[0])
                if not self._infer_expr_type(call.args[0]).is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rax, xmm0")
                self.emit("mov rcx, rax", "start")
                self.emit("pop rdx", "stop")
                self.emit("pop r8", "num")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_linspace")
                self.emit("add rsp, 32")
                return
            elif np_m == "arange" and call.args:
                if len(call.args) == 1:
                    self.emit("xor eax, eax")
                    self.emit("push rax", "start=0.0")
                    self._generate_expr(call.args[0])
                    if not self._infer_expr_type(call.args[0]).is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("push rax", "stop")
                    self._emit_float_bits("rax", 1.0)
                    self.emit("mov r8, rax", "step=1.0")
                else:
                    step_node = kw_map.get("step", call.args[2] if len(call.args) >= 3 else None)
                    if step_node is not None:
                        self._generate_expr(step_node)
                        if not self._infer_expr_type(step_node).is_float():
                            self.emit("cvtsi2sd xmm0, rax")
                            self.emit("movq rax, xmm0")
                    else:
                        self._emit_float_bits("rax", 1.0)
                    self.emit("push rax", "step")
                    self._generate_expr(call.args[1])
                    if not self._infer_expr_type(call.args[1]).is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("push rax", "stop")
                    self._generate_expr(call.args[0])
                    if not self._infer_expr_type(call.args[0]).is_float():
                        self.emit("cvtsi2sd xmm0, rax")
                        self.emit("movq rax, xmm0")
                    self.emit("mov rcx, rax", "start")
                    self.emit("pop rdx", "stop")
                    self.emit("pop r8", "step")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_np_arange")
                    self.emit("add rsp, 32")
                    return
                self.emit("pop rdx", "stop")
                self.emit("pop rcx", "start")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_arange")
                self.emit("add rsp, 32")
                return
            elif np_m == "empty":
                if call.args:
                    self._generate_expr(call.args[0])
                    self.emit("mov rcx, rax")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_empty")
                self.emit("add rsp, 32")
                return
            elif np_m in ("all", "any") and call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call _pyfasm_np_{np_m}")
                self.emit("add rsp, 32")
                return
            elif np_m in ("isfinite", "isnan", "sin", "cos", "tan", "exp", "log", "log10", "floor", "ceil") and call.args:
                uid_map = {
                    "sqrt": 0, "sin": 1, "cos": 2, "tan": 3, "exp": 4,
                    "log": 5, "abs": 6, "isfinite": 7, "isnan": 8,
                    "floor": 9, "ceil": 10, "log10": 11,
                }
                at = self._infer_expr_type(call.args[0])
                self._generate_expr(call.args[0])
                if not at.is_list() and not at.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rcx, xmm0")
                else:
                    self.emit("mov rcx, rax")
                self.emit(f"mov edx, {uid_map[np_m]}")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_vec_ufunc")
                self.emit("add rsp, 32")
                return
            elif np_m == "sign" and call.args:
                at = self._infer_expr_type(call.args[0])
                self._generate_expr(call.args[0])
                if not at.is_list() and not at.is_float():
                    self.emit("cvtsi2sd xmm0, rax")
                    self.emit("movq rcx, xmm0")
                else:
                    self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_np_sign_f64")
                self.emit("add rsp, 32")
                return
            elif np_m in ("ptp", "min", "amin", "max", "amax", "sum", "mean") and call.args:
                norm_m = {"amin": "min", "amax": "max"}.get(np_m, np_m)
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32", "shadow space")
                self.emit(f"call _pyfasm_np_{norm_m}_f64")
                self.emit("add rsp, 32")
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

        # Check Native GUI controls
        is_gui_app = "gui" in self.features or getattr(self.module, "is_modern_gui", False) or getattr(self.module, "is_gui_app", False) or (self.module.ui_spec and not self.module.ui_spec.is_empty())

        if self.target in ("win64", "dll", "linux", "macos", "apple", "myos") and is_gui_app:
            recv_cls = self.resolve_instance_class(call.func.value) if isinstance(call.func, ast.Attribute) else None
            curr_cls = getattr(self.current_func, "class_name", None)
            is_user_class_method = bool(
                (recv_cls and self.resolve_class_method(recv_cls, attr_name))
                or (prefix in ("self", "this") and curr_cls and self.resolve_class_method(curr_cls, attr_name))
            )

            # 1. Widget UI methods: .get()
            if attr_name == "get" and len(call.args) == 0 and not is_user_class_method:
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
            if attr_name == "set" and len(call.args) == 1 and isinstance(call.func, ast.Attribute) and not is_user_class_method:
                self._generate_expr(call.args[0])
                self.emit("push rax", "new value")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "target widget or StringVar")
                self.emit("pop rdx", "new value")
                self.emit("call _pyfasm_unified_set", "set native widget or StringVar value")
                return

            # Canvas clear: canvas.delete("all")
            if attr_name == "delete" and call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == "all" and not is_user_class_method:
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "canvas HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_canvas_clear")
                self.emit("add rsp, 32")
                return

            # GUI window destroy
            if attr_name == "destroy" and "gui" in self.features and not is_user_class_method:
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "window HWND")
                else:
                    self.emit("xor ecx, ecx")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_destroy_window")
                self.emit("add rsp, 32")
                return

            # 2. Widget UI methods: .delete() / .clear()
            if attr_name in ("delete", "clear") and not is_user_class_method:
                if call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == "all":
                    if isinstance(call.func, ast.Attribute):
                        self._generate_expr(call.func.value)
                        self.emit("mov rcx, rax", "canvas HWND")
                    else:
                        self.emit("xor ecx, ecx")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_canvas_clear")
                    self.emit("add rsp, 32")
                    return
                if any(k in prefix.lower() for k in ("list", "listbox", "combo", "select")):
                    self.emit("xor ecx, ecx")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_listbox_clear", "clear native listbox")
                    self.emit("add rsp, 32")
                    self.emit("xor eax, eax")
                    return
                # Default for .delete(...) or .clear() on native controls (Entry, Text, Input, Search)
                if isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "target control HWND")
                else:
                    self.emit("mov rcx, [_pyfasm_last_edit_hwnd]")
                self._emit_string_pointer("rdx", "")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_set_text", "clear native edit box")
                self.emit("add rsp, 32")
                self.emit("xor eax, eax")
                return

            # 3. Widget UI methods: .insert() / .add()
            if not is_user_class_method:
                if attr_name == "insert" and (
                    any(k in prefix.lower() for k in ("ent", "entry", "search", "filter", "edit", "txt", "input", "inp"))
                    or (isinstance(call.func, ast.Attribute) and not self._infer_expr_type(call.func.value).is_list())
                ):
                    if call.args:
                        is_end = len(call.args) >= 2 and (
                            (
                                isinstance(call.args[0], ast.Constant)
                                and isinstance(call.args[0].value, str)
                                and call.args[0].value.lower() == "end"
                            )
                            or (
                                isinstance(call.args[0], ast.Attribute)
                                and call.args[0].attr.lower() == "end"
                            )
                        )
                        self._generate_expr(call.args[-1])
                        self.emit("push rax", "new text/item")
                        if isinstance(call.func, ast.Attribute):
                            self._generate_expr(call.func.value)
                            self.emit("mov rcx, rax", "target control HWND")
                        else:
                            self.emit("mov rcx, [_pyfasm_last_edit_hwnd]")
                        self.emit("pop rdx", "new text/item")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_textbox_append" if is_end else "call _pyfasm_set_text")
                        self.emit("add rsp, 32")
                    self.emit("xor eax, eax")
                    return

                if attr_name in ("insert", "add", "add_item") and any(k in prefix.lower() for k in ("list", "listbox", "combo", "select")):
                    if call.args:
                        self._generate_expr(call.args[-1])
                        self.emit("mov rdx, rax")
                        self.emit("mov rcx, [_pyfasm_last_list_hwnd]")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_listbox_add")
                        self.emit("add rsp, 32")
                    self.emit("xor eax, eax")
                    return

                if attr_name in ("add", "add_tab") and any(k in prefix.lower() for k in ("tab", "tabs", "tabview", "notebook")):
                    self.emit("mov rax, [_pyfasm_h_wnd]", "return tab frame HWND")
                    return

                if attr_name == "add" and any(k in prefix.lower() for k in ("page", "ft_page", "view")):
                    self.emit("xor ecx, ecx")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_show_window")
                    self.emit("add rsp, 32")
                    self.emit("xor eax, eax")
                    return

            # Widget UI method: .cget()
            if attr_name == "cget" and isinstance(call.func, ast.Attribute) and not is_user_class_method:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "target control HWND")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_unified_get")
                self.emit("add rsp, 32")
                return

            # 4. Widget configuration (configure / config)
            if attr_name in ("configure", "config") and not is_user_class_method:
                text_kw = self._extract_kwarg(call, "text")
                fg_kw = self._extract_kwarg(call, "fg_color") or self._extract_kwarg(call, "bg") or self._extract_kwarg(call, "background")
                tc_kw = self._extract_kwarg(call, "text_color") or self._extract_kwarg(call, "fg") or self._extract_kwarg(call, "foreground")
                vals_kw = self._extract_kwarg(call, "values")
                state_kw = self._extract_kwarg(call, "state")
                fg_packed = self._extract_color_packed(call, "fg_color", "bg", "background")
                tc_packed = self._extract_color_packed(call, "text_color", "fg", "foreground")
                if text_kw is not None and fg_kw is None and tc_kw is None and vals_kw is None and state_kw is None:
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
                if any(x is not None for x in (text_kw, fg_kw, tc_kw, fg_packed, tc_packed, vals_kw, state_kw)):
                    self.emit("sub rsp, 64", "configure frame")
                    if isinstance(call.func, ast.Attribute):
                        self._generate_expr(call.func.value)
                        self.emit("mov [rsp], rax")
                    else:
                        self.emit("mov qword [rsp], 0")
                    if text_kw is not None:
                        self._generate_expr(text_kw)
                        self.emit("mov [rsp + 8], rax")
                    else:
                        self.emit("mov qword [rsp + 8], 0")
                    if fg_packed is not None:
                        self.emit(f"mov rax, 0x{fg_packed:016X}")
                        self.emit("mov [rsp + 16], rax")
                    elif fg_kw is not None and not isinstance(fg_kw, (ast.Tuple, ast.List)):
                        self._generate_expr(fg_kw)
                        self.emit("mov rcx, rax")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_parse_color")
                        self.emit("add rsp, 32")
                        self.emit("mov [rsp + 16], rax")
                    else:
                        self.emit("mov qword [rsp + 16], 0")
                    if tc_packed is not None:
                        self.emit(f"mov rax, 0x{tc_packed:016X}")
                        self.emit("mov [rsp + 24], rax")
                    elif tc_kw is not None and not isinstance(tc_kw, (ast.Tuple, ast.List)):
                        self._generate_expr(tc_kw)
                        self.emit("mov rcx, rax")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_parse_color")
                        self.emit("add rsp, 32")
                        self.emit("mov [rsp + 24], rax")
                    else:
                        self.emit("mov qword [rsp + 24], 0")
                    if vals_kw is not None:
                        self._generate_expr(vals_kw)
                        self.emit("mov [rsp + 48], rax")
                    else:
                        self.emit("mov qword [rsp + 48], 0")
                    if state_kw is not None:
                        self._generate_expr(state_kw)
                        self.emit("mov [rsp + 56], rax")
                    else:
                        self.emit("mov qword [rsp + 56], 0")
                    self.emit("mov rcx, [rsp]")
                    self.emit("mov rdx, [rsp + 8]")
                    self.emit("mov r8, [rsp + 16]")
                    self.emit("mov r9, [rsp + 24]")
                    self.emit("mov rax, [rsp + 48]")
                    self.emit("mov [rsp + 32], rax")
                    self.emit("mov rax, [rsp + 56]")
                    self.emit("mov [rsp + 40], rax")
                    self.emit("call _pyfasm_widget_configure")
                    self.emit("add rsp, 64")
                    return
                self.emit("xor eax, eax", f"configure '{attr_name}' no-op")
                return

            # Qt / Tkinter / CustomTkinter / Flet window constructors & widget methods
            raw_ctor = attr_name or func_name
            raw_ctor = attr_name or func_name
            raw_ctor_lower = raw_ctor.lower()
            is_user_defined_call = (
                is_user_class_method
                or (isinstance(call.func, ast.Name) and (func_name in self.module.functions or func_name in self.module.classes))
            )

            if raw_ctor in ("Tk", "CTk", "QMainWindow", "QDialog") and raw_ctor not in self.module.classes and not is_user_defined_call:
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_ensure_window")
                self.emit("add rsp, 32")
                self.emit("mov rax, [_pyfasm_h_wnd]", f"return main window handle for {raw_ctor}")
                return

            if raw_ctor == "QWidget" and raw_ctor not in self.module.classes and not is_user_defined_call:
                parent_node = self._extract_parent_container_node(call)
                if parent_node is not None:
                    self._generate_expr(parent_node)
                    self.emit("mov rcx, rax", "QWidget parent container")
                else:
                    self.emit("xor ecx, ecx", "default root container")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_qt_create_widget")
                self.emit("add rsp, 32")
                return

            if raw_ctor == "QApplication" and not is_user_defined_call:
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_init_gui")
                self.emit("add rsp, 32")
                self.emit("mov rax, [_pyfasm_h_wnd]")
                return

            if not is_user_defined_call and raw_ctor_lower in ("ctkfont", "tkfont", "font", "qfont"):
                fam_node = self._extract_kwarg(call, "family") or (
                    call.args[0]
                    if call.args and (raw_ctor_lower == "qfont" or (isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)))
                    else None
                )
                sz_val = self._extract_kwarg_int(call, "size", 13)
                if sz_val == 13 and len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, int):
                    sz_val = call.args[1].value
                wt_str = (self._get_kwarg_string_val(call, "weight") or "").lower()
                sl_str = (self._get_kwarg_string_val(call, "slant") or "").lower()
                is_bold = 1 if "bold" in wt_str else 0
                is_italic = 1 if "italic" in sl_str else 0
                if len(call.args) >= 3:
                    arg2_txt = ast.unparse(call.args[2]).lower()
                    if "bold" in arg2_txt or (isinstance(call.args[2], ast.Constant) and isinstance(call.args[2].value, int) and call.args[2].value >= 75):
                        is_bold = 1
                if len(call.args) >= 4 and isinstance(call.args[3], ast.Constant) and bool(call.args[3].value):
                    is_italic = 1
                if fam_node is not None:
                    self._generate_expr(fam_node)
                    self.emit("mov rcx, rax")
                else:
                    self.emit("xor ecx, ecx")
                self.emit(f"mov rdx, {sz_val}")
                self.emit(f"mov r8d, {is_bold}")
                self.emit(f"mov r9d, {is_italic}")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_create_font")
                self.emit("add rsp, 32")
                return

            if raw_ctor == "QTimer" and raw_ctor not in self.module.classes and not is_user_defined_call:
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_qtimer_new")
                self.emit("add rsp, 32")
                return

            if any(k in call_name_lower for k in ("ctkimage", "tkimage")) or (call_name_lower == "image" and raw_ctor in ("CTkImage", "PhotoImage")):
                self.emit("mov rax, 1", "dummy GUI Image handle")
                return

            if (
                attr_name == "connect"
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Attribute)
                and call.func.value.attr == "timeout"
                and call.args
            ):
                if self._emit_control_callback_to_rax(call.args[0]):
                    self.emit("push rax", "save timer slot callback")
                    self._generate_expr(call.func.value.value)
                    self.emit("mov rcx, rax", "QTimer pointer")
                    self.emit("pop rdx", "callback pointer")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_qtimer_connect")
                    self.emit("add rsp, 32")
                else:
                    self.emit("xor eax, eax")
                return

            if (
                attr_name == "connect"
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Attribute)
                and call.func.value.attr in (
                    "clicked", "stateChanged", "toggled", "triggered",
                    "textChanged", "currentTextChanged", "currentIndexChanged",
                    "valueChanged", "editingFinished", "returnPressed",
                )
                and call.args
            ):
                if self._emit_control_callback_to_rax(call.args[0]):
                    self.emit("push rax", "save signal slot callback")
                    self._generate_expr(call.func.value.value)
                    self.emit("mov rcx, rax", "control HWND")
                    self.emit("pop rdx", "callback pointer")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_register_control_callback")
                    self.emit("add rsp, 32")
                else:
                    self.emit("xor eax, eax")
                return

            if attr_name == "setText" and call.args and isinstance(call.func, ast.Attribute):
                self._generate_expr(call.args[0])
                self.emit("push rax", "new widget text")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit("pop rdx", "new widget text")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_set_text")
                self.emit("add rsp, 32")
                return

            if attr_name in ("text", "toPlainText") and len(call.args) == 0 and isinstance(call.func, ast.Attribute) and "gui" in self.features:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_unified_get")
                self.emit("add rsp, 32")
                return

            if attr_name == "isChecked" and isinstance(call.func, ast.Attribute):
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "checkbox HWND")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_checkbox_get")
                self.emit("add rsp, 32")
                return

            if attr_name == "setChecked" and call.args and isinstance(call.func, ast.Attribute):
                self._generate_expr(call.args[0])
                self.emit("push rax", "checked state")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "checkbox HWND")
                self.emit("pop rdx", "checked state")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_checkbox_set")
                self.emit("add rsp, 32")
                return

            if attr_name in ("addItem", "addItems") and call.args and isinstance(call.func, ast.Attribute):
                self._generate_expr(call.args[0])
                self.emit("push rax", "item text")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "listbox/combobox HWND")
                self.emit("pop rdx", "item text or list")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_listbox_add")
                self.emit("add rsp, 32")
                return

            if raw_ctor in ("QVBoxLayout", "QHBoxLayout", "QGridLayout") and not is_user_defined_call:
                kind_num = 1 if raw_ctor == "QVBoxLayout" else (2 if raw_ctor == "QHBoxLayout" else 3)
                if call.args:
                    self._generate_expr(call.args[0])
                    self.emit("mov rdx, rax", "layout parent HWND")
                else:
                    self.emit("xor edx, edx", "unattached layout")
                self.emit(f"mov rcx, {kind_num}", f"{raw_ctor} kind")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_qt_layout_new")
                self.emit("add rsp, 32")
                return

            if attr_name == "addWidget" and isinstance(call.func, ast.Attribute) and call.args and not is_user_defined_call:
                self.emit("sub rsp, 64", "aligned frame for qt_layout_add_widget")
                self._generate_expr(call.func.value)
                self.emit("mov [rsp + 48], rax", "layout ptr")
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 56], rax", "child widget HWND")
                if len(call.args) >= 2:
                    self._generate_expr(call.args[1])
                    self.emit("mov r8, rax", "row / stretch")
                else:
                    self.emit("xor r8d, r8d")
                if len(call.args) >= 3:
                    self.emit("push r8")
                    self._generate_expr(call.args[2])
                    self.emit("mov r9, rax", "col")
                    self.emit("pop r8")
                else:
                    self.emit("xor r9d, r9d")
                if len(call.args) >= 4:
                    self.emit("push r8")
                    self.emit("push r9")
                    self._generate_expr(call.args[3])
                    self.emit("pop r9")
                    self.emit("pop r8")
                    self.emit("mov [rsp + 32], rax", "rowspan")
                else:
                    self.emit("mov qword [rsp + 32], 1")
                if len(call.args) >= 5:
                    self.emit("push r8")
                    self.emit("push r9")
                    self._generate_expr(call.args[4])
                    self.emit("pop r9")
                    self.emit("pop r8")
                    self.emit("mov [rsp + 40], rax", "colspan")
                else:
                    self.emit("mov qword [rsp + 40], 1")
                self.emit("mov rcx, [rsp + 48]")
                self.emit("mov rdx, [rsp + 56]")
                self.emit("call _pyfasm_qt_layout_add_widget")
                self.emit("add rsp, 64")
                return

            if attr_name == "addLayout" and isinstance(call.func, ast.Attribute) and call.args and not is_user_defined_call:
                self.emit("sub rsp, 48", "aligned frame for qt_layout_add_layout")
                self._generate_expr(call.func.value)
                self.emit("mov [rsp + 32], rax", "layout ptr")
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 40], rax", "sublayout ptr")
                if len(call.args) >= 2:
                    self._generate_expr(call.args[1])
                    self.emit("mov r8, rax", "row")
                else:
                    self.emit("xor r8d, r8d")
                if len(call.args) >= 3:
                    self.emit("push r8")
                    self._generate_expr(call.args[2])
                    self.emit("mov r9, rax", "col")
                    self.emit("pop r8")
                else:
                    self.emit("xor r9d, r9d")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("call _pyfasm_qt_layout_add_layout")
                self.emit("add rsp, 48")
                return

            if attr_name == "addStretch" and not is_user_defined_call:
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_layout_add_stretch")
                self.emit("add rsp, 32")
                return

            if attr_name == "setContentsMargins" and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                self._generate_expr(call.func.value)
                self.emit("push rax", "layout ptr")
                if call.args:
                    self._generate_expr(call.args[0])
                    self.emit("mov rdx, rax", "margin")
                else:
                    self.emit("mov edx, 8")
                self.emit("pop rcx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_layout_set_margins")
                self.emit("add rsp, 32")
                return

            if attr_name == "setSpacing" and not is_user_defined_call:
                self.emit("xor eax, eax", "Qt layout spacing no-op")
                return

            if attr_name == "setLayout" and call.args and not is_user_defined_call:
                self._generate_expr(call.args[0])
                self.emit("push rax", "layout ptr")
                if isinstance(call.func, ast.Attribute) and not (
                    isinstance(call.func.value, ast.Name) and call.func.value.id in ("self", "this")
                ):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "owner HWND")
                else:
                    self.emit("mov rcx, [_pyfasm_h_wnd]", "window HWND")
                self.emit("pop rdx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_widget_set_layout")
                self.emit("add rsp, 32")
                return

            if attr_name == "setCentralWidget" and call.args and not is_user_defined_call:
                self._generate_expr(call.args[0])
                self.emit("push rax", "central HWND")
                if isinstance(call.func, ast.Attribute) and not (
                    isinstance(call.func.value, ast.Name) and call.func.value.id in ("self", "this")
                ):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "main window HWND")
                else:
                    self.emit("mov rcx, [_pyfasm_h_wnd]", "main window HWND")
                self.emit("pop rdx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_set_central_widget")
                self.emit("add rsp, 32")
                return

            if attr_name == "addTab" and isinstance(call.func, ast.Attribute) and len(call.args) >= 2 and not is_user_defined_call:
                self.emit("sub rsp, 48")
                self._generate_expr(call.func.value)
                self.emit("mov [rsp + 32], rax", "tab widget HWND")
                self._generate_expr(call.args[0])
                self.emit("mov [rsp + 40], rax", "page HWND")
                self._generate_expr(call.args[1])
                self.emit("mov r8, rax", "tab title")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("call _pyfasm_qt_tab_add")
                self.emit("add rsp, 48")
                return

            if attr_name == "currentText" and len(call.args) == 0 and isinstance(call.func, ast.Attribute) and "gui" in self.features and not is_user_defined_call:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "combobox HWND")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_unified_get")
                self.emit("add rsp, 32")
                return

            if attr_name == "currentIndex" and len(call.args) == 0 and isinstance(call.func, ast.Attribute) and "gui" in self.features and not is_user_defined_call:
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "combobox HWND")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_combobox_index")
                self.emit("add rsp, 32")
                return

            if attr_name == "setCurrentIndex" and call.args and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                self._generate_expr(call.args[0])
                self.emit("push rax", "index")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "combobox HWND")
                self.emit("pop rdx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_combobox_set_index")
                self.emit("add rsp, 32")
                return

            if attr_name == "setValue" and call.args and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                self._generate_expr(call.args[0])
                self.emit("push rax", "widget value")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit("pop rdx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_set_value")
                self.emit("add rsp, 32")
                return

            if (
                attr_name == "value"
                and len(call.args) == 0
                and isinstance(call.func, ast.Attribute)
                and "gui" in self.features
                and not is_user_defined_call
                and not self._infer_expr_type(call.func.value).is_dict()
                and not self._infer_expr_type(call.func.value).is_set()
            ):
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qt_get_value")
                self.emit("add rsp, 32")
                return

            if attr_name == "setRange" and len(call.args) >= 2 and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                self.emit("sub rsp, 48")
                self._generate_expr(call.func.value)
                self.emit("mov [rsp + 32], rax", "widget HWND")
                self._generate_expr(call.args[0])
                if self._infer_expr_type(call.args[0]).is_float():
                    self.emit("movq xmm0, rax")
                    self.emit("cvttsd2si rax, xmm0")
                self.emit("mov [rsp + 40], rax", "min")
                self._generate_expr(call.args[1])
                if self._infer_expr_type(call.args[1]).is_float():
                    self.emit("movq xmm0, rax")
                    self.emit("cvttsd2si rax, xmm0")
                self.emit("mov r8, rax", "max")
                self.emit("mov rcx, [rsp + 32]")
                self.emit("mov rdx, [rsp + 40]")
                self.emit("call _pyfasm_qt_set_range")
                self.emit("add rsp, 48")
                return

            if attr_name == "setFont" and call.args and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                self._generate_expr(call.args[0])
                self.emit("push rax", "HFONT handle")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit("pop rdx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_widget_set_font")
                self.emit("add rsp, 32")
                return

            if attr_name == "setStyleSheet" and call.args and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                fg_p64 = 0
                tc_p64 = 0
                if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                    css_l = call.args[0].value.lower()
                    for part in css_l.split(";"):
                        if ":" not in part or "#" not in part:
                            continue
                        k_css, v_css = part.split(":", 1)
                        k_css = k_css.strip().split()[-1] if k_css.strip() else ""
                        idx_h = v_css.find("#")
                        hex6 = v_css[idx_h + 1:idx_h + 7] if idx_h >= 0 else ""
                        if len(hex6) == 6 and all(c in "0123456789abcdef" for c in hex6):
                            rv, gv, bv = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
                            u32 = 0x01000000 | (bv << 16) | (gv << 8) | rv
                            p64 = (1 << 63) | (u32 << 32) | u32
                            if k_css in ("background-color", "background"):
                                fg_p64 = p64
                            elif k_css == "color":
                                tc_p64 = p64
                if fg_p64 or tc_p64:
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax", "widget HWND")
                    self.emit("xor edx, edx")
                    if fg_p64:
                        self.emit(f"mov r8, {fg_p64}")
                    else:
                        self.emit("xor r8d, r8d")
                    if tc_p64:
                        self.emit(f"mov r9, {tc_p64}")
                    else:
                        self.emit("xor r9d, r9d")
                    self.emit("sub rsp, 64")
                    self.emit("mov qword [rsp + 32], 0")
                    self.emit("mov qword [rsp + 40], 0")
                    self.emit("call _pyfasm_widget_configure")
                    self.emit("add rsp, 64")
                else:
                    self.emit("xor eax, eax", "Qt setStyleSheet no-op")
                return

            if (
                attr_name == "start"
                and isinstance(call.func, ast.Attribute)
                and "gui" in self.features
                and self.module.has_library("pyqt5", "pyqt6", "pyside6", "pyside2", "qt")
                and not is_user_defined_call
                and "thread" not in ast.unparse(call.func.value).lower()
            ):
                if call.args:
                    self._generate_expr(call.args[0])
                    self.emit("push rax", "interval ms")
                else:
                    self.emit("push 0")
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "QTimer pointer")
                self.emit("pop rdx")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_qtimer_start")
                self.emit("add rsp, 32")
                return

            if attr_name == "setInterval" and call.args and isinstance(call.func, ast.Attribute) and not is_user_defined_call:
                self._generate_expr(call.args[0])
                self.emit("push rax", "interval ms")
                self._generate_expr(call.func.value)
                self.emit("pop rdx")
                lbl_si_done = self.new_label("qtimer_si")
                self.emit("test rax, rax")
                self.emit(f"jz {lbl_si_done}")
                self.emit("mov r10, 5059465154494D52h")
                self.emit("cmp qword [rax], r10")
                self.emit(f"jne {lbl_si_done}")
                self.emit("mov [rax + 16], rdx")
                self.emit_raw(f"{lbl_si_done}:")
                self.emit("xor eax, eax")
                return

            if (
                attr_name in (
                    "setPlaceholderText", "setReadOnly", "setAlignment", "setWordWrap",
                    "setMinimumSize", "setMaximumSize", "setMaximumWidth", "setMaximumHeight",
                    "setMinimumWidth", "setMinimumHeight", "setFixedWidth", "setFixedHeight",
                    "setEnabled", "setVisible", "setEchoMode", "setTickPosition",
                )
                and isinstance(call.func, ast.Attribute)
                and "gui" in self.features
                and not is_user_defined_call
            ):
                self.emit("xor eax, eax", f"Qt widget attribute {attr_name}")
                return

            if self.module.has_library("flet"):
                if (attr_name == "app" and prefix in ("ft", "flet")) or func_name == "app":
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_ensure_window")
                    self.emit("add rsp, 32")
                    target_node = self._extract_kwarg(call, "target") or (call.args[0] if call.args else None)
                    if target_node is not None:
                        if isinstance(target_node, ast.Name) and target_node.id in self.module.functions and not (
                            self.current_func and hasattr(self.current_func, "local_vars") and target_node.id in self.current_func.local_vars
                        ):
                            self.emit("mov rcx, [_pyfasm_h_wnd]", "pass page handle")
                            self.emit("sub rsp, 32", "shadow space")
                            self.emit(f"call {safe_asm_label(target_node.id)}")
                            self.emit("add rsp, 32")
                        elif self._emit_control_callback_to_rax(target_node):
                            lbl_plain = self.new_label("ft_plain")
                            lbl_done = self.new_label("ft_done")
                            self.emit("test rax, rax")
                            self.emit(f"jz {lbl_done}")
                            self.emit("mov r10, 505946434C4F5355h")
                            self.emit("cmp qword [rax], r10")
                            self.emit(f"jne {lbl_plain}")
                            self.emit("mov rcx, rax", "closure env")
                            self.emit("mov rdx, [_pyfasm_h_wnd]", "pass page handle")
                            self.emit("sub rsp, 32")
                            self.emit("call qword [rax + 8]")
                            self.emit("add rsp, 32")
                            self.emit(f"jmp {lbl_done}")
                            self.emit_raw(f"{lbl_plain}:")
                            self.emit("mov rcx, [_pyfasm_h_wnd]", "pass page handle")
                            self.emit("sub rsp, 32")
                            self.emit("call rax")
                            self.emit("add rsp, 32")
                            self.emit_raw(f"{lbl_done}:")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_run_window_loop")
                    self.emit("add rsp, 32")
                    return

                if attr_name in ("update", "clean") and isinstance(call.func, ast.Attribute) and not self._infer_expr_type(call.func.value).is_dict():
                    self.emit("xor ecx, ecx")
                    self.emit("sub rsp, 32", "shadow space")
                    self.emit("call _pyfasm_show_window")
                    self.emit("add rsp, 32")
                    return

                if (
                    (attr_name == "add" and isinstance(call.func, ast.Attribute) and not self._infer_expr_type(call.func.value).is_set() and call.args)
                    or call_name_lower in ("row", "column", "container", "card", "stack")
                ):
                    def _emit_flet_children(node: ast.AST) -> None:
                        if isinstance(node, ast.Call):
                            self._generate_expr(node)
                        elif isinstance(node, (ast.List, ast.Tuple)):
                            for elt in node.elts:
                                _emit_flet_children(elt)
                    for arg in call.args:
                        _emit_flet_children(arg)
                    ctrl_kw = self._extract_kwarg(call, "controls") or self._extract_kwarg(call, "content")
                    if ctrl_kw is not None:
                        _emit_flet_children(ctrl_kw)
                    self.emit("mov rax, [_pyfasm_h_wnd]", "flet container / page.add")
                    return

            # Canvas 2D Drawing Primitives
            if attr_name == "create_line" and len(call.args) >= 4:
                bgr = self._parse_color_to_bgr(self._extract_kwarg(call, "fill") or self._extract_kwarg(call, "outline"))
                if bgr is not None:
                    self.emit(f"mov ecx, {bgr}", "set canvas BGR color")
                    self.emit("call _pyfasm_canvas_set_color")
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
                self.emit("pop rax", "y2")
                self.emit("sub rsp, 48")
                self.emit("mov [rsp + 32], rax")
                self.emit("call _pyfasm_canvas_create_line")
                self.emit("add rsp, 48")
                return

            if attr_name == "create_rectangle" and len(call.args) >= 4:
                bgr = self._parse_color_to_bgr(self._extract_kwarg(call, "fill") or self._extract_kwarg(call, "outline"))
                if bgr is not None:
                    self.emit(f"mov ecx, {bgr}", "set canvas BGR color")
                    self.emit("call _pyfasm_canvas_set_color")
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
                self.emit("pop rax", "y2")
                self.emit("sub rsp, 48")
                self.emit("mov [rsp + 32], rax")
                self.emit("call _pyfasm_canvas_create_rectangle")
                self.emit("add rsp, 48")
                return

            if attr_name == "create_oval" and len(call.args) >= 4:
                bgr = self._parse_color_to_bgr(self._extract_kwarg(call, "fill") or self._extract_kwarg(call, "outline"))
                if bgr is not None:
                    self.emit(f"mov ecx, {bgr}", "set canvas BGR color")
                    self.emit("call _pyfasm_canvas_set_color")
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
                self.emit("pop rax", "y2")
                self.emit("sub rsp, 48")
                self.emit("mov [rsp + 32], rax")
                self.emit("call _pyfasm_canvas_create_oval")
                self.emit("add rsp, 48")
                return

            if attr_name == "create_text" and len(call.args) >= 2:
                bgr = self._parse_color_to_bgr(self._extract_kwarg(call, "fill"))
                if bgr is not None:
                    self.emit(f"mov ecx, {bgr}", "set canvas BGR text color")
                    self.emit("call _pyfasm_canvas_set_color")
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

            # Layout directives & geometry management (disambiguate Matplotlib ax.grid vs widget .grid)
            if attr_name == "grid" and isinstance(call.func, ast.Attribute) and not is_user_class_method:
                recv_name_l = ""
                if isinstance(call.func.value, ast.Attribute):
                    recv_name_l = call.func.value.attr.lower()
                elif isinstance(call.func.value, ast.Name):
                    recv_name_l = call.func.value.id.lower()
                mpl_kw_names = {"alpha", "linestyle", "ls", "axis", "which", "color", "linewidth", "lw", "b", "visible"}
                is_mpl_grid = (
                    any(k in recv_name_l for k in ("ax", "axes", "subplot", "plt"))
                    or (call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, (bool, str, type(None))))
                    or any(kw.arg in mpl_kw_names for kw in getattr(call, "keywords", []) if kw.arg)
                )
                if is_mpl_grid:
                    vis = 1
                    if call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value is False:
                        vis = 0
                    vis_kw = self._extract_kwarg(call, "visible") or self._extract_kwarg(call, "b")
                    if isinstance(vis_kw, ast.Constant) and vis_kw.value is False:
                        vis = 0
                    col_kw = self._extract_kwarg(call, "color") or self._extract_kwarg(call, "c")
                    self.emit("sub rsp, 48")
                    self._generate_expr(call.func.value)
                    self.emit("mov [rsp + 32], rax", "Axes pointer")
                    if col_kw is not None:
                        self._generate_expr(col_kw)
                        self.emit("mov r8, rax", "grid color")
                    else:
                        self.emit("xor r8d, r8d")
                    self.emit("mov rcx, [rsp + 32]", "Axes pointer")
                    self.emit(f"mov edx, {vis}", "grid visible")
                    self.emit("call _pyfasm_mpl_axes_grid")
                    self.emit("add rsp, 48")
                    return
                row_val = self._extract_kwarg_int(call, "row", 0)
                col_val = self._extract_kwarg_int(call, "column", 0) or self._extract_kwarg_int(call, "col", 0)
                rowspan_val = self._extract_kwarg_int(call, "rowspan", 1)
                colspan_val = self._extract_kwarg_int(call, "colspan", 1)
                padx_val = self._extract_padding(call, "padx", 4)
                pady_val = self._extract_padding(call, "pady", 4)
                sticky_str = self._get_kwarg_string_val(call, "sticky") or ""
                sticky_mask = 0
                s_lower = sticky_str.lower()
                if "n" in s_lower: sticky_mask |= 1
                if "s" in s_lower: sticky_mask |= 2
                if "e" in s_lower: sticky_mask |= 4
                if "w" in s_lower: sticky_mask |= 8
                if not sticky_mask and sticky_str:
                    sticky_mask = 15
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit(f"mov rdx, {row_val}", "row")
                self.emit(f"mov r8, {col_val}", "col")
                self.emit(f"mov r9, {sticky_mask}", "sticky mask")
                self.emit("sub rsp, 64")
                self.emit(f"mov eax, 0x{padx_val & 0xFFFFFFFF:X}")
                self.emit("mov [rsp + 32], rax")
                self.emit(f"mov eax, 0x{pady_val & 0xFFFFFFFF:X}")
                self.emit("mov [rsp + 40], rax")
                self.emit(f"mov qword [rsp + 48], {colspan_val}")
                self.emit(f"mov qword [rsp + 56], {rowspan_val}")
                self.emit("call _pyfasm_widget_set_grid")
                self.emit("add rsp, 64")
                return

            if attr_name == "grid_columnconfigure" and isinstance(call.func, ast.Attribute):
                col_nodes = []
                if call.args:
                    first = call.args[0]
                    if isinstance(first, (ast.Tuple, ast.List)):
                        col_nodes = [elt.value for elt in first.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, int)]
                    elif isinstance(first, ast.Constant) and isinstance(first.value, int):
                        col_nodes = [first.value]
                if not col_nodes:
                    col_nodes = [0]
                weight_val = self._extract_kwarg_int(call, "weight", 0)
                minsize_val = self._extract_kwarg_int(call, "minsize", 0)
                self._generate_expr(call.func.value)
                self.emit("push rax", "container HWND")
                for c in col_nodes:
                    self.emit("mov rcx, [rsp]", "container HWND")
                    self.emit(f"mov rdx, {c}", "col index")
                    self.emit(f"mov r8, {weight_val}", "weight")
                    self.emit(f"mov r9, {minsize_val}", "minsize")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_grid_columnconfigure")
                    self.emit("add rsp, 32")
                self.emit("pop rax")
                return

            if attr_name == "grid_rowconfigure" and isinstance(call.func, ast.Attribute):
                row_nodes = []
                if call.args:
                    first = call.args[0]
                    if isinstance(first, (ast.Tuple, ast.List)):
                        row_nodes = [elt.value for elt in first.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, int)]
                    elif isinstance(first, ast.Constant) and isinstance(first.value, int):
                        row_nodes = [first.value]
                if not row_nodes:
                    row_nodes = [0]
                weight_val = self._extract_kwarg_int(call, "weight", 0)
                minsize_val = self._extract_kwarg_int(call, "minsize", 0)
                self._generate_expr(call.func.value)
                self.emit("push rax", "container HWND")
                for r in row_nodes:
                    self.emit("mov rcx, [rsp]", "container HWND")
                    self.emit(f"mov rdx, {r}", "row index")
                    self.emit(f"mov r8, {weight_val}", "weight")
                    self.emit(f"mov r9, {minsize_val}", "minsize")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_grid_rowconfigure")
                    self.emit("add rsp, 32")
                self.emit("pop rax")
                return

            if attr_name == "pack" and isinstance(call.func, ast.Attribute):
                side_str = self._get_kwarg_string_val(call, "side") or "top"
                fill_str = self._get_kwarg_string_val(call, "fill") or "none"
                expand_val = self._extract_kwarg_int(call, "expand", 0)
                padx_val = self._extract_padding(call, "padx", 4)
                pady_val = self._extract_padding(call, "pady", 4)
                side_code = 0 if side_str == "top" else (1 if side_str == "bottom" else (2 if side_str == "left" else 3))
                fill_code = 0 if fill_str == "none" else (1 if fill_str == "x" else (2 if fill_str == "y" else 3))
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit(f"mov rdx, {side_code}", "side")
                self.emit(f"mov r8, {fill_code}", "fill")
                self.emit(f"mov r9, {expand_val}", "expand")
                self.emit("sub rsp, 48")
                self.emit(f"mov eax, 0x{padx_val & 0xFFFFFFFF:X}")
                self.emit("mov [rsp + 32], rax")
                self.emit(f"mov eax, 0x{pady_val & 0xFFFFFFFF:X}")
                self.emit("mov [rsp + 40], rax")
                self.emit("call _pyfasm_widget_set_pack")
                self.emit("add rsp, 48")
                return

            if attr_name == "place" and isinstance(call.func, ast.Attribute):
                x_val = self._extract_kwarg_int(call, "x", 0)
                y_val = self._extract_kwarg_int(call, "y", 0)
                w_val = self._extract_kwarg_int(call, "width", 0)
                h_val = self._extract_kwarg_int(call, "height", 0)
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "widget HWND")
                self.emit(f"mov rdx, {x_val}", "x")
                self.emit(f"mov r8, {y_val}", "y")
                self.emit(f"mov r9, {w_val}", "width")
                self.emit("sub rsp, 48")
                self.emit(f"mov qword [rsp + 32], {h_val}")
                self.emit("call _pyfasm_widget_set_place")
                self.emit("add rsp, 48")
                return

            if attr_name == "get_tk_widget" and isinstance(call.func, ast.Attribute):
                self._generate_expr(call.func.value)
                self.emit("mov rcx, rax", "canvas wrapper or HWND")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_mpl_canvas_widget")
                self.emit("add rsp, 32")
                return

            # 5. Authentic GUI geometry / timers / event binding / safe visual hints
            if not is_user_class_method:
                if attr_name in ("after",) and len(call.args) >= 2 and isinstance(call.func, ast.Attribute):
                    if self._emit_control_callback_to_rax(call.args[1]):
                        self.emit("push rax", "timer cb")
                        self._generate_expr(call.args[0])
                        self.emit("push rax", "ms")
                        self._generate_expr(call.func.value)
                        self.emit("mov rcx, rax", "hwnd")
                        self.emit("pop rdx", "ms")
                        self.emit("pop r8", "cb")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_after")
                        self.emit("add rsp, 32")
                    return

                if attr_name in ("bind", "bind_all") and len(call.args) >= 2 and isinstance(call.func, ast.Attribute):
                    if self._emit_control_callback_to_rax(call.args[1]):
                        self.emit("push rax", "bind cb")
                        self._generate_expr(call.args[0])
                        self.emit("push rax", "event sequence")
                        self._generate_expr(call.func.value)
                        self.emit("mov rcx, rax", "hwnd")
                        self.emit("pop rdx", "event str")
                        self.emit("pop r8", "cb")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_widget_bind")
                        self.emit("add rsp, 32")
                    return

                if attr_name in ("geometry", "minsize", "resize") and isinstance(call.func, ast.Attribute) and call.args:
                    if attr_name == "geometry" and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                        m_geo = re.search(r"(\d+)\s*[xX]\s*(\d+)", call.args[0].value)
                        if m_geo:
                            self.emit(f"mov rcx, {int(m_geo.group(1))}")
                            self.emit(f"mov rdx, {int(m_geo.group(2))}")
                            self.emit("sub rsp, 32")
                            self.emit("call _pyfasm_resize_window")
                            self.emit("add rsp, 32")
                    elif attr_name == "resize" and len(call.args) >= 2:
                        self._generate_expr(call.args[0])
                        self.emit("push rax")
                        self._generate_expr(call.args[1])
                        self.emit("mov rdx, rax")
                        self.emit("pop rcx")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_resize_window")
                        self.emit("add rsp, 32")
                    return

                if attr_name == "grid_propagate" and call.args and isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.args[0])
                    self.emit("push rax")
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax")
                    self.emit("pop rdx")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_grid_propagate")
                    self.emit("add rsp, 32")
                    return

                if attr_name == "winfo_width" and isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_winfo_width")
                    self.emit("add rsp, 32")
                    return

                if attr_name == "winfo_height" and isinstance(call.func, ast.Attribute):
                    self._generate_expr(call.func.value)
                    self.emit("mov rcx, rax")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_winfo_height")
                    self.emit("add rsp, 32")
                    return

                if attr_name in ("pack_propagate", "focus_set", "select_range", "update_idletasks",
                                 "iconbitmap", "wm_iconphoto", "maxsize", "resizable",
                                 "withdraw", "deiconify", "lift", "focus", "set_widget_scaling", "protocol"):
                    self.emit("xor eax, eax", f"GUI window hint '{attr_name}'")
                    return

            # 6. Hotkeys (keyboard.hook / keyboard.add_hotkey)
            if not is_user_defined_call and raw_ctor_lower in ("hook", "add_hotkey"):
                self.emit("mov rcx, 1", "hotkey id 1")
                self.emit("mov rdx, 19", "VK_PAUSE")
                self.emit("call _pyfasm_register_hotkey")
                self.emit("mov rcx, 2", "hotkey id 2")
                self.emit("mov rdx, 119", "VK_F8")
                self.emit("call _pyfasm_register_hotkey")
                self.emit("xor eax, eax")
                return

            # 7..15 Exact GUI Widget Constructors (NEVER hijack user functions/methods!)
            if not is_user_defined_call:
                # 7. Checkbuttons / Checkboxes / Switches / RadioButtons
                if raw_ctor_lower in ("checkbutton", "ctkcheckbox", "checkbox", "qcheckbox", "ctkswitch", "switch", "radiobutton", "ctkradiobutton", "qradiobutton"):
                    self._generate_checkbox_control(call, call_name_lower)
                    return

                # 8. Buttons
                if raw_ctor_lower in ("button", "ctkbutton", "qpushbutton", "pushbutton", "elevatedbutton", "filledbutton", "outlinedbutton", "textbutton", "iconbutton", "floatingactionbutton"):
                    self._generate_button_control(call, call_name_lower)
                    return

                # 9. Single-line Text Entries / Edits
                if raw_ctor_lower in ("entry", "ctkentry", "qlineedit", "lineedit", "textfield"):
                    self._generate_edit_control(call, call_name_lower)
                    return

                # 10. Static Labels
                if raw_ctor_lower in ("label", "ctklabel", "qlabel", "statictext") or (raw_ctor_lower == "text" and self.module.has_library("flet")):
                    self._generate_label_control(call, call_name_lower)
                    return

                # 11. Listbox / QListWidget
                if raw_ctor_lower in ("listbox", "qlistwidget", "listview"):
                    self._generate_listbox_control(call, call_name_lower)
                    return

                # 12. Multi-line Textbox
                if raw_ctor_lower in ("text", "ctktextbox", "textbox", "scrolledtext", "qtextedit", "qplaintextedit"):
                    self._generate_textbox_control(call, call_name_lower)
                    return

                # 13. tk.Canvas / CTkCanvas / FigureCanvasTkAgg / FigureCanvasQTAgg
                if raw_ctor_lower in ("canvas", "ctkcanvas", "tkcanvas", "figurecanvastkagg", "figurecanvasqtagg"):
                    is_mpl_canvas = raw_ctor_lower in ("figurecanvastkagg", "figurecanvasqtagg")
                    parent_node = self._extract_kwarg(call, "master")
                    if is_mpl_canvas:
                        fig_node = self._extract_kwarg(call, "figure") or (call.args[0] if call.args else None)
                        if parent_node is None and len(call.args) >= 2:
                            parent_node = call.args[1]
                    else:
                        fig_node = None
                        if parent_node is None and call.args:
                            first = call.args[0]
                            if not (isinstance(first, ast.Constant) and isinstance(first.value, (str, int, float, bool))):
                                parent_node = first
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov rcx, rax", "parent container HWND")
                    else:
                        self.emit("mov rcx, [_pyfasm_h_wnd]", "default parent HWND")
                    w_val = self._extract_kwarg_int(call, "width", 640)
                    h_val = self._extract_kwarg_int(call, "height", 500)
                    self.emit(f"mov rdx, {w_val}", "canvas width")
                    self.emit(f"mov r8, {h_val}", "canvas height")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_create_canvas")
                    self.emit("add rsp, 32")
                    if is_mpl_canvas and fig_node is not None:
                        self.emit("push rax", "save canvas HWND")
                        self._generate_expr(fig_node)
                        self.emit("mov rcx, rax", "PYFMFIG ptr")
                        self.emit("pop rdx", "canvas HWND")
                        self.emit("sub rsp, 32")
                        self.emit("call _pyfasm_mpl_canvas_attach")
                        self.emit("add rsp, 32")
                    return

                # 14. Frames, Cards, Scrollable Frames, TabViews, GroupBoxes (auto-sized 0x0 unless specified!)
                if raw_ctor_lower in ("frame", "ctkframe", "labelframe", "ctkscrollableframe", "scrollableframe", "ctktabview", "tabview", "notebook", "qframe", "qgroupbox", "qtabwidget", "container", "card", "row", "column", "stack"):
                    parent_node = self._extract_kwarg(call, "master")
                    if parent_node is None and call.args:
                        first = call.args[0]
                        if not (isinstance(first, ast.Constant) and isinstance(first.value, (str, int, float, bool))):
                            parent_node = first
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov rcx, rax", "parent container HWND")
                    else:
                        self.emit("mov rcx, [_pyfasm_h_wnd]", "default parent HWND")
                    w_val = self._extract_kwarg_int(call, "width", 0)
                    h_val = self._extract_kwarg_int(call, "height", 0)
                    radius_val = self._extract_kwarg_int(call, "corner_radius", 10 if "ctk" in raw_ctor_lower else 0)
                    self.emit(f"mov rdx, {w_val}", "frame width")
                    self.emit(f"mov r8, {h_val}", "frame height")
                    self.emit(f"mov r9, {radius_val}", "corner radius")
                    self.emit("sub rsp, 48")
                    self.emit("mov qword [rsp + 32], 0", "fg_color")
                    self.emit("call _pyfasm_create_frame")
                    self.emit("add rsp, 48")
                    self._emit_post_widget_styling(call, allow_font=False, allow_sv=False)
                    return

                # 15a. SegmentedButton (CTkSegmentedButton)
                if raw_ctor_lower in ("ctksegmentedbutton", "segmentedbutton"):
                    parent_node = self._extract_parent_container_node(call)
                    vals_node = self._extract_kwarg(call, "values")
                    cmd_node = self._extract_kwarg(call, "command")
                    sv_node = self._extract_kwarg(call, "variable") or self._extract_kwarg(call, "textvariable")
                    w_val = self._extract_kwarg_int(call, "width", 220)
                    h_val = self._extract_kwarg_int(call, "height", 32)
                    ctrl_id = self.gui_control_id
                    self.gui_control_id += 1
                    self.emit("sub rsp, 64")
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov [rsp], rax")
                    else:
                        self.emit("mov rax, [_pyfasm_h_wnd]")
                        self.emit("mov [rsp], rax")
                    if vals_node is not None:
                        self._generate_expr(vals_node)
                        self.emit("mov [rsp + 8], rax")
                    else:
                        self.emit("mov qword [rsp + 8], 0")
                    if self._emit_control_callback_to_rax(cmd_node):
                        self.emit("mov [rsp + 16], rax")
                    else:
                        self.emit("mov qword [rsp + 16], 0")
                    if sv_node is not None:
                        self._generate_expr(sv_node)
                        self.emit("mov [rsp + 24], rax")
                    else:
                        self.emit("mov qword [rsp + 24], 0")
                    self.emit("mov rcx, [rsp]")
                    self.emit("mov rdx, [rsp + 8]")
                    self.emit("mov r8, [rsp + 16]")
                    self.emit("mov r9, [rsp + 24]")
                    self.emit(f"mov qword [rsp + 32], {w_val}")
                    self.emit(f"mov qword [rsp + 40], {h_val}")
                    self.emit(f"mov qword [rsp + 48], {ctrl_id}")
                    self.emit("call _pyfasm_create_segmented")
                    self.emit("add rsp, 64")
                    self._emit_post_widget_styling(call, allow_sv=False)
                    return

                # 15b. ComboBox / OptionMenu
                if raw_ctor_lower in ("ctkcombobox", "combobox", "ctkoptionmenu", "optionmenu", "qcombobox"):
                    parent_node = self._extract_parent_container_node(call)
                    vals_node = self._extract_kwarg(call, "values")
                    cmd_node = self._extract_kwarg(call, "command")
                    sv_node = self._extract_kwarg(call, "variable") or self._extract_kwarg(call, "textvariable")
                    w_val = self._extract_kwarg_int(call, "width", 180)
                    h_val = self._extract_kwarg_int(call, "height", 32)
                    ctrl_id = self.gui_control_id
                    self.gui_control_id += 1
                    self.emit("sub rsp, 64")
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov [rsp], rax")
                    else:
                        self.emit("mov rax, [_pyfasm_h_wnd]")
                        self.emit("mov [rsp], rax")
                    if vals_node is not None:
                        self._generate_expr(vals_node)
                        self.emit("mov [rsp + 8], rax")
                    else:
                        self.emit("mov qword [rsp + 8], 0")
                    if self._emit_control_callback_to_rax(cmd_node):
                        self.emit("mov [rsp + 16], rax")
                    else:
                        self.emit("mov qword [rsp + 16], 0")
                    if sv_node is not None:
                        self._generate_expr(sv_node)
                        self.emit("mov [rsp + 24], rax")
                    else:
                        self.emit("mov qword [rsp + 24], 0")
                    self.emit("mov rcx, [rsp]")
                    self.emit("mov rdx, [rsp + 8]")
                    self.emit("mov r8, [rsp + 16]")
                    self.emit("mov r9, [rsp + 24]")
                    self.emit(f"mov qword [rsp + 32], {w_val}")
                    self.emit(f"mov qword [rsp + 40], {h_val}")
                    self.emit(f"mov qword [rsp + 48], {ctrl_id}")
                    self.emit("call _pyfasm_create_combobox")
                    self.emit("add rsp, 64")
                    self._emit_post_widget_styling(call, allow_sv=False)
                    return

                # 15b2. QSpinBox / QDoubleSpinBox (editable numeric input)
                if raw_ctor_lower in ("qspinbox", "qdoublespinbox"):
                    parent_node = self._extract_parent_container_node(call)
                    w_val = self._extract_kwarg_int(call, "width", 100)
                    h_val = self._extract_kwarg_int(call, "height", 28)
                    ctrl_id = self.gui_control_id
                    self.gui_control_id += 1
                    self.emit("sub rsp, 64")
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov [rsp + 48], rax", "parent_hwnd")
                    else:
                        self.emit("mov rax, [_pyfasm_h_wnd]")
                        self.emit("mov [rsp + 48], rax", "parent_hwnd")
                    self._emit_string_pointer("rcx", "0")
                    self.emit("xor edx, edx", "x")
                    self.emit("xor r8d, r8d", "y")
                    self.emit(f"mov r9, {w_val}", "w")
                    self.emit(f"mov qword [rsp + 32], {h_val}", "h")
                    self.emit(f"mov qword [rsp + 40], {ctrl_id}", "id")
                    self.emit("call _pyfasm_create_edit")
                    self.emit("add rsp, 64")
                    self._emit_post_widget_styling(call, allow_sv=False)
                    return

                # 15c. Slider / Scale / QSlider
                if raw_ctor_lower in ("ctkslider", "slider", "scale", "qslider"):
                    parent_node = self._extract_parent_container_node(call)
                    from_node = self._extract_kwarg(call, "from_")
                    to_node = self._extract_kwarg(call, "to")
                    cmd_node = self._extract_kwarg(call, "command")
                    w_val = self._extract_kwarg_int(call, "width", 180)
                    h_val = self._extract_kwarg_int(call, "height", 24)
                    ctrl_id = self.gui_control_id
                    self.gui_control_id += 1
                    self.emit("sub rsp, 64")
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov [rsp], rax")
                    else:
                        self.emit("mov rax, [_pyfasm_h_wnd]")
                        self.emit("mov [rsp], rax")
                    if from_node is not None:
                        self._generate_expr(from_node)
                        if not self._infer_expr_type(from_node).is_float():
                            self.emit("cvtsi2sd xmm0, rax")
                            self.emit("movq rax, xmm0")
                        self.emit("mov [rsp + 8], rax")
                    else:
                        self._emit_float_bits("rax", 0.0)
                        self.emit("mov [rsp + 8], rax")
                    if to_node is not None:
                        self._generate_expr(to_node)
                        if not self._infer_expr_type(to_node).is_float():
                            self.emit("cvtsi2sd xmm0, rax")
                            self.emit("movq rax, xmm0")
                        self.emit("mov [rsp + 16], rax")
                    else:
                        self._emit_float_bits("rax", 100.0)
                        self.emit("mov [rsp + 16], rax")
                    if self._emit_control_callback_to_rax(cmd_node):
                        self.emit("mov [rsp + 24], rax")
                    else:
                        self.emit("mov qword [rsp + 24], 0")
                    self.emit("mov rcx, [rsp]")
                    self.emit("mov rdx, [rsp + 8]")
                    self.emit("mov r8, [rsp + 16]")
                    self.emit("mov r9, [rsp + 24]")
                    self.emit(f"mov qword [rsp + 32], {w_val}")
                    self.emit(f"mov qword [rsp + 40], {h_val}")
                    self.emit(f"mov qword [rsp + 48], {ctrl_id}")
                    self.emit("call _pyfasm_create_slider")
                    self.emit("add rsp, 64")
                    return

                # 15d. ProgressBar
                if raw_ctor_lower in ("ctkprogressbar", "progressbar", "progressring", "qprogressbar"):
                    parent_node = self._extract_parent_container_node(call)
                    w_val = self._extract_kwarg_int(call, "width", 200)
                    h_val = self._extract_kwarg_int(call, "height", 16)
                    if parent_node is not None:
                        self._generate_expr(parent_node)
                        self.emit("mov rcx, rax")
                    else:
                        self.emit("mov rcx, [_pyfasm_h_wnd]")
                    self.emit(f"mov rdx, {w_val}")
                    self.emit(f"mov r8, {h_val}")
                    self.emit("xor r9d, r9d")
                    self.emit("sub rsp, 32")
                    self.emit("call _pyfasm_create_progressbar")
                    self.emit("add rsp, 32")
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
            is_gen = self._is_generator_expr(arg)

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
            is_gen = self._is_generator_expr(arg)

            if is_gen:
                self._generate_expr(arg)
                self.emit("mov rcx, rax", "gen_ptr")
                self.emit("sub rsp, 32", "shadow space")
                self.emit("call _pyfasm_gen_to_list")
                self.emit("add rsp, 32")
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
                    lbl_null_len = self.new_label("null_len")
                    lbl_done_len = self.new_label("done_len")
                    self.emit("test rax, rax", "check null pointer for len")
                    self.emit(f"jz {lbl_null_len}")
                    self.emit("mov rax, [rax]", "load length from header")
                    self.emit(f"jmp {lbl_done_len}")
                    self.emit_raw(f"{lbl_null_len}:")
                    self.emit("xor eax, eax", "len of null is 0")
                    self.emit_raw(f"{lbl_done_len}:")
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
            is_gen = self._is_generator_expr(arg)
            self._generate_expr(arg)
            if is_gen:
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_gen_to_list")
                self.emit("add rsp, 32")
            self.emit("mov rcx, rax", "argument to set")
            if caller_type.is_str():
                self.emit("call _pyfasm_set_from_str")
            elif caller_type.is_list() or is_gen:
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
            is_gen = self._is_generator_expr(call.args[0])
            self._generate_expr(call.args[0])
            if is_gen:
                self.emit("mov rcx, rax")
                self.emit("sub rsp, 32")
                self.emit("call _pyfasm_gen_to_list")
                self.emit("add rsp, 32")
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

        # itertools.batched(seq, n) - Python 3.12+ / 3.14 / 3.15
        if (func_name in ("batched", "itertools_batched") or (prefix == "itertools" and attr_name == "batched")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "batch size n")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "seq list")
            self.emit("pop rdx", "batch size n")
            self.emit("sub rsp, 32", "shadow space for _pyfasm_itertools_batched")
            self.emit("call _pyfasm_itertools_batched")
            self.emit("add rsp, 32")
            return

        # math.sumprod(p, q) - Python 3.12+ / 3.14 / 3.15
        if (func_name in ("sumprod", "math_sumprod") or (prefix == "math" and attr_name == "sumprod")) and len(call.args) >= 2:
            self._generate_expr(call.args[1])
            self.emit("push rax", "vec q")
            self._generate_expr(call.args[0])
            self.emit("mov rcx, rax", "vec p")
            self.emit("pop rdx", "vec q")
            self.emit("call _pyfasm_math_sumprod")
            return

        # os.cpu_count() / os.process_cpu_count() - Python 3.13+ / 3.14 / 3.15
        if func_name in ("cpu_count", "process_cpu_count") or (prefix == "os" and attr_name in ("cpu_count", "process_cpu_count")):
            self.emit("call _pyfasm_os_cpu_count")
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
                    if is_dunder:
                        self.emit("xor edx, edx")
                        self.emit("xor r8d, r8d")
                        self.emit("xor r9d, r9d")
                    else:
                        self.emit("mov rdx, -9223372036854775807", "default sentinel for optional closure arg")
                        self.emit("mov r8, -9223372036854775807", "default sentinel for optional closure arg")
                        self.emit("mov r9, -9223372036854775807", "default sentinel for optional closure arg")
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
                    if is_dunder:
                        self.emit("xor r8d, r8d")
                        self.emit("xor r9d, r9d")
                    else:
                        self.emit("mov r8, -9223372036854775807")
                        self.emit("mov r9, -9223372036854775807")
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
                    if is_dunder:
                        self.emit("xor r9d, r9d")
                    else:
                        self.emit("mov r9, -9223372036854775807")
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
