"""Main module."""
# Standard library
import filecmp
import os
import re
import shutil
import sys
import traceback
from pathlib import Path
from subprocess import PIPE
from subprocess import Popen
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

# Third-party
from git import Repo
from git.exc import InvalidGitRepositoryError

# Local
from .config import CloneConfig
from .config import PlotConfig
from .config import RunConfig
from .config import WorkDirConfig
from .utils import check_paths_equiv
from .utils import run_cmd


def prepare_clone(repo: str, clone_cfg: CloneConfig, cfg: RunConfig) -> Repo:
    """Prepare a local clone of a remote git repository."""
    _name_ = "main.prepare_clone"
    clone_path = clone_cfg.path
    if cfg.debug:
        print(f"DBG:{_name_}: prepare clone at {clone_path}")
    clone: Optional[Repo] = None
    if clone_path.exists():
        clone = handle_existing_clone(repo, clone_cfg, cfg)
        if clone_cfg.reuse and clone is not None:
            if cfg.debug:
                print(f"DBG:{_name_}: reuse existing clone at {clone_path}")
            return clone
    if clone is None:
        if cfg.debug:
            print(f"DBG:{_name_}: clone fresh repo {repo} to {clone_path}")
        clone_path.mkdir(parents=True, exist_ok=True)
        clone = Repo.clone_from(repo, clone_path)
    assert clone is not None  # mypy
    if cfg.debug:
        print(f"DBG:{_name_}: check out rev: {clone_cfg.rev}")
    clone.git.fetch(all=True)
    clone.git.checkout(clone_cfg.rev)
    if not clone.head.is_detached:
        clone.git.pull()
    return clone


def handle_existing_clone(
    repo: str, clone_cfg: CloneConfig, cfg: RunConfig
) -> Optional[Repo]:
    """Check if existing clone can be reused, and if not, remove it."""
    _name_ = "main.handle_existing_clone"
    try:
        clone = Repo(clone_cfg.path)
    except InvalidGitRepositoryError:
        if cfg.debug:
            print(
                f"DBG:{_name_}: existing directory at clone path {clone_cfg.path} is"
                " not a git repo"
            )
    else:
        # Check whether the repo is our target repo based on the origin url
        # Note that this check will fail if, e.g., one link is ssh and the
        # other https although the repo is the same
        if clone.remote().url != repo:
            if cfg.debug:
                print(
                    f"DBG:{_name_}: cannot reuse existing clone at {clone_cfg.path}"
                    f" because remote URL doesn't match: {clone.remote().url} != {repo}"
                )
        elif clone.is_dirty():
            if cfg.debug:
                print(
                    f"DBG:{_name_}: cannot reuse existing clone at {clone_cfg.path}"
                    " because it's dirty"
                )
        elif clone_cfg.reuse:
            if cfg.debug:
                print(f"DBG:{_name_}: reuse existing clone at {clone_cfg.path}")
            return clone
        else:
            if cfg.debug:
                print(
                    f"DBG:{_name_}: could reuse existing clone at {clone_cfg.path}, but"
                    " won't because --reuse-installs (or equivalent) has not been"
                    " passed"
                )
    is_file_or_not_empty = not clone_cfg.path.is_dir() or any(clone_cfg.path.iterdir())
    if is_file_or_not_empty:
        if cfg.debug:
            print(f"DBG:{_name_}: remove existing clone at {clone_cfg.path}")
        shutil.rmtree(clone_cfg.path)
    return None


def install_exe(
    clone_path: Path, reuse: bool, cfg: RunConfig, exe: str = "pyflexplot"
) -> Path:
    """Install pyflexplot into a virtual env and return the executable path."""
    os.chdir(clone_path)
    if not Path("Makefile").exists():
        raise Exception(f"missing Makefile in {os.path.abspath(os.curdir)}")
    venv_path = "venv"
    bin_path = Path(venv_path).absolute() / "bin"
    exe_path = bin_path / exe
    if reuse and exe_path.exists():
        print(f"reuse existing executable {exe_path}")
        return exe_path
    cmd_args = ["make", "install", "CHAIN=1", f"VENV_DIR={venv_path}"]
    for line in run_cmd(cmd_args, real_time=True):
        if cfg.verbose:
            print(line)
    if not (bin_path / "python").exists():
        raise Exception(f"installation of {exe} failed: no bin directory {bin_path}")
    return exe_path


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
        cmd_args += ["--setup", "infile", str(infile)]
    if plot_cfg.only:
        cmd_args += [f"--only={plot_cfg.only}"]
    cmd_args_dry = cmd_args + ["--dry-run"]
    cmd_args += [f"--num-procs={plot_cfg.num_procs}"]

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
                f"data link path {link_path.absolute()} exists and is not a symlink"
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


class PlotPair:
    def __init__(
        self,
        path1: Union[Path, str],
        path2: Union[Path, str],
        base1: Optional[Union[Path, str]] = None,
        base2: Optional[Union[Path, str]] = None,
    ) -> None:
        """Create an instance of ``PlotPair``.

        The two plots must have the same file name but are located in different
        directories, which are part of the paths but may also be specified
        explicitly (or have to; now sure; needs cleanup).

        Args:
            path1: Path to first plot; file name must be the same as ``path2``.

            path2: Path to second plot; file name must be the same as ``path1``.

            base1 (optional): Base directory of ``path1``; equal to the basename
                of ``path1`` plus all preceding subdirectories shared with
                ``path2``; e.g., the bases for two paths 'foo/hello/world.png`
                and 'bar/hello/world.png` would be 'foo` and 'bar`, given the
                shared base compolent 'hello/world.png`.

            base2 (optional): Like ``base1`` but for ``path2``.

        """
        self.path1: Path = Path(path1)
        self.path2: Path = Path(path2)
        self.base1: Path = Path(base1 or self.path1.root)
        self.base2: Path = Path(base2 or self.path2.root)
        shared_base1 = self.path1.relative_to(self.base1)
        shared_base2 = self.path2.relative_to(self.base2)
        if shared_base1 != shared_base2:
            raise ValueError(
                "inconsistent paths and bases; shared path components differ:"
                f" {shared_base1} != {shared_base2}"
            )
        self.shared_base: Path = shared_base1
        self.shared_root: Path = Path(os.path.commonpath([self.base1, self.base2]))

    @property
    def rel_path1(self) -> Path:
        return self.path1.relative_to(self.shared_root)

    @property
    def rel_path2(self) -> Path:
        return self.path2.relative_to(self.shared_root)

    def compare(
        self,
        diffs_path: Optional[Union[Path, str]] = None,
        cfg: RunConfig = RunConfig(),
    ) -> Optional[Path]:
        if cfg.verbose:
            print(f"comparing pair {self.shared_base}")
        if filecmp.cmp(self.path1, self.path2):
            print(f"identical: {self.shared_base}")
            return None
        print(f"differing: {self.shared_base}")
        diff_path = self.shared_base
        if diffs_path:
            diff_path = Path(diffs_path) / diff_path
        if self._equal_sized():
            self._compare_equal_sized(diff_path, cfg)
        else:
            self._compare_unequal_sized(diff_path, cfg)
        return diff_path

    def _compare_equal_sized(self, diff_path: Path, cfg: RunConfig) -> None:
        cmd_args = ["compare", str(self.path1), str(self.path2), str(diff_path)]
        if cfg.verbose:
            print("creating diff plot:\n$ " + " \\\n    ".join(cmd_args))
        run_cmd(cmd_args)

    def _compare_unequal_sized(self, diff_path: Path, cfg: RunConfig) -> None:
        width = max(
            int(self._identify(self.path1, format="%[w]", trim=True)),
            int(self._identify(self.path2, format="%[w]", trim=True)),
        )
        height = max(
            int(self._identify(self.path1, format="%[h]", trim=True)),
            int(self._identify(self.path2, format="%[h]", trim=True)),
        )
        size = f"{width}x{height}"
        args_prep = (
            f"-trim -resize {size} -background white -gravity north-west -extent {size}"
            f" -bordercolor white -border 10"
        )
        args_path1 = f"( {args_prep} {str(self.path1)} )"
        args_path2 = f"( {args_prep} {str(self.path2)} )"
        cmd_prep = f"convert {args_path1} {args_path2} miff:-"
        cmd_comp = f"compare miff:- {diff_path}"
        cmd = " | ".join([cmd_prep, cmd_comp])
        print(f"creating diff plot:\n$ {cmd}")
        _, stderr = Popen(
            cmd_comp.split(),
            stdin=Popen(cmd_prep.split(), stdout=PIPE).stdout,
            stdout=PIPE,
        ).communicate()
        if stderr:
            raise RuntimeError(
                f"error running command '{cmd}':\n{stderr.decode('ascii')}"
            )

    def _equal_sized(self) -> bool:
        """Determine whether the images are of equal size."""
        size1 = self._identify(self.path1, format="%[w]x%[h]")
        size2 = self._identify(self.path2, format="%[w]x%[h]")
        return size1 == size2

    @staticmethod
    def _identify(path: Path, format: Optional[str] = None, trim: bool = False) -> str:
        """Run IM's identify for ``path``."""
        cmd_idfy = "identify"
        if format is not None:
            cmd_idfy += f" -format {format}"
        if not trim:
            cmd_idfy += f" {path}"
            stdout, _ = Popen(cmd_idfy.split(), stdout=PIPE).communicate()
        else:
            cmd_idfy += " miff:-"
            cmd_trim = f"convert -trim {path} miff:-"
            cmd = " | ".join([cmd_trim, cmd_idfy])
            stdout, stderr = Popen(
                cmd_idfy.split(),
                stdin=Popen(cmd_trim.split(), stdout=PIPE).stdout,
                stdout=PIPE,
            ).communicate()
            if stderr:
                raise RuntimeError(
                    f"error running command '{cmd}':\n{stderr.decode('ascii')}"
                )
        return stdout.decode("ascii")


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
        if len(self) == 0:
            print("error: no pairs of plots to compute")
            return []
        print(f"comparing {len(self)} pairs of plots:")
        diff_paths: List[Path] = []
        for pair in self:
            try:
                diff_path = pair.compare(diffs_path, cfg)
            except Exception:
                print("-" * 50, file=sys.stderr)
                traceback.print_exc()
                print("-" * 50, file=sys.stderr)
                print(
                    "error during diff creation (see traceback above);"
                    f" abort comparison of {pair.rel_path1} and {pair.rel_path2}",
                    file=sys.stderr,
                )
            if diff_path is not None:
                diff_paths.append(diff_path)
        return diff_paths

    def __iter__(self) -> Iterator[PlotPair]:
        return iter(self.pairs)

    def __len__(self) -> int:
        return len(self.pairs)
