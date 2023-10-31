#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any
from jd_config.config_base_model import ConfigBaseModel
from jd_config.placeholders import Placeholder
from jd_config.resolver_mixin import MissingConfigException


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ResolvableBaseModel(ConfigBaseModel):
    """xxx"""
