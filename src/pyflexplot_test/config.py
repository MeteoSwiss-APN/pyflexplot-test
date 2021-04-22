"""Configuration classes."""
# Standard library
import dataclasses as dc
from pathlib import Path
from typing import Optional
from typing import Sequence


@dc.dataclass
class RunConfig:
    num_procs: int
    only: Optional[int]
    repo_url: str
    verbosity: int
    #
    start_path: Path = Path(".").absolute()

    @property
    def verbose(self) -> bool:
        return self.verbosity > 0

    @property
    def debug(self) -> bool:
        return self.verbosity > 1


@dc.dataclass
class ReuseConfig:
    old_install: bool = False
    new_install: bool = False
    old_plots: bool = False
    new_plots: bool = False


@dc.dataclass
class WorkDirConfig:
    """Working directory config.

    Params:
        path: Path to working directory.

        reuse: Reuse existing work dir at ``path``; if true, takes precedence
            over ``replace``.

        replace (optional): Replace existing work dir at ``path``, unless
            reused; ignored if ``reuse`` is true.

    """

    path: Path
    reuse: bool
    replace: bool = False


@dc.dataclass
class InstallConfig:
    path: Path
    rev: str
    reuse: bool


@dc.dataclass
class PlotConfig:
    data_path: Optional[Path]
    infiles: Sequence[Path]
    presets: Sequence[str]
    reuse: bool
