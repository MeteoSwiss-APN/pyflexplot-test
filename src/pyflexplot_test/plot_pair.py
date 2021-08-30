"""Plot pairs."""
from __future__ import annotations

# Standard library
import filecmp
import os
import re
import sys
import traceback
from pathlib import Path
from subprocess import PIPE
from subprocess import Popen
from typing import Iterator
from typing import Optional
from typing import Sequence
from typing import Union

# Local
from .config import RunConfig
from .utils import run_cmd


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

    def create_diff(
        self,
        diffs_path: Optional[Union[Path, str]],
        cfg: RunConfig,
        raw: bool = False,
    ) -> Optional[Path]:
        _name_ = f"{__name__}.{type(self).__name__}.create_diff"
        if cfg.debug:
            print(f"DBG:{_name_}: comparing pair {self.shared_base}")
        if filecmp.cmp(self.path1, self.path2):
            if cfg.verbose:
                print(f"identical: {self.shared_base}")
            return None
        else:
            if cfg.verbose:
                print(f"differing: {self.shared_base}")
            diff_path = self.shared_base
            if diffs_path:
                diff_path = Path(diffs_path) / diff_path
            if raw:
                # Add '-raw' before suffix, e.g., a.png -> a-raw.png
                diff_path = diff_path.parent / Path(
                    re.sub(r"(.\w+$)", r"-raw\1", diff_path.name)
                )
            diff_path.parent.mkdir(parents=True, exist_ok=True)
            if self._equal_sized():
                self._compare_equal_sized(diff_path, cfg, raw)
            else:
                self._compare_unequal_sized(diff_path, cfg, raw)
            return diff_path

    def _compare_equal_sized(self, diff_path: Path, cfg: RunConfig, raw: bool) -> None:
        _name_ = f"{__name__}.{type(self).__name__}._compare_equal_sized"
        cmd_args = ["compare", str(self.path1), str(self.path2)]
        if raw:
            cmd_args += ["-compose src -highlight-color red"]
        cmd_args += [str(diff_path)]
        if cfg.debug:
            print(
                f"DBG:{_name_}: create diff plot with following command:\n$ "
                + " \\\n    ".join(cmd_args)
            )
        cmd_args = [sub_arg for arg in cmd_args for sub_arg in arg.split()]
        run_cmd(cmd_args)

    # pylint: disable=R0914  # too-many-locals (>15)
    def _compare_unequal_sized(
        self, diff_path: Path, cfg: RunConfig, raw: bool
    ) -> None:
        _name_ = f"{__name__}.{type(self).__name__}._compare_unequal_sized"
        w1 = int(self._identify(self.path1, fmt="%[w]", trim=True))
        w2 = int(self._identify(self.path2, fmt="%[w]", trim=True))
        h1 = int(self._identify(self.path1, fmt="%[h]", trim=True))
        h2 = int(self._identify(self.path2, fmt="%[h]", trim=True))
        width = max(w1, w2)
        height = max(h1, h2)
        size = f"{width}x{height}"
        if cfg.debug:
            print(f"DBG:{_name_}: original sizes: ({w1}x{h1}), ({w2}x{h2})")
            print(f"DBG:{_name_}: target size: ({size})")
        args_prep = (
            f"-trim -resize {size} -background white -gravity north-west -extent {size}"
            f" -bordercolor white -border 10"
        )
        args_path1 = f"( {args_prep} {str(self.path1)} )"
        args_path2 = f"( {args_prep} {str(self.path2)} )"
        cmd_prep = f"convert {args_path1} {args_path2} miff:-"
        cmd_comp = "compare miff:-"
        if raw:
            cmd_comp += " -compose src -highlight-color red"
        cmd_comp += f" {diff_path}"
        cmd = " | ".join([cmd_prep, cmd_comp])
        if cfg.debug:
            print(f"DBG:{_name_}: creating diff plot with following command:\n$ {cmd}")
        with Popen(
            cmd_comp.split(),
            stdin=Popen(cmd_prep.split(), stdout=PIPE).stdout,
            stdout=PIPE,
        ) as p:
            _, stderr = p.communicate()
        if stderr:
            raise RuntimeError(
                f"error running command '{cmd}':\n{stderr.decode('ascii')}"
            )

    def _equal_sized(self) -> bool:
        """Determine whether the images are of equal size."""
        size1 = self._identify(self.path1, fmt="%[w]x%[h]")
        size2 = self._identify(self.path2, fmt="%[w]x%[h]")
        return size1 == size2

    @staticmethod
    def _identify(path: Path, fmt: Optional[str] = None, trim: bool = False) -> str:
        """Run IM's identify for ``path``."""
        cmd_idfy = "identify"
        if fmt is not None:
            cmd_idfy += f" -format {fmt}"
        if not trim:
            cmd_idfy += f" {path}"
            with Popen(cmd_idfy.split(), stdout=PIPE) as p:
                stdout, _ = p.communicate()
                return stdout.decode("ascii")
        cmd_idfy += " miff:-"
        cmd_trim = f"convert -trim {path} miff:-"
        cmd = " | ".join([cmd_trim, cmd_idfy])
        with Popen(
            cmd_idfy.split(),
            stdin=Popen(cmd_trim.split(), stdout=PIPE).stdout,
            stdout=PIPE,
        ) as p:
            stdout, stderr = p.communicate()
            if stderr:
                raise RuntimeError(
                    f"error running command '{cmd}':\n{stderr.decode('ascii')}"
                )
            return stdout.decode("ascii")


class PlotPairSequence:
    """A sequence of ``PlotPair`` instances."""

    # pylint: disable=R0913  # too-many-arguments (>5)
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
        self.check_paths_equiv(
            paths1=paths1,
            paths2=paths2,
            base1=base1,
            base2=base2,
            err_action="warn",
            del_missing=True,
            sort_rel=sort,
        )
        self.pairs: list[PlotPair] = [
            PlotPair(path1=old_path, path2=new_path, base1=base1, base2=base2)
            for old_path, new_path in zip(paths1, paths2)
        ]

    def create_diffs(
        self,
        diffs_path: Path,
        cfg: RunConfig,
        *,
        err_ok: bool = False,
        raw: bool = False,
    ) -> list[Path]:
        """Create difference plots for those pairs that differ.

        Args:
            diffs_path: Path where diff plots are saved.

            cfg: Run configuration.

            err_ok (optional): Continue in case of an error instead of raising
                an exception.

            raw (optional): Only return raw diff mask.

        """
        if len(self) == 0:
            print("warning: no pairs of plots to create diff plots")
            return []
        print(f"compare {len(self)} pairs of plots")
        diff_paths: list[Path] = []
        for pair in self:
            try:
                diff_path = pair.create_diff(diffs_path, cfg, raw=raw)
            # pylint: disable=W0703  # broad-except
            except Exception as e:
                if not err_ok:
                    raise Exception(
                        f"error comparing {pair.rel_path1} and {pair.rel_path2}:\n{e}"
                    ) from e
                else:
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

    def create_composite_diff(self, diffs_path: Path, cfg: RunConfig) -> Path:
        """Create composite difference plot for those pairs that differ.

        Args:
            diffs_path: Path where diff plots are saved.

            cfg: Run configuration.

        """
        _name_ = f"{__name__}.{type(self).__name__}.create_composite_diff"
        diff_paths = self.create_diffs(diffs_path, cfg, err_ok=False, raw=True)
        if not diff_paths:
            raise Exception("missing diff plots to create composite diff plot")
        composite_path = diffs_path / f"composite_diff_{len(diff_paths)}x.png"
        cmd_args = (
            ["composite"]
            + list(map(str, diff_paths))
            + ["-compose src", str(composite_path)]
        )
        if cfg.verbose:
            print(f"create composite of {len(diff_paths)} diff plots: {composite_path}")
        if cfg.debug:
            print(
                f"DBG:{_name_}: create composite raw diff plot with following command:"
                + ("\n$ " + " \\\n    ".join(cmd_args))
            )
        cmd_args = [sub_arg for arg in cmd_args for sub_arg in arg.split()]
        try:
            run_cmd(cmd_args)
        # pylint: disable=W0703  # broad-except
        except Exception as e:
            raise Exception(
                f"error creating composite diff plot {composite_path}:\n{e}"
            ) from e
        if cfg.verbose:
            print(f"remove {len(diff_paths)} raw diff plots")
        for path in diff_paths:
            if cfg.debug:
                print(f"DBG:{_name_}: remove {path}")
            path.unlink()
        return composite_path

    def __iter__(self) -> Iterator[PlotPair]:
        return iter(self.pairs)

    def __len__(self) -> int:
        return len(self.pairs)

    # pylint: disable=R0913  # too-many-arguments (>5)
    @staticmethod
    def check_paths_equiv(
        paths1: list[Path],
        paths2: list[Path],
        base1: Optional[Path] = None,
        base2: Optional[Path] = None,
        *,
        err_action: str = "raise",
        del_missing: bool = False,
        sort_rel: bool = False,
    ) -> None:
        """Check that to collections of paths are equivalent.

        Args:
            paths1: First collection of paths.

            paths2: Second collection of paths.

            base1 (optional): Base paths subtracted from ``paths1`` to obtain
                relative paths.

            base2 (optional): Base paths subtracted from ``paths2`` to obtain
                relative paths.

            err_action (optional): Action to take when a path in one collection
                is missing in the other; "raise" an exception or only "warn" the
                user.

            del_missing (optional): Delete paths from the collection if they are
                missing in the other; incompatible with ``action`` "raise".

            sort_rel (optional): Sort the paths by their relative
                representation; if ``base1`` or ``base2`` is omitted, the
                respective paths are sorted as is.

        """
        actions = ["raise", "warn"]
        if err_action not in actions:
            raise ValueError(f"invalid action '{err_action}'; must be among {actions}")
        if del_missing and err_action == "raise":
            raise ValueError("del_missing=T is incompatible with action 'raise'")

        def subtract_base(paths: list[Path], base: Optional[Path]) -> list[Path]:
            if base is None:
                return list(paths)
            return [path.relative_to(base) for path in paths]

        # pylint: disable=R0913  # too-many-arguments (>5)
        def run(
            name1: str,
            paths1: list[Path],
            base1: Optional[Path],
            name2: str,
            paths2: list[Path],
            base2: Optional[Path],
        ) -> None:
            rel_paths1 = subtract_base(paths1, base1)
            rel_paths2 = subtract_base(paths2, base2)
            for path1, rel_path1 in zip(list(paths1), list(rel_paths1)):
                if rel_path1 in rel_paths2:
                    continue
                msg = (
                    f"path from relative paths '{name1}' missing in relative paths"
                    f" '{name2}': {rel_path1}"
                )
                if err_action == "raise":
                    raise AssertionError(msg)
                elif err_action == "warn":
                    print(f"warning: {msg}", file=sys.stderr)
                if del_missing:
                    paths1.remove(path1)
                    rel_paths1.remove(rel_path1)
            if sort_rel:
                paths1_sorted_by_rel = sorted(
                    [(rel_path1, path1) for path1, rel_path1 in zip(paths1, rel_paths1)]
                )
                paths1.clear()
                for _, path1 in paths1_sorted_by_rel:
                    paths1.append(path1)

        run("paths2", paths2, base2, "paths1", paths1, base1)
        run("paths1", paths1, base1, "paths2", paths2, base2)
