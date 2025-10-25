"""Main CLI entry point for AICTL."""

import click

from aictl.cli.commands.launch import launch
from aictl.cli.commands.init import init
from aictl.cli.commands.install import install
from aictl.cli.commands.shutdown import shutdown
from aictl.cli.commands.flow import flow


@click.group()
def cli():
    """AI Control Tool."""


# Register commands
cli.add_command(launch)
cli.add_command(init)
cli.add_command(install)
cli.add_command(shutdown)
cli.add_command(flow)


if __name__ == "__main__":
    cli()
