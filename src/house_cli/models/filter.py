from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchFilter:
    """Unified search filter across all platforms."""

    city: str = "上海"
    district: str = ""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    layout: str = ""  # e.g. "2室", "3室"
    listing_type: str = "buy"  # "buy" or "rent"
    sort_by: str = "default"  # default, price_asc, price_desc, area, date
    page: int = 1
    page_size: int = 20
    keywords: str = ""
    tags: list[str] = field(default_factory=list)
