#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from jd_config import StringConverterMixin
import pytest

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

def test_convert_bool():

    assert StringConverterMixin.convert_bool("false") == False
    assert StringConverterMixin.convert_bool("False") == False
    assert StringConverterMixin.convert_bool("faLsE") == False
    assert StringConverterMixin.convert_bool("no") == False
    assert StringConverterMixin.convert_bool("NO") == False
    assert StringConverterMixin.convert_bool("0") == False
    assert StringConverterMixin.convert_bool("true") == True
    assert StringConverterMixin.convert_bool("TrUE") == True
    assert StringConverterMixin.convert_bool("yes") == True
    assert StringConverterMixin.convert_bool("1") == True

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
    assert StringConverterMixin.convert("text") == "text"
    assert StringConverterMixin.convert("0.3.4") == "0.3.4"
    assert StringConverterMixin.convert("true") == True
    assert StringConverterMixin.convert("no") == False
