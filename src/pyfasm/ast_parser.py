"""
AST Parser and Semantic Analyzer for PyFASM.
Traverses Python AST, extracts functions, variables, and type information
across single files or complete multi-module project libraries.
"""
from __future__ import annotations
import ast
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
_AST_MATCH = getattr(ast, 'Match', ())
_AST_MATCH_AS = getattr(ast, 'MatchAs', ())
_AST_MATCH_VALUE = getattr(ast, 'MatchValue', ())
_AST_MATCH_OR = getattr(ast, 'MatchOr', ())
from pyfasm.types import (
    PyFasmType, resolve_type, TYPE_INT, TYPE_VOID, TYPE_STR, TYPE_PTR,
    TYPE_FLOAT, TYPE_COMPLEX, TYPE_BOOL, TYPE_LIST, TYPE_DICT, TYPE_SET, TYPE_TUPLE, TYPE_GENERATOR,
    InstanceType, ListType, DictType, SetType, TupleType
)
from pyfasm.diagnostics import (
    CompilerDiagnostic,
    KNOWN_UNSUPPORTED_EXTERNAL_MODULES,
    NATIVELY_SUPPORTED_OR_ADAPTED_MODULES,
    SUPPORTED_DUNDERS_SUMMARY,
    UNSUPPORTED_DUNDERS,
    from_syntax_error,
)


@dataclass
class VariableSymbol:
    name: str
    var_type: PyFasmType
    stack_offset: int  # Offset from RBP: [rbp - stack_offset]
    is_arg: bool = False
    arg_index: int = 0
    is_generator: bool = False
    is_dynamic: bool = False
    fn_alias: Optional[str] = None
    widget_kind: Optional[str] = None
    pyfasm_group: bool = False


@dataclass
class FunctionSymbol:
    name: str
    args: List[VariableSymbol]
    return_type: PyFasmType
    local_vars: Dict[str, VariableSymbol] = field(default_factory=dict)
    stack_size: int = 0
    ast_node: Optional[ast.FunctionDef] = None
    class_name: Optional[str] = None
    global_names: Set[str] = field(default_factory=set)
    is_generator: bool = False
    defaults: List[ast.expr] = field(default_factory=list)
    source_file: Optional[str] = None
    is_staticmethod: bool = False
    is_classmethod: bool = False
    is_closure: bool = False
    is_dynamic_return: bool = False


@dataclass
class PropertySymbol:
    name: str
    getter_name: Optional[str] = None
    setter_name: Optional[str] = None


@dataclass
class ClassSymbol:
    name: str
    methods: Dict[str, FunctionSymbol] = field(default_factory=dict)
    fields: List[str] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)
    properties: Dict[str, PropertySymbol] = field(default_factory=dict)
    class_attrs: Dict[str, Any] = field(default_factory=dict)
    field_types: Dict[str, PyFasmType] = field(default_factory=dict)
    field_classes: Dict[str, str] = field(default_factory=dict)
    field_widget_kinds: Dict[str, str] = field(default_factory=dict)
    static_methods: Set[str] = field(default_factory=set)
    class_methods: Set[str] = field(default_factory=set)
    ast_node: Optional[ast.ClassDef] = None


@dataclass
class StringLiteral:
    label: str
    value: str


@dataclass
class FloatLiteral:
    label: str
    value: float


@dataclass
class HttpRouteSpec:
    method: str
    path: str
    handler_name: str
    return_kind: str = "auto"
    param_names: List[str] = field(default_factory=list)
    param_int_mask: int = 0
    param_dict_mask: int = 0
    param_defaults: List[Optional[str]] = field(default_factory=list)


@dataclass
class ParsedModule:
    functions: Dict[str, FunctionSymbol] = field(default_factory=dict)
    classes: Dict[str, ClassSymbol] = field(default_factory=dict)
    string_literals: List[StringLiteral] = field(default_factory=list)
    float_literals: List[FloatLiteral] = field(default_factory=list)
    global_vars: Dict[str, int] = field(default_factory=dict)
    global_var_types: Dict[str, PyFasmType] = field(default_factory=dict)
    global_widget_kinds: Dict[str, str] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    detected_libraries: Set[str] = field(default_factory=set)
    main_func: Optional[FunctionSymbol] = None
    calls_main_in_top_level: bool = False
    ui_spec: Optional[Any] = None
    module_inits: List[str] = field(default_factory=list)
    diagnostics: List[CompilerDiagnostic] = field(default_factory=list)
    source_files: Dict[str, str] = field(default_factory=dict)
    http_routes: List[HttpRouteSpec] = field(default_factory=list)
    type_aliases: Dict[str, PyFasmType] = field(default_factory=dict)
    cell_val_types: Dict[str, PyFasmType] = field(default_factory=dict)
    python_version: Tuple[int, int] = field(default_factory=lambda: (sys.version_info.major, sys.version_info.minor))

    def has_library(self, *names: str) -> bool:
        """Check if any of the specified library names is installed in project or imported."""
        targets = {n.lower().replace("-", "_") for n in names}
        for lib in self.detected_libraries:
            l_low = lib.lower().replace("-", "_")
            if any(l_low == t or l_low.startswith(t + "_") for t in targets):
                return True
        for imp in self.imports:
            root = imp.split(".")[0].lower().replace("-", "_")
            if any(root == t or root.startswith(t + "_") for t in targets):
                return True
        return False

    @property
    def is_tray_app(self) -> bool:
        return self.has_library("pystray", "tray") or any("tray" in s.lower() for s in self.classes)

    @property
    def is_keyboard_hook_app(self) -> bool:
        return self.has_library("keyboard", "pynput", "hook") or self.is_tray_app

    @property
    def is_modern_gui(self) -> bool:
        if getattr(self, "_override_is_modern_gui", None) is not None:
            return bool(self._override_is_modern_gui)
        return self.has_library(
            "customtkinter", "tkinter", "ttkbootstrap", "ctk", "flet", "textual",
            "qt", "pyqt5", "pyqt6", "pyside6", "pyside2",
        ) or any("app" in s.lower() or "gui" in s.lower() or "window" in s.lower() for s in self.classes)

    @is_modern_gui.setter
    def is_modern_gui(self, val: bool) -> None:
        self._override_is_modern_gui = val

    @property
    def is_pygame_app(self) -> bool:
        return self.has_library("pygame")

    @property
    def is_http_server_app(self) -> bool:
        return self.has_library("fastapi", "uvicorn", "starlette") or bool(self.http_routes)

    @property
    def is_http_app(self) -> bool:
        return self.has_library("requests", "urllib", "urllib3", "httpx", "aiohttp", "curl_cffi", "json")

    @property
    def is_office_app(self) -> bool:
        return self.has_library("docx", "openpyxl", "xlsxwriter", "fitz", "pymupdf", "pdf", "pypdf")

    @property
    def is_media_app(self) -> bool:
        return self.has_library("cv2", "opencv", "ffmpeg", "pyaudio", "sounddevice", "pil", "pillow")


def is_negative_number_literal(node: Optional[ast.AST]) -> bool:
    """True for a literal such as -1 or -0.5 (a negative exponent turns int ** int into a float)."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = node.operand
        return (
            isinstance(inner, ast.Constant)
            and isinstance(inner.value, (int, float))
            and not isinstance(inner.value, bool)
            and inner.value > 0
        )
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
        and node.value < 0
    )


def walk_local_scope(node: ast.AST):
    """Walk an AST node without descending into nested function or class scopes."""
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            yield from walk_local_scope(child)


GUI_LIBRARY_ROOTS = ("tkinter", "customtkinter", "pyqt5", "pyqt6", "pyside2", "pyside6")

_GUI_WIDGET_KINDS: Dict[str, str] = {
    "StringVar": "strvar",
    "IntVar": "intvar",
    "BooleanVar": "intvar",
    "DoubleVar": "floatvar",
    "Entry": "entry",
    "CTkEntry": "entry",
    "QLineEdit": "entry",
    "Text": "text",
    "ScrolledText": "text",
    "CTkTextbox": "text",
    "QTextEdit": "text",
    "QPlainTextEdit": "text",
    "Listbox": "listbox",
    "QListWidget": "listbox",
    "Combobox": "combo",
    "CTkComboBox": "combo",
    "CTkOptionMenu": "combo",
    "QComboBox": "combo",
    "Scale": "slider",
    "CTkSlider": "slider",
    "QSlider": "slider",
    "Label": "label",
    "CTkLabel": "label",
    "QLabel": "label",
    "Button": "button",
    "CTkButton": "button",
    "QPushButton": "button",
    "Tk": "window",
    "CTk": "window",
    "Toplevel": "window",
    "CTkToplevel": "window",
    "Frame": "frame",
    "CTkFrame": "frame",
    "LabelFrame": "frame",
}

GUI_STRING_GETTER_KINDS = ("strvar", "entry", "text", "combo")
GUI_FLOAT_GETTER_KINDS = ("floatvar", "slider")
GUI_ITEM_LIST_KINDS = ("listbox", "combo")


def gui_method_result_type(kind: Optional[str], attr: str, n_args: int) -> Optional[PyFasmType]:
    """Result type of ``<widget>.<attr>(...)`` for a known widget kind, or None if not a value getter."""
    if kind is None:
        return None
    if attr == "get":
        if kind in GUI_STRING_GETTER_KINDS:
            return TYPE_STR
        if kind in GUI_FLOAT_GETTER_KINDS and n_args == 0:
            return TYPE_FLOAT
        if kind == "intvar" and n_args == 0:
            return TYPE_INT
        return None
    if attr in ("cget", "text", "currentText", "toPlainText", "title"):
        return TYPE_STR
    if attr in ("size", "count") and n_args == 0 and kind in GUI_ITEM_LIST_KINDS:
        return TYPE_INT
    return None


def gui_widget_kind(expr: Optional[ast.AST]) -> Optional[str]:
    """Classify a GUI constructor call (``tk.Entry(...)``, ``QComboBox()``) by widget kind."""
    if not isinstance(expr, ast.Call):
        return None
    func = expr.func
    if isinstance(func, ast.Attribute):
        return _GUI_WIDGET_KINDS.get(func.attr)
    if isinstance(func, ast.Name):
        return _GUI_WIDGET_KINDS.get(func.id)
    return None



class ConstantFolder(ast.NodeTransformer):
    """Evaluates compile-time constant expressions (Constant Folding)."""

    _MAX_FOLD_INT = 1 << 62

    def __init__(self, py_version: Optional[Tuple[int, int]] = None, py_micro: Optional[int] = None):
        super().__init__()
        self.py_version = py_version or (sys.version_info.major, sys.version_info.minor)
        self.py_micro = py_micro if py_micro is not None else sys.version_info.micro

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if len(node.ops) == 1 and len(node.comparators) == 1:
            left = node.left
            op = node.ops[0]
            right = node.comparators[0]
            is_sys_ver = False
            if isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name) and left.value.id == "sys" and left.attr == "version_info":
                is_sys_ver = True
            elif isinstance(left, ast.Subscript) and isinstance(left.value, ast.Attribute) and isinstance(left.value.value, ast.Name) and left.value.value.id == "sys" and left.value.attr == "version_info":
                is_sys_ver = True

            if is_sys_ver and isinstance(right, ast.Tuple):
                cmp_vals = []
                for elt in right.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, int):
                        cmp_vals.append(elt.value)
                    else:
                        break
                if len(cmp_vals) >= 1:
                    target_tup = tuple(cmp_vals)
                    ver_tup = (self.py_version[0], self.py_version[1], self.py_micro)[:len(target_tup)]
                    ans = False
                    if isinstance(op, ast.GtE):
                        ans = ver_tup >= target_tup
                    elif isinstance(op, ast.Gt):
                        ans = ver_tup > target_tup
                    elif isinstance(op, ast.LtE):
                        ans = ver_tup <= target_tup
                    elif isinstance(op, ast.Lt):
                        ans = ver_tup < target_tup
                    elif isinstance(op, ast.Eq):
                        ans = ver_tup == target_tup
                    elif isinstance(op, ast.NotEq):
                        ans = ver_tup != target_tup
                    return ast.copy_location(ast.Constant(value=ans), node)
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            lv, rv = node.left.value, node.right.value
            try:
                res = None
                if isinstance(node.op, ast.Add):
                    res = lv + rv
                elif isinstance(node.op, ast.Sub):
                    res = lv - rv
                elif isinstance(node.op, ast.Mult):
                    if isinstance(lv, str) and isinstance(rv, int):
                        if 0 <= rv <= 4096 and len(lv) * rv <= 4096:
                            res = lv * rv
                    elif isinstance(rv, str) and isinstance(lv, int):
                        if 0 <= lv <= 4096 and len(rv) * lv <= 4096:
                            res = lv * rv
                    else:
                        res = lv * rv
                elif isinstance(node.op, ast.FloorDiv) and rv != 0:
                    res = lv // rv
                elif isinstance(node.op, ast.Mod) and rv != 0:
                    res = lv % rv
                elif isinstance(node.op, ast.Pow):
                    if isinstance(lv, int) and isinstance(rv, int):
                        if 0 <= rv <= 62:
                            res = lv ** rv
                    elif isinstance(lv, (int, float)) and isinstance(rv, (int, float)):
                        cand = lv ** rv
                        if not isinstance(cand, complex):
                            res = cand
                elif isinstance(node.op, ast.BitAnd):
                    res = lv & rv
                elif isinstance(node.op, ast.BitOr):
                    res = lv | rv
                elif isinstance(node.op, ast.BitXor):
                    res = lv ^ rv
                elif isinstance(node.op, ast.LShift):
                    if isinstance(lv, int) and isinstance(rv, int) and 0 <= rv <= 62:
                        res = lv << rv
                elif isinstance(node.op, ast.RShift):
                    if isinstance(lv, int) and isinstance(rv, int) and 0 <= rv <= 63:
                        res = lv >> rv

                if res is not None and not isinstance(res, complex):
                    if isinstance(res, int) and not isinstance(res, bool):
                        if not (-self._MAX_FOLD_INT <= res <= self._MAX_FOLD_INT):
                            return node
                    if isinstance(res, str) and len(res) > 4096:
                        return node
                    return ast.Constant(value=res)
            except Exception:
                pass
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.operand, ast.Constant):
            v = node.operand.value
            try:
                res = None
                if isinstance(node.op, ast.USub):
                    res = -v
                elif isinstance(node.op, ast.UAdd):
                    res = +v
                elif isinstance(node.op, ast.Invert):
                    res = ~v
                elif isinstance(node.op, ast.Not):
                    res = not v
                if res is not None:
                    if isinstance(res, int) and not isinstance(res, bool):
                        if not (-self._MAX_FOLD_INT <= res <= self._MAX_FOLD_INT):
                            return node
                    return ast.Constant(value=res)
            except Exception:
                pass
        return node


class ClassLambdaDesugarer(ast.NodeTransformer):
    """
    Transforms class-level and module-level lambda assignments:
        has_subpattern = lambda st, ...: ...
    into explicit function definitions:
        def has_subpattern(st, ...):
            return ...
    """
    def _desugar_stmts(self, stmts):
        new_body = []
        for item in stmts:
            if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name) and isinstance(item.value, ast.Lambda):
                fn_name = item.targets[0].id
                fn_node = ast.FunctionDef(
                    name=fn_name,
                    args=item.value.args,
                    body=[ast.Return(value=item.value.body)],
                    decorator_list=[],
                    returns=None,
                    lineno=getattr(item, "lineno", 1),
                    col_offset=getattr(item, "col_offset", 0)
                )
                new_body.append(self.visit(fn_node))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and isinstance(item.value, ast.Lambda):
                fn_name = item.target.id
                fn_node = ast.FunctionDef(
                    name=fn_name,
                    args=item.value.args,
                    body=[ast.Return(value=item.value.body)],
                    decorator_list=[],
                    returns=item.annotation,
                    lineno=getattr(item, "lineno", 1),
                    col_offset=getattr(item, "col_offset", 0)
                )
                new_body.append(self.visit(fn_node))
            else:
                new_body.append(self.visit(item))
        return new_body

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.body = self._desugar_stmts(node.body)
        return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        node.body = self._desugar_stmts(node.body)
        return node




class ImportCallTransformer(ast.NodeTransformer):
    """
    Transforms __import__('mod').attr into mod.attr
    and __import__('mod') into mod.
    """
    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "__import__":
            if node.value.args and isinstance(node.value.args[0], ast.Constant) and isinstance(node.value.args[0].value, str):
                mod_name = node.value.args[0].value
                return ast.Attribute(value=ast.Name(id=mod_name, ctx=ast.Load()), attr=node.attr, ctx=node.ctx)
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return ast.Name(id=node.args[0].value, ctx=ast.Load())
        return node


class MapMethodTransformer(ast.NodeTransformer):
    """
    Transforms map(obj.method, seq) into [obj.method(x) for x in seq]
    so that bound methods can be evaluated naturally.
    """
    def __init__(self):
        super().__init__()
        self._counter = 0

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "map" and len(node.args) == 2:
            func_arg, seq_arg = node.args[0], node.args[1]
            if isinstance(func_arg, ast.Attribute):
                self._counter += 1
                var_name = f"_pyfasm_map_item_{self._counter}"
                target = ast.Name(id=var_name, ctx=ast.Store())
                elt = ast.Call(
                    func=ast.Attribute(value=func_arg.value, attr=func_arg.attr, ctx=ast.Load()),
                    args=[ast.Name(id=var_name, ctx=ast.Load())],
                    keywords=[]
                )
                comp = ast.comprehension(target=target, iter=seq_arg, ifs=[], is_async=0)
                return ast.ListComp(elt=elt, generators=[comp])
        return node


class ChainedCompareTransformer(ast.NodeTransformer):
    """
    Transforms chained comparisons like:
        idx == i == x - 1
    into:
        (idx == i) and (i == x - 1)
    """
    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if len(node.ops) <= 1:
            return node

        comparisons = []
        curr_left = node.left
        for op, comp in zip(node.ops, node.comparators):
            comparisons.append(ast.Compare(
                left=curr_left,
                ops=[op],
                comparators=[comp],
                lineno=getattr(node, "lineno", 1),
                col_offset=getattr(node, "col_offset", 0)
            ))
            curr_left = comp

        return ast.BoolOp(
            op=ast.And(),
            values=comparisons,
            lineno=getattr(node, "lineno", 1),
            col_offset=getattr(node, "col_offset", 0)
        )


class _RewriteNestedRefs(ast.NodeTransformer):
    """Rewrites direct calls/references inside lifted nested functions and recursive closures."""

    def __init__(
        self,
        nested_rename: Dict[str, str],
        closure_self_name: Optional[str] = None,
        closure_lifted_name: Optional[str] = None,
        shadowed: Optional[Set[str]] = None,
    ):
        self.nested_rename = nested_rename
        self.closure_self_name = closure_self_name
        self.closure_lifted_name = closure_lifted_name
        self.shadowed = set(shadowed or ())

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return node

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        own_args: Set[str] = set()
        for a in getattr(node.args, "posonlyargs", []):
            own_args.add(a.arg)
        for a in node.args.args:
            own_args.add(a.arg)
        for a in getattr(node.args, "kwonlyargs", []):
            own_args.add(a.arg)
        if node.args.vararg:
            own_args.add(node.args.vararg.arg)
        if node.args.kwarg:
            own_args.add(node.args.kwarg.arg)
        sub = _RewriteNestedRefs(
            self.nested_rename,
            closure_self_name=self.closure_self_name,
            closure_lifted_name=self.closure_lifted_name,
            shadowed=self.shadowed | own_args,
        )
        node.body = sub.visit(node.body)
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        node.args = [self.visit(a) for a in node.args]
        node.keywords = [ast.keyword(arg=k.arg, value=self.visit(k.value)) for k in node.keywords]
        if (
            self.closure_self_name
            and self.closure_lifted_name
            and isinstance(node.func, ast.Name)
            and node.func.id == self.closure_self_name
            and node.func.id not in self.shadowed
        ):
            new_call = ast.Call(
                func=ast.Name(id=self.closure_lifted_name, ctx=ast.Load()),
                args=[ast.Name(id="_pyfasm_env", ctx=ast.Load())] + list(node.args),
                keywords=node.keywords,
            )
            return ast.copy_location(new_call, node)
        node.func = self.visit(node.func)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id not in self.shadowed:
            if node.id in self.nested_rename:
                return ast.copy_location(ast.Name(id=self.nested_rename[node.id], ctx=ast.Load()), node)
            if self.closure_self_name and node.id == self.closure_self_name:
                return ast.copy_location(ast.Name(id="_pyfasm_env", ctx=ast.Load()), node)
        return node


class ClosureLifter(ast.NodeTransformer):
    """Lifts anonymous lambdas and nested functions to top-level definitions with lexical closure capture."""

    def __init__(self):
        super().__init__()
        self.lambdas: List[ast.FunctionDef] = []
        self.counter: int = 0
        self.scope_stack: List[Set[str]] = []
        self._nested_rename_stack: List[Dict[str, str]] = []

    @staticmethod
    def _collect_target_names(target: ast.AST, out: Set[str]) -> None:
        if isinstance(target, ast.Name):
            out.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                ClosureLifter._collect_target_names(elt, out)
        elif isinstance(target, ast.Starred):
            ClosureLifter._collect_target_names(target.value, out)

    @classmethod
    def _collect_fn_bound_names(cls, fn_node: ast.FunctionDef) -> Set[str]:
        bound: Set[str] = set()
        globals_declared: Set[str] = set()
        for a in getattr(fn_node.args, "posonlyargs", []):
            bound.add(a.arg)
        for a in fn_node.args.args:
            bound.add(a.arg)
        for a in getattr(fn_node.args, "kwonlyargs", []):
            bound.add(a.arg)
        if fn_node.args.vararg:
            bound.add(fn_node.args.vararg.arg)
        if fn_node.args.kwarg:
            bound.add(fn_node.args.kwarg.arg)

        for sub in walk_local_scope(fn_node):
            if isinstance(sub, ast.Global):
                globals_declared.update(sub.names)
            elif isinstance(sub, ast.Assign):
                for t in sub.targets:
                    cls._collect_target_names(t, bound)
            elif isinstance(sub, ast.AnnAssign):
                cls._collect_target_names(sub.target, bound)
            elif isinstance(sub, ast.AugAssign):
                cls._collect_target_names(sub.target, bound)
            elif isinstance(sub, ast.For):
                cls._collect_target_names(sub.target, bound)
            elif isinstance(sub, ast.With):
                for item in sub.items:
                    if item.optional_vars:
                        cls._collect_target_names(item.optional_vars, bound)
            elif isinstance(sub, ast.ExceptHandler) and sub.name:
                bound.add(sub.name)
            elif isinstance(sub, ast.NamedExpr):
                cls._collect_target_names(sub.target, bound)
            elif isinstance(sub, ast.FunctionDef) and sub is not fn_node:
                bound.add(sub.name)

        return bound - globals_declared

    @classmethod
    def _collect_comp_and_walrus_names(cls, node: ast.AST) -> Set[str]:
        bound: Set[str] = set()
        for sub in ast.walk(node):
            if isinstance(sub, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for gen in sub.generators:
                    cls._collect_target_names(gen.target, bound)
            elif isinstance(sub, ast.NamedExpr):
                cls._collect_target_names(sub.target, bound)
        return bound

    @staticmethod
    def _collect_loaded_names(nodes: List[ast.AST]) -> Set[str]:
        loaded: Set[str] = set()
        for root in nodes:
            for sub in ast.walk(root):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    loaded.add(sub.id)
        return loaded

    @staticmethod
    def _make_closure_args(orig_args: ast.arguments) -> ast.arguments:
        env_arg = ast.arg(arg="_pyfasm_env", annotation=None, type_comment=None)
        posonly = list(getattr(orig_args, "posonlyargs", []))
        args = list(orig_args.args)
        if posonly:
            posonly = [env_arg] + posonly
        else:
            args = [env_arg] + args
        return ast.arguments(
            posonlyargs=posonly,
            args=args,
            vararg=orig_args.vararg,
            kwonlyargs=list(getattr(orig_args, "kwonlyargs", [])),
            kw_defaults=list(getattr(orig_args, "kw_defaults", [])),
            kwarg=orig_args.kwarg,
            defaults=list(orig_args.defaults),
        )

    def _enclosing_vars(self) -> Set[str]:
        out: Set[str] = set()
        for s in self.scope_stack:
            out.update(s)
        return out

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        self.generic_visit(node)
        return node

    @staticmethod
    def _own_arg_names(args: ast.arguments) -> Set[str]:
        own: Set[str] = set()
        for a in getattr(args, "posonlyargs", []):
            own.add(a.arg)
        for a in args.args:
            own.add(a.arg)
        for a in getattr(args, "kwonlyargs", []):
            own.add(a.arg)
        if args.vararg:
            own.add(args.vararg.arg)
        if args.kwarg:
            own.add(args.kwarg.arg)
        return own

    def _active_nested_renames(self) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        for d in self._nested_rename_stack:
            merged.update(d)
        return merged

    def _preassign_pure_siblings(self, fn_node: ast.FunctionDef, fn_bound: Set[str]) -> Dict[str, str]:
        direct_defs: List[ast.FunctionDef] = []
        for s in fn_node.body:
            if isinstance(s, ast.FunctionDef) and not s.decorator_list:
                is_gen = any(isinstance(sub, (ast.Yield, ast.YieldFrom)) for sub in walk_local_scope(s))
                if not is_gen:
                    direct_defs.append(s)
        if not direct_defs:
            return {}
        sibling_names = {s.name for s in direct_defs}
        enclosing_non_sib = (self._enclosing_vars() | fn_bound) - sibling_names
        pure: Set[str] = set(sibling_names)
        changed = True
        while changed:
            changed = False
            for s in direct_defs:
                if s.name not in pure:
                    continue
                sb = self._collect_fn_bound_names(s)
                sl = self._collect_loaded_names(list(s.body))
                sc = self._collect_comp_and_walrus_names(s)
                free = sl - sb - sc - {s.name}
                if free & enclosing_non_sib:
                    pure.discard(s.name)
                    changed = True
                    continue
                if any(ref in sibling_names and ref not in pure for ref in free):
                    pure.discard(s.name)
                    changed = True
        pre: Dict[str, str] = {}
        for s in direct_defs:
            if s.name in pure:
                self.counter += 1
                pre[s.name] = f"_pyfasm_nested_{self.counter}"
        return pre

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        is_nested = len(self.scope_stack) > 0
        if is_nested:
            is_nested_gen = any(isinstance(sub, (ast.Yield, ast.YieldFrom)) for sub in walk_local_scope(node))
            if is_nested_gen or node.decorator_list:
                return node

        fn_bound = self._collect_fn_bound_names(node)
        active_top = self._active_nested_renames() if is_nested else {}
        pre_siblings = self._preassign_pure_siblings(node, fn_bound)

        self.scope_stack.append(fn_bound)
        self._nested_rename_stack.append(pre_siblings)
        try:
            self.generic_visit(node)
        finally:
            self._nested_rename_stack.pop()
            self.scope_stack.pop()

        if pre_siblings:
            rewriter = _RewriteNestedRefs(pre_siblings, shadowed=self._own_arg_names(node.args))
            node.body = [rewriter.visit(st) for st in node.body]

        if not is_nested:
            return node

        enclosing = self._enclosing_vars()
        loaded = self._collect_loaded_names(list(node.body))
        comp_bound = self._collect_comp_and_walrus_names(node)
        free = loaded - fn_bound - comp_bound - {node.name} - set(active_top.keys())
        captured = sorted(n for n in free if n in enclosing)

        if not captured:
            if node.name in active_top:
                lifted_name = active_top[node.name]
            else:
                self.counter += 1
                lifted_name = f"_pyfasm_nested_{self.counter}"
            self_rename = dict(active_top)
            self_rename[node.name] = lifted_name
            rewriter = _RewriteNestedRefs(self_rename, shadowed=self._own_arg_names(node.args))
            rewritten_body = [rewriter.visit(st) for st in node.body]
            lifted_fn = ast.FunctionDef(
                name=lifted_name,
                args=node.args,
                body=rewritten_body,
                decorator_list=[],
                returns=node.returns,
                lineno=getattr(node, "lineno", 1),
                col_offset=getattr(node, "col_offset", 0),
            )
            self.lambdas.append(lifted_fn)
            assign = ast.Assign(
                targets=[ast.Name(id=node.name, ctx=ast.Store())],
                value=ast.Name(id=lifted_name, ctx=ast.Load()),
            )
            return ast.copy_location(assign, node)

        self.counter += 1
        lifted_name = f"_pyfasm_closure_{self.counter}"
        preamble: List[ast.stmt] = [
            ast.Assign(
                targets=[ast.Name(id=cap_name, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_pyfasm_closure_get", ctx=ast.Load()),
                    args=[ast.Name(id="_pyfasm_env", ctx=ast.Load()), ast.Constant(value=idx)],
                    keywords=[],
                ),
            )
            for idx, cap_name in enumerate(captured)
        ]
        rewriter = _RewriteNestedRefs(
            active_top,
            closure_self_name=node.name,
            closure_lifted_name=lifted_name,
            shadowed=self._own_arg_names(node.args) | set(captured),
        )
        rewritten_body = [rewriter.visit(st) for st in node.body]
        lifted_fn = ast.FunctionDef(
            name=lifted_name,
            args=self._make_closure_args(node.args),
            body=preamble + rewritten_body,
            decorator_list=[],
            returns=node.returns,
            lineno=getattr(node, "lineno", 1),
            col_offset=getattr(node, "col_offset", 0),
        )
        self.lambdas.append(lifted_fn)
        factory_call = ast.Call(
            func=ast.Name(id="_pyfasm_closure_new", ctx=ast.Load()),
            args=[ast.Name(id=lifted_name, ctx=ast.Load())]
            + [ast.Name(id=cap_name, ctx=ast.Load()) for cap_name in captured],
            keywords=[],
        )
        assign = ast.Assign(
            targets=[ast.Name(id=node.name, ctx=ast.Store())],
            value=factory_call,
        )
        return ast.copy_location(assign, node)

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        own_args: Set[str] = set()
        for a in getattr(node.args, "posonlyargs", []):
            own_args.add(a.arg)
        for a in node.args.args:
            own_args.add(a.arg)
        for a in getattr(node.args, "kwonlyargs", []):
            own_args.add(a.arg)
        if node.args.vararg:
            own_args.add(node.args.vararg.arg)
        if node.args.kwarg:
            own_args.add(node.args.kwarg.arg)

        self.scope_stack.append(own_args)
        try:
            self.generic_visit(node)
        finally:
            self.scope_stack.pop()

        enclosing = self._enclosing_vars()
        comp_bound = self._collect_comp_and_walrus_names(node.body)
        loaded = self._collect_loaded_names([node.body])
        free = loaded - own_args - comp_bound
        captured = sorted(n for n in free if n in enclosing)

        # Capture early-bound default arguments (e.g. lambda vals=coeffs: ...)
        orig_args_list = list(node.args.args)
        orig_defaults = list(node.args.defaults)
        default_caps: List[Tuple[str, ast.expr]] = []
        new_defaults = list(orig_defaults)
        has_dynamic_default = any(not isinstance(d, ast.Constant) for d in orig_defaults)
        if orig_defaults and (captured or has_dynamic_default):
            def_start = len(orig_args_list) - len(orig_defaults)
            for d_i, d_expr in enumerate(orig_defaults):
                a_name = orig_args_list[def_start + d_i].arg
                default_caps.append((a_name, d_expr))
                new_defaults[d_i] = ast.Constant(value=-9223372036854775807)

        self.counter += 1
        if not captured and not default_caps:
            fn_name = f"_pyfasm_lambda_{self.counter}"
            fn_def = ast.FunctionDef(
                name=fn_name,
                args=node.args,
                body=[ast.Return(value=node.body)],
                decorator_list=[],
                returns=None,
                lineno=getattr(node, "lineno", 1),
                col_offset=getattr(node, "col_offset", 0),
            )
            self.lambdas.append(fn_def)
            return ast.copy_location(ast.Name(id=fn_name, ctx=ast.Load()), node)

        fn_name = f"_pyfasm_closure_{self.counter}"
        body_stmts: List[ast.stmt] = [
            ast.Assign(
                targets=[ast.Name(id=cap_name, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_pyfasm_closure_get", ctx=ast.Load()),
                    args=[ast.Name(id="_pyfasm_env", ctx=ast.Load()), ast.Constant(value=idx)],
                    keywords=[],
                ),
            )
            for idx, cap_name in enumerate(captured)
        ]
        for d_i, (a_name, _) in enumerate(default_caps):
            cap_idx = len(captured) + d_i
            body_stmts.append(
                ast.If(
                    test=ast.Compare(
                        left=ast.Name(id=a_name, ctx=ast.Load()),
                        ops=[ast.Eq()],
                        comparators=[ast.Constant(value=-9223372036854775807)],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=a_name, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(id="_pyfasm_closure_get", ctx=ast.Load()),
                                args=[ast.Name(id="_pyfasm_env", ctx=ast.Load()), ast.Constant(value=cap_idx)],
                                keywords=[],
                            ),
                        )
                    ],
                    orelse=[],
                )
            )
        body_stmts.append(ast.Return(value=node.body))
        patched_args = ast.arguments(
            posonlyargs=list(getattr(node.args, "posonlyargs", [])),
            args=orig_args_list,
            vararg=node.args.vararg,
            kwonlyargs=list(getattr(node.args, "kwonlyargs", [])),
            kw_defaults=list(getattr(node.args, "kw_defaults", [])),
            kwarg=node.args.kwarg,
            defaults=new_defaults,
        )
        fn_def = ast.FunctionDef(
            name=fn_name,
            args=self._make_closure_args(patched_args),
            body=body_stmts,
            decorator_list=[],
            returns=None,
            lineno=getattr(node, "lineno", 1),
            col_offset=getattr(node, "col_offset", 0),
        )
        self.lambdas.append(fn_def)
        cap_arg_exprs = [ast.Name(id=cap_name, ctx=ast.Load()) for cap_name in captured] + [
            d_expr for _, d_expr in default_caps
        ]
        factory_call = ast.Call(
            func=ast.Name(id="_pyfasm_closure_new", ctx=ast.Load()),
            args=[ast.Name(id=fn_name, ctx=ast.Load())] + cap_arg_exprs,
            keywords=[],
        )
        return ast.copy_location(factory_call, node)


LambdaLifter = ClosureLifter


class YieldFromTransformer(ast.NodeTransformer):
    """Desugars 'yield from expr' statements into a standard for-loop with yield."""

    def __init__(self):
        super().__init__()
        self.counter = 0

    def visit_Expr(self, node: ast.Expr) -> Any:
        self.generic_visit(node)
        if isinstance(node.value, ast.YieldFrom):
            self.counter += 1
            tmp_name = f"_pyfasm_yf_{self.counter}"
            loop_stmt = ast.For(
                target=ast.Name(id=tmp_name, ctx=ast.Store()),
                iter=node.value.value,
                body=[
                    ast.Expr(value=ast.Yield(value=ast.Name(id=tmp_name, ctx=ast.Load())))
                ],
                orelse=[]
            )
            return ast.copy_location(loop_stmt, node)
        return node

    def visit_Assign(self, node: ast.Assign) -> Any:
        self.generic_visit(node)
        if isinstance(node.value, ast.YieldFrom):
            self.counter += 1
            tmp_name = f"_pyfasm_yf_{self.counter}"
            loop_stmt = ast.For(
                target=ast.Name(id=tmp_name, ctx=ast.Store()),
                iter=node.value.value,
                body=[
                    ast.Expr(value=ast.Yield(value=ast.Name(id=tmp_name, ctx=ast.Load())))
                ],
                orelse=[]
            )
            assign_stmt = ast.Assign(
                targets=node.targets,
                value=ast.Constant(value=0)
            )
            return [ast.copy_location(loop_stmt, node), ast.copy_location(assign_stmt, node)]
        return node


class GeneratorExpLifter(ast.NodeTransformer):
    """Lifts anonymous generator expressions into module-level FunctionDef nodes."""

    BUILTIN_NAMES = {
        "range", "len", "print", "int", "str", "float", "bool",
        "abs", "min", "max", "sum", "list", "dict", "set", "tuple",
        "next", "iter", "open", "round", "pow", "ord", "chr", "input",
        "any", "all", "map", "filter", "zip", "enumerate", "eval",
        "bisect", "bisect_right", "bisect_left", "heappush", "heappop",
        "_pyfasm_cell_new", "_pyfasm_cell_get", "_pyfasm_cell_set",
        "gcd", "lcm", "isqrt", "factorial", "accumulate", "chain", "reduce",
        # Inspection & Object model
        "getattr", "hasattr", "setattr", "delattr", "isinstance", "issubclass",
        "callable", "classmethod", "staticmethod", "property", "super",
        "type", "object", "id", "repr", "dir", "vars", "format", "hash",
        "sorted", "reversed", "slice", "complex", "frozenset", "globals", "locals",
        # Built-in Exceptions & Warnings
        "BaseException", "Exception", "ValueError", "TypeError", "KeyError",
        "IndexError", "AttributeError", "RuntimeError", "NotImplementedError",
        "ZeroDivisionError", "AssertionError", "OverflowError", "StopIteration",
        "DeprecationWarning", "Warning", "LookupError", "NameError", "SyntaxError",
        "FileNotFoundError", "PermissionError", "OSError", "IOError",
    }

    def __init__(self, known_globals: Optional[Set[str]] = None):
        super().__init__()
        self.generators: List[ast.FunctionDef] = []
        self.counter: int = 0
        self.known_globals: Set[str] = set(known_globals or set())

    def _find_free_names(self, node: ast.AST, bound_names: Set[str]) -> List[str]:
        free_names: List[str] = []

        def _collect(curr: ast.AST, bound: Set[str]):
            if isinstance(curr, ast.Lambda):
                lambda_bound = set(bound)
                for a in getattr(curr.args, "posonlyargs", []):
                    lambda_bound.add(a.arg)
                for a in curr.args.args:
                    lambda_bound.add(a.arg)
                for a in getattr(curr.args, "kwonlyargs", []):
                    lambda_bound.add(a.arg)
                if curr.args.vararg:
                    lambda_bound.add(curr.args.vararg.arg)
                if curr.args.kwarg:
                    lambda_bound.add(curr.args.kwarg.arg)
                for d in curr.args.defaults + [kd for kd in getattr(curr.args, "kw_defaults", []) if kd is not None]:
                    _collect(d, bound)
                _collect(curr.body, lambda_bound)
                return

            if isinstance(curr, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                comp_bound = set(bound)
                for gen in curr.generators:
                    for sub in ast.walk(gen.target):
                        if isinstance(sub, ast.Name):
                            comp_bound.add(sub.id)
                    for if_expr in gen.ifs:
                        _collect(if_expr, comp_bound)
                    _collect(gen.iter, bound)
                if isinstance(curr, ast.DictComp):
                    _collect(curr.key, comp_bound)
                    _collect(curr.value, comp_bound)
                else:
                    _collect(getattr(curr, "elt"), comp_bound)
                return

            if isinstance(curr, ast.Name) and isinstance(curr.ctx, ast.Load):
                nid = curr.id
                if nid not in bound and nid not in self.BUILTIN_NAMES and nid not in self.known_globals:
                    if nid not in free_names:
                        free_names.append(nid)
                return

            for child in ast.iter_child_nodes(curr):
                _collect(child, bound)

        _collect(node, set(bound_names))
        return free_names

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> ast.AST:
        self.generic_visit(node)
        self.counter += 1
        fn_name = f"_pyfasm_genexp_{self.counter}"

        # Collect targets from comprehension clauses
        targets = set()
        for comp in node.generators:
            for sub in ast.walk(comp.target):
                if isinstance(sub, ast.Name):
                    targets.add(sub.id)
            for sub in ast.walk(comp):
                if isinstance(sub, ast.NamedExpr) and isinstance(sub.target, ast.Name):
                    targets.add(sub.target.id)
        for sub in ast.walk(node.elt):
            if isinstance(sub, ast.NamedExpr) and isinstance(sub.target, ast.Name):
                targets.add(sub.target.id)

        # Free names: check elt, ifs, and secondary iters (idx > 0)
        free_names_set = set()
        for idx, comp in enumerate(node.generators):
            if idx > 0:
                for fn in self._find_free_names(comp.iter, targets):
                    free_names_set.add(fn)
            for if_expr in comp.ifs:
                for fn in self._find_free_names(if_expr, targets):
                    free_names_set.add(fn)
        for fn in self._find_free_names(node.elt, targets):
            free_names_set.add(fn)

        ordered_free = sorted(list(free_names_set))

        # First iterator is passed as _iter_0 (matching Python PEP 289 semantics)
        fn_param_names = ["_iter_0"] + ordered_free

        # Build nested loop body with yield
        inner_body: List[ast.stmt] = [ast.Expr(value=ast.Yield(value=node.elt))]
        for comp_idx in reversed(range(len(node.generators))):
            comp = node.generators[comp_idx]
            current_body = inner_body
            for if_expr in reversed(comp.ifs):
                current_body = [ast.If(test=if_expr, body=current_body, orelse=[])]

            iter_expr = ast.Name(id="_iter_0", ctx=ast.Load()) if comp_idx == 0 else comp.iter
            inner_body = [ast.For(
                target=comp.target,
                iter=iter_expr,
                body=current_body,
                orelse=[]
            )]

        fn_def = ast.FunctionDef(
            name=fn_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=name, annotation=None, type_comment=None) for name in fn_param_names],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[]
            ),
            body=inner_body,
            decorator_list=[],
            returns=None,
            lineno=getattr(node, "lineno", 1),
            col_offset=getattr(node, "col_offset", 0)
        )
        self.generators.append(fn_def)

        # Replace with call: first iter expr + free variable names
        call_args = [node.generators[0].iter] + [ast.Name(id=fn, ctx=ast.Load()) for fn in ordered_free]
        call_node = ast.Call(
            func=ast.Name(id=fn_name, ctx=ast.Load()),
            args=call_args,
            keywords=[]
        )
        return ast.copy_location(call_node, node)


class NonlocalCellTransformer(ast.NodeTransformer):
    """Boxes variables captured via `nonlocal` into shared 8-byte heap cells before ClosureLifter."""

    def __init__(self):
        super().__init__()
        self.counter: int = 0
        self.active_cells: Dict[str, str] = {}

    @staticmethod
    def _collect_target_names(target: ast.AST, out: Set[str]) -> None:
        if isinstance(target, ast.Name):
            out.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                NonlocalCellTransformer._collect_target_names(elt, out)
        elif isinstance(target, ast.Starred):
            NonlocalCellTransformer._collect_target_names(target.value, out)

    @classmethod
    def collect_direct_bindings(cls, fn_node: ast.AST) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
        """Return (own_params, own_bound, own_globals, own_nonlocals) for a function AST node."""
        own_params: Set[str] = set()
        args = getattr(fn_node, "args", None)
        if args is not None:
            for a in getattr(args, "posonlyargs", []):
                own_params.add(a.arg)
            for a in args.args:
                own_params.add(a.arg)
            for a in getattr(args, "kwonlyargs", []):
                own_params.add(a.arg)
            if args.vararg:
                own_params.add(args.vararg.arg)
            if args.kwarg:
                own_params.add(args.kwarg.arg)

        assigned: Set[str] = set(own_params)
        own_globals: Set[str] = set()
        own_nonlocals: Set[str] = set()
        for sub in walk_local_scope(fn_node):
            if isinstance(sub, ast.Global):
                own_globals.update(sub.names)
            elif isinstance(sub, ast.Nonlocal):
                own_nonlocals.update(sub.names)
            elif isinstance(sub, ast.Assign):
                for t in sub.targets:
                    cls._collect_target_names(t, assigned)
            elif isinstance(sub, ast.AnnAssign):
                cls._collect_target_names(sub.target, assigned)
            elif isinstance(sub, ast.AugAssign):
                cls._collect_target_names(sub.target, assigned)
            elif isinstance(sub, ast.For):
                cls._collect_target_names(sub.target, assigned)
            elif isinstance(sub, ast.With):
                for item in sub.items:
                    if item.optional_vars:
                        cls._collect_target_names(item.optional_vars, assigned)
            elif isinstance(sub, ast.ExceptHandler) and sub.name:
                assigned.add(sub.name)
            elif isinstance(sub, ast.NamedExpr):
                cls._collect_target_names(sub.target, assigned)
            elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and sub is not fn_node:
                assigned.add(sub.name)
            elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                for alias in sub.names:
                    assigned.add(alias.asname or alias.name.split(".")[0])

        own_bound = assigned - own_globals - own_nonlocals
        return own_params, own_bound, own_globals, own_nonlocals

    @classmethod
    def _find_needed_nonlocals(cls, container: ast.AST, candidates: Set[str]) -> Set[str]:
        needed: Set[str] = set()
        if not candidates:
            return needed

        def _walk_children(node: ast.AST, rem: Set[str]) -> None:
            if not rem:
                return
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _, sub_bound, sub_globals, sub_nonlocals = cls.collect_direct_bindings(child)
                    needed.update(rem & sub_nonlocals)
                    next_rem = rem - sub_bound - sub_globals
                    if next_rem:
                        _walk_children(child, next_rem)
                else:
                    _walk_children(child, rem)

        _walk_children(container, set(candidates))
        return needed

    @staticmethod
    def _make_cell_get(cell_name: str, ref_node: Optional[ast.AST] = None) -> ast.Call:
        call = ast.Call(
            func=ast.Name(id="_pyfasm_cell_get", ctx=ast.Load()),
            args=[ast.Name(id=cell_name, ctx=ast.Load())],
            keywords=[],
        )
        return ast.copy_location(call, ref_node) if ref_node is not None else call

    @staticmethod
    def _make_cell_set(cell_name: str, value_expr: ast.expr, ref_node: Optional[ast.AST] = None) -> ast.Call:
        call = ast.Call(
            func=ast.Name(id="_pyfasm_cell_set", ctx=ast.Load()),
            args=[ast.Name(id=cell_name, ctx=ast.Load()), value_expr],
            keywords=[],
        )
        return ast.copy_location(call, ref_node) if ref_node is not None else call

    def _target_has_cell_store(self, node: ast.AST) -> bool:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store) and sub.id in self.active_cells:
                return True
        return False

    def _replace_cell_stores_with_temps(self, target: ast.AST, replacements: List[Tuple[str, str]]) -> ast.AST:
        """Replace cell-var stores in a complex target with fresh temps and rewrite nested loads."""
        if isinstance(target, ast.Name):
            if isinstance(target.ctx, ast.Store) and target.id in self.active_cells:
                self.counter += 1
                tmp_name = f"_pyfasm_nl_tmp_{self.counter}"
                replacements.append((self.active_cells[target.id], tmp_name))
                return ast.copy_location(ast.Name(id=tmp_name, ctx=ast.Store()), target)
            return target
        if isinstance(target, (ast.Tuple, ast.List)):
            target.elts = [self._replace_cell_stores_with_temps(elt, replacements) for elt in target.elts]
            return target
        if isinstance(target, ast.Starred):
            target.value = self._replace_cell_stores_with_temps(target.value, replacements)
            return target
        return self.visit(target)

    def _visit_stmt_block(self, stmts: List[ast.stmt]) -> List[ast.stmt]:
        out: List[ast.stmt] = []
        for s in stmts:
            res = self.visit(s)
            if res is None:
                continue
            if isinstance(res, list):
                out.extend(res)
            else:
                out.append(res)
        return out

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.active_cells:
            return self._make_cell_get(self.active_cells[node.id], node)
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.AST:
        remaining = [nm for nm in node.names if nm not in self.active_cells]
        if not remaining:
            return ast.copy_location(ast.Pass(), node)
        node.names = remaining
        return node

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ast.AST:
        new_val = self.visit(node.value)
        if node.target.id in self.active_cells:
            return self._make_cell_set(self.active_cells[node.target.id], new_val, node)
        node.value = new_val
        return node

    def visit_Assign(self, node: ast.Assign) -> Any:
        new_val = self.visit(node.value)
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in self.active_cells
        ):
            call = self._make_cell_set(self.active_cells[node.targets[0].id], new_val, node)
            return ast.copy_location(ast.Expr(value=call), node)

        if any(self._target_has_cell_store(t) for t in node.targets):
            replacements: List[Tuple[str, str]] = []
            new_targets = [self._replace_cell_stores_with_temps(t, replacements) for t in node.targets]
            node.targets = new_targets
            node.value = new_val
            stmts: List[ast.stmt] = [node]
            for cell_name, tmp_name in replacements:
                set_call = self._make_cell_set(cell_name, ast.Name(id=tmp_name, ctx=ast.Load()), node)
                stmts.append(ast.copy_location(ast.Expr(value=set_call), node))
            return stmts

        node.targets = [self.visit(t) for t in node.targets]
        node.value = new_val
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
        if isinstance(node.target, ast.Name) and node.target.id in self.active_cells:
            if node.value is not None:
                new_val = self.visit(node.value)
                call = self._make_cell_set(self.active_cells[node.target.id], new_val, node)
                return ast.copy_location(ast.Expr(value=call), node)
            return ast.copy_location(ast.Pass(), node)
        node.target = self.visit(node.target)
        if node.value is not None:
            node.value = self.visit(node.value)
        return node

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        new_val = self.visit(node.value)
        if isinstance(node.target, ast.Name) and node.target.id in self.active_cells:
            cell_name = self.active_cells[node.target.id]
            bin_op = ast.copy_location(
                ast.BinOp(left=self._make_cell_get(cell_name, node), op=node.op, right=new_val),
                node,
            )
            call = self._make_cell_set(cell_name, bin_op, node)
            return ast.copy_location(ast.Expr(value=call), node)
        node.target = self.visit(node.target)
        node.value = new_val
        return node

    def visit_For(self, node: ast.For) -> ast.AST:
        node.iter = self.visit(node.iter)
        node.body = self._visit_stmt_block(node.body)
        node.orelse = self._visit_stmt_block(node.orelse)
        if self._target_has_cell_store(node.target):
            replacements: List[Tuple[str, str]] = []
            node.target = self._replace_cell_stores_with_temps(node.target, replacements)
            prefix: List[ast.stmt] = [
                ast.copy_location(
                    ast.Expr(value=self._make_cell_set(cell_name, ast.Name(id=tmp_name, ctx=ast.Load()), node)),
                    node,
                )
                for cell_name, tmp_name in replacements
            ]
            node.body = prefix + node.body
        else:
            node.target = self.visit(node.target)
        return node

    def visit_With(self, node: ast.With) -> ast.AST:
        node.items = [
            ast.withitem(
                context_expr=self.visit(item.context_expr),
                optional_vars=self.visit(item.optional_vars) if item.optional_vars is not None else None,
            )
            for item in node.items
        ]
        node.body = self._visit_stmt_block(node.body)
        return node

    def visit_If(self, node: ast.If) -> ast.AST:
        node.test = self.visit(node.test)
        node.body = self._visit_stmt_block(node.body)
        node.orelse = self._visit_stmt_block(node.orelse)
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        node.test = self.visit(node.test)
        node.body = self._visit_stmt_block(node.body)
        node.orelse = self._visit_stmt_block(node.orelse)
        return node

    def visit_Try(self, node: ast.Try) -> ast.AST:
        node.body = self._visit_stmt_block(node.body)
        for handler in node.handlers:
            if handler.type is not None:
                handler.type = self.visit(handler.type)
            handler.body = self._visit_stmt_block(handler.body)
        node.orelse = self._visit_stmt_block(node.orelse)
        node.finalbody = self._visit_stmt_block(node.finalbody)
        return node

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        node.args.defaults = [self.visit(d) for d in node.args.defaults]
        node.args.kw_defaults = [self.visit(kd) if kd is not None else None for kd in node.args.kw_defaults]
        own_args: Set[str] = set()
        for a in getattr(node.args, "posonlyargs", []):
            own_args.add(a.arg)
        for a in node.args.args:
            own_args.add(a.arg)
        for a in getattr(node.args, "kwonlyargs", []):
            own_args.add(a.arg)
        if node.args.vararg:
            own_args.add(node.args.vararg.arg)
        if node.args.kwarg:
            own_args.add(node.args.kwarg.arg)
        prev = self.active_cells
        self.active_cells = {k: v for k, v in prev.items() if k not in own_args}
        try:
            node.body = self.visit(node.body)
        finally:
            self.active_cells = prev
        return node

    def _visit_comprehension(self, node: ast.AST) -> ast.AST:
        gens = getattr(node, "generators", [])
        if gens:
            gens[0].iter = self.visit(gens[0].iter)
        comp_bound: Set[str] = set()
        for g in gens:
            self._collect_target_names(g.target, comp_bound)
        prev = self.active_cells
        self.active_cells = {k: v for k, v in prev.items() if k not in comp_bound}
        try:
            for idx, g in enumerate(gens):
                if idx > 0:
                    g.iter = self.visit(g.iter)
                g.ifs = [self.visit(c) for c in g.ifs]
            if isinstance(node, ast.DictComp):
                node.key = self.visit(node.key)
                node.value = self.visit(node.value)
            else:
                node.elt = self.visit(node.elt)
        finally:
            self.active_cells = prev
        return node

    def visit_ListComp(self, node: ast.ListComp) -> ast.AST:
        return self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> ast.AST:
        return self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> ast.AST:
        return self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> ast.AST:
        return self._visit_comprehension(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.bases = [self.visit(b) for b in node.bases]
        node.keywords = [ast.keyword(arg=k.arg, value=self.visit(k.value)) for k in node.keywords]
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        node.body = self._visit_stmt_block(node.body)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        node.args.defaults = [self.visit(d) for d in node.args.defaults]
        node.args.kw_defaults = [self.visit(kd) if kd is not None else None for kd in node.args.kw_defaults]

        own_params, own_bound, own_globals, _ = self.collect_direct_bindings(node)
        needed_here = self._find_needed_nonlocals(node, own_bound)

        owned_cells: Dict[str, str] = {}
        init_stmts: List[ast.stmt] = []
        for var_name in sorted(needed_here):
            self.counter += 1
            cell_name = f"_pyfasm_cell_{self.counter}_{var_name}"
            owned_cells[var_name] = cell_name
            init_args = [ast.Name(id=var_name, ctx=ast.Load())] if var_name in own_params else []
            init_assign = ast.Assign(
                targets=[ast.Name(id=cell_name, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id="_pyfasm_cell_new", ctx=ast.Load()),
                    args=init_args,
                    keywords=[],
                ),
            )
            init_stmts.append(ast.copy_location(init_assign, node))

        prev = self.active_cells
        child_cells = {k: v for k, v in prev.items() if k not in own_bound and k not in own_globals}
        child_cells.update(owned_cells)
        self.active_cells = child_cells
        try:
            node.body = init_stmts + self._visit_stmt_block(node.body)
        finally:
            self.active_cells = prev
        return node


def preprocess_ast(
    tree: ast.AST,
    py_version: Optional[Tuple[int, int]] = None,
    py_micro: Optional[int] = None,
) -> ast.AST:
    """Preprocesses AST: folds constants, desugars yield from, lifts generator expressions and lambdas."""
    tree = ImportCallTransformer().visit(tree)
    tree = ClassLambdaDesugarer().visit(tree)
    tree = MapMethodTransformer().visit(tree)
    tree = ChainedCompareTransformer().visit(tree)
    tree = ConstantFolder(py_version=py_version, py_micro=py_micro).visit(tree)
    tree = YieldFromTransformer().visit(tree)
    tree = NonlocalCellTransformer().visit(tree)

    known_globals = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Import):
            for alias in node.names:
                known_globals.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                known_globals.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            known_globals.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    known_globals.add(target.id)

    gen_lifter = GeneratorExpLifter(known_globals=known_globals)
    tree = gen_lifter.visit(tree)
    for gen_def in gen_lifter.generators:
        tree.body.append(gen_def)
    lambda_lifter = LambdaLifter()
    tree = lambda_lifter.visit(tree)
    for lambda_def in lambda_lifter.lambdas:
        tree.body.append(lambda_def)
    ast.fix_missing_locations(tree)
    return tree


class AstAnalyzer:
    """Extracts function signatures, local variables, and literals across single files or multi-module projects."""

    def __init__(
        self,
        project_root: Optional[Path | str] = None,
        py_version: Optional[Tuple[int, int]] = None,
        py_micro: Optional[int] = None,
    ):
        self.strings: List[StringLiteral] = []
        self.floats: List[FloatLiteral] = []
        self.project_root: Optional[Path] = Path(project_root).resolve() if project_root else None
        self.py_version: Tuple[int, int] = py_version or (sys.version_info.major, sys.version_info.minor)
        self.py_micro: int = py_micro if py_micro is not None else sys.version_info.micro
        self._visited_files: Set[Path] = set()
        self._site_packages_dirs: List[Path] = []
        self._str_counter = 0
        self._flt_counter = 0
        self._current_source_file: Optional[str] = None
        self._current_mod_prefix: str = ""
        self._closure_cap_types: Dict[str, List[PyFasmType]] = {}
        self._genexp_arg_types: Dict[str, List[PyFasmType]] = {}
        self._current_func_name: str = ""
        if self.project_root:
            self._discover_site_packages()

    @staticmethod
    def _ast_span(node: ast.AST) -> tuple:
        lineno = getattr(node, "lineno", None)
        col0 = getattr(node, "col_offset", None)
        col = (col0 + 1) if isinstance(col0, int) else None
        end_col0 = getattr(node, "end_col_offset", None)
        end_ln = getattr(node, "end_lineno", lineno)
        end_col = (end_col0 + 1) if (isinstance(end_col0, int) and end_ln == lineno) else None
        return lineno, col, end_col

    def _is_binary_site_package(self, root_name: str) -> bool:
        for sp in self._site_packages_dirs:
            pkg_dir = sp / root_name
            mod_file = sp / f"{root_name}.py"
            if (pkg_dir.is_dir() and self._is_binary_extension_module(pkg_dir)) or (
                mod_file.is_file() and self._is_binary_extension_module(mod_file)
            ):
                return True
        return False

    def _validate_ast_tree(
        self,
        tree: ast.AST,
        module: ParsedModule,
        file_path: Optional[str],
        source_text: str,
        current_dir: Optional[Path] = None,
    ) -> None:
        """Collects semantic errors and warnings before AST lowering."""
        key = file_path or "<source>"
        module.source_files[key] = source_text
        src_lines = source_text.splitlines()

        def _line_at(ln: Optional[int]) -> Optional[str]:
            if ln is not None and 1 <= ln <= len(src_lines):
                return src_lines[ln - 1]
            return None

        cm_classes: Set[str] = set()
        for cls_node in ast.walk(tree):
            if isinstance(cls_node, ast.ClassDef):
                for cls_item in cls_node.body:
                    if isinstance(cls_item, (ast.FunctionDef, ast.AsyncFunctionDef)) and cls_item.name in ("__enter__", "__exit__"):
                        cm_classes.add(cls_node.name)
                        break

        cm_var_names: Set[str] = set()
        if cm_classes:
            for sub in ast.walk(tree):
                if isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Call) and isinstance(sub.value.func, ast.Name):
                    if sub.value.func.id in cm_classes:
                        for tgt in sub.targets:
                            if isinstance(tgt, ast.Name):
                                cm_var_names.add(tgt.id)
                elif isinstance(sub, ast.arg) and isinstance(getattr(sub, "annotation", None), ast.Name):
                    if sub.annotation.id in cm_classes:
                        cm_var_names.add(sub.arg)

        def _check_import(mod_name: str, imp_node: ast.AST) -> None:
            if not mod_name:
                return
            root = mod_name.split(".")[0].lower().replace("-", "_")
            if root in NATIVELY_SUPPORTED_OR_ADAPTED_MODULES:
                return
            if current_dir is not None:
                resolved = self._resolve_local_module(mod_name, current_dir)
                if resolved is not None:
                    res_low = str(resolved).lower()
                    if ".venv" not in res_low and "venv" not in res_low and "site-packages" not in res_low:
                        return
            if root in KNOWN_UNSUPPORTED_EXTERNAL_MODULES or self._is_binary_site_package(root):
                ln, col, end_col = self._ast_span(imp_node)
                module.diagnostics.append(
                    CompilerDiagnostic(
                        severity="warning",
                        code="W2005",
                        message=(
                            f"External or C-extension module '{mod_name}' is not natively "
                            "compiled by PyFASM64 in standalone compile mode"
                        ),
                        file_path=key,
                        lineno=ln,
                        col_offset=col,
                        end_col_offset=end_col,
                        source_line=_line_at(ln),
                        hint=(
                            "Use `pyfasm64 bundle` to package apps with external/C-extension dependencies, "
                            "or compile pure compute hotspots as `--target dll`."
                        ),
                    )
                )

        for node in ast.walk(tree):
            ln, col, end_col = self._ast_span(node)
            src_line = _line_at(ln)
            if isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
                construct = type(node).__name__.replace("Async", "async ").replace("Await", "await")
                module.diagnostics.append(
                    CompilerDiagnostic(
                        severity="error",
                        code="E2001",
                        message=f"Asyncio construct '{construct}' is not supported in AOT native compilation",
                        file_path=key,
                        lineno=ln,
                        col_offset=col,
                        end_col_offset=end_col,
                        source_line=src_line,
                        hint=(
                            "Use OS threads (`spawn_thread()` / `wait_thread()`) for native concurrency, "
                            "or package async code with `pyfasm64 bundle`."
                        ),
                    )
                )
            elif isinstance(node, ast.ClassDef):
                for kw in getattr(node, "keywords", []):
                    if kw.arg == "metaclass":
                        k_ln, k_col, k_end = self._ast_span(kw)
                        module.diagnostics.append(
                            CompilerDiagnostic(
                                severity="error",
                                code="E2002",
                                message=f"Metaclasses are not supported on class '{node.name}'",
                                file_path=key,
                                lineno=k_ln or ln,
                                col_offset=k_col or col,
                                end_col_offset=k_end,
                                source_line=_line_at(k_ln or ln),
                                hint="Use standard single inheritance, `@property`, or helper factory functions instead of metaclasses.",
                            )
                        )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in UNSUPPORTED_DUNDERS:
                        m_ln, m_col, m_end = self._ast_span(item)
                        module.diagnostics.append(
                            CompilerDiagnostic(
                                severity="warning",
                                code="W2006",
                                message=f"Magic method '{node.name}.{item.name}' is not wired for automatic dispatch",
                                file_path=key,
                                lineno=m_ln,
                                col_offset=m_col,
                                end_col_offset=m_end,
                                source_line=_line_at(m_ln),
                                hint=f"Supported dunder methods: {SUPPORTED_DUNDERS_SUMMARY}.",
                            )
                        )
            elif isinstance(node, ast.With):
                for item in node.items:
                    ctx = item.context_expr
                    is_open_call = (
                        isinstance(ctx, ast.Call)
                        and isinstance(ctx.func, ast.Name)
                        and ctx.func.id == "open"
                    )
                    is_custom_cm = (
                        (isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Name) and ctx.func.id in cm_classes)
                        or (isinstance(ctx, ast.Name) and ctx.id in cm_var_names)
                    )
                    if not is_open_call and not is_custom_cm:
                        w_ln, w_col, w_end = self._ast_span(ctx)
                        module.diagnostics.append(
                            CompilerDiagnostic(
                                severity="warning",
                                code="W2004",
                                message="Custom `with` context manager is not natively lowered (only `with open(...)` is compiled)",
                                file_path=key,
                                lineno=w_ln or ln,
                                col_offset=w_col or col,
                                end_col_offset=w_end,
                                source_line=_line_at(w_ln or ln),
                                hint="Call explicit setup/cleanup methods in `try ... finally`, or use `pyfasm64 bundle`.",
                            )
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    _check_import(alias.name, alias if hasattr(alias, "lineno") else node)
            elif isinstance(node, ast.ImportFrom):
                if getattr(node, "level", 0) == 0 and node.module:
                    _check_import(node.module, node)

        # Lexical scope check for `nonlocal`: reject only unbound module-level or missing bindings
        def _emit_nonlocal_err(nl_node: ast.Nonlocal, var_name: str, reason: str) -> None:
            nl_ln, nl_col, nl_end = self._ast_span(nl_node)
            module.diagnostics.append(
                CompilerDiagnostic(
                    severity="error",
                    code="E2003",
                    message=f"No binding for nonlocal '{var_name}' {reason}",
                    file_path=key,
                    lineno=nl_ln,
                    col_offset=nl_col,
                    end_col_offset=nl_end,
                    source_line=_line_at(nl_ln),
                    hint=f"Bind '{var_name}' in an enclosing function scope (or declare it `global` at module level).",
                )
            )

        def _validate_nonlocal_container(container: ast.AST, encl_bounds: List[Set[str]]) -> None:
            for sub in walk_local_scope(container):
                if isinstance(sub, ast.Nonlocal):
                    for nm in sub.names:
                        if not encl_bounds:
                            _emit_nonlocal_err(sub, nm, "allowed at module scope")
                        elif not any(nm in b for b in encl_bounds):
                            _emit_nonlocal_err(sub, nm, "found in enclosing function scopes")

            def _scan_children(cur: ast.AST) -> None:
                for child in ast.iter_child_nodes(cur):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _, own_bound, _, _ = NonlocalCellTransformer.collect_direct_bindings(child)
                        _validate_nonlocal_container_with_bound(child, encl_bounds, own_bound)
                    else:
                        _scan_children(child)

            _scan_children(container)

        def _validate_nonlocal_container_with_bound(
            fn_node: ast.AST, encl_bounds: List[Set[str]], own_bound: Set[str]
        ) -> None:
            for sub in walk_local_scope(fn_node):
                if isinstance(sub, ast.Nonlocal):
                    for nm in sub.names:
                        if not any(nm in b for b in encl_bounds):
                            _emit_nonlocal_err(sub, nm, "found in enclosing function scopes")
            encl_bounds.append(own_bound)
            try:
                def _scan_nested(cur: ast.AST) -> None:
                    for child in ast.iter_child_nodes(cur):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            _, sub_bound, _, _ = NonlocalCellTransformer.collect_direct_bindings(child)
                            _validate_nonlocal_container_with_bound(child, encl_bounds, sub_bound)
                        else:
                            _scan_nested(child)
                _scan_nested(fn_node)
            finally:
                encl_bounds.pop()

        _validate_nonlocal_container(tree, [])

    def get_or_create_string(self, text: str) -> str:
        for s in self.strings:
            if s.value == text:
                return s.label
        self._str_counter += 1
        label = f"_str_lit_{self._str_counter}"
        self.strings.append(StringLiteral(label=label, value=text))
        return label

    def get_or_create_float(self, val: float) -> str:
        val_f = float(val)
        val_bytes = struct.pack("<d", val_f)
        for f in self.floats:
            if struct.pack("<d", f.value) == val_bytes:
                return f.label
        self._flt_counter += 1
        label = f"_flt_lit_{self._flt_counter}"
        self.floats.append(FloatLiteral(label=label, value=val_f))
        return label

    def _detect_project_libraries(self, module: ParsedModule) -> None:
        """Inspects project dependencies from pyproject.toml, requirements.txt, uv.lock, and imports."""
        if not self.project_root or not self.project_root.exists():
            return

        def _add_dep_spec(spec: str) -> None:
            m = re.match(r"^\s*([a-zA-Z0-9_.-]+)", spec)
            if m:
                lib = m.group(1).lower().replace("-", "_").replace(".", "_")
                if lib not in ("pyfasm", "pyfasm64", "python"):
                    module.detected_libraries.add(lib)

        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                raw_bytes = pyproject.read_bytes()
                parsed_toml = None
                try:
                    import tomllib  # Python 3.11+
                    parsed_toml = tomllib.loads(raw_bytes.decode("utf-8", errors="ignore"))
                except ImportError:
                    parsed_toml = None

                if isinstance(parsed_toml, dict):
                    proj_tbl = parsed_toml.get("project", {})
                    if isinstance(proj_tbl, dict):
                        for dep in proj_tbl.get("dependencies", []) or []:
                            if isinstance(dep, str):
                                _add_dep_spec(dep)
                        opt_deps = proj_tbl.get("optional-dependencies", {}) or {}
                        if isinstance(opt_deps, dict):
                            for group_list in opt_deps.values():
                                if isinstance(group_list, list):
                                    for dep in group_list:
                                        if isinstance(dep, str):
                                            _add_dep_spec(dep)
                    dep_groups = parsed_toml.get("dependency-groups", {}) or {}
                    if isinstance(dep_groups, dict):
                        for group_list in dep_groups.values():
                            if isinstance(group_list, list):
                                for dep in group_list:
                                    if isinstance(dep, str):
                                        _add_dep_spec(dep)
                    poetry_deps = parsed_toml.get("tool", {}).get("poetry", {}).get("dependencies", {})
                    if isinstance(poetry_deps, dict):
                        for dep_name in poetry_deps.keys():
                            if isinstance(dep_name, str):
                                _add_dep_spec(dep_name)
                else:
                    text = raw_bytes.decode("utf-8", errors="ignore")
                    for block in re.finditer(r"dependencies\s*=\s*\[(.*?)\]", text, re.S):
                        for match in re.finditer(r"['\"]([a-zA-Z0-9_.-]+)", block.group(1)):
                            _add_dep_spec(match.group(1))
            except Exception:
                pass

        reqs = self.project_root / "requirements.txt"
        if reqs.exists():
            try:
                for line in reqs.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip().split("#")[0].strip()
                    if line:
                        _add_dep_spec(line)
            except Exception:
                pass

        uvlock = self.project_root / "uv.lock"
        if uvlock.exists():
            try:
                text = uvlock.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r"^\s*name\s*=\s*['\"]([a-zA-Z0-9_.-]+)['\"]", text, re.M):
                    _add_dep_spec(match.group(1))
            except Exception:
                pass

    def _propagate_generator_types(self, module: ParsedModule) -> None:
        """Marks local variables that receive generator call returns with is_generator = True."""
        for fn in module.functions.values():
            if fn.ast_node:
                for sub in walk_local_scope(fn.ast_node):
                    if isinstance(sub, ast.Assign) and len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Name):
                        if isinstance(sub.value, ast.Call) and isinstance(sub.value.func, ast.Name):
                            target_fn = module.functions.get(sub.value.func.id)
                            if target_fn and getattr(target_fn, "is_generator", False):
                                v = fn.local_vars.get(sub.targets[0].id)
                                if v:
                                    v.is_generator = True
                                    v.var_type = TYPE_GENERATOR

    def parse_source(self, source_code: str) -> ParsedModule:
        """Parses a raw Python source code string into a ParsedModule."""
        source_code = source_code.lstrip("\ufeff")
        module = ParsedModule()
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            module.source_files["<source>"] = source_code
            module.diagnostics.append(from_syntax_error(e, file_path="<source>", source_text=source_code))
            return module

        pending_routes = self._prepare_fastapi_routes_in_tree(tree, mod_prefix="")
        self._validate_ast_tree(tree, module, "<source>", source_code, current_dir=self.project_root)
        tree = preprocess_ast(tree, py_version=self.py_version, py_micro=self.py_micro)

        # First pass: find imports, string and float constants across the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module.imports.append(alias.name)
                    module.detected_libraries.add(alias.name.split(".")[0].lower().replace("-", "_"))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module.imports.append(node.module)
                    module.detected_libraries.add(node.module.split(".")[0].lower().replace("-", "_"))
            elif isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    self.get_or_create_string(node.value)
                elif isinstance(node.value, float):
                    self.get_or_create_float(node.value)

        module.string_literals = self.strings
        module.float_literals = self.floats

        # Second pass: extract functions, classes, and top-level statements
        prev_file = self._current_source_file
        self._current_source_file = "<source>"
        try:
            self._extract_top_level_and_functions(tree, module, is_entry=True, mod_prefix="")
            self._finalize_http_routes(pending_routes, module, mod_prefix_pre="")
            self._propagate_generator_types(module)
        finally:
            self._current_source_file = prev_file

        return module

    def _discover_site_packages(self) -> None:
        """Finds active virtual environments (.venv, venv) to enable importing pure-Python packages."""
        if not self.project_root:
            return
        roots_to_check = [self.project_root]
        roots_to_check.extend(list(self.project_root.parents)[:3])
        for r in roots_to_check:
            for venv_name in (".venv", "venv"):
                v = r / venv_name
                if not v.is_dir():
                    continue
                # Windows site-packages
                win_sp = v / "Lib" / "site-packages"
                if win_sp.is_dir() and win_sp not in self._site_packages_dirs:
                    self._site_packages_dirs.append(win_sp)
                # Unix site-packages
                lib_dir = v / "lib"
                if lib_dir.is_dir():
                    for py_dir in lib_dir.glob("python*"):
                        u_sp = py_dir / "site-packages"
                        if u_sp.is_dir() and u_sp not in self._site_packages_dirs:
                            self._site_packages_dirs.append(u_sp)

    @staticmethod
    def _is_binary_extension_module(path: Path) -> bool:
        """Determines if a package/module relies on compiled C-extensions (.pyd, .so, .dll)."""
        parts = [p.lower() for p in path.parts]
        known = {
            "numpy", "scipy", "matplotlib", "torch", "cv2", "pandas",
            "cryptography", "win32api", "win32gui", "pythoncom", "ctypes",
            "customtkinter", "tkinter", "ttkbootstrap", "pil", "pillow",
            "pygame", "pyqt5", "pyqt6", "pyside6", "pyside2", "flet",
            "fastapi", "uvicorn", "starlette",
            "pyfasm", "pyfasm64", "nanogemm",
        }
        if any(k in parts for k in known):
            return True
        if path.is_file():
            if path.suffix.lower() in (".pyd", ".so", ".dll"):
                return True
        elif path.is_dir():
            if any(path.glob("*.pyd")) or any(path.glob("*.so")):
                return True
        return False

    def parse_file(self, file_path: str | Path, project_root: Optional[Path | str] = None) -> ParsedModule:
        """
        Parses an entry Python file and recursively discovers and compiles all
        imported local project modules into 1 unified standalone module.
        """
        entry_path = Path(file_path).resolve()
        if project_root:
            self.project_root = Path(project_root).resolve()
        elif not self.project_root:
            self.project_root = entry_path.parent
        self._discover_site_packages()

        module = ParsedModule()
        self._visited_files.clear()

        self._detect_project_libraries(module)
        # Recursively parse entry script and all internal project dependencies
        self._parse_file_recursive(entry_path, module, is_entry=True)

        # Fallback entry point resolution if main was imported or namespaced
        if module.main_func is None:
            if "main" in module.functions:
                module.main_func = module.functions["main"]
            else:
                for fn_name, fn_obj in module.functions.items():
                    if fn_name.endswith("_main"):
                        module.main_func = fn_obj
                        break

        try:
            from pyfasm.ui_analyzer import analyze_ui_structure
            entry_tree = ast.parse(entry_path.read_text(encoding="utf-8-sig").lstrip("\ufeff"))
            module.ui_spec = analyze_ui_structure(entry_tree)
            if not module.ui_spec and hasattr(self, "_visited_files"):
                for v_path in self._visited_files:
                    v_str = str(v_path).replace("\\", "/").lower()
                    if ".venv" in v_str or "site-packages" in v_str:
                        continue
                    try:
                        v_tree = ast.parse(v_path.read_text(encoding="utf-8-sig").lstrip("\ufeff"))
                        cand_spec = analyze_ui_structure(v_tree)
                        if cand_spec and (cand_spec.widgets or cand_spec.window_title != "PyFASM Application"):
                            module.ui_spec = cand_spec
                            break
                    except Exception:
                        pass
        except Exception:
            pass
        self._propagate_generator_types(module)
        module.string_literals = self.strings
        module.float_literals = self.floats
        return module

    def _resolve_local_module(self, mod_name: str, current_dir: Path) -> Optional[Path]:
        """Resolves an imported module name to a local or pure-Python venv file, strictly ignoring pyfasm itself."""
        if mod_name in ("pyfasm", "pyfasm64") or mod_name.startswith(("pyfasm.", "pyfasm64.")):
            return None

        parts = mod_name.split(".")
        top_pkg = parts[0].lower() if parts else ""
        known_ext = {
            "numpy", "scipy", "matplotlib", "torch", "cv2", "pandas",
            "cryptography", "win32api", "win32gui", "pythoncom", "ctypes",
            "customtkinter", "tkinter", "ttkbootstrap", "pil", "pillow",
            "pygame", "pyqt5", "pyqt6", "pyside6", "pyside2", "flet",
            "fastapi", "uvicorn", "starlette",
            "pyfasm", "pyfasm64", "nanogemm",
        }
        if top_pkg in known_ext:
            return None
        # 1. Try relative to current directory
        cand1 = current_dir.joinpath(*parts).with_suffix(".py")
        if cand1.exists() and cand1.is_file():
            return cand1
        cand2 = current_dir.joinpath(*parts, "__init__.py")
        if cand2.exists() and cand2.is_file():
            return cand2

        # 2. Try relative to project root
        if self.project_root:
            cand3 = self.project_root.joinpath(*parts).with_suffix(".py")
            if cand3.exists() and cand3.is_file():
                return cand3
            cand4 = self.project_root.joinpath(*parts, "__init__.py")
            if cand4.exists() and cand4.is_file():
                return cand4

        # 3. Try site-packages from project venv (pure-Python packages only)
        for sp in self._site_packages_dirs:
            cand5 = sp.joinpath(*parts).with_suffix(".py")
            if cand5.exists() and cand5.is_file() and not self._is_binary_extension_module(cand5):
                return cand5
            cand6 = sp.joinpath(*parts, "__init__.py")
            if cand6.exists() and cand6.is_file() and not self._is_binary_extension_module(cand6.parent):
                return cand6

        return None

    @staticmethod
    def _normalize_http_path(prefix: str, route_path: str) -> str:
        p1 = prefix.strip() if prefix else ""
        p2 = route_path.strip() if route_path else "/"
        joined = f"/{p1.strip('/')}/{p2.strip('/')}".replace("//", "/")
        if len(joined) > 1:
            joined = joined.rstrip("/")
        return joined or "/"

    def _prepare_fastapi_routes_in_tree(
        self, tree: ast.AST, mod_prefix: str = ""
    ) -> List[Tuple[str, str, str, str]]:
        """Harvests @app.get/@router.post decorators & lowers FastAPI async defs before validation."""
        has_fastapi = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name.split(".")[0] == "fastapi" for a in node.names):
                has_fastapi = True
                break
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "fastapi":
                has_fastapi = True
                break
        if not has_fastapi or not isinstance(tree, ast.Module):
            return []

        app_names: Set[str] = {"app"}
        router_prefixes: Dict[str, str] = {}
        raw_routes: List[Tuple[str, str, str, str]] = []  # (owner, method, path, fn_name)
        http_methods = {"get": "GET", "post": "POST", "put": "PUT", "delete": "DELETE", "patch": "PATCH"}

        new_body: List[ast.stmt] = []
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                tgt_name = stmt.targets[0].id
                if isinstance(stmt.value, ast.Call):
                    call_id = stmt.value.func.id if isinstance(stmt.value.func, ast.Name) else getattr(stmt.value.func, "attr", "")
                    if call_id == "FastAPI":
                        app_names.add(tgt_name)
                    elif call_id == "APIRouter":
                        pfx = ""
                        if stmt.value.args and isinstance(stmt.value.args[0], ast.Constant) and isinstance(stmt.value.args[0].value, str):
                            pfx = stmt.value.args[0].value
                        for kw in stmt.value.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                pfx = kw.value.value
                        router_prefixes[tgt_name] = pfx
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                c = stmt.value
                if isinstance(c.func, ast.Attribute) and c.func.attr == "include_router" and c.args:
                    r_name = c.args[0].id if isinstance(c.args[0], ast.Name) else ""
                    if r_name:
                        inc_pfx = ""
                        for kw in c.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                inc_pfx = kw.value.value
                        if inc_pfx:
                            old_pfx = router_prefixes.get(r_name, "")
                            router_prefixes[r_name] = self._normalize_http_path(inc_pfx, old_pfx)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.decorator_list:
                kept_decs: List[ast.expr] = []
                matched_fastapi = False
                for dec in stmt.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        m_low = dec.func.attr.lower()
                        owner = dec.func.value.id if isinstance(dec.func.value, ast.Name) else ""
                        if m_low in http_methods and (owner in app_names or owner in router_prefixes or owner in ("app", "router", "api")):
                            r_path = "/"
                            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                                r_path = dec.args[0].value
                            else:
                                for kw in dec.keywords:
                                    if kw.arg == "path" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                        r_path = kw.value.value
                            fn_key = f"{mod_prefix}_{stmt.name}" if mod_prefix else stmt.name
                            raw_routes.append((owner, http_methods[m_low], r_path, fn_key))
                            matched_fastapi = True
                            continue
                    kept_decs.append(dec)
                if matched_fastapi:
                    stmt.decorator_list = kept_decs
                    if isinstance(stmt, ast.AsyncFunctionDef):
                        has_real_await = any(isinstance(sub, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for sub in walk_local_scope(stmt))
                        if not has_real_await:
                            sync_fn = ast.FunctionDef(
                                name=stmt.name,
                                args=stmt.args,
                                body=stmt.body,
                                decorator_list=stmt.decorator_list,
                                returns=stmt.returns,
                                type_comment=getattr(stmt, "type_comment", None),
                                lineno=stmt.lineno,
                                col_offset=stmt.col_offset,
                                end_lineno=getattr(stmt, "end_lineno", stmt.lineno),
                                end_col_offset=getattr(stmt, "end_col_offset", stmt.col_offset),
                            )
                            ast.copy_location(sync_fn, stmt)
                            stmt = sync_fn
            new_body.append(stmt)
        tree.body = new_body

        resolved: List[Tuple[str, str, str, str]] = []
        for owner, method, r_path, fn_key in raw_routes:
            pfx = router_prefixes.get(owner, "")
            full_path = self._normalize_http_path(pfx, r_path)
            resolved.append((owner, method, full_path, fn_key))
        return resolved

    def _parse_file_recursive(self, path: Path, module: ParsedModule, is_entry: bool = False) -> None:
        real_path = path.resolve()

        # Prevent circular imports and duplicate processing
        if real_path in self._visited_files:
            return
        self._visited_files.add(real_path)

        path_str = str(real_path).lower()
        if any(ign in path_str for ign in ["__pycache__", ".git", ".pytest_cache"]):
            return

        # If it's inside venv or site-packages, make sure it's not a binary extension
        if any(v in path_str for v in [".venv", "venv", "site-packages"]):
            if self._is_binary_extension_module(real_path.parent) or self._is_binary_extension_module(real_path):
                return

        # Never add pyfasm / pyfasm64 source itself
        if ("pyfasm" in real_path.parts or "pyfasm64" in real_path.parts) and "src" in real_path.parts:
            try:
                import pyfasm
                import pyfasm64
                for pkg_mod in (pyfasm, pyfasm64):
                    pkg_dir = Path(pkg_mod.__file__).parent.resolve()
                    if pkg_dir in real_path.parents or real_path == pkg_dir:
                        return
            except Exception:
                pass

        if not real_path.exists() or not real_path.is_file():
            module.diagnostics.append(
                CompilerDiagnostic(
                    severity="error",
                    code="E1002",
                    message=f"Source file not found: {real_path}",
                    file_path=str(real_path),
                    hint="Verify the file path and imported module names.",
                )
            )
            return

        try:
            source_code = real_path.read_text(encoding="utf-8-sig").lstrip("\ufeff")
        except OSError as e:
            module.diagnostics.append(
                CompilerDiagnostic(
                    severity="error",
                    code="E1002",
                    message=f"Cannot read source file {real_path}: {e}",
                    file_path=str(real_path),
                    hint="Check file permissions and encoding (expected UTF-8).",
                )
            )
            return

        try:
            tree = ast.parse(source_code, filename=str(real_path))
        except SyntaxError as e:
            module.source_files[str(real_path)] = source_code
            module.diagnostics.append(from_syntax_error(e, file_path=str(real_path), source_text=source_code))
            return

        mod_prefix_pre = "" if is_entry else re.sub(r'[^a-zA-Z0-9_]', '_', real_path.stem)
        if mod_prefix_pre and mod_prefix_pre[0].isdigit():
            mod_prefix_pre = f"_{mod_prefix_pre}"
        pending_routes = self._prepare_fastapi_routes_in_tree(tree, mod_prefix=mod_prefix_pre)

        if not any(v in path_str for v in (".venv", "venv", "site-packages")):
            self._validate_ast_tree(tree, module, str(real_path), source_code, current_dir=real_path.parent)
        try:
            tree = preprocess_ast(tree, py_version=self.py_version, py_micro=self.py_micro)
        except Exception as e:
            module.diagnostics.append(
                CompilerDiagnostic(
                    severity="error",
                    code="E2000",
                    message=f"AST preprocessing failed for {real_path}: {e}",
                    file_path=str(real_path),
                )
            )
            return

        # 1. Collect imports, string & float constants across the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module.imports.append(node.module)
            elif isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    self.get_or_create_string(node.value)
                elif isinstance(node.value, float):
                    self.get_or_create_float(node.value)

        mod_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', real_path.stem)
        if mod_prefix and mod_prefix[0].isdigit():
            mod_prefix = f"_{mod_prefix}" 

        # 2. Discover and recursively parse imported project modules across entire AST first (topological post-order)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("pyfasm", "pyfasm64") or alias.name.startswith(("pyfasm.", "pyfasm64.")):
                        continue
                    dep = self._resolve_local_module(alias.name, real_path.parent)
                    if dep and dep != real_path:
                        self._parse_file_recursive(dep, module, is_entry=False)
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                if not mod_name and node.names:
                    for alias in node.names:
                        dep = self._resolve_local_module(alias.name, real_path.parent)
                        if dep and dep != real_path:
                            self._parse_file_recursive(dep, module, is_entry=False)
                elif mod_name:
                    if mod_name in ("pyfasm", "pyfasm64") or mod_name.startswith(("pyfasm.", "pyfasm64.")):
                        continue
                    dep = self._resolve_local_module(mod_name, real_path.parent)
                    if dep and dep != real_path:
                        self._parse_file_recursive(dep, module, is_entry=False)

                    # Register import aliases: `from mod import name as alias`
                    for alias in node.names:
                        imported_name = alias.name
                        local_alias = alias.asname
                        if local_alias and local_alias != imported_name:
                            orig_fn = module.functions.get(imported_name)
                            if not orig_fn:
                                mod_stem = mod_name.lstrip(".").split(".")[-1] if mod_name else ""
                                prefixed = f"{mod_stem}_{imported_name}" if mod_stem else imported_name
                                orig_fn = module.functions.get(prefixed)
                            if orig_fn and local_alias not in module.functions:
                                module.functions[local_alias] = orig_fn

        # 3. Extract functions and top-level code from this module
        prev_file = self._current_source_file
        self._current_source_file = str(real_path)
        try:
            self._extract_top_level_and_functions(tree, module, is_entry=is_entry, mod_prefix=mod_prefix)
        finally:
            self._current_source_file = prev_file

        # 4. Finalize any harvested FastAPI routes with resolved handler return/param types
        self._finalize_http_routes(pending_routes, module, mod_prefix_pre=mod_prefix_pre)

    @staticmethod
    def _finalize_http_routes(
        pending_routes: List[tuple],
        module: ParsedModule,
        mod_prefix_pre: str = "",
    ) -> None:
        """Resolves return_kind and integer parameter bitmasks for harvested FastAPI routes."""
        for _owner, method, full_path, fn_key in pending_routes:
            fn_sym = module.functions.get(fn_key) or module.functions.get(
                fn_key.split("_", 1)[-1]
                if mod_prefix_pre and fn_key.startswith(f"{mod_prefix_pre}_")
                else fn_key
            )
            if not fn_sym:
                continue
            r_kind = "auto"
            if fn_sym.ast_node:
                for sub_n in walk_local_scope(fn_sym.ast_node):
                    if isinstance(sub_n, ast.Return) and isinstance(sub_n.value, ast.Call):
                        c_name = (
                            sub_n.value.func.id
                            if isinstance(sub_n.value.func, ast.Name)
                            else getattr(sub_n.value.func, "attr", "")
                        )
                        if c_name == "HTMLResponse":
                            r_kind = "html"
                            break
                        if c_name == "PlainTextResponse":
                            r_kind = "text"
                            break
            if r_kind == "auto":
                rt = fn_sym.return_type
                if rt.is_dict():
                    r_kind = "dict"
                elif rt.is_list():
                    r_kind = "list"
                elif rt.is_str():
                    r_kind = "str"
                elif rt.is_float():
                    r_kind = "float"
                elif rt.is_bool():
                    r_kind = "bool"
                elif rt.is_int() and not getattr(fn_sym, "is_dynamic_return", False):
                    r_kind = "auto"
            default_texts: Dict[str, str] = {}
            fn_args = getattr(fn_sym.ast_node, "args", None)
            if isinstance(fn_args, ast.arguments):
                positional = list(getattr(fn_args, "posonlyargs", [])) + list(fn_args.args)
                pairs = list(zip(positional[len(positional) - len(fn_args.defaults):], fn_args.defaults))
                pairs += [(a, d) for a, d in zip(fn_args.kwonlyargs, fn_args.kw_defaults) if d is not None]
                for arg_node, default_node in pairs:
                    if not isinstance(default_node, ast.Constant):
                        continue
                    value = default_node.value
                    if isinstance(value, bool):
                        default_texts[arg_node.arg] = "1" if value else "0"
                    elif isinstance(value, (int, str)):
                        default_texts[arg_node.arg] = str(value)
            p_names: List[str] = []
            p_defaults: List[Optional[str]] = []
            p_int_mask = 0
            p_dict_mask = 0
            for idx, arg in enumerate(fn_sym.args):
                p_names.append(arg.name)
                p_defaults.append(default_texts.get(arg.name))
                if arg.is_dynamic:
                    continue
                if arg.var_type.is_int() or arg.var_type.is_bool():
                    p_int_mask |= (1 << idx)
                elif arg.var_type.is_dict():
                    p_dict_mask |= (1 << idx)
            module.http_routes.append(
                HttpRouteSpec(
                    method=method,
                    path=full_path,
                    handler_name=fn_sym.name,
                    return_kind=r_kind,
                    param_names=p_names,
                    param_int_mask=p_int_mask,
                    param_dict_mask=p_dict_mask,
                    param_defaults=p_defaults,
                )
            )

    def _extract_top_level_and_functions(
        self,
        tree: ast.AST,
        module: ParsedModule,
        is_entry: bool = True,
        mod_prefix: str = ""
    ) -> None:
        self.current_module = module
        prev_mod_prefix = self._current_mod_prefix
        self._current_mod_prefix = mod_prefix
        try:
            top_level_stmts = []
            func_defs: List[ast.FunctionDef] = []

            # Pass 0: pre-register module-level globals (including types) so functions defined
            # anywhere in the module see accurate global_var_types.
            def _scan_global_stmt(s: ast.stmt) -> None:
                if isinstance(s, ast.Assign):
                    val_t = self._infer_node_type(s.value, {})
                    val_kind = self._constructed_widget_kind(s.value)
                    for tgt in s.targets:
                        if isinstance(tgt, ast.Name):
                            if val_kind is not None:
                                module.global_widget_kinds[tgt.id] = val_kind
                                if mod_prefix:
                                    module.global_widget_kinds[f"{mod_prefix}_{tgt.id}"] = val_kind
                            init_val = 0
                            if isinstance(s.value, ast.Constant) and isinstance(s.value.value, int):
                                init_val = int(s.value.value)
                            module.global_vars[tgt.id] = init_val
                            self._record_global_var_type(module, tgt.id, val_t, mod_prefix)
                            if mod_prefix:
                                module.global_vars[f"{mod_prefix}_{tgt.id}"] = init_val
                        elif isinstance(tgt, (ast.Tuple, ast.List)):
                            self._record_global_unpack_types(module, tgt, val_t, mod_prefix)
                elif hasattr(ast, "TypeAlias") and isinstance(s, ast.TypeAlias):
                    aname = s.name.id if isinstance(s.name, ast.Name) else str(s.name)
                    resolved = self._resolve_annotation_type(s.value)
                    if resolved:
                        module.type_aliases[aname] = resolved
                        if mod_prefix:
                            module.type_aliases[f"{mod_prefix}_{aname}"] = resolved
                elif isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                    vname = s.target.id
                    vtype = TYPE_INT
                    if isinstance(s.annotation, ast.Name):
                        vtype = resolve_type(s.annotation.id)
                    elif isinstance(s.annotation, ast.Constant) and isinstance(s.annotation.value, str):
                        vtype = resolve_type(s.annotation.value)
                    if s.value is not None:
                        inferred = self._infer_node_type(s.value, {})
                        if vtype == TYPE_INT or self._should_upgrade_type(vtype, inferred):
                            vtype = inferred
                    init_val = 0
                    if s.value is not None and isinstance(s.value, ast.Constant) and isinstance(s.value.value, int):
                        init_val = int(s.value.value)
                    module.global_vars.setdefault(vname, init_val)
                    self._record_global_var_type(module, vname, vtype, mod_prefix)
                    if mod_prefix:
                        module.global_vars.setdefault(f"{mod_prefix}_{vname}", init_val)

            for _scan_pass in range(2):
                for stmt in tree.body:
                    if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                        _scan_global_stmt(stmt)
                    elif isinstance(stmt, ast.If) and is_entry:
                        is_mg = False
                        if isinstance(stmt.test, ast.Compare):
                            if (isinstance(stmt.test.left, ast.Name) and stmt.test.left.id == "__name__") or \
                               any(isinstance(c, ast.Name) and getattr(c, "id", None) == "__name__" for c in stmt.test.comparators):
                                is_mg = True
                        if is_mg:
                            for sub_s in stmt.body:
                                if isinstance(sub_s, (ast.Assign, ast.AnnAssign)):
                                    _scan_global_stmt(sub_s)

            owned_fn_keys: List[Tuple[ast.FunctionDef, bool, bool]] = []
            for stmt in tree.body:
                if isinstance(stmt, ast.FunctionDef):
                    func_defs.append(stmt)
                    fn = self._analyze_function(stmt)
                    added_primary = fn.name not in module.functions
                    if added_primary:
                        module.functions[fn.name] = fn
                    added_alias = False
                    if mod_prefix:
                        alias_name = f"{mod_prefix}_{fn.name}"
                        if alias_name not in module.functions:
                            module.functions[alias_name] = fn
                            added_alias = True
                    owned_fn_keys.append((stmt, added_primary, added_alias))
                    if is_entry and fn.name == "main":
                        module.main_func = fn
                elif isinstance(stmt, ast.ClassDef):
                    cls_assigns = self._analyze_class(stmt, module, mod_prefix=mod_prefix)
                    if cls_assigns:
                        top_level_stmts.extend(cls_assigns)
                elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    continue
                elif isinstance(stmt, ast.If):
                    is_main_guard = False
                    if isinstance(stmt.test, ast.Compare):
                        if (isinstance(stmt.test.left, ast.Name) and stmt.test.left.id == "__name__") or \
                           any(isinstance(c, ast.Name) and getattr(c, "id", None) == "__name__" for c in stmt.test.comparators):
                            is_main_guard = True
                    if is_main_guard:
                        if is_entry:
                            top_level_stmts.extend(stmt.body)
                        continue
                    else:
                        top_level_stmts.append(stmt)
                else:
                    top_level_stmts.append(stmt)

            if is_entry and top_level_stmts:
                calls_main = any(
                    isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name) and s.value.func.id == "main"
                    for s in top_level_stmts
                )
                if "main" not in module.functions:
                    names_used_in_scopes: Set[str] = set()
                    for scope_node in ast.walk(tree):
                        if isinstance(scope_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                            for inner in ast.walk(scope_node):
                                if isinstance(inner, ast.Name):
                                    names_used_in_scopes.add(inner.id)
                                elif isinstance(inner, ast.Global):
                                    names_used_in_scopes.update(inner.names)
                    shared_names: List[str] = []
                    for s in top_level_stmts:
                        bound_here: Set[str] = set()
                        if isinstance(s, ast.Assign):
                            for tgt in s.targets:
                                ClosureLifter._collect_target_names(tgt, bound_here)
                        elif isinstance(s, ast.AnnAssign):
                            ClosureLifter._collect_target_names(s.target, bound_here)
                        for bname in sorted(bound_here):
                            if bname in names_used_in_scopes and bname not in shared_names:
                                shared_names.append(bname)
                    if shared_names:
                        top_level_stmts = [ast.Global(names=shared_names)] + top_level_stmts

                    entry_fn_def = ast.FunctionDef(
                        name="main",
                        args=ast.arguments(posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
                        body=top_level_stmts,
                        decorator_list=[],
                        returns=None,
                        lineno=1,
                        col_offset=0
                    )
                    fn_sym = self._analyze_function(entry_fn_def)
                    module.functions["main"] = fn_sym
                    module.main_func = fn_sym
                else:
                    assigned_names = []
                    filtered_stmts = [
                        s for s in top_level_stmts
                        if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name) and s.value.func.id == "main")
                    ]
                    for s in filtered_stmts:
                        if isinstance(s, ast.Assign):
                            for tgt in s.targets:
                                if isinstance(tgt, ast.Name) and tgt.id not in assigned_names:
                                    assigned_names.append(tgt.id)
                        elif isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                            if s.target.id not in assigned_names:
                                assigned_names.append(s.target.id)
                    if assigned_names:
                        filtered_stmts = [ast.Global(names=assigned_names)] + filtered_stmts

                    entry_fn_def = ast.FunctionDef(
                        name="_pyfasm_top_level_init",
                        args=ast.arguments(posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
                        body=filtered_stmts,
                        decorator_list=[],
                        returns=None,
                        lineno=1,
                        col_offset=0
                    )
                    fn_sym = self._analyze_function(entry_fn_def)
                    module.functions["_pyfasm_top_level_init"] = fn_sym
                    if "_pyfasm_top_level_init" not in module.module_inits:
                        module.module_inits.append("_pyfasm_top_level_init")
            elif not is_entry and mod_prefix and top_level_stmts:
                init_fn_name = f"_pyfasm_modinit_{mod_prefix}"
                assigned_names = []
                for s in top_level_stmts:
                    if isinstance(s, ast.Assign):
                        for tgt in s.targets:
                            if isinstance(tgt, ast.Name) and tgt.id not in assigned_names:
                                assigned_names.append(tgt.id)
                    elif isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                        if s.target.id not in assigned_names:
                            assigned_names.append(s.target.id)
                if assigned_names:
                    top_level_stmts = [ast.Global(names=assigned_names)] + top_level_stmts

                init_fn_def = ast.FunctionDef(
                    name=init_fn_name,
                    args=ast.arguments(posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
                    body=top_level_stmts,
                    decorator_list=[],
                    returns=None,
                    lineno=1,
                    col_offset=0
                )
                fn_sym = self._analyze_function(init_fn_def)
                module.functions[init_fn_name] = fn_sym
                if init_fn_name not in module.module_inits:
                    module.module_inits.append(init_fn_name)

            # Second pass on module functions so forward-called functions and globals initialized
            # in top-level statements propagate return/variable types everywhere.
            for fn_def, added_primary, added_alias in owned_fn_keys:
                fn2 = self._analyze_function(fn_def)
                if added_primary:
                    module.functions[fn2.name] = fn2
                if added_alias and mod_prefix:
                    module.functions[f"{mod_prefix}_{fn2.name}"] = fn2
                if is_entry and fn2.name == "main":
                    module.main_func = fn2
        finally:
            self._current_mod_prefix = prev_mod_prefix

    def _resolve_annotation_type(self, ann_node: Optional[ast.AST]) -> Optional[PyFasmType]:
        if ann_node is None:
            return None
        ann_name: Optional[str] = None
        if isinstance(ann_node, ast.Name):
            ann_name = ann_node.id
        elif isinstance(ann_node, ast.Constant) and isinstance(ann_node.value, str):
            ann_name = ann_node.value
        elif isinstance(ann_node, ast.Subscript):
            val_t = self._resolve_annotation_type(ann_node.value)
            if val_t and val_t.is_list():
                elt_t = self._resolve_annotation_type(ann_node.slice)
                return ListType(element_type=elt_t)
            elif val_t and val_t.is_dict():
                if isinstance(ann_node.slice, ast.Tuple) and len(ann_node.slice.elts) >= 2:
                    kt = self._resolve_annotation_type(ann_node.slice.elts[0])
                    vt = self._resolve_annotation_type(ann_node.slice.elts[1])
                    return DictType(key_type=kt, val_type=vt)
                return TYPE_DICT
            elif val_t and val_t.is_set():
                elt_t = self._resolve_annotation_type(ann_node.slice)
                return SetType(element_type=elt_t)
            elif val_t and val_t.is_tuple():
                if isinstance(ann_node.slice, ast.Tuple):
                    elt_ts = tuple(self._resolve_annotation_type(e) or TYPE_INT for e in ann_node.slice.elts)
                    return TupleType(element_types=elt_ts)
                return TYPE_TUPLE
            return val_t or TYPE_INT
        elif isinstance(ann_node, ast.BinOp) and isinstance(ann_node.op, ast.BitOr):
            left_t = self._resolve_annotation_type(ann_node.left)
            right_t = self._resolve_annotation_type(ann_node.right)
            if left_t and left_t != TYPE_VOID:
                return left_t
            return right_t or TYPE_INT

        if not ann_name:
            return None
        mod = getattr(self, "current_module", None)
        if mod is not None:
            if hasattr(mod, "type_aliases") and ann_name in mod.type_aliases:
                return mod.type_aliases[ann_name]
            if ann_name in mod.classes:
                return InstanceType(class_name=ann_name)
        return resolve_type(ann_name)

    def _analyze_class(self, node: ast.ClassDef, module: ParsedModule, mod_prefix: str = "") -> ClassSymbol:
        cls_name = node.name
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(b.attr)

        cls_sym = ClassSymbol(name=cls_name, bases=bases, ast_node=node)

        # Inherit known field types & classes from base classes
        for base in bases:
            base_sym = module.classes.get(base)
            if base_sym:
                cls_sym.field_types.update(getattr(base_sym, "field_types", {}))
                cls_sym.field_classes.update(getattr(base_sym, "field_classes", {}))
                cls_sym.field_widget_kinds.update(getattr(base_sym, "field_widget_kinds", {}))
                cls_sym.static_methods.update(getattr(base_sym, "static_methods", set()))
                cls_sym.class_methods.update(getattr(base_sym, "class_methods", set()))

        # Discover field declarations & class attributes in class body and methods
        fields: List[str] = []
        class_assigns: List[ast.Assign] = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fname = item.target.id
                if fname not in fields:
                    fields.append(fname)
                ann_t = self._resolve_annotation_type(item.annotation)
                if ann_t is not None:
                    cls_sym.field_types[fname] = ann_t
                    if isinstance(ann_t, InstanceType):
                        cls_sym.field_classes[fname] = ann_t.class_name
                if item.value is not None:
                    val = None
                    if isinstance(item.value, ast.Constant):
                        val = item.value.value
                    cls_sym.class_attrs[fname] = val
                    global_name = f"{cls_name}_{fname}"
                    module.global_vars[global_name] = 0
                    module.global_vars[fname] = 0
                    if ann_t is None:
                        vt = self._infer_node_type(item.value, {})
                        cls_sym.field_types[fname] = vt
                        if isinstance(vt, InstanceType):
                            cls_sym.field_classes[fname] = vt.class_name
                    class_assigns.append(ast.Assign(
                        targets=[ast.Name(id=global_name, ctx=ast.Store())],
                        value=item.value
                    ))
            elif isinstance(item, ast.Assign):
                for tgt in item.targets:
                    if isinstance(tgt, ast.Name):
                        if tgt.id not in fields:
                            fields.append(tgt.id)
                        val = None
                        if isinstance(item.value, ast.Constant):
                            val = item.value.value
                        cls_sym.class_attrs[tgt.id] = val
                        global_name = f"{cls_name}_{tgt.id}"
                        module.global_vars[global_name] = 0
                        module.global_vars[tgt.id] = 0
                        vt = self._infer_node_type(item.value, {})
                        cls_sym.field_types[tgt.id] = vt
                        if isinstance(vt, InstanceType):
                            cls_sym.field_classes[tgt.id] = vt.class_name
                        class_assigns.append(ast.Assign(
                            targets=[ast.Name(id=global_name, ctx=ast.Store())],
                            value=item.value
                        ))
            elif isinstance(item, ast.FunctionDef):
                for sub in ast.walk(item):
                    if isinstance(sub, ast.Assign):
                        for tgt in sub.targets:
                            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                                if tgt.attr not in fields:
                                    fields.append(tgt.attr)
                                if isinstance(sub.value, (ast.Dict, ast.DictComp)):
                                    cls_sym.field_types[tgt.attr] = TYPE_DICT
                                elif isinstance(sub.value, (ast.List, ast.ListComp)):
                                    cls_sym.field_types[tgt.attr] = TYPE_LIST
                    elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Attribute):
                        if isinstance(sub.target.value, ast.Name) and sub.target.value.id == "self":
                            if sub.target.attr not in fields:
                                fields.append(sub.target.attr)
                            ann_t = self._resolve_annotation_type(sub.annotation)
                            if ann_t is not None:
                                cls_sym.field_types[sub.target.attr] = ann_t
                                if isinstance(ann_t, InstanceType):
                                    cls_sym.field_classes[sub.target.attr] = ann_t.class_name
        cls_sym.fields = fields
        module.classes[cls_name] = cls_sym
        if mod_prefix:
            module.classes[f"{mod_prefix}_{cls_name}"] = cls_sym

        def _register_class_methods() -> None:
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                is_prop_getter = False
                prop_setter_target = None
                is_static = False
                is_clsmethod = False
                for dec in item.decorator_list:
                    if isinstance(dec, ast.Name):
                        if dec.id == "property":
                            is_prop_getter = True
                        elif dec.id == "staticmethod":
                            is_static = True
                        elif dec.id == "classmethod":
                            is_clsmethod = True
                    elif isinstance(dec, ast.Attribute) and dec.attr == "setter" and isinstance(dec.value, ast.Name):
                        prop_setter_target = dec.value.id

                m_fn = self._analyze_function(
                    item,
                    owner_class=cls_name,
                    is_static=is_static,
                    is_classmethod=is_clsmethod,
                )
                m_fn.class_name = cls_name

                if is_static:
                    cls_sym.static_methods.add(item.name)
                if is_clsmethod:
                    cls_sym.class_methods.add(item.name)
                    if m_fn.return_type == TYPE_VOID or m_fn.return_type == TYPE_INT:
                        for sub in walk_local_scope(item):
                            if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Call):
                                if isinstance(sub.value.func, ast.Name) and sub.value.func.id in ("cls", cls_name):
                                    m_fn.return_type = InstanceType(class_name=cls_name)
                                    break

                # Record exact inferred types for `self.<field> = <expr>` assignments
                for sub in walk_local_scope(item):
                    if isinstance(sub, ast.Assign):
                        for tgt in sub.targets:
                            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                                ft = self._infer_node_type(sub.value, m_fn.local_vars)
                                cur_ft = cls_sym.field_types.get(tgt.attr)
                                if cur_ft is None or self._should_upgrade_type(cur_ft, ft):
                                    cls_sym.field_types[tgt.attr] = ft
                                if isinstance(ft, InstanceType):
                                    cls_sym.field_classes[tgt.attr] = ft.class_name
                                field_kind = self._constructed_widget_kind(sub.value)
                                if field_kind is not None:
                                    cls_sym.field_widget_kinds[tgt.attr] = field_kind
                    elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Attribute):
                        if isinstance(sub.target.value, ast.Name) and sub.target.value.id == "self" and sub.value is not None:
                            ft = self._infer_node_type(sub.value, m_fn.local_vars)
                            cur_ft = cls_sym.field_types.get(sub.target.attr)
                            if cur_ft is None or self._should_upgrade_type(cur_ft, ft):
                                cls_sym.field_types[sub.target.attr] = ft
                            if isinstance(ft, InstanceType):
                                cls_sym.field_classes[sub.target.attr] = ft.class_name

                if is_prop_getter:
                    prop_name = item.name
                    getter_name = f"{cls_name}_get_{prop_name}"
                    m_fn.name = getter_name
                    cls_sym.methods[getter_name] = m_fn
                    module.functions[getter_name] = m_fn
                    module.functions[f"{cls_name}_{prop_name}"] = m_fn
                    if prop_name not in cls_sym.properties:
                        cls_sym.properties[prop_name] = PropertySymbol(name=prop_name)
                    cls_sym.properties[prop_name].getter_name = getter_name
                elif prop_setter_target:
                    prop_name = prop_setter_target
                    setter_name = f"{cls_name}_set_{prop_name}"
                    m_fn.name = setter_name
                    cls_sym.methods[setter_name] = m_fn
                    module.functions[setter_name] = m_fn
                    if prop_name not in cls_sym.properties:
                        cls_sym.properties[prop_name] = PropertySymbol(name=prop_name)
                    cls_sym.properties[prop_name].setter_name = setter_name
                else:
                    method_name = f"{cls_name}_{item.name}"
                    m_fn.name = method_name  # Ensure class method has unique namespaced symbol name
                    cls_sym.methods[item.name] = m_fn
                    module.functions[method_name] = m_fn
                    if mod_prefix:
                        pref_name = f"{mod_prefix}_{cls_name}_{item.name}"
                        module.functions[pref_name] = m_fn

        _register_class_methods()
        _register_class_methods()

        # Register constructor function symbol
        init_fn = cls_sym.methods.get("__init__")
        if not init_fn:
            # Check base classes for inherited __init__
            for base in cls_sym.bases:
                base_sym = module.classes.get(base)
                if base_sym and "__init__" in base_sym.methods:
                    init_fn = base_sym.methods["__init__"]
                    break

        if not init_fn and fields:
            synth_args = [ast.arg(arg="self", annotation=None, type_comment=None)] + [
                ast.arg(arg=f, annotation=None, type_comment=None) for f in fields
            ]
            assign_stmts = [
                ast.Assign(
                    targets=[ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=f, ctx=ast.Store())],
                    value=ast.Name(id=f, ctx=ast.Load())
                )
                for f in fields
            ]
            synth_node = ast.FunctionDef(
                name="__init__",
                args=ast.arguments(posonlyargs=[], args=synth_args, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
                body=assign_stmts or [ast.Pass()],
                decorator_list=[],
                returns=None,
                lineno=getattr(node, "lineno", 1),
                col_offset=0
            )
            init_fn = self._analyze_function(synth_node, owner_class=cls_name)
            init_fn.class_name = cls_name
            method_name = f"{cls_name}___init__"
            init_fn.name = method_name
            cls_sym.methods["__init__"] = init_fn
            cls_sym.methods[method_name] = init_fn
            module.functions[method_name] = init_fn

        ctor_args: List[VariableSymbol] = []
        if init_fn and len(init_fn.args) > 1:
            for idx, a in enumerate(init_fn.args[1:]):
                ctor_args.append(VariableSymbol(
                    name=a.name,
                    var_type=a.var_type,
                    stack_offset=(idx + 1) * 8,
                    is_arg=True,
                    arg_index=idx
                ))

        ctor_sym = FunctionSymbol(
            name=cls_name,
            args=ctor_args,
            defaults=list(getattr(init_fn, "defaults", [])) if init_fn else [],
            return_type=InstanceType(class_name=cls_name),
            stack_size=64
        )
        module.functions[cls_name] = ctor_sym
        if mod_prefix:
            module.functions[f"{mod_prefix}_{cls_name}"] = ctor_sym

        return class_assigns

    def _record_global_var_type(
        self,
        module: Optional[ParsedModule],
        vname: str,
        new_type: Optional[PyFasmType],
        mod_prefix: str = "",
    ) -> None:
        if module is None or new_type is None:
            return
        cur = module.global_var_types.get(vname)
        if cur is None or self._should_upgrade_type(cur, new_type):
            module.global_var_types[vname] = new_type
        if mod_prefix:
            mname = f"{mod_prefix}_{vname}"
            cur_m = module.global_var_types.get(mname)
            if cur_m is None or self._should_upgrade_type(cur_m, new_type):
                module.global_var_types[mname] = new_type

    def _unpack_target_types(
        self,
        target: ast.AST,
        rhs_type: PyFasmType,
    ) -> List[Tuple[str, PyFasmType]]:
        """Compute `(var_name, inferred_type)` pairs for simple and tuple/list unpacking targets."""
        if isinstance(target, ast.Name):
            return [(target.id, rhs_type)]
        if not isinstance(target, (ast.Tuple, ast.List)):
            return []

        fallback_elt = TYPE_INT
        if rhs_type.is_str():
            fallback_elt = TYPE_STR
        elif rhs_type.is_list() and getattr(rhs_type, "element_type", None):
            fallback_elt = rhs_type.element_type
        elif rhs_type.is_tuple():
            if getattr(rhs_type, "element_type", None):
                fallback_elt = rhs_type.element_type
            elif getattr(rhs_type, "element_types", None):
                fallback_elt = self._merge_element_types(list(rhs_type.element_types)) or TYPE_INT

        pos_types = getattr(rhs_type, "element_types", None) if rhs_type.is_tuple() else None
        out: List[Tuple[str, PyFasmType]] = []
        for idx, elt in enumerate(target.elts):
            if isinstance(elt, ast.Starred) and isinstance(elt.value, ast.Name):
                star_elt = fallback_elt if fallback_elt != TYPE_INT else None
                out.append((elt.value.id, ListType(element_type=star_elt) if star_elt else TYPE_LIST))
                continue
            elt_t = pos_types[idx] if (pos_types is not None and idx < len(pos_types)) else fallback_elt
            if isinstance(elt, ast.Name):
                out.append((elt.id, elt_t))
            elif isinstance(elt, (ast.Tuple, ast.List)):
                out.extend(self._unpack_target_types(elt, elt_t))
        return out

    def _record_global_unpack_types(
        self,
        module: ParsedModule,
        target: ast.AST,
        rhs_type: PyFasmType,
        mod_prefix: str = "",
    ) -> None:
        for vname, t_type in self._unpack_target_types(target, rhs_type):
            module.global_vars.setdefault(vname, 0)
            self._record_global_var_type(module, vname, t_type, mod_prefix)
            if mod_prefix:
                module.global_vars.setdefault(f"{mod_prefix}_{vname}", 0)

    def _merge_element_types(self, types: List[Optional[PyFasmType]]) -> Optional[PyFasmType]:
        """Return a common element type if all elements share a compatible shape, else None."""
        concrete = [t for t in types if t is not None]
        if not concrete:
            return None
        first = concrete[0]
        if all(t == first for t in concrete):
            return first
        # Numeric tower: mixed int/float sequences are stored as doubles.
        if all(t in (TYPE_INT, TYPE_FLOAT) for t in concrete):
            return TYPE_FLOAT
        if all(t.is_list() for t in concrete):
            inner = [getattr(t, "element_type", None) for t in concrete if getattr(t, "element_type", None) is not None]
            if inner:
                merged_inner = self._merge_element_types(inner)
                if merged_inner is not None:
                    return ListType(element_type=merged_inner)
            return TYPE_LIST
        if all(t.is_dict() for t in concrete):
            return TYPE_DICT
        if all(t.is_set() for t in concrete):
            return TYPE_SET
        if all(t.is_tuple() for t in concrete):
            return TYPE_TUPLE
        if all(isinstance(t, InstanceType) for t in concrete):
            cls_names = [t.class_name for t in concrete]
            if len(set(cls_names)) == 1:
                return first
            mod = getattr(self, "current_module", None)
            if mod is not None:
                def _ancestors(cname: str) -> List[str]:
                    order: List[str] = []
                    seen: Set[str] = set()
                    q = [cname]
                    while q:
                        cur = q.pop(0)
                        if cur in seen:
                            continue
                        seen.add(cur)
                        order.append(cur)
                        csym = mod.classes.get(cur)
                        if csym:
                            q.extend(csym.bases)
                    return order

                base_anc = _ancestors(cls_names[0])
                other_sets = [set(_ancestors(cn)) for cn in cls_names[1:]]
                for cand in base_anc:
                    if all(cand in s for s in other_sets):
                        return InstanceType(class_name=cand)
            return TYPE_PTR
        return None

    def _module_uses_gui(self) -> bool:
        mod = getattr(self, "current_module", None)
        if mod is None:
            return False
        return any(imp.split(".")[0].lower() in GUI_LIBRARY_ROOTS for imp in mod.imports)

    def _constructed_widget_kind(self, expr: Optional[ast.AST]) -> Optional[str]:
        """Widget kind created by ``expr`` when it is a GUI constructor call, else None."""
        kind = gui_widget_kind(expr)
        if kind is None or not self._module_uses_gui():
            return None
        mod = self.current_module
        func = expr.func
        if isinstance(func, ast.Name) and (func.id in mod.classes or func.id in mod.functions):
            return None
        return kind

    def _receiver_widget_kind(self, expr: Optional[ast.AST], local_vars: Dict[str, VariableSymbol]) -> Optional[str]:
        """Widget kind of a receiver expression: a local, a global or ``self.<field>``."""
        mod = getattr(self, "current_module", None)
        if isinstance(expr, ast.Name):
            sym = local_vars.get(expr.id)
            if sym is not None:
                return sym.widget_kind
            if mod is not None:
                prefix = getattr(self, "_current_mod_prefix", "")
                if prefix and f"{prefix}_{expr.id}" in mod.global_widget_kinds:
                    return mod.global_widget_kinds[f"{prefix}_{expr.id}"]
                return mod.global_widget_kinds.get(expr.id)
            return None
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and mod is not None:
            owner = local_vars.get(expr.value.id)
            owner_t = owner.var_type if owner is not None else None
            cls_name = getattr(owner_t, "class_name", None) if isinstance(owner_t, InstanceType) else None
            seen: Set[str] = set()
            while cls_name and cls_name not in seen and cls_name in mod.classes:
                seen.add(cls_name)
                cls_sym = mod.classes[cls_name]
                if expr.attr in cls_sym.field_widget_kinds:
                    return cls_sym.field_widget_kinds[expr.attr]
                cls_name = cls_sym.bases[0] if cls_sym.bases else None
        return None

    @staticmethod
    def _should_upgrade_type(cur: Optional[PyFasmType], new: Optional[PyFasmType]) -> bool:
        if new is None:
            return False
        if cur is None:
            return True
        if cur == new:
            return False
        if cur == TYPE_INT and new != TYPE_INT:
            return True
        if cur.is_list() and new.is_list():
            return getattr(cur, "element_type", None) is None and getattr(new, "element_type", None) is not None
        if cur.is_dict() and new.is_dict():
            return (
                (cur.key_type is None and new.key_type is not None)
                or (cur.val_type is None and new.val_type is not None)
            )
        if cur.is_set() and new.is_set():
            return cur.element_type is None and new.element_type is not None
        if cur.is_tuple() and new.is_tuple():
            return (
                (cur.element_type is None and new.element_type is not None)
                or (cur.element_types is None and new.element_types is not None)
            )
        return False

    def _infer_map_element_type(self, call_node: ast.Call) -> Optional[PyFasmType]:
        """Infer element type yielded by map(func, iterable) without recursing into iter_node."""
        if len(call_node.args) >= 2 and isinstance(call_node.args[0], ast.Name):
            fn_name = call_node.args[0].id
            if fn_name == "str":
                return TYPE_STR
            if fn_name == "float":
                return TYPE_FLOAT
            if fn_name == "bool":
                return TYPE_BOOL
            if fn_name == "int":
                return TYPE_INT
            mod = getattr(self, "current_module", None)
            if mod is not None and fn_name in mod.functions:
                rt = mod.functions[fn_name].return_type
                return rt if rt != TYPE_VOID else None
        return None

    def _is_dynamic_expr(self, expr: Optional[ast.AST], local_vars: Dict[str, VariableSymbol]) -> bool:
        """True when expr has statically ambiguous value representation (dynamic param or untyped container element)."""
        if expr is None:
            return False
        if isinstance(expr, ast.Name):
            sym = local_vars.get(expr.id)
            return bool(sym and sym.is_dynamic and sym.var_type == TYPE_INT)
        if isinstance(expr, ast.Subscript) and not isinstance(expr.slice, ast.Slice):
            ct = self._infer_node_type(expr.value, local_vars)
            if ct.is_list() and getattr(ct, "element_type", None) is None:
                return True
            if ct.is_tuple() and getattr(ct, "element_type", None) is None and getattr(ct, "element_types", None) is None:
                return True
            if ct.is_dict() and getattr(ct, "val_type", None) is None:
                return True
        if isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Attribute) and expr.func.attr in ("pop", "get"):
                ct = self._infer_node_type(expr.func.value, local_vars)
                if ct.is_list() and getattr(ct, "element_type", None) is None:
                    return True
                if ct.is_dict() and getattr(ct, "val_type", None) is None and len(expr.args) < 2:
                    return True
            elif isinstance(expr.func, ast.Name):
                if expr.func.id == "eval":
                    return True
                mod = getattr(self, "current_module", None)
                if expr.func.id in local_vars and self._infer_node_type(expr, local_vars) == TYPE_INT:
                    return True
                if mod is not None and expr.func.id in mod.functions:
                    if getattr(mod.functions[expr.func.id], "is_dynamic_return", False):
                        return True
            elif isinstance(expr.func, ast.Subscript) and self._infer_node_type(expr, local_vars) == TYPE_INT:
                return True
        return False

    def _infer_iter_element_type(self, iter_node: Optional[ast.AST], local_vars: Dict[str, VariableSymbol]) -> PyFasmType:
        """Infer the yielded item type when iterating over `iter_node` in a loop or comprehension."""
        if iter_node is None:
            return TYPE_INT
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Name):
                fid = iter_node.func.id
                if fid == "range":
                    return TYPE_INT
                if fid == "enumerate":
                    inner = self._infer_iter_element_type(iter_node.args[0], local_vars) if iter_node.args else TYPE_INT
                    return TupleType(element_type=None, element_types=(TYPE_INT, inner))
                if fid == "zip":
                    if iter_node.args:
                        elt_ts = tuple(self._infer_iter_element_type(a, local_vars) for a in iter_node.args)
                        return TupleType(element_type=self._merge_element_types(list(elt_ts)), element_types=elt_ts)
                    return TYPE_TUPLE
                if fid in ("sorted", "list", "reversed", "tuple", "set") and iter_node.args:
                    return self._infer_iter_element_type(iter_node.args[0], local_vars)
                if fid == "map":
                    return self._infer_map_element_type(iter_node) or TYPE_INT
            elif isinstance(iter_node.func, ast.Attribute):
                attr = iter_node.func.attr
                recv_t = self._infer_node_type(iter_node.func.value, local_vars)
                if attr in ("split", "splitlines"):
                    return TYPE_STR
                if attr == "keys":
                    return getattr(recv_t, "key_type", None) or TYPE_INT
                if attr == "values":
                    return getattr(recv_t, "val_type", None) or TYPE_INT
                if attr == "items":
                    kt = getattr(recv_t, "key_type", None) or TYPE_INT
                    vt = getattr(recv_t, "val_type", None) or TYPE_INT
                    return TupleType(element_type=self._merge_element_types([kt, vt]), element_types=(kt, vt))

        iter_t = self._infer_node_type(iter_node, local_vars)
        if iter_t.is_str():
            return TYPE_STR
        if iter_t.is_list() or iter_t.is_set():
            return getattr(iter_t, "element_type", None) or TYPE_INT
        if iter_t.is_tuple():
            if getattr(iter_t, "element_type", None):
                return iter_t.element_type
            if getattr(iter_t, "element_types", None):
                return self._merge_element_types(list(iter_t.element_types)) or TYPE_INT
            return TYPE_INT
        if iter_t.is_dict():
            return getattr(iter_t, "key_type", None) or TYPE_INT
        if isinstance(iter_t, InstanceType):
            mod = getattr(self, "current_module", None)
            if mod is not None:
                seen_cls: Set[str] = set()
                q = [iter_t.class_name]
                while q:
                    cn = q.pop(0)
                    if cn in seen_cls:
                        continue
                    seen_cls.add(cn)
                    cs = mod.classes.get(cn)
                    if cs:
                        nm = cs.methods.get("__next__")
                        if nm and nm.return_type != TYPE_VOID:
                            return nm.return_type
                        im = cs.methods.get("__iter__")
                        if im and isinstance(im.return_type, InstanceType) and im.return_type.class_name != cn:
                            q.append(im.return_type.class_name)
                        q.extend(cs.bases)
        return TYPE_INT

    def _infer_node_type(self, expr: Optional[ast.AST], local_vars: Dict[str, VariableSymbol]) -> PyFasmType:
        """Infers the PyFasmType of an AST expression using local type propagation (inspired by Shedskin & Mypyc)."""
        if expr is None:
            return TYPE_INT
        if hasattr(ast, "Index") and isinstance(expr, ast.Index):
            return self._infer_node_type(expr.value, local_vars)

        if isinstance(expr, ast.Constant):
            if isinstance(expr.value, bool):
                return TYPE_BOOL
            elif isinstance(expr.value, int):
                return TYPE_INT
            elif isinstance(expr.value, float):
                return TYPE_FLOAT
            elif isinstance(expr.value, str):
                return TYPE_STR
            return TYPE_INT

        elif isinstance(expr, ast.Name):
            if expr.id in local_vars:
                return local_vars[expr.id].var_type
            if expr.id in ("True", "False"):
                return TYPE_BOOL
            mod = getattr(self, "current_module", None)
            if mod is not None:
                if self._current_mod_prefix:
                    prefixed_key = f"{self._current_mod_prefix}_{expr.id}"
                    if prefixed_key in mod.global_var_types:
                        return mod.global_var_types[prefixed_key]
                if expr.id in mod.global_var_types:
                    return mod.global_var_types[expr.id]
            return TYPE_INT

        elif isinstance(expr, ast.List):
            elem_t = self._merge_element_types([self._infer_node_type(e, local_vars) for e in expr.elts]) if expr.elts else None
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST

        elif isinstance(expr, ast.ListComp):
            comp_vars = dict(local_vars)
            for gen in expr.generators:
                elt_t = self._infer_iter_element_type(gen.iter, comp_vars)
                for vname, v_t in self._unpack_target_types(gen.target, elt_t):
                    comp_vars[vname] = VariableSymbol(name=vname, var_type=v_t, stack_offset=0)
            elem_t = self._infer_node_type(expr.elt, comp_vars)
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST

        elif isinstance(expr, ast.Dict):
            kt = self._merge_element_types([self._infer_node_type(k, local_vars) for k in expr.keys if k is not None])
            vt = self._merge_element_types([self._infer_node_type(v, local_vars) for v in expr.values])
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT

        elif isinstance(expr, ast.DictComp):
            comp_vars = dict(local_vars)
            for gen in expr.generators:
                elt_t = self._infer_iter_element_type(gen.iter, comp_vars)
                for vname, v_t in self._unpack_target_types(gen.target, elt_t):
                    comp_vars[vname] = VariableSymbol(name=vname, var_type=v_t, stack_offset=0)
            kt = self._infer_node_type(expr.key, comp_vars)
            vt = self._infer_node_type(expr.value, comp_vars)
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT

        elif isinstance(expr, ast.Set):
            elem_t = self._merge_element_types([self._infer_node_type(e, local_vars) for e in expr.elts]) if expr.elts else None
            return SetType(element_type=elem_t) if elem_t else TYPE_SET

        elif isinstance(expr, ast.SetComp):
            comp_vars = dict(local_vars)
            for gen in expr.generators:
                elt_t = self._infer_iter_element_type(gen.iter, comp_vars)
                for vname, v_t in self._unpack_target_types(gen.target, elt_t):
                    comp_vars[vname] = VariableSymbol(name=vname, var_type=v_t, stack_offset=0)
            elem_t = self._infer_node_type(expr.elt, comp_vars)
            return SetType(element_type=elem_t) if elem_t else TYPE_SET

        elif isinstance(expr, ast.Tuple):
            if not expr.elts:
                return TYPE_TUPLE
            elt_ts = tuple(self._infer_node_type(e, local_vars) for e in expr.elts)
            elem_t = self._merge_element_types(list(elt_ts))
            return TupleType(element_type=elem_t, element_types=elt_ts)

        elif isinstance(expr, ast.JoinedStr):
            return TYPE_STR

        elif isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.MatMult):
                return ListType(element_type=TYPE_LIST)
            left_t = self._infer_node_type(expr.left, local_vars)
            right_t = self._infer_node_type(expr.right, local_vars)
            mod = getattr(self, "current_module", None)
            if mod is not None:
                op_map = {
                    ast.Add: ("__add__", "__radd__"),
                    ast.Sub: ("__sub__", "__rsub__"),
                    ast.Mult: ("__mul__", "__rmul__"),
                    ast.FloorDiv: ("__floordiv__", "__rfloordiv__"),
                    ast.Div: ("__truediv__", "__rtruediv__"),
                    ast.Mod: ("__mod__", "__rmod__"),
                    ast.Pow: ("__pow__", "__rpow__"),
                    ast.BitAnd: ("__and__", None),
                    ast.BitOr: ("__or__", None),
                    ast.BitXor: ("__xor__", None),
                    ast.LShift: ("__lshift__", None),
                    ast.RShift: ("__rshift__", None),
                }
                if type(expr.op) in op_map:
                    fwd_d, rev_d = op_map[type(expr.op)]
                    if isinstance(left_t, InstanceType):
                        cs = mod.classes.get(left_t.class_name)
                        if cs and fwd_d in cs.methods and cs.methods[fwd_d].return_type != TYPE_VOID:
                            return cs.methods[fwd_d].return_type
                    if rev_d and isinstance(right_t, InstanceType):
                        cs = mod.classes.get(right_t.class_name)
                        if cs and rev_d in cs.methods and cs.methods[rev_d].return_type != TYPE_VOID:
                            return cs.methods[rev_d].return_type
            if left_t.is_complex() or right_t.is_complex():
                return TYPE_COMPLEX
            if isinstance(expr.op, ast.Mult):
                if left_t.is_list() and getattr(left_t, "element_type", None) != TYPE_FLOAT:
                    return left_t
                if right_t.is_list() and getattr(right_t, "element_type", None) != TYPE_FLOAT:
                    return right_t
                if left_t.is_tuple():
                    return left_t
                if right_t.is_tuple():
                    return right_t
            if left_t.is_list() or right_t.is_list():
                lt_elem = getattr(left_t, "element_type", None) if left_t.is_list() else (TYPE_FLOAT if left_t.is_float() else None)
                rt_elem = getattr(right_t, "element_type", None) if right_t.is_list() else (TYPE_FLOAT if right_t.is_float() else None)
                merged = self._merge_element_types([t for t in (lt_elem, rt_elem) if t is not None])
                return ListType(element_type=merged) if merged else TYPE_LIST
            if left_t.is_float() or right_t.is_float():
                return TYPE_FLOAT
            if left_t.is_str() or right_t.is_str():
                return TYPE_STR
            if left_t.is_tuple() or right_t.is_tuple():
                return TYPE_TUPLE
            if (
                (isinstance(expr.op, ast.Div) or (isinstance(expr.op, ast.Pow) and is_negative_number_literal(expr.right)))
                and (left_t.is_int() or left_t.is_bool())
                and (right_t.is_int() or right_t.is_bool())
            ):
                return TYPE_FLOAT
            return TYPE_INT

        elif isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.Not):
                return TYPE_BOOL
            return self._infer_node_type(expr.operand, local_vars)

        elif isinstance(expr, ast.IfExp):
            bt = self._infer_node_type(expr.body, local_vars)
            ot = self._infer_node_type(expr.orelse, local_vars)
            if bt == ot:
                return bt
            merged = self._merge_element_types([bt, ot])
            return merged if merged is not None else TYPE_INT

        elif isinstance(expr, ast.NamedExpr):
            return self._infer_node_type(expr.value, local_vars)

        elif isinstance(expr, (ast.Compare, ast.BoolOp)):
            return TYPE_BOOL

        elif isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                fid = expr.func.id
                if fid == "_pyfasm_closure_get":
                    caps = self._closure_cap_types.get(self._current_func_name)
                    if caps and len(expr.args) >= 2 and isinstance(expr.args[1], ast.Constant) and isinstance(expr.args[1].value, int):
                        cidx = expr.args[1].value
                        if 0 <= cidx < len(caps):
                            return caps[cidx]
                    return TYPE_INT
                if fid == "_pyfasm_closure_new":
                    if expr.args and isinstance(expr.args[0], ast.Name):
                        self._closure_cap_types[expr.args[0].id] = [
                            self._infer_node_type(a, local_vars) for a in expr.args[1:]
                        ]
                    return TYPE_PTR
                if fid == "_pyfasm_cell_new":
                    return TYPE_PTR
                if fid == "_pyfasm_cell_get":
                    mod = getattr(self, "current_module", None)
                    if mod is not None and expr.args and isinstance(expr.args[0], ast.Name):
                        return mod.cell_val_types.get(expr.args[0].id, TYPE_INT)
                    return TYPE_INT
                if fid == "_pyfasm_cell_set":
                    if len(expr.args) >= 2:
                        return self._infer_node_type(expr.args[1], local_vars)
                    return TYPE_INT
                if fid in ("str", "repr", "chr", "input", "hex", "bin", "oct", "file_read", "get_simd_isa"):
                    return TYPE_STR
                elif fid in ("alloc_memory", "malloc", "VirtualAlloc", "calloc"):
                    return TYPE_PTR
                elif fid in ("int", "ord", "len", "hash", "open", "file_open", "bit_length"):
                    return TYPE_INT
                elif fid in ("float", "pow"):
                    return TYPE_FLOAT
                elif fid == "complex":
                    return TYPE_COMPLEX
                elif fid == "round":
                    return TYPE_FLOAT if len(expr.args) >= 2 else TYPE_INT
                elif fid == "abs":
                    if expr.args:
                        a0_t = self._infer_node_type(expr.args[0], local_vars)
                        mod = getattr(self, "current_module", None)
                        if isinstance(a0_t, InstanceType) and mod is not None:
                            cs = mod.classes.get(a0_t.class_name)
                            if cs and "__abs__" in cs.methods and cs.methods["__abs__"].return_type != TYPE_VOID:
                                return cs.methods["__abs__"].return_type
                        if a0_t.is_complex() or a0_t.is_float():
                            return TYPE_FLOAT
                    return TYPE_INT
                elif fid in ("min", "max"):
                    if len(expr.args) >= 2 and any(self._infer_node_type(a, local_vars).is_float() for a in expr.args):
                        return TYPE_FLOAT
                    if len(expr.args) == 1:
                        a0_t = self._infer_node_type(expr.args[0], local_vars)
                        if getattr(a0_t, "element_type", None) and a0_t.element_type.is_float():
                            return TYPE_FLOAT
                    return TYPE_INT
                elif fid in ("bool", "isinstance", "issubclass", "hasattr", "isdigit", "isascii"):
                    return TYPE_BOOL
                elif fid == "getattr" and len(expr.args) >= 2:
                    if isinstance(expr.args[1], ast.Constant) and isinstance(expr.args[1].value, str):
                        ocls = None
                        o_t = self._infer_node_type(expr.args[0], local_vars)
                        if isinstance(o_t, InstanceType):
                            ocls = o_t.class_name
                        mod_ref = getattr(self, "current_module", None)
                        if ocls and mod_ref and ocls in mod_ref.classes:
                            cs = mod_ref.classes[ocls]
                            if expr.args[1].value in getattr(cs, "field_types", {}):
                                return cs.field_types[expr.args[1].value]
                    if len(expr.args) >= 3:
                        return self._infer_node_type(expr.args[2], local_vars)
                    return TYPE_INT
                elif fid == "range":
                    return ListType(element_type=TYPE_INT)
                elif fid in ("list", "sorted", "reversed"):
                    if expr.args:
                        a0 = expr.args[0]
                        a0_t = self._infer_node_type(a0, local_vars)
                        inner_t: Optional[PyFasmType] = None
                        if a0_t.is_str():
                            inner_t = TYPE_STR
                        elif a0_t.is_list() or a0_t.is_set():
                            inner_t = getattr(a0_t, "element_type", None)
                        elif a0_t.is_tuple():
                            inner_t = getattr(a0_t, "element_type", None)
                            if inner_t is None and getattr(a0_t, "element_types", None):
                                inner_t = self._merge_element_types(list(a0_t.element_types))
                        elif a0_t.is_dict():
                            inner_t = getattr(a0_t, "key_type", None)
                        elif isinstance(a0, ast.Call) and isinstance(a0.func, ast.Name) and a0.func.id in ("range", "enumerate", "zip", "map"):
                            inner_t = self._infer_iter_element_type(a0, local_vars)
                        elif isinstance(a0, ast.Call) and isinstance(a0.func, ast.Attribute) and a0.func.attr in ("keys", "values", "items", "split", "splitlines"):
                            inner_t = self._infer_iter_element_type(a0, local_vars)
                        if inner_t is not None:
                            return ListType(element_type=inner_t)
                    return TYPE_LIST
                elif fid in ("enumerate",):
                    inner = self._infer_iter_element_type(expr.args[0], local_vars) if expr.args else TYPE_INT
                    return ListType(element_type=TupleType(element_types=(TYPE_INT, inner)))
                elif fid in ("map", "filter", "zip", "chain", "accumulate", "matmul", "zeros", "ones", "array", "asarray", "arange", "pairwise"):
                    if fid in ("matmul",):
                        return ListType(element_type=TYPE_LIST)
                    if fid == "map":
                        map_elt = self._infer_map_element_type(expr)
                        return ListType(element_type=map_elt) if map_elt else TYPE_LIST
                    return TYPE_LIST
                elif fid in ("dict",):
                    return TYPE_DICT
                elif fid in ("set",):
                    if expr.args:
                        a0 = expr.args[0]
                        a0_t = self._infer_node_type(a0, local_vars)
                        if a0_t.is_str():
                            return SetType(element_type=TYPE_STR)
                        if (a0_t.is_list() or a0_t.is_set() or a0_t.is_tuple()) and getattr(a0_t, "element_type", None):
                            return SetType(element_type=a0_t.element_type)
                    return TYPE_SET
                elif fid in ("tuple",):
                    if expr.args:
                        a0 = expr.args[0]
                        a0_t = self._infer_node_type(a0, local_vars)
                        if a0_t.is_str():
                            return TupleType(element_type=TYPE_STR)
                        if a0_t.is_list() or a0_t.is_set() or a0_t.is_tuple():
                            return TupleType(
                                element_type=getattr(a0_t, "element_type", None),
                                element_types=getattr(a0_t, "element_types", None),
                            )
                    return TYPE_TUPLE
                mod = getattr(self, "current_module", None)
                if mod is not None and fid in mod.functions:
                    rt = mod.functions[fid].return_type
                    if rt != TYPE_VOID:
                        return rt
                if mod is not None and fid in local_vars and getattr(local_vars[fid], "fn_alias", None):
                    al = local_vars[fid].fn_alias
                    if al in mod.functions and mod.functions[al].return_type != TYPE_VOID:
                        return mod.functions[al].return_type
                if fid in local_vars and isinstance(local_vars[fid].var_type, InstanceType) and mod is not None:
                    cls_t = local_vars[fid].var_type
                    seen_c: Set[str] = set()
                    cq = [cls_t.class_name]
                    while cq:
                        cn = cq.pop(0)
                        if cn in seen_c:
                            continue
                        seen_c.add(cn)
                        cs = mod.classes.get(cn)
                        if cs:
                            cm = cs.methods.get("__call__")
                            if cm and cm.return_type != TYPE_VOID:
                                return cm.return_type
                            cq.extend(cs.bases)
            elif isinstance(expr.func, ast.Attribute):
                attr = expr.func.attr
                if attr == "Group":
                    return ListType(element_type=TYPE_PTR)
                if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "random":
                    return TYPE_FLOAT if attr in ("random", "uniform") else TYPE_INT
                mod = getattr(self, "current_module", None)
                gui_t = gui_method_result_type(
                    self._receiver_widget_kind(expr.func.value, local_vars), attr, len(expr.args)
                )
                if gui_t is not None:
                    return gui_t
                if mod is not None and isinstance(expr.func.value, ast.Name) and expr.func.value.id in mod.classes:
                    cname = expr.func.value.id
                    cq = [cname]
                    seen_c = set()
                    while cq:
                        cn = cq.pop(0)
                        if cn in seen_c:
                            continue
                        seen_c.add(cn)
                        cs = mod.classes.get(cn)
                        if cs:
                            if attr in cs.class_methods:
                                mfn = cs.methods.get(attr)
                                if mfn and isinstance(mfn.return_type, InstanceType):
                                    return InstanceType(class_name=cname)
                            if attr in cs.methods and cs.methods[attr].return_type != TYPE_VOID:
                                return cs.methods[attr].return_type
                            cq.extend(cs.bases)
                if attr in ("split", "splitlines"):
                    return ListType(element_type=TYPE_STR)
                elif attr in ("read", "strip", "lstrip", "rstrip", "replace", "lower", "upper", "capitalize", "title", "format", "choice", "get_simd_isa", "join", "removeprefix", "removesuffix"):
                    return TYPE_STR
                elif attr == "keys":
                    recv_t = self._infer_node_type(expr.func.value, local_vars)
                    kt = getattr(recv_t, "key_type", None) if recv_t.is_dict() else None
                    return ListType(element_type=kt) if kt else TYPE_LIST
                elif attr == "values":
                    recv_t = self._infer_node_type(expr.func.value, local_vars)
                    vt = getattr(recv_t, "val_type", None) if recv_t.is_dict() else None
                    return ListType(element_type=vt) if vt else TYPE_LIST
                elif attr == "items":
                    recv_t = self._infer_node_type(expr.func.value, local_vars)
                    if recv_t.is_dict():
                        kt = getattr(recv_t, "key_type", None) or TYPE_INT
                        vt = getattr(recv_t, "val_type", None) or TYPE_INT
                        return ListType(element_type=TupleType(element_types=(kt, vt)))
                    return TYPE_LIST
                elif attr == "copy":
                    recv_t = self._infer_node_type(expr.func.value, local_vars)
                    if recv_t.is_list() or recv_t.is_dict() or recv_t.is_set():
                        return recv_t
                elif attr in ("linspace", "empty", "arange", "zeros", "ones", "sign", "array", "asarray", "asanyarray"):
                    if attr == "sign" and expr.args and not self._infer_node_type(expr.args[0], local_vars).is_list():
                        return TYPE_FLOAT
                    if attr in ("zeros", "ones", "empty") and expr.args and isinstance(expr.args[0], (ast.Tuple, ast.List)) and len(expr.args[0].elts) >= 2:
                        return ListType(element_type=ListType(element_type=TYPE_FLOAT))
                    return ListType(element_type=TYPE_FLOAT)
                elif attr == "column_stack":
                    return ListType(element_type=ListType(element_type=TYPE_FLOAT))
                elif attr in ("sin", "cos", "tan", "exp", "log", "log10"):
                    if expr.args and self._infer_node_type(expr.args[0], local_vars).is_list():
                        return ListType(element_type=TYPE_FLOAT)
                    return TYPE_FLOAT
                elif attr in ("ptp", "mean", "sum", "hypot", "atan2", "pow"):
                    return TYPE_FLOAT
                elif attr == "sqrt":
                    if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "cmath":
                        return TYPE_COMPLEX
                    return TYPE_FLOAT
                elif attr in ("isfinite", "isnan", "isinf", "isclose", "all", "any"):
                    return TYPE_BOOL
                elif attr in ("chain", "accumulate", "matmul", "pairwise"):
                    if attr in ("matmul",):
                        return ListType(element_type=TYPE_LIST)
                    return TYPE_LIST
                elif attr in ("count", "find", "index", "bit_length"):
                    return TYPE_INT
                elif attr in ("isdigit", "isascii"):
                    return TYPE_BOOL
                elif attr == "loads":
                    # json.loads() returns dict
                    if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "json":
                        return TYPE_DICT
                elif attr in ("get", "pop"):
                    obj_type = self._infer_node_type(expr.func.value, local_vars)
                    if attr == "pop" and obj_type.is_list() and getattr(obj_type, "element_type", None):
                        return obj_type.element_type
                    if obj_type.is_dict() and getattr(obj_type, "val_type", None):
                        return obj_type.val_type
                    if len(expr.args) >= 2:
                        return self._infer_node_type(expr.args[1], local_vars)
                if mod is not None:
                    if isinstance(expr.func.value, ast.Name):
                        pref = f"{expr.func.value.id}_{attr}"
                        if pref in mod.functions and mod.functions[pref].return_type != TYPE_VOID:
                            return mod.functions[pref].return_type
                    recv_t = self._infer_node_type(expr.func.value, local_vars)
                    if isinstance(recv_t, InstanceType):
                        seen_c = set()
                        cq = [recv_t.class_name]
                        while cq:
                            cn = cq.pop(0)
                            if cn in seen_c:
                                continue
                            seen_c.add(cn)
                            mname = f"{cn}_{attr}"
                            if mname in mod.functions and mod.functions[mname].return_type != TYPE_VOID:
                                return mod.functions[mname].return_type
                            cs = mod.classes.get(cn)
                            if cs:
                                cq.extend(cs.bases)

        elif isinstance(expr, ast.Attribute):
            if (
                isinstance(expr.value, ast.Name)
                and expr.value.id in ("math", "cmath", "np", "numpy")
                and expr.attr in ("pi", "e", "tau", "inf", "nan")
            ):
                return TYPE_FLOAT
            mod = getattr(self, "current_module", None)
            if mod is not None:
                recv_t = self._infer_node_type(expr.value, local_vars)
                if expr.attr in ("real", "imag") and (recv_t.is_complex() or recv_t.is_float()):
                    return TYPE_FLOAT
                if isinstance(recv_t, InstanceType):
                    seen_c: Set[str] = set()
                    cq = [recv_t.class_name]
                    while cq:
                        cn = cq.pop(0)
                        if cn in seen_c:
                            continue
                        seen_c.add(cn)
                        cs = mod.classes.get(cn)
                        if cs:
                            if expr.attr in cs.properties and cs.properties[expr.attr].getter_name:
                                gname = cs.properties[expr.attr].getter_name
                                if gname in mod.functions and mod.functions[gname].return_type != TYPE_VOID:
                                    return mod.functions[gname].return_type
                            if expr.attr in cs.field_types:
                                return cs.field_types[expr.attr]
                            cq.extend(cs.bases)
                if isinstance(expr.value, ast.Name) and expr.value.id in mod.classes:
                    cs = mod.classes[expr.value.id]
                    if expr.attr in cs.field_types:
                        return cs.field_types[expr.attr]
                    if expr.attr in cs.class_attrs:
                        cval = cs.class_attrs[expr.attr]
                        if isinstance(cval, bool):
                            return TYPE_BOOL
                        if isinstance(cval, float):
                            return TYPE_FLOAT
                        if isinstance(cval, str):
                            return TYPE_STR

        elif isinstance(expr, ast.Subscript):
            container_type = self._infer_node_type(expr.value, local_vars)
            sub_slice = expr.slice.value if (hasattr(ast, "Index") and isinstance(expr.slice, ast.Index)) else expr.slice
            if isinstance(sub_slice, ast.Slice):
                if container_type.is_str():
                    return TYPE_STR
                if container_type.is_list() or container_type.is_tuple():
                    return container_type
                return container_type
            else:
                if container_type.is_str():
                    return TYPE_STR
                if container_type.is_list():
                    if isinstance(sub_slice, ast.Tuple) and len(sub_slice.elts) == 2 and not any(isinstance(e, ast.Slice) for e in sub_slice.elts):
                        elem1 = getattr(container_type, "element_type", None)
                        if elem1 and elem1.is_list() and getattr(elem1, "element_type", None):
                            return elem1.element_type
                        return TYPE_INT
                    if hasattr(container_type, "element_type") and container_type.element_type:
                        return container_type.element_type
                    return TYPE_INT
                if container_type.is_tuple():
                    if (
                        isinstance(sub_slice, ast.Constant)
                        and isinstance(sub_slice.value, int)
                        and getattr(container_type, "element_types", None)
                    ):
                        idx = sub_slice.value
                        ets = container_type.element_types
                        if -len(ets) <= idx < len(ets):
                            return ets[idx]
                    if getattr(container_type, "element_type", None):
                        return container_type.element_type
                    return TYPE_INT
                if container_type.is_dict() and hasattr(container_type, "val_type") and container_type.val_type:
                    return container_type.val_type
                if isinstance(expr.value, ast.Name):
                    vname = expr.value.id.lower()
                    if any(k in vname for k in ("words", "tags", "names", "lines", "strs", "strings", "titles")):
                        return TYPE_STR
                return TYPE_INT

        return TYPE_INT

    def _analyze_function(
        self,
        node: ast.FunctionDef,
        owner_class: Optional[str] = None,
        is_static: bool = False,
        is_classmethod: bool = False,
    ) -> FunctionSymbol:
        prev_fn_name = self._current_func_name
        self._current_func_name = node.name
        try:
            return self._analyze_function_impl(
                node,
                owner_class=owner_class,
                is_static=is_static,
                is_classmethod=is_classmethod,
            )
        finally:
            self._current_func_name = prev_fn_name

    def _analyze_function_impl(
        self,
        node: ast.FunctionDef,
        owner_class: Optional[str] = None,
        is_static: bool = False,
        is_classmethod: bool = False,
    ) -> FunctionSymbol:
        # Determine return type
        ret_type = TYPE_VOID
        if node.returns:
            rt_ann = self._resolve_annotation_type(node.returns)
            if rt_ann is not None:
                ret_type = rt_ann

        args: List[VariableSymbol] = []
        local_vars: Dict[str, VariableSymbol] = {}
        offset = 8

        # Process function arguments (include posonlyargs if present)
        all_ast_args = list(getattr(node.args, "posonlyargs", [])) + list(node.args.args)
        for idx, arg in enumerate(all_ast_args):
            arg_name = arg.arg
            arg_type = TYPE_INT
            is_dyn_arg = False
            ann = getattr(arg, "annotation", None)
            if ann:
                ann_t = self._resolve_annotation_type(ann)
                arg_type = ann_t if ann_t is not None else TYPE_INT
            elif idx == 0 and owner_class and not is_static and not is_classmethod and arg_name in ("self", "this"):
                arg_type = InstanceType(class_name=owner_class)
            elif idx == 0 and is_classmethod:
                arg_type = TYPE_PTR
            elif arg_name == "_pyfasm_env":
                arg_type = TYPE_PTR
            elif node.name.startswith("_pyfasm_genexp_") and node.name in getattr(self, "_genexp_arg_types", {}):
                gtypes = self._genexp_arg_types[node.name]
                if idx < len(gtypes) and gtypes[idx] != TYPE_INT:
                    arg_type = gtypes[idx]
                else:
                    is_dyn_arg = arg_name != "self"
            elif node.name.startswith(("_pyfasm_lambda_", "_pyfasm_closure_", "_pyfasm_nested_")):
                is_dyn_arg = True
            elif arg_name in ("st", "s", "str", "string", "text", "txt", "msg", "prompt", "pattern", "subpattern", "word", "line"):
                arg_type = TYPE_STR
            else:
                is_dyn_arg = arg_name != "self"

            var_sym = VariableSymbol(
                name=arg_name,
                var_type=arg_type,
                stack_offset=offset,
                is_arg=True,
                arg_index=idx,
                is_dynamic=is_dyn_arg,
            )
            args.append(var_sym)
            local_vars[arg_name] = var_sym
            offset += 8

        # Discover all assigned variables in the function body with local type inference (multi-pass for chained type resolution)
        global_names: Set[str] = set()
        for sub_node in walk_local_scope(node):
            if isinstance(sub_node, ast.Global):
                for gname in sub_node.names:
                    global_names.add(gname)
                    if hasattr(self, "current_module") and self.current_module is not None:
                        if gname not in self.current_module.global_vars:
                            self.current_module.global_vars[gname] = 0

        mod = getattr(self, "current_module", None)
        mod_prefix = getattr(self, "_current_mod_prefix", "")

        def _get_var_type(vname: str) -> Optional[PyFasmType]:
            if vname in local_vars:
                return local_vars[vname].var_type
            if mod is not None:
                if mod_prefix and f"{mod_prefix}_{vname}" in mod.global_var_types:
                    return mod.global_var_types[f"{mod_prefix}_{vname}"]
                if vname in mod.global_var_types:
                    return mod.global_var_types[vname]
            return None

        def _set_var_type(vname: str, new_t: PyFasmType) -> None:
            if vname in local_vars:
                local_vars[vname].var_type = new_t
            elif vname in global_names or (mod is not None and vname in mod.global_var_types):
                self._record_global_var_type(mod, vname, new_t, mod_prefix)

        def _record_cell_val(cname: str, new_t: Optional[PyFasmType]) -> None:
            if mod is None or new_t is None:
                return
            cur_c = mod.cell_val_types.get(cname)
            if cur_c is None or self._should_upgrade_type(cur_c, new_t):
                mod.cell_val_types[cname] = new_t

        for _pass in range(4):
            pass_list_obs: Dict[str, List[Optional[PyFasmType]]] = {}
            pass_set_obs: Dict[str, List[Optional[PyFasmType]]] = {}
            pass_dict_k_obs: Dict[str, List[Optional[PyFasmType]]] = {}
            pass_dict_v_obs: Dict[str, List[Optional[PyFasmType]]] = {}

            for sub_node in walk_local_scope(node):
                if isinstance(sub_node, ast.Assign):
                    if (
                        len(sub_node.targets) == 1
                        and isinstance(sub_node.targets[0], ast.Name)
                        and isinstance(sub_node.value, ast.Call)
                        and isinstance(sub_node.value.func, ast.Name)
                        and sub_node.value.func.id == "_pyfasm_cell_new"
                        and sub_node.value.args
                    ):
                        _record_cell_val(sub_node.targets[0].id, self._infer_node_type(sub_node.value.args[0], local_vars))
                    inferred_type = self._infer_node_type(sub_node.value, local_vars)
                    rhs_dynamic = inferred_type == TYPE_INT and self._is_dynamic_expr(sub_node.value, local_vars)
                    rhs_widget_kind = self._constructed_widget_kind(sub_node.value)
                    targets_to_proc = []
                    for target in sub_node.targets:
                        if isinstance(target, ast.Name):
                            targets_to_proc.append((target.id, inferred_type, rhs_dynamic))
                        elif isinstance(target, (ast.Tuple, ast.List)):
                            rhs_seq_dyn = (
                                (inferred_type.is_list() and getattr(inferred_type, "element_type", None) is None)
                                or (inferred_type.is_tuple() and getattr(inferred_type, "element_type", None) is None and getattr(inferred_type, "element_types", None) is None)
                                or rhs_dynamic
                            )
                            for un_name, un_t in self._unpack_target_types(target, inferred_type):
                                targets_to_proc.append((un_name, un_t, un_t == TYPE_INT and rhs_seq_dyn))
                        elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                            cname = target.value.id
                            ct = _get_var_type(cname)
                            kt = self._infer_node_type(target.slice, local_vars)
                            vt = inferred_type
                            if ct is not None and ct.is_dict():
                                pass_dict_k_obs.setdefault(cname, []).append(kt)
                                pass_dict_v_obs.setdefault(cname, []).append(vt)
                            elif ct is not None and ct.is_list() and not isinstance(target.slice, ast.Slice):
                                pass_list_obs.setdefault(cname, []).append(vt)
                    for vname, t_type, is_dyn in targets_to_proc:
                        rhs_fn_alias: Optional[str] = None
                        if isinstance(sub_node.value, ast.Name) and mod is not None and sub_node.value.id in mod.functions:
                            rhs_fn_alias = sub_node.value.id
                        elif isinstance(sub_node.value, ast.Call) and isinstance(sub_node.value.func, ast.Name):
                            if sub_node.value.func.id == "_pyfasm_closure_new" and sub_node.value.args and isinstance(sub_node.value.args[0], ast.Name):
                                rhs_fn_alias = sub_node.value.args[0].id
                        if vname in global_names:
                            self._record_global_var_type(mod, vname, t_type, mod_prefix)
                        else:
                            if vname not in local_vars:
                                local_vars[vname] = VariableSymbol(
                                    name=vname,
                                    var_type=t_type,
                                    stack_offset=offset,
                                    is_arg=False,
                                    is_dynamic=is_dyn,
                                    fn_alias=rhs_fn_alias,
                                )
                                offset += 8
                            else:
                                if rhs_fn_alias is not None and local_vars[vname].fn_alias is None:
                                    local_vars[vname].fn_alias = rhs_fn_alias
                                if self._should_upgrade_type(local_vars[vname].var_type, t_type):
                                    local_vars[vname].var_type = t_type
                                    local_vars[vname].is_dynamic = False
                                elif is_dyn and local_vars[vname].var_type == TYPE_INT:
                                    local_vars[vname].is_dynamic = True
                        if rhs_widget_kind is not None:
                            if vname in local_vars:
                                local_vars[vname].widget_kind = rhs_widget_kind
                            elif mod is not None:
                                mod.global_widget_kinds[vname] = rhs_widget_kind
                                if mod_prefix:
                                    mod.global_widget_kinds[f"{mod_prefix}_{vname}"] = rhs_widget_kind
                        if t_type.is_list() and getattr(t_type, "element_type", None) is not None:
                            pass_list_obs.setdefault(vname, []).append(t_type.element_type)
                        elif t_type.is_set() and getattr(t_type, "element_type", None) is not None:
                            pass_set_obs.setdefault(vname, []).append(t_type.element_type)
                        elif t_type.is_dict():
                            if getattr(t_type, "key_type", None) is not None:
                                pass_dict_k_obs.setdefault(vname, []).append(t_type.key_type)
                            if getattr(t_type, "val_type", None) is not None:
                                pass_dict_v_obs.setdefault(vname, []).append(t_type.val_type)
                elif isinstance(sub_node, ast.AnnAssign) and isinstance(sub_node.target, ast.Name):
                    vname = sub_node.target.id
                    vtype = TYPE_INT
                    if isinstance(sub_node.annotation, ast.Name):
                        vtype = resolve_type(sub_node.annotation.id)
                    elif isinstance(sub_node.annotation, ast.Constant) and isinstance(sub_node.annotation.value, str):
                        vtype = resolve_type(sub_node.annotation.value)
                    if sub_node.value is not None:
                        inferred_val_t = self._infer_node_type(sub_node.value, local_vars)
                        if vtype == TYPE_INT or self._should_upgrade_type(vtype, inferred_val_t):
                            vtype = inferred_val_t
                    if vname in global_names:
                        self._record_global_var_type(mod, vname, vtype, mod_prefix)
                        continue
                    if vname not in local_vars:
                        local_vars[vname] = VariableSymbol(
                            name=vname,
                            var_type=vtype,
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8
                    elif self._should_upgrade_type(local_vars[vname].var_type, vtype):
                        local_vars[vname].var_type = vtype
                elif isinstance(sub_node, ast.Call):
                    if isinstance(sub_node.func, ast.Name):
                        cfid = sub_node.func.id
                        if cfid == "_pyfasm_closure_new" and sub_node.args and isinstance(sub_node.args[0], ast.Name):
                            self._closure_cap_types[sub_node.args[0].id] = [
                                self._infer_node_type(a, local_vars) for a in sub_node.args[1:]
                            ]
                        elif cfid == "_pyfasm_cell_set" and len(sub_node.args) >= 2 and isinstance(sub_node.args[0], ast.Name):
                            _record_cell_val(sub_node.args[0].id, self._infer_node_type(sub_node.args[1], local_vars))
                        elif cfid.startswith("_pyfasm_genexp_"):
                            self._genexp_arg_types[cfid] = [
                                self._infer_node_type(a, local_vars) for a in sub_node.args
                            ]
                    if (
                        isinstance(sub_node.func, ast.Attribute)
                        and isinstance(sub_node.func.value, ast.Call)
                        and isinstance(sub_node.func.value.func, ast.Name)
                        and sub_node.func.value.func.id == "_pyfasm_cell_get"
                        and sub_node.func.value.args
                        and isinstance(sub_node.func.value.args[0], ast.Name)
                    ):
                        cell_n = sub_node.func.value.args[0].id
                        m_attr = sub_node.func.attr
                        if m_attr == "append" and len(sub_node.args) == 1:
                            _record_cell_val(cell_n, ListType(element_type=self._infer_node_type(sub_node.args[0], local_vars)))
                        elif m_attr == "insert" and len(sub_node.args) >= 2:
                            _record_cell_val(cell_n, ListType(element_type=self._infer_node_type(sub_node.args[1], local_vars)))
                        elif m_attr == "extend" and len(sub_node.args) == 1:
                            _record_cell_val(cell_n, ListType(element_type=self._infer_iter_element_type(sub_node.args[0], local_vars)))
                    if isinstance(sub_node.func, ast.Attribute) and isinstance(sub_node.func.value, ast.Name):
                        cname = sub_node.func.value.id
                        attr = sub_node.func.attr
                        if attr in ("append",) and len(sub_node.args) == 1:
                            pass_list_obs.setdefault(cname, []).append(self._infer_node_type(sub_node.args[0], local_vars))
                        elif attr == "insert" and len(sub_node.args) >= 2:
                            pass_list_obs.setdefault(cname, []).append(self._infer_node_type(sub_node.args[1], local_vars))
                        elif attr == "extend" and len(sub_node.args) == 1:
                            ext_elem = self._infer_iter_element_type(sub_node.args[0], local_vars)
                            ext_t = self._infer_node_type(sub_node.args[0], local_vars)
                            if ext_t.is_str() or getattr(ext_t, "element_type", None) is not None:
                                pass_list_obs.setdefault(cname, []).append(ext_elem)
                        elif attr == "add" and len(sub_node.args) == 1:
                            pass_set_obs.setdefault(cname, []).append(self._infer_node_type(sub_node.args[0], local_vars))
                elif isinstance(sub_node, ast.For):
                    loop_elem_t = self._infer_iter_element_type(sub_node.iter, local_vars)
                    iter_container_t = self._infer_node_type(sub_node.iter, local_vars)
                    loop_iter_is_range = (
                        isinstance(sub_node.iter, ast.Call)
                        and isinstance(sub_node.iter.func, ast.Name)
                        and sub_node.iter.func.id == "range"
                    )
                    loop_dyn = (
                        not loop_iter_is_range
                        and (
                            (iter_container_t.is_list() and getattr(iter_container_t, "element_type", None) is None)
                            or (iter_container_t.is_set() and getattr(iter_container_t, "element_type", None) is None)
                            or (iter_container_t.is_tuple() and getattr(iter_container_t, "element_type", None) is None and getattr(iter_container_t, "element_types", None) is None)
                            or (iter_container_t.is_dict() and getattr(iter_container_t, "key_type", None) is None)
                            or self._is_dynamic_expr(sub_node.iter, local_vars)
                        )
                    )
                    for vname, elem_t in self._unpack_target_types(sub_node.target, loop_elem_t):
                        if vname in global_names:
                            self._record_global_var_type(mod, vname, elem_t, mod_prefix)
                            continue
                        is_elt_dyn = elem_t == TYPE_INT and loop_dyn
                        if vname not in local_vars:
                            local_vars[vname] = VariableSymbol(
                                name=vname,
                                var_type=elem_t,
                                stack_offset=offset,
                                is_arg=False,
                                is_dynamic=is_elt_dyn,
                            )
                            offset += 8
                        elif self._should_upgrade_type(local_vars[vname].var_type, elem_t):
                            local_vars[vname].var_type = elem_t
                            local_vars[vname].is_dynamic = False
                        elif is_elt_dyn and local_vars[vname].var_type == TYPE_INT:
                            local_vars[vname].is_dynamic = True

                    # Loop buffers for safe register spilling across yields and nested loops
                    buf_name = f"_pyfasm_for_buf_{id(sub_node)}"
                    idx_name = f"_pyfasm_for_idx_{id(sub_node)}"
                    if buf_name not in local_vars:
                        local_vars[buf_name] = VariableSymbol(
                            name=buf_name,
                            var_type=TYPE_PTR,
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8
                    if idx_name not in local_vars:
                        local_vars[idx_name] = VariableSymbol(
                            name=idx_name,
                            var_type=TYPE_INT,
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8
                elif isinstance(sub_node, ast.With):
                    for item in sub_node.items:
                        if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                            vname = item.optional_vars.id
                            if vname in global_names:
                                continue
                            if vname not in local_vars:
                                local_vars[vname] = VariableSymbol(
                                    name=vname,
                                    var_type=TYPE_INT,
                                    stack_offset=offset,
                                    is_arg=False
                                )
                                offset += 8
                elif isinstance(sub_node, ast.NamedExpr) and isinstance(sub_node.target, ast.Name):
                    vname = sub_node.target.id
                    val_t = self._infer_node_type(sub_node.value, local_vars)
                    if vname in global_names:
                        self._record_global_var_type(mod, vname, val_t, mod_prefix)
                        continue
                    if vname not in local_vars:
                        local_vars[vname] = VariableSymbol(
                            name=vname,
                            var_type=val_t,
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8
                    elif self._should_upgrade_type(local_vars[vname].var_type, val_t):
                        local_vars[vname].var_type = val_t
                elif isinstance(sub_node, (ast.ListComp, ast.DictComp, ast.SetComp)):
                    for gen in sub_node.generators:
                        comp_elt_t = self._infer_iter_element_type(gen.iter, local_vars)
                        for vname, elt_t in self._unpack_target_types(gen.target, comp_elt_t):
                            if vname in global_names:
                                continue
                            if vname not in local_vars:
                                local_vars[vname] = VariableSymbol(
                                    name=vname,
                                    var_type=elt_t,
                                    stack_offset=offset,
                                    is_arg=False
                                )
                                offset += 8
                            elif self._should_upgrade_type(local_vars[vname].var_type, elt_t):
                                local_vars[vname].var_type = elt_t
                elif isinstance(sub_node, _AST_MATCH):
                    for case in sub_node.cases:
                        if isinstance(case.pattern, _AST_MATCH_AS) and case.pattern.name:
                            vname = case.pattern.name
                            if vname != "_" and vname not in global_names and vname not in local_vars:
                                local_vars[vname] = VariableSymbol(
                                    name=vname,
                                    var_type=TYPE_INT,
                                    stack_offset=offset,
                                    is_arg=False
                                )
                                offset += 8
                elif isinstance(sub_node, ast.ExceptHandler) and sub_node.name:
                    vname = sub_node.name
                    if vname in global_names:
                        continue
                    if vname not in local_vars:
                        local_vars[vname] = VariableSymbol(
                            name=vname,
                            var_type=TYPE_INT,
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8

            # Reconcile container element/key/value types observed in this pass.
            # GUI handles are not containers: widget.insert()/.add() must not retype them.
            for obs_map in (pass_list_obs, pass_set_obs, pass_dict_k_obs, pass_dict_v_obs):
                for cname in [c for c in obs_map if self._receiver_widget_kind(ast.Name(id=c), local_vars)]:
                    del obs_map[cname]
            for cname, obs in pass_list_obs.items():
                cur_t = _get_var_type(cname)
                if cur_t is not None and (cur_t.is_list() or cur_t == TYPE_INT):
                    merged = self._merge_element_types(obs)
                    if (
                        cur_t.is_list()
                        and getattr(cur_t, "element_type", None) is not None
                        and cur_t.element_type.is_list()
                        and (merged is None or not merged.is_list())
                    ):
                        continue
                    new_lt = ListType(element_type=merged) if merged else TYPE_LIST
                    _set_var_type(cname, new_lt)
            for cname, obs in pass_set_obs.items():
                cur_t = _get_var_type(cname)
                if cur_t is not None and (cur_t.is_set() or cur_t == TYPE_INT):
                    merged = self._merge_element_types(obs)
                    new_st = SetType(element_type=merged) if merged else TYPE_SET
                    _set_var_type(cname, new_st)
            for cname in set(pass_dict_k_obs) | set(pass_dict_v_obs):
                cur_t = _get_var_type(cname)
                if cur_t is not None and (cur_t.is_dict() or cur_t == TYPE_INT):
                    kt = self._merge_element_types(pass_dict_k_obs.get(cname, []))
                    vt = self._merge_element_types(pass_dict_v_obs.get(cname, []))
                    _set_var_type(cname, DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT)

        is_gen = any(isinstance(sub, (ast.Yield, ast.YieldFrom)) for sub in walk_local_scope(node))
        if is_gen and ret_type == TYPE_VOID:
            ret_type = TYPE_PTR

        # Usage-based type refinement: upgrade INT variables to LIST/DICT
        # based on how they are used in the function body (e.g. .get() → dict, len() → list).
        # GUI handles (widgets, StringVar) keep their type: their .get()/.insert() are widget calls.
        def _refinable(vname: str) -> bool:
            sym = local_vars.get(vname)
            return sym is not None and sym.var_type == TYPE_INT and sym.widget_kind is None

        for sub_node in walk_local_scope(node):
            for usage_node in ast.walk(sub_node):
                if isinstance(usage_node, ast.Call):
                    if isinstance(usage_node.func, ast.Attribute):
                        attr_name = usage_node.func.attr
                        if attr_name in ("get", "keys", "values", "items", "update", "setdefault") and isinstance(usage_node.func.value, ast.Name):
                            vname = usage_node.func.value.id
                            if _refinable(vname):
                                local_vars[vname].var_type = TYPE_DICT
                        elif attr_name in ("append", "extend", "insert", "remove", "sort", "reverse") and isinstance(usage_node.func.value, ast.Name):
                            vname = usage_node.func.value.id
                            if _refinable(vname):
                                local_vars[vname].var_type = TYPE_LIST
                    elif isinstance(usage_node.func, ast.Name) and usage_node.func.id in ("len", "heappop", "heappush", "heapreplace", "heapify"):
                        if usage_node.args and isinstance(usage_node.args[0], ast.Name):
                            vname = usage_node.args[0].id
                            if _refinable(vname):
                                local_vars[vname].var_type = TYPE_LIST

        # If return type wasn't explicitly annotated, infer from return statements
        if ret_type == TYPE_VOID:
            ret_candidates = []
            for sub_node in walk_local_scope(node):
                if isinstance(sub_node, ast.Return) and sub_node.value is not None:
                    ret_candidates.append(self._infer_node_type(sub_node.value, local_vars))
            if ret_candidates:
                merged_ret = self._merge_element_types(ret_candidates)
                ret_type = merged_ret if merged_ret is not None else TYPE_INT

        is_dyn_ret = False
        if node.returns is None and ret_type == TYPE_INT:
            is_dyn_ret = any(
                self._is_dynamic_expr(sub_node.value, local_vars)
                for sub_node in walk_local_scope(node)
                if isinstance(sub_node, ast.Return) and sub_node.value is not None
            )

        # 16-byte alignment + shadow space
        aligned_stack = ((offset + 15) // 16) * 16 + 32

        return FunctionSymbol(
            name=node.name,
            args=args,
            return_type=ret_type,
            local_vars=local_vars,
            stack_size=aligned_stack,
            ast_node=node,
            global_names=global_names,
            is_generator=is_gen,
            defaults=list(node.args.defaults),
            source_file=self._current_source_file,
            is_staticmethod=is_static,
            is_classmethod=is_classmethod,
            is_closure=node.name.startswith("_pyfasm_closure_"),
            is_dynamic_return=is_dyn_ret,
        )
