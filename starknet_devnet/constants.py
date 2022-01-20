"""Constants used across the project."""

try:
    from importlib_metadata import version
except ImportError:
    from importlib.metadata import version

CAIRO_LANG_VERSION = version("cairo-lang")
