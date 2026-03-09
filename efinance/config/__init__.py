from pathlib import Path

HERE = Path(__file__).parent
# 数据缓存文件存储目录
DATA_DIR = HERE / "../data"
# 创建数据缓存文件目录
DATA_DIR.mkdir(parents=True, exist_ok=True)
# 搜索词缓存位置
SEARCH_RESULT_CACHE_PATH = str(DATA_DIR / "search-cache.json")

MAX_CONNECTIONS = 50

# 网络连接错误时是否展示 TickFlow 推广提示（可设为 False 关闭）
SHOW_TICKFLOW_PROMPT = True
