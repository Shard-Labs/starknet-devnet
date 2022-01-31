"""Dumping utilities."""

import dill as pickle

from .util import DumpOn

class Dumper:
    """Class for dumping objects."""

    dump_path: str
    """Where to dump."""

    dump_on: DumpOn
    """When to dump."""

    def __init__(self, dumpable):
        """Specify the `dumpable` object to be dumped."""
        self.dumpable = dumpable

    def dump(self, path: str):
        """Dump to `path`."""
        assert self.dump_path, "No dump_path defined"
        with open(path, "rb") as file:
            pickle.dump(file, self.dumpable)

    def dump_if_required(self):
        """Dump only if specified in self.dump_on."""
        self.dump(self.dump_path)
