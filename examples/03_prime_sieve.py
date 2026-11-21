"""PyFASM Example 03: Prime Sieve (Sieve of Eratosthenes)
Demonstrates low-level memory allocation, direct pointer buffer indexing, and algorithmic speed.
"""

def main():
    limit = 100000
    print("================================================================")
    print("  PyFASM Sieve of Eratosthenes (Direct Native Memory)")
    print("================================================================")
    print(f"Finding primes up to {limit}...")

    t0 = get_tick_count()

    # Allocate native 64-bit word buffer
    sieve = alloc_memory(limit * 8)

    # Initialize all numbers as prime (1)
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

    print(f"Total prime numbers found: {primes_count}")
    print(f"Computation time: {t1 - t0} ms")

    free_memory(sieve)
    return 0


if __name__ == "__main__":
    main()
