import logging
import os
import re
import shutil
import subprocess

import docker
from reequirements import Requirement
import setuptools
import zmtools
from pkg_resources import resource_filename

LOGGER = logging.getLogger("InstallDirectives")
REQUIREMENTS = {
    "vermin": Requirement("vermin", ["vermin", "--version"], warn=True)
}
HAS_VERMIN = REQUIREMENTS["vermin"].check()


class SetuptoolsExtensions():

    """Extensions for setuptools setup.py file. Assumes you are in the source code folder

    Args:
        name (str): The name of the pip package, what should get put into setuptools's name field
        author (str, optional): Author of the package. If None, uses git's username. Defaults to None.
        author_email (str, optional): Author of the package's email. If Nome, uses git's email. Defaults to None.

    Attributes:
        name (str): The name of the pip package, what should get put into setuptools's name field
        author (str): The author of the package
        author_email (str): The email of the author of the package
        packages (list[str]): A list of packages that this pip package contains (simply the output of setuptools.find_packages())
        all_files (dict[str, list[str]]): A dict for use in setuptools's package_data if you want to include every single file in pakcage_data
        minimum_version_required (str): The minimum version required for installing this pip package (determiend by vermin)
        version (str): The version of the pip package, found by parsing the package's __init__.py file
    """

    def __init__(self, name, author=None, author_email=None):
        if author is None:
            author = subprocess.check_output(
                ["git", "config", "user.name"]).decode().strip()
        if author_email is None:
            author_email = subprocess.check_output(
                ["git", "config", "user.email"]).decode().strip()
        self.name = name
        self.author = author
        self.author_email = author_email
        self.packages = setuptools.find_packages()
        self.all_files = {package: ["*"] for package in self.packages}
        if HAS_VERMIN:
            self.minimum_version_required = ">=" + \
                re.search(r"(?<=Minimum required versions: ).+",
                          subprocess.check_output(["vermin", "."]).decode()).group(0)
        self.version = zmtools.get_package_version(self.name)


class PipPackage():

    """A class that represents a pip package

    Args:
        name (str): The name of the pip package

    Attributes:
        name (str): The name of the pip package
        version (str): The version of the pip package
        sumamry (str): The summary of the pip package
        home_page (str): The home page of the pip package
        author (str): The author of the pip package
        author_email (str): The email of the author of the pip package
        license (str): The license of the pip package
        location (str): The location of the pip package
        requires (list[str]): Packages that this pip package requires
        required_by (list[str]): Packages on your system that require this pip package
        docker_images (list[tuple[str]]): Names of the Docker images 
    """

    def __init__(self, name):
        self._name = name
        self.version = ""
        self.summary = ""
        self.home_page = ""
        self.author = ""
        self.author_email = ""
        self.license = ""
        self.location = ""
        self.requires = []
        self.required_by = []

        try:
            out = subprocess.check_output(
                ["pip3", "show", self._name, "--no-color"], stderr=subprocess.PIPE).decode().strip().split("\n")
        except subprocess.CalledProcessError as e:
            if e.stderr.decode().strip().startswith("WARNING: Package(s) not found:"):
                raise FileNotFoundError(
                    f"No such package {self._name} on your system")
        for item in out:
            d = [i.strip() for i in item.split(":", 1)]
            if d[0] in ("Requires", "Required-by"):
                d[1] = [r.strip() for r in d[1].split(",")]
            setattr(self, d[0].replace("-", "_").lower(), d[1])
        self.name = self.name.replace("-", "_")

        docker_images_package = os.path.abspath(resource_filename(self.name, "docker_images"))
        uses_docker = os.path.isdir(docker_images_package)
        if uses_docker:
            docker_client = docker.from_env()
        else:
            docker_client = None

        self._docker_client = docker_client
        docker_images = []
        if uses_docker:
            for sf in os.listdir(docker_images_package):
                f = os.path.join(docker_images_package, sf)
                if os.path.isdir(f) and "Dockerfile" in os.listdir(f):
                    docker_images.append((sf, f))

        self.docker_images = docker_images

    def build_docker_images(self):
        """Remove the package's Docker images

        Raises:
            ValueError: If the package does not use Docker images
        """
        if not self.docker_images:
            raise ValueError("This pip package does not use Docker")
        for sf, f in self.docker_images:
            tag = f"{sf}:{self.version}"
            LOGGER.info(f"Building Docker image {tag}")
            self._docker_client.images.build(path=f, tag=tag)
            self._docker_client.images.get(tag).tag(sf)

    def remove_docker_images(self):
        """Remove the package's Docker images

        Raises:
            ValueError: If the package does not use Docker images
        """
        if not self.docker_images:
            raise ValueError("This pip package does not use Docker")
        for sf, _ in self.docker_images:
            tag = f"{sf}:{self.version}"
            LOGGER.info(f"Removing Docker image {sf}")
            self._docker_client.images.remove(
                self._docker_client.images.get(tag).id, force=True)

    def __repr__(self):
        return f"Package(name='{self.name}', version='{self.version}')"


class InstallDirectivesException(Exception):

    """Exception when an install directive fails

    Args:
        original_exception (Exception): The exception that caused this one

    Attributes:
        original_exception (Exception): The exception that caused this one
        message (str): Friendly message
    """

    def __init__(self, original_exception):
        self.original_exception = original_exception
        self.message = self._construct_message()

    def _construct_message(self):
        """Construct the friendly message

        Returns:
            str: The message
        """
        return "InstallDirective base exception"

    def __str__(self):
        return self.message


class InstallException(InstallDirectivesException):

    """Exception thrown when install directive "install" fails"""

    def _construct_message(self):
        return "Install directive \"install\" failed; you may need to manually intervene to remove leftover pieces"


class UninstallException(InstallDirectivesException):

    """Exception thrown when install directive "uninstall" fails"""

    def _construct_message(self):
        return "Install directive \"uninstall\" failed; you may need to manually intervene to remove leftover pieces"


class InstallDirectivesNotYetRunException(Exception):

    """Exception to throw when install directive "install" has not yet been run"""

    def __init__(self):
        super(InstallDirectivesNotYetRunException, self).__init__(
            "Install directive \"install\" was not yet run for this package yet; you may want to run `install-directives [package_name] install`")


class InstallDirectives():

    def __init__(self, package_name):
        """Class to help run post-install/post-uninstall scripts

        Args:
            package_name (str): The name of the pip package

        Attributes:
            package (PipPackage): The pip package
            base_dir (str): The .python_installdirectives base directory
            version (str): The current version of the package
        """
        self.package = PipPackage(package_name)
        self.base_dir = os.path.join(os.path.expanduser(
            "~"), ".python_installdirectives", package_name)
        self.version = self.package.version

    def _install(self, old_version, new_version):
        """Function that should be overridden by a custom class that extends InstallDirectives"""

        # Override me!
        LOGGER.debug("No install directive \"install\"")

    def install(self):
        """Function to run after installing a pip package

        Raises:
            InstallException: If the install throws an exception
        """

        LOGGER.info("Running install directive \"install\"")
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            LOGGER.debug(f"Folder {self.base_dir} ensured to exist")
            old_version = zmtools.read_text(os.path.join(
                self.base_dir, "version"), not_exists_ok=True)
            LOGGER.debug(f"Version change: {old_version} => {self.version}")
            self._install(old_version, self.version)
            zmtools.write_text(os.path.join(
                self.base_dir, "version"), self.version)
            LOGGER.info("Finished install directive \"install\"")
        except Exception as e:
            LOGGER.exception(e)
            raise InstallException(e)

    def _uninstall(self, version):
        """Function that should be overridden by a custom class that extends InstallDirectives"""

        # Override me!
        LOGGER.debug("No install directive \"uninstall\"")

    def uninstall(self):
        """Function to run after uninstalling a pip package

        Raises:
            InstallException: If the install throws an exception
        """

        LOGGER.info("Running install directive \"uninstall\"")
        if not os.path.isdir(self.base_dir):
            raise FileNotFoundError(
                f"{self.base_dir} does not exist; was install-directives ever run for {self.package.name}?")
        try:
            self._uninstall(self.version)
            shutil.rmtree(self.base_dir)
            LOGGER.info("Finished install directive \"uninstall\"")
        except Exception as e:
            LOGGER.exception(e)
            raise UninstallException(e)
