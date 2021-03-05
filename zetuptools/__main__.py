#! /usr/bin/env python3

import argparse
import importlib
import sys

import zmtools

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=lambda x: x.replace("-", "_"))
    parser.add_argument("action", choices=[
                        "install", "uninstall"], type=str.lower)
    parser.add_argument("--log_level", default="INFO", type=str.upper, choices=[
                        "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"], help="how verbose")
    args = parser.parse_args()

    zmtools.init_logging(level=args.log_level)

    _id = importlib.import_module(f"{args.package}.install_directives")
    install_directives = _id.InstallDirectives()
    if args.action == "install":
        install_directives.install()
    elif args.action == "uninstall":
        install_directives.uninstall()

    return 0


if __name__ == "__main__":
    sys.exit(main())
