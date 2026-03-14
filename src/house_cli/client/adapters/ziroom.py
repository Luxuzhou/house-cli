# Ziroom (自如) rental platform adapter
"""Ziroom adapter for rental listings only.

Ziroom uses JS-based anti-bot (obfuscated cookie challenge).
Requires browser cookies to access.

List page URL:
    https://{city_abbr}.ziroom.com/z/
    Filters: p{min}-{max}/ (price), s{min}-{max}/ (area)
"""

import re
from html import unescape

from house_cli.client.base import BaseClient
from house_cli.client.http import HttpClient
from house_cli.client.auth import load_or_extract_cookies, save_cookies
from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter

ZIROOM_CITY = {
    "北京": "www", "上海": "sh", "深圳": "sz", "广州": "gz",
    "成都": "cd", "杭州": "hz", "武汉": "wh", "南京": "nj",
    "天津": "tj", "苏州": "su", "重庆": "cq", "西安": "xa",
}


class ZiroomClient(BaseClient):
    """Ziroom adapter (rent only). Requires browser cookies."""

    platform_name = "ziroom"

    def _build_list_url(self, filters: SearchFilter) -> str:
        city_abbr = ZIROOM_CITY.get(filters.city, "sh")
        base = f"https://{city_abbr}.ziroom.com/z/"

        segs: list[str] = []
        if filters.page > 1:
            segs.append(f"p{filters.page}")

        if segs:
            return base + "-".join(segs) + "/"
        return base

    async def search(self, filters: SearchFilter) -> list[House]:
        if filters.listing_type == "buy":
            raise RuntimeError("Ziroom only supports rent listings, not buy")

        url = self._build_list_url(filters)
        cookies = load_or_extract_cookies("ziroom.com")

        city_abbr = ZIROOM_CITY.get(filters.city, "sh")
        referer = f"https://{city_abbr}.ziroom.com/"

        async with HttpClient(referer=referer) as client:
            resp = await client.get(url, cookies=cookies)
            html = resp.text

            if resp.cookies:
                merged = {**cookies, **{k: v for k, v in resp.cookies.items()}}
                save_cookies("ziroom.com", merged)

        # Ziroom returns obfuscated JS without cookies
        if len(html) < 5000 or "EO_Bot_Ssid" in html:
            raise RuntimeError(
                "ziroom.com requires browser cookies (JS anti-bot challenge). "
                "Please visit ziroom.com in your browser first, "
                "then cookies will be automatically extracted (or export to "
                "~/.config/house-cli/cookies.json)"
            )

        return self._parse_list(html, filters.city)

    async def detail(self, house_id: str) -> HouseDetail:
        cookies = load_or_extract_cookies("ziroom.com")
        if not cookies:
            raise RuntimeError(
                "Ziroom detail pages require browser cookies. "
                "Please visit ziroom.com in your browser first."
            )

        url = f"https://sh.ziroom.com/x/{house_id}.html"
        async with HttpClient(referer="https://sh.ziroom.com/z/") as client:
            resp = await client.get(url, cookies=cookies)
            html = resp.text

        if len(html) < 5000:
            raise RuntimeError("Ziroom detail page not accessible")

        return self._parse_detail(html, house_id)

    async def get_price_history(self, house_id: str) -> list[dict]:
        return []  # Ziroom doesn't provide price history

    def _parse_list(self, html: str, city: str) -> list[House]:
        houses: list[House] = []

        # Ziroom uses <div class="Z_list-box"> with individual room cards
        cards = re.split(r'<div[^>]*class="[^"]*item[^"]*"', html)

        for card in cards[1:]:
            try:
                h = self._parse_card(card, city)
                if h:
                    houses.append(h)
            except Exception:
                continue

        return houses

    def _parse_card(self, card: str, city: str) -> House | None:
        # Room ID from href
        href_m = re.search(r'href="[^"]*?/(\d+)\.html"', card)
        if not href_m:
            return None
        room_id = href_m.group(1)

        # Title
        title_m = re.search(r'title="([^"]+)"', card)
        title = _clean(title_m.group(1)) if title_m else ""

        # Price (monthly rent in 元)
        price = 0.0
        price_m = re.search(r'([\d,]+)\s*元/月', card)
        if price_m:
            price = float(price_m.group(1).replace(",", ""))

        # Area
        area = 0.0
        area_m = re.search(r'([\d.]+)\s*㎡', card)
        if area_m:
            area = float(area_m.group(1))

        city_abbr = ZIROOM_CITY.get(city, "sh")
        return House(
            id=room_id,
            platform="ziroom",
            title=title,
            price=price,
            price_unit="元/月",
            area=area,
            city=city,
            url=f"https://{city_abbr}.ziroom.com/x/{room_id}.html",
        )

    def _parse_detail(self, html: str, house_id: str) -> HouseDetail:
        title_m = re.search(r"<title>([^<]+)", html)
        title = _clean(title_m.group(1)) if title_m else ""

        price = 0.0
        price_m = re.search(r'([\d,]+)\s*元/月', html)
        if price_m:
            price = float(price_m.group(1).replace(",", ""))

        return HouseDetail(
            id=house_id, platform="ziroom", title=title, price=price,
            price_unit="元/月", area=0.0,
            url=f"https://sh.ziroom.com/x/{house_id}.html",
        )


def _clean(text: str) -> str:
    return unescape(text).strip()
