"""
AST Parser and Semantic Analyzer for PyFASM.
Traverses Python AST, extracts functions, variables, and type information
across single files or complete multi-module project libraries.
"""
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from pyfasm.types import (
    PyFasmType, resolve_type, TYPE_INT, TYPE_VOID, TYPE_STR, TYPE_PTR,
    TYPE_FLOAT, TYPE_BOOL, TYPE_LIST, TYPE_DICT, TYPE_SET, TYPE_TUPLE, TYPE_GENERATOR, InstanceType, ListType, DictType, SetType
)


@dataclass
class VariableSymbol:
    name: str
    var_type: PyFasmType
    stack_offset: int  # Offset from RBP: [rbp - stack_offset]
    is_arg: bool = False
    arg_index: int = 0
    is_generator: bool = False


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
class ParsedModule:
    functions: Dict[str, FunctionSymbol] = field(default_factory=dict)
    classes: Dict[str, ClassSymbol] = field(default_factory=dict)
    string_literals: List[StringLiteral] = field(default_factory=list)
    float_literals: List[FloatLiteral] = field(default_factory=list)
    global_vars: Dict[str, int] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    detected_libraries: Set[str] = field(default_factory=set)
    main_func: Optional[FunctionSymbol] = None
    calls_main_in_top_level: bool = False
    ui_spec: Optional[Any] = None
    module_inits: List[str] = field(default_factory=list)

    def has_library(self, *names: str) -> bool:
        """Check if any of the specified library names is installed in project or imported."""
        targets = {n.lower() for n in names}
        for lib in self.detected_libraries:
            l_low = lib.lower()
            if l_low in targets or any(l_low.startswith(t) or t in l_low for t in targets):
                return True
        for imp in self.imports:
            root = imp.split(".")[0].lower().replace("-", "_")
            if root in targets or any(root.startswith(t) or t in root for t in targets):
                return True
        return False

    @property
    def is_tray_app(self) -> bool:
        return self.has_library("pystray", "tray") or any("punto" in s.lower() or "tray" in s.lower() for s in self.classes)

    @property
    def is_keyboard_hook_app(self) -> bool:
        return self.has_library("keyboard", "pynput", "hook") or self.is_tray_app

    @property
    def is_modern_gui(self) -> bool:
        return self.has_library("customtkinter", "tkinter", "ctk", "flet", "textual", "qt", "pyqt5", "pyqt6", "pyside6") or any("app" in s.lower() or "gui" in s.lower() or "window" in s.lower() for s in self.classes)

    @property
    def is_http_app(self) -> bool:
        return self.has_library("requests", "urllib", "urllib3", "httpx", "aiohttp", "curl_cffi", "json")

    @property
    def is_office_app(self) -> bool:
        return self.has_library("docx", "openpyxl", "xlsxwriter", "fitz", "pymupdf", "pdf", "pypdf")

    @property
    def is_media_app(self) -> bool:
        return self.has_library("cv2", "opencv", "ffmpeg", "pyaudio", "sounddevice", "pil", "pillow")


def walk_local_scope(node: ast.AST):
    """Walk an AST node without descending into nested function or class scopes."""
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            yield from walk_local_scope(child)



class ConstantFolder(ast.NodeTransformer):
    """Evaluates compile-time constant expressions (Constant Folding)."""

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
                    res = lv * rv
                elif isinstance(node.op, ast.FloorDiv) and rv != 0:
                    res = lv // rv
                elif isinstance(node.op, ast.Mod) and rv != 0:
                    res = lv % rv
                elif isinstance(node.op, ast.Pow):
                    res = lv ** rv
                elif isinstance(node.op, ast.BitAnd):
                    res = lv & rv
                elif isinstance(node.op, ast.BitOr):
                    res = lv | rv
                elif isinstance(node.op, ast.BitXor):
                    res = lv ^ rv
                elif isinstance(node.op, ast.LShift):
                    res = lv << rv
                elif isinstance(node.op, ast.RShift):
                    res = lv >> rv

                if res is not None:
                    return ast.Constant(value=res)
            except Exception:
                pass
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.operand, ast.Constant):
            v = node.operand.value
            try:
                if isinstance(node.op, ast.USub):
                    return ast.Constant(value=-v)
                elif isinstance(node.op, ast.UAdd):
                    return ast.Constant(value=+v)
                elif isinstance(node.op, ast.Invert):
                    return ast.Constant(value=~v)
                elif isinstance(node.op, ast.Not):
                    return ast.Constant(value=not v)
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


class LambdaLifter(ast.NodeTransformer):
    """Lifts anonymous lambda expressions into module-level FunctionDef nodes."""

    def __init__(self):
        super().__init__()
        self.lambdas: List[ast.FunctionDef] = []
        self.counter: int = 0

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        self.generic_visit(node)
        self.counter += 1
        fn_name = f"_pyfasm_lambda_{self.counter}"
        ret_stmt = ast.Return(value=node.body)
        fn_def = ast.FunctionDef(
            name=fn_name,
            args=node.args,
            body=[ret_stmt],
            decorator_list=[],
            returns=None,
            lineno=getattr(node, "lineno", 1),
            col_offset=getattr(node, "col_offset", 0)
        )
        self.lambdas.append(fn_def)
        return ast.Name(id=fn_name, ctx=ast.Load())


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
        "any", "all", "map", "filter", "zip", "enumerate",
        "bisect", "bisect_right", "bisect_left", "heappush", "heappop",
        "gcd", "lcm", "isqrt", "factorial", "accumulate", "chain", "reduce"
    }

    def __init__(self):
        super().__init__()
        self.generators: List[ast.FunctionDef] = []
        self.counter: int = 0

    def _find_free_names(self, node: ast.AST, bound_names: Set[str]) -> List[str]:
        free_names: List[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                nid = sub.id
                if nid not in bound_names and nid not in self.BUILTIN_NAMES:
                    if nid not in free_names:
                        free_names.append(nid)
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
                args=[ast.arg(arg=name) for name in fn_param_names],
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


def preprocess_ast(tree: ast.AST) -> ast.AST:
    """Preprocesses AST: folds constants, desugars yield from, lifts generator expressions and lambdas."""
    tree = ImportCallTransformer().visit(tree)
    tree = ClassLambdaDesugarer().visit(tree)
    tree = MapMethodTransformer().visit(tree)
    tree = ChainedCompareTransformer().visit(tree)
    tree = ConstantFolder().visit(tree)
    tree = YieldFromTransformer().visit(tree)
    gen_lifter = GeneratorExpLifter()
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

    def __init__(self, project_root: Optional[Path | str] = None):
        self.strings: List[StringLiteral] = []
        self.floats: List[FloatLiteral] = []
        self.project_root: Optional[Path] = Path(project_root).resolve() if project_root else None
        self._visited_files: Set[Path] = set()
        self._site_packages_dirs: List[Path] = []
        self._str_counter = 0
        self._flt_counter = 0
        if self.project_root:
            self._discover_site_packages()

    def get_or_create_string(self, text: str) -> str:
        for s in self.strings:
            if s.value == text:
                return s.label
        self._str_counter += 1
        label = f"_str_lit_{self._str_counter}"
        self.strings.append(StringLiteral(label=label, value=text))
        return label

    def get_or_create_float(self, val: float) -> str:
        for f in self.floats:
            if abs(f.value - val) < 1e-12:
                return f.label
        self._flt_counter += 1
        label = f"_flt_lit_{self._flt_counter}"
        self.floats.append(FloatLiteral(label=label, value=val))
        return label

    def _detect_project_libraries(self, module: ParsedModule) -> None:
        """Inspects project dependencies from pyproject.toml, requirements.txt, uv.lock, and imports."""
        if not self.project_root or not self.project_root.exists():
            return

        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r"['\"]([a-zA-Z0-9_-]+)", text):
                    lib = match.group(1).lower().replace("-", "_")
                    if lib not in ("true", "false", "wheel", "pyfasm", "pyfasm64", "version", "description", "name"):
                        module.detected_libraries.add(lib)
            except Exception:
                pass

        reqs = self.project_root / "requirements.txt"
        if reqs.exists():
            try:
                for line in reqs.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip().split("#")[0].strip()
                    if line:
                        match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                        if match:
                            module.detected_libraries.add(match.group(1).lower().replace("-", "_"))
            except Exception:
                pass

        uvlock = self.project_root / "uv.lock"
        if uvlock.exists():
            try:
                text = uvlock.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r"['\"]([a-zA-Z0-9_-]+)", text):
                    lib = match.group(1).lower().replace("-", "_")
                    if lib not in ("pyfasm", "pyfasm64"):
                        module.detected_libraries.add(lib)
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
        tree = ast.parse(source_code)
        tree = preprocess_ast(tree)
        module = ParsedModule()

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
        self._extract_top_level_and_functions(tree, module, is_entry=True, mod_prefix="")
        self._propagate_generator_types(module)

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
        root_name = path.stem.lower() if path.is_file() else path.name.lower()
        if root_name in (
            "numpy", "scipy", "matplotlib", "torch", "cv2", "pandas",
            "cryptography", "win32api", "win32gui", "pythoncom", "ctypes",
            "customtkinter", "tkinter", "ttkbootstrap", "pil", "pillow",
            "pyfasm", "pyfasm64", "nanogemm",
        ):
            return True
        if path.is_dir():
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
        if mod_name == "pyfasm" or mod_name.startswith("pyfasm."):
            return None

        parts = mod_name.split(".")
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

        # Never add pyfasm source itself
        if "pyfasm" in real_path.parts and "src" in real_path.parts:
            try:
                import pyfasm
                pyfasm_pkg_dir = Path(pyfasm.__file__).parent.resolve()
                if pyfasm_pkg_dir in real_path.parents or real_path == pyfasm_pkg_dir:
                    return
            except Exception:
                pass

        if not real_path.exists() or not real_path.is_file():
            return

        try:
            source_code = real_path.read_text(encoding="utf-8-sig").lstrip("\ufeff")
            tree = ast.parse(source_code)
            tree = preprocess_ast(tree)
        except Exception as e:
            if is_entry:
                import sys
                print(f"[PyFASM ERROR] Failed to parse {real_path}: {e}", file=sys.stderr)
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
                    if alias.name == "pyfasm" or alias.name.startswith("pyfasm."):
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
                    if mod_name == "pyfasm" or mod_name.startswith("pyfasm."):
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
        self._extract_top_level_and_functions(tree, module, is_entry=is_entry, mod_prefix=mod_prefix)

    def _extract_top_level_and_functions(
        self,
        tree: ast.AST,
        module: ParsedModule,
        is_entry: bool = True,
        mod_prefix: str = ""
    ) -> None:
        self.current_module = module
        top_level_stmts = []
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign):
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name):
                        init_val = 0
                        if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, int):
                            init_val = int(stmt.value.value)  # bool -> int (False->0, True->1)
                        module.global_vars[tgt.id] = init_val
                        if mod_prefix:
                            module.global_vars[f"{mod_prefix}_{tgt.id}"] = init_val
            if isinstance(stmt, ast.FunctionDef):
                fn = self._analyze_function(stmt)
                if fn.name not in module.functions:
                    module.functions[fn.name] = fn
                if mod_prefix:
                    alias_name = f"{mod_prefix}_{fn.name}"
                    if alias_name not in module.functions:
                        module.functions[alias_name] = fn
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

    def _analyze_class(self, node: ast.ClassDef, module: ParsedModule, mod_prefix: str = "") -> ClassSymbol:
        cls_name = node.name
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(b.attr)

        cls_sym = ClassSymbol(name=cls_name, bases=bases, ast_node=node)

        # Discover field assignments in class methods (especially self.x = ...)
        fields: List[str] = []
        class_assigns: List[ast.Assign] = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.target.id not in fields:
                    fields.append(item.target.id)
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
                        if isinstance(item.value, (ast.Dict, ast.DictComp)):
                            cls_sym.field_types[tgt.id] = TYPE_DICT
                        elif isinstance(item.value, (ast.List, ast.ListComp)):
                            cls_sym.field_types[tgt.id] = TYPE_LIST
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
        cls_sym.fields = fields

        # Extract and register methods, properties, and getters/setters
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                is_prop_getter = False
                prop_setter_target = None
                for dec in item.decorator_list:
                    if isinstance(dec, ast.Name) and dec.id == "property":
                        is_prop_getter = True
                    elif isinstance(dec, ast.Attribute) and dec.attr == "setter" and isinstance(dec.value, ast.Name):
                        prop_setter_target = dec.value.id

                m_fn = self._analyze_function(item)
                m_fn.class_name = cls_name

                if is_prop_getter:
                    prop_name = item.name
                    getter_name = f"{cls_name}_get_{prop_name}"
                    m_fn.name = getter_name
                    cls_sym.methods[getter_name] = m_fn
                    if getter_name not in module.functions:
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
                    if setter_name not in module.functions:
                        module.functions[setter_name] = m_fn
                    if prop_name not in cls_sym.properties:
                        cls_sym.properties[prop_name] = PropertySymbol(name=prop_name)
                    cls_sym.properties[prop_name].setter_name = setter_name
                else:
                    method_name = f"{cls_name}_{item.name}"
                    m_fn.name = method_name  # Ensure class method has unique namespaced symbol name
                    cls_sym.methods[item.name] = m_fn

                    # Register namespaced method: ClassName_method (e.g. StackOverflowApp_mainloop)
                    if method_name not in module.functions:
                        module.functions[method_name] = m_fn

                    if mod_prefix:
                        pref_name = f"{mod_prefix}_{cls_name}_{item.name}"
                        if pref_name not in module.functions:
                            module.functions[pref_name] = m_fn

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
            synth_args = [ast.arg(arg="self")] + [ast.arg(arg=f) for f in fields]
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
            init_fn = self._analyze_function(synth_node)
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
            return_type=TYPE_PTR,
            stack_size=64
        )
        module.functions[cls_name] = ctor_sym
        if mod_prefix:
            module.functions[f"{mod_prefix}_{cls_name}"] = ctor_sym

        module.classes[cls_name] = cls_sym
        if mod_prefix:
            module.classes[f"{mod_prefix}_{cls_name}"] = cls_sym

        return class_assigns

    def _infer_node_type(self, expr: Optional[ast.AST], local_vars: Dict[str, VariableSymbol]) -> PyFasmType:
        """Infers the PyFasmType of an AST expression using local type propagation (inspired by Shedskin & Mypyc)."""
        if expr is None:
            return TYPE_INT

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
            return TYPE_INT

        elif isinstance(expr, ast.List):
            elem_t = None
            if expr.elts:
                elem_t = self._infer_node_type(expr.elts[0], local_vars)
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST

        elif isinstance(expr, ast.ListComp):
            elem_t = self._infer_node_type(expr.elt, local_vars)
            return ListType(element_type=elem_t) if elem_t else TYPE_LIST

        elif isinstance(expr, ast.Dict):
            kt = None
            vt = None
            if expr.keys and expr.keys[0] is not None:
                kt = self._infer_node_type(expr.keys[0], local_vars)
            if expr.values:
                vt = self._infer_node_type(expr.values[0], local_vars)
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT

        elif isinstance(expr, ast.DictComp):
            kt = self._infer_node_type(expr.key, local_vars)
            vt = self._infer_node_type(expr.value, local_vars)
            return DictType(key_type=kt, val_type=vt) if (kt or vt) else TYPE_DICT

        elif isinstance(expr, ast.Set):
            elem_t = None
            if expr.elts:
                elem_t = self._infer_node_type(expr.elts[0], local_vars)
            return SetType(element_type=elem_t) if elem_t else TYPE_SET

        elif isinstance(expr, ast.SetComp):
            elem_t = self._infer_node_type(expr.elt, local_vars)
            return SetType(element_type=elem_t) if elem_t else TYPE_SET

        elif isinstance(expr, ast.Tuple):
            return TYPE_TUPLE

        elif isinstance(expr, ast.JoinedStr):
            return TYPE_STR

        elif isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.MatMult):
                return ListType(element_type=TYPE_LIST)
            left_t = self._infer_node_type(expr.left, local_vars)
            right_t = self._infer_node_type(expr.right, local_vars)
            if left_t.is_float() or right_t.is_float():
                return TYPE_FLOAT
            if left_t.is_str() or right_t.is_str():
                return TYPE_STR
            if left_t.is_list() or right_t.is_list() or isinstance(expr.left, (ast.List, ast.Tuple)) or isinstance(expr.right, (ast.List, ast.Tuple)):
                return TYPE_LIST
            return TYPE_INT

        elif isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.Not):
                return TYPE_BOOL
            return self._infer_node_type(expr.operand, local_vars)

        elif isinstance(expr, ast.IfExp):
            return self._infer_node_type(expr.body, local_vars)

        elif isinstance(expr, ast.NamedExpr):
            return self._infer_node_type(expr.value, local_vars)

        elif isinstance(expr, (ast.Compare, ast.BoolOp)):
            return TYPE_BOOL

        elif isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                fid = expr.func.id
                if fid in ("str", "chr", "hex", "bin", "file_read", "get_simd_isa"):
                    return TYPE_STR
                elif fid in ("int", "ord", "len", "hash", "abs", "round", "open", "file_open", "bit_length"):
                    return TYPE_INT
                elif fid in ("float", "pow"):
                    return TYPE_FLOAT
                elif fid in ("bool", "isinstance", "issubclass", "isdigit", "isascii"):
                    return TYPE_BOOL
                elif fid in ("list", "range", "map", "filter", "zip", "enumerate", "chain", "accumulate", "sorted", "matmul", "zeros", "ones", "array", "asarray", "arange", "pairwise"):
                    if fid in ("matmul",):
                        return ListType(element_type=TYPE_LIST)
                    return TYPE_LIST
                elif fid in ("dict",):
                    return TYPE_DICT
                elif fid in ("set",):
                    return TYPE_SET
                elif fid in ("tuple",):
                    return TYPE_TUPLE
            elif isinstance(expr.func, ast.Attribute):
                attr = expr.func.attr
                if attr in ("read", "split", "strip", "replace", "lower", "upper", "capitalize", "format", "choice", "get_simd_isa"):
                    return TYPE_STR
                elif attr in ("keys", "values", "items", "chain", "accumulate", "matmul", "zeros", "ones", "array", "asarray", "arange", "pairwise"):
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
                elif attr == "get":
                    # dict.get(key, default) — infer from default arg type
                    if isinstance(expr.func.value, ast.Name) and expr.func.value.id in local_vars:
                        obj_type = local_vars[expr.func.value.id].var_type
                        if obj_type.is_dict() and len(expr.args) >= 2:
                            return self._infer_node_type(expr.args[1], local_vars)

        elif isinstance(expr, ast.Subscript):
            container_type = self._infer_node_type(expr.value, local_vars)
            if isinstance(expr.slice, ast.Slice):
                if container_type.is_str():
                    return TYPE_STR
                if container_type.is_list():
                    return container_type
                if container_type.is_tuple():
                    return TYPE_TUPLE
                return container_type
            else:
                if container_type.is_str():
                    return TYPE_STR
                if container_type.is_list():
                    if hasattr(container_type, "element_type") and container_type.element_type:
                        return container_type.element_type
                    return TYPE_LIST
                if container_type.is_dict() and hasattr(container_type, "val_type") and container_type.val_type:
                    return container_type.val_type
                if isinstance(expr.value, ast.Name):
                    vname = expr.value.id.lower()
                    if any(k in vname for k in ("words", "tags", "names", "lines", "strs", "strings", "titles")):
                        return TYPE_STR
                return TYPE_INT

        return TYPE_INT

    def _analyze_function(self, node: ast.FunctionDef) -> FunctionSymbol:
        # Determine return type
        ret_type = TYPE_VOID
        if node.returns:
            if isinstance(node.returns, ast.Name):
                ret_type = resolve_type(node.returns.id)
            elif isinstance(node.returns, ast.Constant) and isinstance(node.returns.value, str):
                ret_type = resolve_type(node.returns.value)

        args: List[VariableSymbol] = []
        local_vars: Dict[str, VariableSymbol] = {}
        offset = 8

        # Process function arguments
        for idx, arg in enumerate(node.args.args):
            arg_name = arg.arg
            arg_type = TYPE_INT
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    arg_type = resolve_type(arg.annotation.id)
                elif isinstance(arg.annotation, ast.Constant) and isinstance(arg.annotation.value, str):
                    arg_type = resolve_type(arg.annotation.value)
            elif arg_name in ("st", "s", "str", "string", "text", "txt", "msg", "prompt", "pattern", "subpattern", "word", "line"):
                arg_type = TYPE_STR

            var_sym = VariableSymbol(
                name=arg_name,
                var_type=arg_type,
                stack_offset=offset,
                is_arg=True,
                arg_index=idx
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

        for _pass in range(3):
            for sub_node in walk_local_scope(node):
                if isinstance(sub_node, ast.Assign):
                    inferred_type = self._infer_node_type(sub_node.value, local_vars)
                    targets_to_proc = []
                    for target in sub_node.targets:
                        if isinstance(target, ast.Name):
                            targets_to_proc.append((target.id, inferred_type))
                        elif isinstance(target, (ast.Tuple, ast.List)):
                            for elt in target.elts:
                                if isinstance(elt, ast.Name):
                                    targets_to_proc.append((elt.id, TYPE_INT))
                                elif isinstance(elt, ast.Starred) and isinstance(elt.value, ast.Name):
                                    targets_to_proc.append((elt.value.id, TYPE_LIST))
                    for vname, t_type in targets_to_proc:
                        if vname in global_names:
                            continue
                        if vname not in local_vars:
                            local_vars[vname] = VariableSymbol(
                                name=vname,
                                var_type=t_type,
                                stack_offset=offset,
                                is_arg=False
                            )
                            offset += 8
                        elif local_vars[vname].var_type == TYPE_INT and t_type != TYPE_INT:
                            local_vars[vname].var_type = t_type
                elif isinstance(sub_node, ast.AnnAssign) and isinstance(sub_node.target, ast.Name):
                    vname = sub_node.target.id
                    if vname in global_names:
                        continue
                    vtype = TYPE_INT
                    if isinstance(sub_node.annotation, ast.Name):
                        vtype = resolve_type(sub_node.annotation.id)
                    elif isinstance(sub_node.annotation, ast.Constant) and isinstance(sub_node.annotation.value, str):
                        vtype = resolve_type(sub_node.annotation.value)
                    if vname not in local_vars:
                        local_vars[vname] = VariableSymbol(
                            name=vname,
                            var_type=vtype,
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8
                elif isinstance(sub_node, ast.For):
                    if isinstance(sub_node.target, ast.Name):
                        vname = sub_node.target.id
                        if vname not in global_names and vname not in local_vars:
                            local_vars[vname] = VariableSymbol(
                                name=vname,
                                var_type=TYPE_INT,
                                stack_offset=offset,
                                is_arg=False
                            )
                            offset += 8
                    elif isinstance(sub_node.target, (ast.Tuple, ast.List)):
                        for sub_elt in ast.walk(sub_node.target):
                            if isinstance(sub_elt, ast.Name):
                                vname = sub_elt.id
                                if vname not in global_names and vname not in local_vars:
                                    local_vars[vname] = VariableSymbol(
                                        name=vname,
                                        var_type=TYPE_INT,
                                        stack_offset=offset,
                                        is_arg=False
                                    )
                                    offset += 8

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
                    if vname in global_names:
                        continue
                    if vname not in local_vars:
                        local_vars[vname] = VariableSymbol(
                            name=vname,
                            var_type=self._infer_node_type(sub_node.value, local_vars),
                            stack_offset=offset,
                            is_arg=False
                        )
                        offset += 8
                elif isinstance(sub_node, (ast.ListComp, ast.DictComp, ast.SetComp)):
                    for gen in sub_node.generators:
                        for sub_t in ast.walk(gen.target):
                            if isinstance(sub_t, ast.Name) and sub_t.id not in global_names:
                                vname = sub_t.id
                                if vname not in local_vars:
                                    local_vars[vname] = VariableSymbol(
                                        name=vname,
                                        var_type=TYPE_INT,
                                        stack_offset=offset,
                                        is_arg=False
                                    )
                                    offset += 8
                elif isinstance(sub_node, ast.Match):
                    for case in sub_node.cases:
                        if isinstance(case.pattern, ast.MatchAs) and case.pattern.name:
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
    
        is_gen = any(isinstance(sub, (ast.Yield, ast.YieldFrom)) for sub in walk_local_scope(node))
        if is_gen and ret_type == TYPE_VOID:
            ret_type = TYPE_PTR

        # Usage-based type refinement: upgrade INT variables to LIST/DICT
        # based on how they are used in the function body (e.g. .get() → dict, len() → list)
        for sub_node in walk_local_scope(node):
            for usage_node in ast.walk(sub_node):
                if isinstance(usage_node, ast.Call):
                    if isinstance(usage_node.func, ast.Attribute):
                        attr_name = usage_node.func.attr
                        if attr_name in ("get", "keys", "values", "items", "pop", "update", "setdefault") and isinstance(usage_node.func.value, ast.Name):
                            vname = usage_node.func.value.id
                            if vname in local_vars and local_vars[vname].var_type == TYPE_INT:
                                local_vars[vname].var_type = TYPE_DICT
                        elif attr_name in ("append", "extend", "insert", "remove", "sort", "reverse") and isinstance(usage_node.func.value, ast.Name):
                            vname = usage_node.func.value.id
                            if vname in local_vars and local_vars[vname].var_type == TYPE_INT:
                                local_vars[vname].var_type = TYPE_LIST
                    elif isinstance(usage_node.func, ast.Name) and usage_node.func.id in ("len", "heappop", "heappush", "heapreplace", "heapify"):
                        if usage_node.args and isinstance(usage_node.args[0], ast.Name):
                            vname = usage_node.args[0].id
                            if vname in local_vars and local_vars[vname].var_type == TYPE_INT:
                                local_vars[vname].var_type = TYPE_LIST

        # If return type wasn't explicitly annotated, infer from return statements
        if ret_type == TYPE_VOID:
            for sub_node in walk_local_scope(node):
                if isinstance(sub_node, ast.Return) and sub_node.value is not None:
                    ret_type = self._infer_node_type(sub_node.value, local_vars)
                    break

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
            defaults=list(node.args.defaults)
        )
