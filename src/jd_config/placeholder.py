#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

from abc import ABC, abstractmethod
import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Optional, Union
from .config_getter import ConfigException, ConfigGetter
from .convert import convert


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)



ValueType = Union[int, float, bool, str, 'Placeholder']

class CompoundValue(list):
    """A Yaml value that consists of multiple parts.

    E.g. Upon reading the yaml file, a value such as "test-{ref:database}-url"
    will be preprocessed and split into 3 parts: "test-", <Placeholder>, and "-url".
    All part together make CompoundValue, with few helper. E.g. resolve
    the placeholders and determine the actual value.
    """

    def __init__(self, values: Iterator[ValueType]) -> None:
        super().__init__(list(values))

    def is_import(self) -> bool:
        """Determine if one the parts is a '{import:..}' placeholder
        """

        for elem in self:
            if isinstance(elem, ImportPlaceholder):
                # Import Placeholders must be standalone.
                if len(self) != 1:
                    raise ConfigException("Invalid '{import: ...}', ${elem}")

                return True

        return False


class Placeholder(ABC):
    """A common base class for all Placeholders
    """

    def post_load(self, _data: Mapping) -> None:
        """A hook that gets invoked after the yaml file has been loaded.

        E.g. to attach the file root dict with a Placeholder.

        :param _data: The dict associated with the file
        """

    @abstractmethod
    def resolve(self, data: Mapping):
        """Resolve the placeholder"""

@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'
    """

    file: str
    replace: bool = False

    def __post_init__(self):
        assert self.file

    def resolve(self, data: Mapping):
        pass     # Nothing to do

@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'
    """

    path: str
    default_val: Any = None
    file_root: Optional[Mapping] = None

    def __post_init__(self):
        assert self.path

    def post_load(self, _data: Mapping) -> None:
        self.file_root = _data

    def resolve(self, data: Mapping):
        # 1. Search in the yaml file which contains the reference
        if self.file_root:
            try:
                obj = ConfigGetter.get(self.file_root, self.path, sep = ",")
                return obj.value
            except:     # pylint: disable=bare-except
                pass

        # 2. Search starting from the root of all the config files.
        obj = ConfigGetter.get(data, self.path, sep = ",", default = self.default_val)
        return obj.value


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'
    """

    env_var: str
    default_val: Any = None

    def __post_init__(self):
        assert self.env_var

    def resolve(self, _) -> str:
        value = os.environ.get(self.env_var, self.default_val)
        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'
    """

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, _) -> str:
        now = datetime.now()
        value = now.strftime(self.format)
        return value


class ValueReaderException(ConfigException):
    """Denote an Exception that occured while parsing a yaml value (wiht placeholder)"""

class ValueReader:
    """Parse a yaml value
    """

    def __init__(self, registry: dict[str, Placeholder] = None) -> None:
        self.registry = registry

        if not self.registry:
            self.registry = {
                "ref": RefPlaceholder,
                "import": ImportPlaceholder,
                "env": EnvPlaceholder,
                "timestamp": TimestampPlaceholder,
            }


    def parse(self, strval: str, *, sep: str = ",") -> Iterator[ValueType]:
        """Parse a yaml value and yield the various parts.

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual parts of the yaml string value
        """

        _iter = self.tokenize(strval, sep)
        try:
            while text := next(_iter, None):
                if text == sep:
                    pass
                elif text == "{":
                    placeholder = self.parse_placeholder(_iter, sep)
                    yield placeholder
                elif isinstance(text, str) and text.find("{") != -1:
                    values = list(self.parse(text))
                    values = [self.convert(x) for x in values]
                    value = CompoundValue(values)
                    yield value
                else:
                    value = self.convert(text)
                    yield value

        except StopIteration as exc:
            raise ValueReaderException(
                f"Failed to parse yaml value with placeholder: '${strval}'") from exc

    def parse_placeholder(self, _iter: Iterator, sep: str) -> Placeholder:
        """Parse {<name>: <arg-1>, ...} into registered Placeholder objects
        """

        name = next(_iter)
        args = []
        compound = []

        colon = next(_iter)
        assert colon == ":"

        while text := next(_iter, None):
            if text in [sep, "}"]:
                if len(compound) == 1:
                    args.append(compound[0])
                elif len(compound) > 1:
                    args.append(CompoundValue(compound))
                compound.clear()

            if text == "{":
                placeholder = self.parse_placeholder(_iter, sep)
                compound.append(placeholder)
            elif text == "}":
                placeholder = self.registry[name](*args)
                return placeholder
            elif text != sep:
                if isinstance(text, str) and text.find("{") != -1:
                    values = list(self.parse(text))
                    values = [self.convert(x) for x in values]
                    value = CompoundValue(values)
                else:
                    value = self.convert(text)

                compound.append(value)

        raise ConfigException(f"Unexpected end: '{text}'")


    @classmethod
    def tokenize(cls, strval: str, sep: str = ",") -> Iterator[str]:
        """Tokenize the yaml string value

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual string tokens
        """

        start = 0
        i = 0
        while i < len(strval):
            ch = strval[i]
            if ch == "\\":
                i += 1
            elif ch in ['"', "'"]:
                i = cls.find_closing_quote(strval, i)
                value = strval[start + 2 : i]
                yield value
                start = i + 1
            elif ch in [sep, "{", "}", ":"]:
                value = strval[start : i].strip()
                if value:
                    yield value

                start = i + 1
                yield ch

            i += 1

        value = strval[start : ].strip()
        if value:
            yield value

    @classmethod
    def find_closing_quote(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a quote.

        The first character determine the quote, e.g. "'", '"'

        :param strval: Input yaml string value
        :param start: position where the quote starts
        :return: position where the quote ends

        """

        quote_char = strval[start]
        i = start + 1
        while i < len(strval):
            char = strval[i]
            if char == "\\":
                i += 1
            elif char == quote_char:
                return i

            i += 1

        return i - 1


    @classmethod
    def convert(cls, strval: Any) -> int | float | str | bool:
        """Convert a string into int, float or bool of possible, else
        return the string value.

        :param strval: Input yaml string value
        """
        return convert(strval)
