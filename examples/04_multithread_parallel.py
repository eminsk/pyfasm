def worker(counter_ptr: int) -> int:
    # 250,000 atomic increments per thread without GIL
    for i in range(250000):
        atomic_add(counter_ptr, 1)
    return 0

def main() -> int:
    print_str("=====================================================\n")
    print_str("  PyFASM True Multi-Threading Benchmark (No-GIL)\n")
    print_str("=====================================================\n")
    print_str("Spawning 8 native OS threads across CPU cores...\n")

    counter = alloc_memory(64)
    counter[0] = 0

    t0 = get_tick_count()

    t1 = spawn_thread(worker, counter)
    t2 = spawn_thread(worker, counter)
    t3 = spawn_thread(worker, counter)
    t4 = spawn_thread(worker, counter)
    t5 = spawn_thread(worker, counter)
    t6 = spawn_thread(worker, counter)
    t7 = spawn_thread(worker, counter)
    t8 = spawn_thread(worker, counter)

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
    print_str("Expected count: 2000000 (8 x 250,000)\n")
    print_str("Actual count:   ")
    print_int(total)
    print_newline()

    print_str("Elapsed time (ms): ")
    print_int(t1_end - t0)
    print_newline()

    free_memory(counter)
    return 0
