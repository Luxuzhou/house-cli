# Zhuge Zhaofang (诸葛找房) platform adapter
"""Zhuge adapter for second-hand houses.

Zhuge actively blocks scrapers with HTTP 418 "I'm a Teapot".
Requires browser cookies to access.

List page URL:
    https://{city_abbr}.zhuge.com/ershoufang/
    Filters: various query params
"""

import re
from html import unescape

from house_cli.client.base import BaseClient
from house_cli.client.http import HttpClient
from house_cli.client.auth import load_or_extract_cookies, save_cookies
from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter

ZHUGE_CITY = {
    "北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz",
    "成都": "cd", "杭州": "hz", "重庆": "cq", "武汉": "wh",
    "苏州": "su", "南京": "nj", "天津": "tj", "西安": "xa",
    "长沙": "cs", "郑州": "zz", "东莞": "dg", "青岛": "qd",
    "合肥": "hf", "佛山": "fs", "宁波": "nb", "昆明": "km",
    "沈阳": "sy", "大连": "dl", "厦门": "xm", "济南": "jn",
}


class ZhugeClient(BaseClient):
    """Zhuge Zhaofang adapter (buy + rent). Requires browser cookies."""

    platform_name = "zhuge"

    def _build_list_url(self, filters: SearchFilter) -> str:
        city_abbr = ZHUGE_CITY.get(filters.city, "sh")
        base = f"https://{city_abbr}.zhuge.com/ershoufang/"

        params: list[str] = []
        if filters.page > 1:
            params.append(f"p{filters.page}")

        if params:
            return base + "?page=" + str(filters.page)
        return base

    async def search(self, filters: SearchFilter) -> list[House]:
        url = self._build_list_url(filters)
        cookies = load_or_extract_cookies("zhuge.com")

        city_abbr = ZHUGE_CITY.get(filters.city, "sh")
        referer = f"https://{city_abbr}.zhuge.com/"

        try:
            async with HttpClient(referer=referer) as client:
                resp = await client.get(url, cookies=cookies)
                html = resp.text

                if resp.cookies:
                    merged = {**cookies, **{k: v for k, v in resp.cookies.items()}}
                    save_cookies("zhuge.com", merged)
        except Exception:
            html = ""

        if len(html) < 5000:
            raise RuntimeError(
                "zhuge.com returned 418 (anti-bot). "
                "Please visit zhuge.com in your browser first, "
                "then cookies will be automatically extracted (or export to "
                "~/.config/house-cli/cookies.json)"
            )

        return self._parse_list(html, filters.city)

    async def detail(self, house_id: str) -> HouseDetail:
        cookies = load_or_extract_cookies("zhuge.com")
        if not cookies:
            raise RuntimeError(
                "Zhuge detail pages require browser cookies. "
                "Please visit zhuge.com in your browser first."
            )

        city_abbr = "sh"
        url = f"https://{city_abbr}.zhuge.com/ershoufang/{house_id}.html"

        async with HttpClient(referer=f"https://{city_abbr}.zhuge.com/ershoufang/") as client:
            resp = await client.get(url, cookies=cookies)
            html = resp.text

        if len(html) < 5000:
            raise RuntimeError("Zhuge detail page not accessible")

        return self._parse_detail(html, house_id)

    async def get_price_history(self, house_id: str) -> list[dict]:
        d = await self.detail(house_id)
        return d.price_history

    def _parse_list(self, html: str, city: str) -> list[House]:
        houses: list[House] = []

        # Zhuge uses <div class="houseList"> with individual items
        cards = re.split(r'<div[^>]*class="[^"]*house-item[^"]*"', html)
        if len(cards) <= 1:
            cards = re.split(r'<li[^>]*class="[^"]*list-item[^"]*"', html)

        for card in cards[1:]:
            try:
                h = self._parse_card(card, city)
                if h:
                    houses.append(h)
            except Exception:
                continue

        return houses

    def _parse_card(self, card: str, city: str) -> House | None:
        # House ID from href
        href_m = re.search(r'href="[^"]*?/ershoufang/(\d+)\.html"', card)
        if not href_m:
            href_m = re.search(r'href="[^"]*?/(\d+)\.html"', card)
        if not href_m:
            return None
        house_id = href_m.group(1)

        # Title
        title_m = re.search(r'title="([^"]+)"', card)
        title = _clean(title_m.group(1)) if title_m else ""

        # Price
        price = 0.0
        price_m = re.search(r'([\d.]+)\s*万', card)
        if price_m:
            price = float(price_m.group(1))

        # Unit price
        unit_price = None
        up_m = re.search(r'([\d,]+)\s*元/㎡', card)
        if up_m:
            unit_price = float(up_m.group(1).replace(",", ""))

        # Area
        area = 0.0
        area_m = re.search(r'([\d.]+)\s*㎡', card)
        if area_m:
            area = float(area_m.group(1))

        # Layout
        layout = ""
        layout_m = re.search(r'(\d室\d厅)', card)
        if layout_m:
            layout = layout_m.group(1)

        city_abbr = ZHUGE_CITY.get(city, "sh")
        return House(
            id=house_id,
            platform="zhuge",
            title=title,
            price=price,
            price_unit="万",
            area=area,
            unit_price=unit_price,
            layout=layout,
            city=city,
            url=f"https://{city_abbr}.zhuge.com/ershoufang/{house_id}.html",
        )

    def _parse_detail(self, html: str, house_id: str) -> HouseDetail:
        title_m = re.search(r"<title>([^<]+)", html)
        title = _clean(title_m.group(1)) if title_m else ""

        price = 0.0
        price_m = re.search(r'([\d.]+)\s*万', html)
        if price_m:
            price = float(price_m.group(1))

        return HouseDetail(
            id=house_id, platform="zhuge", title=title, price=price,
            price_unit="万", area=0.0,
            url=f"https://sh.zhuge.com/ershoufang/{house_id}.html",
        )


def _clean(text: str) -> str:
    return unescape(text).strip()
