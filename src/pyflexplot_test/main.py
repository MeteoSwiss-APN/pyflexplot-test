"""Main module."""
# Standard library
import os
import shutil
from pathlib import Path
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
    for line in run_cmd(cmd_args):
        if cfg.verbose:
            print(line)
    bin_path = Path(venv_path).absolute() / "bin"
    if not (bin_path / "python").exists():
        raise Exception(f"installation of {exe} failed: no bin directory {bin_path}")
    return bin_path


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

    cmd_args = [str(exe_path)]
    cmd_args.append(f"--num-procs={plot_cfg.num_procs}")
    cmd_args.append(f"--preset={preset}")
    if infile:
        cmd_args.append(f"--setup infile {infile}")
    if plot_cfg.only:
        cmd_args.append(f"--only={plot_cfg.only}")

    # Perform dry-run to obtain the plots that will be produced
    cmd_args_dry = cmd_args + ["--dry-run"]
    plots: List[str] = []
    for line in run_cmd(cmd_args_dry):
        try:
            _, plot = line.split(" -> ")
        except ValueError:
            continue
        else:
            plots.append(plot)

    # Perform actual run, using the number of plots to show progress
    n_plots = len(plots)
    print(f"create {n_plots} plots:")
    print(f"$ {' '.join(cmd_args)}")
    i_plot = 0
    for line in run_cmd(cmd_args):
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
    if not cfg.verbose:
        print()

    # Check that plots have been created as expected
    plot_paths: List[Path] = []
    for plot in plots:
        plot_path = work_path / plot
        if not plot_path.exists():
            print(f"warning: plot has not been created: {plot}")
        else:
            plot_paths.append(plot_path)

    return plot_paths
