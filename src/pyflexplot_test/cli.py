"""Command line interface."""
# Third-party
import click

# Local
from . import __version__


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "--version", "-V", message="%(version)s")
def cli() -> None:
    raise NotImplementedError("anything")
