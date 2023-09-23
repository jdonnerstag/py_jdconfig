#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import logging
from jd_config import JDConfig, ConfigGetter

logger = logging.getLogger(__name__)



if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    data = JDConfig().load(os.path.abspath("./configs/main_config.yaml"))
    assert ConfigGetter.get(data, "version").value == 1
