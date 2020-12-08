import os
import re
import subprocess

import docker
import setuptools
from pkg_resources import resource_filename


class ZetupTools():

    def __init__(self, name=None, author=None, author_email=None):
        if name is None:
            d = os.getcwd().split(os.sep)
            if len(d) > 1:
                name = name[-1]
        if author is None:
            author = subprocess.check_output(
                ["git", "config", "user.name"]).decode().strip()
        if author_email is None:
            author_email = subprocess.check_output(
                ["git", "config", "user.email"]).decode().strip()
        self.name = name
        self.author = author
        self.author_email = author_email
        self.packages = {package: Package(package)
                         for package in setuptools.find_packages()}
        self.all_files = {package_name: ["*"]
                          for package_name in self.packages.keys()}
        self.minimum_version_required = ">=" + \
            re.search(r"(?<=Minimum required versions: ).+",
                      subprocess.check_output(["vermin", "."]).decode()).group(0)


class Package():
    def __init__(self, package):
        self._package = package
        # Yes, this "version-grabbing" code is very specific; it may be changed later to accomidate more stuff
        with open(os.path.join(self._package.replace(".", os.sep), "__init__.py"), encoding="utf8") as f:
            try:
                version = re.search(
                    r'__version__ = "(.*?)"', f.read()).group(1)
            except AttributeError:
                version = None
        self.version = version

    def build_docker_images(self, docker_images_folder="docker_images"):
        docker_client = docker.from_env()
        docker_images_folder = os.path.abspath(
            resource_filename(self._package, docker_images_folder))
        for sf in os.listdir(docker_images_folder):
            f = os.path.join(docker_images_folder, sf)
            if os.path.isdir(f) and "Dockerfile" in os.listdir(f):
                tag = f"{sf}:{self.version}"
                print(f"Building Docker image {tag}")
                docker_client.images.build(path=f, tag=tag)

    def __repr__(self):
        return f"Package(package={self._package})"
