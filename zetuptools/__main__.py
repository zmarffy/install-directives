#! /usr/bin/env python3

import argparse
import importlib
import sys

import zmtools


def main() -> int:

    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=lambda x: x.replace("-", "_"))
    parser.add_argument("action", choices=[
                        "install", "uninstall"], type=str.lower)
    parser.add_argument("--verbose", action="store_true", help="be verbose")
    args = parser.parse_args()

    if args.verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    zmtools.init_logging(level=log_level)
    _id = importlib.import_module(f"{args.package}.install_directives")
    install_directives = _id.InstallDirectives()
    if args.action == "install":
        install_directives.install()
    elif args.action == "uninstall":
        install_directives.uninstall()

    return 0


if __name__ == "__main__":
    sys.exit(main())
