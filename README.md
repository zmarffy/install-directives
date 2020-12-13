# `zetuptools`

`zetuptools` has a collection of useful functions to be used in a setup.py file used by `setuptools`, as well as a command line tool, `install-directives`, used to aid in post-install and post-uninstall steps for packages installed with `pip`.

## Usage

Read the docstrings for information on how to use `SetuptoolsExtensions`. They are there to make construction of `setup.py` files quicker, such as automatically reading the version (if it is placed in an `__init__.py` file and named `__version__`).

Regarding `InstallDirectives`, the idea is to write a custom class that extends `InstallDirective`, overriding its `_install` and `_uninstall` functions. This should be placed in a Python package called "`install_directives`".

These overridden functions will be automatically called upon running the command line tool as such.

```text
usage: install-directives [-h] package {install,uninstall}

positional arguments:
  package
  {install,uninstall}

optional arguments:
  -h, --help           show this help message and exit
```

See [`apt-repo`](https://github.com/zmarffy/apt-repo) for a real-world example of this. Note the placement of `install_directives` as well as the fact that the README mentions that you should run `install-directives apt-repo install` after the `pip` package is installed.

Note that this is extremely helpful for building Docker images related to the project. There is a function called `build_docker_images` that will do just that. Check out its docstring.

`install-directives [package_name] uninstall` should be run *before* the uninstallation of the `pip` package. Similarly, a `remove_docker_images` function exists.
