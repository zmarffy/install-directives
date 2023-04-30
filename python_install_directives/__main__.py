import argparse
import importlib
import logging
from enum import Enum


class ACTION(Enum):
    INSTALL = "INSTALL"
    UNINSTALL = "UNINSTALL"


def main(package: str, action: ACTION) -> int:
    """Main method.

    Args:
        package (str): The name of the package.
        action (ACTION): The InstallDirective action to take.
    """
    install_directives = importlib.import_module(
        f"{package}.install_directives"
    ).InstallDirectives()

    if action == ACTION.INSTALL:
        install_directives.install()
    elif action == ACTION.UNINSTALL:
        install_directives.uninstall()

    return 0


def _entry() -> int:
    # Console entry point

    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=lambda x: x.replace("-", "_"))
    parser.add_argument("action", choices=[action.name.lower() for action in ACTION])
    parser.add_argument("--verbose", action="store_true", help="be verbose")
    args = parser.parse_args()

    if not args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG
    args.action = ACTION(args.action.upper())
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s")
    logging.getLogger().setLevel(log_level)

    return main(args.package, args.action)


if __name__ == "__main__":
    import sys

    sys.exit(_entry())
