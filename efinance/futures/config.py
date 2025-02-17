from pathlib import Path

HERE = Path(__file__).parent
FUTURES_BASE_INFO_SAVE_PATH = HERE / "futures_info.csv"
# K 线表头映射
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

EASTMONEY_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
    "Referer": "http://quote.eastmoney.com/center/gridlist.html",
}
