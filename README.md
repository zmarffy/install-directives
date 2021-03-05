# `zetuptools`

`zetuptools` contains a command line tool, `install-directives`, used to aid in post-install and post-uninstall steps for packages installed with `pip`.

It originally had some other functions I considered useful in a `setup.py` file, but these have been scrapped as of version 3.0 as they cause too many dependecy confusions.

## Usage

The idea is to write a custom class that extends `InstallDirective`, overriding its `_install` and `_uninstall` functions. This should be placed in a Python package called `install_directives`.

These overridden functions will be automatically called upon running the command line tool as such.

```text
usage: install-directives [-h] [--log_level {CRITICAL,ERROR,WARNING,INFO,DEBUG}] package {install,uninstall}

positional arguments:
  package
  {install,uninstall}

optional arguments:
  -h, --help            show this help message and exit
  --log_level {CRITICAL,ERROR,WARNING,INFO,DEBUG}
                        how verbose
```

See [`apt-repo`](https://github.com/zmarffy/apt-repo) for a real-world example of this. Note the placement of `install_directives` as well as the fact that the README mentions that you should run `install-directives apt-repo install` after the `pip` package is installed.

Note that this is extremely helpful for building Docker images related to the project. There is a function called `build_docker_images` that will do just that. Check out its docstring.

`install-directives [package_name] uninstall` should be run *before* the uninstallation of the `pip` package. Similarly, a `remove_docker_images` function exists.
