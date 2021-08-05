from typing import Dict
from ..config import SEARCH_RESULT_CACHE_PATH
from pathlib import Path
import requests
import json
session = requests.Session()
SEARCH_RESULT_DICT: Dict[str, dict] = dict()
path = Path(SEARCH_RESULT_CACHE_PATH)
if path.exists():
    load_success = False
    with path.open('r', encoding='utf-8') as f:
        try:
            SEARCH_RESULT_DICT = json.load(f)
            load_success = True
        except:
            pass
    if not load_success:
        path.open('w').close()
