import csv
import json
import os

import click
from rich.console import Console

err_console = Console(stderr=True)

CACHE_FILE = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "house-cli",
    "last_search.json",
)


@click.command("export")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--output", "output_path", default="houses.csv", help="Output file path")
def export_cmd(fmt, output_path):
    """Export last search results to CSV or JSON."""
    if not os.path.exists(CACHE_FILE):
        err_console.print("[red]No cached search results. Run 'house search' first.[/red]")
        raise SystemExit(1)

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        houses = json.load(f)

    if not houses:
        err_console.print("[yellow]Cached results are empty.[/yellow]")
        return

    if fmt == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(houses, f, ensure_ascii=False, indent=2)
    else:
        keys = houses[0].keys()
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(houses)

    err_console.print(f"[green]Exported {len(houses)} records to {output_path}[/green]")
