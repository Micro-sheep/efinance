from pathlib import Path
HERE = Path(__file__).parent
# K 线表头
EASTMONEY_KLINE_FIELDS = {
    'f51': '日期',
    'f52': '开盘',
    'f53': '收盘',
    'f54': '最高',
    'f55': '最低',
    'f56': '成交量',
    'f57': '成交额',
    'f58': '振幅',
    'f59': '涨跌幅',
    'f60': '涨跌额',
    'f61': '换手率',
}

# 请求头
EASTMONEY_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Referer': 'http://quote.eastmoney.com/center/gridlist.html',
}

# 债券实时行情表头
EASTMONEY_BOND_QUOTE_FIELDS = {
    'f12': '债券代码',
    'f14': '债券名称',
    'f13': '市场编号',
    'f3': '涨跌幅',
    'f2': '最新价',
    'f15': '最高',
    'f16':'最低',
    'f4': '涨跌额',
    'f8': '换手率',
    'f9': '动态市盈率',
    'f5': '成交量',
    'f6': '成交额',
    'f18': '昨日收盘',
    'f20': '总市值',
    'f21': '流通市值'
}
EASTMONEY_BOND_BASE_INFO_FIELDS = {
    'SECURITY_CODE': '债券代码',
    'SECURITY_NAME_ABBR': '债券名称',
    'CONVERT_STOCK_CODE': '正股代码',
    'SECURITY_SHORT_NAME': '正股名称',
    'RATING': '债券评级',
    'PUBLIC_START_DATE': '申购日期',
    'ACTUAL_ISSUE_SCALE': '发行规模(亿)',
    'ONLINE_GENERAL_LWR': '网上发行中签率(%)',
    'LISTING_DATE': '上市日期',
    'EXPIRE_DATE': '到期日期',
    'BOND_EXPIRE': '期限(年)',
    'INTEREST_RATE_EXPLAIN': '利率说明'

}
