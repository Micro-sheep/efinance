from .config import QUOTES_SAVE_PATH
import pandas as pd


def gen_secid(stock_code: str) -> str:
    """
    生成东方财富股票专用的 secid

    Parameters
    ----------
    stock_code : str
        6 位股票代码

    Returns
    -------
    str
        东方财富股票专用的 secid
    """

    _type = get_stock_market_type(stock_code, update=False)
    return f'{int(_type)}.{stock_code}'


def update_local_market_stocks_info(path: str = None) -> pd.DataFrame:
    """
    更新本地沪深基本情况表格文件

    Parameters
    ----------
    path : str, optional
        文件存储路径

    Returns
    -------
    DataFrame
    """
    if path is None:
        path = QUOTES_SAVE_PATH
    from . import get_realtime_quotes
    df = get_realtime_quotes()
    df.to_csv(QUOTES_SAVE_PATH, encoding='utf-8-sig', index=None)
    return df


def get_stock_market_type(stock_code: str, update=True) -> int:
    """
    根据股票代码获取其所属市场

    Parameters
    ----------
    stock_code : str
        [description]
    update : bool, optional
        [description], by default True

    Returns
    -------
    int
        0 表示深市股票
        1 表示沪市股票

    Raises
    ------
    KeyError
        当股票代码有误时
    """

    import os
    import pandas as pd
    from . import get_realtime_quotes
    if not os.path.exists(QUOTES_SAVE_PATH):

        df = get_realtime_quotes()
        df.to_csv(QUOTES_SAVE_PATH, encoding='utf-8-sig', index=None)

    elif update is False:
        import time
        if time.time() - os.path.getmtime(QUOTES_SAVE_PATH) >= 24*3600:
            df = get_realtime_quotes()
            df.to_csv(QUOTES_SAVE_PATH, encoding='utf-8-sig', index=None)
    else:
        update_local_market_stocks_info()
    df = pd.read_csv(QUOTES_SAVE_PATH, dtype={
        '股票代码': str
    })
    df.index = df['股票代码']
    if stock_code in df.index:
        return df.loc[stock_code, '沪/深']
    update_local_market_stocks_info()
    raise KeyError(
        f'股票代码 {stock_code} 可能有误 '
    )
