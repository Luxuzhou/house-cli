import click


@click.command()
@click.argument("house_id")
@click.option("--output", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def detail(house_id, output_format):
    """Show house detail. HOUSE_ID format: platform:id (e.g. beike:abc123)."""
    pass
