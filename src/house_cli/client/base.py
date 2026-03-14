from abc import ABC, abstractmethod

from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter


class BaseClient(ABC):
    """Abstract base class for all platform adapters.

    Every platform adapter must implement these methods,
    returning unified data models regardless of the source platform.
    """

    platform_name: str = ""

    @abstractmethod
    async def search(self, filters: SearchFilter) -> list[House]:
        """Search houses with given filters, return unified House list."""
        ...

    @abstractmethod
    async def detail(self, house_id: str) -> HouseDetail:
        """Get house detail by platform-specific ID."""
        ...

    @abstractmethod
    async def get_price_history(self, house_id: str) -> list[dict]:
        """Get price change history for a listing."""
        ...
