"""Dumping utilities."""

import multiprocessing

import dill as pickle

from .util import DumpOn

def perform_dump(dumpable, path):
    """Performs the very act of dumping."""
    with open(path, "wb") as file:
        pickle.dump(dumpable, file)

class Dumper:
    """Class for dumping objects."""

    def __init__(self, dumpable):
        """Specify the `dumpable` object to be dumped."""

        self.dumpable = dumpable

        self.dump_path: str = None
        """Where to dump."""

        self.dump_on: DumpOn = None
        """When to dump."""

    def dump(self, path: str):
        """Dump to `path`."""
        path = path or self.dump_path
        assert path, "No dump_path defined"
        print("Dumping Devnet to:", path)

        multiprocessing.Process(
            target=perform_dump,
            args=[self.dumpable, path]
        ).start()
        # don't .join(), let it run in background

    def dump_if_required(self):
        """Dump only if specified in self.dump_on."""
        if self.dump_on == DumpOn.TRANSACTION:
            self.dump(self.dump_path)
