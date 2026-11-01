def main() -> int:
    limit = 100000
    print_str("Sieve of Eratosthenes up to ")
    print_int(limit)
    print_str(" in native x64 memory buffer...\n")

    t0 = get_tick_count()

    # Allocate limit * 8 bytes
    sieve = alloc_memory(limit * 8)

    # Initialize all as prime (1)
    for i in range(limit):
        sieve[i] = 1

    sieve[0] = 0
    sieve[1] = 0

    p = 2
    while p * p < limit:
        if sieve[p] == 1:
            multiple = p * p
            while multiple < limit:
                sieve[multiple] = 0
                multiple = multiple + p
        p = p + 1

    # Count total primes
    primes_count = 0
    for i in range(limit):
        if sieve[i] == 1:
            primes_count = primes_count + 1

    t1 = get_tick_count()

    print_str("Total prime numbers found: ")
    print_int(primes_count)
    print_newline()

    print_str("Computation time (ms): ")
    print_int(t1 - t0)
    print_newline()

    free_memory(sieve)
    return 0
