from dataclasses import dataclass, field
from typing import Optional


@dataclass
class House:
    """Unified house data model across all platforms."""

    id: str
    platform: str  # beike, anjuke, tongcheng, ziroom, fang, zhuge
    title: str
    price: float  # total price (万元) for buy, monthly rent (元) for rent
    price_unit: str  # "万" or "元/月"
    area: float  # square meters
    unit_price: Optional[float] = None  # 元/㎡
    layout: str = ""  # e.g. "3室2厅1卫"
    floor: str = ""  # e.g. "中楼层/共18层"
    orientation: str = ""  # e.g. "南北"
    community: str = ""  # community/小区 name
    district: str = ""  # district/区
    city: str = ""
    address: str = ""
    url: str = ""
    listing_date: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class HouseDetail(House):
    """Extended house detail with additional info."""

    description: str = ""
    building_year: str = ""
    building_type: str = ""  # 塔楼/板楼
    elevator: str = ""
    parking: str = ""
    green_ratio: str = ""  # 绿化率
    volume_ratio: str = ""  # 容积率
    property_fee: str = ""  # 物业费
    nearby_schools: list[str] = field(default_factory=list)
    nearby_subway: list[str] = field(default_factory=list)
    price_history: list[dict] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
