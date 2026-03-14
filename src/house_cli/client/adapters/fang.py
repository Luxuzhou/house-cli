# Fang.com (房天下) platform adapter
"""Fang.com adapter for second-hand houses.

List page URL pattern:
    https://{city_abbr}.esf.fang.com/house/i3{page}/
    Filters appended as path segments:
    - Area (district): a{code}/ (numeric codes per city)
    - Price: c{min}_{max}/ (万元)
    - Area size: d{min}_{max}/ (㎡)
    - Layout: e290 (1室), e291 (2室), e292 (3室), e293 (4室), e294 (5室+)
    - Sort: g21(总价从低到高) g22(总价从高到低) g23(单价从低到高) g24(单价从高到低) g25(面积从小到大) g26(面积从大到小)
    Combined: /house/a{district}c{price}e{layout}g{sort}i3{page}/

Detail page:
    https://{city_abbr}.esf.fang.com/chushou/3_{house_id}.htm

HTML structure:
    Listings in <div class="shop_list shop_list_4">
    Each card is a <dl class="clearfix"> with:
    - <dt>: thumbnail image, href to detail
    - <dd>: h4 (title), p.tel_shop (layout|area|floor|orientation), p.add_shop (community, district)
    - <dd class="price_right">: <b>price</b>万, unit_price元/㎡
"""

import re
from html import unescape

from house_cli.client.base import BaseClient
from house_cli.client.http import HttpClient
from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter
from house_cli.models.cities import CITY_ABBR

# Fang.com uses different city subdomains
FANG_CITY_ABBR = {
    "北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz",
    "成都": "cd", "杭州": "hz", "重庆": "cq", "武汉": "wh",
    "苏州": "su", "南京": "nj", "天津": "tj", "西安": "xa",
    "长沙": "cs", "郑州": "zz", "东莞": "dg", "青岛": "qd",
    "合肥": "hf", "佛山": "fs", "宁波": "nb", "昆明": "km",
    "沈阳": "sy", "大连": "dl", "厦门": "xm", "济南": "jn",
    "无锡": "wx", "福州": "fz", "哈尔滨": "hrb", "石家庄": "sjz",
}

LAYOUT_MAP = {"1": "e290", "2": "e291", "3": "e292", "4": "e293", "5": "e294"}

SORT_MAP = {
    "default": "",
    "price_asc": "g21",
    "price_desc": "g22",
    "area": "g25",
}


class FangClient(BaseClient):
    """Fang.com adapter (buy + rent)."""

    platform_name = "fang"

    def _build_list_url(self, filters: SearchFilter, area_code: str = "") -> str:
        city_abbr = FANG_CITY_ABBR.get(filters.city, "sh")
        base = f"https://{city_abbr}.esf.fang.com"

        # District area code: /house-a0154/ format
        if area_code:
            base_path = f"/house-{area_code}"
        else:
            base_path = "/house"

        segs: list[str] = []

        # Price range: c{min}_{max}
        if filters.min_price is not None or filters.max_price is not None:
            lo = int(filters.min_price) if filters.min_price else 0
            hi = int(filters.max_price) if filters.max_price else 0
            segs.append(f"c{lo}_{hi}")

        # Area range: d{min}_{max}
        if filters.min_area is not None or filters.max_area is not None:
            lo = int(filters.min_area) if filters.min_area else 0
            hi = int(filters.max_area) if filters.max_area else 0
            segs.append(f"d{lo}_{hi}")

        # Layout
        if filters.layout:
            m = re.search(r"(\d)", filters.layout)
            if m and m.group(1) in LAYOUT_MAP:
                segs.append(LAYOUT_MAP[m.group(1)])

        # Sort
        sort_seg = SORT_MAP.get(filters.sort_by, "")
        if sort_seg:
            segs.append(sort_seg)

        # Pagination
        if filters.page > 1:
            segs.append(f"i3{filters.page}")

        filter_str = "".join(segs)
        if filter_str:
            return f"{base}{base_path}/{filter_str}/"
        return f"{base}{base_path}/"

    async def search(self, filters: SearchFilter) -> list[House]:
        city_abbr = FANG_CITY_ABBR.get(filters.city, "sh")
        referer = f"https://{city_abbr}.esf.fang.com/"

        async with HttpClient(referer=referer) as client:
            # If district specified, resolve area code from page first
            if filters.district:
                index_url = f"https://{city_abbr}.esf.fang.com/house/"
                resp = await client.get(index_url)
                area_code = self._find_area_code(resp.text, filters.district)
                if area_code:
                    url = self._build_list_url(filters, area_code=area_code)
                else:
                    url = self._build_list_url(filters)
            else:
                area_code = ""
                url = self._build_list_url(filters)

            client.set_referer(referer)
            resp = await client.get(url)
            html = resp.text

        if len(html) < 5000:
            raise RuntimeError("fang.com returned unexpected response, possible anti-bot block")

        houses = self._parse_list(html, filters.city)
        # When server-side area code filtering was applied, tag all results with the district
        # (fang.com's HTML only contains sub-district/bizcircle names, not the district itself)
        if filters.district and area_code:
            for h in houses:
                h.district = filters.district
        return houses

    @staticmethod
    def _find_area_code(html: str, district: str) -> str:
        """Extract fang.com area code (e.g. 'a0154') for a district name from the page HTML."""
        pattern = re.compile(
            r'href="/house-(a\d+)/"[^>]*>\s*' + re.escape(district) + r'\s*</a>'
        )
        m = pattern.search(html)
        return m.group(1) if m else ""

    async def detail(self, house_id: str) -> HouseDetail:
        # Default to Shanghai; could infer from stored search context
        city_abbr = "sh"
        url = f"https://{city_abbr}.esf.fang.com/chushou/3_{house_id}.htm"
        referer = f"https://{city_abbr}.esf.fang.com/house/"

        async with HttpClient(referer=referer) as client:
            resp = await client.get(url)
            html = resp.text

        if len(html) < 5000:
            raise RuntimeError("fang.com detail page returned unexpected response")

        return self._parse_detail(html, house_id)

    async def get_price_history(self, house_id: str) -> list[dict]:
        d = await self.detail(house_id)
        return d.price_history

    # ── HTML Parsing ────────────────────────────────────────────────

    def _parse_list(self, html: str, city: str) -> list[House]:
        houses: list[House] = []

        # Cards are <dl class="clearfix"> inside <div class="shop_list">
        cards = re.split(r'<dl\s+class="clearfix\s*"', html)

        for card in cards[1:]:  # skip before first match
            try:
                h = self._parse_card(card, city)
                if h:
                    houses.append(h)
            except Exception:
                continue

        return houses

    def _parse_card(self, card: str, city: str) -> House | None:
        # House ID and URL from href
        href_m = re.search(r'href="(/chushou/3_(\d+)\.htm)"', card)
        if not href_m:
            return None
        house_id = href_m.group(2)

        # Also check data-bg for houseid
        data_bg_m = re.search(r'"houseid"\s*:\s*"(\d+)"', card)
        if data_bg_m:
            house_id = data_bg_m.group(1)

        # Title from h4 > a > span.tit_shop
        title = ""
        title_m = re.search(r'class="tit_shop">\s*([^<]+)', card)
        if title_m:
            title = _clean(title_m.group(1))

        # tel_shop: "3室2厅 | 138㎡ | 低层（共18层）| 南北向"
        layout = ""
        area = 0.0
        floor = ""
        orientation = ""
        tel_m = re.search(r'class="tel_shop">(.*?)</p>', card, re.DOTALL)
        if tel_m:
            tel_text = _strip_tags(tel_m.group(1))
            segments = [s.strip() for s in tel_text.split("|")]
            for seg in segments:
                seg = seg.strip()
                if "室" in seg or "厅" in seg or "房" in seg:
                    layout = seg
                elif "㎡" in seg:
                    area_m = re.search(r"([\d.]+)", seg)
                    if area_m:
                        area = float(area_m.group(1))
                elif "层" in seg:
                    floor = seg
                elif "向" in seg or seg in ("南", "北", "东", "西", "南北", "东南", "东北", "西南", "西北"):
                    orientation = seg

        # Community and district from add_shop
        community = ""
        district = ""
        add_m = re.search(r'class="add_shop">(.*?)</p>', card, re.DOTALL)
        if add_m:
            # Community from <a> tag
            comm_m = re.search(r'<a[^>]*>\s*([^<]+)', add_m.group(1))
            if comm_m:
                community = _clean(comm_m.group(1))
            # District from <span> text
            span_m = re.search(r'<span>([^<]+)', add_m.group(1))
            if span_m:
                addr_text = _clean(span_m.group(1))
                # First word is usually the district/bizcircle
                parts = addr_text.split()
                if parts:
                    district = parts[0]

        # Price from price_right
        price = 0.0
        price_m = re.search(r'<b>([\d.]+)</b>\s*万', card)
        if price_m:
            price = float(price_m.group(1))

        # Unit price
        unit_price = None
        up_m = re.search(r'([\d,]+)\s*元/㎡', card)
        if up_m:
            unit_price = float(up_m.group(1).replace(",", ""))

        # Tags from label paragraph
        tags: list[str] = []
        label_m = re.search(r'class="clearfix label">(.*?)</p>', card, re.DOTALL)
        if label_m:
            tag_items = re.findall(r'>([^<]+)<', label_m.group(1))
            tags = [t.strip() for t in tag_items if t.strip() and len(t.strip()) < 20]

        # URL
        city_abbr = FANG_CITY_ABBR.get(city, "sh")
        url = f"https://{city_abbr}.esf.fang.com/chushou/3_{house_id}.htm"

        return House(
            id=house_id,
            platform="fang",
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
        # Title
        title = ""
        title_m = re.search(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)', html)
        if not title_m:
            title_m = re.search(r"<title>([^<]+)", html)
        title = _clean(title_m.group(1)) if title_m else ""

        # Price
        price = 0.0
        price_m = re.search(r'class="[^"]*price[^"]*"[^>]*>.*?<b>([\d.]+)</b>\s*万', html, re.DOTALL)
        if not price_m:
            price_m = re.search(r'<b>([\d.]+)</b>\s*万', html)
        if price_m:
            price = float(price_m.group(1))

        # Unit price
        unit_price = None
        up_m = re.search(r'([\d,]+)\s*元/㎡', html)
        if up_m:
            unit_price = float(up_m.group(1).replace(",", ""))

        # Parse info table rows
        area = 0.0
        layout = ""
        floor = ""
        orientation = ""
        building_type = ""
        building_year = ""
        elevator = ""
        community = ""
        district = ""
        address = ""

        # Common pattern: <span class="lab">xxx</span> value
        info_pairs = re.findall(
            r'<span[^>]*class="lab"[^>]*>([^<]+)</span>\s*([^<]+)', html
        )
        for label, value in info_pairs:
            label = label.strip()
            value = _clean(value)
            if "面积" in label:
                m = re.search(r"([\d.]+)", value)
                if m:
                    area = float(m.group(1))
            elif "户型" in label or "房型" in label:
                layout = value
            elif "楼层" in label:
                floor = value
            elif "朝向" in label:
                orientation = value
            elif "建筑类型" in label:
                building_type = value
            elif "年代" in label or "建成" in label:
                building_year = value
            elif "电梯" in label:
                elevator = value

        return HouseDetail(
            id=house_id,
            platform="fang",
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
            city="",
            address=address,
            url=f"https://sh.esf.fang.com/chushou/3_{house_id}.htm",
            building_year=building_year,
            building_type=building_type,
            elevator=elevator,
        )


def _clean(text: str) -> str:
    return unescape(text).strip()


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
