"""Some utilities."""
# Standard library
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence


# pylint: disable=W0102  # dangerous-default-value
def tmp_path(base: str, _time_stamp: List[int] = []) -> str:
    """Get a temporary path containing a time stamp."""
    if not _time_stamp:
        _time_stamp.append(int(time.time()))
    return f"{base}{_time_stamp[0]}"


def run_cmd(args: Sequence[str]) -> Iterator[str]:
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


def check_paths_equiv(
    paths1: List[Path],
    paths2: List[Path],
    base1: Optional[Path] = None,
    base2: Optional[Path] = None,
    action: str = "raise",
    del_missing: bool = False,
) -> None:
    """Check that to collections of paths are equivalent.

    Args:
        paths1: First collection of paths.

        paths2: Second collection of paths.

        base1 (optional): Base paths subtracted from ``paths1``.

        base2 (optional): Base paths subtracted from ``paths2``.

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

    def check_paths(
        name1: str,
        paths1: List[Path],
        base1: Optional[Path],
        name2: str,
        paths2: List[Path],
        base2: Optional[Path],
    ) -> None:
        if base2 is None:
            rel_paths2 = list(paths2)
        else:
            rel_paths2 = [path2.relative_to(base2) for path2 in paths2]
        for path1 in list(paths1):
            rel_path1 = path1 if base1 is None else path1.relative_to(base1)
            if rel_path1 in rel_paths2:
                continue
            msg = f"path from relative {name1} missing in relative {name2}: {rel_path1}"
            if action == "raise":
                raise AssertionError(msg)
            elif action == "warn":
                print(f"warning: {msg}", file=sys.stderr)
            if del_missing:
                paths1.remove(path1)

    check_paths("paths2", paths2, base2, "paths1", paths1, base1)
    check_paths("paths1", paths1, base1, "paths2", paths2, base2)
