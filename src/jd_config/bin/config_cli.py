#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A little cli to dump configs, list stats, find keys or values, ...
"""

import argparse
import json
import logging
import sys
import pprint
from pathlib import Path

import yaml

# We need to define the root of the package for python to be able to import the modules
sys.path.append(str(Path(__file__).parent.parent.parent))

# pylint: disable=wrong-import-position
from jd_config.objwalk import NodeEvent
from jd_config.config_ini import IniData
from jd_config.config_path_extended import ExtendedCfgPath
from jd_config.deep_dict_mixin import DeepDictMixin
from jd_config.file_loader import ConfigFile
from jd_config.jd_config import JDConfig
from jd_config.stats import ConfigStats
from jd_config.string_converter import StringConverter
from jd_config.utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


def config_cli(args):
    """Process and execute the CLI: main entry point"""

    args = parse_cli_args(args)

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=args.loglevel.upper(), format=fmt)

    if args.ini_file == "None":
        args.ini_file = None

    cfg = JDConfig(ini_file=args.ini_file)

    # TODO move into JDConfig or better even config_ini.
    update_ini_with_cli_args(cfg.ini, args)

    # TODO Maybe replace load() to return self, or ConfigFile?
    data = cfg.load(fname=args.cfg_file, config_dir=args.cfg_dir, env=args.env)
    if isinstance(data.obj, ConfigFile):
        data.obj.add_cli_args(analyse_set_args(args.set))

    if args.stats:
        # Print the statistics
        stats = ConfigStats().create(cfg)
        print(stats, file=sys.stdout)
        return

    # Resolve all placeholders, imports etc.
    data = cfg.resolve_all()

    if args.print is not None:
        # Print all or parts (path) of the config
        exec_print(cfg, args.print, args.yaml, sys.stdout)
        return

    if args.find is not None:
        # Find key or values containing the <pattern>
        exec_find(cfg, args.find)
        return


def exec_print(cfg: JDConfig, path: str, print_yaml=False, out=sys.stdout):
    """Execute the --print cli argument"""

    data = cfg.get(path, resolve=True)
    if isinstance(data, DeepDictMixin):
        data = data.obj

    if print_yaml is True:
        yaml.dump(data, out, indent=4)
    else:
        json.dump(data, out, indent=4)


def exec_find(cfg: JDConfig, pattern: str, out=sys.stdout):
    """Execute the --find cli argument"""

    for node in cfg.walk(nodes_only=True, resolve=True):
        if not isinstance(node, NodeEvent):
            continue

        if node.path and pattern in node.path[-1]:
            data = {node.path.to_str(), node.value}
            pprint.pprint(data, stream=out)
        elif node.value and pattern in node.value:
            data = {node.path.to_str(), node.value}
            pprint.pprint(data, stream=out)


def analyse_set_args(set_args: str | list[str]):
    """The --set cli argument allows to set/overwrite config value

    Examples:
    --set a=b
    --set a.b.c=20

    For everything more complicated, please use env overlay files.
    """
    if set_args is None:
        return None

    rtn = {}
    if isinstance(set_args, list):
        for i in set_args:
            rtn.update(analyse_set_args(i))

        return rtn

    if "=" not in set_args:
        raise ConfigException(f"Invalid CLI set parameter: '{set_args}'")

    key, value = set_args.split("=", maxsplit=1)
    key = ExtendedCfgPath(key)
    value = StringConverter.convert(value)

    elem = rtn
    for i in key[:-1]:
        elem = elem[i] = {}

    elem[key[-1]] = value

    return rtn


def update_ini_with_cli_args(ini: IniData, args):
    """Apply the cli arguments relevant to initialize IniData"""

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
        ini.env_dirs = add_env_dir

    return ini


def parse_cli_args(args):
    """Configure argparse with the CLI arguments and parse the command-line"""

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
        "--set",
        nargs="+",
        metavar="VALUE",
        help="Set a config value",
    )
    parser.add_argument(
        "--print", metavar="CFG-PATH", nargs="?", const="", help="Optional args: path"
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
