"""Some utilities."""
# Standard library
import subprocess
import time
from typing import Iterator
from typing import List
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
            raise RuntimeError(
                f"error ({returncode}) running command '{' '.join(args)}':\n"
                + "".join(stderr)
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
