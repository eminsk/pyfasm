"""
x86_64 Code Generator for PyFASM.
Emits clean, optimized Flat Assembler (FASM) assembly instructions.
"""
from __future__ import annotations
import ast
from typing import List, Dict, Optional, Tuple
from pyfasm.ast_parser import ParsedModule, FunctionSymbol, VariableSymbol, StringLiteral
from pyfasm.types import TYPE_INT, TYPE_FLOAT, TYPE_STR


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

    def generate(self) -> str:
        self.lines = []

        # 1. Target Header
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_header
            self.emit_raw(get_win64_runtime_header(is_dll=(self.target == "dll")))
        elif self.target == "linux":
            from pyfasm.runtime_linux import get_linux_runtime_header
            self.emit_raw(get_linux_runtime_header())
        elif self.target in ("macos", "apple"):
            from pyfasm.runtime_macos import get_macos_runtime_header
            self.emit_raw(get_macos_runtime_header())
        else:
            from pyfasm.runtime_myos import get_myos_runtime_header
            self.emit_raw(get_myos_runtime_header())

        # 2. Data Section (String literals and global data)
        self._generate_data_section()

        # 3. Text Section (Entry point and user functions)
        self._generate_text_section()

        # 4. Runtime Routines and Exports
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_code, get_win64_runtime_imports, get_win64_export_section
            self.emit_raw(get_win64_runtime_code())
            if self.target == "dll":
                fn_names = list(self.module.functions.keys())
                self.emit_raw(get_win64_export_section("pyfasm_module.dll", fn_names))
            self.emit_raw(get_win64_runtime_imports())
        elif self.target == "linux":
            from pyfasm.runtime_linux import get_linux_runtime_code
            self.emit_raw(get_linux_runtime_code())
        elif self.target in ("macos", "apple"):
            from pyfasm.runtime_macos import get_macos_runtime_code
            self.emit_raw(get_macos_runtime_code())
        else:
            from pyfasm.runtime_myos import get_myos_runtime_code
            self.emit_raw(get_myos_runtime_code())

        return "\n".join(self.lines)

    def _generate_data_section(self) -> None:
        if self.target in ("win64", "dll"):
            from pyfasm.runtime_win64 import get_win64_runtime_data
            self.emit_raw(get_win64_runtime_data())
        elif self.target == "linux":
            from pyfasm.runtime_linux import get_linux_runtime_data
            self.emit_raw(get_linux_runtime_data())
        elif self.target in ("macos", "apple"):
            from pyfasm.runtime_macos import get_macos_runtime_data
            self.emit_raw(get_macos_runtime_data())
        else:
            from pyfasm.runtime_myos import get_myos_runtime_data
            self.emit_raw(get_myos_runtime_data())

        # Emit user string literals
        for slit in self.module.string_literals:
            # Escape characters for FASM
            escaped_bytes = []
            for b in slit.value.encode("utf-8"):
                escaped_bytes.append(str(b))
            escaped_bytes.append("0")  # null terminator
            bytes_str = ", ".join(escaped_bytes)
            self.emit_raw(f"    {slit.label} db {bytes_str}")

        # Emit user float literals
        for flit in self.module.float_literals:
            self.emit_raw(f"    {flit.label} dq {flit.value}")

        self.emit_raw("")

    def _generate_text_section(self) -> None:
        if self.target in ("win64", "dll"):
            self.emit_raw("section '.text' code readable executable")
        elif self.target == "linux":
            self.emit_raw("segment readable executable")
        elif self.target in ("macos", "apple"):
            self.emit_raw("align 16")
        else:
            self.emit_raw("align 16")
        self.emit_raw("")

        if self.target == "dll":
            from pyfasm.runtime_win64 import get_win64_dll_entry
            self.emit_raw(get_win64_dll_entry())
        else:
            # Global Entry Point
            self.emit_raw("_pyfasm_entry_point:")
            self.emit("push rbp")
            self.emit("mov rbp, rsp")
            self.emit("sub rsp, 32", "shadow/local frame")
            self.emit("and rsp, -16", "16-byte stack alignment")
            self.emit("call _pyfasm_init_io", "initialize runtime I/O")

            if self.module.main_func:
                self.emit("call main", "execute user main()")
                self.emit("mov ecx, eax", "exit code in ecx (Windows)")
                self.emit("mov edi, eax", "exit code in edi (Linux/macOS)")
            else:
                self.emit("xor ecx, ecx", "exit code 0")
                self.emit("xor edi, edi", "exit code 0")

            if self.target == "win64":
                self.emit("call [ExitProcess]")
            elif self.target == "linux":
                self.emit("mov rax, 60", "sys_exit")
                self.emit("syscall")
            elif self.target in ("macos", "apple"):
                self.emit("mov rax, 0x2000001", "Darwin sys_exit")
                self.emit("syscall")
            else:
                self.emit("mov rsp, rbp")
                self.emit("pop rbp")
                self.emit("ret")

        self.emit_raw("")

        # Generate User Functions (group aliases)
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
            self._generate_function(fn, aliases=names)

    def _generate_function(self, fn: FunctionSymbol, aliases: Optional[List[str]] = None) -> None:
        self.current_func = fn
        self.emit_raw("; ============================================================")
        self.emit_raw(f"; Function: {fn.name}")
        self.emit_raw("; ============================================================")
        if aliases:
            for alias in aliases:
                self.emit_raw(f"{alias}:")
        else:
            self.emit_raw(f"{fn.name}:")

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
        if fn.ast_node:
            for stmt in fn.ast_node.body:
                self._generate_statement(stmt)

        # Epilog
        self.emit_raw(f".epilog_{fn.name}:")
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
            self.emit(f"jmp .epilog_{self.current_func.name}")

        elif isinstance(stmt, ast.Assign):
            # Target = Expr
            self._generate_expr(stmt.value)  # result in RAX
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
            if isinstance(expr.value, int):
                self.emit(f"mov rax, {expr.value}")
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
            elif isinstance(expr.value, bool):
                self.emit(f"mov rax, {1 if expr.value else 0}")
            elif expr.value is None:
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
            var = self.current_func.local_vars.get(expr.id)
            if var:
                self.emit(f"mov rax, [rbp - {var.stack_offset}]", f"load {var.name}")
            else:
                # Could be global function pointer
                self.emit(f"lea rax, [{expr.id}]", f"address of {expr.id}")

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
        func_name = ""
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            attr_name = call.func.attr
            if isinstance(call.func.value, ast.Name):
                prefix = call.func.value.id
                if f"{prefix}_{attr_name}" in self.module.functions:
                    func_name = f"{prefix}_{attr_name}"
                elif attr_name in self.module.functions:
                    func_name = attr_name
                else:
                    func_name = f"{prefix}_{attr_name}"
            else:
                func_name = attr_name

        # Built-in runtime calls
        if func_name in ("print", "print_int"):
            if call.args:
                self._generate_expr(call.args[0])
                self.emit("mov rcx, rax")
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

        # User Function Call (x64 ABI)
        # Evaluate arguments and push them in reverse order
        for arg in reversed(call.args):
            self._generate_expr(arg)
            self.emit("push rax")

        # Pop into register parameters
        arg_regs = ["rcx", "rdx", "r8", "r9"]
        n_args = len(call.args)
        for i in range(min(n_args, 4)):
            self.emit(f"pop {arg_regs[i]}")

        # Allocate 32 bytes shadow space
        self.emit("sub rsp, 32", "shadow space for callee")
        self.emit(f"call {func_name}")
        self.emit("add rsp, 32", "restore shadow space")

        # If more than 4 arguments, cleanup extra stack args
        if n_args > 4:
            extra_bytes = (n_args - 4) * 8
            self.emit(f"add rsp, {extra_bytes}", "cleanup stack args")
