import click


@click.command()
@click.argument("id1")
@click.argument("id2")
@click.option("--output", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def compare(id1, id2, output_format):
    """Compare two houses side by side. ID format: platform:id."""
    pass
