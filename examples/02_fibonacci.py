def fib(n: int) -> int:
    if n <= 1:
        return n
    a = 0
    b = 1
    for i in range(2, n + 1):
        c = a + b
        a = b
        b = c
    return b

def main() -> int:
    print_str("Computing Fibonacci sequence up to N = 40 in native x64...\n")
    t0 = get_tick_count()
    ans = fib(40)
    t1 = get_tick_count()

    print_str("Fib(40) = ")
    print_int(ans)
    print_newline()

    print_str("Elapsed time (ms): ")
    print_int(t1 - t0)
    print_newline()
    return 0
