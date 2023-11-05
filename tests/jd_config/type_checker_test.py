#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
import logging
from pathlib import Path

from typing import Annotated, Any, ForwardRef, List, Mapping, Optional, Sequence

import pytest

from jd_config.type_checker import TypeChecker

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def my_strptime(fmt):
    def inner_strptime(expected_type, value):
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
    assert tc.instanceof("99", int).value == 99
    assert tc.instanceof(99, str).value == "99"
    assert tc.instanceof("1.1", float).value == 1.1
    assert tc.instanceof("c:/temp", Path).value == Path("c:/temp")
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
