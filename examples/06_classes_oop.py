"""PyFASM Example 06: Object-Oriented Programming (OOP)
Demonstrates classes, methods, inheritance, and polymorphism compiled directly to native machine code.
"""

class Shape:
    def __init__(self, name: str):
        self.name = name

    def area(self) -> int:
        return 0

    def describe(self) -> str:
        return f"Shape '{self.name}' with area {self.area()}"


class Rectangle(Shape):
    def __init__(self, width: int, height: int):
        super().__init__("Rectangle")
        self.width = width
        self.height = height

    def area(self) -> int:
        return self.width * self.height


class Square(Rectangle):
    def __init__(self, side: int):
        super().__init__(side, side)
        self.name = "Square"


def main():
    print("================================================================")
    print("  PyFASM OOP & Polymorphism Demo (Native x86-64)")
    print("================================================================")

    r = Rectangle(10, 20)
    print(r.describe())

    s = Square(15)
    print(s.describe())
    return 0


if __name__ == "__main__":
    main()
