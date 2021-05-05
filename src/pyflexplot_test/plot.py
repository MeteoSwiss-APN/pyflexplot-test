"""Create plots."""
# Standard library
import os
import re
import shutil
from pathlib import Path
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

# Local
from .config import PlotConfig
from .config import RunConfig
from .config import WorkDirConfig
from .utils import run_cmd


def prepare_work_path(wdir_cfg: WorkDirConfig, cfg: RunConfig) -> None:
    _name_ = "main.prepare_work_path"
    path = wdir_cfg.path
    if path.exists() and any(path.iterdir()):
        if wdir_cfg.reuse:
            if cfg.debug:
                print(f"DBG:{_name_}: reuse old work dir at {path}")
        else:
            if cfg.debug:
                print(f"DBG:{_name_}: remove old work dir at {path}")
            shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def create_plots(
    exe_path: Path, work_path: Path, plot_cfg: PlotConfig, cfg: RunConfig
) -> List[Path]:
    """Create plots for multiple presets with one call per preset."""
    plot_paths: List[Path] = []
    for preset, infile in zip_presets_infiles(plot_cfg):
        plot_paths.extend(
            create_plots_for_preset(exe_path, work_path, preset, infile, plot_cfg, cfg)
        )
    return plot_paths


# pylint: disable=R0912  # too-many-branches (>12)
# pylint: disable=R0913  # too-many-arguments (>5)
# pylint: disable=R0914  # too-many-locals (>15)
# pylint: disable=R0915  # too-many-statements (>50)
def create_plots_for_preset(
    exe_path: Path,
    work_path: Path,
    preset: str,
    infile: Optional[Path],
    plot_cfg: PlotConfig,
    cfg: RunConfig,
) -> List[Path]:
    """Create plots for an individual preset."""
    _name_ = "main.create_plots_for_preset"
    os.chdir(work_path)
    if plot_cfg.data_path:
        link_data_path(plot_cfg.data_path, cfg)

    cmd_args = [
        str(exe_path),
        "--no-show-version",
        f"--preset={preset}",
    ]
    if infile:
        if plot_cfg.data_path and not infile.is_absolute():
            infile = (plot_cfg.data_path / infile).resolve()
        cmd_args += ["--setup", "infile", str(infile)]
    if cfg.only:
        cmd_args += [f"--only={cfg.only}"]
    cmd_args_dry = cmd_args + ["--dry-run"]
    cmd_args += [f"--num-procs={cfg.num_procs}"]

    # Perform dry-run to obtain the plots that will be produced
    expected_plot_names = perform_dry_run(cmd_args_dry, cfg)
    expected_plot_paths = [work_path / name for name in expected_plot_names]
    n_plots = len(expected_plot_names)
    if n_plots == 0:
        raise Exception("zero expected plots detected during dry run")
    n_existing = sum(map(Path.exists, expected_plot_paths))
    if cfg.debug:
        print(
            f"DBG:{_name_}: found {n_existing}/{n_plots} expected plots in"
            f" {work_path}/"
        )

    if plot_cfg.reuse:
        if cfg.debug:
            print(f"DBG:{_name_}: check whether existing plots can be reused")
        if n_existing == n_plots:
            print(f"reuse the {n_existing}/{n_plots} expected plots in {work_path}/")
            return expected_plot_paths
        elif n_existing == 0:
            if cfg.debug:
                print(
                    f"DBG:{_name_}: compute plots because none of the {n_plots}"
                    f" expected plots already exist in {work_path}/"
                )
        else:
            print(
                f"recompute all plots because only {n_existing}/{n_plots} expected"
                f" plots already exist in {work_path}/"
            )
            for path in expected_plot_paths:
                if not path.exists():
                    if cfg.debug:
                        print(f"DBG:{_name_}: skip non-existing {path}")
                else:
                    if cfg.debug:
                        print(f"DBG:{_name_}: remove {path}")
                    path.unlink()

    # Perform actual run, using the number of plots to show progress
    print(f"create {n_plots} plots in {work_path}:")
    print(f"$ {' '.join(cmd_args)}")
    plot_paths: List[Path] = []
    i_plot = 0
    for i_line, line in enumerate(run_cmd(cmd_args, real_time=True)):
        if cfg.debug:
            print(f"DBG:{_name_}: line {i_line}: {line}")
        plot_name = parse_line_for_plot_name(line, cfg)
        if not plot_name:
            continue
        plot_path = work_path / plot_name
        plot_paths.append(plot_path)
        if plot_path not in expected_plot_paths:
            raise Exception(
                f"unexpected plot path: {plot_path}\nexpected:\n"
                + "\n  ".join(map(str, expected_plot_paths))
            )
        i_plot += 1
        if cfg.verbose:
            print(f"[{i_plot / n_plots:.0%}] {line}")
        else:
            print(f"\r[{i_plot / n_plots:.0%}] {i_plot}/{n_plots}", end="", flush=True)
    if not cfg.verbose:
        print()

    return plot_paths


def link_data_path(target_path: Path, cfg: RunConfig) -> None:
    _name_ = "main.link_data_path"
    if not target_path.exists():
        raise Exception(f"data path not found: {target_path}")
    link_path = Path("data")
    if link_path.exists():
        if not link_path.is_symlink():
            raise Exception(
                f"data link path {link_path.resolve()} exists and is not a symlink"
            )
        if cfg.debug:
            print(f"DBG:{_name_}: remove existing data link path {link_path}")
        link_path.unlink()
    if cfg.debug:
        print(f"DBG:{_name_}: symlinklink data path {link_path} to {target_path}")
    link_path.symlink_to(target_path)


def perform_dry_run(cmd_args_dry: List[str], cfg: RunConfig) -> List[str]:
    """Perform a dry-run to obtain the number of plots to be created."""
    _name_ = "main.perform_dry_run"
    if cfg.verbose:
        print(
            "perform dry run to determine expected plots:\n$ " + " ".join(cmd_args_dry)
        )
    plots: List[str] = []
    for line in run_cmd(cmd_args_dry, real_time=True):
        if cfg.debug:
            print(f"DBG:{_name_}: {line}")
        plot = parse_line_for_plot_name(line, cfg)
        if plot:
            if cfg.debug:
                print(f"DBG:{_name_}: plot detected: {plot}")
            plots.append(plot)
    if cfg.verbose:
        print(f"expecting {len(plots)} plots to be created")
    return plots


def parse_line_for_plot_name(line: str, cfg: RunConfig) -> Optional[str]:
    _name_ = "parse_line_for_plot_name"
    expr = r"^[^ ]+ -> (?P<path>[^ ]+)$"
    match = re.match(expr, line)
    if cfg.debug:
        print(
            f"DBG:{_name_}: '{expr}' {'' if match else 'not '} matched by line '{line}'"
        )
    return match.group("path") if match else None


def animate_diff_plots(
    diffs_path: Path,
    diff_plot_paths: Sequence[Path],
    cfg: RunConfig,
    *,
    delay: int = 80,
) -> Path:
    """Animate diff plots."""
    _name_ = "animate_diff_plots"
    if not diff_plot_paths:
        raise ValueError("missing diff plots to create composite diff plot")
    n_diffs = len(diff_plot_paths)
    anim_path = diffs_path / f"animated_diff_{n_diffs}x.gif"
    cmd_args = (
        [f"convert -delay {delay}"] + list(map(str, diff_plot_paths)) + [str(anim_path)]
    )
    if cfg.verbose:
        print(f"create animation of {n_diffs} diff plots: {anim_path}")
    if cfg.debug:
        print(
            f"DBG:{_name_}: create diff animation plot with following command:"
            + ("\n$ " + " \\\n    ".join(cmd_args))
        )
    cmd_args = [sub_arg for arg in cmd_args for sub_arg in arg.split()]
    try:
        run_cmd(cmd_args)
    # pylint: disable=W0703  # broad-except
    except Exception as e:
        raise Exception(f"error creating diff animation plot {anim_path}:\n{e}") from e
    return anim_path


def zip_presets_infiles(plot_cfg) -> Iterator[Tuple[str, Optional[Path]]]:
    infiles: Sequence[Optional[Path]]
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
