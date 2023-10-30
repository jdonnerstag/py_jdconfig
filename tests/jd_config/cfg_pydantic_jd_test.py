#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from datetime import date, datetime
from decimal import Decimal
from enum import Enum, auto
import logging
import os
from pathlib import Path

from typing import Annotated, Any, ForwardRef

import pytest

from jd_config.cfg_pydantic_jd import ConfigBaseModel
from jd_config.utils import ConfigException
from jd_config.cfg_types import EmailType, ExistingDirectoryType, ExistingFileType

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


LoggingConfig = ForwardRef("LoggingConfig")


class AppMetaConfig(ConfigBaseModel):
    version: str  # TODO define type that matches 0.6.0
    contact: str  # TODO define email type
    git_repo: str  # TODO define github repo type


class AppConfig(ConfigBaseModel):
    input_directory: str
    crm_database: str
    logging: LoggingConfig
    number: int = 99
    xfloat: float = 1.1


class LoggingConfig(ConfigBaseModel):
    format: str


class MyConfig(ConfigBaseModel):
    app_meta: AppMetaConfig
    app: AppConfig


class FailConfig(ConfigBaseModel):
    input_directory: str
    crm_database: str
    logging: LoggingConfig
    number: int  # Default not defined
    xfloat: float = 1.1


class ListConfig(ConfigBaseModel):
    xlist: list[LoggingConfig]


def my_strptime(fmt):
    def inner_strptime(text):
        return datetime.strptime(text, fmt)

    return inner_strptime


class DateConfig(ConfigBaseModel):
    modified: Annotated[date, my_strptime("%Y-%m-%d %H:%M:%S")]
    # TODO DATE["%Y-%m-%d %H:%M:%S"] => A GenericAlias with [T] == the format


class MyEnum(Enum):
    FIRST = auto()
    NEXT = auto()
    LAST = auto()


class VariousConfig(ConfigBaseModel):
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


def test_load_simple():
    data = dict(
        version="0.0.1",
        contact="xyz@me.com",
        git_repo="http://github.com/jdonnerstag/my_repo",
    )

    app = AppMetaConfig(data, None)
    assert app
    assert app.version == "0.0.1"
    assert app.contact == "xyz@me.com"
    assert app.git_repo == "http://github.com/jdonnerstag/my_repo"


def test_load_deep():
    data = dict(
        input_directory=".", crm_database="postgres", logging=dict(format="ascii")
    )

    app = AppConfig(data, None)
    assert app
    assert app.input_directory == "."
    assert app.crm_database == "postgres"
    assert app.logging.format == "ascii"


def test_load_fail_missing():
    data = dict(
        input_directory=".", crm_database="postgres", logging=dict(format="ascii")
    )

    # 'number' has not default and is not provided via data
    with pytest.raises(ConfigException):
        FailConfig(data, None)


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

    cfg = MyConfig(data, None)
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

    app = AppConfig(data, None)
    assert app
    assert app.input_directory == "."
    assert app.crm_database == "postgres"
    assert app.logging.format == "ascii"

    assert not hasattr(app, "me")
    assert app.extra_keys == ["me"]


def test_list():
    data = dict(xlist=[{"format": 1}, {"format": 2}, {"format": 3}])

    app = ListConfig(data, None)
    assert app
    assert app.xlist[0].format == "1"  # Converted to string as per class definition
    assert app.xlist[1].format == "2"  # Converted to string as per class definition
    assert app.xlist[2].format == "3"  # Converted to string as per class definition


def test_date():
    data = dict(modified="2023-10-11 12:32:00")

    app = DateConfig(data, None)
    assert app
    assert app.modified == datetime(2023, 10, 11, 12, 32, 00)


def test_various():
    data = dict(
        myenum="LAST",
        std_dict_no_types={"a": "aa"},
        std_dict={"a": 11},
        mypath="c:\\temp",
        mydecimal="0.1",
        myemail="juergen.donnerstag@neverland.de",
        existing_file="readme.md",
        existing_dir=".",
    )

    app = VariousConfig(data, None)
    assert app
    assert app.myenum == MyEnum.LAST
    assert app.std_dict_no_types == {"a": "aa"}
    assert app.std_dict == {"a": 11}
    assert app.mypath == Path("c:\\temp")
    assert app.mydecimal == Decimal("0.1")
    assert app.myemail == "juergen.donnerstag@neverland.de"
    assert app.existing_file == Path("readme.md")
    assert app.existing_dir == Path(".")
