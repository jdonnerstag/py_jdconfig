#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
import logging

import pytest
from jd_config import ValueType, ValueReader, ConfigException
from jd_config import Placeholder, RefPlaceholder, ImportPlaceholder, EnvPlaceholder

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

    # File names are mandatory
    with pytest.raises(Exception):
        ImportPlaceholder(file="")

    with pytest.raises(Exception):
        RefPlaceholder(path="")

    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")


def test_ValueReader():
    value_reader = ValueReader()
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

    value = parse(" aaa, bbb,ccc ,   123, ddd ")
    assert value == ["aaa", "bbb", "ccc", 123, "ddd"]

    value = parse("{ref: test}")
    assert value == [RefPlaceholder("test")]

    value = parse("{ref: test,}")
    assert value == [RefPlaceholder("test")]

    value = parse("{ref: test}-{ref: db}")
    assert value == [RefPlaceholder("test"), "-", RefPlaceholder("db")]

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

    should_fail = ["{ref:db", "{db}", "{:db}", "{xxx: db}", "{ref:,db}"]
    for fail in should_fail:
        with pytest.raises(ConfigException):
            parse(fail)

    value = list(value_reader.parse(" aaa, bbb,ccc ,   123, ddd ", sep=";"))
    assert value == ["aaa, bbb,ccc ,   123, ddd"]   # Only leading and trailing whitespaces are stripped

    value = list(value_reader.parse(" aaa; bbb;ccc ;   123; ddd ", sep=";"))
    assert value == ["aaa", "bbb", "ccc", 123, "ddd"]

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
