# `install-directives`

`install-directives` contains a command line tool, `install-directives`, used to aid in post-install and post-uninstall steps for packages installed with `pip`. It also includes a class to represent packages installed with `pip`.

## Usage

The idea is to write a custom class that inherts from `InstallDirectives`, overriding its `package_name` and `module_name` attributes and its `_install` and `_uninstall` functions. This should be placed in a package called `install_directives` in your module.

For example, if your package is called "mypackage", you could set up `InstallDirectives` for it to run a script on install and another script on uninstall as such.

```python
# mypackage/install_directives/__init__.py

from python_install_directives import InstallDirectives as InstallDirectives_


class InstallDirectives(InstallDirectives_):
    def __init__(self) -> None:
        super().__init__("mypackage")
        
    def _install(old_version: str, new_version: str) -> None:
        run_script()
    
    def _uninstall(version: str) -> None:
        run_another_script()
```

These overridden functions will be called upon running the command line tool as such. You can utilize the current and incoming versions of the package to perform different actions on install, as they come in as parameters. Similarly, you can utilize the current version during uninstall.

```sh
# Do a pip install of myproject first

install-directives myproject install  # Calls `run_script`
install-directives myproject uninstall  # Calls `run_another_script`
```
