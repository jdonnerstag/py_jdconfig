#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

import logging

import pytest

from jd_config import ConfigException, CfgPath

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_path():
    cfg = CfgPath()
    assert cfg == []
    assert CfgPath("") == []
    assert CfgPath("a", sep=".") == ["a"]
    assert CfgPath(["a"], sep=".") == ["a"]
    assert CfgPath(["a[1]"], sep=".") == ["a", 1]
    assert CfgPath(["a[1][2]"], sep=".") == ["a", 1, 2]
    assert CfgPath("a.b.c", sep=".") == ["a", "b", "c"]
    assert CfgPath("a[1].b", sep=".") == ["a", 1, "b"]
    assert CfgPath("a/b/c", sep="/") == ["a", "b", "c"]
    assert CfgPath("a/b[1]/c", sep="/") == ["a", "b", 1, "c"]
    assert CfgPath(["a", "b", "c"]) == ["a", "b", "c"]
    assert CfgPath(("a", "b.c")) == ["a", "b", "c"]
    assert CfgPath(("a", ("b", "c"))) == ["a", "b", "c"]
    assert CfgPath(("a", ("b.c"))) == ["a", "b", "c"]
    assert CfgPath("[1]") == [1]
    assert CfgPath("222[1]") == ["222", 1]


def test_parent_dir():
    assert CfgPath("a/../b") == ["b"]
    assert CfgPath("../b") == ["..", "b"]
    assert CfgPath("a/b/..") == ["a"]
    assert CfgPath("..") == [".."]
    assert CfgPath("../../a") == ["..", "..", "a"]


def test_current_dir():
    assert CfgPath("a/./b") == ["a", "b"]
    assert CfgPath("./b") == [".", "b"]
    assert CfgPath("a/b/.") == ["a", "b"]
    assert CfgPath(".") == []
    assert CfgPath("././a") == [".", "a"]


@pytest.mark.parametrize(
    "path",
    [
        "a[1",
        "a[a]",
        "a]1]",
        "a[1[",
        "a[",
        "a]",
        "a[]",
        "a..b",
        "a../b",
        "a/..b",
        "a..",
        "a.[1]",
        "a[*]",  # Must be int
        # "a.**.b",  # "**" considered a name
    ],
)
def test_should_fail(path):
    with pytest.raises(ConfigException):
        CfgPath(path)


def test_to_str():
    assert CfgPath("").to_str() == ""
    assert CfgPath("a").to_str() == "a"
    assert CfgPath(["a"]).to_str() == "a"
    assert CfgPath(["a[1]"]).to_str() == "a[1]"
    assert CfgPath(["a[1][2]"]).to_str() == "a[1][2]"
    assert CfgPath("a.b.c").to_str() == "a.b.c"
    assert CfgPath("a[1].b").to_str() == "a[1].b"
    assert CfgPath("a/b/c", sep="/").to_str("/") == "a/b/c"
    assert CfgPath("a/b[1]/c", sep="/").to_str("/") == "a/b[1]/c"
    assert CfgPath(["a", "b", "c"]).to_str() == "a.b.c"
    assert CfgPath(("a", "b.c")).to_str() == "a.b.c"
    assert CfgPath(("a", ("b", "c"))).to_str() == "a.b.c"
    assert CfgPath(("a", ("b.c"))).to_str() == "a.b.c"
    assert CfgPath("[1]").to_str() == "[1]"
    assert CfgPath("222[1]").to_str() == "222[1]"
    assert CfgPath("a/../b").to_str() == "b"
    assert CfgPath("../b").to_str() == "../b"
    assert CfgPath("a/b/..") == "a/b/.."
    assert CfgPath("..") == ".."
    assert CfgPath("../../a") == "../../a"


def test_sequence():
    assert len(CfgPath("a[1].b")) == 3
    assert CfgPath("a[1].b")[0] == "a"
    assert CfgPath("a[1].b")[1] == 1
    assert CfgPath("a[1].b")[2] == "b"

    # Test iterator
    assert list(CfgPath("a[1].b")) == ["a", 1, "b"]


def test_auto_detect():
    cfg = CfgPath()
    assert cfg == []
    assert CfgPath("") == []
    assert CfgPath("a") == ["a"]
    assert CfgPath(["a"]) == ["a"]
    assert CfgPath(["a[1]"]) == ["a", 1]
    assert CfgPath(["a[1][2]"]) == ["a", 1, 2]
    assert CfgPath("a.b.c") == ["a", "b", "c"]  # detect "."
    assert CfgPath("a[1].b") == ["a", 1, "b"]  # detect "."
    assert CfgPath("a/b/c") == ["a", "b", "c"]  # detect "/"
    assert CfgPath("a/b[1]/c") == ["a", "b", 1, "c"]  # detect "/"
    assert CfgPath(["a", "b", "c"]) == ["a", "b", "c"]
    assert CfgPath(("a", "b.c")) == ["a", "b", "c"]
    assert CfgPath(("a", ("b", "c"))) == ["a", "b", "c"]
    assert CfgPath(("a", ("b.c"))) == ["a", "b", "c"]
    assert CfgPath("[1]") == [1]
    assert CfgPath("222[1]") == ["222", 1]
