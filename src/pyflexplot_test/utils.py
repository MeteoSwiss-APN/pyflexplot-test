"""Some utilities."""
# Standard library
import subprocess
import time
from typing import Iterator
from typing import List
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
