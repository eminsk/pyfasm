"""PyFASM Example 02: High-Performance Fibonacci
Demonstrates native 64-bit iterative computation and timer benchmarking.
"""

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


def main():
    print("================================================================")
    print("  PyFASM Fibonacci Benchmark (Native x86-64)")
    print("================================================================")
    print("Calculating Fib(45) in native CPU registers...")

    t0 = get_tick_count()
    ans = fib(45)
    t1 = get_tick_count()

    print(f"Fib(45) = {ans}")
    print(f"Elapsed time: {t1 - t0} ms")
    return 0


if __name__ == "__main__":
    main()
