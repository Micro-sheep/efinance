from pathlib import Path
HERE = Path(__file__).parent
DATA_DIR = HERE/'../data'
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

# 各个市场编号
MARKET_NUMBER_DICT = {
    '0': '深A',
    '1': '沪A',
    '105': '美股',
    '116': '港股'
}
# 搜索词缓存位置
SEARCH_RESULT_CACHE_PATH = str(DATA_DIR/'search-cache.json')

FS_DICT = {
    'bond': 'b:MK0354',
    'stock': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',
}
