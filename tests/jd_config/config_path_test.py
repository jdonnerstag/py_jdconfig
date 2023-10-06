#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

import logging
from jd_config import ConfigPath, ConfigException
import pytest

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_normalize_path():
    normalize = ConfigPath().normalize_path

    assert normalize("") == []
    assert normalize("a", sep=".") == ["a"]
    assert normalize(["a"], sep=".") == ["a"]
    assert normalize(["a[1]"], sep=".") == ["a", 1]
    assert normalize(["a[1][2]"], sep=".") == ["a", 1, 2]
    assert normalize("a.b.c", sep=".") == ["a", "b", "c"]
    assert normalize("a[1].b", sep=".") == ["a", 1, "b"]
    assert normalize("a/b/c", sep="/") == ["a", "b", "c"]
    assert normalize("a/b[1]/c", sep="/") == ["a", "b", 1, "c"]
    assert normalize(["a", "b", "c"]) == ["a", "b", "c"]
    assert normalize(("a", "b.c")) == ["a", "b", "c"]
    assert normalize(("a", ("b", "c"))) == ["a", "b", "c"]
    assert normalize(("a", ("b.c"))) == ["a", "b", "c"]
    assert normalize("[1]") == [1]
    assert normalize("222[1]") == ["222", 1]
    assert normalize("a.*.c") == ["a", "*", "c"]
    assert normalize("a.b[*].c") == ["a", "b", "%", "c"]
    assert normalize("a..c") == ["a", "", "c"]
    assert normalize("a...c") == ["a", "", "c"]
    assert normalize("a.*.*.c") == ["a", "*", "*", "c"]
    assert normalize("a.*..c") == ["a", "", "c"]  # same as "a..c"
    assert normalize("a..*.c") == ["a", "", "c"]  # same as "a..c"
    assert normalize("a[*]..c") == ["a", "", "c"]  # same as "a..c"
    assert normalize("..c") == ["", "c"]
    assert normalize("*.c") == ["*", "c"]

    should_fail = ["a[1", "a[a]", "a]1]", "a[1[", "a[", "a]", "a[]", "a..", "a.*"]

    for elem in should_fail:
        with pytest.raises(ConfigException):
            normalize(elem)


def test_path_to_str():
    cg = ConfigPath()

    def to_str(x, sep="."):
        p = cg.normalize_path(x, sep=sep)
        return cg.normalized_path_to_str(p, sep=sep)

    assert to_str("") == ""
    assert to_str("a") == "a"
    assert to_str(["a"]) == "a"
    assert to_str(["a[1]"]) == "a[1]"
    assert to_str(["a[1][2]"]) == "a[1][2]"
    assert to_str("a.b.c") == "a.b.c"
    assert to_str("a[1].b") == "a[1].b"
    assert to_str("a/b/c", sep="/") == "a/b/c"
    assert to_str("a/b[1]/c", sep="/") == "a/b[1]/c"
    assert to_str(["a", "b", "c"]) == "a.b.c"
    assert to_str(("a", "b.c")) == "a.b.c"
    assert to_str(("a", ("b", "c"))) == "a.b.c"
    assert to_str(("a", ("b.c"))) == "a.b.c"
    assert to_str("[1]") == "[1]"
    assert to_str("222[1]") == "222[1]"
    assert to_str("a.*.c") == "a.*.c"
    assert to_str("a.b[*].c") == "a.b[*].c"
    assert to_str("a..c") == "a..c"
    assert to_str("a...c") == "a..c"
    assert to_str("a.*.*.c") == "a.*.*.c"
    assert to_str("a.*..c") == "a..c"  # ".*.." == ".."
    assert to_str("a..*.c") == "a..c"  # "..*." == ".."
    assert to_str("a[*]..c") == "a..c"  # "[*].." == ".."
    assert to_str("..c") == "..c"
    assert to_str("*.c") == "*.c"
