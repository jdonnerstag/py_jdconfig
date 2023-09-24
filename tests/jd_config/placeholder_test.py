#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

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

    assert isinstance(Placeholder(), Placeholder)
    assert isinstance(ImportPlaceholder(file="xxx"), Placeholder)
    assert isinstance(RefPlaceholder(path="db"), Placeholder)
    assert isinstance(EnvPlaceholder(env_var="ENV"), Placeholder)

    # TODO I'm currently using Python 3.11.2, and this seems to be a bug
    # ValueType is a Union Type with one entry being a ForwardRef('Placeholder').
    # Even though isinstance works with all other types in the Union, it doesn't
    # work with the ForwardRef.
    #x = ValueType
    #obj = Placeholder("test", [])
    #assert isinstance(obj, ValueType)
    #assert isinstance(ImportPlaceholder("test", []), ValueType)
    #assert isinstance(RefPlaceholder("test", []), ValueType)

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


def test_ImportPlaceholder():
    obj = ImportPlaceholder(file="xxx")
    assert obj.file == "xxx"
    assert obj.replace == False

    # Filename is missing
    with pytest.raises(Exception):
        ImportPlaceholder(file="")


def test_RefPlaceholder():
    obj = RefPlaceholder(path="db")
    assert obj.path == "db"
    assert obj.default_val == None

    # Filename is missing
    with pytest.raises(Exception):
        RefPlaceholder(path="")

def test_EnvPlaceholder():
    obj = EnvPlaceholder(env_var="ENV")
    assert obj.env_var == "ENV"
    assert obj.default_val == None

    # Filename is missing
    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")

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

    value = list(ValueReader().parse('{import: "./db/{ref:db}_config.yaml"}', sep=","))
    assert value == [ImportPlaceholder(["./db/", RefPlaceholder("db"), "_config.yaml"])]
