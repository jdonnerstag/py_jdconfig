#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

import logging

import pytest

from jd_config import ConfigException, ExtendedCfgPath

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_path():
    cfg = ExtendedCfgPath()
    assert cfg == []
    assert ExtendedCfgPath("") == []
    assert ExtendedCfgPath("a", sep=".") == ["a"]
    assert ExtendedCfgPath(["a"], sep=".") == ["a"]
    assert ExtendedCfgPath(["a[1]"], sep=".") == ["a", 1]
    assert ExtendedCfgPath(["a[1][2]"], sep=".") == ["a", 1, 2]
    assert ExtendedCfgPath("a.b.c", sep=".") == ["a", "b", "c"]
    assert ExtendedCfgPath("a[1].b", sep=".") == ["a", 1, "b"]
    assert ExtendedCfgPath("a/b/c", sep="/") == ["a", "b", "c"]
    assert ExtendedCfgPath("a/b[1]/c", sep="/") == ["a", "b", 1, "c"]
    assert ExtendedCfgPath(["a", "b", "c"]) == ["a", "b", "c"]
    assert ExtendedCfgPath(("a", "b.c")) == ["a", "b", "c"]
    assert ExtendedCfgPath(("a", ("b", "c"))) == ["a", "b", "c"]
    assert ExtendedCfgPath(("a", ("b.c"))) == ["a", "b", "c"]
    assert ExtendedCfgPath("[1]") == [1]
    assert ExtendedCfgPath("222[1]") == ["222", 1]
    assert ExtendedCfgPath("a.*.c") == ["a", "*", "c"]
    assert ExtendedCfgPath("a.b[*].c") == ["a", "b", "%", "c"]
    assert ExtendedCfgPath("a.**.c") == ["a", "**", "c"]
    assert ExtendedCfgPath("a.**.**.c") == ["a", "**", "c"]
    assert ExtendedCfgPath("a.*.*.c") == ["a", "*", "*", "c"]
    assert ExtendedCfgPath("a.*.**.c") == ["a", "**", "c"]  # same as "a.**.c"
    assert ExtendedCfgPath("a.**.*.c") == ["a", "**", "c"]  # same as "a.**.c"
    assert ExtendedCfgPath("a[*].**.c") == ["a", "**", "c"]  # same as "a.**.c"
    assert ExtendedCfgPath("**.c") == ["**", "c"]
    assert ExtendedCfgPath("*.c") == ["*", "c"]
    assert ExtendedCfgPath("a*.c") == [
        "a*",
        "c",
    ]  # only "*" and "**" have special meanings
    assert ExtendedCfgPath("a.*c") == ["a", "*c"]


def test_parent_dir():
    assert ExtendedCfgPath("a/../b") == ["b"]
    assert ExtendedCfgPath("../b") == ["..", "b"]
    assert ExtendedCfgPath("a/b/..") == ["a"]
    assert ExtendedCfgPath("a/*/..") == ["a"]
    assert ExtendedCfgPath("..") == [".."]
    assert ExtendedCfgPath("../../a") == ["..", "..", "a"]
    assert ExtendedCfgPath("a/**/../b") == ["a", "**", "..", "b"]


def test_current_dir():
    assert ExtendedCfgPath("a/./b") == ["a", "b"]
    assert ExtendedCfgPath("./b") == [".", "b"]
    assert ExtendedCfgPath("a/b/.") == ["a", "b"]
    assert ExtendedCfgPath(".") == []
    assert ExtendedCfgPath("././a") == [".", "a"]
    assert ExtendedCfgPath("a/**/./b") == ["a", "**", "b"]


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
        "a.*",
        "a.**",
        "a.[1]",
        "a/**/..",
        "a/*/.",  # Same as "a/*", which is invalid
    ],
)
def test_should_fail(path):
    with pytest.raises(ConfigException):
        ExtendedCfgPath(path)


def test_to_str():
    assert ExtendedCfgPath("").to_str() == ""
    assert ExtendedCfgPath("a").to_str() == "a"
    assert ExtendedCfgPath(["a"]).to_str() == "a"
    assert ExtendedCfgPath(["a[1]"]).to_str() == "a[1]"
    assert ExtendedCfgPath(["a[1][2]"]).to_str() == "a[1][2]"
    assert ExtendedCfgPath("a.b.c").to_str() == "a.b.c"
    assert ExtendedCfgPath("a[1].b").to_str() == "a[1].b"
    assert ExtendedCfgPath("a/b/c", sep="/").to_str("/") == "a/b/c"
    assert ExtendedCfgPath("a/b[1]/c", sep="/").to_str("/") == "a/b[1]/c"
    assert ExtendedCfgPath(["a", "b", "c"]).to_str() == "a.b.c"
    assert ExtendedCfgPath(("a", "b.c")).to_str() == "a.b.c"
    assert ExtendedCfgPath(("a", ("b", "c"))).to_str() == "a.b.c"
    assert ExtendedCfgPath(("a", ("b.c"))).to_str() == "a.b.c"
    assert ExtendedCfgPath("[1]").to_str() == "[1]"
    assert ExtendedCfgPath("222[1]").to_str() == "222[1]"
    assert ExtendedCfgPath("a.*.c").to_str() == "a.*.c"
    assert ExtendedCfgPath("a.b[*].c").to_str() == "a.b[*].c"
    assert ExtendedCfgPath("a.**.c").to_str() == "a.**.c"
    assert ExtendedCfgPath("a.**.**.c").to_str() == "a.**.c"
    assert ExtendedCfgPath("a.*.*.c").to_str() == "a.*.*.c"
    assert ExtendedCfgPath("a.*.**.c").to_str() == "a.**.c"
    assert ExtendedCfgPath("a.**.*.c").to_str() == "a.**.c"
    assert ExtendedCfgPath("a[*].**.c").to_str() == "a.**.c"
    assert ExtendedCfgPath("**.c").to_str() == "**.c"
    assert ExtendedCfgPath("*.c").to_str() == "*.c"
    assert ExtendedCfgPath("a/../b").to_str() == "b"
    assert ExtendedCfgPath("../b").to_str() == "../b"
    assert ExtendedCfgPath("a/b/..") == "a/b/.."
    assert ExtendedCfgPath("a/*/..") == "a"
    assert ExtendedCfgPath("..") == ".."
    assert ExtendedCfgPath("../../a") == "../../a"
    assert ExtendedCfgPath("a/**/../b") == "a/**/../b"


def test_sequence():
    assert len(ExtendedCfgPath("a[1].b")) == 3
    assert ExtendedCfgPath("a[1].b")[0] == "a"
    assert ExtendedCfgPath("a[1].b")[1] == 1
    assert ExtendedCfgPath("a[1].b")[2] == "b"

    # Test iterator
    assert list(ExtendedCfgPath("a[1].b")) == ["a", 1, "b"]


def test_auto_detect():
    cfg = ExtendedCfgPath()
    assert cfg == []
    assert ExtendedCfgPath("") == []
    assert ExtendedCfgPath("a") == ["a"]
    assert ExtendedCfgPath(["a"]) == ["a"]
    assert ExtendedCfgPath(["a[1]"]) == ["a", 1]
    assert ExtendedCfgPath(["a[1][2]"]) == ["a", 1, 2]
    assert ExtendedCfgPath("a.b.c") == ["a", "b", "c"]  # detect "."
    assert ExtendedCfgPath("a[1].b") == ["a", 1, "b"]  # detect "."
    assert ExtendedCfgPath("a/b/c") == ["a", "b", "c"]  # detect "/"
    assert ExtendedCfgPath("a/b[1]/c") == ["a", "b", 1, "c"]  # detect "/"
    assert ExtendedCfgPath(["a", "b", "c"]) == ["a", "b", "c"]
    assert ExtendedCfgPath(("a", "b.c")) == ["a", "b", "c"]
    assert ExtendedCfgPath(("a", ("b", "c"))) == ["a", "b", "c"]
    assert ExtendedCfgPath(("a", ("b.c"))) == ["a", "b", "c"]
    assert ExtendedCfgPath("[1]") == [1]
    assert ExtendedCfgPath("222[1]") == ["222", 1]
    assert ExtendedCfgPath("a.*.c") == ["a", "*", "c"]
    assert ExtendedCfgPath("a.b[*].c") == ["a", "b", "%", "c"]
    assert ExtendedCfgPath("a.**.c") == ["a", "**", "c"]
    assert ExtendedCfgPath("a.**.**.c") == ["a", "**", "c"]
    assert ExtendedCfgPath("a.*.*.c") == ["a", "*", "*", "c"]
    assert ExtendedCfgPath("a.*.**.c") == ["a", "**", "c"]  # same as "a.**.c"
    assert ExtendedCfgPath("a.**.*.c") == ["a", "**", "c"]  # same as "a.**.c"
    assert ExtendedCfgPath("a[*].**.c") == ["a", "**", "c"]  # same as "a.**.c"
    assert ExtendedCfgPath("**.c") == ["**", "c"]
    assert ExtendedCfgPath("*.c") == ["*", "c"]
    assert ExtendedCfgPath("a*.c") == [
        "a*",
        "c",
    ]  # only "*" and "**" have special meanings
    assert ExtendedCfgPath("a.*c") == ["a", "*c"]
