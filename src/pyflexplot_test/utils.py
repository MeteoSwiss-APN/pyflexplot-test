"""Some utilities."""
# Standard library
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator
from typing import List
from typing import Optional
from typing import overload
from typing import Sequence

# Third-party
from typing_extensions import Literal


# pylint: disable=W0102  # dangerous-default-value
def tmp_path(base: str, _time_stamp: List[int] = []) -> str:
    """Get a temporary path containing a time stamp."""
    if not _time_stamp:
        _time_stamp.append(int(time.time()))
    return f"{base}{_time_stamp[0]}"


@overload
def run_cmd(args: Sequence[str], real_time: Literal[False] = False) -> List[str]:
    ...


@overload
def run_cmd(args: Sequence[str], real_time: Literal[True]) -> Iterator[str]:
    ...


def run_cmd(args: Sequence[str], real_time: bool = False):
    """Run a command and yield the standard output line by line.

    By default, the standard output is collected and returned after the command
    has finished. Alternatively, the option ``real_time`` enables access to the
    standard by returning an iterator, which however must be iterated over,
    otherwise the subprocess is silently skipped.

    Args:
        args: Arguments passed to the subprocess.

        real_time (optional): Yield standard output line by line in real time
            instead of returning them together in the end.

    Returns:
        List of lines of standard output if ``real_time`` is false.

        Iterator over lines of standard output is ``real_time`` is true.

    """

    def raise_if_err(returncode: int, stderr: List[str]) -> None:
        if returncode:
            raise Exception(
                f"error ({returncode}) running command '{' '.join(args)}':\n"
                + "\n".join(stderr)
            )

    def _run_cmd_real_time(proc: subprocess.Popen) -> Iterator[str]:
        assert proc.stdout is not None  # mypy
        with proc.stdout:
            for raw_line in iter(proc.stdout.readline, b""):
                line = raw_line.decode("utf-8").strip()
                yield line
        proc.wait()
        assert proc.stderr is not None  # mypy
        stderr = [raw_line.decode("utf-8") for raw_line in proc.stderr]
        raise_if_err(proc.returncode, stderr)

    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if real_time:
        return _run_cmd_real_time(proc)
    raw_stdout, raw_stderr = proc.communicate()
    stdout = list(map(str.strip, raw_stdout.decode("utf-8").split("\n")))
    stderr = list(map(str.strip, raw_stderr.decode("utf-8").split("\n")))
    if stderr == [""]:
        stderr = []
    raise_if_err(int(bool(stderr)), stderr)
    return stdout


def git_get_remote_tags(repo: str) -> List[str]:
    """Get tags from remote git repository, sorted as version numbers."""
    cmd_args = ["git", "ls-remote", "--tags", "--sort=version:refname", repo]
    tags: List[str] = []
    for line in run_cmd(cmd_args, real_time=True):
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


# pylint: disable=R0913  # too-many-arguments (>5)
def check_paths_equiv(
    paths1: List[Path],
    paths2: List[Path],
    base1: Optional[Path] = None,
    base2: Optional[Path] = None,
    sort_rel: bool = False,
    action: str = "raise",
    del_missing: bool = False,
) -> None:
    """Check that to collections of paths are equivalent.

    Args:
        paths1: First collection of paths.

        paths2: Second collection of paths.

        base1 (optional): Base paths subtracted from ``paths1`` to obtain
            relative paths.

        base2 (optional): Base paths subtracted from ``paths2`` to obtain
            relative paths.

        sort_rel (optional): Sort the paths by their relative representation.
            If ``base1`` or ``base2`` is omitted, the respective paths are
            sorted as is.

        action (optional): Action to take when a path in one collection is
            missing in the other: "raise" an exception or only "warn" the user.

        del_missing (optional): Delete paths from the collection if they are
            missing in the other. Incompatible with ``action`` "raise".

    """
    actions = ["raise", "warn"]
    if action not in actions:
        raise ValueError(f"invalid action '{action}'; must be among {actions}")
    if del_missing and action == "raise":
        raise ValueError("del_missing=T is incompatible with action 'raise'")

    def subtract_base(paths: List[Path], base: Optional[Path]) -> List[Path]:
        if base is None:
            return list(paths)
        return [path.relative_to(base) for path in paths]

    # pylint: disable=R0913  # too-many-arguments (>5)
    def run(
        name1: str,
        paths1: List[Path],
        base1: Optional[Path],
        name2: str,
        paths2: List[Path],
        base2: Optional[Path],
    ) -> None:
        rel_paths1 = subtract_base(paths1, base1)
        rel_paths2 = subtract_base(paths2, base2)
        for path1, rel_path1 in zip(list(paths1), list(rel_paths1)):
            if rel_path1 in rel_paths2:
                continue
            msg = f"path from relative {name1} missing in relative {name2}: {rel_path1}"
            if action == "raise":
                raise AssertionError(msg)
            elif action == "warn":
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
