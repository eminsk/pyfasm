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
    TYPE_FLOAT, TYPE_BOOL, TYPE_LIST, TYPE_DICT, TYPE_TUPLE, InstanceType
)


@dataclass
class VariableSymbol:
    name: str
    var_type: PyFasmType
    stack_offset: int  # Offset from RBP: [rbp - stack_offset]
    is_arg: bool = False
    arg_index: int = 0


@dataclass
class FunctionSymbol:
    name: str
    args: List[VariableSymbol]
    return_type: PyFasmType
    local_vars: Dict[str, VariableSymbol] = field(default_factory=dict)
    stack_size: int = 0
    ast_node: Optional[ast.FunctionDef] = None
    class_name: Optional[str] = None


@dataclass
class ClassSymbol:
    name: str
    methods: Dict[str, FunctionSymbol] = field(default_factory=dict)
    fields: List[str] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)
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
        return self.has_library("customtkinter", "tkinter", "ctk", "flet", "textual", "qt", "pyqt5", "pyqt6", "pyside6") or any("app" in s.lower() or "gui" in s.lower() for s in self.classes)

    @property
    def is_http_app(self) -> bool:
        return self.has_library("requests", "urllib", "urllib3", "httpx", "aiohttp", "curl_cffi")

    @property
    def is_office_app(self) -> bool:
        return self.has_library("docx", "openpyxl", "xlsxwriter", "fitz", "pymupdf", "pdf", "pypdf")

    @property
    def is_media_app(self) -> bool:
        return self.has_library("cv2", "opencv", "ffmpeg", "pyaudio", "sounddevice", "pil", "pillow")


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


class AstAnalyzer:
    """Extracts function signatures, local variables, and literals across single files or multi-module projects."""

    def __init__(self, project_root: Optional[Path | str] = None):
        self.strings: List[StringLiteral] = []
        self.floats: List[FloatLiteral] = []
        self.project_root: Optional[Path] = Path(project_root).resolve() if project_root else None
        self._visited_files: Set[Path] = set()
        self._str_counter = 0
        self._flt_counter = 0

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

    def parse_source(self, source_code: str) -> ParsedModule:
        """Parses a raw Python source code string into a ParsedModule."""
        tree = ast.parse(source_code)
        tree = ConstantFolder().visit(tree)
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

        # Second pass: extract functions and classes
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                fn = self._analyze_function(stmt)
                module.functions[fn.name] = fn
                if fn.name == "main":
                    module.main_func = fn
            elif isinstance(stmt, ast.ClassDef):
                self._analyze_class(stmt, module, mod_prefix="")

        return module

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

        module = ParsedModule()
        self._visited_files.clear()

        self._detect_project_libraries(module)
        # Recursively parse entry script and all internal project dependencies
        self._parse_file_recursive(entry_path, module, is_entry=True)

        module.string_literals = self.strings
        module.float_literals = self.floats
        return module

    def _resolve_local_module(self, mod_name: str, current_dir: Path) -> Optional[Path]:
        """Resolves an imported module name to a local .py file, strictly ignoring pyfasm itself."""
        # Never add or import pyfasm itself ("естественно добавлять саму себя не должна уже")
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

        return None

    def _parse_file_recursive(self, path: Path, module: ParsedModule, is_entry: bool = False) -> None:
        real_path = path.resolve()

        # Prevent circular imports and duplicate processing
        if real_path in self._visited_files:
            return
        self._visited_files.add(real_path)

        # Ignore virtual environments, cache, and git folders
        path_str = str(real_path).lower()
        if any(ign in path_str for ign in [".venv", "venv", "__pycache__", "site-packages", ".git"]):
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
            source_code = real_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code)
            tree = ConstantFolder().visit(tree)
        except Exception:
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

        # 2. Extract functions from this module
        mod_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', real_path.stem)
        if mod_prefix and mod_prefix[0].isdigit():
            mod_prefix = f"_{mod_prefix}" 
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                fn = self._analyze_function(stmt)
                # Primary name
                if fn.name not in module.functions:
                    module.functions[fn.name] = fn
                # Namespaced alias (e.g., utils_add, math_calc)
                alias_name = f"{mod_prefix}_{fn.name}"
                if alias_name not in module.functions:
                    module.functions[alias_name] = fn

                if is_entry and fn.name == "main":
                    module.main_func = fn
            elif isinstance(stmt, ast.ClassDef):
                self._analyze_class(stmt, module, mod_prefix=mod_prefix)

        # 3. Discover and recursively parse imported project modules
        for stmt in tree.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    # Never import self or pyfasm
                    if alias.name == "pyfasm" or alias.name.startswith("pyfasm."):
                        continue
                    dep = self._resolve_local_module(alias.name, real_path.parent)
                    if dep and dep != real_path:
                        self._parse_file_recursive(dep, module, is_entry=False)
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    if stmt.module == "pyfasm" or stmt.module.startswith("pyfasm."):
                        continue
                    dep = self._resolve_local_module(stmt.module, real_path.parent)
                    if dep and dep != real_path:
                        self._parse_file_recursive(dep, module, is_entry=False)

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
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                for sub in ast.walk(item):
                    if isinstance(sub, ast.Assign):
                        for tgt in sub.targets:
                            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                                if tgt.attr not in fields:
                                    fields.append(tgt.attr)
        cls_sym.fields = fields

        # Extract and register methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                m_fn = self._analyze_function(item)
                method_name = f"{cls_name}_{item.name}"
                m_fn.name = method_name  # Ensure class method has unique namespaced symbol name
                m_fn.class_name = cls_name
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

        return cls_sym

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
            return TYPE_LIST

        elif isinstance(expr, ast.Dict):
            return TYPE_DICT

        elif isinstance(expr, ast.Tuple):
            return TYPE_TUPLE

        elif isinstance(expr, ast.JoinedStr):
            return TYPE_STR

        elif isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.Div):
                return TYPE_FLOAT
            left_t = self._infer_node_type(expr.left, local_vars)
            right_t = self._infer_node_type(expr.right, local_vars)
            if left_t.is_float() or right_t.is_float():
                return TYPE_FLOAT
            if left_t.is_str() or right_t.is_str():
                return TYPE_STR
            if left_t.is_list():
                return TYPE_LIST
            return TYPE_INT

        elif isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.Not):
                return TYPE_BOOL
            return self._infer_node_type(expr.operand, local_vars)

        elif isinstance(expr, (ast.Compare, ast.BoolOp)):
            return TYPE_BOOL

        elif isinstance(expr, ast.Call):
            if isinstance(expr.func, ast.Name):
                fid = expr.func.id
                if fid in ("str", "chr", "hex", "bin"):
                    return TYPE_STR
                elif fid in ("int", "ord", "len", "hash", "abs", "round"):
                    return TYPE_INT
                elif fid in ("float", "pow"):
                    return TYPE_FLOAT
                elif fid in ("bool", "isinstance", "issubclass"):
                    return TYPE_BOOL
                elif fid in ("list", "range"):
                    return TYPE_LIST
                elif fid in ("dict",):
                    return TYPE_DICT
                elif fid in ("tuple",):
                    return TYPE_TUPLE
            elif isinstance(expr.func, ast.Attribute):
                attr = expr.func.attr
                if attr in ("split", "strip", "replace", "lower", "upper", "capitalize", "format"):
                    return TYPE_STR
                elif attr in ("keys", "values", "items"):
                    return TYPE_LIST
                elif attr in ("count", "find", "index"):
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

        # Discover all assigned variables in the function body with local type inference
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Assign):
                inferred_type = self._infer_node_type(sub_node.value, local_vars)
                for target in sub_node.targets:
                    if isinstance(target, ast.Name):
                        vname = target.id
                        if vname not in local_vars:
                            local_vars[vname] = VariableSymbol(
                                name=vname,
                                var_type=inferred_type,
                                stack_offset=offset,
                                is_arg=False
                            )
                            offset += 8
                        elif not local_vars[vname].is_arg and local_vars[vname].var_type == TYPE_INT and inferred_type != TYPE_INT:
                            local_vars[vname].var_type = inferred_type
            elif isinstance(sub_node, ast.AnnAssign) and isinstance(sub_node.target, ast.Name):
                vname = sub_node.target.id
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
            elif isinstance(sub_node, ast.For) and isinstance(sub_node.target, ast.Name):
                vname = sub_node.target.id
                if vname not in local_vars:
                    local_vars[vname] = VariableSymbol(
                        name=vname,
                        var_type=TYPE_INT,
                        stack_offset=offset,
                        is_arg=False
                    )
                    offset += 8

        # If return type wasn't explicitly annotated, infer from return statements
        if ret_type == TYPE_VOID:
            for sub_node in ast.walk(node):
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
            ast_node=node
        )
