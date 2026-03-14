import click


@click.command("export")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--output", "output_path", default="houses.csv", help="Output file path")
def export_cmd(fmt, output_path):
    """Export last search results to CSV or JSON."""
    pass
