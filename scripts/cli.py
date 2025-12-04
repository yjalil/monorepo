# /// script
# requires-python = ">=3.12"
# dependencies = ["click"]
# ///

import click
from scripts.commands import sanity

@click.group()
def cli():
    pass

cli.add_command(sanity.sanity)
