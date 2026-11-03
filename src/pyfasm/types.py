"""
Type definitions and annotations for the PyFASM compiler.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any


class PyFasmType:
    """Base class for all PyFASM supported types."""
    name: str = "void"
    size_bytes: int = 0

    def is_int(self) -> bool:
        return isinstance(self, IntType)

    def is_float(self) -> bool:
        return isinstance(self, FloatType)

    def is_bool(self) -> bool:
        return isinstance(self, BoolType)

    def is_str(self) -> bool:
        return isinstance(self, StrType)

    def is_ptr(self) -> bool:
        return isinstance(self, PtrType)

    def is_list(self) -> bool:
        return isinstance(self, ListType)

    def is_dict(self) -> bool:
        return isinstance(self, DictType)

    def is_set(self) -> bool:
        return isinstance(self, SetType)

    def is_tuple(self) -> bool:
        return isinstance(self, TupleType)

    def is_void(self) -> bool:
        return isinstance(self, VoidType)

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class IntType(PyFasmType):
    name: str = "int"
    size_bytes: int = 8  # 64-bit signed integer


@dataclass(frozen=True)
class FloatType(PyFasmType):
    name: str = "float"
    size_bytes: int = 8  # 64-bit double precision float (SSE)


@dataclass(frozen=True)
class BoolType(PyFasmType):
    name: str = "bool"
    size_bytes: int = 8  # 64-bit boolean (0 or 1)


@dataclass(frozen=True)
class StrType(PyFasmType):
    name: str = "str"
    size_bytes: int = 8  # Pointer to null-terminated ASCII/UTF-8 buffer


@dataclass(frozen=True)
class PtrType(PyFasmType):
    name: str = "ptr"
    element_type: Optional[PyFasmType] = None
    size_bytes: int = 8  # 64-bit raw pointer/buffer


@dataclass(frozen=True)
class ListType(PyFasmType):
    name: str = "list"
    element_type: Optional[PyFasmType] = None
    size_bytes: int = 8  # Pointer to heap list descriptor


@dataclass(frozen=True)
class DictType(PyFasmType):
    name: str = "dict"
    key_type: Optional[PyFasmType] = None
    val_type: Optional[PyFasmType] = None
    size_bytes: int = 8  # Pointer to heap hash table descriptor


@dataclass(frozen=True)
class SetType(PyFasmType):
    name: str = "set"
    element_type: Optional[PyFasmType] = None
    size_bytes: int = 8  # Pointer to heap hash set descriptor


@dataclass(frozen=True)
class TupleType(PyFasmType):
    name: str = "tuple"
    size_bytes: int = 8  # Pointer to heap tuple descriptor


@dataclass(frozen=True)
class InstanceType(PyFasmType):
    name: str = "object"
    class_name: Optional[str] = None
    size_bytes: int = 8  # Pointer to heap object instance


@dataclass(frozen=True)
class VoidType(PyFasmType):
    name: str = "void"
    size_bytes: int = 0


# Singletons
TYPE_INT = IntType()
TYPE_FLOAT = FloatType()
TYPE_BOOL = BoolType()
TYPE_STR = StrType()
TYPE_PTR = PtrType()
TYPE_LIST = ListType()
TYPE_DICT = DictType()
TYPE_SET = SetType()
TYPE_TUPLE = TupleType()
TYPE_VOID = VoidType()


def resolve_type(type_name: Optional[str]) -> PyFasmType:
    """Resolves a Python type annotation string into a PyFasmType."""
    if not type_name:
        return TYPE_INT  # Default to 64-bit integer if unannotated
    norm = type_name.strip().lower()
    if norm in ("int", "i64", "long"):
        return TYPE_INT
    if norm in ("float", "f64", "double"):
        return TYPE_FLOAT
    if norm in ("bool", "boolean"):
        return TYPE_BOOL
    if norm in ("str", "string"):
        return TYPE_STR
    if norm in ("ptr", "pointer", "array", "buffer"):
        return TYPE_PTR
    if norm in ("list", "seq", "sequence"):
        return TYPE_LIST
    if norm in ("dict", "map", "mapping"):
        return TYPE_DICT
    if norm in ("set", "hashset"):
        return TYPE_SET
    if norm in ("tuple",):
        return TYPE_TUPLE
    if norm in ("none", "void"):
        return TYPE_VOID
    return TYPE_INT
