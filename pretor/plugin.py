# Copyright 2019 Charles A Daniels
# Distributed under the GNU AGPLv3 License (https://www.gnu.org/licenses/agpl.txt)

import importlib
import importlib.util
import pathlib
import logging
import sys
import argparse
import pdb
import tabulate

from . import g
from . import util
from . import constants

"""
This module handles pretor plugins.
"""

def plugin_cli():
    """plugin_cli"""

    parser = argparse.ArgumentParser("""CLI tool for displaying information
about loaded Pretor plugins. This tool is primarily for debugging Pretor
installations, and will likely only be of use to system administrators
and plugin developers.""")

    parser.add_argument("--version", action="version",
            version=constants.version)

    parser.add_argument("--debug", "-d", action="store_true", default=False,
            help="Log debugging output to the console.")

    parser.add_argument("--debugload", "-L", action="store_true", default=False,
            help="If a plugin fails to import, drop to a PDB shell.")

    parser.add_argument("--plugin_dir", "-D", default="./",
            help="Specify location where pretor plugins are stored. " +
            "(default: ./)")

    action = parser.add_mutually_exclusive_group(required=True)

    action.add_argument("--pdb", "-p", default=False, action="store_true",
            help="Drop to PDB shell after loading plugins.")

    action.add_argument("--list", "-l", default=False, action="store_true",
            help="List all loaded plugins")

    action.add_argument("--info", "-i", default=None, nargs=1,
            help="Display the description and other information for the " +
            "specified plugin.")

    args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    load_plugins(args.plugin_dir, args.debugload)

    if args.pdb:
        logging.info("--pdb asserted, dropping to PDB shell... ")
        pdb.set_trace()

    elif args.list:
        print(tabulate.tabulate(
            [(
                    k,
                    format_version(g.plugins[k].pretor_plugin_version),
                    ', '.join(g.plugins[k].pretor_plugin_hooks.keys()))
             for k in g.plugins], tablefmt="plain"))

    elif args.info is not None:
        args.info = args.info[0]
        if args.info not in g.plugins:
            logging.error("No such plugin {}.".format(args.info))
            sys.exit(1)

        plugin = g.plugins[args.info]

        print("{}, version {}".format(
                plugin.pretor_plugin_name,
                format_version(plugin.pretor_plugin_version)))

        print("")
        print("hooks: {}".format(', '.join(plugin.pretor_plugin_hooks.keys())))
        print("")

        if hasattr(plugin, "pretor_plugin_author"):
            print("")
            print("AUTHOR:")
            print(plugin.pretor_plugin_author)

        if hasattr(plugin, "pretor_plugin_description"):
            print("")
            print("DESCRIPTION:")
            print(plugin.pretor_plugin_description)

        if hasattr(plugin, "pretor_plugin_license"):
            print("")
            print("LICENSE:")
            print(plugin.pretor_plugin_license)

def format_version(v):
    """format_version

    Format a plugin version tuple for printing

    :param v:
    """

    if len(v) == 3:
        return "{}.{}.{}".format(*v)
    elif len(v) == 4:
        return "{}.{}.{}-{}".format(*v)
    else:
        raise ValueError("Invalid version tuple: {}".format(v))


def validate_plugin(obj):
    """validate_plugin

    Validate that the given object quacks like a Pretor plugin. A valid
    plugin must define the following fields:

    pretor_plugin_name:
        The name of the plugin, must the same as the basename of the plugin's
        directory

    pretor_plugin_version:
        Tuple of three integers and one string suffix forming the semantic
        visioning version number of the plugin (i.e. (1,2,3,'RC4') )

    pretor_plugin_hooks:
        Hash table containing function pointers pointing to the handlers for
        various hooks. Valid hook names and signatures are documented at TODO.

    Plugins may optionally define the following fields:

    pretor_plugin_description:
        String description of the plugin.

    pretor_plugin_author:
        String containing authorship information.

    pretor_plugin_license:
        String containing licensing / copyright information.

    :param obj:
    """

    required_attrs = [
        "pretor_plugin_name",
        "pretor_plugin_version",
        "pretor_plugin_hooks",
    ]

    for attr in required_attrs:
        if not hasattr(obj, attr):
            raise KeyError("plugin object missing required attribute {}"
                    .format(attr))

    if not (len(obj.pretor_plugin_version) in [3,4]):
        raise ValueError("plugin object has invalid version field")

    if not hasattr(obj.pretor_plugin_hooks, "__getitem__"):
        raise TypeError("plugin object hooks are not subscriptable")

def load_plugins(plugin_dir: pathlib.Path, debugfail=False):
    """load_plugins

    Load all plugins stored in the specified plugin directory.

    A valid Pretor plugin:

    * Is also a valid python module (directory containing __init__.py, with the
      directory basename being the plugin/module name)

    * Contains a file named "pretorplugin.py", which implements a singleton
      class named PretorPlugin. For information on the requirements for this
      class, see the documentation for validate_plugin().

    Because Pretor plugins are also valid Python modules, they may contain
    multiple files, or import other Python libraries if desired.

    :param plugin_dir:
    :type plugin_dir: pathlib.Path
    :param debufail: If True, drop to PDB on plugin load failure
    """

    plugin_dir = pathlib.Path(plugin_dir)
    sys.path.append(plugin_dir)
    plugin_dir = plugin_dir.resolve()
    logging.debug("loading plugins from {}".format(plugin_dir))

    g.plugins = {}

    for plugin_file in plugin_dir.glob("*/pretorplugin.py"):
        plugin_dir = plugin_file.parent
        plugin_name = str(plugin_dir.name)
        module_name = "{}.pretorplugin".format(plugin_name)

        logging.debug("considering plugin {} from {}"
                .format(plugin_name, plugin_file))

        plugin_object = None
        try:

            # import the plugin module
            spec = importlib.util.spec_from_file_location(
                    module_name, plugin_file)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)

            # instantiate the plugin object
            plugin_object = plugin.PretorPlugin()

            # make sure it is valid
            validate_plugin(plugin_object)

        except Exception as e:
            util.log_exception(e)
            logging.warning("failed to load plugin from file {}"
                    .format(plugin_file))
            if debugfail:
                logging.info("debugfail=True, dropping to PDB shell.")
                pdb.set_trace()
            continue

        logging.debug("successfully imported plugin")

        g.plugins[plugin_name] = plugin_object

