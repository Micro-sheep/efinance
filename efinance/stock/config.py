from pathlib import Path

HERE = Path(__file__).parent

# 股票基本信息表头
EASTMONEY_STOCK_BASE_INFO_FIELDS = {
    "f57": "股票代码",
    "f58": "股票名称",
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

EASTMONEY_STOCK_DAILY_BILL_BOARD_FIELDS = {
    "SECURITY_CODE": "股票代码",
    "SECURITY_NAME_ABBR": "股票名称",
    "TRADE_DATE": "上榜日期",
    "EXPLAIN": "解读",
    "CLOSE_PRICE": "收盘价",
    "CHANGE_RATE": "涨跌幅",
    "TURNOVERRATE": "换手率",
    "BILLBOARD_NET_AMT": "龙虎榜净买额",
    "BILLBOARD_BUY_AMT": "龙虎榜买入额",
    "BILLBOARD_SELL_AMT": "龙虎榜卖出额",
    "BILLBOARD_DEAL_AMT": "龙虎榜成交额",
    "ACCUM_AMOUNT": "市场总成交额",
    "DEAL_NET_RATIO": "净买额占总成交比",
    "DEAL_AMOUNT_RATIO": "成交额占总成交比",
    "FREE_MARKET_CAP": "流通市值",
    "EXPLANATION": "上榜原因",
}
