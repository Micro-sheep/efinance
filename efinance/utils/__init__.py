import json
import re
import time
from collections import OrderedDict, namedtuple
from functools import wraps
from typing import Any, Callable, Dict, List, TypeVar, Union

import pandas as pd
import rich
from retry.api import retry

from ..common.config import FS_DICT, MARKET_NUMBER_DICT, MagicConfig, MarketType
from ..config import SEARCH_RESULT_CACHE_PATH
from ..shared import SEARCH_RESULT_DICT, session

# 函数变量
F = TypeVar("F")


def to_numeric(func: F) -> F:
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

    ignore = [
        "股票代码",
        "基金代码",
        "代码",
        "市场类型",
        "市场编号",
        "债券代码",
        "行情ID",
        "正股代码",
    ]

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
        if not re.findall("\d", str(o)):
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
Quote = namedtuple(
    "Quote",
    [
        "code",
        "name",
        "pinyin",
        "id",
        "jys",
        "classify",
        "market_type",
        "security_typeName",
        "security_type",
        "mkt_num",
        "type_us",
        "quote_id",
        "unified_code",
        "inner_code",
    ],
)


@retry(tries=3, delay=1)
def get_quote_id(
    stock_code: str,
    market_type: Union[MarketType, None] = None,
    use_local=True,
    suppress_error=False,
    **kwargs,
) -> str:
    """
    生成东方财富股票专用的行情ID

    Parameters
    ----------
    stock_code : str
        证券代码或者证券名称
    market_type : MarketType, optional
        市场类型，目前可筛选A股，港股，美股和英股。默认不筛选
    use_local : bool, optional
        是否使用本地缓存
    suppress_error : bool, optional
        遇到错误的股票代码，是否不报错，返回空字符串

    Returns
    -------
    str
        东方财富股票专用的 secid
    """
    if len(str(stock_code).strip()) == 0:
        if suppress_error:
            return ""
        raise Exception("证券代码应为长度不应为 0")
    quote = search_quote(
        stock_code, market_type=market_type, use_local=use_local, **kwargs
    )
    if isinstance(quote, Quote):
        return quote.quote_id
    if quote is None:
        if not suppress_error:
            rich.print(f'证券代码 "{stock_code}" 可能有误')
        return ""


def search_quote(
    keyword: str,
    market_type: Union[MarketType, None] = None,
    count: int = 1,
    use_local: bool = True,
    **kwargs,
) -> Union[Quote, None, List[Quote]]:
    """
    根据关键词搜索以获取证券信息

    Parameters
    ----------
    keyword : str
        搜索词(股票代码、债券代码甚至证券名称都可以)
    market_type : MarketType, optional
        市场类型，目前可筛选A股，港股，美股和英股。默认不筛选
    count : int, optional
        最多搜索结果数, 默认为 `1`
    use_local : bool, optional
        是否使用本地缓存

    Returns
    -------
    Union[Quote, None, List[Quote]]

    """
    # NOTE 本地仅存储第一个搜索结果
    if use_local and count == 1:
        quote = search_quote_locally(keyword, market_type=market_type)
        if quote:
            return quote
    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = (
        ("input", f"{keyword}"),
        ("type", "14"),
        ("token", "D43BF722C8E33BDC906FB84D85E326E8"),
        ("count", f"{max(count, 5)}"),
    )
    try:
        json_response = session.get(url, params=params).json()
        items = json_response["QuotationCodeTable"]["Data"]
    except json.JSONDecodeError:
        RuntimeWarning(
            "unable to parse search quote result, consider if you are blocked"
        )
        return None

    if items is not None and items:
        quotes = [
            Quote(*item.values())
            for item in items
            # 支持精确查找股票代码
            if (
                not kwargs.get(MagicConfig.QUOTE_SYMBOL_MODE, False)
                or (keyword == item["Code"])
            )
            # 支持筛选股票市场
            and (market_type is None or (market_type.value == item["Classify"]))
        ]
        # NOTE 暂时仅存储第一个搜索结果
        save_search_result(keyword, quotes[:1])
        if count == 1:
            return quotes[0] if len(quotes) >= 1 else None

        return quotes[:count]

    return None


def search_quote_locally(
    keyword: str, market_type: Union[MarketType, None] = None
) -> Union[Quote, None]:
    """
    在本地里面使用搜索记录进行关键词搜索

    Parameters
    ----------
    keyword : str
        搜索词
    market_type : MarketType, optional
        市场类型，目前可筛选A股，港股，美股和英股。默认不筛选

    Returns
    -------
    Union[Quote,None]

    """
    q = SEARCH_RESULT_DICT.get(keyword)
    # NOTE 兼容旧版本 给缓存加上最后修改时间
    if (
        q is None
        or not q.get("last_time")
        or (
            isinstance(market_type, MarketType)
            and (q.get("classify")) != (market_type.value)
        )
    ):
        return None

    last_time: float = q["last_time"]
    # 缓存过期秒数
    max_ts = 3600 * 24 * 3
    now = time.time()
    # 缓存过期，在线搜索
    if (now - last_time) > max_ts:
        return None
    # NOTE 一定要拷贝 否则改变源对象
    _q = q.copy()
    # NOTE 一定要删除它 否则会构造错误
    del _q["last_time"]
    quote = Quote(**_q)
    return quote


def save_search_result(keyword: str, quotes: List[Quote]):
    """
    存储搜索结果到文件中

    Parameters
    ----------
    keyword : str
        搜索词
    quotes : List[Quote]
        搜索结果
    """
    with open(SEARCH_RESULT_CACHE_PATH, "w", encoding="utf-8") as f:
        # TODO考虑如何存储多个搜索结果
        for quote in quotes:
            now = time.time()
            d = dict(quote._asdict())
            d["last_time"] = now
            SEARCH_RESULT_DICT[keyword] = d
            break
        json.dump(SEARCH_RESULT_DICT.copy(), f)


def rename_dataframe_and_series(
    fields: dict, to_be_removed: List[str] = [], keep_all: bool = True
):
    """
    重命名 DataFrame 和 Series 的列名的装饰器

    Parameters
    ----------
    fields : dict
        新的表头
    to_be_removed : List[str], optional
        要移除的列, by default []
    keep_all : bool, optional
        是否保存全部列(包含未重命名的列), by default True
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            values = func(*args, **kwargs)
            if isinstance(values, pd.DataFrame):
                columns = list(fields.values())
                if keep_all:
                    for column in values.columns:
                        if column not in columns:
                            columns.append(column)
                    values = values.rename(columns=fields)[columns]
                else:
                    values = values.rename(columns=fields)[columns]
                for column in values:
                    if column in to_be_removed:
                        del values[column]
            elif isinstance(values, pd.Series):
                values = values.rename(fields)

            return values

        return wrapper

    return decorator


def process_dataframe_and_series(
    function_fields: Dict[str, Callable] = dict(),
    remove_columns_and_indexes: List[str] = list(),
):
    """
    对 DataFrame 和 Series 进一步操作

    Parameters
    ----------
    function_fields : Dict[str, Callable], optional
        函数字典
    remove_columns_and_indexes : List[str], optional
        需要删除的行或者列, by default list()
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            values = func(*args, **kwargs)
            if isinstance(values, pd.DataFrame):
                for column, function_name in function_fields.items():
                    if column not in values.columns:
                        continue
                    values[column] = values[column].apply(function_name)
                for column in remove_columns_and_indexes:
                    if column in values.columns:
                        del values[column]
            elif isinstance(values, pd.Series):
                for index in remove_columns_and_indexes:
                    values = values.drop(index)
            return values

        return wrapper

    return decorator


T = TypeVar("T")


def to_type(f: Callable[[str], T], value: Any, default: T = None) -> T:
    """
    类型转换

    Parameters
    ----------
    f : Callable[[str], T]
        转换函数
    value : Any
        待转换的值

    default : T, optional
        转换失败时的返回值, 默认为  ``None`` 表示原样返回

    Returns
    -------
    T
        转换结果
    """
    try:
        value = f(value)
        return value
    except:
        if default is None:
            return value
        return default


def add_market(
    category: str, market_number: str, market_name: str, drop_duplicate: bool = True
) -> None:
    """
    添加市场

    Parameters
    ----------
    category : str
        市场类别
    market_number : str
        市场编号
    market_name : str
        市场名称
    drop_duplicate : bool, optional
        是否去重, 默认为 ``True``
    """
    MARKET_NUMBER_DICT[market_number] = market_name
    old = FS_DICT.get(category, "")
    new = f"{old},m:{market_number}"
    if drop_duplicate:
        FS_DICT[category] = ",".join(OrderedDict.fromkeys(new.split(",")))
    else:
        FS_DICT[category] = new


__all__ = []
