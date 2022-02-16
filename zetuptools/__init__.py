from .api import *

package_name = "zetuptools"

__version__ = "0.0.0"
if __version__ == "0.0.0":
    __version__ = PipPackage(package_name).version
