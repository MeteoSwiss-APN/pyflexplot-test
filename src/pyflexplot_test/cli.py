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
from click import Context

# Local
from . import __version__
from .config import CloneConfig
from .config import PlotConfig
from .config import RunConfig
from .config import WorkDirConfig
from .exceptions import PathExistsError
from .main import create_plots as _create_plots_core
from .main import install_exe
from .main import PlotPairSequence
from .main import prepare_clone
from .main import prepare_work_path as _prepare_work_path_core
from .utils import git_get_remote_tags

DEFAULT_DATA_PATH = "data"


class PathlibPath(click.ParamType):
    name = "Path"

    # pylint: disable=W0613  # unused-argument (param, ctx)
    # pylint: disable=R0201  # no-self-use
    def convert(self, value, param, ctx) -> Path:
        return Path(value)


def check_for_active_venv(ctx: Context) -> None:
    """Abort if an active virtual environment is detected."""
    venv = os.getenv("VIRTUAL_ENV")
    if not venv:
        return
    click.echo(f"error: active virtual environment detected: {venv}", file=sys.stderr)
    exe = os.path.basename(sys.argv[0])
    click.echo(f"deactivate it and call {exe} directly by its path", file=sys.stderr)
    ctx.exit(1)


def check_infiles(ctx: Context, infiles: Sequence[Path], n_presets: int) -> None:
    n_in = len(infiles)
    if n_in > n_presets:
        click.echo(
            f"error: more infiles ({n_in}) than presets ({n_presets})", file=sys.stderr
        )
        ctx.exit(1)
    if n_presets > 1 and n_in > 1 and n_in != n_presets:
        click.echo(
            f"error: multiple presets ({n_presets}) and infiles ({n_in}), but their"
            " numbersdon't match",
            file=sys.stderr,
        )
        ctx.exit(1)


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--data",
    "data_path",
    help=(
        f"path to data directory; defaults to {DEFAULT_DATA_PATH}; overridden by"
        " --old-data and --new-data; ignored if --infile and/or --infiles-old-new are"
        " passed"
    ),
    type=PathlibPath(),
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
    type=PathlibPath(),
    multiple=True,
    default=[],
)
@click.option(
    "--new-data",
    "new_data_path",
    help=(
        "path to data directory for --old-rev; overrides or defaults to --data;"
        " ignored if --infile and/or --infiles-old-new are passed"
    ),
    type=PathlibPath(),
    default=None,
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
    "--num-procs",
    help="number of parallel processes during plotting",
    type=int,
    default=1,
)
@click.option(
    "--old-data",
    "old_data_path",
    help=(
        "path to data directory for --new-rev; overrides or defaults to --data;"
        " ignored if --infile and/or --infiles-old-new are passed"
    ),
    type=PathlibPath(),
    default=None,
)
@click.option(
    "--presets-old-new",
    "presets_old_new",
    help=(
        "pair of presets used to create old and new plots, respectively; may be"
        " repeated; equivalent to (but incompatible with) --preset"
    ),
    nargs=2,
    multiple=True,
)
@click.option(
    "--old-rev",
    help=(
        "old revision of pyflexplot; defaults to lanew tag; may be anything"
        " that git can check out (tag name, branch name, commit hash)"
    ),
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
    help=(
        "preset used to create plots; may be repeated; equivalent to (but"
        " incompatible with) --presets-old-new"
    ),
    multiple=True,
)
@click.option(
    "--repo",
    "repo_path",
    help="pyflexplot repository path",
    default="git@github.com:MeteoSwiss-APN/pyflexplot.git",
)
@click.option(
    "--reuse-installs/--reinstall",
    help="reuse venvs of existing repo clones instead of reinstalling",
    default=False,
)
@click.option(
    "--reuse-plots/--recompute-plots",
    help="reuse existing plots rather than recomputing them",
    default=False,
)
@click.option(
    "-v",
    "verbosity",
    help="increase verbosity",
    count=True,
)
@click.version_option(
    __version__,
    "--version",
    "-V",
    message="%(version)s",
)
@click.option(
    "--work-dir",
    "work_dir_path",
    help="working directory",
    default="pyflexplot-test",
    type=PathlibPath(),
)
@click.pass_context
# pylint: disable=R0913  # too-many-arguments (>5)
# pylint: disable=R0914  # too-many-locals (>15)
def cli(
    ctx: Context,
    data_path: Path,
    infiles: Tuple[Path, ...],
    new_data_path: Optional[Path],
    new_rev: str,
    num_procs: int,
    old_data_path: Optional[Path],
    presets_old_new: Tuple[Tuple[str, str], ...],
    old_rev: Optional[str],
    only: Optional[int],
    presets: Tuple[str, ...],
    repo_path: str,
    reuse_installs: bool,
    reuse_plots: bool,
    work_dir_path: Path,
    **cfg_kwargs,
) -> None:
    _name_ = "cli.cli"
    cfg = RunConfig(**cfg_kwargs)

    check_for_active_venv(ctx)

    start_path = Path(".").absolute()
    # SR_TMP <
    if data_path is None:
        data_path = Path(DEFAULT_DATA_PATH)
    # SR_TMP >
    old_data_path, new_data_path = prepare_data_paths(
        data_path, old_data_path, new_data_path
    )
    old_presets, new_presets = prepare_presets(ctx, presets, presets_old_new)
    check_infiles(ctx, infiles, len(old_presets))
    # SR_TMP < TODO implement --old-infile and --new-infile or --infiles-old-new
    infiles = tuple([Path(infile).absolute() for infile in infiles])
    old_infiles, new_infiles = tuple(infiles), tuple(infiles)
    # SR_TMP >

    work_dir_path = work_dir_path.absolute()

    if old_rev is None:
        if cfg.verbose:
            print(f"obtain old_rev from repo {repo_path}")
        tags = git_get_remote_tags(repo_path)
        if cfg.verbose:
            sel_tags = tags if len(tags) <= 7 else tags[:3] + ["..."] + tags[-3:]
            print(f"select most recent of {len(tags)} tags ({', '.join(sel_tags)})")
        old_rev = tags[-1]
        if cfg.verbose:
            print(f"old_rev: {old_rev}")

    if cfg.debug:
        print(f"DBG:{_name_}: infiles: {infiles}")
        print(f"DBG:{_name_}: new_data_path: {new_data_path}")
        print(f"DBG:{_name_}: new_presets: {new_presets}")
        print(f"DBG:{_name_}: new_rev: {new_rev}")
        print(f"DBG:{_name_}: num_procs: {num_procs}")
        print(f"DBG:{_name_}: old_data_path: {old_data_path}")
        print(f"DBG:{_name_}: old_presets: {old_presets}")
        print(f"DBG:{_name_}: old_rev: {old_rev}")
        print(f"DBG:{_name_}: only: {only}")
        print(f"DBG:{_name_}: repo_path: {repo_path}")
        print(f"DBG:{_name_}: work_dir_path: {work_dir_path}")

    clones_path = work_dir_path / "git"
    clones_path.mkdir(parents=True, exist_ok=True)

    old_clones_path = clones_path / old_rev
    new_clones_path = clones_path / new_rev

    old_work_path = work_dir_path / "work" / old_rev
    new_work_path = work_dir_path / "work" / new_rev

    diffs_path = work_dir_path / "work" / f"{old_rev}_vs_{new_rev}"
    diffs_path.mkdir(parents=True, exist_ok=True)

    old_wdir_cfg = WorkDirConfig(
        path=old_work_path,
        reuse=reuse_plots,
        replace=cfg.force,
    )
    new_wdir_cfg = WorkDirConfig(
        path=new_work_path,
        reuse=reuse_plots,
        replace=cfg.force,
    )
    # Note: This always replaces all diff plots, even if a rerun is made with
    # fewer presets than a previous runs, in which case the diff plots of the
    # left-out presets will be lost (but can easily be recomputed by rerunning
    # with all previous presets at once with --reuse-plots and --reuse-installs)
    diffs_wdir_cfg = WorkDirConfig(
        path=diffs_path,
        reuse=False,
        replace=True,
    )
    old_clone_cfg = CloneConfig(
        path=old_clones_path,
        rev=old_rev,
        reuse=reuse_installs,
        wdir=old_wdir_cfg,
    )
    new_clone_cfg = CloneConfig(
        path=new_clones_path,
        rev=new_rev,
        reuse=reuse_installs,
        wdir=new_wdir_cfg,
    )
    old_plot_cfg = PlotConfig(
        data_path=old_data_path,
        infiles=infiles,  # SR_TMP TODO old-specific infiles
        num_procs=num_procs,
        only=only,
        presets=old_presets,
        reuse=reuse_plots,  # SR_TMP TODO old-specific reuse
    )
    new_plot_cfg = PlotConfig(
        data_path=new_data_path,
        infiles=infiles,  # SR_TMP TODO new-specific infiles
        num_procs=num_procs,
        only=only,
        presets=new_presets,
        reuse=reuse_plots,  # SR_TMP TODO new-specific reuse
    )

    old_exe_path = prepare_exe(
        ctx, repo_path=repo_path, case="old", clone_cfg=old_clone_cfg, cfg=cfg
    )
    new_exe_path = prepare_exe(
        ctx, repo_path=repo_path, case="new", clone_cfg=new_clone_cfg, cfg=cfg
    )

    prepare_work_path(ctx, "old work dir", old_wdir_cfg, cfg)
    prepare_work_path(ctx, "new work dir", new_wdir_cfg, cfg)
    prepare_work_path(ctx, "diffs dir", diffs_wdir_cfg, cfg)

    old_plot_paths = create_plots(
        "old", old_exe_path, old_clone_cfg.wdir.path, old_plot_cfg, cfg
    )
    new_plot_paths = create_plots(
        "new", new_exe_path, new_clone_cfg.wdir.path, new_plot_cfg, cfg
    )

    plot_pairs = PlotPairSequence(
        paths1=old_plot_paths,
        paths2=new_plot_paths,
        base1=old_clone_cfg.wdir.path,
        base2=new_clone_cfg.wdir.path,
    )

    # Compare plots
    diff_plot_paths = plot_pairs.compare(diffs_path, cfg)
    if diff_plot_paths:
        print(
            f"created {len(diff_plot_paths)} diff plots in "
            f"{diffs_path.relative_to(start_path)}"
        )
        if cfg.verbose:
            print("\n".join([str(p.relative_to(start_path)) for p in diff_plot_paths]))


def prepare_presets(
    ctx: Context,
    presets: Sequence[str],
    presets_old_new: Sequence[Tuple[str, str]],
) -> Tuple[List[str], List[str]]:
    """Prepare preset strings for old and new revision."""
    old_presets: List[str] = []
    new_presets: List[str] = []
    if not presets and not presets_old_new:
        click.echo(
            "must pass --preset or --presets-old-new at least once", file=sys.stderr
        )
        ctx.exit(1)
    elif presets:
        old_presets.extend(presets)
        new_presets.extend(presets)
    else:
        for old_preset, new_preset in presets_old_new:
            old_presets.append(old_preset)
            new_presets.append(new_preset)
    for presets_i in [old_presets, new_presets]:
        for preset in presets_i:
            if preset.endswith("_pdf"):
                raise NotImplementedError(f"PDF presets ({preset})")
    return old_presets, new_presets


def prepare_data_paths(
    path: Optional[Path], old_path: Optional[Path], new_path: Optional[Path]
) -> Tuple[Path, Path]:
    assert path is not None  # mypy  # SR_TMP
    if old_path is None:
        old_path = path
    if new_path is None:
        new_path = path
    return old_path.absolute(), new_path.absolute()


# pylint: disable=R0913  # too-many-arguments (>5)
def prepare_exe(
    ctx: Context,
    *,
    case: str,
    cfg: RunConfig,
    clone_cfg: CloneConfig,
    repo_path: str,
) -> Path:
    """Prepare clone of repo, install into virtual env and return exe path."""
    print(f"prepare {case} clone or {repo_path}@{clone_cfg.rev} at {clone_cfg.path}")
    try:
        prepare_clone(repo_path, clone_cfg, cfg)
    except PathExistsError as e:
        click.echo(
            f"error: preparing {case} clone failed because {e} already exists"
            "; use --reuse-installs or similar to reuse or --force to overwrite",
            file=sys.stderr,
        )
        ctx.exit(1)
    if cfg.verbose:
        print(f"prepare {case} executable in {clone_cfg.path}")
    exe_path = install_exe(clone_cfg.path, clone_cfg.reuse, cfg)
    return exe_path


def prepare_work_path(
    ctx: Context, name: str, wdir_cfg: WorkDirConfig, cfg: RunConfig
) -> None:
    try:
        _prepare_work_path_core(wdir_cfg, cfg)
    except PathExistsError as e:
        click.echo(
            f"error: preparing {name} failed because {e} already exists"
            "; use --reuse-plots or similar to reuse or --force to overwrite",
            file=sys.stderr,
        )
        ctx.exit(1)


def create_plots(
    case: str, exe_path: Path, work_path: Path, plot_cfg: PlotConfig, cfg: RunConfig
) -> List[Path]:
    print(f"prepare {case} plots in {work_path}")
    return _create_plots_core(exe_path, work_path, plot_cfg, cfg)
