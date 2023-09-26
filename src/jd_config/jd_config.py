#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

import os
import logging
import configparser
from typing import Any, Iterator,  Mapping, Optional
import yaml
from .placeholder import ImportPlaceholder, Placeholder, ValueReader
from .placeholder import CompoundValue
from .objwalk import objwalk, NodeEvent, NewMappingEvent, NewSequenceEvent, DropContainerEvent
from .config_getter import ConfigGetter, ConfigException, PathType, DEFAULT
from .yaml_loader import MyYamlLoader, YamlObj


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class EnvInterpolation(configparser.BasicInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)
        return os.path.expandvars(value)


class JDConfig:
    """Main class load and access config values.
    """

    def __init__(self, *, ini_file: str = "config.ini") -> None:
        """Initialize.

        User and Config specific configurations are kept separate.
        'JDConfig' can be configured by means of 'config.ini'

        Only the '[config]' section will be used. Everything else will
        be ignored. The following keys (and default values) are supported.

        ```
        [config]
        config_dir = .
        config_file = config.yaml
        env_var =
        default_env = prod
        ```

        Some of the JDConfig configs determine where to find the user
        specific configurations files, including environment specific
        overlays.

        :param ini_file: Path to JDConfig config file. Default: 'config.ini'
        """

        config = configparser.ConfigParser(interpolation=EnvInterpolation())
        if ini_file:
            logger.debug("Config: Load ini-file: '%s'", ini_file)
            config.read(ini_file)

        try:
            config = config["config"]
        except KeyError:
            config = {}

        self.config_dir = config.get("config_dir", ".")
        self.config_file = config.get("config_file", "config.yaml")
        self.default_env = config.get("default_env", None)
        self.env = config.get("env", self.default_env)

        # The yaml config data after loading them
        self.data = None

        # Read string into Placeholders ...
        self.value_reader = ValueReader()

        # The list of yaml files loaded
        self.files_loaded = []
        self.file_recursions = []

    def load_yaml_raw_fd(self, fd) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fd: a file descriptor
        :return: A deep dict-like structure, representing the yaml content
        """
        loader = MyYamlLoader(fd)
        return loader.get_single_data()

    def load_yaml_raw(self, fname: os.PathLike) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fname: the yaml file to load
        :return: A deep dict-like structure, representing the yaml content
        """

        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        logger.debug("Config: Load from file: '%s'", fname)
        with open(fname, "rb") as fd:
            return self.load_yaml_raw_fd(fd)

    def load(self,
        fname: Optional[os.PathLike] = None,
        config_dir: Optional[os.PathLike] = None
    ) -> Mapping:
        """Load a Yaml config file, and if an env var is defined, also load
        the environment specific overlay.
        """
        # Load the yaml file, including all imports
        _data = self.load_one_file(fname, config_dir)

        if self.env:
            fname, oldext = os.path.splitext(fname)
            fname = fname + "-" + self.env + oldext
            data_2 = self.load_one_file(fname, config_dir)
            _data.update(data_2)

        # Make the yaml config data accessible via JDConfig
        self.data = _data
        return _data

    def load_one_file(self,
        fname: Optional[os.PathLike] = None,
        config_dir: Optional[os.PathLike] = None
    ) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in config.ini
        """

        if fname is None:
            fname = self.config_file

        if config_dir is None:
            config_dir = self.config_dir

        if isinstance(fname, str):
            if not os.path.isabs(fname):
                fname = os.path.join(config_dir, fname)

            fname = os.path.abspath(fname)
            if fname in self.file_recursions:
                raise ConfigException(
                    "File recursion. The following config file gets imported "
                    f"in circles: '{fname}'")

            self.file_recursions.append(fname)
            self.files_loaded.append(fname)

            _data = self.load_yaml_raw(fname)
        else:
            # Assuming it is an IO stream of some sort
            _data = self.load_yaml_raw_fd(fname)
            self.files_loaded.append("<data>")

        _data = self.post_process(_data, config_dir)

        if isinstance(fname, str):
            self.file_recursions.pop()

        return _data

    def post_process(self, _data: Mapping, config_dir: os.PathLike) -> Mapping:
        """Replace '{..}' with Placeholders and execute imports if needed.

        :param _data: the yaml data loaded already
        :return: the updated yaml data with imports replaced.
        """

        imports: dict[Any, ImportPlaceholder] = {}
        for event in objwalk(_data, nodes_only=True):
            value = event.value.value
            if isinstance(value, str) and value.find("{") != -1:
                event.value.value = value = CompoundValue(self.value_reader.parse(value))
                if value.is_import():
                    imports[event.path] = value[0]

            if isinstance(value, Placeholder):
                value.post_load(_data)
            elif isinstance(value, list):
                for elem in value:
                    if isinstance(elem, Placeholder):
                        elem.post_load(_data)

        for path, obj in imports.items():
            fname = self.resolve(obj.file, _data)
            import_data = self.load(fname, config_dir)
            if obj.replace:
                ConfigGetter.delete(_data, path)
                _data.update(import_data)
            else:
                ConfigGetter.set(_data, path, import_data)

        return _data

    def resolve(self, value: Any, _data: Optional[Mapping] = None):
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a CompoundValue will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        key = value
        if isinstance(value, Placeholder):
            value = value.resolve(_data)

        if isinstance(value, list):
            value = [self.resolve(x, _data) for x in value]
            value = "".join(value)
            return value

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '${key}'")

        if isinstance(value, (str, int, float, bool)):
            return value

        raise ConfigException(f"Unable to resolve: '${value}'")

    def get(self, path: PathType, default: Any = DEFAULT, *, sep: str=".") -> Any:
        """Similar to dict.get(), but with deep path support.

        Placeholders are automatically resolved.
        Mappings and Sequences are returned as is.
        """

        try:
            obj = ConfigGetter.get(self.data, path, sep=sep)
            if not isinstance(obj, YamlObj):
                return obj

            value = self.resolve(obj.value, self.data)
            return value
        except:     # pylint: disable=bare-except
            return default

    def delete(self, path: PathType, *, sep: str=".", exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support
        """
        return ConfigGetter.delete(self.data, path, sep=sep, exception=exception)


    def set(self, path: PathType, value: Any, *, create_missing: [callable, bool, dict]=True, sep: str=".") -> Any:
        """Similar to 'dict[key] = valie', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.
        """

        return ConfigGetter.set(self.data, path, value, create_missing=create_missing, sep=sep)


    def walk(self, root: Optional[PathType] = None, resolve: bool = True
        ) -> Iterator[NodeEvent]:
        """Walk the config items with an optional starting point

        :param root: An optional starting point.
        :param resolve: If true (default), then resolve all Placeholders
        :return: Generator, yielding a Tuple
        """

        obj = self.data
        if root:
            obj = self.get(root)

        for event in objwalk(obj, nodes_only=True):
            if resolve:
                event.value = self.resolve(event.value.value, self.data)

            yield event


    def to_dict(self, root: Optional[PathType] = None, resolve: bool = True) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        obj = self.data
        if root:
            obj = self.get(root)

        stack = []
        for event in objwalk(obj, nodes_only=False):
            if isinstance(event, (NewMappingEvent, NewSequenceEvent)):
                if isinstance(event, NewMappingEvent):
                    new = {}
                else:
                    new = []
                stack.append(new)
                if event.path:
                    if isinstance(cur, Mapping):
                        cur[event.path[-1]] = new
                    else:
                        cur.append(new)
                cur = new
            elif isinstance(event, DropContainerEvent):
                stack.pop()
                if stack:
                    cur = stack[-1]
            elif isinstance(event, NodeEvent):
                value = event.value
                if resolve:
                    value = self.resolve(event.value.value, self.data)

                if isinstance(cur, Mapping):
                    cur[event.path[-1]] = value
                else:
                    cur.append(value)

        return cur

    def to_yaml(self, root: Optional[PathType] = None, stream = None, **kvargs):
        """Convert the configs (or part of it), into a yaml document
        """

        data = self.to_dict(root, resolve=True)
        return yaml.dump(data, stream, **kvargs)

    def register_placeholder(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler
        """

        self.value_reader.registry[name] = type_
