import click


@click.command()
@click.argument("house_id")
@click.option("--remove", is_flag=True, help="Remove from watch list")
@click.option("--list", "list_all", is_flag=True, help="List all watched houses")
def watch(house_id, remove, list_all):
    """Watch a house for price changes."""
    pass
