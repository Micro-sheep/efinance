from ..common.config import MARKET_NUMBER_DICT
from jsonpath import jsonpath
from retry import retry
from typing import Dict, List, Union
from tqdm import tqdm
import multitasking
import pandas as pd
from ..utils import to_numeric
from ..shared import session
from .config import (EASTMONEY_QUOTE_FIELDS,
                     EASTMONEY_REQUEST_HEADERS,
                     EASTMONEY_KLINE_FIELDS,
                     EASTMONEY_HISTORY_BILL_FIELDS)
from ..utils import get_quote_id


@to_numeric
def get_realtime_quotes_by_fs(fs: str) -> pd.DataFrame:
    """
    获取沪深市场最新行情总体情况

    Returns
    -------
    DataFrame
        沪深市场最新行情信息（涨跌幅、换手率等信息）

    """

    fields = ",".join(EASTMONEY_QUOTE_FIELDS.keys())
    params = (
        ('pn', '1'),
        ('pz', '1000000'),
        ('po', '1'),
        ('np', '1'),
        ('fltt', '2'),
        ('invt', '2'),
        ('fid', 'f3'),
        ('fs', fs),
        ('fields', fields)
    )
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    json_response = session.get(url,
                                headers=EASTMONEY_REQUEST_HEADERS,
                                params=params).json()
    df = pd.DataFrame(json_response['data']['diff'])
    df = df.rename(columns=EASTMONEY_QUOTE_FIELDS)
    df = df[EASTMONEY_QUOTE_FIELDS.values()]
    df['行情ID'] = df['市场编号'].astype(str)+'.'+df['代码'].astype('str')
    df['市场类型'] = df['市场编号'].astype(str).apply(
        lambda x: MARKET_NUMBER_DICT.get(x))

    return df


@to_numeric
def get_quote_history_single(code: str,
                             beg: str = '19000101',
                             end: str = '20500101',
                             klt: int = 101,
                             fqt: int = 1,
                             **kwargs) -> pd.DataFrame:
    """
    获取单只股票、债券 K 线数据

    """

    fields = list(EASTMONEY_KLINE_FIELDS.keys())
    columns = list(EASTMONEY_KLINE_FIELDS.values())
    fields2 = ",".join(fields)
    if kwargs.get('quote_id_mode'):
        quote_id = code
    else:
        quote_id = get_quote_id(code)
    params = (
        ('fields1', 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13'),
        ('fields2', fields2),
        ('beg', beg),
        ('end', end),
        ('rtntype', '6'),
        ('secid', quote_id),
        ('klt', f'{klt}'),
        ('fqt', f'{fqt}'),
    )

    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'

    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params).json()
    klines: List[str] = jsonpath(json_response, '$..klines[:]')
    if not klines:
        columns.insert(0, '代码')
        columns.insert(0, '名称')
        return pd.DataFrame(columns=columns)

    rows = [kline.split(',') for kline in klines]
    name = json_response['data']['name']
    code = quote_id.split('.')[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '代码', code)
    df.insert(0, '名称', name)

    return df


def get_quote_history_multi(codes: List[str],
                            beg: str = '19000101',
                            end: str = '20500101',
                            klt: int = 101,
                            fqt: int = 1,
                            tries: int = 3,
                            **kwargs
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
            **kwargs)
        dfs[code] = _df
        pbar.update(1)
        pbar.set_description_str(f'Processing => {code}')

    pbar = tqdm(total=total)
    for code in codes:
        start(code)
    multitasking.wait_for_tasks()
    pbar.close()
    return dfs


def get_quote_history(codes: Union[str, List[str]],
                      beg: str = '19000101',
                      end: str = '20500101',
                      klt: int = 101,
                      fqt: int = 1,
                      **kwargs) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
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

    Returns
    -------
    Union[DataFrame, Dict[str, DataFrame]]
        股票、债券的 K 线数据

        - ``DataFrame`` : 当 ``codes`` 是 ``str`` 时
        - ``Dict[str, DataFrame]`` : 当 ``codes`` 是 ``List[str]`` 时

    """

    if isinstance(codes, str):
        return get_quote_history_single(codes,
                                        beg=beg,
                                        end=end,
                                        klt=klt,
                                        fqt=fqt,
                                        **kwargs)

    elif hasattr(codes, '__iter__'):
        codes = list(codes)
        return get_quote_history_multi(codes,
                                       beg=beg,
                                       end=end,
                                       klt=klt,
                                       fqt=fqt,
                                       **kwargs)
    raise TypeError(
        '代码数据类型输入不正确！'
    )


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
        ('lmt', '100000'),
        ('klt', '101'),
        ('secid', quote_id),
        ('fields1', 'f1,f2,f3,f7'),
        ('fields2', fields2),

    )
    url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get'
    json_response = session.get(url,
                                headers=EASTMONEY_REQUEST_HEADERS,
                                params=params).json()

    klines: List[str] = jsonpath(json_response, '$..klines[:]')
    if not klines:
        columns.insert(0, '代码')
        columns.insert(0, '名称')
        return pd.DataFrame(columns=columns)
    rows = [kline.split(',') for kline in klines]
    name = jsonpath(json_response, '$..name')[0]
    code = quote_id.split('.')[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '代码', code)
    df.insert(0, '名称', name)

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
        ('lmt', '0'),
        ('klt', '1'),
        ('secid', quote_id),
        ('fields1', 'f1,f2,f3,f7'),
        ('fields2', 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63'),
    )
    url = 'http://push2.eastmoney.com/api/qt/stock/fflow/kline/get'
    json_response = session.get(url,
                                headers=EASTMONEY_REQUEST_HEADERS,
                                params=params).json()
    columns = ['时间', '主力净流入', '小单净流入', '中单净流入', '大单净流入', '超大单净流入']
    name = jsonpath(json_response, '$..name')[0]
    code = quote_id.split('.')[-1]
    klines: List[str] = jsonpath(json_response, '$..klines[:]')
    if not klines:
        columns.insert(0, '代码')
        columns.insert(0, '名称')
        return pd.DataFrame(columns=columns)
    rows = [kline.split(',') for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '代码', code)
    df.insert(0, '名称', name)
    return df
