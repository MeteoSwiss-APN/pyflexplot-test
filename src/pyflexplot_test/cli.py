"""Command line interface."""
# Standard library
import os
import sys
from pathlib import Path
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

# Third-party
import click

# Local
from . import __version__
from .config import PlotConfig
from .config import RepoConfig
from .config import RunConfig
from .exceptions import PathExistsError
from .main import create_plots
from .main import install_exe
from .main import PlotPairSequence
from .main import prepare_clone
from .main import prepare_work_path
from .utils import git_get_remote_tags
from .utils import tmp_path


class PathlibPath(click.ParamType):
    name = "pathlib.Path"

    # pylint: disable=W0613  # unused-argument (param, ctx)
    # pylint: disable=R0201  # no-self-use
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
# pylint: disable=R0913  # too-many-arguments (>5)
# pylint: disable=R0914  # too-many-locals (>15)
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

    start_path = Path(".").absolute()
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
            sel_tags = tags if len(tags) <= 7 else tags[:3] + ["..."] + tags[-3:]
            print(f"select most recent of {len(tags)} tags ({', '.join(sel_tags)})")
        old_rev = tags[-1]
        if cfg.verbose:
            print(f"old_rev: {old_rev}")

    clones_path = work_dir_path / "git"
    clones_path.mkdir(parents=True, exist_ok=True)

    work_dir_path = work_dir_path / "work"

    diff_dir_path = work_dir_path / f"{old_rev}_vs_{new_rev}"
    diff_dir_path.mkdir(parents=True, exist_ok=True)

    old_repo_cfg = RepoConfig(
        rev=old_rev,
        clone_path=clones_path / old_rev,
        work_path=work_dir_path / old_rev,
    )
    new_repo_cfg = RepoConfig(
        rev=new_rev,
        clone_path=clones_path / new_rev,
        work_path=work_dir_path / new_rev,
    )
    plot_cfg = PlotConfig(
        presets=presets,
        infiles=infiles,
        data_path=data_path,
        num_procs=num_procs,
        only=only,
    )

    # Create plots
    old_plot_paths = create_clone_and_plots(
        ctx, repo_path, "old", old_repo_cfg, plot_cfg, cfg
    )
    new_plot_paths = create_clone_and_plots(
        ctx, repo_path, "new", new_repo_cfg, plot_cfg, cfg
    )
    plot_pairs = PlotPairSequence(
        paths1=old_plot_paths,
        paths2=new_plot_paths,
        base1=old_repo_cfg.work_path,
        base2=new_repo_cfg.work_path,
    )

    # Compare plots
    diff_plot_paths = plot_pairs.compare(diff_dir_path, cfg)
    if diff_plot_paths:
        print(
            f"created {len(diff_plot_paths)} diff plots in "
            f"{diff_dir_path.relative_to(start_path)}"
        )
        if cfg.verbose:
            print("\n".join([str(p.relative_to(start_path)) for p in diff_plot_paths]))


# pylint: disable=R0913  # too-many-arguments (>5)
def create_clone_and_plots(
    ctx: click.Context,
    repo_path: str,
    case: str,
    repo_cfg: RepoConfig,
    plot_cfg: PlotConfig,
    cfg: RunConfig,
) -> List[Path]:

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
    bin_path = install_exe(repo_cfg.clone_path, cfg)
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
    plot_paths = create_plots(exe_path, repo_cfg.work_path, plot_cfg, cfg)

    return plot_paths
