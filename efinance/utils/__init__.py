import json
import re
from typing import Union, List
from functools import wraps
import pandas as pd
from collections import namedtuple
from retry.api import retry
from ..config import SEARCH_RESULT_CACHE_PATH
from ..shared import (SEARCH_RESULT_DICT,
                      session)


def to_numeric(func):
    """
    将 DataFrame 或者 Series 尽可能地转为数字的装饰器

    Parameters
    ----------
    func : Callable
        返回结果为 DataFrame 或者 Series 的函数

    Returns
    -------
    Union[DataFrame, Series]

    """

    ignore = ['股票代码', '基金代码', '代码', '市场类型', '市场编号', '债券代码']

    @wraps(func)
    def run(*args, **kwargs):
        values = func(*args, **kwargs)
        if isinstance(values, pd.DataFrame):
            for column in values.columns:
                if column not in ignore:

                    values[column] = values[column].apply(convert)
        elif isinstance(values, pd.Series):
            for index in values.index:
                if index not in ignore:

                    values[index] = convert(values[index])
        return values

    def convert(o: Union[str, int, float]) -> Union[str, float, int]:
        if not re.findall('\d', str(o)):
            return o
        try:
            if str(o).isalnum():
                o = int(o)
            else:
                o = float(o)
        except:
            pass
        return o
    return run


# 存储证券代码的实体
Quote = namedtuple('Quote', ['code', 'name', 'pinyin', 'id', 'jys', 'classify', 'market_type',
                   'security_typeName', 'security_type', 'mkt_num', 'type_us', 'quote_id', 'unified_code', 'inner_code'])


@retry(tries=3, delay=1)
def get_quote_id(stock_code: str) -> str:
    """
    生成东方财富股票专用的行情ID

    Parameters
    ----------
    stock_code : str
        证券代码或者证券名称

    Returns
    -------
    str
        东方财富股票专用的 secid
    """
    if len(str(stock_code).strip()) == 0:
        raise Exception('证券代码应为长度不应为 0')
    quote = search_quote(stock_code)
    if isinstance(quote, Quote):
        return quote.quote_id
    if quote is None:
        raise Exception(f'证券代码 {stock_code} 可能有误')


def search_quote(keyword: str,
                 count: int = 1) -> Union[Quote, None, List[Quote]]:
    """
    根据关键词搜索以获取证券信息

    Parameters
    ----------
    keyword : str
        搜索词(股票代码、债券代码甚至证券名称都可以)
    count : int, optional
        最多搜索结果数, by default 1

    Returns
    -------
    Union[Quote, None, List[Quote]]

    """
    quote = search_quote_locally(keyword)
    if quote:
        return quote
    url = 'https://searchapi.eastmoney.com/api/suggest/get'
    params = (
        ('input', f'{keyword}'),
        ('type', '14'),
        ('token', 'D43BF722C8E33BDC906FB84D85E326E8'),
        ('count', f'{count}'))
    json_response = session.get(url, params=params).json()
    items = json_response['QuotationCodeTable']['Data']
    if items is not None:
        quotes = [Quote(*item.values()) for item in items]
        save_search_result(keyword, quotes)
        if count == 1:
            return quotes[0]
        return quotes
    return None


def search_quote_locally(keyword: str) -> Union[Quote, None]:
    """
    在本地里面使用搜索记录进行关键词搜索

    Parameters
    ----------
    keyword : str
        搜索词

    Returns
    -------
    Union[Quote,None]

    """
    q = SEARCH_RESULT_DICT.get(keyword)
    if q is None:
        return None
    quote = Quote(**q)
    return quote


def save_search_result(keyword: str, quotes: List[Quote]):
    with open(SEARCH_RESULT_CACHE_PATH, 'w', encoding='utf-8') as f:
        for quote in quotes:
            SEARCH_RESULT_DICT[keyword] = quote._asdict()
        json.dump(SEARCH_RESULT_DICT.copy(), f)


__all__ = []
