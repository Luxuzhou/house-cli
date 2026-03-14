import click


@click.command()
@click.argument("house_id")
@click.option("--aspects", default="all", help="Analysis aspects: price,commute,school,invest,all")
def analyze(house_id, aspects):
    """AI-powered analysis of a house listing."""
    pass
