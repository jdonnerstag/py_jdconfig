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


class PlaceholderException(ConfigException):
    """Placeholder related exception"""


class ValueReaderException(ConfigException):
    """ValueReader related exception"""


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

    def parse(self, strval: str, *, sep: str = ",") -> Iterator[ValueType]:
        """Parse a yaml value (leaf node) and yield the various parts.

        The YAML parser has applied its char escapes already, and also chars
        like "&#58;" should be converted already. However every parser seems
        to be somewhat different. This implementation applies '\\' for escaping
        on top of whatever is provided as input.

        The YAML parser will pass on surrounding quotes as in 'a: "text"'. They
        are automatically removed.

        Similar to python, r".." yields the text verbatim, without any further
        parsing.

        Notes:
        - It does not parse deep, e.g. {ref: db, {env:DB}} will create
          a reference for "db", but '{env:DB}' will remain text.
        - Trailing separators are ok: {ref: db,}
        - Placeholder arguments are not required to be in quotes, e.g.
          '{ref: "./db/{ref:db}"}' == '{ref: ./db/{ref:db}}'

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual parts of the yaml string value
        """

        if not isinstance(strval, str):
            raise ValueReaderException(
                f"Bug: only string values can be parsed: '{strval}'"
            )

        # Make sure we yield at least ones, even if value is empty.
        if not strval:
            return

        # Handle special case r"..", which is similar to python. It is
        # considered raw text and will not be parsed or anything.
        if self.is_raw_text(strval):
            yield strval[2:-1]
            return

        for text in self.split_yaml_value(strval):
            if text.startswith("{"):
                placeholder = self.parse_placeholder(text, sep)
                yield placeholder
            else:
                value = self.convert(text)
                yield value

    @classmethod
    def is_raw_text(cls, strval: str) -> bool:
        """True if string matches raw text pattern: r'..'"""
        if strval.startswith("r") and len(strval) >= 3:
            quote_1 = strval[1]
            quote_2 = strval[-1]
            if quote_1 in ["'", '"'] and quote_2 == quote_1:
                return True

        return False

    @classmethod
    def split_yaml_value(cls, strval: str) -> Iterator[str]:
        """Split the yaml value into text and placeholders

        E.g. "a {b}c" => ["a ", "{b}", "c"]

        Backslash is used to escape characters. But the backslash will not be removed.

        :param strval: Input yaml string value
        :return: Generator yielding individual string tokens
        """

        start = 0
        i = 0
        while i < len(strval):
            ch = strval[i]  # pylint: disable=invalid-name
            if ch == "\\":
                i += 2
            elif ch == "{":
                value = strval[start:i]
                if value.strip():  # ignore whitespace only
                    yield value  # but pass on any whitespaces

                start = i
                i = cls.find_bracket_end(strval, i)
                value = strval[start:i]
                yield value
                start = i
            else:
                i += 1

        if start < len(strval):
            value = strval[start:]
            if value.strip():  # ignore whitespace only
                yield value  # but pass on any whitespaces

    def parse_placeholder(self, strval: str, sep: str) -> ph.Placeholder:
        """Parse {<name>: <arg-1>, ...} into a registered Placeholder object"""

        # Remove the brackets
        strval = strval[1:-1]

        # Determine the placeholder's name
        i = strval.find(":")
        if i == -1:
            raise PlaceholderException(
                f"Expected to find placeholder name separated by colon: '{strval}'"
            )

        name = strval[:i].strip()
        if not name:
            raise PlaceholderException(f"Missing placeholder name in '{strval}'")

        if name not in self.registry:
            raise PlaceholderException(
                f"Unknown placeholder name: '{name}' in '{strval}'"
            )

        # Determine the parameters
        args = list(self.tokenize_placeholder_args(strval[i + 1 :], sep))

        try:
            return self.registry[name](*args)
        except Exception as exc:
            raise PlaceholderException(
                f"Error while instantiating Placeholder: '{strval}'"
            ) from exc

    @classmethod
    def tokenize_placeholder_args(cls, strval: str, sep: str = ",") -> Iterator[str]:
        """Tokenize the placeholder parameters: {ref: ...}

        Parameters are separated by "," (by default). Whitespaces around
        separators are stripped.
        Trailing separator is allowed: {ref:a,}. Nothing will be yielded
        for the 2nd argument.
        Strings can optionally be quoted: '..', ".." as in {ref:'a'}
        Parameters are converted in int, float, bool if possible. Else,
        they remain strings.
        Parameters are not analysed any further, e.g. '{ref:a, {ref:b}}'
        will yield ["a", "{ref:b"}]

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual string tokens
        """

        start = 0
        i = 0
        while i < len(strval):
            start = i
            i = cls.find_next_sep(strval, start, sep=sep)
            value = strval[start:i].strip()
            if len(value) > 2 and value[0] in ["'", '"'] and value[0] == value[-1]:
                value = value[1:-1]

            if start == 0 and not value:
                raise ValueReaderException(
                    f"Config value: unexpected separator: '{strval}'"
                )

            value = cls.convert(value)
            yield value

            i += 1

    @classmethod
    def find_next_sep(cls, strval: str, start: int, sep: str = ",") -> int:
        """Find the next separator.

        Jump over any quoted text.
        Jump over any placeholders {..}

        :param strval: Input string
        :param start: Current position within the string
        :param sep: The separator
        :return: position following the closing bracket
        """
        i = start
        while i < len(strval):
            char = strval[i]
            if char == "\\":
                i += 2
            elif char == "{":
                i = cls.find_bracket_end(strval, i)
            elif char in ["'", '"']:
                i = cls.find_quote_end(strval, i)
            elif char == sep:
                return i
            else:
                i += 1

        return i

    @classmethod
    def find_bracket_end(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a bracket {}.

        Backslash is used to escape characters. But the backslash will not be removed.

        Quoted text ("..", '..') will be skipped.

        Brackets can be nested, e.g. {a: b:{..}}

        :param strval: Input yaml string value
        :param start: position where the bracket starts
        :return: position following the closing bracket
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
            elif char in ["'", '"']:
                i = cls.find_quote_end(strval, i) - 1

            i += 1

        raise ValueReaderException(f"Missing closing bracket in '{strval}'")

    @classmethod
    def find_quote_end(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a quote

        Backslash is used to escape characters. But the backslash will not be removed.

        Any text in between the quotes, will not be analysed.

        :param strval: Input yaml string value
        :param start: position where the quote starts
        :return: position following the quote ends
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

        raise ValueReaderException(f"Missing closing quote in '{strval}'")
