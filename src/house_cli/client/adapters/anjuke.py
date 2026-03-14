# Anjuke (安居客) platform adapter
"""Anjuke adapter for second-hand houses.

Anjuke's /sale/ page returns 403 without full browser session.
The city homepage (/{city}.anjuke.com/?from=AJK_Web_City) contains
recommended house listings that can be parsed.

URL patterns:
    City homepage: https://{city}.anjuke.com/?from=AJK_Web_City
    Sale listing:  https://{city}.anjuke.com/sale/ (requires full cookies)
    Detail:        https://{city}.anjuke.com/prop/view/{id}

HTML card structure (Vue SSR):
    <div class="item-info">
      <div class="item-info-title">小区名</div>
      <div class="item-info-meta"><span>区域</span><span>户型 面积</span></div>
      <div class="item-info-price">
        <span class="item-info-price-one-num">599</span>
        <span class="item-info-price-one-unit">万</span>
        <span class="item-info-price-one-avg">62396元/㎡</span>
      </div>
    </div>
"""

import re
from html import unescape

from house_cli.client.base import BaseClient
from house_cli.client.http import HttpClient
from house_cli.client.auth import load_or_extract_cookies, save_cookies
from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter

ANJUKE_CITY = {
    "北京": "beijing", "上海": "shanghai", "广州": "guangzhou", "深圳": "shenzhen",
    "成都": "chengdu", "杭州": "hangzhou", "重庆": "chongqing", "武汉": "wuhan",
    "苏州": "suzhou", "南京": "nanjing", "天津": "tianjin", "西安": "xian",
    "长沙": "changsha", "郑州": "zhengzhou", "东莞": "dongguan", "青岛": "qingdao",
    "合肥": "hefei", "佛山": "foshan", "宁波": "ningbo", "昆明": "kunming",
    "沈阳": "shenyang", "大连": "dalian", "厦门": "xiamen", "济南": "jinan",
    "无锡": "wuxi", "福州": "fuzhou", "哈尔滨": "haerbin", "石家庄": "shijiazhuang",
}


class AnjukeClient(BaseClient):
    """Anjuke adapter (buy + rent). Requires browser cookies."""

    platform_name = "anjuke"

    def _build_list_url(self, filters: SearchFilter) -> str:
        city = ANJUKE_CITY.get(filters.city, "shanghai")

        # Try /sale/ first if we have cookies, fall back to homepage
        if filters.district:
            # District pages: /sale/{district}/
            district_slug = filters.district.lower()
            return f"https://{city}.anjuke.com/sale/{district_slug}/"

        return f"https://{city}.anjuke.com/sale/?from=HomePage_RecommendHouse"

    async def search(self, filters: SearchFilter) -> list[House]:
        city = ANJUKE_CITY.get(filters.city, "shanghai")
        cookies = load_or_extract_cookies("anjuke.com")
        referer = "https://www.anjuke.com/sy-city.html"

        # Try /sale/ page first
        sale_url = self._build_list_url(filters)
        async with HttpClient(referer=referer) as client:
            try:
                resp = await client.get(sale_url, cookies=cookies)
                html = resp.text

                if resp.cookies:
                    merged = {**cookies, **{k: v for k, v in resp.cookies.items()}}
                    save_cookies("anjuke.com", merged)

                if resp.status_code != 403 and len(html) > 5000:
                    houses = self._parse_list(html, filters.city)
                    if houses:
                        return houses
            except Exception:
                pass

            # Fallback: city homepage has recommended listings
            homepage_url = f"https://{city}.anjuke.com/?from=AJK_Web_City"
            try:
                client.set_referer(referer)
                resp = await client.get(homepage_url, cookies=cookies)
                html = resp.text
            except Exception:
                html = ""

        if len(html) < 5000:
            raise RuntimeError(
                "anjuke.com requires browser cookies. "
                "Please visit anjuke.com in your browser, select a city, "
                "then cookies will be automatically extracted (or export to "
                "~/.config/house-cli/cookies.json)"
            )

        return self._parse_list(html, filters.city)

    async def detail(self, house_id: str) -> HouseDetail:
        cookies = load_or_extract_cookies("anjuke.com")
        if not cookies:
            raise RuntimeError(
                "Anjuke detail pages require browser cookies. "
                "Please visit anjuke.com in your browser first."
            )

        city = "beijing"
        url = f"https://{city}.anjuke.com/prop/view/{house_id}"
        async with HttpClient(referer=f"https://{city}.anjuke.com/sale/") as client:
            try:
                resp = await client.get(url, cookies=cookies)
                html = resp.text
            except Exception:
                html = ""

        if len(html) < 5000:
            raise RuntimeError("Anjuke detail page not accessible")

        return self._parse_detail(html, house_id)

    async def get_price_history(self, house_id: str) -> list[dict]:
        d = await self.detail(house_id)
        return d.price_history

    def _parse_list(self, html: str, city: str) -> list[House]:
        houses: list[House] = []
        city_slug = ANJUKE_CITY.get(city, "shanghai")

        # Find all recommendation cards with price-one-num (actual house listings)
        # Split by <a> tags that link to /prop/view/
        card_pattern = re.compile(
            r'<a\s+href="(https?://[^"]*?/prop/view/([^?"]+)[^"]*)"[^>]*>'
            r'(.*?)</a>',
            re.DOTALL,
        )

        for m in card_pattern.finditer(html):
            url = m.group(1)
            house_id = m.group(2)
            card_html = m.group(3)

            # Must have price to be a real listing
            if "item-info-price-one-num" not in card_html:
                continue

            try:
                h = self._parse_card(card_html, house_id, url, city)
                if h:
                    houses.append(h)
            except Exception:
                continue

        return houses

    def _parse_card(self, card: str, house_id: str, url: str, city: str) -> House | None:
        # Community / title
        title = ""
        title_m = re.search(r'class="item-info-title"[^>]*>([^<]+)', card)
        if title_m:
            title = _clean(title_m.group(1))

        # Meta: district + layout/area
        district = ""
        layout = ""
        area = 0.0
        meta_spans = re.findall(
            r'<span[^>]*data-v-[^>]*>([^<]+)</span>', card
        )
        for span in meta_spans:
            span = span.strip()
            if not span:
                continue
            # "朝阳 双井" pattern
            if re.match(r'[\u4e00-\u9fff]+\s+[\u4e00-\u9fff]+$', span):
                parts = span.split()
                district = parts[0]
            # "2室1厅 96㎡" pattern
            layout_m = re.search(r'(\d室\d厅)', span)
            if layout_m:
                layout = layout_m.group(1)
            area_m = re.search(r'([\d.]+)㎡', span)
            if area_m:
                area = float(area_m.group(1))

        # Price
        price = 0.0
        price_m = re.search(r'item-info-price-one-num"[^>]*>([\d.]+)', card)
        if price_m:
            price = float(price_m.group(1))

        # Unit price
        unit_price = None
        up_m = re.search(r'item-info-price-one-avg"[^>]*>([\d,]+)元/㎡', card)
        if up_m:
            unit_price = float(up_m.group(1).replace(",", ""))

        if not price:
            return None

        return House(
            id=house_id,
            platform="anjuke",
            title=title,
            price=price,
            price_unit="万",
            area=area,
            unit_price=unit_price,
            layout=layout,
            district=district,
            city=city,
            url=url,
        )

    def _parse_detail(self, html: str, house_id: str) -> HouseDetail:
        title_m = re.search(r"<title>([^<]+)", html)
        title = _clean(title_m.group(1)) if title_m else ""

        price = 0.0
        price_m = re.search(r'item-info-price-one-num[^>]*>([\d.]+)', html)
        if price_m:
            price = float(price_m.group(1))

        return HouseDetail(
            id=house_id, platform="anjuke", title=title, price=price,
            price_unit="万", area=0.0,
            url=f"https://beijing.anjuke.com/prop/view/{house_id}",
        )


def _clean(text: str) -> str:
    return unescape(text).strip()
