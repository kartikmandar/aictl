"""Init command for AICTL CLI."""

import click

from aictl.clients.database import init_db


@click.command()
def init():
    """Initialize AICTL database."""
    try:
        init_db()
        click.echo("AICTL initialized successfully")
    except Exception as e:
        raise click.ClickException(str(e))
