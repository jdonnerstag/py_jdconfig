#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
import logging
from pathlib import Path

from typing import Annotated, Any, ForwardRef, List, Mapping, Sequence, TypedDict, Union

import pytest

from jd_config.type_checker import TypeChecker

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def my_strptime(fmt):
    def inner_strptime(_expected_type, value):
        return datetime.strptime(value, fmt)

    return inner_strptime


@dataclass
class A:
    a: str
    b: str
    c: str


def test_simple():
    tc = TypeChecker()
    assert tc.instanceof("a", str) == True  # __eq__
    assert tc.instanceof(1, int)  # __bool__
    assert tc.instanceof(1.1, float)
    assert tc.instanceof(True, bool)
    assert tc.instanceof(Path("c:/temp"), Path)
    assert tc.instanceof(Decimal(1.1), Decimal)
    assert tc.instanceof(A("a", "b", "c"), A)


def test_simple_converter():
    tc = TypeChecker()
    assert tc.instanceof("99", int) == False
    assert tc.instanceof("99", int, True).value == 99
    assert tc.instanceof(99, str, True).value == "99"
    assert tc.instanceof("1.1", float, True).value == 1.1
    assert tc.instanceof("c:/temp", Path, True).value == Path("c:/temp")
    assert tc.instanceof(Decimal(1.1), Decimal)

    # TODO Can we try-auto-convert "2023-11..." to Date, Datetime ..?
    assert tc.instanceof(
        "2023-11-01", datetime, my_strptime("%Y-%m-%d")
    ).value == datetime(2023, 11, 1)

    assert tc.instanceof("aa", int) == False


def test_simple_list():
    tc = TypeChecker()
    assert tc.instanceof(["a"], list)
    assert tc.instanceof(("a",), tuple)
    assert tc.instanceof(["a"], List)
    assert tc.instanceof(["a"], Sequence)
    assert tc.instanceof([], list)


def test_simple_dict():
    tc = TypeChecker()
    assert tc.instanceof({"a": "aa"}, dict)
    assert tc.instanceof(dict(a="aa"), dict)
    assert tc.instanceof(dict(a="aa"), Mapping)
    assert tc.instanceof({}, Mapping)


def test_Any():
    tc = TypeChecker()
    assert tc.instanceof("a", Any)
    assert tc.instanceof(int, Any)
    assert tc.instanceof(None, Any)
    assert tc.instanceof(["a"], Any)
    assert tc.instanceof({"a": 99}, Any)


def test_None():
    tc = TypeChecker()
    assert tc.instanceof(None, None)
    assert tc.instanceof(0, None) == False
    assert tc.instanceof([], None) == False


def test_simple_union():
    tc = TypeChecker()
    assert tc.instanceof("a", str | int)
    assert tc.instanceof("a", str | int).type_ == str

    assert tc.instanceof(99, str | int)
    assert tc.instanceof(99, str | int).type_ == int

    assert tc.instanceof(None, str | int) == False
    assert tc.instanceof(1.111, str | int) == False
    assert tc.instanceof(1.111, str | int, True) == True  # will be auto-converted
    assert (
        tc.instanceof(1.111, str | int, True).value == "1.111"
    )  # will be auto-converted
    assert tc.instanceof(1.111, int | str, True).value == 1  # will be auto-converted
    assert tc.instanceof(Path("c:/temp"), str | int) == False


def test_union():
    tc = TypeChecker()
    assert tc.instanceof("a", Union[str, int])
    assert tc.instanceof("a", Union[str, int]).type_ == str

    assert tc.instanceof(99, Union[str, int])
    assert tc.instanceof(99, Union[str, int]).type_ == int

    assert tc.instanceof(None, Union[str, int]) == False
    assert tc.instanceof(1.111, Union[str, int]) == False
    assert tc.instanceof(1.111, Union[str, int], True) == True  # will be auto-converted
    assert (
        tc.instanceof(1.111, Union[str, int], True).value == "1.111"
    )  # will be auto-converted
    assert (
        tc.instanceof(1.111, Union[int, str], True).value == 1
    )  # will be auto-converted
    assert tc.instanceof(Path("c:/temp"), Union[str, int]) == False


def test_tuple_type_param():
    tc = TypeChecker()
    assert tc.instanceof("a", (str, int))
    assert tc.instanceof("a", (str, int)).type_ == str

    assert tc.instanceof(99, (str, int))
    assert tc.instanceof(99, (str, int)).type_ == int

    assert tc.instanceof(None, (str, int)) == False
    assert tc.instanceof(1.111, (str, int)) == False
    assert tc.instanceof(1.111, (str, int), True) == True  # will be auto-converted
    assert (
        tc.instanceof(1.111, (str, int), True).value == "1.111"
    )  # will be auto-converted
    assert tc.instanceof(1.111, (int, str), True).value == 1  # will be auto-converted
    assert tc.instanceof(Path("c:/temp"), (str, int)) == False


def test_generic_list():
    tc = TypeChecker()
    assert tc.instanceof(["a"], list[str])
    assert tc.instanceof(["a"], list[int]) == False
    assert tc.instanceof(["a"], list[int | str])
    # We evaluate the types adjust the type
    # TODO assert tc.instanceof(["a"], list[int | str]).type_ == list[str]
    assert tc.instanceof(["a", 99], list[int | str])
    assert tc.instanceof(["a"], list[Any])
    assert tc.instanceof(["a", 99], list[str], True).value == ["a", "99"]


def test_generic_dict():
    tc = TypeChecker()
    assert tc.instanceof(dict(a="a"), dict[str, str])
    assert tc.instanceof(dict(a="a"), dict[str, int]) == False
    assert tc.instanceof(dict(a="a"), dict[int, str]) == False
    assert tc.instanceof(dict(a="a"), dict[str, str | int])
    assert tc.instanceof(dict(a=99), dict[str, str | int])

    assert tc.instanceof(dict(a=99), dict[str, str], True).value == dict(a="99")


def test_annotated_types():
    tc = TypeChecker()
    assert tc.instanceof("a", Annotated[str, str.upper])
    assert tc.instanceof("a", Annotated[str, str.upper]).type_ == str

    # This annotation will convert the value to str(value)
    assert tc.instanceof(99, Annotated[str, str]).value == "99"
    # upper(int) will raise an exception => False
    assert tc.instanceof(99, Annotated[str, str.upper]) == False
    assert tc.instanceof("a", Annotated[str, str.upper], True).value == "A"

class B(TypedDict):
    a: str

def test_typed_dict():
    tc = TypeChecker()
    assert tc.instanceof(dict(a="a"), B)
    assert tc.instanceof(dict(a=99), B) == False


def test_type_alias():
    tc = TypeChecker()
