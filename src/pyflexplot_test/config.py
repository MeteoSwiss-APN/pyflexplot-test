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
class WorkDirConfig:
    """Work dir config.

    Params:
        path: Path to work dir.

        reuse: Reuse existing work dir at ``path``; if true, takes precedence
            over ``replace``.

        replace (optional): Replace existing work dir at ``path``, unless
            reused; ignored if ``reuse`` is true.

    """

    path: Path
    reuse: bool
    replace: bool = False


@dc.dataclass
class CloneConfig:
    path: Path
    rev: str
    reuse: bool
    wdir: WorkDirConfig


@dc.dataclass
class PlotConfig:
    data_path: Optional[Path]
    infiles: Sequence[Path]
    num_procs: int
    only: Optional[int]
    presets: Sequence[str]
    reuse: bool
