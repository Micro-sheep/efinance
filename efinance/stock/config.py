from pathlib import Path
HERE = Path(__file__).parent

# 股票基本信息表头
EASTMONEY_STOCK_BASE_INFO_FIELDS = {
    'f57': '股票代码',
    'f58': '股票名称',
    'f162': '市盈率(动)',
    'f167': '市净率',
    'f127': '所处行业',
    'f116': '总市值',
    'f117': '流通市值',
    'f198': '板块编号',
    'f173': 'ROE',
    'f187': '净利率',
    'f105': '净利润',
    'f186': '毛利率'

}
