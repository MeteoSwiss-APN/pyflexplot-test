"""Main module."""
# Standard library
import filecmp
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence

# Third-party
from git import Repo
from git.exc import InvalidGitRepositoryError

# Local
from .config import PlotConfig
from .config import RunConfig
from .exceptions import PathExistsError
from .utils import check_paths_equiv
from .utils import run_cmd


def prepare_clone(repo: str, clone_path: Path, rev: str, cfg: RunConfig) -> Repo:
    """Prepare a local clone of a remote git repository."""
    if cfg.verbose:
        print(f"prepare clone dir: {clone_path}")
    clone: Optional[Repo] = None
    if clone_path.exists():
        clone = prepare_existing_clone(repo, clone_path, cfg)
    if clone is None:
        if cfg.verbose:
            print(f"clone fresh repo {repo} to {clone_path}")
        clone_path.mkdir(parents=True, exist_ok=True)
        clone = Repo.clone_from(repo, clone_path)
    assert clone is not None  # mypy
    if cfg.verbose:
        print(f"check out rev: {rev}")
    clone.git.fetch(all=True)
    clone.git.checkout(rev)
    if not clone.head.is_detached:
        clone.git.pull()
    return clone


def prepare_existing_clone(
    repo: str, clone_path: Path, cfg: RunConfig
) -> Optional[Repo]:
    try:
        clone = Repo(clone_path)
    except InvalidGitRepositoryError:
        pass
    else:
        # Check whether the repo is our target repo based on the origin url
        # Note that this check will fail if, e.g., one link is ssh and the
        # other https although the repo is the same
        if clone.remote().url == repo:
            if not clone.is_dirty():
                if cfg.verbose:
                    print(f"use existing clone: {clone_path}")
                return clone
    if not clone_path.is_dir() or any(clone_path.iterdir()):
        if not cfg.force:
            raise PathExistsError(clone_path)
        shutil.rmtree(clone_path)
    return None


def install_exe(clone_path: Path, cfg: RunConfig, exe: str = "pyflexplot") -> Path:
    """Install pyflexplot into a virtual env and return the executable path."""
    os.chdir(clone_path)
    if not Path("Makefile").exists():
        raise Exception(f"missing Makefile in {os.path.abspath(os.curdir)}")
    venv_path = "venv"
    cmd_args = ["make", "install", "CHAIN=1", f"VENV_DIR={venv_path}"]
    for line in run_cmd(cmd_args, real_time=True):
        if cfg.verbose:
            print(line)
    bin_path = Path(venv_path).absolute() / "bin"
    if not (bin_path / "python").exists():
        raise Exception(f"installation of {exe} failed: no bin directory {bin_path}")
    exe_path = bin_path / exe
    return exe_path


def zip_presets_infiles(plot_cfg):
    infiles: Sequence[Optional[str]]
    n_pre = len(plot_cfg.presets)
    n_in = len(plot_cfg.infiles)
    if n_in == 0:
        infiles = [None] * n_pre
    elif n_in == 1:
        infiles = [next(iter(plot_cfg.infiles))] * n_pre
    elif n_in == n_pre:
        infiles = plot_cfg.infiles
    else:
        raise Exception(
            f"incompatible numbers of presets ({n_pre}) and infiles ({n_in})"
        )
    return zip(plot_cfg.presets, infiles)


def prepare_work_path(work_path: Path, cfg: RunConfig) -> None:
    if work_path.exists() and any(work_path.iterdir()):
        if not cfg.force:
            raise PathExistsError(work_path)
        shutil.rmtree(work_path)
    work_path.mkdir(parents=True, exist_ok=True)


def create_plots(
    exe_path: Path, work_path: Path, plot_cfg: PlotConfig, cfg: RunConfig
) -> List[Path]:
    """Create plots for multiple presets with one call per preset."""
    plot_paths: List[Path] = []
    for preset, infile in zip_presets_infiles(plot_cfg):
        plot_paths.extend(
            create_plots_preset(exe_path, work_path, preset, infile, plot_cfg, cfg)
        )
    return plot_paths


# pylint: disable=R0912  # too-many-branches (>12)
# pylint: disable=R0913  # too-many-arguments (>5)
# pylint: disable=R0914  # too-many-locals (>15)
def create_plots_preset(
    exe_path: Path,
    work_path: Path,
    preset: str,
    infile: Optional[str],
    plot_cfg: PlotConfig,
    cfg: RunConfig,
) -> List[Path]:
    """Create plots for an individual preset."""
    os.chdir(work_path)
    if plot_cfg.data_path:
        data_path = Path("data")
        if data_path.exists():
            if not data_path.is_symlink():
                raise Exception(f"{data_path.absolute()} exists and is not a symlink")
            data_path.unlink()
        Path("data").symlink_to(plot_cfg.data_path)

    cmd_args = [
        str(exe_path),
        "--no-show-version",
        f"--preset={preset}",
    ]
    if infile:
        cmd_args += ["--setup", "infile", infile]
    if plot_cfg.only:
        cmd_args += [f"--only={plot_cfg.only}"]
    cmd_args_dry = cmd_args + ["--dry-run"]
    cmd_args += [f"--num-procs={plot_cfg.num_procs}"]

    # Perform dry-run to obtain the plots that will be produced
    n_plots = perform_dry_run(cmd_args_dry, cfg)

    # Perform actual run, using the number of plots to show progress
    if cfg.verbose:
        print(f"current directory: {Path('.').absolute()}")
    print(f"create {n_plots} plots:")
    print(f"$ {' '.join(cmd_args)}")
    plot_paths: List[Path] = []
    i_plot = 0
    for i_line, line in enumerate(run_cmd(cmd_args, real_time=True)):
        if cfg.debug:
            print(f"({i_line}) {line}")
        try:
            _, plot = line.split(" -> ")
        except ValueError:
            continue
        i_plot += 1
        prog = f"[{i_plot / n_plots:.0%}]"
        if cfg.verbose:
            print(f"{prog} {line}")
        else:
            print(f"\r{prog} {i_plot}/{n_plots}", end="", flush=True)
        plot_path = work_path / plot
        plot_paths.append(plot_path)
    if not cfg.verbose:
        print()

    return plot_paths


def perform_dry_run(cmd_args_dry: List[str], cfg: RunConfig) -> int:
    """Perform a dry-run to obtain the number of plots to be created."""
    if cfg.verbose:
        print(
            "perform dry run to identify plots to be created:\n$ "
            + " ".join(cmd_args_dry)
        )
    n_plots = 0
    for line in run_cmd(cmd_args_dry, real_time=True):
        try:
            _, _ = line.split(" -> ")
        except ValueError:
            continue
        else:
            n_plots += 1
    if cfg.verbose:
        print(f"expecting {n_plots} to be created")
    return n_plots


@dataclass
class PlotPair:
    path1: Path
    path2: Path
    base1: Optional[Path]
    base2: Optional[Path]

    def __post_init__(self) -> None:
        shared1 = self.path1.relative_to(self.base1) if self.base1 else self.path1
        shared2 = self.path2.relative_to(self.base2) if self.base2 else self.path2
        if shared1 != shared2:
            raise ValueError(
                "inconsistent paths and bases; shared path components differ:"
                f" {shared1} != {shared2}"
            )
        self.shared_path: Path = shared1

    def compare(self, diffs_path: Path, cfg: RunConfig) -> Optional[Path]:
        if cfg.verbose:
            print(f"comparing pair {self.shared_path}")
        if filecmp.cmp(self.path1, self.path2):
            print(f"identical: {self.shared_path}")
            return None
        print(f"differing: {self.shared_path}")
        diff_path = diffs_path / self.shared_path
        cmd_args = ["compare", str(self.path1), str(self.path2), str(diff_path)]
        if cfg.verbose:
            print("creating diff plot:\n$ " + " \\\n    ".join(cmd_args))
        run_cmd(cmd_args)
        return diff_path


class PlotPairSequence:
    """A sequence of ``PlotPair`` instances."""

    def __init__(
        self,
        paths1: Sequence[Path],
        paths2: Sequence[Path],
        base1: Optional[Path],
        base2: Optional[Path],
        sort: bool = True,
    ) -> None:
        """Create an instance of ``PlotPair``."""
        paths1 = list(paths1)
        paths2 = list(paths2)
        check_paths_equiv(
            paths1=paths1,
            paths2=paths2,
            base1=base1,
            base2=base2,
            sort_rel=sort,
            action="warn",
            del_missing=True,
        )
        self.pairs: List[PlotPair] = [
            PlotPair(path1=old_path, path2=new_path, base1=base1, base2=base2)
            for old_path, new_path in zip(paths1, paths2)
        ]

    def compare(self, diffs_path: Path, cfg: RunConfig) -> List[Path]:
        """Compare the pairs of plots.

        For pairs that differ, diff plots showing the differences are created.

        Args:
            diffs_path: Path where diff plots are saved.

            cfg: Run configuration.

        """
        print(f"comparing {len(self)} pairs of plots")
        diff_paths: List[Path] = []
        for pair in self:
            diff_path = pair.compare(diffs_path, cfg)
            if diff_path is not None:
                diff_paths.append(diff_path)
        return diff_paths

    def __iter__(self) -> Iterator[PlotPair]:
        return iter(self.pairs)

    def __len__(self) -> int:
        return len(self.pairs)
