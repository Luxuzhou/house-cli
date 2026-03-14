"""City and district mappings for all supported platforms.

Shared across adapters — each platform may use a subset of these mappings.
District slugs vary by platform; this module provides a base Chinese-name mapping.
"""

# ── Major cities: Chinese name → common pinyin abbreviation ──────────
# Used by ke.com, fang.com, anjuke, etc. as city subdomains
CITY_ABBR: dict[str, str] = {
    # Tier-1
    "北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz",
    # New Tier-1
    "成都": "cd", "杭州": "hz", "重庆": "cq", "武汉": "wh",
    "苏州": "su", "南京": "nj", "天津": "tj", "西安": "xa",
    "长沙": "cs", "郑州": "zz", "东莞": "dg", "青岛": "qd",
    "合肥": "hf", "佛山": "fs", "宁波": "nb", "昆明": "km",
    "沈阳": "sy", "大连": "dl",
    # Tier-2
    "厦门": "xm", "济南": "jn", "无锡": "wx", "福州": "fz",
    "哈尔滨": "hrb", "石家庄": "sjz", "烟台": "yt", "珠海": "zh",
    "惠州": "hui", "中山": "zs", "太原": "ty", "南昌": "nc",
    "贵阳": "gy", "南宁": "nn", "温州": "wz", "常州": "cz",
    "徐州": "xz", "兰州": "lz", "绍兴": "sx", "嘉兴": "jx",
}

# ── District mappings per city ───────────────────────────────────────
# Key = city Chinese name, Value = {district Chinese name: pinyin slug}
# These slugs are used by ke.com and fang.com; other platforms may differ.

DISTRICTS: dict[str, dict[str, str]] = {
    "北京": {
        "东城": "dongcheng", "西城": "xicheng", "朝阳": "chaoyang",
        "海淀": "haidian", "丰台": "fengtai", "石景山": "shijingshan",
        "通州": "tongzhou", "顺义": "shunyi", "房山": "fangshan",
        "大兴": "daxing", "昌平": "changping", "门头沟": "mentougou",
        "怀柔": "huairou", "平谷": "pinggu", "密云": "miyun",
        "延庆": "yanqing", "亦庄开发区": "yizhuangkaifaqu",
    },
    "上海": {
        "浦东": "pudong", "闵行": "minhang", "宝山": "baoshan",
        "徐汇": "xuhui", "普陀": "putuo", "杨浦": "yangpu",
        "长宁": "changning", "松江": "songjiang", "嘉定": "jiading",
        "黄浦": "huangpu", "静安": "jingan", "虹口": "hongkou",
        "青浦": "qingpu", "奉贤": "fengxian", "金山": "jinshan",
        "崇明": "chongming",
    },
    "广州": {
        "天河": "tianhe", "越秀": "yuexiu", "海珠": "haizhu",
        "荔湾": "liwan", "白云": "baiyun", "番禺": "panyu",
        "黄埔": "huangpu", "花都": "huadu", "增城": "zengcheng",
        "从化": "conghua", "南沙": "nansha",
    },
    "深圳": {
        "福田": "futian", "南山": "nanshan", "罗湖": "luohu",
        "宝安": "baoan", "龙岗": "longgang", "龙华": "longhua",
        "光明": "guangming", "坪山": "pingshan", "盐田": "yantian",
        "大鹏": "dapeng",
    },
    "杭州": {
        "上城": "shangcheng", "拱墅": "gongshu", "西湖": "xihu",
        "滨江": "binjiang", "萧山": "xiaoshan", "余杭": "yuhang",
        "临平": "linping", "钱塘": "qiantang", "富阳": "fuyang",
        "临安": "linan",
    },
    "成都": {
        "锦江": "jinjiang", "青羊": "qingyang", "金牛": "jinniu",
        "武侯": "wuhou", "成华": "chenghua", "龙泉驿": "longquanyi",
        "青白江": "qingbaijiang", "新都": "xindu", "温江": "wenjiang",
        "双流": "shuangliu", "郫都": "pidu", "天府新区": "tianfuxinqu",
        "高新区": "gaoxinqu",
    },
    "南京": {
        "玄武": "xuanwu", "秦淮": "qinhuai", "建邺": "jianye",
        "鼓楼": "gulou", "栖霞": "qixia", "雨花台": "yuhuatai",
        "江宁": "jiangning", "浦口": "pukou", "六合": "luhe",
        "溧水": "lishui", "高淳": "gaochun",
    },
    "武汉": {
        "江岸": "jiangan", "江汉": "jianghan", "硚口": "qiaokou",
        "汉阳": "hanyang", "武昌": "wuchang", "青山": "qingshan",
        "洪山": "hongshan", "东西湖": "dongxihu", "汉南": "hannan",
        "蔡甸": "caidan", "江夏": "jiangxia", "黄陂": "huangpi",
        "新洲": "xinzhou", "光谷": "guanggu",
    },
    "重庆": {
        "渝中": "yuzhong", "江北": "jiangbei", "南岸": "nanan",
        "沙坪坝": "shapingba", "九龙坡": "jiulongpo", "大渡口": "dadukou",
        "渝北": "yubei", "巴南": "banan", "北碚": "beibei",
        "两江新区": "liangjiangxinqu",
    },
    "天津": {
        "和平": "heping", "河东": "hedong", "河西": "hexi",
        "南开": "nankai", "河北": "hebei", "红桥": "hongqiao",
        "滨海新区": "binhaixinqu", "东丽": "dongli", "西青": "xiqing",
        "津南": "jinnan", "北辰": "beichen", "武清": "wuqing",
    },
    "苏州": {
        "姑苏": "gusu", "虎丘": "huqiu", "吴中": "wuzhong",
        "相城": "xiangcheng", "吴江": "wujiang", "工业园区": "gongyeyuanqu",
        "高新区": "gaoxinqu", "昆山": "kunshan", "太仓": "taicang",
        "常熟": "changshu", "张家港": "zhangjiagang",
    },
    "西安": {
        "雁塔": "yanta", "碑林": "beilin", "莲湖": "lianhu",
        "新城": "xincheng", "未央": "weiyang", "灞桥": "baqiao",
        "长安": "changan", "高新区": "gaoxinqu", "曲江": "qujiang",
        "浐灞": "chanba",
    },
}


def get_city_abbr(city: str) -> str:
    """Get city abbreviation, fallback to 'sh'."""
    return CITY_ABBR.get(city, "sh")


def get_district_slug(city: str, district: str) -> str:
    """Get district slug for a city. Returns empty string if not found."""
    return DISTRICTS.get(city, {}).get(district, "")


def get_district_names(city: str) -> list[str]:
    """Get list of district names for a city."""
    return list(DISTRICTS.get(city, {}).keys())
