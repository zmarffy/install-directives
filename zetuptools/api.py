import getpass
import logging
import os
import re
import shutil
import subprocess
import sys

import docker
import zmtools
from pkg_resources import resource_filename

LOGGER = logging.getLogger(__name__)


def _get_docker_image_name_from_string(s):
    # I don't remember lol
    test = s.split(" as", 1)
    if len(test) != 1:
        return test[0]
    test = s.split(":", 1)
    if len(test) != 1:
        return test[0]
    return s.strip()


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
        newer_version_available (bool): If there is a newer version of this package available
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
        self._newer_version_available = None

        try:
            out = subprocess.check_output(
                [sys.executable, "-m", "pip", "show", self._name, "--no-color"], stderr=subprocess.PIPE).decode().strip().split("\n")
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

    @property
    def newer_version_available(self):
        # Only do this if the user wants to check; it's kind of time-consuming
        if self._newer_version_available is None:
            outdated_packages = [r.decode().split("==")[0] for r in subprocess.check_output(
                [sys.executable, "-m", 'pip', "list", "--outdated"], stderr=subprocess.DEVNULL).split()]
            self._newer_version_available = self.name in outdated_packages
        return self._newer_version_available

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

    package_name = None
    data_folder = ""

    def __init__(self):
        """Class to help run post-install/post-uninstall scripts

        Attributes:
            package_name (str): The name of the pip package
            data_folder (Union(str, None)): The folder where data for the package should be stored in. If the empty string, defaults to ~/.[package_name]. If None, no data folder is used
            package (PipPackage): The pip package
            base_dir (str): The .python_installdirectives base directory
            version (str): The current version of the package
            docker_images (list[tuple[str]]): Names of the Docker images
        """
        self.package = PipPackage(self.package_name)
        self.base_dir = os.path.join(os.path.expanduser(
            "~"), ".python_installdirectives", self.package_name)
        self.version = self.package.version
        if self.data_folder == "":
            self.data_folder = os.path.join(
                os.sep, os.path.expanduser("~"), f".{self.package_name}")

        docker_images_package = os.path.abspath(
            resource_filename(self.package.name, "docker_images"))
        uses_docker = os.path.isdir(docker_images_package)
        if uses_docker:
            docker_client = docker.from_env()
        else:
            docker_client = None

        self._docker_client = docker_client
        docker_images = {}
        if uses_docker:
            for sf in os.listdir(docker_images_package):
                f = os.path.join(docker_images_package, sf)
                if os.path.isdir(f) and "Dockerfile" in os.listdir(f):
                    docker_images[sf] = f
        # Sort
        sorted_docker_images = []
        for docker_image in docker_images.values():
            with open(os.path.join(docker_image, "Dockerfile"), "r") as dfc:
                content = dfc.readlines()[0]
            # Find if one relies on another
            d = re.findall(r"(?i)(?<=FROM ).+\n", content)
            if d:
                uses_image = _get_docker_image_name_from_string(d[0])
                if uses_image in docker_images.keys() and docker_images[uses_image] not in sorted_docker_images:
                    sorted_docker_images.insert(0, docker_images[uses_image])
            if docker_image not in sorted_docker_images:
                sorted_docker_images.append(docker_image)
        self.docker_images = sorted_docker_images

    def build_docker_images(self):
        """Remove the package's Docker images

        Raises:
            ValueError: If the package does not use Docker images
        """
        if not self.docker_images:
            raise ValueError("This pip package does not use Docker")
        for f in self.docker_images:
            sf = os.path.basename(f)
            tag = f"{sf}:{self.version}"
            LOGGER.info(f"Building Docker image {tag}")
            self._docker_client.images.build(path=f, tag=tag, rm=True)
            self._docker_client.images.get(tag).tag(sf)

    def remove_docker_images(self):
        """Remove the package's Docker images

        Raises:
            ValueError: If the package does not use Docker images
            docker.errors.APIError: If there is any other Docker API error
        """
        if not self.docker_images:
            raise ValueError("This pip package does not use Docker")
        for f in reversed(self.docker_images):
            sf = os.path.basename(f)
            tag = f"{sf}:{self.version}"
            LOGGER.info(f"Removing Docker image {sf}")
            try:
                image_id = self._docker_client.images.get(tag).id
            except docker.errors.APIError as e:
                if e.status_code == 404:
                    LOGGER.warning(f"Image {tag} could not be found; ignoring")
                else:
                    raise e
            self._docker_client.images.remove(image_id, force=True)

    def set_secret(self, secret_name, secret_value=None, error_if_exists=True):
        """Set a Docker secret

        Args:
            secret_name (str): Name of secret
            secret_value (str, optional): Value of secret. If None, prompt. Defaults to None.
            error_if_exists (bool, optional): If False, do not error if secret already exists. Defaults to True.

        Raises:
            ValueError: If the secret already exists and error_if_exists is True
            docker.errors.APIError: If there is any other Docker API error
        """
        try:
            self._docker_client.secrets.get(secret_name)
            if error_if_exists:
                raise ValueError(f"Secret {secret_name} already exists")
            else:
                LOGGER.warning(
                    f"Secret {secret_name} already exists; ignoring")
            return
        except docker.errors.APIError as e:
            if e.status_code != 404:
                raise e
        if secret_value is None:
            secret_value = getpass.getpass(
                f"Enter value for secret {secret_name}: ")
        self._docker_client.secrets.create(name=secret_name, data=secret_value)

    def remove_secret(self, secret_name, error_if_not_exists=True):
        """Remove a Docker secret

        Args:
            secret_name (str): Name of secret
            error_if_not_exists (bool, optional): If False, do not error if secret does not exist. Defaults to True.

        Raises:
            ValueError: If the secret already exists and error_if_not_exists is True
            docker.errors.APIError: If there is any other Docker API error
        """
        try:
            self._docker_client.secrets.get(secret_name).remove()
        except docker.errors.APIError as e:
            if e.status_code != 404:
                raise e
            else:
                if error_if_not_exists:
                    raise ValueError(f"Secret {secret_name} does not exist")
                else:
                    LOGGER.warning(
                        f"Secret {secret_name} does not exist; ignoring")

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
            if self.data_folder is not None:
                os.makedirs(self.data_folder, exist_ok=True)
                LOGGER.debug(f"Folder {self.data_folder} ensured to exist")
            old_version = zmtools.read_text(os.path.join(
                self.base_dir, "version"), not_exists_ok=True)
            if old_version and old_version != self.version:
                LOGGER.debug(
                    f"Version change: {old_version} => {self.version}")
            else:
                LOGGER.debug("No version change")
            self._install(old_version, self.version)
            zmtools.write_text(os.path.join(
                self.base_dir, "version"), self.version)
            LOGGER.info("Finished install directive \"install\"")
        except Exception as e:
            LOGGER.exception(e)
            shutil.rmtree(self.base_dir)
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
            if self.data_folder is not None:
                try:
                    shutil.rmtree(self.data_folder)
                except FileNotFoundError:
                    LOGGER.warning("Data folder does not exist")
            shutil.rmtree(self.base_dir)
            LOGGER.info("Finished install directive \"uninstall\"")
        except Exception as e:
            LOGGER.exception(e)
            raise UninstallException(e)
