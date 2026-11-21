"""PyFASM Example 04: True Multi-Threading (No-GIL Concurrency)
Demonstrates spawning 8 native OS threads across CPU cores with lock-free atomic increments.
"""

def worker(counter_ptr: int) -> int:
    # 250,000 atomic increments per thread without GIL interference
    for i in range(250000):
        atomic_add(counter_ptr, 1)
    return 0


def main():
    print("================================================================")
    print("  PyFASM True Multi-Threading Benchmark (Native OS Threads)")
    print("================================================================")
    print("Spawning 8 native OS threads across CPU cores...")

    # Allocate shared counter memory
    counter = alloc_memory(64)
    counter[0] = 0

    t0 = get_tick_count()

    # Launch 8 worker threads
    t1 = spawn_thread(worker, counter)
    t2 = spawn_thread(worker, counter)
    t3 = spawn_thread(worker, counter)
    t4 = spawn_thread(worker, counter)
    t5 = spawn_thread(worker, counter)
    t6 = spawn_thread(worker, counter)
    t7 = spawn_thread(worker, counter)
    t8 = spawn_thread(worker, counter)

    # Wait for all threads to terminate
    wait_thread(t1)
    wait_thread(t2)
    wait_thread(t3)
    wait_thread(t4)
    wait_thread(t5)
    wait_thread(t6)
    wait_thread(t7)
    wait_thread(t8)

    t1_end = get_tick_count()

    total = counter[0]
    print("Expected count: 2000000 (8 x 250,000)")
    print(f"Actual count:   {total}")
    print(f"Elapsed time:   {t1_end - t0} ms")

    free_memory(counter)
    return 0


if __name__ == "__main__":
    main()
