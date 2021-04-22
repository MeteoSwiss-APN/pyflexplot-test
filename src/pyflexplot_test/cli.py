"""Command line interface."""
# Standard library
import os
import sys
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

# Third-party
import click
from click import Context

# Local
from . import __version__
from .config import InstallConfig
from .config import PlotConfig
from .config import ReuseConfig
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


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--data",
    "data_path",
    help=(
        f"path to data directory; defaults to {DEFAULT_DATA_PATH}"
        "; overridden by --old-data and --new-data"
        "; ignored if --infile and/or --infiles-old-new are passed"
    ),
    type=PathlibPath(),
)
@click.option(
    "--infile",
    "infiles",
    help=(
        "input file path overriding the input file specified in the preset"
        "; incompatible with --infiles-old-new"
        "; may be omitted, passed once (in which case the same infile is used for all"
        " presets), passed the same number of times as --preset/--presets-old-new (in"
        " which case the infiles and presets are paired in order) or passed an"
        " arbitrary number of times if --preset/--presets-old-new is not passed more"
        " than once (in which case the same preset is used for all infiles)"
    ),
    type=PathlibPath(),
    multiple=True,
)
@click.option(
    "--infiles-old-new",
    "infiles_old_new",
    help=(
        "pair of input file paths overriding the input file specified in the old and"
        " new preset, respectively; may be repeated (see --infile for details)"
        "; equivalent to but incompatible with --infile"
    ),
    nargs=2,
    type=PathlibPath(),
    multiple=True,
)
@click.option(
    "--install-dir",
    "install_dir_path",
    help="install directory in which git clones and their venvs are saved",
    type=PathlibPath(),
    default="pyflexplot-test/install",
)
@click.option(
    "--new-data",
    "new_data_path",
    help=(
        "path to data directory for --old-rev; overrides or defaults to --data"
        "; ignored if --infile and/or --infiles-old-new are passed"
    ),
    type=PathlibPath(),
    default=None,
)
@click.option(
    "--new-rev",
    help=(
        "new revision of pyflexplot; defaults to 'dev' (head of development branch)"
        "; may be anything that git can check out (tag name, branch name, commit hash"
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
        "path to data directory for --new-rev; overrides or defaults to --data"
        "; ignored if --infile and/or --infiles-old-new are passed"
    ),
    type=PathlibPath(),
    default=None,
)
@click.option(
    "--presets-old-new",
    "presets_old_new",
    help=(
        "pair of presets used to create old and new plots, respectively"
        "; may be repeated (see --preset for details)"
        "; equivalent to but incompatible with --preset"
    ),
    nargs=2,
    multiple=True,
)
@click.option(
    "--old-rev",
    help=(
        "old revision of pyflexplot; defaults to lanew tag; may be anything that git"
        " can check out (tag name, branch name, commit hash)"
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
        "preset used to create plots; may be repeated; equivalent to but incompatible"
        " with --presets-old-new; may be omitted, passed once (in which case the same"
        " preset is used for all infiles), passed the same number of times as --infile"
        "/--infiles-old-new (in which case the presets and infiles are paired in order)"
        " or passed an arbitrary number of times if --infile/--infiles-old-new is not"
        " passed more than once (in which case the same infile is used for all presets)"
    ),
    multiple=True,
)
@click.option(
    "--repo",
    "repo_url",
    help="pyflexplot repository URL",
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
        "reuse venv of existing clones of new repo instead of reinstalling it"
        "; overrides --reuse-installs/--reinstall for new repo"
    ),
    default=None,
)
@click.option(
    "--reuse-old-install/--reinstall-old",
    help=(
        "reuse venv of existing clones of old repo instead of reinstalling it"
        "; overrides --reuse-installs/--reinstall for old repo"
    ),
    default=None,
)
@click.option(
    "--reuse-new-plots/--replot-new",
    help=(
        "reuse existing new plots rather than recomputing them"
        "; overrides --reuse-plots/--replot for new plots"
    ),
    default=None,
)
@click.option(
    "--reuse-old-plots/--replot-old",
    help=(
        "reuse existing old plots rather than recomputing them"
        "; overrides --reuse-plots/--replot for old plots"
    ),
    default=None,
)
@click.option(
    "--reuse-plots/--replot",
    help=(
        "reuse existing plots rather than recomputing them"
        "; overridden by --reuse-(old|new)-plots/--replot-(old|new)"
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
    "--work-dir",
    "work_dir_paths",
    help=(
        "working directory in which plots and diffs are saved in subdirectories"
        "; may be passed repeatedly, specifically once for every --preset"
        "/--presets-old-new in order to prevent plots based on the same prefix but"
        " different input files from overwriting each other"
    ),
    type=PathlibPath(),
    default=["pyflexplot-test/work"],
    multiple=True,
)
@click.pass_context
# pylint: disable=R0912  # too-many-branches (>12)
# pylint: disable=R0913  # too-many-arguments (>5)
# pylint: disable=R0914  # too-many-locals (>15)
# pylint: disable=R0915  # too-many-statements (>50)
def cli(
    ctx: Context,
    data_path: Path,
    infiles: Sequence[Path],
    infiles_old_new: Sequence[Tuple[Path, Path]],
    install_dir_path: Path,
    new_data_path: Optional[Path],
    new_rev: str,
    old_data_path: Optional[Path],
    presets_old_new: Sequence[Tuple[str, str]],
    old_rev: Optional[str],
    presets: Sequence[str],
    reuse_installs: bool,
    reuse_new_install: Optional[bool],
    reuse_old_install: Optional[bool],
    reuse_new_plots: Optional[bool],
    reuse_old_plots: Optional[bool],
    reuse_plots: bool,
    work_dir_paths: Sequence[Path],
    **cfg_kwargs,
) -> None:
    _name_ = "cli.cli"
    cfg = RunConfig(**cfg_kwargs)

    check_for_active_venv(ctx)

    if cfg.debug:
        print(f"DBG:{_name_}: prepare presets and infiles")
    old_presets, new_presets, old_infiles, new_infiles = prepare_presets_infiles(
        ctx, presets, presets_old_new, infiles, infiles_old_new
    )
    del presets, infiles
    assert len(old_presets) == len(new_presets) == len(old_infiles) == len(new_infiles)
    n_presets = len(old_presets)

    if cfg.debug:
        print(f"DBG:{_name_}: prepare data paths")
    old_data_path, new_data_path = prepare_data_paths(
        ctx,
        data_path,
        old_data_path,
        new_data_path,
        old_default_path=None if old_infiles else Path(DEFAULT_DATA_PATH),
        new_default_path=None if new_infiles else Path(DEFAULT_DATA_PATH),
    )
    del data_path

    reuse_cfg = ReuseConfig()

    if cfg.debug:
        print(f"DBG:{_name_}: prepare install reuse flags")
    reuse_cfg.old_install, reuse_cfg.new_install = prepare_reuse(
        reuse_installs, reuse_old_install, reuse_new_install
    )
    del reuse_installs

    if cfg.debug:
        print(f"DBG:{_name_}: prepare plot reuse flags")
    reuse_cfg.old_plots, reuse_cfg.new_plots = prepare_reuse(
        reuse_plots, reuse_old_plots, reuse_new_plots
    )
    del reuse_plots

    if cfg.debug:
        print(f"DBG:{_name_}: prepare old rev")
    if old_rev is None:
        if cfg.verbose:
            print(f"obtain old_rev from repo {cfg.repo_url}")
        tags = git_get_remote_tags(cfg.repo_url)
        if cfg.verbose:
            sel_tags = tags if len(tags) <= 7 else tags[:3] + ["..."] + tags[-3:]
            print(f"select most recent of {len(tags)} tags ({', '.join(sel_tags)})")
        old_rev = tags[-1]
        if cfg.verbose:
            print(f"old_rev: {old_rev}")

    if cfg.debug:
        print(f"DBG:{_name_}: prepare work dir paths")
    work_dir_paths = prepare_work_dir_paths(ctx, work_dir_paths, n_presets)

    if cfg.debug:
        print("+" * 40)
        print(f"DBG:{_name_}: Setup")
        print("-" * 40)
        print("{:20}: {}".format("old_data_path", old_data_path))
        print("{:20}: {}".format("new_data_path", new_data_path))
        print("{:20}: {}".format("old_infiles", list(map(str, old_infiles))))
        print("{:20}: {}".format("new_infiles", list(map(str, new_infiles))))
        print("{:20}: {}".format("old_presets", old_presets))
        print("{:20}: {}".format("new_presets", new_presets))
        print("{:20}: {}".format("old_rev", old_rev))
        print("{:20}: {}".format("new_rev", new_rev))
        #
        print("{:20}: {}".format("install_dir_path", install_dir_path))
        print("{:20}: {}".format("work_dir_paths", work_dir_paths))
        print("+" * 40)

    if cfg.debug:
        print(f"DBG:{_name_}: prepare install dir")
    install_dir_path = install_dir_path.absolute()
    install_dir_path.mkdir(parents=True, exist_ok=True)
    old_install_path = install_dir_path / old_rev
    new_install_path = install_dir_path / new_rev

    if cfg.debug:
        print(f"DBG:{_name_}: prepare install configs")
    old_install_cfg = InstallConfig(
        path=old_install_path,
        rev=old_rev,
        reuse=reuse_cfg.old_install,
    )
    new_install_cfg = InstallConfig(
        path=new_install_path,
        rev=new_rev,
        reuse=reuse_cfg.new_install,
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: prepare old executable")
    old_exe_path = prepare_exe("old", old_install_cfg, cfg)

    if cfg.debug:
        print(f"\nDBG:{_name_}: prepare new executable")
    new_exe_path = prepare_exe("new", new_install_cfg, cfg)

    grouped_by_work_dir = group_by_work_dir(
        old_presets, new_presets, old_infiles, new_infiles, work_dir_paths
    )
    for (
        work_dir_path,
        (
            old_presets_i,
            new_presets_i,
            old_infiles_i,
            new_infiles_i,
        ),
    ) in grouped_by_work_dir.items():
        run_in_work_dir(
            work_dir_path,
            old_presets_i,
            new_presets_i,
            old_infiles_i,
            new_infiles_i,
            old_data_path,
            new_data_path,
            old_exe_path,
            new_exe_path,
            old_install_cfg,
            new_install_cfg,
            reuse_cfg,
            cfg,
        )


# pylint: disable=R0912  # too-many-branches (>12)
# pylint: disable=R0913  # too-many-arguments
# pylint: disable=R0914  # too-many-locals (>15)
# pylint: disable=R0915  # too-many-statements (>50)
def run_in_work_dir(
    work_dir_path: Path,
    old_presets: Sequence[str],
    new_presets: Sequence[str],
    old_infiles: Sequence[Path],
    new_infiles: Sequence[Path],
    old_data_path: Optional[Path],
    new_data_path: Optional[Path],
    old_exe_path: Path,
    new_exe_path: Path,
    old_install_cfg: InstallConfig,
    new_install_cfg: InstallConfig,
    reuse_cfg: ReuseConfig,
    cfg: RunConfig,
) -> None:
    _name_ = "run_in_work_dir"
    if cfg.debug:
        print(f"DBG:{_name_}: prepare work dirs")
    old_work_path = work_dir_path / old_install_cfg.rev
    old_work_path.mkdir(parents=True, exist_ok=True)
    new_work_path = work_dir_path / new_install_cfg.rev
    new_work_path.mkdir(parents=True, exist_ok=True)
    diffs_path = work_dir_path / f"{old_install_cfg.rev}_vs_{new_install_cfg.rev}"
    diffs_path.mkdir(parents=True, exist_ok=True)

    if cfg.debug:
        print(f"DBG:{_name_}: prepare work dirs configs")
    old_work_dirs_cfg = WorkDirConfig(
        path=old_work_path,
        reuse=reuse_cfg.old_plots,
    )
    new_work_dirs_cfg = WorkDirConfig(
        path=new_work_path,
        reuse=reuse_cfg.new_plots,
    )
    # Note: This always replaces all diff plots, even if a rerun is made with
    # fewer presets than a previous runs, in which case the diff plots of the
    # left-out presets will be lost (but can easily be recomputed by rerunning
    # with all previous presets at once with --reuse-plots and --reuse-installs)
    diffs_work_dirs_cfg = WorkDirConfig(
        path=diffs_path,
        reuse=False,
        replace=True,
    )

    if cfg.debug:
        print(f"DBG:{_name_}: prepare plot configs")
    old_plot_cfg = PlotConfig(
        data_path=old_data_path,
        infiles=old_infiles,
        presets=old_presets,
        reuse=reuse_cfg.old_plots,
    )
    new_plot_cfg = PlotConfig(
        data_path=new_data_path,
        infiles=new_infiles,
        presets=new_presets,
        reuse=reuse_cfg.new_plots,
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: prepare work dirs")
    prepare_work_path(old_work_dirs_cfg, cfg)
    prepare_work_path(new_work_dirs_cfg, cfg)
    prepare_work_path(diffs_work_dirs_cfg, cfg)

    if cfg.debug:
        print(f"\nDBG:{_name_}: create old plots")
    print(f"prepare old plots in {old_exe_path}")
    old_plot_paths = create_plots(
        old_exe_path, old_work_dirs_cfg.path, old_plot_cfg, cfg
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: create new plots")
    print(f"prepare new plots in {new_exe_path}")
    new_plot_paths = create_plots(
        new_exe_path, new_work_dirs_cfg.path, new_plot_cfg, cfg
    )

    if cfg.debug:
        print(f"\nDBG:{_name_}: compare plots")
    plot_pairs = PlotPairSequence(
        paths1=old_plot_paths,
        paths2=new_plot_paths,
        base1=old_work_dirs_cfg.path,
        base2=new_work_dirs_cfg.path,
    )
    diff_plot_paths = plot_pairs.create_diffs(diffs_path, cfg, err_ok=True)
    n_plots = len(plot_pairs)
    n_diff = len(diff_plot_paths)
    frac = 0 if n_plots == 0 else n_diff / n_plots
    print()
    print(f"{n_diff}/{n_plots} ({frac:.0%}) plot pairs differ")
    if diff_plot_paths:
        if cfg.debug:
            print(f"DBG:{_name_}: create composite diff plot")
        composite_diff_plot = plot_pairs.create_composite_diff(diffs_path, cfg)
        animated_diff_plot = animate_diff_plots(diffs_path, diff_plot_paths, cfg)
        print()
        print(f"{n_diff} new diff plots in {diffs_path.relative_to(cfg.start_path)}/")
        if cfg.verbose:
            for path in diff_plot_paths:
                print(path.relative_to(cfg.start_path))
        print()
        print(f"diff composite: {composite_diff_plot.relative_to(cfg.start_path)}")
        print(f"diff animation: {animated_diff_plot.relative_to(cfg.start_path)}")
    print()


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


def prepare_exe(
    case: str,
    install_cfg: InstallConfig,
    cfg: RunConfig,
) -> Path:
    """Prepare clone of repo, install into virtual env and return exe path."""
    print(
        f"prepare {case} clone or {cfg.repo_url}@{install_cfg.rev} at"
        f" {install_cfg.path}"
    )
    prepare_clone(cfg.repo_url, install_cfg, cfg)
    if cfg.verbose:
        print(f"prepare {case} executable in {install_cfg.path}")
    exe_path = install_exe(install_cfg.path, install_cfg.reuse, cfg)
    return exe_path


def prepare_presets_infiles(
    ctx: Context,
    presets: Sequence[str],
    presets_old_new: Sequence[Tuple[str, str]],
    infiles: Sequence[Path],
    infiles_old_new: Sequence[Tuple[Path, Path]],
    absolute: bool = True,
) -> Tuple[List[str], List[str], List[Path], List[Path]]:
    """Prepare preset strings and infile paths for old and new revision."""
    old_presets: List[str] = []
    new_presets: List[str] = []
    if not presets and not presets_old_new:
        click.echo(
            "must pass --preset/--presets-old-new at least once", file=sys.stderr
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
    n_presets = len(old_presets)
    if not infiles and not infiles_old_new:
        old_infiles = []
        new_infiles = []
    elif infiles and not infiles_old_new:
        if len(infiles) in [1, n_presets] or n_presets == 1:
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
    n_infiles = len(old_infiles)
    if n_presets == 1 and n_infiles > 1:
        n_presets = n_infiles
        old_presets = [next(iter(old_presets)) for _ in range(n_infiles)]
        new_presets = [next(iter(new_presets)) for _ in range(n_infiles)]
    if absolute:
        old_infiles = [path.absolute() for path in old_infiles]
        new_infiles = [path.absolute() for path in new_infiles]
    return old_presets, new_presets, old_infiles, new_infiles


def prepare_reuse(
    reuse: bool, reuse_old: Optional[bool], reuse_new: Optional[bool]
) -> Tuple[bool, bool]:
    if reuse_old is None:
        reuse_old = reuse
    if reuse_new is None:
        reuse_new = reuse
    return reuse_old, reuse_new


# pylint: disable=R1710  # inconsistent-return-statements (ctx.exit)
def prepare_work_dir_paths(
    ctx: Context, work_dir_paths: Sequence[Path], n_presets: int
) -> List[Path]:
    if len(work_dir_paths) == 1:
        work_dir_paths = [next(iter(work_dir_paths))] * n_presets
    if len(work_dir_paths) == n_presets:
        return [Path(path).absolute() for path in work_dir_paths]
    else:
        click.echo(
            f"wrong number of --work-dir ({len(work_dir_paths)}); unless omitted, must"
            f" be passed once or as often as --preset/--presets-old-new ({n_presets})"
        )
        ctx.exit(1)


def group_by_work_dir(
    old_presets: Sequence[str],
    new_presets: Sequence[str],
    old_infiles: Sequence[Path],
    new_infiles: Sequence[Path],
    work_dir_paths: Sequence[Path],
) -> Dict[Path, Tuple[List[str], List[str], List[Path], List[Path]]]:
    n = len(work_dir_paths)
    if len(old_presets) != n:
        raise ValueError(f"old_preset has wrong size: {len(old_presets)} != {n}")
    if len(new_presets) != n:
        raise ValueError(f"new_preset has wrong size: {len(old_presets)} != {n}")
    if len(old_infiles) not in [0, n]:
        raise ValueError(
            f"old_infiles has wrong size: {len(old_infiles)} not in [1, {n}]"
        )
    if len(new_infiles) not in [0, n]:
        raise ValueError(
            f"new_infiles has wrong size: {len(new_infiles)} not in [1, {n}]"
        )
    grouped: Dict[Path, Tuple[List[str], List[str], List[Path], List[Path]]] = {
        path: ([], [], [], []) for path in work_dir_paths
    }
    # new_infile: Sequence[Optional[Path]]
    # new_infile: Sequence[Optional[Path]]
    old_infiles_zip: Sequence[Optional[Path]] = (
        [None] * n if not old_infiles else old_infiles
    )
    new_infiles_zip: Sequence[Optional[Path]] = (
        [None] * n if not new_infiles else new_infiles
    )
    for old_preset, new_preset, old_infile, new_infile, path in zip(
        old_presets, new_presets, old_infiles_zip, new_infiles_zip, work_dir_paths
    ):
        grouped[path][0].append(old_preset)
        grouped[path][1].append(new_preset)
        if old_infile:
            grouped[path][2].append(old_infile)
        if new_infile:
            grouped[path][3].append(new_infile)
    return grouped
