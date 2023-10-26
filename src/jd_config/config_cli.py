#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A little cli to dump configs, list stats, find keys or values, ...
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jd_config.config_ini_mixin import IniData
from jd_config.config_path_extended import ExtendedCfgPath
from jd_config.file_loader import ConfigFile
from jd_config.jd_config import JDConfig
from jd_config.string_converter_mixin import StringConverterMixin
from jd_config.utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


def config_cli(args):
    args = parse_cli_args(args)

    logging.basicConfig(level=args.loglevel.upper())

    if args.ini_file == "None":
        args.ini_file = None

    cfg = JDConfig(ini_file=args.ini_file)

    # TODO move into JDConfig or better even config_ini_mixin.
    update_ini_with_cli_args(cfg.ini, args)

    # TODO Maybe replace load() to return self.
    data = cfg.load(fname=args.cfg_file, config_dir=args.cfg_dir, env=args.env)
    if isinstance(data.obj, ConfigFile):
        data.obj.add_cli_args(analyse_set_args(args.set))

    data = cfg.resolve_all()

    # parser.add_argument("--print", help="Optional args: path")
    # parser.add_argument("--json", help="")
    # parser.add_argument("--yaml", help="")
    # parser.add_argument("--stats", help="")
    # parser.add_argument("--find", help="in key or value")


def analyse_set_args(set_args: str | list[str]):
    rtn = {}
    if isinstance(set_args, list):
        for i in set_args:
            rtn.update(analyse_set_args(i))

        return rtn

    if "=" not in set_args:
        raise ConfigException(f"Invalid CLI set parameter: '{set_args}'")

    key, value = set_args.split("=", maxsplit=1)
    key = ExtendedCfgPath(key)
    value = StringConverterMixin.convert(value)

    elem = rtn
    for i in key[:-1]:
        elem = elem[i] = {}

    elem[key[-1]] = value

    return rtn


def update_ini_with_cli_args(ini: IniData, args):
    if args.cfg_dir:
        ini.config_dir = args.cfg_dir

    if args.cfg_file:
        ini.config_file = args.cfg_file

    if args.env:
        ini.env = args.env

    if args.add_env_dir:
        add_env_dir = args.add_env_dir
        if not isinstance(add_env_dir, list):
            add_env_dir = [add_env_dir]
        ini.add_env_dirs = add_env_dir

    if args.default_env:
        ini.default_env = args.default_env

    return ini


def parse_cli_args(args):
    parser = argparse.ArgumentParser(
        prog="Config Management",
        description="Make arbitrary configs easily accessible to app",
    )

    parser.add_argument(
        "--ini_file",
        metavar="FILE",
        default="config.ini",
        help="Defaults to ./config.ini",
    )
    parser.add_argument("--cfg_dir", metavar="DIR", help="Defaults to ./configs")
    parser.add_argument("--cfg_file", metavar="FILE", help="Defaults to config.yaml")
    parser.add_argument("--env", help="The config environment, e.g. dev, test, prod")
    parser.add_argument(
        "--add_env_dir",
        nargs="+",
        metavar="DIR",
        help="Additional directories to scan for environment overlay files. Default: './'",
    )
    parser.add_argument(
        "--default_env",
        metavar="ENV",
        help="If default config environment, if not nothing else defined",
    )
    parser.add_argument(
        "--set",
        nargs="+",
        metavar="VALUE",
        help="Set a config value",
    )
    parser.add_argument(
        "--print", metavar="CFG-PATH", nargs="?", help="Optional args: path"
    )
    parser.add_argument("--json", action="store_true", help="")
    parser.add_argument("--yaml", action="store_true", help="")
    parser.add_argument("--stats", action="store_true", help="")
    parser.add_argument("--find", metavar="VALUE", help="in key or value")
    parser.add_argument(
        "--loglevel",
        default="warning",
        help="Provide logging level. Example --loglevel debug. Default=warning",
    )

    return parser.parse_args(args)


if __name__ == "__main__":
    config_cli(sys.argv[1:])
