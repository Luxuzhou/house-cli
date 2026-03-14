import asyncio
import json
from dataclasses import asdict

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from house_cli.client.adapters import ADAPTER_REGISTRY

err_console = Console(stderr=True)


def _parse_house_id(house_id: str) -> tuple[str, str]:
    """Parse 'platform:id' format, return (platform, id)."""
    if ":" not in house_id:
        raise click.UsageError(
            f"Invalid house ID format: {house_id}. Expected platform:id (e.g. beike:abc123)."
        )
    platform, _, raw_id = house_id.partition(":")
    if platform not in ADAPTER_REGISTRY:
        raise click.UsageError(f"Unknown platform: {platform}")
    return platform, raw_id


def _render_detail(d):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("字段", style="bold")
    table.add_column("值")
    table.add_row("标题", d.title)
    table.add_row("平台", d.platform)
    table.add_row("价格", f"{d.price}{d.price_unit}")
    table.add_row("面积", f"{d.area:.1f}㎡")
    if d.unit_price:
        table.add_row("单价", f"{d.unit_price:.0f}元/㎡")
    table.add_row("户型", d.layout)
    table.add_row("楼层", d.floor)
    table.add_row("朝向", d.orientation)
    table.add_row("小区", d.community)
    table.add_row("区域", d.district)
    table.add_row("地址", d.address)
    if d.building_year:
        table.add_row("建筑年代", d.building_year)
    if d.building_type:
        table.add_row("建筑类型", d.building_type)
    if d.elevator:
        table.add_row("电梯", d.elevator)
    if d.nearby_subway:
        table.add_row("地铁", ", ".join(d.nearby_subway))
    if d.nearby_schools:
        table.add_row("学校", ", ".join(d.nearby_schools))
    if d.url:
        table.add_row("链接", d.url)
    err_console.print(Panel(table, title=f"房源详情 [{d.platform}:{d.id}]"))


@click.command()
@click.argument("house_id")
@click.option("--output", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def detail(house_id, output_format):
    """Show house detail. HOUSE_ID format: platform:id (e.g. beike:abc123)."""
    platform, raw_id = _parse_house_id(house_id)
    adapter = ADAPTER_REGISTRY[platform]()
    d = asyncio.run(adapter.detail(raw_id))

    if output_format == "json":
        click.echo(json.dumps(asdict(d), ensure_ascii=False, indent=2))
    elif output_format == "yaml":
        click.echo(yaml.dump(asdict(d), allow_unicode=True, default_flow_style=False))
    else:
        _render_detail(d)
