from .config import FUTURES_BASE_INFO_SAVE_PATH


def update_local_futures_info(path: str = FUTURES_BASE_INFO_SAVE_PATH) -> None:
    from .getter import get_futures_base_info
    df = get_futures_base_info()
    df.to_csv(path,
              encoding='utf-8-sig',
              index=None)
