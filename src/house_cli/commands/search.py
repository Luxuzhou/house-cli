import click


@click.command()
@click.option("--city", default="上海", help="City name")
@click.option("--district", default="", help="District name")
@click.option("--min-price", type=float, help="Minimum price")
@click.option("--max-price", type=float, help="Maximum price")
@click.option("--min-area", type=float, help="Minimum area (sqm)")
@click.option("--max-area", type=float, help="Maximum area (sqm)")
@click.option("--layout", default="", help="Layout filter, e.g. 2室")
@click.option("--type", "listing_type", type=click.Choice(["buy", "rent"]), default="buy")
@click.option("--platform", default="all", help="Platform: beike,anjuke,tongcheng,ziroom,fang,zhuge,all")
@click.option("--sort", "sort_by", default="default", help="Sort: default,price_asc,price_desc,area,date")
@click.option("--output", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def search(**kwargs):
    """Search houses across platforms."""
    pass
