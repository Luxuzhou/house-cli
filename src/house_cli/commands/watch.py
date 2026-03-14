import asyncio
import json
import os

import click
from rich.console import Console
from rich.table import Table

from house_cli.client.adapters import ADAPTER_REGISTRY

err_console = Console(stderr=True)

WATCH_FILE = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "house-cli",
    "watchlist.json",
)


def _load_watchlist() -> list[dict]:
    if os.path.exists(WATCH_FILE):
        with open(WATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_watchlist(watchlist: list[dict]):
    os.makedirs(os.path.dirname(WATCH_FILE), exist_ok=True)
    with open(WATCH_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def _parse_house_id(house_id: str) -> tuple[str, str]:
    if ":" not in house_id:
        raise click.UsageError(
            f"Invalid house ID format: {house_id}. Expected platform:id."
        )
    platform, _, raw_id = house_id.partition(":")
    if platform not in ADAPTER_REGISTRY:
        raise click.UsageError(f"Unknown platform: {platform}")
    return platform, raw_id


@click.command()
@click.argument("house_id", default="")
@click.option("--remove", is_flag=True, help="Remove from watch list")
@click.option("--list", "list_all", is_flag=True, help="List all watched houses")
def watch(house_id, remove, list_all):
    """Watch a house for price changes."""
    if list_all:
        watchlist = _load_watchlist()
        if not watchlist:
            err_console.print("[yellow]Watch list is empty.[/yellow]")
            return
        table = Table(title="关注列表", show_lines=True)
        table.add_column("ID")
        table.add_column("标题")
        table.add_column("价格")
        table.add_column("添加时间")
        for item in watchlist:
            table.add_row(
                f"{item['platform']}:{item['house_id']}",
                item.get("title", ""),
                item.get("price", ""),
                item.get("added_at", ""),
            )
        err_console.print(table)
        return

    if not house_id:
        raise click.UsageError("Please provide a house ID or use --list.")

    platform, raw_id = _parse_house_id(house_id)
    watchlist = _load_watchlist()

    if remove:
        watchlist = [
            w for w in watchlist
            if not (w["platform"] == platform and w["house_id"] == raw_id)
        ]
        _save_watchlist(watchlist)
        err_console.print(f"[green]Removed {house_id} from watch list.[/green]")
        return

    # Add to watch list: fetch current detail for snapshot
    adapter = ADAPTER_REGISTRY[platform]()
    d = asyncio.run(adapter.detail(raw_id))

    from datetime import datetime
    entry = {
        "platform": platform,
        "house_id": raw_id,
        "title": d.title,
        "price": f"{d.price}{d.price_unit}",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Avoid duplicates
    if any(w["platform"] == platform and w["house_id"] == raw_id for w in watchlist):
        err_console.print(f"[yellow]{house_id} is already in watch list.[/yellow]")
        return

    watchlist.append(entry)
    _save_watchlist(watchlist)
    err_console.print(f"[green]Added {house_id} ({d.title}) to watch list.[/green]")
