"""Constants used across the project."""

try:
    from importlib_metadata import version
except ImportError:
    # >= py 3.8
    from importlib.metadata import version

CAIRO_LANG_VERSION = version("cairo-lang")
