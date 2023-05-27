import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import zmtools

LOGGER = logging.getLogger(__name__)
HOME_FOLDER = Path("~").expanduser()


class PipPackage:
    def __init__(self, name: str) -> None:
        """A class that represents a pip package.

        Args:
            name (str): The name of the pip package.

        Attributes:
            name (str): The name of the pip package.
            version (str): The version of the pip package.
            summary (str): The summary of the pip package.
            home_page (str): The home page of the pip package.
            author (str): The author of the pip package.
            author_email (str): The email of the author of the pip package.
            license (str): The license of the pip package.
            location (str): The location of the pip package.
            requires (list[str]): Packages that this pip package requires.
            required_by (list[str]): Packages on your system that require this pip package.
            newer_version_available (bool): If there is a newer version of this package available.
        """
        self.name: str
        self.version: str
        self.summary: str
        self.home_page: str
        self.author: str
        self.author_email: str
        self.license: str
        self.location: str
        self.requires: list[str]
        self.required_by: list[str]
        self._newer_version_available = None

        try:
            out = (
                subprocess.run(
                    [sys.executable, "-m", "pip", "show", name, "--no-color"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                .stdout.strip()
                .split("\n")
            )
        except subprocess.CalledProcessError as e:
            if "WARNING: Package(s) not found:" in e.stderr:
                raise FileNotFoundError(f"No such package {name} on your system")
            else:
                raise e
        for item in out:
            d = [i.strip() for i in item.split(":", 1)]
            if d[0] in ("Requires", "Required-by"):
                d[1] = [r.strip() for r in d[1].split(",")]  # type: ignore
            setattr(self, d[0].replace("-", "_").lower(), d[1])
        self.name = self.name.replace("-", "_")

    @property
    def newer_version_available(self) -> bool:
        # Only do this if the user wants to check; it's kind of time-consuming
        if self._newer_version_available is None:
            outdated_packages = [
                r.split("==")[0]
                for r in subprocess.run(
                    [sys.executable, "-m", "pip", "list", "--outdated"],
                    capture_output=True,
                    text=True,
                ).stdout.split()
            ]
            self._newer_version_available = self.name in outdated_packages
        return self._newer_version_available

    def __repr__(self) -> str:
        return f"PipPackage(name='{self.name}', version='{self.version}')"


class InstallDirectivesException(Exception):
    def __init__(self, original_exception: Exception) -> None:
        """Exception thrown when an install directive fails.

        Args:
            original_exception (Exception): The exception that caused this one.

        Attributes:
            original_exception (Exception): The exception that caused this one.
            message (str): Friendly message.
        """
        self.original_exception = original_exception
        self.message = self._construct_message()

    def _construct_message(self) -> str:
        return "InstallDirective base exception"

    def __str__(self) -> str:
        return self.message


class InstallException(InstallDirectivesException):
    def _construct_message(self) -> str:
        """Exception thrown when install directive "install" fails."""
        return 'Install directive "install" failed; you may need to manually intervene to remove leftover pieces'


class UninstallException(InstallDirectivesException):
    def _construct_message(self) -> str:
        """Exception thrown when install directive "uninstall" fails."""
        return 'Install directive "uninstall" failed; you may need to manually intervene to remove leftover pieces'


class InstallDirectivesNotYetRunException(Exception):
    def __init__(self) -> None:
        """Exception to throw when install directive "install" has not yet been run."""
        super(InstallDirectivesNotYetRunException, self).__init__(
            'Install directive "install" was not run for this package yet; you may want to run `install-directives [package_name] install`'
        )


class InstallDirectives:
    def __init__(
        self,
        package_name: str,
        module_name: Optional[str] = None,
        data_folder: Optional[str] = "",
    ) -> None:
        """Class to help run post-install/post-uninstall scripts.

        Args:
            package_name (str): The name of the pip package.
            module_name (str, optional): The module name that contains the install-directives in it. If None, will default to the package name (with dashes replaced with underscores). Defaults to None.
            data_folder (Path, optional): The folder where data for the package should be stored in. If None, defaults to f"~/.{package_name}". If False, no data folder is used. Defaults to None.

        Attributes:
            package_name (str): The name of the pip package.
            module_name (str): The module name that contains in install-directives in it.
            data_folder (Union[Path, None]): The folder where data for the package should be stored in.
            package (PipPackage): The pip package.
            base_dir (Path): The .python_installdirectives base directory.
            version (str): The current version of the package.
        """
        self.package_name = package_name
        self.module_name = module_name

        self.package = PipPackage(self.package_name)
        if self.module_name is None:
            self.module_name = self.package.name
        self.base_dir = Path(
            HOME_FOLDER, ".python_installdirectives", f".{self.package_name}"
        )
        self.version = self.package.version
        if data_folder is not False:
            self.data_folder = Path(HOME_FOLDER, f".{self.package_name}")
        else:
            self.data_folder = None

    def _install(self, old_version: str, new_version: str) -> None:
        """Function that should be overridden by a custom class that extends InstallDirectives"""
        # Override me!
        LOGGER.debug('No install directive "install"')

    def install(self) -> None:
        """Function to run after installing a pip package.

        Raises:
            InstallException: If the install throws an exception.
        """
        LOGGER.info('Running install directive "install"')
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            LOGGER.debug(f"Folder {self.base_dir} ensured to exist")
            if self.data_folder is not None:
                self.data_folder.mkdir(parents=True, exist_ok=True)
                LOGGER.debug(f"Folder {self.data_folder} ensured to exist")
            old_version = zmtools.read_text_file(
                self.base_dir / "version", not_exists_ok=True
            )
            if old_version and old_version != self.version:
                LOGGER.debug(f"Version change: {old_version} => {self.version}")
            else:
                LOGGER.debug("No version change")
            self._install(old_version, self.version)
            zmtools.write_text_file(self.base_dir / "version", self.version)
            LOGGER.info('Finished install directive "install"')
        except Exception as e:
            LOGGER.exception(e)
            shutil.rmtree(self.base_dir)
            raise InstallException(e)

    def _uninstall(self, version: str) -> None:
        """Function that should be overridden by a custom class that extends InstallDirectives."""
        # Override me!
        LOGGER.debug('No install directive "uninstall"')

    def uninstall(self) -> None:
        """Function to run after uninstalling a pip package.

        Raises:
            InstallException: If the install throws an exception.
        """
        LOGGER.info('Running install directive "uninstall"')
        if not self.base_dir.is_dir():
            raise FileNotFoundError(
                f"{self.base_dir} does not exist; was install-directives ever run for {self.package.name}?"
            )
        try:
            self._uninstall(self.version)
            if self.data_folder is not None:
                try:
                    shutil.rmtree(self.data_folder)
                except FileNotFoundError:
                    LOGGER.warning("Data folder does not exist")
            shutil.rmtree(self.base_dir)
            LOGGER.info('Finished install directive "uninstall"')
        except Exception as e:
            LOGGER.exception(e)
            raise UninstallException(e)
