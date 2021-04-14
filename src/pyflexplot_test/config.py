"""Configuration classes."""
# Standard library
import dataclasses as dc
from pathlib import Path
from typing import Optional
from typing import Sequence


@dc.dataclass
class RunConfig:
    force: bool = False
    verbosity: int = 0

    @property
    def verbose(self) -> bool:
        return self.verbosity > 0

    @property
    def debug(self) -> bool:
        return self.verbosity > 1


@dc.dataclass
class RepoConfig:
    clone_path: Path
    rev: str
    work_path: Path


@dc.dataclass
class PlotConfig:
    presets: Sequence[str]
    infiles: Sequence[str]
    data_path: Optional[Path]
    num_procs: int
    only: Optional[int]
