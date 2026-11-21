"""PyFASM Example 11: Python 3.14 & 3.15 Language Features
Demonstrates dynamic Python environment version detection, PEP 695 type aliases,
generic type parameters, math.sumprod, itertools.batched, and OS CPU detection.

Compile with:
    pyfasm64 compile examples/11_python314_315_features.py -o 11_python314_315_features.exe
"""

import sys
import math
import itertools
import os

# 1. PEP 695 / Python 3.12+ TypeAlias
type Vector = list[int]
type Matrix = list[list[int]]

# 2. Generic function with type parameter
def identity[T](val: T) -> T:
    return val


def main():
    print("================================================================")
    print("  PyFASM Native Python 3.14 & 3.15 Feature Suite")
    print("================================================================")

    # Automatic environment version detection
    print(f"Detected Runtime : {sys.version}")
    print(f"Version Tuple    : ({sys.version_info.major}, {sys.version_info.minor}, {sys.version_info.micro})")
    print(f"Target Platform  : {sys.platform} (Byteorder: {sys.byteorder})")

    # Conditional compilation / version branch folding
    if sys.version_info >= (3, 14):
        print("Active Target    : Python 3.14+ / 3.15 Modern Execution Mode")
    else:
        print("Active Target    : Backward-Compatible Legacy Python Mode")

    # PEP 695 TypeAlias in action
    vec: Vector = [10, 20, 30, 40]
    print(f"Vector elements  : {len(vec)}")

    # Python 3.12+ / 3.14+ math.sumprod (Vectorized Dot Product)
    weights = [2, 3, 4, 5]
    dot_product = math.sumprod(vec, weights)
    print(f"math.sumprod     : {dot_product} (10*2 + 20*3 + 30*4 + 40*5)")

    # Python 3.12+ / 3.14+ itertools.batched
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    batches = itertools.batched(data, 3)
    print(f"itertools.batched: {len(batches)} batches from 10 elements")

    # os.cpu_count / process_cpu_count
    cpus = os.cpu_count()
    print(f"Logical CPU Cores: {cpus}")
    return 0


if __name__ == "__main__":
    main()
