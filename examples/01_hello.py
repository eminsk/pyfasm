"""PyFASM Example 01: Hello Native World
Compiles standard Python into a standalone native x86-64 PE executable with zero runtime dependencies.
"""

def main():
    print("================================================================")
    print("  PyFASM v1.1.0: Pure Native Machine Code (No GIL, No Python VM)")
    print("================================================================")
    
    # Basic arithmetic and variables
    a = 100
    b = 25
    c = 5
    d = 42
    ans = (a * b) // c + d
    
    print(f"Computed in native CPU registers: ({a} * {b}) // {c} + {d} = {ans}")
    print("Execution completed successfully.")
    return 0


if __name__ == "__main__":
    main()
