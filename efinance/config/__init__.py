# -*- coding: utf-8 -*-
import logging
import os
import sys
import time
import json
import uuid
import random
import requests
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


def get_cache_dir():
    """Resolve efinance cache directory from environment, in priority order:
    1. $EFINANCE_CACHE_DIR if set (user override)
    2. $XDG_CACHE_HOME/efinance
    3. <site-packages>/efinance/../data (legacy default)
    """
    override = os.environ.get("EFINANCE_CACHE_DIR", "").strip()
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg:
        return Path(xdg) / "efinance"
    return Path(__file__).parent / "../data"


DATA_DIR = get_cache_dir()
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logger.warning(
        "efinance cache dir %s not creatable (%s); "
        "downstream writes will surface a clear error",
        DATA_DIR, e,
    )

SEARCH_RESULT_CACHE_PATH = str(DATA_DIR / "search-cache.json")
MAX_CONNECTIONS = 50
SHOW_TICKFLOW_PROMPT = True


def get_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }


def sleep_time():
    return round(random.uniform(0.5, 1.5), 2)
