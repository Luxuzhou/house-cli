import asyncio
import json
from dataclasses import asdict

import click
import yaml
from rich.console import Console
from rich.table import Table

from house_cli.client.adapters import ADAPTER_REGISTRY

err_console = Console(stderr=True)


def _parse_house_id(house_id: str) -> tuple[str, str]:
    if ":" not in house_id:
        raise click.UsageError(
            f"Invalid house ID format: {house_id}. Expected platform:id."
        )
    platform, _, raw_id = house_id.partition(":")
    if platform not in ADAPTER_REGISTRY:
        raise click.UsageError(f"Unknown platform: {platform}")
    return platform, raw_id


async def _fetch_both(p1, id1, p2, id2):
    a1 = ADAPTER_REGISTRY[p1]()
    a2 = ADAPTER_REGISTRY[p2]()
    d1, d2 = await asyncio.gather(a1.detail(id1), a2.detail(id2))
    return d1, d2


def _render_compare(d1, d2):
    table = Table(title="房源对比", show_lines=True)
    table.add_column("字段", style="bold")
    table.add_column(f"{d1.platform}:{d1.id}", max_width=30)
    table.add_column(f"{d2.platform}:{d2.id}", max_width=30)

    rows = [
        ("标题", d1.title, d2.title),
        ("价格", f"{d1.price}{d1.price_unit}", f"{d2.price}{d2.price_unit}"),
        ("面积", f"{d1.area:.1f}㎡", f"{d2.area:.1f}㎡"),
        ("单价", f"{d1.unit_price or '-'}元/㎡", f"{d2.unit_price or '-'}元/㎡"),
        ("户型", d1.layout, d2.layout),
        ("楼层", d1.floor, d2.floor),
        ("朝向", d1.orientation, d2.orientation),
        ("小区", d1.community, d2.community),
        ("区域", d1.district, d2.district),
        ("建筑年代", d1.building_year, d2.building_year),
        ("地铁", ", ".join(d1.nearby_subway) or "-", ", ".join(d2.nearby_subway) or "-"),
    ]
    for label, v1, v2 in rows:
        table.add_row(label, str(v1), str(v2))
    err_console.print(table)


@click.command()
@click.argument("id1")
@click.argument("id2")
@click.option("--output", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def compare(id1, id2, output_format):
    """Compare two houses side by side. ID format: platform:id."""
    p1, rid1 = _parse_house_id(id1)
    p2, rid2 = _parse_house_id(id2)

    d1, d2 = asyncio.run(_fetch_both(p1, rid1, p2, rid2))

    if output_format == "json":
        click.echo(json.dumps([asdict(d1), asdict(d2)], ensure_ascii=False, indent=2))
    elif output_format == "yaml":
        click.echo(yaml.dump([asdict(d1), asdict(d2)], allow_unicode=True, default_flow_style=False))
    else:
        _render_compare(d1, d2)
