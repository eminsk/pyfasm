"""PyFASM Example 08: Native Data Structures & Strings
Demonstrates native hash dictionaries, dynamic lists, sets, and string operations.
"""

def main():
    print("================================================================")
    print("  PyFASM Native Data Structures (Hash Maps, Lists, Strings)")
    print("================================================================")

    # 1. Dictionary / Hash Table
    inventory = {"cpu": 16, "ram_gb": 64, "nvme_tb": 2}
    print(f"Inventory items count: {len(inventory)}")
    print(f"RAM installed: {inventory.get('ram_gb', 0)} GB")

    # 2. String manipulation
    tags = ["PyFASM", "Native", "x86-64", "Ahead-of-Time"]
    pipeline = " -> ".join(tags)
    print(f"Joined pipeline: {pipeline}")

    modified = pipeline.replace("Ahead-of-Time", "Zero-VM")
    print(f"Replaced string: {modified}")

    # 3. Dynamic lists and slicing
    nums = [10, 20, 30, 40, 50]
    total = sum(nums)
    print(f"Sum of numbers: {total}")
    return 0


if __name__ == "__main__":
    main()
