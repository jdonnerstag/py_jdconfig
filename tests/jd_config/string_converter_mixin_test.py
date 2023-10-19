#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging

import pytest

from jd_config import StringConverterMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_convert_bool():
    assert StringConverterMixin.convert_bool("false") is False
    assert StringConverterMixin.convert_bool("False") is False
    assert StringConverterMixin.convert_bool("faLsE") is False
    assert StringConverterMixin.convert_bool("no") is False
    assert StringConverterMixin.convert_bool("NO") is False
    assert StringConverterMixin.convert_bool("0") is False
    assert StringConverterMixin.convert_bool("true") is True
    assert StringConverterMixin.convert_bool("TrUE") is True
    assert StringConverterMixin.convert_bool("yes") is True
    assert StringConverterMixin.convert_bool("1") is True

    with pytest.raises(KeyError):
        StringConverterMixin.convert_bool("2")

    with pytest.raises(KeyError):
        StringConverterMixin.convert_bool("10")

    with pytest.raises(KeyError):
        StringConverterMixin.convert_bool("00")

    with pytest.raises(KeyError):
        StringConverterMixin.convert_bool("truex")


def test_convert():
    assert StringConverterMixin.convert("0") == 0
    assert StringConverterMixin.convert("1") == 1
    assert StringConverterMixin.convert("2") == 2
    assert StringConverterMixin.convert("-1") == -1
    assert StringConverterMixin.convert("1.2") == 1.2
    assert StringConverterMixin.convert("0.3") == 0.3
    assert StringConverterMixin.convert("1e3") == 1000
    assert StringConverterMixin.convert("1_000") == 1000
    assert StringConverterMixin.convert("text") == "text"
    assert StringConverterMixin.convert("0.3.4") == "0.3.4"
    assert StringConverterMixin.convert("true") is True
    assert StringConverterMixin.convert("no") is False
