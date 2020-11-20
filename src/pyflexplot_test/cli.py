"""Command line interface."""
# Standard library
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

# Third-party
import click
from git import Repo
from git.exc import InvalidGitRepositoryError

# Local
from . import __version__


class PathExistsError(Exception):
    """Path already exists."""


def tmp_path(base: str, _time_stamp: List[int] = []) -> str:
    """Get a temporary path containing a time stamp."""
    if not _time_stamp:
        _time_stamp.append(int(time.time()))
    return f"{base}{_time_stamp[0]}"


class PathlibPath(click.ParamType):
    name = "pathlib.Path"

    def convert(self, value, param, ctx) -> Path:
        return Path(value)


def check_for_active_venv(ctx: click.Context) -> None:
    """Abort if an active virtual environment is detected."""
    venv = os.getenv("VIRTUAL_ENV")
    if not venv:
        return
    click.echo(f"error: active virtual environment detected: {venv}", file=sys.stderr)
    exe = os.path.basename(sys.argv[0])
    click.echo(f"deactivate it and call {exe} directly by its path", file=sys.stderr)
    ctx.exit(1)


def check_infiles(
    ctx: click.Context, infiles: Sequence[str], presets: Sequence[str]
) -> None:
    n_in = len(infiles)
    n_pre = len(presets)
    if n_in > n_pre:
        click.echo(
            f"error: more infiles ({n_in}) than presets ({n_pre})", file=sys.stderr
        )
        ctx.exit(1)
    if n_pre > 1 and n_in > 1 and n_in != n_pre:
        click.echo(
            f"error: multiple presets ({n_pre}) and infiles ({n_in}), but their numbers"
            " don't match",
            file=sys.stderr,
        )
        ctx.exit(1)


@dataclass
class RunConfig:
    force: bool
    verbose: bool


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


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--data-path",
    help="path to data directory",
    type=PathlibPath(),
    default=None,
)
@click.option(
    "-f",
    "--force",
    help="overwrite existing repos etc.",
    is_flag=True,
    default=False,
)
@click.option(
    "--infile",
    "infiles",
    help=(
        "input file (netcdf) overriding that specified in the preset; --infile must not"
        " be passed more often than --preset; if both --preset and --infile are passed"
        " more than once, their numbers must match"
    ),
    multiple=True,
    default=[],
)
@click.option(
    "--only",
    help="restrict the number of plots per preset",
    type=int,
    default=None,
)
@click.option(
    "--preset",
    "presets",
    help="preset used to create plots; may be repeated",
    multiple=True,
    default=["opr/*/all_png"],
)
@click.option(
    "--num-procs",
    help="number of parallel processes during plotting",
    type=int,
    default=1,
)
@click.option(
    "--old-rev",
    help=(
        "old revision of pyflexplot; defaults to lanew tag; may be anything"
        " that git can check out (tag name, branch name, commit hash)"
    ),
)
@click.option(
    "--repo",
    "repo_path",
    help="pyflexplot repository path",
    default="git@github.com:MeteoSwiss-APN/pyflexplot.git",
)
@click.option(
    "--new-rev",
    help=(
        "new revision of pyflexplot; defaults to 'dev' (head of development"
        " branch); may be anything that git can check out (tag name, branch"
        " name, commit hash"
    ),
    default="dev",
)
@click.option(
    "--work-dir",
    "work_dir_path",
    help="working directory",
    default=tmp_path("pyflexplot-new-"),
    type=PathlibPath(),
)
@click.option("-v", "verbose", help="verbose output", is_flag=True, default=False)
@click.version_option(
    __version__,
    "--version",
    "-V",
    message="%(version)s",
)
@click.pass_context
def cli(
    ctx: click.Context,
    data_path: Optional[Path],
    infiles: Tuple[str, ...],
    num_procs: int,
    only: Optional[int],
    presets: Tuple[str, ...],
    old_rev: Optional[str],
    repo_path: str,
    new_rev: str,
    work_dir_path: Path,
    **cfg_kwargs,
) -> None:
    cfg = RunConfig(**cfg_kwargs)

    check_for_active_venv(ctx)
    check_infiles(ctx, infiles, presets)

    if data_path:
        data_path = data_path.absolute()

    for preset in presets:
        if preset.endswith("_pdf"):
            raise NotImplementedError(f"PDF presets ({preset})")

    infiles = tuple([str(Path(infile).absolute()) for infile in infiles])

    work_dir_path = work_dir_path.absolute()

    if cfg.verbose:
        print(f"data_path: {data_path}")
        print(f"infiles: {infiles}")
        print(f"num_procs: {num_procs}")
        print(f"only: {only}")
        print(f"presets: {presets}")
        print(f"old_rev: {old_rev}")
        print(f"repo_path: {repo_path}")
        print(f"new_rev: {new_rev}")
        print(f"work_dir_path: {work_dir_path}")

    if old_rev is None:
        if cfg.verbose:
            print(f"obtain old_rev from repo: {repo_path}")
        tags = git_get_remote_tags(repo_path)
        if cfg.verbose:
            print(f"select most recent of {len(tags)} tags ({', '.join(tags)})")
        old_rev = tags[-1]
        if cfg.verbose:
            print(f"old_rev: {old_rev}")

    clones_path = work_dir_path / "git"
    clones_path.mkdir(parents=True, exist_ok=True)

    old_clone_path = clones_path / old_rev
    new_clone_path = clones_path / new_rev

    old_work_path = work_dir_path / "work" / old_rev
    new_work_path = work_dir_path / "work" / new_rev

    old_repo_cfg = RepoConfig(
        clone_path=old_clone_path, rev=old_rev, work_path=old_work_path
    )
    new_repo_cfg = RepoConfig(
        clone_path=new_clone_path, rev=new_rev, work_path=new_work_path
    )

    plot_cfg = PlotConfig(
        presets=presets,
        infiles=infiles,
        data_path=data_path,
        num_procs=num_procs,
        only=only,
    )

    create_clone_and_plots(ctx, repo_path, "old", old_repo_cfg, plot_cfg, cfg)
    create_clone_and_plots(ctx, repo_path, "new", new_repo_cfg, plot_cfg, cfg)


def create_clone_and_plots(
    ctx: click.Context,
    repo_path: str,
    case: str,
    repo_cfg: RepoConfig,
    plot_cfg: PlotConfig,
    cfg: RunConfig,
) -> None:

    # Create clone of repository
    print(f"prepare {case} clone: {repo_path}@{repo_cfg.rev} -> {repo_cfg.clone_path}")
    try:
        prepare_clone(repo_path, repo_cfg.clone_path, repo_cfg.rev, cfg)
    except PathExistsError as e:
        click.echo(
            f"error: preparing {case} clone failed because '{e}' already exists"
            "; use -f or --force to overwrite",
            file=sys.stderr,
        )
        ctx.exit(1)

    # Install pyflexplot into virtual env
    exe_name = "pyflexplot"
    print(f"prepare {case} {exe_name} executable in {repo_cfg.clone_path}")
    bin_path = install(repo_cfg.clone_path, cfg)
    exe_path = bin_path / exe_name

    # Create plots
    print(f"create {case} plots with {exe_path} in {repo_cfg.work_path}")
    try:
        prepare_work_path(repo_cfg.work_path, cfg)
    except PathExistsError as e:
        click.echo(
            f"error: preparing {case} clone failed because '{e}' already exists"
            "; use -f or --force to overwrite",
            file=sys.stderr,
        )
        ctx.exit(1)
    os.chdir(repo_cfg.work_path)
    create_plots(exe_path, plot_cfg, cfg)


def prepare_clone(repo: str, clone_path: Path, rev: str, cfg: RunConfig) -> Repo:
    """Prepare a local clone of a remote git repository."""
    if cfg.verbose:
        print(f"prepare clone dir: {clone_path}")
    use_existing = False
    clone: Optional[Repo] = None
    if clone_path.exists():
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
                    use_existing = True
        if not use_existing and (not clone_path.is_dir() or any(clone_path.iterdir())):
            if not cfg.force:
                raise PathExistsError(clone_path)
            shutil.rmtree(clone_path)
    if not use_existing:
        if cfg.verbose:
            print(f"clone fresh repo {repo} to {clone_path}")
        clone_path.mkdir(parents=True, exist_ok=True)
        clone = Repo.clone_from(repo, clone_path)
    assert clone is not None  # mypy
    if cfg.verbose:
        print(f"check out rev: {rev}")
    clone.git.fetch(all=True)
    clone.git.checkout(rev)
    if use_existing and not clone.head.is_detached:
        clone.git.pull()
    return clone


def install(clone_path: Path, cfg: RunConfig, exe: str = "pyflexplot") -> Path:
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


def create_plots(exe_path: Path, plot_cfg: PlotConfig, cfg: RunConfig) -> None:
    """Create plots for multiple presets with one call per preset."""
    if plot_cfg.data_path:
        Path("data").symlink_to(plot_cfg.data_path)
    for preset, infile in zip_presets_infiles(plot_cfg):
        create_plots_preset(exe_path, preset, infile, plot_cfg, cfg)


def create_plots_preset(
    exe_path: Path,
    preset: str,
    infile: Optional[str],
    plot_cfg: PlotConfig,
    cfg: RunConfig,
) -> None:
    """Create plots for an individual preset."""
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


def git_get_remote_tags(repo: str) -> List[str]:
    """Get tags from remote git repository, sorted as version numbers."""
    cmd_args = ["git", "ls-remote", "--tags", "--sort=version:refname", repo]
    tags: List[str] = []
    for line in run_cmd(cmd_args):
        try:
            # Format: "<hash>\t<refs/tags/tag>"
            _, tag = line.split("\trefs/tags/")
        except ValueError:
            continue
        if not tag.endswith("^{}"):
            tags.append(tag)
    if not tags:
        raise Exception(f"no tags found for repo: {repo}")
    return tags


def run_cmd(args: List[str]) -> Iterator[str]:
    """Run a command and yield the standard output line by line."""
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None  # mypy
    with proc.stdout:
        for raw_line in iter(proc.stdout.readline, b""):
            line = raw_line.decode("utf-8").strip()
            yield line
    proc.wait()
    assert proc.stderr is not None  # mypy
    stderr = [line.decode("utf-8") for line in iter(proc.stderr.readline, b"")]
    # stdout, stderr = proc.communicate()
    if proc.returncode:
        raise Exception(
            f"error ({proc.returncode}) running command '{' '.join(args)}':\n"
            + "\n".join(stderr)
        )
