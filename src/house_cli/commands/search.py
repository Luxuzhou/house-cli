import asyncio
import json
from dataclasses import asdict

import click
import yaml
from rich.console import Console
from rich.table import Table

from house_cli.client.adapters import get_adapters
from house_cli.models.filter import SearchFilter

err_console = Console(stderr=True)


async def _search_all(adapters, filters: SearchFilter):
    """Run search on all adapters concurrently, collect results."""
    results = []
    tasks = [adapter.search(filters) for adapter in adapters]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    for adapter, outcome in zip(adapters, outcomes):
        if isinstance(outcome, Exception):
            err_console.print(
                f"[yellow]⚠ {adapter.platform_name}: {outcome}[/yellow]"
            )
        else:
            results.extend(outcome)
    return results


def _sort_results(houses, sort_by: str):
    if sort_by == "price_asc":
        return sorted(houses, key=lambda h: h.price)
    elif sort_by == "price_desc":
        return sorted(houses, key=lambda h: h.price, reverse=True)
    elif sort_by == "area":
        return sorted(houses, key=lambda h: h.area, reverse=True)
    elif sort_by == "date":
        return sorted(houses, key=lambda h: h.listing_date, reverse=True)
    return houses


def _render_table(houses):
    table = Table(title="搜索结果", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("平台", width=6)
    table.add_column("标题", max_width=30)
    table.add_column("价格", justify="right")
    table.add_column("面积(㎡)", justify="right")
    table.add_column("户型")
    table.add_column("小区")
    table.add_column("区域")
    for i, h in enumerate(houses, 1):
        table.add_row(
            str(i),
            h.platform,
            h.title,
            f"{h.price}{h.price_unit}",
            f"{h.area:.1f}",
            h.layout,
            h.community,
            h.district,
        )
    err_console.print(table)


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
def search(city, district, min_price, max_price, min_area, max_area,
           layout, listing_type, platform, sort_by, output_format):
    """Search houses across platforms."""
    filters = SearchFilter(
        city=city,
        district=district,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        layout=layout,
        listing_type=listing_type,
        sort_by=sort_by,
    )

    adapters = get_adapters(platform, listing_type)
    if not adapters:
        err_console.print("[red]No adapters available for the selected platform/type.[/red]")
        raise SystemExit(1)

    houses = asyncio.run(_search_all(adapters, filters))

    # Client-side district filter: some platforms don't support server-side district filtering
    if district:
        houses = [h for h in houses if not h.district or district in h.district]

    houses = _sort_results(houses, sort_by)

    if not houses:
        err_console.print("[yellow]No results found.[/yellow]")
        return

    if output_format == "json":
        click.echo(json.dumps([asdict(h) for h in houses], ensure_ascii=False, indent=2))
    elif output_format == "yaml":
        click.echo(yaml.dump([asdict(h) for h in houses], allow_unicode=True, default_flow_style=False))
    else:
        _render_table(houses)
