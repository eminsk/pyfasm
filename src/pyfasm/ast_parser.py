"""
AST Parser and Semantic Analyzer for PyFASM.
Traverses Python AST, extracts functions, variables, and type information
across single files or complete multi-module project libraries.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from pyfasm.types import PyFasmType, resolve_type, TYPE_INT, TYPE_VOID, TYPE_STR


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
    string_literals: List[StringLiteral] = field(default_factory=list)
    float_literals: List[FloatLiteral] = field(default_factory=list)
    global_vars: Dict[str, int] = field(default_factory=dict)
    main_func: Optional[FunctionSymbol] = None


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

    def parse_source(self, source_code: str) -> ParsedModule:
        """Parses a raw Python source code string into a ParsedModule."""
        tree = ast.parse(source_code)
        module = ParsedModule()

        # First pass: find string and float constants across the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    self.get_or_create_string(node.value)
                elif isinstance(node.value, float):
                    self.get_or_create_float(node.value)

        module.string_literals = self.strings
        module.float_literals = self.floats

        # Second pass: extract functions
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                fn = self._analyze_function(stmt)
                module.functions[fn.name] = fn
                if fn.name == "main":
                    module.main_func = fn

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
        except Exception:
            return

        # 1. Collect string & float constants across the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    self.get_or_create_string(node.value)
                elif isinstance(node.value, float):
                    self.get_or_create_float(node.value)

        # 2. Extract functions from this module
        mod_prefix = real_path.stem
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

        # Discover all assigned variables in the function body
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Assign):
                for target in sub_node.targets:
                    if isinstance(target, ast.Name):
                        vname = target.id
                        if vname not in local_vars:
                            local_vars[vname] = VariableSymbol(
                                name=vname,
                                var_type=TYPE_INT,
                                stack_offset=offset,
                                is_arg=False
                            )
                            offset += 8
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
