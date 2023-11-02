#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A collection of easy to use Type for config values.

E.g. 'email: Email', or 'modified: Date["%Y-%m-%d"]'
"""

import logging
import os
import re
from pathlib import Path
from typing import Annotated

from jd_config.utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

# Check out https://python-validators.github.io/validators/reference/email/ for all
# sorts of validators


def is_email_address(text: str) -> str:
    m = re.match(
        r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
        r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$",
        text,
    )

    if m is not None:
        return text

    raise ConfigException(f"Not a valid email address: '{text}")


EmailType = Annotated[str, is_email_address]


def file_existing(fname: str) -> Path:
    if os.path.isfile(fname):
        return Path(fname)

    raise ConfigException(f"File not found: '{fname}")


def directory_existing(fname: str) -> Path:
    if os.path.isdir(fname):
        return Path(fname)

    raise ConfigException(f"Directory not found: '{fname}")


ExistingFileType = Annotated[Path, file_existing]
ExistingDirectoryType = Annotated[Path, directory_existing]

# TODO
# DATE["%Y%m%d"]
