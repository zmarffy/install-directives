import argparse
import importlib
import logging
from enum import Enum

import zmtools


class ACTION(Enum):
    INSTALL = "INSTALL"
    UNINSTALL = "UNINSTALL"


def main(package: str, action: ACTION):
    """Main method

    Args:
        package (str): The name of the package
        action (ACTION): The InstallDirective action to take
    """
    _id = importlib.import_module(f"{package}.install_directives")

    install_directives = _id.InstallDirectives()

    if action == ACTION.INSTALL:
        install_directives.install()
    elif action == ACTION.UNINSTALL:
        install_directives.uninstall()


def _entry() -> int:
    # Console entry point

    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=lambda x: x.replace("-", "_"))
    parser.add_argument("action", choices=[
                        action.name.lower() for action in ACTION])
    parser.add_argument("--verbose", action="store_true", help="be verbose")
    args = parser.parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    args.action = ACTION(args.action.upper())
    zmtools.init_logging(level=log_level)

    return main(args.package, args.action)


if __name__ == "__main__":

    import sys  # noqa

    sys.exit(_entry())
