from pathlib import Path
import os

HERE = Path(__file__).parent
# 数据缓存文件存储目录
# 优先使用环境变量 EFINANCE_DATA_DIR 设置的路径，如未设置则使用默认路径
DATA_DIR = Path(os.environ.get('EFINANCE_DATA_DIR', HERE / "../data"))
# 创建数据缓存文件目录
DATA_DIR.mkdir(parents=True, exist_ok=True)
# 搜索词缓存位置
SEARCH_RESULT_CACHE_PATH = str(DATA_DIR / "search-cache.json")

MAX_CONNECTIONS = 50
