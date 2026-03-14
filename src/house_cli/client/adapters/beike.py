# Beike/Lianjia platform adapter
"""Beike (ke.com) adapter for searching and viewing second-hand houses.

List page URL pattern:
    https://{city_abbr}.ke.com/ershoufang/{district}/{filters}pg{page}/

Filters are path segments that can be combined:
    - District: pudong, xuhui, changning, etc.
    - Price: p1-p7 (predefined ranges) or bp{min}ep{max} (custom, unit: 万)
    - Area: a1-a7 (predefined) or ba{min}ea{max} (custom, unit: ㎡)
    - Layout: l1(1室) l2(2室) l3(3室) l4(4室) l5(5室+) l6(other)
    - Sort: no param=default, co41(单价从低到高), co42(单价从高到低),
            co31(总价从低到高), co32(总价从高到低),
            co11(面积从小到大), co12(面积从大到小)
    - Pagination: pg{N}

Detail page:
    https://{city_abbr}.ke.com/ershoufang/{house_id}.html
    Requires browser cookies to avoid CAPTCHA.
"""

import re
from html import unescape

from house_cli.client.base import BaseClient
from house_cli.client.http import HttpClient
from house_cli.client.auth import load_or_extract_cookies, save_cookies
from house_cli.models.house import House, HouseDetail
from house_cli.models.filter import SearchFilter
from house_cli.models.cities import CITY_ABBR, DISTRICTS

SORT_MAP = {
    "default": "",
    "price_asc": "co31",
    "price_desc": "co32",
    "area": "co11",
    "unit_price_asc": "co41",
    "unit_price_desc": "co42",
}


class BeikeClient(BaseClient):
    """Beike/Lianjia adapter (buy + rent)."""

    platform_name = "beike"

    def _build_list_url(self, filters: SearchFilter) -> str:
        city_abbr = CITY_ABBR.get(filters.city, "sh")
        base = f"https://{city_abbr}.ke.com/ershoufang/"

        parts: list[str] = []

        # District
        district_map = DISTRICTS.get(filters.city, {})
        if filters.district:
            slug = district_map.get(filters.district, "")
            if slug:
                parts.append(slug + "/")

        # Build filter segment
        segs: list[str] = []

        # Price filter
        if filters.min_price is not None or filters.max_price is not None:
            lo = int(filters.min_price) if filters.min_price else 0
            hi = int(filters.max_price) if filters.max_price else 0
            if lo and hi:
                segs.append(f"bp{lo}ep{hi}")
            elif lo:
                segs.append(f"bp{lo}ep0")
            elif hi:
                segs.append(f"bp0ep{hi}")

        # Area filter
        if filters.min_area is not None or filters.max_area is not None:
            lo = int(filters.min_area) if filters.min_area else 0
            hi = int(filters.max_area) if filters.max_area else 0
            if lo and hi:
                segs.append(f"ba{lo}ea{hi}")
            elif lo:
                segs.append(f"ba{lo}ea0")
            elif hi:
                segs.append(f"ba0ea{hi}")

        # Layout filter: "2室" -> l2, "3室" -> l3
        if filters.layout:
            m = re.search(r"(\d)", filters.layout)
            if m:
                n = int(m.group(1))
                if 1 <= n <= 5:
                    segs.append(f"l{n}")

        # Sort
        sort_seg = SORT_MAP.get(filters.sort_by, "")
        if sort_seg:
            segs.append(sort_seg)

        # Pagination
        if filters.page > 1:
            segs.append(f"pg{filters.page}")

        filter_str = "".join(segs)
        if filter_str:
            if parts:
                # district + filters: /ershoufang/pudong/bp100ep300pg2/
                return base + parts[0] + filter_str + "/"
            else:
                return base + filter_str + "/"

        if parts:
            return base + parts[0]
        return base

    async def search(self, filters: SearchFilter) -> list[House]:
        """Search ke.com second-hand houses, parse HTML list page."""
        url = self._build_list_url(filters)
        city_abbr = CITY_ABBR.get(filters.city, "sh")
        referer = f"https://{city_abbr}.ke.com/ershoufang/"

        cookies = load_or_extract_cookies("ke.com")
        async with HttpClient(referer=referer) as client:
            resp = await client.get(url, cookies=cookies)

            # Save session cookies for future use
            if resp.cookies:
                new_cookies = {k: v for k, v in resp.cookies.items()}
                if new_cookies:
                    merged = {**cookies, **new_cookies}
                    save_cookies("ke.com", merged)

            html = resp.text

        if "CAPTCHA" in html or len(html) < 5000:
            raise RuntimeError(
                "ke.com returned CAPTCHA. Please visit ke.com in your browser first, "
                "then export cookies to ~/.config/house-cli/cookies.json"
            )

        return self._parse_list(html, filters.city)

    async def detail(self, house_id: str) -> HouseDetail:
        """Get house detail by ID. Requires valid browser cookies."""
        cookies = load_or_extract_cookies("ke.com")
        if not cookies:
            raise RuntimeError(
                "Detail pages require browser cookies. "
                "Please visit ke.com in your browser, then export cookies to "
                "~/.config/house-cli/cookies.json"
            )

        # Determine city from cookies or default to sh
        city_abbr = "sh"
        url = f"https://{city_abbr}.ke.com/ershoufang/{house_id}.html"
        referer = f"https://{city_abbr}.ke.com/ershoufang/"

        async with HttpClient(referer=referer) as client:
            resp = await client.get(url, cookies=cookies)
            html = resp.text

        if "CAPTCHA" in html or len(html) < 10000:
            raise RuntimeError(
                "ke.com returned CAPTCHA for detail page. "
                "Please refresh cookies in ~/.config/house-cli/cookies.json"
            )

        return self._parse_detail(html, house_id)

    async def get_price_history(self, house_id: str) -> list[dict]:
        """Get price history. Requires detail page data."""
        d = await self.detail(house_id)
        return d.price_history

    # ── HTML Parsing ────────────────────────────────────────────────

    def _parse_list(self, html: str, city: str) -> list[House]:
        """Parse the sellListContent HTML into House objects."""
        houses: list[House] = []

        # Split by listing card boundaries
        container_start = html.find('<ul class="sellListContent"')
        if container_start < 0:
            return houses

        container = html[container_start:]
        container_end = container.find("</ul>")
        if container_end > 0:
            container = container[:container_end]

        cards = container.split('<li class="clear">')

        for card in cards[1:]:  # skip first empty split
            try:
                h = self._parse_card(card, city)
                if h:
                    houses.append(h)
            except Exception:
                continue

        return houses

    def _parse_card(self, card: str, city: str) -> House | None:
        """Parse a single listing card HTML into a House."""
        # House ID and URL
        href_m = re.search(
            r'href="(https?://[^"]*?/ershoufang/(\d+)\.html)"', card
        )
        if not href_m:
            return None
        url = href_m.group(1)
        house_id = href_m.group(2)

        # Title
        title_m = re.search(
            r'class="VIEWDATA CLICKDATA maidian-detail"[^>]*>([^<]+)<', card
        )
        title = _clean(title_m.group(1)) if title_m else ""

        # Community
        comm_m = re.search(
            r'href="https?://[^"]*?/xiaoqu/\d+/">([^<]+)</a>', card
        )
        community = _clean(comm_m.group(1)) if comm_m else ""

        # Price
        price = 0.0
        price_m = re.search(
            r'class="totalPrice[^"]*">\s*(?:<i>)?.*?<span[^>]*>\s*([\d.]+)\s*</span>',
            card,
            re.DOTALL,
        )
        if price_m:
            try:
                price = float(price_m.group(1))
            except ValueError:
                pass

        # Unit price
        unit_price = None
        uprice_m = re.search(
            r'class="unitPrice"[^>]*>.*?<span>([^<]+)</span>', card, re.DOTALL
        )
        if uprice_m:
            raw = uprice_m.group(1).replace(",", "").replace("元/平", "")
            try:
                unit_price = float(raw)
            except ValueError:
                pass

        # House info: floor, year, layout, area, orientation
        floor = ""
        layout = ""
        area = 0.0
        orientation = ""
        building_year = ""

        info_m = re.search(
            r'class="houseInfo">(.*?)</div>', card, re.DOTALL
        )
        if info_m:
            info_text = _strip_tags(info_m.group(1))
            # Pattern: "高楼层 (共25层) | 2006年 | 1室2厅 | 73.67平米 | 东南"
            segments = [s.strip() for s in info_text.split("|")]
            for seg in segments:
                seg = seg.strip()
                if "楼层" in seg or "层" in seg:
                    floor = seg
                elif re.search(r"\d{4}年", seg):
                    building_year = seg
                elif "室" in seg or "厅" in seg or "房" in seg:
                    layout = seg
                elif "平米" in seg or "平" in seg:
                    area_m = re.search(r"([\d.]+)", seg)
                    if area_m:
                        area = float(area_m.group(1))
                elif seg and not any(c.isdigit() for c in seg):
                    # Likely orientation (南, 南北, 东南, etc.)
                    if len(seg) <= 4:
                        orientation = seg

        # District from image alt text: "title-上海静安南京西路二手房"
        district = ""
        alt_m = re.search(r'alt="[^"]*-[^"]*?(?:上海|北京|深圳|广州)(\S+?)二手房"', card)
        if alt_m:
            # alt contains "城市+区+商圈", e.g. "静安南京西路"
            raw_district = alt_m.group(1)
            # Known district names (2-3 chars) at the start
            for d in ["浦东", "闵行", "宝山", "徐汇", "普陀", "杨浦",
                       "长宁", "松江", "嘉定", "黄浦", "静安", "虹口",
                       "青浦", "奉贤", "金山", "崇明"]:
                if raw_district.startswith(d):
                    district = d
                    break
            if not district:
                district = raw_district

        # Tags
        tag_spans = re.findall(
            r'<span class="(?:subway|taxfree|isVrFutureHome|is_key|five|haskey'
            r'|VRFutureHome|goodhouse_tag)[^"]*"[^>]*>\s*([^<]+?)\s*</span>',
            card,
        )
        tags = [t.strip() for t in tag_spans if t.strip()]

        # Follow info for listing date
        listing_date = ""
        follow_m = re.search(
            r'class="followInfo">(.*?)</div>', card, re.DOTALL
        )
        if follow_m:
            follow_text = _strip_tags(follow_m.group(1))
            date_m = re.search(r"([\d]+[月天年前]+.*?发布)", follow_text)
            if date_m:
                listing_date = date_m.group(1).strip()

        return House(
            id=house_id,
            platform="beike",
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
            listing_date=listing_date,
            tags=tags,
        )

    def _parse_detail(self, html: str, house_id: str) -> HouseDetail:
        """Parse detail page HTML into HouseDetail.

        Detail page sections:
        - .overview: title, price, unit price, tags
        - .houseInfo: layout, floor, area, orientation, building type, etc.
        - .aroundInfo: subway, schools
        - .introduction: description
        - .baseinform: building year, elevator, parking, green ratio, etc.
        """
        # Title
        title_m = re.search(r'<h1[^>]*class="main"[^>]*>([^<]+)', html)
        if not title_m:
            title_m = re.search(r"<title>([^<]+)", html)
        title = _clean(title_m.group(1)) if title_m else ""

        # Total price
        price = 0.0
        price_m = re.search(
            r'class="total">\s*([\d.]+)\s*</span>', html
        )
        if not price_m:
            price_m = re.search(
                r'class="totalPrice[^"]*">\s*<span[^>]*>\s*([\d.]+)', html
            )
        if price_m:
            price = float(price_m.group(1))

        # Unit price
        unit_price = None
        up_m = re.search(r'class="unitPriceValue">\s*([\d,.]+)', html)
        if up_m:
            unit_price = float(up_m.group(1).replace(",", ""))

        # Basic info from .houseInfo or .base table
        area = 0.0
        layout = ""
        floor = ""
        orientation = ""
        building_type = ""
        building_year = ""
        elevator = ""

        # Parse info items: <span class="label">xxx</span><span>xxx</span>
        info_items = re.findall(
            r'<span class="label">\s*([^<]+)</span>\s*<span>\s*([^<]+)',
            html,
        )
        for label, value in info_items:
            label = label.strip()
            value = value.strip()
            if "面积" in label:
                m = re.search(r"([\d.]+)", value)
                if m:
                    area = float(m.group(1))
            elif "户型" in label:
                layout = value
            elif "楼层" in label or "所在楼层" in label:
                floor = value
            elif "朝向" in label:
                orientation = value
            elif "建筑" in label and "年" not in label:
                building_type = value
            elif "年代" in label or "建成" in label:
                building_year = value
            elif "电梯" in label:
                elevator = value

        # Community
        community = ""
        comm_m = re.search(
            r'class="communityName"[^>]*>.*?<a[^>]*>([^<]+)', html, re.DOTALL
        )
        if comm_m:
            community = _clean(comm_m.group(1))

        # District & address
        district = ""
        address = ""
        area_info = re.search(
            r'class="areaName"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        if area_info:
            links = re.findall(r">([^<]+)</a>", area_info.group(1))
            if links:
                district = links[0].strip()
            if len(links) > 1:
                address = " ".join(l.strip() for l in links)

        # URL
        url = f"https://sh.ke.com/ershoufang/{house_id}.html"

        # Nearby subway
        nearby_subway: list[str] = []
        subway_m = re.search(
            r'class="subwayInfo"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        if subway_m:
            subway_items = re.findall(r">([^<]+)</a>", subway_m.group(1))
            nearby_subway = [s.strip() for s in subway_items if s.strip()]

        # Nearby schools
        nearby_schools: list[str] = []
        school_section = re.search(
            r"学校|教育(.*?)</div>", html, re.DOTALL
        )
        if school_section:
            school_items = re.findall(r">([^<]+)</a>", school_section.group(1))
            nearby_schools = [s.strip() for s in school_items if s.strip()]

        # Description
        description = ""
        desc_m = re.search(
            r'class="introContent"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        if desc_m:
            description = _strip_tags(desc_m.group(1)).strip()[:500]

        # Property fee, green ratio, volume ratio, parking
        property_fee = ""
        green_ratio = ""
        volume_ratio = ""
        parking = ""

        base_items = re.findall(
            r'<span class="label">\s*([^<]+)</span>\s*(?:<span>)?\s*([^<]+)',
            html,
        )
        for label, value in base_items:
            label = label.strip()
            value = value.strip()
            if "物业费" in label:
                property_fee = value
            elif "绿化率" in label:
                green_ratio = value
            elif "容积率" in label:
                volume_ratio = value
            elif "车位" in label or "停车" in label:
                parking = value

        # Tags
        tags = re.findall(
            r'class="[^"]*tag[^"]*"[^>]*>\s*([^<]+?)\s*</span>', html
        )
        tags = [t.strip() for t in tags if t.strip() and len(t.strip()) < 20]

        # Price history from embedded JSON
        price_history: list[dict] = []
        ph_m = re.search(r"priceHistory\s*[:=]\s*(\[[^\]]*\])", html)
        if ph_m:
            import json
            try:
                price_history = json.loads(ph_m.group(1))
            except (json.JSONDecodeError, ValueError):
                pass

        # Images
        images: list[str] = []
        img_urls = re.findall(
            r'data-src="(https?://[^"]+(?:\.jpg|\.png|\.webp)[^"]*)"', html
        )
        images = img_urls[:10]

        return HouseDetail(
            id=house_id,
            platform="beike",
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
            url=url,
            listing_date="",
            tags=tags,
            description=description,
            building_year=building_year,
            building_type=building_type,
            elevator=elevator,
            parking=parking,
            green_ratio=green_ratio,
            volume_ratio=volume_ratio,
            property_fee=property_fee,
            nearby_schools=nearby_schools,
            nearby_subway=nearby_subway,
            price_history=price_history,
            images=images,
        )


def _clean(text: str) -> str:
    """Unescape HTML entities and strip whitespace."""
    return unescape(text).strip()


def _strip_tags(html: str) -> str:
    """Remove HTML tags, unescape entities, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
