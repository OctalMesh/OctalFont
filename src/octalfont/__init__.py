"""OctalFont: shared build tooling for the Octal font families."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("octalfont")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
