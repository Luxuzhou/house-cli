import click

from house_cli.commands.search import search
from house_cli.commands.detail import detail
from house_cli.commands.compare import compare
from house_cli.commands.analyze import analyze
from house_cli.commands.mortgage import mortgage
from house_cli.commands.watch import watch
from house_cli.commands.export import export_cmd


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """House CLI - Search houses across multiple platforms."""
    pass


cli.add_command(search)
cli.add_command(detail)
cli.add_command(compare)
cli.add_command(analyze)
cli.add_command(mortgage)
cli.add_command(watch)
cli.add_command(export_cmd, name="export")


if __name__ == "__main__":
    cli()
