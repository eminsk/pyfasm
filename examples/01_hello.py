def main() -> int:
    print_str("Hello from PyFASM: Pure Native x64 Assembly without GIL!\n")
    print_str("Computing basic arithmetic: (100 * 25) / 5 + 42 = ")
    ans = (100 * 25) // 5 + 42
    print_int(ans)
    print_newline()
    return 0
