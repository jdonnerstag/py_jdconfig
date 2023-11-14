#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging

import pytest

from jd_config import StringConverter

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_convert_bool():
    assert StringConverter.convert_bool("false") is False
    assert StringConverter.convert_bool("False") is False
    assert StringConverter.convert_bool("faLsE") is False
    assert StringConverter.convert_bool("no") is False
    assert StringConverter.convert_bool("NO") is False
    assert StringConverter.convert_bool("0") is False
    assert StringConverter.convert_bool("true") is True
    assert StringConverter.convert_bool("TrUE") is True
    assert StringConverter.convert_bool("yes") is True
    assert StringConverter.convert_bool("1") is True

    with pytest.raises(KeyError):
        StringConverter.convert_bool("2")

    with pytest.raises(KeyError):
        StringConverter.convert_bool("10")

    with pytest.raises(KeyError):
        StringConverter.convert_bool("00")

    with pytest.raises(KeyError):
        StringConverter.convert_bool("truex")


def test_convert():
    assert StringConverter.convert("0") == 0
    assert StringConverter.convert("1") == 1
    assert StringConverter.convert("2") == 2
    assert StringConverter.convert("-1") == -1
    assert StringConverter.convert("1.2") == 1.2
    assert StringConverter.convert("0.3") == 0.3
    assert StringConverter.convert("1e3") == 1000
    assert StringConverter.convert("1_000") == 1000
    assert StringConverter.convert("text") == "text"
    assert StringConverter.convert("0.3.4") == "0.3.4"
    assert StringConverter.convert("true") is True
    assert StringConverter.convert("no") is False
