from pathlib import Path
HERE = Path(__file__).parent
DATA_DIR = HERE/'../data'
if not DATA_DIR.exists():
    DATA_DIR.mkdir()
# 各个市场编号
MARET_NUMBER_DICT = {
    '0': '深A',
    '1': '沪A',
    '105': '美股',
    '116': '港股'

}
# 搜索词缓存位置
SEARCH_RESULT_CACHE_PATH = str(DATA_DIR/'search-cache.json')
