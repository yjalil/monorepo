# repoctl/cli.py
"""Main CLI entry point."""

import click

from repoctl.commands.add.main import add_group


@click.group()
def cli() -> None:
    """Repoctl - Repository control CLI."""


cli.add_command(add_group)


if __name__ == "__main__":
    cli()
