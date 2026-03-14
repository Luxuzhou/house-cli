import asyncio
import json
from dataclasses import asdict

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

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


def _generate_analysis(d, aspects: list[str]) -> str:
    """Generate a basic analysis report from house detail data."""
    sections = []

    if "price" in aspects or "all" in aspects:
        unit_price_str = f"{d.unit_price:.0f}元/㎡" if d.unit_price else "未知"
        sections.append(
            f"## 价格分析\n"
            f"- 总价: {d.price}{d.price_unit}\n"
            f"- 单价: {unit_price_str}\n"
            f"- 面积: {d.area:.1f}㎡\n"
        )

    if "commute" in aspects or "all" in aspects:
        subway = ", ".join(d.nearby_subway) if d.nearby_subway else "无数据"
        sections.append(
            f"## 通勤分析\n"
            f"- 地铁: {subway}\n"
            f"- 地址: {d.address or d.district}\n"
        )

    if "school" in aspects or "all" in aspects:
        schools = ", ".join(d.nearby_schools) if d.nearby_schools else "无数据"
        sections.append(f"## 教育资源\n- 周边学校: {schools}\n")

    if "invest" in aspects or "all" in aspects:
        sections.append(
            f"## 投资参考\n"
            f"- 建筑年代: {d.building_year or '未知'}\n"
            f"- 小区: {d.community}\n"
            f"- 区域: {d.district}\n"
        )

    return "\n".join(sections) if sections else "无分析数据"


@click.command()
@click.argument("house_id")
@click.option("--aspects", default="all", help="Analysis aspects: price,commute,school,invest,all")
def analyze(house_id, aspects):
    """AI-powered analysis of a house listing."""
    platform, raw_id = _parse_house_id(house_id)
    adapter = ADAPTER_REGISTRY[platform]()
    d = asyncio.run(adapter.detail(raw_id))

    aspect_list = [a.strip() for a in aspects.split(",")]
    report = _generate_analysis(d, aspect_list)
    err_console.print(Panel(Markdown(report), title=f"房源分析 [{platform}:{raw_id}]"))
