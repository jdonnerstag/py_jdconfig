#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage parsing yaml values with placeholders, such as
```
  db_user: '{env: DB_USER, ???}'
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes. Because '{}'
is a valid yaml/json construct.
"""

import logging
from typing import Iterator, Optional

from . import placeholders as ph
from .string_converter_mixin import StringConverterMixin
from .utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


ValueType = int | float | bool | str | ph.Placeholder

RegistryType = dict[str, ph.Placeholder]


class ValueReader(StringConverterMixin):
    """Maintain a registry of supported placeholders and parse a yaml value
    into its constituent parts.

    E.g. "text", 1_000, 1.4, 1e3, True, Yes, "/tmp/{ref:a}-{ref.b}.txt".

    Either return the literal value converted into str, int, float, bool,
    or a list of literals and Placeholders, such as
    `["/tmp/", RefPlaceholder("a"), "-", RefPlaceholder("b"), ".txt"]`
    """

    def __init__(self, registry: Optional[RegistryType] = None) -> None:
        """Constructor

        :param registry: An optional dict of name and Placeholder handlers pairs
        """

        # The registry is publically accessible and users may add, remove, or
        # modify the entries. The 'name' (dict key) will be used to identify
        # the Placeholder handler. E.g. as in the default below, '{ref:a}' will
        # apply the RefPlaceholder,
        self.registry = registry

        if registry is None:
            # Initialize the registry with default Placeholders
            self.registry = {
                "ref": ph.RefPlaceholder,
                "global": ph.GlobalRefPlaceholder,
                "import": ph.ImportPlaceholder,
                "env": ph.EnvPlaceholder,
                "timestamp": ph.TimestampPlaceholder,
            }

    def parse(
        self, strval: str, *, sep: str = ",", registry: Optional[RegistryType] = None
    ) -> Iterator[ValueType]:
        """Parse a yaml value and yield the various parts.

        Notes:
        - It does not parse deep, e.g. {ref: db, {env:DB}} will create
          a reference for "db", but '{env:DB}' will not.
        - Trailing separators are ok: {ref: db,}
        - Placeholder arguments are not required to be in quotes, e.g.
          '{ref: "./db/{ref:db}"}' == '{ref: ./db/{ref:db}}'

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual parts of the yaml string value
        """

        for text in self.tokenize(strval, sep):
            if text == sep:
                pass
            elif len(text) > 0 and text[0] in ["'", '"']:
                yield value
            elif text.startswith("{"):
                placeholder = self.parse_placeholder(text, sep, registry)
                yield placeholder
            else:
                value = self.convert(text)
                yield value

    def parse_placeholder(
        self, strval: str, sep: str, registry: Optional[RegistryType] = None
    ) -> ph.Placeholder:
        """Parse {<name>: <arg-1>, ...} into registered Placeholder objects"""

        strval = strval[1:-1]
        i = strval.find(":")
        if i == -1:
            raise ConfigException(
                f"Expected to find placeholder name separated by colon: '{strval}'"
            )

        name = strval[:i].strip()
        if not name:
            raise ConfigException(f"Missing placeholder name in '{strval}'")

        if registry is None:
            registry = self.registry

        if name not in registry:
            raise ConfigException(f"Unknown placeholder name: '{name}' in '{strval}'")

        args = []
        same = False
        for text in self.tokenize(strval[i + 1 :], sep):
            if not args and text == sep:
                raise ConfigException(f"Unexpected ',' in f'{strval}'")

            if text == sep:
                same = False
                continue

            if len(text) > 1 and text[0] in ["'", '"']:
                text = text[1:-1]

            if not same:
                args.append(text)
                same = True
            else:
                args[-1] += text

        return registry[name](*args)

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
            ch = strval[i]  # pylint: disable=invalid-name
            if ch == "\\":
                i += 2
            elif ch in [sep, "'", '"', "{"]:
                value = strval[start:i].strip()
                start = i
                if value:
                    yield value

            if ch in ['"', "'"]:
                i = cls.find_quote_end(strval, i)
                value = strval[start:i].strip()
                start = i
                yield value
            elif ch == "{":
                i = cls.find_bracket_end(strval, i)
                value = strval[start:i].strip()
                start = i
                yield value
            elif ch == sep:
                i += 1
                start = i
                yield ch
            else:
                i += 1

        if start < len(strval):
            value = strval[start:].strip()
            if value:
                yield value

    @classmethod
    def find_quote_end(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a quote or placeholder

        :param strval: Input yaml string value
        :param end_ch: the end of the section
        :param start: position where the quote starts
        :return: position where the quote ends
        """

        end_ch = strval[start]
        i = start + 1
        while i < len(strval):
            char = strval[i]
            if char == "\\":
                i += 1
            elif char == end_ch:
                return i + 1

            i += 1

        raise ConfigException(f"Missing section close: '{strval}'")

    @classmethod
    def find_bracket_end(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a quote or placeholder

        :param strval: Input yaml string value
        :param end_ch: the end of the section
        :param start: position where the quote starts
        :return: position where the quote ends
        """

        count = 1
        i = start + 1
        while i < len(strval):
            char = strval[i]
            if char == "\\":
                i += 1
            elif char == "{":
                count += 1
            elif char == "}":
                count -= 1
                if count == 0:
                    return i + 1

            i += 1

        raise ConfigException(f"Missing section close: '{strval}'")
