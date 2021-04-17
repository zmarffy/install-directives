# `zetuptools`

`zetuptools` contains a command line tool, `install-directives`, used to aid in post-install and post-uninstall steps for packages installed with `pip`. It also includes a class to represent packages installed with `pip`.

It originally had some other functions I considered useful in a `setup.py` file, but these have been scrapped as of version 3.0 as they cause too many dependecy confusions and honestly do not save that much time.

## Usage

The idea is to write a custom class that extends `InstallDirective`, overriding its `package_name` and `module_name` attributes and its `_install` and `_uninstall` functions. This should be placed in a Python package called `install_directives`.

These overridden functions will be automatically called upon running the command line tool as such.

```text
usage: install-directives [-h] [--verbose] package {install,uninstall}

positional arguments:
  package
  {install,uninstall}

optional arguments:
  -h, --help           show this help message and exit
  --verbose            be verbose
```

See [`apt-repo`](https://github.com/zmarffy/apt-repo) for a real-world example of how to use this with your Python package. Note the placement of `install_directives` as well as the fact that the README mentions that you should run `install-directives apt-repo install` after the `pip` package is installed.

`zetuptools` should be also helpful for building Docker images related to the project. There is a function called `build_docker_images` that will do just that. It attempts to build Docker images cleverly in the order in which they are needed to be built, but this could actually be coded wrong. Be advised. I will revisit this at some point in the future.

`install-directives [package_name] uninstall` should be run *before* the uninstallation of the `pip` package. Similarly, a `remove_docker_images` function exists.
