#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
import logging

import pytest
from jd_config import CompoundValue, ConfigException, ValueType, ValueReader
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

    assert isinstance(ImportPlaceholder("test.yaml", False), ValueType)
    assert isinstance(RefPlaceholder("db.engine"), ValueType)
    assert isinstance(EnvPlaceholder("ENV"), ValueType)

    # File names are mandatory
    with pytest.raises(Exception):
        ImportPlaceholder(file="")

    with pytest.raises(Exception):
        RefPlaceholder(path="")

    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")

def test_CompoundValue():
    obj = CompoundValue([1, 2, 3, 4])
    assert len(obj) == 4
    assert obj.is_import() is False

    obj = CompoundValue([ImportPlaceholder(file="some_path")])
    assert obj.is_import() is True

    # If there is a ImportPlaceholder's, nothing is allowed
    with pytest.raises(ConfigException):
        obj = CompoundValue(["something else", ImportPlaceholder(file="some_path")])
        obj.is_import()


def test_ValueReader():
    value = list(ValueReader().parse("", sep=","))
    assert len(value) == 0

    value = list(ValueReader().parse("test", sep=","))
    assert len(value) == 1
    assert value[0] == "test"

    value = list(ValueReader().parse("123", sep=","))
    assert len(value) == 1
    assert value[0] == 123

    value = list(ValueReader().parse(" aaa, bbb,ccc ,   123, ddd ", sep=","))
    assert value == ["aaa", "bbb", "ccc", 123, "ddd"]

    value = list(ValueReader().parse("{ref: test}", sep=","))
    assert value == [RefPlaceholder("test")]

    value = list(ValueReader().parse("{ref: test}-{ref: db}", sep=","))
    assert value == [RefPlaceholder("test"), "-", RefPlaceholder("db")]

    # Nested placeholders
    value = list(ValueReader().parse("{ref: test}-{ref: db, {ref: db_default, mysql}}", sep=","))
    assert value == [RefPlaceholder("test"), "-", RefPlaceholder("db", RefPlaceholder("db_default", "mysql"))]

    value = list(ValueReader().parse("{import: ./db/{ref: db}-config.yaml, true}", sep=","))
    assert value == [ImportPlaceholder(["./db/", RefPlaceholder("db"), "-config.yaml"], True)]

    value = list(ValueReader().parse("{import: ./db/{ref: db}-config.yaml}", sep=","))
    assert value == [ImportPlaceholder(["./db/", RefPlaceholder("db"), "-config.yaml"])]

    # Value with quotes
    value = list(ValueReader().parse('{import: "./db/{ref:db}_config.yaml"}', sep=","))
    assert value == [ImportPlaceholder(["./db/", RefPlaceholder("db"), "_config.yaml"])]


@dataclass
class MyBespokePlaceholder(Placeholder):
    """This is also a test for a placeholder that does not take any parameters"""

    def resolve(self, _) -> str:
        return "value"


def test_add_placeholder():
    reader = ValueReader()
    reader.registry["bespoke"] = MyBespokePlaceholder

    value = list(reader.parse("{ref: test}-{ref: db}", sep=","))
    assert value == [RefPlaceholder("test"), "-", RefPlaceholder("db")]

    value = list(reader.parse("{bespoke:}", sep=","))
    assert value == [MyBespokePlaceholder()]
