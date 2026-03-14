# 58 Tongcheng (58同城) platform adapter
"""58.com adapter for second-hand houses.

Requires browser cookies (JS anti-bot redirect without them).

List page URL:
    https://{city_abbr}.58.com/ershoufang/

HTML card structure (Vue SSR):
    <div class="property">
      <a href="/ershoufang/{id}x.shtml?...">
        <div class="property-content">
          <h3 class="property-content-title-name">标题</h3>
          <div class="property-content-info">
            <p class="property-content-info-attribute">
              <span>3</span><span>室</span><span>1</span><span>厅</span>
            </p>
            <p>74.24㎡</p>
            <p>南北</p>
            <p>中层(共6层)</p>
            <p>1999年建造</p>
          </div>
          <div class="property-content-info-comm">
            <p class="property-content-info-comm-name">小区名</p>
            <p class="property-content-info-comm-address">
              <span>静安</span><span>大宁</span><span>地址</span>
            </p>
          </div>
          <div class="property-content-info">
            <span class="property-content-info-tag">满五年</span>
          </div>
        </div>
        <div class="property-price">
          <span class="property-price-total-num">332</span>
          <span class="property-price-total-text">万</span>
          <p class="property-price-average">44720元/㎡</p>
        </div>
      </a>
    </div>
"""

import re
from html import unescape

from house_cli.client.base import BaseClient
from house_cli.client.http import HttpClient
from house_cli.client.auth import load_or_extract_cookies, save_cookies
from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter

TC_CITY_ABBR = {
    "北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz",
    "成都": "cd", "杭州": "hz", "重庆": "cq", "武汉": "wh",
    "苏州": "su", "南京": "nj", "天津": "tj", "西安": "xa",
    "长沙": "cs", "郑州": "zz", "东莞": "dg", "青岛": "qd",
    "合肥": "hf", "佛山": "fs", "宁波": "nb", "昆明": "km",
    "沈阳": "sy", "大连": "dl", "厦门": "xm", "济南": "jn",
    "无锡": "wx", "福州": "fz", "哈尔滨": "hrb", "石家庄": "sjz",
}


class TongchengClient(BaseClient):
    """58 Tongcheng adapter (buy + rent). Requires browser cookies."""

    platform_name = "tongcheng"

    def _build_list_url(self, filters: SearchFilter) -> str:
        city_abbr = TC_CITY_ABBR.get(filters.city, "sh")
        base = f"https://{city_abbr}.58.com/ershoufang/"

        if filters.page > 1:
            return f"{base}pn{filters.page}/"
        return base

    async def search(self, filters: SearchFilter) -> list[House]:
        url = self._build_list_url(filters)
        cookies = load_or_extract_cookies("58.com")

        city_abbr = TC_CITY_ABBR.get(filters.city, "sh")
        referer = f"https://{city_abbr}.58.com/"

        try:
            async with HttpClient(referer=referer) as client:
                resp = await client.get(url, cookies=cookies)
                html = resp.text

                if resp.cookies:
                    merged = {**cookies, **{k: v for k, v in resp.cookies.items()}}
                    save_cookies("58.com", merged)
        except Exception:
            html = ""

        if len(html) < 5000 or "antibot" in html or "verifycode" in html:
            raise RuntimeError(
                "58.com requires browser cookies (JS anti-bot). "
                "Please visit 58.com/ershoufang in your browser first, "
                "then export cookies via document.cookie to "
                "~/.config/house-cli/cookies.json"
            )

        return self._parse_list(html, filters.city)

    async def detail(self, house_id: str) -> HouseDetail:
        cookies = load_or_extract_cookies("58.com")
        if not cookies:
            raise RuntimeError("58.com detail pages require browser cookies.")

        city_abbr = "sh"
        url = f"https://{city_abbr}.58.com/ershoufang/{house_id}x.shtml"

        try:
            async with HttpClient(referer=f"https://{city_abbr}.58.com/ershoufang/") as client:
                resp = await client.get(url, cookies=cookies)
                html = resp.text
        except Exception:
            html = ""

        if len(html) < 5000:
            raise RuntimeError("58.com detail page not accessible")

        return self._parse_detail(html, house_id)

    async def get_price_history(self, house_id: str) -> list[dict]:
        d = await self.detail(house_id)
        return d.price_history

    def _parse_list(self, html: str, city: str) -> list[House]:
        houses: list[House] = []
        city_abbr = TC_CITY_ABBR.get(city, "sh")

        # Split by property cards
        cards = html.split('class="property"')

        for card in cards[1:]:
            try:
                h = self._parse_card(card, city, city_abbr)
                if h:
                    houses.append(h)
            except Exception:
                continue

        return houses

    def _parse_card(self, card: str, city: str, city_abbr: str) -> House | None:
        # House ID from href
        href_m = re.search(r'href="[^"]*?/ershoufang/(\d+)x\.shtml', card)
        if not href_m:
            return None
        house_id = href_m.group(1)

        # Title
        title = ""
        title_m = re.search(
            r'class="property-content-title-name"[^>]*>([^<]+)', card
        )
        if title_m:
            title = _clean(title_m.group(1))

        # Layout: <span>3</span> <span>室</span> <span>1</span> <span>厅</span>
        layout = ""
        attr_m = re.search(
            r'class="[^"]*property-content-info-attribute[^"]*"[^>]*>(.*?)</p>',
            card, re.DOTALL,
        )
        if attr_m:
            spans = re.findall(r'<span[^>]*>([^<]+)</span>', attr_m.group(1))
            layout = "".join(s.strip() for s in spans)

        # Info texts: area, orientation, floor, year
        area = 0.0
        orientation = ""
        floor = ""
        building_year = ""
        info_texts = re.findall(
            r'class="property-content-info-text"[^>]*>\s*([^<]+?)\s*<', card
        )
        for text in info_texts:
            text = text.strip()
            if "㎡" in text:
                m = re.search(r"([\d.]+)", text)
                if m:
                    area = float(m.group(1))
            elif "层" in text:
                floor = text
            elif "建造" in text or "年" in text:
                building_year = text
            elif text in ("南", "北", "东", "西", "南北", "东南", "东北", "西南", "西北"):
                orientation = text

        # Community
        community = ""
        comm_m = re.search(
            r'class="property-content-info-comm-name"[^>]*>([^<]+)', card
        )
        if comm_m:
            community = _clean(comm_m.group(1))

        # District and address
        district = ""
        address_spans = re.findall(
            r'class="property-content-info-comm-address"[^>]*>(.*?)</p>',
            card, re.DOTALL,
        )
        if address_spans:
            addr_items = re.findall(r'<span[^>]*>([^<]+)</span>', address_spans[0])
            if addr_items:
                district = addr_items[0].strip()

        # Price
        price = 0.0
        price_m = re.search(
            r'class="property-price-total-num"[^>]*>([\d.]+)', card
        )
        if price_m:
            price = float(price_m.group(1))

        # Unit price
        unit_price = None
        up_m = re.search(
            r'class="property-price-average"[^>]*>\s*([\d,]+)元/㎡', card
        )
        if up_m:
            unit_price = float(up_m.group(1).replace(",", ""))

        # Tags
        tags: list[str] = []
        tag_items = re.findall(
            r'class="property-content-info-tag"[^>]*>([^<]+)', card
        )
        tags = [t.strip() for t in tag_items if t.strip()]

        url = f"https://{city_abbr}.58.com/ershoufang/{house_id}x.shtml"

        return House(
            id=house_id,
            platform="tongcheng",
            title=title,
            price=price,
            price_unit="万",
            area=area,
            unit_price=unit_price,
            layout=layout,
            floor=floor,
            orientation=orientation,
            community=community,
            district=district,
            city=city,
            url=url,
            tags=tags,
        )

    def _parse_detail(self, html: str, house_id: str) -> HouseDetail:
        title_m = re.search(r"<title>([^<]+)", html)
        title = _clean(title_m.group(1)) if title_m else ""

        price = 0.0
        price_m = re.search(r'property-price-total-num[^>]*>([\d.]+)', html)
        if price_m:
            price = float(price_m.group(1))

        return HouseDetail(
            id=house_id, platform="tongcheng", title=title, price=price,
            price_unit="万", area=0.0,
            url=f"https://sh.58.com/ershoufang/{house_id}x.shtml",
        )


def _clean(text: str) -> str:
    return unescape(text).strip()
