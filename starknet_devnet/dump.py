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
        path = path or self.dump_path
        assert path, "No dump_path defined"
        print("Dumping Devnet to:", path)
        with open(path, "wb") as file:
            pickle.dump(self.dumpable, file)

    def dump_if_required(self):
        """Dump only if specified in self.dump_on."""
        if self.dump_on == DumpOn.TRANSACTION:
            self.dump(self.dump_path)
