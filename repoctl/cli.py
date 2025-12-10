# repoctl/cli.py
"""Main CLI entry point."""

import click

from repoctl.commands.adr import adr
from repoctl.commands.infra import infra


@click.group()
def cli() -> None:
    """Repoctl - Repository control CLI."""


cli.add_command(adr)
cli.add_command(infra)


if __name__ == "__main__":
    cli()
