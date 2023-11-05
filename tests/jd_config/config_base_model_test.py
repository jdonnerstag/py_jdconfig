#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
import logging
import os
from pathlib import Path

from typing import Annotated, Any, ForwardRef, Optional

import pytest

from jd_config.config_base_model import BaseModel
from jd_config.utils import ConfigException
from jd_config.cfg_types import EmailType, ExistingDirectoryType, ExistingFileType
from jd_config.validators import String, OneOf, Number
from jd_config.field import Field

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


class A(BaseModel):
    a: str
    b: str
    c: str = "default cc"


def test_class_init():
    data = dict(a="aa", b="bb", c="cc")
    app = A(data)
    assert app.__type_hints__ == dict(a=str, b=str, c=str)
    assert app.__input_names_map__ == {}


def test_load_simple_str():
    data = dict(
        a="aa",
        b="bb",
        c="cc",
    )

    app = A(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "cc"

    data = dict(
        a="aa",
        b="bb",
    )

    app = A(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "default cc"


class B(BaseModel):
    a: str
    b: int
    c: Decimal
    d: Path


def test_load_simple_converter():
    data = dict(a=1, b="99", c="1.1", d=str(Path.cwd()))

    app = B(data)
    assert app
    assert app.a == "1"
    assert app.b == 99
    assert app.c == Decimal("1.1")
    assert app.d == Path.cwd()


class C(BaseModel):
    a: str
    b: A


def test_load_deep():
    data = dict(a="aa", b=dict(a="aaa", b="bb", c="cc"))

    app = C(data)
    assert app
    assert isinstance(app, C)
    assert app.a == "aa"
    assert isinstance(app.b, A)
    assert app.b.a == "aaa"
    assert app.b.b == "bb"
    assert app.b.c == "cc"

    # get
    assert app.get("a") == "aa"
    assert app.get("b.a") == "aaa"
    assert app.get("b.b") == "bb"
    assert app.get("b.c") == "cc"

    # getitem
    assert app["a"] == "aa"
    assert app["b"]["a"] == "aaa"
    assert app["b"]["b"] == "bb"
    assert app["b"]["c"] == "cc"

    assert app["b.a"] == "aaa"
    assert app["b.b"] == "bb"
    assert app["b.c"] == "cc"


class D(BaseModel):
    a: list
    b: dict
    c: list = []  # TODO Why is this not a good idea? How to detect?


def test_load_simple_container():
    data = dict(a=["a1", 2], b=dict(b1="bb1", b2=3))

    app = D(data)
    assert app
    assert app.a == ["a1", 2]
    assert app.a[0] == "a1"
    assert app.a[1] == 2
    assert app.b == {"b1": "bb1", "b2": 3}
    assert app.b["b1"] == "bb1"
    assert app.b["b2"] == 3

    data = dict(a="a1", b=dict(b1="bb1", b2=3))
    with pytest.raises(ConfigException):
        D(data)  # "a" is not a list

    data = dict(a=["a1", 2], b="bb1")
    with pytest.raises(ConfigException):
        D(data)  # "b" is not a dict


class E(BaseModel):
    # The type is only used for validation, but not providing a default value
    a: Optional[str] = None
    b: str | None = None
    c: str | int  # process left to right. Return the first that works
    d: list[str] | None = None
    e: list[int | str]  # process left to right. Return the first that works


def test_load_optional_and_unions():
    data = dict(a="aa", b="bb", c="cc", d=["dd"], e=["ee"])

    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "cc"
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee"]
    assert app.e[0] == "ee"

    # Optional "a"
    data = dict(b="bb", c="cc", d=["dd"], e=["ee"])
    app = E(data)
    assert app
    assert app.a is None
    assert app.b == "bb"
    assert app.c == "cc"
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee"]
    assert app.e[0] == "ee"

    # Optional "b"
    data = dict(a="aa", c="cc", d=["dd"], e=["ee"])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b is None
    assert app.c == "cc"
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee"]
    assert app.e[0] == "ee"

    # "b" is None
    data = dict(a="aa", b=None, c="cc", d=["dd"], e=["ee"])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b is None
    assert app.c == "cc"
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee"]
    assert app.e[0] == "ee"

    # 'c' is an int
    data = dict(a="aa", b="bb", c=99, d=["dd"], e=["ee"])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == 99
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee"]
    assert app.e[0] == "ee"

    # optional "d"
    data = dict(a="aa", b="bb", c="cc", e=["ee"])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "cc"
    assert app.d is None
    assert app.e == ["ee"]
    assert app.e[0] == "ee"

    # list with same types
    data = dict(a="aa", b="bb", c="cc", d=["dd"], e=["ee", "99"])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "cc"
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee", "99"]
    assert app.e[0] == "ee"
    assert app.e[1] == "99"

    # list with same types
    data = dict(a="aa", b="bb", c="cc", d=["dd"], e=["ee", 99])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "cc"
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee", 99]
    assert app.e[0] == "ee"
    assert app.e[1] == 99

    # A float can be converted to str and int. We process left to right.
    data = dict(a="aa", b="bb", c=99.11, d=["dd"], e=["ee", 99.11])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "99.11"  # str | int. First is str
    assert app.d == ["dd"]
    # pylint: disable=unsubscriptable-object
    assert isinstance(app.d, list) and app.d[0] == "dd"
    assert app.e == ["ee", 99]  # list[int|str]. First is int
    assert app.e[0] == "ee"
    assert app.e[1] == 99

    # Empty lists
    data = dict(a="aa", b="bb", c=99.11, d=[], e=[])
    app = E(data)
    assert app
    assert app.a == "aa"
    assert app.b == "bb"
    assert app.c == "99.11"  # str | int. First is str
    assert isinstance(app.d, list) and len(app.d) == 0
    assert isinstance(app.e, list) and len(app.e) == 0

    # 'd' is not a list
    data = dict(a="aa", b="bb", c=99.11, d="xxx", e=["ee", 99.11])
    with pytest.raises(ConfigException):
        E(data)  # "b" is not a dict

    # 'e' is not a list
    data = dict(a="aa", b="bb", c=99.11, d=["dd"], e=11)
    with pytest.raises(ConfigException):
        E(data)  # "b" is not a dict


class F(BaseModel):
    a: list[Any]
    b: dict[str, str]
    c: dict[str, int | str]
    d: dict[str, Any]


def test_generic_dicts():
    data = dict(
        a=["aa", 1, 1.1, Path("c:/temp"), ["a1", "a2"]],
        b=dict(a="aaa", b="bbb"),
        c=dict(a="a1", b=99.11),
        d=dict(a=[1, 2, 3, 4]),
    )

    app = F(data)
    assert app
    assert app.a[0] == "aa"
    assert app.a[1] == 1
    assert app.a[2] == 1.1
    assert app.a[3] == Path("c:/temp")
    assert app.a[4] == ["a1", "a2"]
    assert app.b["a"] == "aaa"
    assert app.b["b"] == "bbb"
    assert app.c["a"] == "a1"
    assert app.c["b"] == 99
    assert app.d["a"] == [1, 2, 3, 4]


class G(BaseModel):
    a: Annotated[str, lambda x: x.upper()]


def test_annotated():
    data = dict(a="aa")

    app = G(data)
    assert app
    assert app.a == "AA"


class H(BaseModel):
    a: str = Field(default="xx")


def test_field_descriptor():
    app = H({})
    assert app.a == "xx"

    data = dict(a="aa")
    app = H(data)
    assert app.a == "aa"

    data = dict()
    app = H(data)
    assert app.a == "xx"


class I(BaseModel):
    a: str
    b: str = "2"

    # My VSCode pylint does not detect this mismatch???
    c: str = 3  # It will auto-convert to str type.


def test_default_values():
    data = dict(a="a")
    app = I(data)
    assert app
    assert app.a == "a"
    assert app.b == "2"
    assert app.c == "3"  # auto-converted to str.


def test_load_fail_missing():
    data = dict(a="aa", c="cc")

    # 'b' has not default and is not provided via data
    with pytest.raises(ConfigException):
        A(data)


def test_load_app():
    data = dict(
        app_meta=dict(
            version="0.0.1",
            contact="xyz@me.com",
            git_repo="http://github.com/jdonnerstag/my_repo",
        ),
        app=dict(
            input_directory=".", crm_database="postgres", logging=dict(format="ascii")
        ),
    )

    cfg = MyConfig(data)
    assert cfg
    assert cfg.app_meta.version == "0.0.1"
    assert cfg.app_meta.contact == "xyz@me.com"
    assert cfg.app_meta.git_repo == "http://github.com/jdonnerstag/my_repo"
    assert cfg.app.input_directory == "."
    assert cfg.app.crm_database == "postgres"
    assert cfg.app.logging.format == "ascii"


def test_extra_key():
    data = dict(
        input_directory=".",
        crm_database="postgres",
        logging=dict(format="ascii"),
        me="test",
    )

    app = AppConfig(data)
    assert app
    assert app.input_directory == "."
    assert app.crm_database == "postgres"
    assert app.logging.format == "ascii"

    assert not hasattr(app, "me")
    assert app.__extra_keys__ == ["me"]


def test_list():
    data = dict(xlist=[{"format": 1}, {"format": 2}, {"format": 3}])

    app = ListConfig(data)
    assert app
    assert app.xlist[0].format == "1"  # Converted to string as per class definition
    assert app.xlist[1].format == "2"  # Converted to string as per class definition
    assert app.xlist[2].format == "3"  # Converted to string as per class definition


def test_date():
    data = dict(modified="2023-10-11 12:32:00")

    app = DateConfig(data)
    assert app
    assert app.modified == datetime(2023, 10, 11, 12, 32, 00)


def test_various():
    data = dict(
        myany=datetime(2023, 1, 1),
        myenum="LAST",
        std_dict_no_types={"a": "aa"},
        std_dict={"a": 11},
        mypath="c:\\temp",
        mydecimal="0.1",
        myemail="juergen.donnerstag@neverland.de",
        existing_file="readme.md",
        existing_dir=".",
        name="TEST",
        kind="metal",
        quantity=99,
    )

    app = VariousConfig(data)
    assert app
    assert app.myany == datetime(2023, 1, 1)
    assert app.myenum == MyEnum.LAST
    assert app.std_dict_no_types == {"a": "aa"}
    assert app.std_dict == {"a": 11}
    assert app.mypath == Path("c:\\temp")
    assert app.mydecimal == Decimal("0.1")
    assert app.myemail == "juergen.donnerstag@neverland.de"
    assert app.existing_file == Path("readme.md")
    assert app.existing_dir == Path(".")
    assert app.name == "TEST"
    assert app.kind == "metal"
    assert app.quantity == 99


LoggingConfig = ForwardRef("LoggingConfig")


class AppMetaConfig(BaseModel):
    version: str  # TODO define type that matches 0.6.0
    contact: str  # TODO define email type
    git_repo: str  # TODO define github repo type


class AppConfig(BaseModel):
    input_directory: str
    crm_database: str
    logging: LoggingConfig
    number: int = 99
    xfloat: float = 1.1


class LoggingConfig(BaseModel):
    format: str


class MyConfig(BaseModel):
    app_meta: AppMetaConfig
    app: AppConfig


class FailConfig(BaseModel):
    input_directory: str
    crm_database: str
    logging: LoggingConfig
    number: int  # Default not defined
    xfloat: float = 1.1


class ListConfig(BaseModel):
    xlist: list[LoggingConfig]


def my_strptime(fmt):
    def inner_strptime(text):
        return datetime.strptime(text, fmt)

    return inner_strptime


class DateConfig(BaseModel):
    modified: Annotated[date, my_strptime("%Y-%m-%d %H:%M:%S")]
    # TODO DATE["%Y-%m-%d %H:%M:%S"] => A GenericAlias with [T] == the format


class MyEnum(Enum):
    FIRST = auto()
    NEXT = auto()
    LAST = auto()


class VariousConfig(BaseModel):
    myany: Any
    myenum: MyEnum
    std_dict_no_types: dict
    std_dict: dict[str, Any]
    mypath: Path
    mydecimal: Decimal
    myemail: EmailType
    existing_file: ExistingFileType
    existing_dir: ExistingDirectoryType
    # TODO dates: list[Annotated[date, my_strptime("%Y-%m-%d %H:%M:%S")]]
    # TODO typed_dict: TypedDict[str, int] # Not sure it is urgent to support it
    # TODO mytuple: tuple
    # TODO mytuple_str_int: tuple(str, int)
    # TODO mytuple_str_list: tuple(str, ...)
    # TODO myurl: Url #  See the email example and use a public validator package
    name: str = String(minsize=3, maxsize=10, predicate=str.isupper)
    kind: str = OneOf("wood", "metal", "plastic")
    quantity: int = Number(minvalue=0)
