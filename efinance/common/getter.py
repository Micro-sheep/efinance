from datetime import datetime
from typing import Dict, List, Union
import numpy as np
import multitasking
import pandas as pd
from jsonpath import jsonpath
from retry import retry
from tqdm.auto import tqdm
import time
from concurrent.futures import ThreadPoolExecutor

from ..common.config import MARKET_NUMBER_DICT, MarketType
from ..shared import BASE_INFO_CACHE, session, MAX_CONNECTIONS
from ..utils import get_quote_id, to_numeric
from .config import (
    EASTMONEY_BASE_INFO_FIELDS,
    EASTMONEY_HISTORY_BILL_FIELDS,
    EASTMONEY_KLINE_FIELDS,
    EASTMONEY_KLINE_NDAYS_FIELDS,
    EASTMONEY_QUOTE_FIELDS,
    EASTMONEY_REQUEST_HEADERS,
    MagicConfig,
)


@to_numeric
def get_realtime_quotes_by_fs(fs: str, **kwargs) -> pd.DataFrame:
    """
    获取沪深市场最新行情总体情况

    Returns
    -------
    DataFrame
        沪深市场最新行情信息（涨跌幅、换手率等信息）

    """

    columns = {**EASTMONEY_QUOTE_FIELDS, **kwargs.get(MagicConfig.EXTRA_FIELDS, {})}
    fields = ",".join(columns.keys())

    def get_by_page(pn: int, pz: int):
        params = (
            ("pn", pn),
            ("pz", pz),
            ("po", "1"),
            ("np", "1"),
            ("fltt", "2"),
            ("invt", "2"),
            # NOTE 按代码排序。避免多次请求顺序不一致
            ("fid", "f12"),
            ("fs", fs),
            ("fields", fields),
        )
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        json_response = session.get(
            url, headers=EASTMONEY_REQUEST_HEADERS, params=params
        ).json()
        return json_response

    def mixed_sort_key(series: pd.Series):
        sort_keys = pd.Series(index=series.index, dtype=float)

        for idx, val in series.items():
            if isinstance(val, str):
                sort_keys[idx] = np.nan
            else:
                sort_keys[idx] = val

        return sort_keys

    json_response = get_by_page(1, pz=200)
    total = json_response["data"]["total"]
    pz = len(json_response["data"]["diff"])
    div, mod = divmod(total, pz)
    pages = div + 1 if mod else div

    with ThreadPoolExecutor() as executor:
        tasks = executor.map(get_by_page, range(1, pages + 1), [pz] * pages)
        responses = list(tasks)

    dfs = [
        pd.DataFrame(response["data"]["diff"])[list(columns.keys())]
        for response in responses
    ]
    df = (
        pd.concat(dfs, axis=0, ignore_index=True)
        .rename(columns=columns)[columns.values()]
        .sort_values(
            by="涨跌幅",
            ascending=False,
            ignore_index=True,
            key=mixed_sort_key,
        )
    )

    df["行情ID"] = df["市场编号"].astype(str) + "." + df["代码"].astype(str)
    df["市场类型"] = (
        df["市场编号"].astype(str).apply(lambda x: MARKET_NUMBER_DICT.get(x))
    )
    df["更新时间"] = df["更新时间戳"].apply(lambda x: str(datetime.fromtimestamp(x)))
    df["最新交易日"] = pd.to_datetime(df["最新交易日"], format="%Y%m%d").astype(str)
    tmp = df["最新交易日"]
    del df["最新交易日"]
    df["最新交易日"] = tmp
    del df["更新时间戳"]
    return df


@to_numeric
def get_quote_history_single(
    code: str,
    beg: str = "19000101",
    end: str = "20500101",
    klt: int = 101,
    fqt: int = 1,
    market_type: Union[MarketType, None] = None,
    suppress_error: bool = False,
    use_id_cache: bool = True,
    **kwargs,
) -> pd.DataFrame:
    """
    获取单只股票、债券 K 线数据

    """

    fields = list(EASTMONEY_KLINE_FIELDS.keys())
    columns = list(EASTMONEY_KLINE_FIELDS.values())
    fields2 = ",".join(fields)
    if kwargs.get(MagicConfig.QUOTE_ID_MODE):
        quote_id = code
    else:
        quote_id = get_quote_id(
            stock_code=code,
            market_type=market_type,
            use_local=use_id_cache,
            suppress_error=suppress_error,
            **kwargs,
        )
    params = (
        ("fields1", "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"),
        ("fields2", fields2),
        ("beg", beg),
        ("end", end),
        ("rtntype", "6"),
        ("secid", quote_id),
        ("klt", f"{klt}"),
        ("fqt", f"{fqt}"),
    )

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params, verify=False
    ).json()
    klines: List[str] = jsonpath(json_response, "$..klines[:]")
    if not klines:
        columns.insert(0, "代码")
        columns.insert(0, "名称")
        return pd.DataFrame(columns=columns)

    rows = [kline.split(",") for kline in klines]
    name = json_response["data"]["name"]
    code = quote_id.split(".")[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, "代码", code)
    df.insert(0, "名称", name)

    return df


def get_quote_history_multi(
    codes: List[str],
    beg: str = "19000101",
    end: str = "20500101",
    klt: int = 101,
    fqt: int = 1,
    tries: int = 3,
    market_type: Union[MarketType, None] = None,
    suppress_error: bool = False,
    use_id_cache: bool = True,
    **kwargs,
) -> Dict[str, pd.DataFrame]:
    """
    获取多只股票、债券历史行情信息

    """

    dfs: Dict[str, pd.DataFrame] = {}
    total = len(codes)

    @multitasking.task
    @retry(tries=tries, delay=1)
    def start(code: str):
        _df = get_quote_history_single(
            code,
            beg=beg,
            end=end,
            klt=klt,
            fqt=fqt,
            market_type=market_type,
            suppress_error=suppress_error,
            use_id_cache=use_id_cache,
            **kwargs,
        )
        dfs[code] = _df
        pbar.update(1)
        pbar.set_description_str(f"Processing => {code}")

    pbar = tqdm(total=total)
    for code in codes:
        if len(multitasking.get_active_tasks()) > MAX_CONNECTIONS:
            time.sleep(3)
        start(code)

    multitasking.wait_for_tasks()
    pbar.close()

    if kwargs.get(MagicConfig.RETURN_DF):
        return pd.concat(dfs, axis=0, ignore_index=True)
    return dfs


def get_quote_history(
    codes: Union[str, List[str]],
    beg: str = "19000101",
    end: str = "20500101",
    klt: int = 101,
    fqt: int = 1,
    market_type: Union[MarketType, None] = None,
    suppress_error: bool = False,
    use_id_cache: bool = True,
    **kwargs,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    获取股票、ETF、债券的 K 线数据

    Parameters
    ----------
    codes : Union[str,List[str]]
        股票、债券代码 或者 代码构成的列表
    beg : str, optional
        开始日期，默认为 ``'19000101'`` ，表示 1900年1月1日
    end : str, optional
        结束日期，默认为 ``'20500101'`` ，表示 2050年1月1日
    klt : int, optional
        行情之间的时间间隔，默认为 ``101`` ，可选示例如下

        - ``1`` : 分钟
        - ``5`` : 5 分钟
        - ``15`` : 15 分钟
        - ``30`` : 30 分钟
        - ``60`` : 60 分钟
        - ``101`` : 日
        - ``102`` : 周
        - ``103`` : 月

    fqt : int, optional
        复权方式，默认为 ``1`` ，可选示例如下

        - ``0`` : 不复权
        - ``1`` : 前复权
        - ``2`` : 后复权

    market_type : MarketType, optional
        市场类型，目前可筛选A股，港股，美股和英股。默认不筛选，可选示例如下

        - ``A_stock`` : A股
        - ``Hongkong`` : 香港
        - ``London_stock_exchange`` : 英股
        - ``US_stock`` : 美股

    suppress_error : bool, optional
        遇到错误的股票代码，是否不报错，返回空的DataFrame
    use_id_cache : bool, optional
        是否使用本地缓存的东方财富股票行情ID

    Returns
    -------
    Union[DataFrame, Dict[str, DataFrame]]
        股票、债券的 K 线数据

        - ``DataFrame`` : 当 ``codes`` 是 ``str`` 时
        - ``Dict[str, DataFrame]`` : 当 ``codes`` 是 ``List[str]`` 时

    """

    if isinstance(codes, str):
        return get_quote_history_single(
            codes,
            beg=beg,
            end=end,
            klt=klt,
            fqt=fqt,
            market_type=market_type,
            suppress_error=suppress_error,
            use_id_cache=use_id_cache,
            **kwargs,
        )

    elif hasattr(codes, "__iter__"):
        codes = list(codes)
        return get_quote_history_multi(
            codes,
            beg=beg,
            end=end,
            klt=klt,
            fqt=fqt,
            market_type=market_type,
            suppress_error=suppress_error,
            use_id_cache=use_id_cache,
            **kwargs,
        )
    raise TypeError("代码数据类型输入不正确！")


@to_numeric
def get_history_bill(code: str) -> pd.DataFrame:
    """
    获取单支股票、债券的历史单子流入流出数据

    Parameters
    ----------
    code : str
        股票、债券代码

    Returns
    -------
    DataFrame
        沪深市场单只股票、债券历史单子流入流出数据

    """

    fields = list(EASTMONEY_HISTORY_BILL_FIELDS.keys())
    columns = list(EASTMONEY_HISTORY_BILL_FIELDS.values())
    fields2 = ",".join(fields)
    quote_id = get_quote_id(code)
    params = (
        ("lmt", "100000"),
        ("klt", "101"),
        ("secid", quote_id),
        ("fields1", "f1,f2,f3,f7"),
        ("fields2", fields2),
    )
    url = "http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params
    ).json()

    klines: List[str] = jsonpath(json_response, "$..klines[:]")
    if not klines:
        columns.insert(0, "代码")
        columns.insert(0, "名称")
        return pd.DataFrame(columns=columns)
    rows = [kline.split(",") for kline in klines]
    name = jsonpath(json_response, "$..name")[0]
    code = quote_id.split(".")[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, "代码", code)
    df.insert(0, "名称", name)

    return df


@to_numeric
def get_today_bill(code: str) -> pd.DataFrame:
    """
    获取单只股票最新交易日的日内分钟级单子流入流出数据

    Parameters
    ----------
    code : str
        股票、债券代码

    Returns
    -------
    DataFrame
        单只股票、债券最新交易日的日内分钟级单子流入流出数据

    """
    quote_id = get_quote_id(code)
    params = (
        ("lmt", "0"),
        ("klt", "1"),
        ("secid", quote_id),
        ("fields1", "f1,f2,f3,f7"),
        ("fields2", "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63"),
    )
    url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params
    ).json()
    columns = [
        "时间",
        "主力净流入",
        "小单净流入",
        "中单净流入",
        "大单净流入",
        "超大单净流入",
    ]
    name = jsonpath(json_response, "$..name")[0]
    code = quote_id.split(".")[-1]
    klines: List[str] = jsonpath(json_response, "$..klines[:]")
    if not klines:
        columns.insert(0, "代码")
        columns.insert(0, "名称")
        return pd.DataFrame(columns=columns)
    rows = [kline.split(",") for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, "代码", code)
    df.insert(0, "名称", name)
    return df


@to_numeric
def get_base_info(quote_id: str) -> pd.Series:

    fields = ",".join(EASTMONEY_BASE_INFO_FIELDS.keys())
    params = (
        ("ut", "fa5fd1943c7b386f172d6893dbfba10b"),
        ("invt", "2"),
        ("fltt", "2"),
        ("fields", fields),
        ("secid", quote_id),
    )
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params
    ).json()
    items = json_response["data"]
    if not items:
        return pd.Series(index=EASTMONEY_BASE_INFO_FIELDS.values(), dtype="object")

    s = pd.Series(items, dtype="object").rename(index=EASTMONEY_BASE_INFO_FIELDS)
    return s


@to_numeric
def get_deal_detail(quote_id: str, max_count: int = 1000000) -> pd.DataFrame:
    """
    获取股票、期货、债券的最新交易日成交情况

    Parameters
    ----------
    quote_id : str
        包含市场编号的股票、期货、债券代码
    max_count : int, optional
        最大数据条数, 默认为 ``1000000``

    Returns
    -------
    DataFrame
        股票、期货、债券的最新交易日成交情况

    Notes
    ------
    返回的数据表头: ``['名称', '代码', '时间', '昨收', '成交价', '成交量', '单数']``
    """
    base_info = BASE_INFO_CACHE.get(quote_id, get_base_info(quote_id))
    BASE_INFO_CACHE[quote_id] = base_info
    columns = ["名称", "代码", "时间", "昨收", "成交价", "成交量", "单数"]
    if str(base_info["代码"]).lower() == "nan":
        return pd.DataFrame(columns=columns)
    code = base_info["代码"]
    name = base_info["名称"]
    params = (
        ("secid", quote_id),
        ("fields1", "f1,f2,f3,f4,f5"),
        ("fields2", "f51,f52,f53,f54,f55"),
        ("pos", f"-{int(max_count)}"),
    )

    response = session.get(
        "https://push2.eastmoney.com/api/qt/stock/details/get", params=params
    )

    js: dict = response.json()
    lines: List[str] = js["data"]["details"]
    rows = [line.split(",")[:4] for line in lines]
    df = pd.DataFrame(columns=columns, index=range(len(rows)))
    df.loc[:, "代码"] = code
    df.loc[:, "名称"] = name
    detail_df = pd.DataFrame(rows, columns=["时间", "成交价", "成交量", "单数"])
    detail_df.insert(1, "昨收", js["data"]["prePrice"])
    df.loc[:, detail_df.columns] = detail_df.values
    return df


@to_numeric
def get_latest_quote(quote_id_list: Union[str, List[str]], **kwargs) -> pd.DataFrame:
    """
    获取股票、期货、债券的最新行情

    Parameters
    ----------
    quote_id_list : List[str]
        带市场编号的行情ID或者行情ID组成的列表格式如下
        -  ``'1.600159'``
        - ``['1.600159','0.300750']``

        市场编号参见文件 ``efinance/common/config.py`` 中的 ``MARKET_NUMBER_DICT``

    Returns
    -------
    DataFrame
        股票、期货、债券的最新行情

    Notes
    ------
    返回的数据表头: ``['代码', '名称', '涨跌幅', '最新价', '最高', '最低', '今开', '涨跌额', '换手率', '量比', '动态市盈率','成交量', '成交额', '昨日收盘', '总市值', '流通市值', '市场类型', '行情ID']``
    """
    if isinstance(quote_id_list, str):
        quote_id_list = [quote_id_list]
    secids: List[str] = quote_id_list

    columns = {**EASTMONEY_QUOTE_FIELDS, **kwargs.get(MagicConfig.EXTRA_FIELDS, {})}
    fields = ",".join(columns.keys())
    params = (
        ("OSVersion", "14.3"),
        ("appVersion", "6.3.8"),
        ("fields", fields),
        ("fltt", "2"),
        ("plat", "Iphone"),
        ("product", "EFund"),
        ("secids", ",".join(secids)),
        ("serverVersion", "6.3.6"),
        ("version", "6.3.8"),
    )
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params
    ).json()
    rows = jsonpath(json_response, "$..diff[:]")
    if not rows:
        df = pd.DataFrame(columns=columns.values())
    else:
        df = pd.DataFrame(rows)[list(columns.keys())].rename(columns=columns)
    df["市场类型"] = df["市场编号"].apply(lambda x: MARKET_NUMBER_DICT.get(str(x)))
    df["行情ID"] = df["市场编号"].astype(str) + "." + df["代码"].astype(str)
    del df["市场编号"]
    df["更新时间"] = df["更新时间戳"].apply(lambda x: str(datetime.fromtimestamp(x)))
    df["最新交易日"] = pd.to_datetime(df["最新交易日"], format="%Y%m%d").astype(str)
    tmp = df["最新交易日"]
    del df["最新交易日"]
    df["最新交易日"] = tmp
    del df["更新时间戳"]
    return df


@to_numeric
def get_latest_ndays_quote(code: str, ndays: int = 1, **kwargs) -> pd.DataFrame:
    """
    获取股票、期货、债券的最近 ``ndays`` 天的1分钟K线行情

    Parameters
    ----------
    code : str
        代码、名称或者行情ID 如果是行情ID则需传入 ``quote_id_mode=True``
    ndays : int, optional
        天数 默认为 ``1`` 最大为 ``5``

    Returns
    -------
    DataFrame
        股票、期货、债券的最近 ndays 天的1分钟K线行情
    """
    # TODO 考虑如何解决 ndays 不为 1 时，第一天开盘价为 0 的问题
    fields = list(EASTMONEY_KLINE_NDAYS_FIELDS.keys())
    columns = list(EASTMONEY_KLINE_NDAYS_FIELDS.values())
    fields2 = ",".join(fields)
    if kwargs.get(MagicConfig.QUOTE_ID_MODE):
        quote_id = code
    else:
        quote_id = get_quote_id(code)
    params = (
        ("fields1", "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"),
        ("fields2", fields2),
        ("ndays", ndays),
        ("iscr", "0"),
        ("iscca", "0"),
        ("secid", quote_id),
    )

    json_response = session.get(
        "http://push2his.eastmoney.com/api/qt/stock/trends2/get", params=params
    ).json()

    klines: List[str] = jsonpath(json_response, "$..trends[:]")
    if not klines:
        columns.insert(0, "代码")
        columns.insert(0, "名称")
        return pd.DataFrame(columns=columns)

    rows = [kline.split(",") for kline in klines]
    name = json_response["data"]["name"]
    code = quote_id.split(".")[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, "代码", code)
    df.insert(0, "名称", name)

    return df
