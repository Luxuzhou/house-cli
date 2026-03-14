from house_cli.client.adapters.beike import BeikeClient
from house_cli.client.adapters.ziroom import ZiroomClient
from house_cli.client.adapters.anjuke import AnjukeClient
from house_cli.client.adapters.tongcheng import TongchengClient
from house_cli.client.adapters.fang import FangClient
from house_cli.client.adapters.zhuge import ZhugeClient

ADAPTER_REGISTRY: dict[str, type] = {
    "beike": BeikeClient,
    "anjuke": AnjukeClient,
    "tongcheng": TongchengClient,
    "ziroom": ZiroomClient,
    "fang": FangClient,
    "zhuge": ZhugeClient,
}

# Platforms that support buy listings
BUY_PLATFORMS = ["beike", "anjuke", "tongcheng", "fang", "zhuge"]
# Platforms that support rent listings
RENT_PLATFORMS = ["beike", "anjuke", "tongcheng", "ziroom", "fang", "zhuge"]

ALL_PLATFORMS = list(ADAPTER_REGISTRY.keys())


def get_adapters(platform: str, listing_type: str = "buy") -> list:
    """Return adapter instances for the given platform selector and listing type.

    Args:
        platform: "all" or comma-separated platform names (e.g. "beike,anjuke").
        listing_type: "buy" or "rent".

    Returns:
        List of adapter instances.
    """
    if platform == "all":
        names = RENT_PLATFORMS if listing_type == "rent" else BUY_PLATFORMS
    else:
        names = [p.strip() for p in platform.split(",")]

    adapters = []
    for name in names:
        cls = ADAPTER_REGISTRY.get(name)
        if cls is None:
            raise click.UsageError(f"Unknown platform: {name}")
        if listing_type == "buy" and name == "ziroom":
            continue  # ziroom is rent-only
        adapters.append(cls())
    return adapters


# Avoid circular import - click is only needed at runtime for error reporting
import click  # noqa: E402
