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
from .main import animate_diff_plots
from .main import create_plots
from .main import install_exe
from .main import PlotPairSequence
from .main import prepare_clone
from .main import prepare_work_path
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
    "--infile",
    "infiles",
    help=(
        "input file path overriding the input file specified in the preset;"
        " incompatible with --infiles-old-new; may be omitted, passed once or passed"
        " the same number of times as --preset, in which case the infiles and presets"
        " are paired in order"
    ),
    type=PathlibPath(),
    multiple=True,
)
@click.option(
    "--infiles-old-new",
    "infiles_old_new",
    help=(
        "pair of input file paths overriding the input file specified in the old and"
        " new preset, respectively; incompatible with --infile; may be omitted, passed"
        " once or passed the same number of times as --preset, in which case the infile"
        " pairs and presets are paired in order"
    ),
    nargs=2,
    type=PathlibPath(),
    multiple=True,
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
    help=(
        "reuse venvs of existing repo clones instead of reinstalling them; overridden"
        "by --reuse-(old|new)-install/--reinstall-(old|new)"
    ),
    default=False,
)
@click.option(
    "--reuse-new-install/--reinstall-new",
    help=(
        "reuse venv of existing clones of new repo instead of reinstalling it;"
        " overrides --reuse-installs/--reinstall for new repo"
    ),
    default=None,
)
@click.option(
    "--reuse-old-install/--reinstall-old",
    help=(
        "reuse venv of existing clones of old repo instead of reinstalling it;"
        " overrides --reuse-installs/--reinstall for old repo"
    ),
    default=None,
)
@click.option(
    "--reuse-new-plots/--replot-new",
    help=(
        "reuse existing new plots rather than recomputing them; overrides"
        " --reuse-plots/--replot for new plots"
    ),
    default=None,
)
@click.option(
    "--reuse-old-plots/--replot-old",
    help=(
        "reuse existing old plots rather than recomputing them; overrides"
        " --reuse-plots/--replot for old plots"
    ),
    default=None,
)
@click.option(
    "--reuse-plots/--replot",
    help=(
        "reuse existing plots rather than recomputing them; overridden by"
        " --reuse-(old|new)-plots/--replot-(old|new)"
    ),
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
    "--work",
    "wdir_path",
    help="working directory",
    default="pyflexplot-test",
    type=PathlibPath(),
)
@click.pass_context
# pylint: disable=R0912  # too-many-branches (>12)
# pylint: disable=R0913  # too-many-arguments (>5)
# pylint: disable=R0914  # too-many-locals (>15)
# pylint: disable=R0915  # too-many-statements (>50)
def cli(
    ctx: Context,
    data_path: Path,
    infiles: Tuple[Path, ...],
    infiles_old_new: Tuple[Tuple[Path, Path], ...],
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
    reuse_new_install: Optional[bool],
    reuse_old_install: Optional[bool],
    reuse_new_plots: Optional[bool],
    reuse_old_plots: Optional[bool],
    reuse_plots: bool,
    wdir_path: Path,
    **cfg_kwargs,
) -> None:
    _name_ = "cli.cli"
    cfg = RunConfig(**cfg_kwargs)

    check_for_active_venv(ctx)

    if cfg.debug:
        print(f"DBG:{_name_}: prepare presets")
    old_presets, new_presets = prepare_presets(ctx, presets, presets_old_new)
    check_infiles(ctx, infiles, len(old_presets))
    old_infiles, new_infiles = prepare_infiles(
        ctx, infiles, infiles_old_new, len(old_presets)
    )
    del infiles

    if cfg.debug:
        print(f"DBG:{_name_}: prepare data paths")
    start_path = Path(".").absolute()
    old_data_path, new_data_path = prepare_data_paths(
        ctx,
        data_path,
        old_data_path,
        new_data_path,
        old_default_path=None if old_infiles else Path(DEFAULT_DATA_PATH),
        new_default_path=None if new_infiles else Path(DEFAULT_DATA_PATH),
    )
    del data_path

    if cfg.debug:
        print(f"DBG:{_name_}: prepare install reuse flags")
    reuse_old_install, reuse_new_install = prepare_reuse(
        reuse_installs, reuse_old_install, reuse_new_install
    )
    del reuse_installs

    if cfg.debug:
        print(f"DBG:{_name_}: prepare plot reuse flags")
    reuse_old_plots, reuse_new_plots = prepare_reuse(
        reuse_plots, reuse_old_plots, reuse_new_plots
    )
    del reuse_plots

    if cfg.debug:
        print(f"DBG:{_name_}: prepare old rev")
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

    if cfg.verbose:
        print("+" * 40)
        print("{:20}: {}".format("old_data_path", old_data_path))
        print("{:20}: {}".format("new_data_path", new_data_path))
        print("{:20}: {}".format("old_infiles", list(map(str, old_infiles))))
        print("{:20}: {}".format("new_infiles", list(map(str, new_infiles))))
        print("{:20}: {}".format("old_presets", old_presets))
        print("{:20}: {}".format("new_presets", new_presets))
        print("{:20}: {}".format("old_rev", old_rev))
        print("{:20}: {}".format("new_rev", new_rev))
        #
        print("{:20}: {}".format("num_procs", num_procs))
        print("{:20}: {}".format("only", only))
        print("{:20}: {}".format("repo_path", repo_path))
        print("{:20}: {}".format("wdir_path", wdir_path))
        print("+" * 40)

    if cfg.debug:
        print(f"DBG:{_name_}: prepare paths")
    wdir_path = wdir_path.absolute()
    clones_path = wdir_path / "git"
    old_clones_path = clones_path / old_rev
    new_clones_path = clones_path / new_rev
    old_work_path = wdir_path / "work" / old_rev
    new_work_path = wdir_path / "work" / new_rev
    diffs_path = wdir_path / "work" / f"{old_rev}_vs_{new_rev}"
    clones_path.mkdir(parents=True, exist_ok=True)
    diffs_path.mkdir(parents=True, exist_ok=True)

    old_wdir_cfg = WorkDirConfig(
        path=old_work_path,
        reuse=reuse_old_plots,
    )
    new_wdir_cfg = WorkDirConfig(
        path=new_work_path,
        reuse=reuse_new_plots,
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
        reuse=reuse_old_install,
        wdir=old_wdir_cfg,
    )
    new_clone_cfg = CloneConfig(
        path=new_clones_path,
        rev=new_rev,
        reuse=reuse_new_install,
        wdir=new_wdir_cfg,
    )
    old_plot_cfg = PlotConfig(
        data_path=old_data_path,
        infiles=old_infiles,
        num_procs=num_procs,
        only=only,
        presets=old_presets,
        reuse=reuse_old_plots,
    )
    new_plot_cfg = PlotConfig(
        data_path=new_data_path,
        infiles=new_infiles,
        num_procs=num_procs,
        only=only,
        presets=new_presets,
        reuse=reuse_new_plots,
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: prepare old executable")
    old_exe_path = prepare_exe("old", repo_path, old_clone_cfg, cfg)

    if cfg.debug:
        print(f"\nDBG:{_name_}: prepare new executable")
    new_exe_path = prepare_exe("new", repo_path, new_clone_cfg, cfg)

    if cfg.debug:
        print(f"\nDBG:{_name_}: prepare work dirs")
    prepare_work_path(old_wdir_cfg, cfg)
    prepare_work_path(new_wdir_cfg, cfg)
    prepare_work_path(diffs_wdir_cfg, cfg)

    if cfg.debug:
        print(f"\nDBG:{_name_}: create old plots")
    print(f"prepare old plots in {old_exe_path}")
    old_plot_paths = create_plots(
        old_exe_path, old_clone_cfg.wdir.path, old_plot_cfg, cfg
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: create new plots")
    print(f"prepare new plots in {new_exe_path}")
    new_plot_paths = create_plots(
        new_exe_path, new_clone_cfg.wdir.path, new_plot_cfg, cfg
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: compare plots")
    plot_pairs = PlotPairSequence(
        paths1=old_plot_paths,
        paths2=new_plot_paths,
        base1=old_clone_cfg.wdir.path,
        base2=new_clone_cfg.wdir.path,
    )
    diff_plot_paths = plot_pairs.create_diffs(diffs_path, cfg, err_ok=True)
    n_plots = len(plot_pairs)
    n_diff = len(diff_plot_paths)
    print(f"{n_diff}/{n_plots} ({n_diff / n_plots:.0%}) plot pairs differ")
    if diff_plot_paths:
        if cfg.debug:
            print(f"DBG:{_name_}: create composite diff plot")
        composite_diff_plot = plot_pairs.create_composite_diff(diffs_path, cfg)
        animated_diff_plot = animate_diff_plots(diffs_path, diff_plot_paths, cfg)
        print()
        print(f"{n_diff} new diff plots in {diffs_path.relative_to(start_path)}/")
        if cfg.verbose:
            for path in diff_plot_paths:
                print(path.relative_to(start_path))
        print()
        print(f"diff composite: {composite_diff_plot.relative_to(start_path)}")
        print(f"diff animation: {animated_diff_plot.relative_to(start_path)}")


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


def prepare_infiles(
    ctx: Context,
    infiles: Sequence[Path],
    infiles_old_new: Sequence[Tuple[Path, Path]],
    n_presets: int,
    absolute: bool = True,
) -> Tuple[List[Path], List[Path]]:
    """Prepare infile paths for old and new revision."""
    if not infiles and not infiles_old_new:
        old_infiles = []
        new_infiles = []
    elif infiles and not infiles_old_new:
        if len(infiles) in [1, n_presets]:
            old_infiles = [Path(infile) for infile in infiles]
            new_infiles = [Path(infile) for infile in infiles]
        else:
            click.echo(
                f"error: wrong number of --infile: {len(infiles)} neither 1 nor"
                f" {n_presets} (like --preset/--presets-old-new)",
                file=sys.stderr,
            )
            ctx.exit(1)
    elif infiles_old_new and not infiles:
        if len(infiles_old_new) in [1, n_presets]:
            old_infiles = [Path(old_infile) for old_infile, _ in infiles_old_new]
            new_infiles = [Path(new_infile) for _, new_infile in infiles_old_new]
        else:
            click.echo(
                f"error: wrong number of --infiles-old-new: {len(infiles_old_new)}"
                f" neither 1 nor {n_presets} (like --preset/--presets-old-new)",
                file=sys.stderr,
            )
            ctx.exit(1)
    else:
        click.echo(
            "error: --infile and --infiles-old-new are incompatible", file=sys.stderr
        )
        ctx.exit(1)
    if absolute:
        old_infiles = [path.absolute() for path in old_infiles]
        new_infiles = [path.absolute() for path in new_infiles]
    return (old_infiles, new_infiles)


# pylint: disable=R0913  # too-many-arguments (>5)
def prepare_data_paths(
    ctx: Context,
    path: Optional[Path],
    old_path: Optional[Path],
    new_path: Optional[Path],
    old_default_path: Optional[Path],
    new_default_path: Optional[Path],
    absolute: bool = True,
) -> Tuple[Optional[Path], Optional[Path]]:
    old_path = old_path or path or old_default_path
    new_path = new_path or path or new_default_path
    if old_path and not old_path.exists():
        click.echo(
            f"error: old data path does not exist: '{old_path}/'", file=sys.stderr
        )
        ctx.exit(1)
    if new_path and not new_path.exists():
        click.echo(
            f"error: new data path does not exist: '{new_path}/'", file=sys.stderr
        )
        ctx.exit(1)
    if absolute:
        old_path = None if not old_path else old_path.absolute()
        new_path = None if not new_path else new_path.absolute()
    return old_path, new_path


def prepare_reuse(
    reuse: bool, reuse_old: Optional[bool], reuse_new: Optional[bool]
) -> Tuple[bool, bool]:
    if reuse_old is None:
        reuse_old = reuse
    if reuse_new is None:
        reuse_new = reuse
    return reuse_old, reuse_new


def prepare_exe(
    case: str,
    repo_path: str,
    clone_cfg: CloneConfig,
    cfg: RunConfig,
) -> Path:
    """Prepare clone of repo, install into virtual env and return exe path."""
    print(f"prepare {case} clone or {repo_path}@{clone_cfg.rev} at {clone_cfg.path}")
    prepare_clone(repo_path, clone_cfg, cfg)
    if cfg.verbose:
        print(f"prepare {case} executable in {clone_cfg.path}")
    exe_path = install_exe(clone_cfg.path, clone_cfg.reuse, cfg)
    return exe_path
