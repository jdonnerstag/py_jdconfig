#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging

import pytest
from jd_config import CompoundValue, ConfigException, ValueType, ValueReader
from jd_config import Placeholder, RefPlaceholder, ImportPlaceholder

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_ValueType():
    assert isinstance(11, ValueType)
    assert isinstance(1.1, ValueType)
    assert isinstance(True, ValueType)
    assert isinstance("test", ValueType)

    assert isinstance(Placeholder("test", []), Placeholder)
    assert isinstance(ImportPlaceholder("test", []), Placeholder)
    assert isinstance(RefPlaceholder("test", []), Placeholder)

    # TODO I'm currently using Python 3.11.2, and this seems to be a bug
    # ValueType is a Union Type with one entry being a ForwardRef('Placeholder').
    # Even though isinstance works with all other types in the Union, it doesn't
    # work with the ForwardRef.
    #x = ValueType
    #obj = Placeholder("test", [])
    #assert isinstance(obj, ValueType)
    #assert isinstance(ImportPlaceholder("test", []), ValueType)
    #assert isinstance(RefPlaceholder("test", []), ValueType)


def test_CompoundValue():
    obj = CompoundValue([1, 2, 3, 4])
    assert len(obj) == 4
    assert obj.is_import() is False

    obj = CompoundValue([ImportPlaceholder("test", [])])
    with pytest.raises(AssertionError):
        obj.is_import()

    obj = CompoundValue([ImportPlaceholder("import", [])])
    assert obj.is_import() is True

    # If there is a ImportPlaceholder's, nothing is allowed
    with pytest.raises(ConfigException):
        obj = CompoundValue(["something else", ImportPlaceholder("import", [])])
        obj.is_import()


def test_Placeholder():
    obj = Placeholder("test", [])
    assert obj.name == "test"
    assert len(obj.args) == 0

    obj.args.append("me")
    assert len(obj.args) == 1


def test_ImportPlaceholder():
    obj = ImportPlaceholder("import", [])
    assert obj.name == "import"
    assert len(obj.args) == 0

    # Filename is missing
    with pytest.raises(IndexError):
        assert obj.file == None

    obj = ImportPlaceholder("import", ["myfile"])
    assert obj.file == "myfile"
    assert obj.env == None
    assert obj.replace == False

    # This is actually how we are using it in the source code. We create
    # a Placeholder object, and later tell him, it is now an ImportPlaceholder.
    # Pylint complains about it, but it works.
    # TODO we may change it create the correct Placeholder in the first place.
    obj = Placeholder("import", ["myfile"])
    obj.__class__ = ImportPlaceholder
    assert obj.file == "myfile"     # pylint: disable=no-member
    assert obj.env == None          # pylint: disable=no-member
    assert obj.replace == False     # pylint: disable=no-member


def test_RefPlaceholder():
    obj = RefPlaceholder("ref", [])
    assert obj.name == "ref"
    assert len(obj.args) == 0

    # Filename is missing
    with pytest.raises(IndexError):
        assert obj.path == None

    obj = RefPlaceholder("ref", ["db"])
    assert obj.path == "db"
    assert obj.default == None

    obj = RefPlaceholder("ref", ["db", "mysql"])
    assert obj.path == "db"
    assert obj.default == "mysql"

    # This is actually how we are using it in the source code. We create
    # a Placeholder object, and later tell him, it is now an ImportPlaceholder.
    # Pylint complains about it, but it works.
    # TODO we may change it create the correct Placeholder in the first place.
    obj = Placeholder("ref", ["db"])
    obj.__class__ = RefPlaceholder
    assert obj.path == "db"         # pylint: disable=no-member
    assert obj.default == None      # pylint: disable=no-member

def test_ValueReader():
    value = list(ValueReader.parse("", sep=","))
    assert len(value) == 0

    value = list(ValueReader.parse("test", sep=","))
    assert len(value) == 1
    assert value[0] == "test"

    value = list(ValueReader.parse("123", sep=","))
    assert len(value) == 1
    assert value[0] == 123

    value = list(ValueReader.parse(" aaa, bbb,ccc ,   123, ddd ", sep=","))
    assert value == ["aaa", "bbb", "ccc", 123, "ddd"]

    value = list(ValueReader.parse("{ref: test}", sep=","))
    assert value == [RefPlaceholder("ref", ["test"])]

    value = list(ValueReader.parse("{ref: test}-{ref: db}", sep=","))
    assert value == [RefPlaceholder("ref", ["test"]), "-", RefPlaceholder("ref", ["db"])]
