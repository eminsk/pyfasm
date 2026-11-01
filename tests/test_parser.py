import pytest
from pyfasm.ast_parser import AstAnalyzer


def test_parser_functions_and_variables():
    source = """
def add(a: int, b: int) -> int:
    result = a + b
    return result

def main() -> int:
    msg: str = "Test String"
    x = add(10, 20)
    return x
"""
    analyzer = AstAnalyzer()
    mod = analyzer.parse_source(source)

    assert "add" in mod.functions
    assert "main" in mod.functions

    fn_add = mod.functions["add"]
    assert len(fn_add.args) == 2
    assert fn_add.args[0].name == "a"
    assert fn_add.args[1].name == "b"
    assert "result" in fn_add.local_vars

    fn_main = mod.functions["main"]
    assert mod.main_func == fn_main
    assert len(mod.string_literals) == 1
    assert mod.string_literals[0].value == "Test String"
