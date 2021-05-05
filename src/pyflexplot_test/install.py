"""Main module."""
# Standard library
import os
import shutil
from pathlib import Path
from typing import Optional

# Third-party
from git import Repo
from git.exc import InvalidGitRepositoryError

# Local
from .config import InstallConfig
from .config import RunConfig
from .utils import run_cmd


def prepare_clone(repo: str, install_cfg: InstallConfig, cfg: RunConfig) -> Repo:
    """Prepare a local clone of a remote git repository."""
    _name_ = "main.prepare_clone"
    clone_path = install_cfg.path
    if cfg.debug:
        print(f"DBG:{_name_}: prepare clone at {clone_path}")
    clone: Optional[Repo] = None
    if clone_path.exists():
        clone = handle_existing_clone(repo, install_cfg, cfg)
        if install_cfg.reuse and clone is not None:
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
        print(f"DBG:{_name_}: check out rev: {install_cfg.rev}")
    clone.git.fetch(all=True)
    clone.git.checkout(install_cfg.rev)
    if not clone.head.is_detached:
        clone.git.pull()
    return clone


def handle_existing_clone(
    repo: str, install_cfg: InstallConfig, cfg: RunConfig
) -> Optional[Repo]:
    """Check if existing clone can be reused, and if not, remove it."""
    _name_ = "main.handle_existing_clone"
    try:
        clone = Repo(install_cfg.path)
    except InvalidGitRepositoryError:
        if cfg.debug:
            print(
                f"DBG:{_name_}: existing directory at clone path {install_cfg.path} is"
                " not a git repo"
            )
    else:
        # Check whether the repo is our target repo based on the origin url
        # Note that this check will fail if, e.g., one link is ssh and the
        # other https although the repo is the same
        if clone.remote().url != repo:
            if cfg.debug:
                print(
                    f"DBG:{_name_}: cannot reuse existing clone at {install_cfg.path}"
                    f" because remote URL doesn't match: {clone.remote().url} != {repo}"
                )
        elif clone.is_dirty():
            if cfg.debug:
                print(
                    f"DBG:{_name_}: cannot reuse existing clone at {install_cfg.path}"
                    " because it's dirty"
                )
        elif install_cfg.reuse:
            if cfg.debug:
                print(f"DBG:{_name_}: reuse existing clone at {install_cfg.path}")
            return clone
        else:
            if cfg.debug:
                print(
                    f"DBG:{_name_}: could reuse existing clone at {install_cfg.path},"
                    " but won't because --reuse-installs (or equivalent) has not been"
                    " passed"
                )
    is_file_or_not_empty = not install_cfg.path.is_dir() or any(
        install_cfg.path.iterdir()
    )
    if is_file_or_not_empty:
        if cfg.debug:
            print(f"DBG:{_name_}: remove existing clone at {install_cfg.path}")
        shutil.rmtree(install_cfg.path)
    return None


def install_exe(
    clone_path: Path, reuse: bool, cfg: RunConfig, exe: str = "pyflexplot"
) -> Path:
    """Install pyflexplot into a virtual env and return the executable path."""
    os.chdir(clone_path)
    if not Path("Makefile").exists():
        raise Exception(f"missing Makefile in {os.path.abspath(os.curdir)}")
    venv_path = "venv"
    bin_path = Path(venv_path).resolve() / "bin"
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
