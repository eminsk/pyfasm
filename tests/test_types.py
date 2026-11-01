import pytest
from pyfasm.types import resolve_type, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_STR, TYPE_PTR, TYPE_VOID


def test_resolve_types():
    assert resolve_type("int") == TYPE_INT
    assert resolve_type("i64") == TYPE_INT
    assert resolve_type("float") == TYPE_FLOAT
    assert resolve_type("bool") == TYPE_BOOL
    assert resolve_type("str") == TYPE_STR
    assert resolve_type("ptr") == TYPE_PTR
    assert resolve_type("void") == TYPE_VOID
    assert resolve_type(None) == TYPE_INT  # default
