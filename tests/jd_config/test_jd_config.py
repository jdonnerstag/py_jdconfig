#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import os
import logging
from jd_config import JDConfig, ConfigGetter

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

def test_run(caplog):
    caplog.set_level(level=logging.DEBUG)

    data = JDConfig().load(os.path.abspath("./configs/main_config.yaml"))
    assert ConfigGetter.get(data, "version").value == 1
