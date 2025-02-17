import enum
from pathlib import Path

HERE = Path(__file__).parent


class MarketType(enum.Enum):
    A_stock = "AStock"  # A股
    A_stock_index = "Index"  # A股指数
    B_stock = "BStock"  # B股
    index = "Index"  # 沪深京指数
    STAR_market = "23"  # 科创板
    CSI_free_float = "24"  # 中证系列指数
    NEEQ = "NEEQ"  # 京A，新三板（全国中小企业股份转让系统）
    BK = "BK"  # 板块
    Hongkong = "HK"  # 港股
    US_stock = "UsStock"  # 美股
    London_stock = "LSE"  # 英股
    London_stock_IOB = "LSEIOB"  # 伦敦交易所国际挂盘册
    universal_index = "UniversalIndex"  # 国外指数
    SIX_Swiss = "SIX"  # SIX瑞士股市

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class MagicConfig:
    EXTRA_FIELDS = "extra_fields"
    QUOTE_ID_MODE = "quote_id_mode"
    QUOTE_SYMBOL_MODE = "quote_symbol_mode"
    RETURN_DF = "return_df"


# 各个市场编号
MARKET_NUMBER_DICT = {
    "0": "深A",
    "1": "沪A",
    "105": "美股",
    "106": "美股",
    "107": "美股",
    "116": "港股",
    "128": "港股",
    "113": "上期所",
    "114": "大商所",
    "115": "郑商所",
    "8": "中金所",
    "142": "上海能源期货交易所",
    "155": "英股",
    "90": "板块",
    "225": "广期所",
}
# ! Powerful
FS_DICT = {
    # 可转债
    "bond": "b:MK0354",
    "可转债": "b:MK0354",
    "stock": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
    # 沪深A股
    # 'stock': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
    "沪深A股": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
    "沪深京A股": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
    "北证A股": "m:0 t:81 s:2048",
    "北A": "m:0 t:81 s:2048",
    # 期货
    "futures": "m:113,m:114,m:115,m:8,m:142,m:225",
    "期货": "m:113,m:114,m:115,m:8,m:142,m:225",
    "上证A股": "m:1 t:2,m:1 t:23",
    "沪A": "m:1 t:2,m:1 t:23",
    "深证A股": "m:0 t:6,m:0 t:80",
    "深A": "m:0 t:6,m:0 t:80",
    # 沪深新股
    "新股": "m:0 f:8,m:1 f:8",
    "创业板": "m:0 t:80",
    "科创板": "m:1 t:23",
    "沪股通": "b:BK0707",
    "深股通": "b:BK0804",
    "风险警示板": "m:0 f:4,m:1 f:4",
    "两网及退市": "m:0 s:3",
    # 板块
    "地域板块": "m:90 t:1 f:!50",
    "行业板块": "m:90 t:2 f:!50",
    "概念板块": "m:90 t:3 f:!50",
    # 指数
    "上证系列指数": "m:1 s:2",
    "深证系列指数": "m:0 t:5",
    "沪深系列指数": "m:1 s:2,m:0 t:5",
    # ETF 基金
    "ETF": "b:MK0021,b:MK0022,b:MK0023,b:MK0024",
    # LOF 基金
    "LOF": "b:MK0404,b:MK0405,b:MK0406,b:MK0407",
    "美股": "m:105,m:106,m:107",
    "港股": "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
    "英股": "m:155 t:1,m:155 t:2,m:155 t:3,m:156 t:1,m:156 t:2,m:156 t:5,m:156 t:6,m:156 t:7,m:156 t:8",
    "中概股": "b:MK0201",
    "中国概念股": "b:MK0201",
}

# 股票、ETF、债券 K 线表头
EASTMONEY_KLINE_FIELDS = {
    "f51": "日期",
    "f52": "开盘",
    "f53": "收盘",
    "f54": "最高",
    "f55": "最低",
    "f56": "成交量",
    "f57": "成交额",
    "f58": "振幅",
    "f59": "涨跌幅",
    "f60": "涨跌额",
    "f61": "换手率",
}
# 股票、ETF、债券 近 n 天 1 分钟 K 线表头
EASTMONEY_KLINE_NDAYS_FIELDS = {
    "f51": "日期",
    "f52": "开盘",
    "f53": "收盘",
    "f54": "最高",
    "f55": "最低",
    "f56": "成交量",
    "f57": "成交额",
}
# 股票、债券榜单表头
EASTMONEY_QUOTE_FIELDS = {
    "f12": "代码",
    "f14": "名称",
    "f3": "涨跌幅",
    "f2": "最新价",
    "f15": "最高",
    "f16": "最低",
    "f17": "今开",
    "f4": "涨跌额",
    "f8": "换手率",
    "f10": "量比",
    "f9": "动态市盈率",
    "f5": "成交量",
    "f6": "成交额",
    "f18": "昨日收盘",
    "f20": "总市值",
    "f21": "流通市值",
    "f13": "市场编号",
    "f124": "更新时间戳",
    "f297": "最新交易日",
}

# 股票、债券历史大单数据表头
EASTMONEY_HISTORY_BILL_FIELDS = {
    "f51": "日期",
    "f52": "主力净流入",
    "f53": "小单净流入",
    "f54": "中单净流入",
    "f55": "大单净流入",
    "f56": "超大单净流入",
    "f57": "主力净流入占比",
    "f58": "小单流入净占比",
    "f59": "中单流入净占比",
    "f60": "大单流入净占比",
    "f61": "超大单流入净占比",
    "f62": "收盘价",
    "f63": "涨跌幅",
}
# 请求头
EASTMONEY_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    # 'Referer': 'http://quote.eastmoney.com/center/gridlist.html',
}

EASTMONEY_BASE_INFO_FIELDS = {
    "f57": "代码",
    "f58": "名称",
    "f162": "市盈率(动)",
    "f167": "市净率",
    "f127": "所处行业",
    "f116": "总市值",
    "f117": "流通市值",
    "f198": "板块编号",
    "f173": "ROE",
    "f187": "净利率",
    "f105": "净利润",
    "f186": "毛利率",
}
