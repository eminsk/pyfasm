"""
Assembly Peephole Optimizer for PyFASM.
Implements multi-pass instruction pipeline optimizations inspired by pyast64 and minijit.
Eliminates redundant stack push/pop sequences, self-moves, and dead code with strict
thread-safety and memory ordering guards.
"""
from __future__ import annotations
import re
from typing import List, Set

X64_64BIT_REGS: Set[str] = {
    "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
}


class PeepholeOptimizer:
    """Optimizes emitted x86-64 FASM assembly text with thread-safe guards."""

    def __init__(self):
        self.passes_run = 0

    def optimize(self, asm_text: str) -> str:
        lines = asm_text.splitlines()
        optimized = lines
        for _ in range(3):  # Run up to 3 passes until convergence
            prev_len = len(optimized)
            optimized = self._optimize_pass(optimized)
            if len(optimized) == prev_len:
                break
        return "\n".join(optimized)

    def _optimize_pass(self, lines: List[str]) -> List[str]:
        result: List[str] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # Pass through labels, comments, directives, empty lines
            if not stripped or stripped.startswith(";") or stripped.endswith(":") or stripped.startswith("format") or stripped.startswith("section") or stripped.startswith("entry"):
                result.append(line)
                i += 1
                continue

            # Thread safety barrier: lock prefixes, memory fences, bus-locked atomic operations
            if any(stripped.lower().startswith(b) for b in ("lock ", "mfence", "sfence", "lfence", "pause")):
                result.append(line)
                i += 1
                continue

            # Parse instruction opcode and arguments
            match = re.match(r'^\s*([a-zA-Z0-9_\.]+)(?:\s+(.*?))?(?:\s*;.*)?$', line)
            if not match:
                result.append(line)
                i += 1
                continue

            op = match.group(1).lower()
            args_str = match.group(2) or ""
            args = [a.strip() for a in args_str.split(",")] if args_str else []

            # 1. Eliminate redundant self-moves: mov reg, reg
            # CRITICAL ABI/Thread Guard: Only valid for full 64-bit registers!
            # 32-bit `mov eax, eax` zeroes upper 32 bits and MUST be preserved!
            if op == "mov" and len(args) == 2 and args[0].lower() == args[1].lower():
                if args[0].lower() in X64_64BIT_REGS:
                    i += 1
                    continue

            # 2. Eliminate redundant add/sub by 0
            if op in ("add", "sub") and len(args) == 2 and args[1] in ("0", "0h", "$0"):
                i += 1
                continue

            # Look ahead to next non-comment line
            next_idx = i + 1
            while next_idx < n and (not lines[next_idx].strip() or lines[next_idx].strip().startswith(";")):
                next_idx += 1

            if next_idx < n:
                next_line = lines[next_idx]
                next_stripped = next_line.strip()

                # If next line is a memory barrier, do not optimize across it!
                if any(next_stripped.lower().startswith(b) for b in ("lock ", "mfence", "sfence", "lfence", "pause")):
                    result.append(line)
                    i += 1
                    continue

                # 3. Eliminate redundant jmp to next immediate label:
                if op in ("jmp", "jmp short") and len(args) == 1:
                    target_label = args[0]
                    if next_stripped == f"{target_label}:":
                        i = next_idx
                        continue

                next_match = re.match(r'^\s*([a-zA-Z0-9_\.]+)(?:\s+(.*?))?(?:\s*;.*)?$', next_line)
                if next_match:
                    next_op = next_match.group(1).lower()
                    next_args_str = next_match.group(2) or ""
                    next_args = [a.strip() for a in next_args_str.split(",")] if next_args_str else []

                    # 4. Collapse push X; pop Y
                    if op == "push" and next_op == "pop" and len(args) == 1 and len(next_args) == 1:
                        push_arg = args[0]
                        pop_arg = next_args[0]
                        indent = "    "
                        if push_arg.lower() == pop_arg.lower():
                            # push rax; pop rax -> eliminated entirely
                            i = next_idx + 1
                            continue
                        else:
                            # push rdx; pop rax -> mov rax, rdx
                            result.append(f"{indent}mov {pop_arg}, {push_arg} ; optimized push/pop")
                            i = next_idx + 1
                            continue

                    # 5. Eliminate redundant write then immediate read from stack:
                    # mov [rbp - X], rax
                    # mov rax, [rbp - X] -> second is redundant ONLY for private local stack frames!
                    if op == "mov" and next_op == "mov" and len(args) == 2 and len(next_args) == 2:
                        dst1, src1 = args[0].lower(), args[1].lower()
                        dst2, src2 = next_args[0].lower(), next_args[1].lower()
                        if dst1 == src2 and src1 == dst2:
                            # Thread Safety: ONLY eliminate for thread-private stack variables:
                            # [rbp - ...] or [rsp + ...].
                            # NEVER eliminate for heap memory ([rcx]), globals ([rel ...]), or shared memory!
                            if dst1.startswith("[rbp -") or dst1.startswith("[rsp +"):
                                result.append(line)
                                i = next_idx + 1
                                continue

            result.append(line)
            i += 1

        return result


def optimize_fasm_code(asm_code: str) -> str:
    """Convenience helper to run peephole optimization on FASM code."""
    opt = PeepholeOptimizer()
    return opt.optimize(asm_code)
