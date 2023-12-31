#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass

import pytest
import yaml

from jd_config import (
    ConfigException,
    EnvPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
    ValueReader,
    ValueType,
)

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_ValueType():
    assert isinstance(11, ValueType)
    assert isinstance(1.1, ValueType)
    assert isinstance(True, ValueType)
    assert isinstance("test", ValueType)

    # assert isinstance(Placeholder(), Placeholder)   # Will fail, because it is abstract
    assert isinstance(ImportPlaceholder(file="xxx"), Placeholder)
    assert isinstance(RefPlaceholder(path="db"), Placeholder)
    assert isinstance(EnvPlaceholder(env_var="ENV"), Placeholder)

    assert isinstance(ImportPlaceholder("test.yaml"), ValueType)
    assert isinstance(RefPlaceholder("db.engine"), ValueType)
    assert isinstance(EnvPlaceholder("ENV", "default"), ValueType)


def test_yaml_input():
    data = yaml.safe_load("a: aa")
    assert data["a"] == "aa"
    data = yaml.safe_load("a: 'aa'")  # The yaml parser removes all quotes
    assert data["a"] == "aa"
    data = yaml.safe_load('a: "aa"')  # The yaml parser removes all quotes
    assert data["a"] == "aa"
    data = yaml.safe_load("a: a'b'a")  # Quotes in the middle are allowed
    assert data["a"] == "a'b'a"
    data = yaml.safe_load('a: a"b"a')  # Quotes in the middle are allowed
    assert data["a"] == 'a"b"a'
    data = yaml.safe_load("a: a'ba")  # Even single quotes
    assert data["a"] == "a'ba"
    # data = yaml.safe_load("a: 'aba")  # But if at the beginning, an end-quote is needed
    # assert data["a"] == "'aba"
    data = yaml.safe_load("a: aba'")  # A quote at the end is fine though
    assert data["a"] == "aba'"
    data = yaml.safe_load("a:    aa    ")  # Spaces are stripped (tabs are not!)
    assert data["a"] == "aa"

    # data = yaml.safe_load('a: ""aa""')  # The yaml parser throws an exception
    # data = yaml.safe_load('a: "\"aa\""') # The same. The yaml parser throws an exception
    data = yaml.safe_load(r'a: "\"aa\""')  # Not convinient to use for users
    assert data["a"] == '"aa"'
    data = yaml.safe_load('a: "\\"aa\\""')  # Not convinient to use for users
    assert data["a"] == '"aa"'
    data = yaml.safe_load('a: r"aa"')  # Pythonic way for raw text
    assert data["a"] == 'r"aa"'  # This is very much like python: r".." is a raw string


def test_find_quote_end():
    find = ValueReader.find_quote_end
    assert find("'test'", 0) == 0 + len("'test'")
    assert find("'test' xxx", 0) == 0 + len("'test'")
    # The first char is used to determined the quote char
    assert find('"test"', 0) == 0 + len('"test"')
    assert find('"test" xxx', 0) == 0 + len('"test"')
    # !! The first char ...
    assert find("testing", 0) == 0 + len("test")
    # The backslash escapes the next char, but the backslash will not be removed.
    assert find(r"'test\'test'", 0) == 0 + len("'test\\'test'")
    assert find('"{ref:a}" xxx', 0) == 0 + len('"{ref:a}"')

    with pytest.raises(ConfigException):
        find("'test", 0)

    with pytest.raises(ConfigException):
        find('"test', 0)

    with pytest.raises(ConfigException):
        find('"test\\"test', 0)


def test_find_bracket_end():
    find = ValueReader.find_bracket_end
    assert find("{test}", 0) == 0 + len("{test}")
    assert find("{test} xxx", 0) == 0 + len("{test}")
    # No re-validation that start position is correct
    assert find("test}", 0) == 0 + len("test}")
    assert find("{{test}} xxx", 0) == 0 + len("{{test}}")
    assert find("{{test}} xxx", 1) == 1 + len("{test}")
    assert find("{11{test}22}", 0) == 0 + len("{11{test}22}")
    # No re-validation that start position is correct
    assert find("{11{test}22}", 1) == 1 + len("11{test}22}")
    # The backslash escapes the next char, but the backslash will not be removed.
    assert find(r"{test\}test}", 0) == 0 + len("{test\\}test}")
    assert find("{test\\}test}", 0) == 0 + len(r"{test\}test}")
    assert find("{11'text'22}", 0) == 0 + len("{11'text'22}")
    # Brackets within quotes are ignored
    assert find("{11'{text}'22}", 0) == 0 + len("{11'{text}'22}")
    assert find('{11"{text}"22}', 0) == 0 + len('{11"{text}"22}')
    assert find("{11'a{b'22}", 0) == 0 + len("{11'a{b'22}")
    assert find("{11'a}b'22}", 0) == 0 + len("{11'a}b'22}")

    with pytest.raises(ConfigException):
        find("{test", 0)

    with pytest.raises(ConfigException):
        find(r"{test\}test", 0)

    with pytest.raises(ConfigException):
        find("{test{inner}test", 0)

    with pytest.raises(ConfigException):
        find("{test{inner}test", 1)


def test_is_raw_text():
    assert ValueReader.is_raw_text("r'abc'") is True
    assert ValueReader.is_raw_text('r"abc"') is True
    assert ValueReader.is_raw_text("abc") is False
    assert ValueReader.is_raw_text("r'abc") is False
    assert ValueReader.is_raw_text("'abc'") is False


def test_split_yaml_value():
    split = ValueReader.split_yaml_value
    assert list(split("test")) == ["test"]
    assert list(split("test, more")) == ["test, more"]
    assert list(split("test   , more")) == ["test   , more"]
    # Escape char
    assert list(split(r"test \{\} more")) == [r"test \{\} more"]
    assert list(split("{ref:a}")) == ["{ref:a}"]
    assert list(split(" {ref:a} ")) == ["{ref:a}"]
    assert list(split("{ref:a} - {ref:b}")) == ["{ref:a}", " - ", "{ref:b}"]
    assert list(split("{ref:a, b}")) == ["{ref:a, b}"]
    assert list(split("{ref:'aa'}")) == ["{ref:'aa'}"]
    assert list(split("{ref:'a{}a'}")) == ["{ref:'a{}a'}"]


def test_tokenize_placeholder_args():
    tokenize = ValueReader.tokenize_placeholder_args
    assert list(tokenize("")) == []
    assert list(tokenize("test, more")) == ["test", "more"]
    # Strip whitespace around the separator
    assert list(tokenize("test   , more")) == ["test", "more"]
    # Separator escaped
    assert list(tokenize(r"test\, more")) == ["test\\, more"]
    assert list(tokenize("1")) == [1]  # Including conversion to int.
    assert list(tokenize("a, 1")) == ["a", 1]
    assert list(tokenize("'aa'")) == ["aa"]
    assert list(tokenize("'aa', bb, cc")) == ["aa", "bb", "cc"]
    assert list(tokenize("'aa',")) == ["aa"]
    assert list(tokenize("{ref:a}, {ref:'default'}")) == ["{ref:a}", "{ref:'default'}"]


def test_ValueReader():
    registry = {"ref": RefPlaceholder}
    value_reader = ValueReader(registry=registry)
    assert len(value_reader.registry) == 1
    assert "ref" in value_reader.registry

    value_reader = ValueReader()
    assert len(value_reader.registry) > 0  # Default placeholders should be registered

    def parse(x):
        return list(value_reader.parse(x))

    value = parse("")
    assert len(value) == 0

    value = parse("test")
    assert len(value) == 1
    assert value[0] == "test"

    value = parse("123")
    assert len(value) == 1
    assert value[0] == 123

    # Treat as simple string. Separators only apply to placeholders
    value = parse(" aaa, bbb,ccc ,   123, ddd ")
    assert value == [" aaa, bbb,ccc ,   123, ddd "]

    value = parse("{ref: test}")
    assert value == [RefPlaceholder("test")]

    value = parse("{ref: test,}")
    assert value == [RefPlaceholder("test")]

    value = parse("{ref: test} - {ref: db}")
    assert value == [RefPlaceholder("test"), " - ", RefPlaceholder("db")]

    # Nested placeholders
    value = parse("{ref: test}-{ref: db, {ref: db_default, mysql}}")
    assert value == [
        RefPlaceholder("test"),
        "-",
        RefPlaceholder("db", "{ref: db_default, mysql}"),
    ]

    value = parse("{import: ./db/{ref: db}-config.yaml}")
    assert value == [ImportPlaceholder("./db/{ref: db}-config.yaml")]

    # Value with quotes
    value = parse('{import: "./db/{ref:db}-config.yaml"}')
    assert value == [ImportPlaceholder("./db/{ref:db}-config.yaml")]

    value = parse("{ref: ./db/{ref: db, {ref: mydef}}-config.yaml, default}")
    assert value == [
        RefPlaceholder("./db/{ref: db, {ref: mydef}}-config.yaml", "default")
    ]

    should_fail = ["{ref:db", "{db}", "{:db}", "{xxx: db}", "{ref:,db}"]
    for fail in should_fail:
        with pytest.raises(ConfigException):
            parse(fail)


@dataclass
class MyBespokePlaceholder(Placeholder):
    """This is also a test for a placeholder that does not take any parameters"""

    def resolve(self, *_) -> str:
        return "value"


def test_add_placeholder():
    reader = ValueReader()
    reader.registry["bespoke"] = MyBespokePlaceholder

    value = list(reader.parse("{ref: test}-{ref: db}", sep=","))
    assert value == [RefPlaceholder("test"), "-", RefPlaceholder("db")]

    value = list(reader.parse("{bespoke:}", sep=","))
    assert value == [MyBespokePlaceholder()]
