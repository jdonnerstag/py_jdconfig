#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
import logging

import pytest
from jd_config import CompoundValue, ConfigException, ValueType, ValueReader, YamlObj
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

    # Value with quotes
    value = list(ValueReader().parse('{import: "./db/{ref:db}_config.yaml"}', sep=","))
    assert value == [ImportPlaceholder(["./db/", RefPlaceholder("db"), "_config.yaml"])]

def test_resolve():
    # "db-a" is the reference we want to resolve. "db-a" occurs in the db yaml file,
    # as well as the main yaml file.
    # We want the resolver to first try against the the yaml file which contains the {ref:..},
    # and only if not found, try from the very root.

    placeholder_db_a = RefPlaceholder("db-a")
    placeholder_a = RefPlaceholder("a")

    # Simulate a db yaml file
    cfg_db = {
        "db-a": YamlObj(0, 0, None, "db-a1"),
        "db-b": YamlObj(0, 0, None, [placeholder_db_a]),
        "db-c": YamlObj(0, 0, None, [placeholder_a]),
    }

    # Simulate the main yaml file, which has imported the db yaml file.
    # Both files contain a "db-a" key.
    cfg = {
        "a": YamlObj(0, 0, None, 11),
        "db": cfg_db,
        "db-a": YamlObj(0, 0, None, "from root"),
    }

    # First placeholder.post_load() was not invoked, so that RefPlaceholder does
    # not know about the root obj of the db yaml file.
    assert placeholder_db_a.file_root is None
    assert placeholder_db_a.resolve(cfg) == "from root"  # From the main yaml file

    # Invoke post_load() as JDConfig.load() will do, and register the db yaml
    # file obj with the placeholder. This way, placeholder.resolve() can leverage
    # it to resolve in 2 steps: step 1: db yaml file; step 2: main yaml file.
    placeholder_db_a.post_load(cfg_db)
    assert placeholder_db_a.file_root is not None
    assert placeholder_db_a.resolve(cfg) == "db-a1"

    # This placeholder will fail resolving in the db yaml file, but succeed in
    # the main yaml file.
    placeholder_a.post_load(cfg_db)
    assert placeholder_a.file_root is not None
    assert placeholder_a.resolve(cfg) == 11


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
