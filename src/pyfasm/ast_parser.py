"""
AST Parser and Semantic Analyzer for PyFASM.
Traverses Python AST, extracts functions, variables, and type information.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
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
class ParsedModule:
    functions: Dict[str, FunctionSymbol] = field(default_factory=dict)
    string_literals: List[StringLiteral] = field(default_factory=list)
    global_vars: Dict[str, int] = field(default_factory=dict)
    main_func: Optional[FunctionSymbol] = None


class AstAnalyzer:
    """Extracts function signatures, local variables, and string literals."""

    def __init__(self):
        self.strings: List[StringLiteral] = []
        self._str_counter = 0

    def get_or_create_string(self, text: str) -> str:
        for s in self.strings:
            if s.value == text:
                return s.label
        self._str_counter += 1
        label = f"_str_lit_{self._str_counter}"
        self.strings.append(StringLiteral(label=label, value=text))
        return label

    def parse_source(self, source_code: str) -> ParsedModule:
        tree = ast.parse(source_code)
        module = ParsedModule()

        # First pass: find string literals across the whole AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.get_or_create_string(node.value)

        module.string_literals = self.strings

        # Second pass: extract functions
        for stmt in tree.body:
            if isinstance(stmt, ast.FunctionDef):
                fn = self._analyze_function(stmt)
                module.functions[fn.name] = fn
                if fn.name == "main":
                    module.main_func = fn

        return module

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
        # In x64 Windows ABI, stack frames should be a multiple of 16 bytes
        # plus 32 bytes shadow space for outgoing calls
        aligned_stack = ((offset + 15) // 16) * 16 + 32

        return FunctionSymbol(
            name=node.name,
            args=args,
            return_type=ret_type,
            local_vars=local_vars,
            stack_size=aligned_stack,
            ast_node=node
        )
