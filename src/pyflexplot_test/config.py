"""Configuration classes."""
# Standard library
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Sequence


@dataclass
class RunConfig:
    force: bool
    verbosity: int

    def __post_init__(self) -> None:
        self.verbose: bool = self.verbosity > 0
        self.debug: bool = self.verbosity > 1


@dataclass
class RepoConfig:
    clone_path: Path
    rev: str
    work_path: Path


@dataclass
class PlotConfig:
    presets: Sequence[str]
    infiles: Sequence[str]
    data_path: Optional[Path]
    num_procs: int
    only: Optional[int]
