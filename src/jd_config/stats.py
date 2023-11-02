#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Config stats such as
- number of config values
- list imported files
- number of {ref:}
- max depth
- list of envs referenced
...

"""

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from .placeholders import EnvPlaceholder

if TYPE_CHECKING:
    from .jd_config import JDConfig

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigStats:
    """Config Stats"""

    def __init__(self) -> None:
        # Use to_dict and count the node_events
        self.value_count: int = 0
        # Use to_dict and count the mapping_events
        self.dict_count: int = 0
        # Use to_dict and count the list_events
        self.list_count: int = 0
        # Can also be done while walking: len(path)
        self.max_depth: int = 0
        # Because of defaults, env overlays, etc. there is a difference
        # between used (resolve()) and present in the files.
        # Search the dict of placeholder handlers to find the name for the EnvPlaceholder
        self.envvars: set[str] = set()
        # Something that works with remote configs as well
        # Some as with envvars: difference between used and present
        # Maybe to_dict(resolve=False) and search for "{name:}" pattern in the values?
        self.placeholders: dict[str, int] = {}
        # The file loader creates this list anyways
        self.files: list[Path] = []
        # Get from .ini[env]
        self.env_name: str | None = None
        # from config_ini_mixin
        self.ini_file: Path | None = None

    def create(self, cfg: "JDConfig"):
        """Create the stats"""

        self.env_name = cfg.env
        self.ini_file = cfg.ini_file

        self.files = cfg.files_loaded

        self.value_count = 0
        self.dict_count = 1 if isinstance(cfg.config(), Mapping) else 0
        self.list_count = 0
        self.max_depth = 0
        for event in cfg.walk(nodes_only=False, resolve=True):
            if isinstance(event, NodeEvent):
                self.value_count += 1
                self.max_depth = max(self.max_depth, len(event.path))
            elif isinstance(event, NewMappingEvent):
                self.dict_count += 1
            elif isinstance(event, NewSequenceEvent):
                self.list_count += 1

        self.envvars = set()
        self.placeholders = {}

        for i, fd in enumerate(self.files):
            if i == 0:
                data = cfg.config().obj
            else:
                data = cfg.load_import(fd)

            for event in objwalk(data, nodes_only=True):
                self.parse_value(cfg, event.value, self.envvars, self.placeholders)

        return self

    def parse_value(self, cfg, value, envvars, placeholders) -> int:
        """Quickly parse the config value for placeholders"""

        if not isinstance(value, str):
            return 0

        # Find all OVERLAPPING sections matching the pattern
        # https://stackoverflow.com/questions/5616822/how-to-use-regex-to-find-all-overlapping-matches
        count = 0
        for match in re.finditer(r"(?=(\{\s*(\w+)\s*\:.*?\}))", value):
            count += 1

            _ph_text = match.group(1)
            name = match.group(2)
            placeholders[name] = placeholders.get(name, 0) + 1

            if name != "env":
                continue

            for elem in cfg.value_reader.parse(value):
                if isinstance(elem, EnvPlaceholder):
                    envvars.add(elem.env_var)

        return count

    def __str__(self) -> str:
        data = vars(self)
        rtn = json.dumps(data, cls=SetEncoder, indent=4)
        return rtn

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)})"


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, Path):
            return str(obj)

        return json.JSONEncoder.default(self, obj)
