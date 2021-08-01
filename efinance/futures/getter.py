from typing import Dict, List, Union
import pandas as pd
import requests
from urllib.parse import urlencode
import multitasking
from tqdm import tqdm
from retry import retry
from jsonpath import jsonpath
from ..utils import to_numeric
from .config import (EASTMONEY_REQUEST_HEADERS,
                     EASTMONEY_KLINE_FIELDS)


def get_futures_base_info() -> pd.DataFrame:
    """
    获取四个交易所全部期货基本信息

    Returns
    -------
    DataFrame
        四个交易所全部期货基本信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.futures.get_futures_base_info()
        期货代码     期货名称       secid 归属交易所
    0       jmm     焦煤主力     114.jmm   大商所
    1    jm2109   焦煤2109  114.jm2109   大商所
    2    ss2204  不锈钢2204  113.ss2204   上期所
    3    jm2110   焦煤2110  114.jm2110   大商所
    4    jm2108   焦煤2108  114.jm2108   大商所
    ..      ...      ...         ...   ...
    782   i2204  铁矿石2204   114.i2204   大商所
    783   i2112  铁矿石2112   114.i2112   大商所
    784   i2203  铁矿石2203   114.i2203   大商所
    785      im    铁矿石主力      114.im   大商所
    786   i2109  铁矿石2109   114.i2109   大商所

    """

    params = (
        ('np', '1'),
        ('fltt', '2'),
        ('invt', '2'),
        ('fields', 'f1,f2,f3,f4,f12,f13,f14'),
        ('pn', '1'),
        ('pz', '300000'),
        ('fid', 'f3'),
        ('po', '1'),
        ('fs', 'm:113,m:114,m:115,m:8'),
        ('forcect', '1'),
    )
    rows = []
    cfg = {
        113: '上期所',
        114: '大商所',
        115: '郑商所',
        8: '中金所'
    }
    response = requests.get(
        'https://push2.eastmoney.com/api/qt/clist/get', headers=EASTMONEY_REQUEST_HEADERS, params=params)
    for item in response.json()['data']['diff']:
        code = item['f12']
        name = item['f14']
        secid = str(item['f13'])+'.'+code
        belong = cfg[item['f13']]
        row = [code, name, secid, belong]
        rows.append(row)
    columns = ['期货代码', '期货名称', 'secid', '归属交易所']
    df = pd.DataFrame(rows, columns=columns)
    return df


@to_numeric
def get_quote_history_single(secid: str,
                             beg: str = '19000101',
                             end: str = '20500101',
                             klt: int = 101,
                             fqt: int = 1) -> pd.DataFrame:
    """
    获取期货历史行情信息

    Parameters
    ----------
    secid : str
        根据 efinance.Futures.get_futures_base_info 函数获取
    beg : str, optional
        开始日期，默认为 '19000101'，表示 1900年1月1日
    end : str, optional
        结束日期，默认为 '20500101'，表示 2050年1月1日
    klt : int, optional
        行情之间的时间间隔
        可选示例如下
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt : int, optional
        复权方式，默认为 1
        可选示例如下
            不复权 : 0
            前复权 : 1
            后复权 : 2 

    Returns
    -------
    DataFrame
        指定日期区间的期货历史行情信息
    """

    fields = list(EASTMONEY_KLINE_FIELDS.keys())
    columns = list(EASTMONEY_KLINE_FIELDS.values())
    fields2 = ",".join(fields)

    params = (
        ('fields1', 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13'),
        ('fields2', fields2),
        ('beg', beg),
        ('end', end),
        ('rtntype', '6'),
        ('secid', secid),
        ('klt', f'{klt}'),
        ('fqt', f'{fqt}'),
    )
    base_url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    url = base_url+'?'+urlencode(params)
    json_response = requests.get(
        url, headers=EASTMONEY_REQUEST_HEADERS).json()
    klines: List[str] = jsonpath(json_response, '$..klines[:]')
    if not klines:
        columns.insert(0, '期货代码')
        columns.insert(0, '期货名称')
        return pd.DataFrame(columns=columns)
    code = json_response['data']['code']
    name = json_response['data']['name']
    rows = [kline.split(',') for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '期货代码', [code for _ in range(len(df))])
    df.insert(0, '期货名称', [name for _ in range(len(df))])
    return df


def get_quote_history_multi(secids: List[str],
                            beg: str = '19000101',
                            end: str = '20500101',
                            klt: int = 101,
                            fqt: int = 1,
                            tries: int = 3) -> Dict[str, pd.DataFrame]:
    """
    获取多个期货历史行情信息

    Parameters
    ----------
    secids : List[str]
        多个 期货 secid 列表
    beg : str, optional
        开始日期，默认为 '19000101'，表示 1900年1月1日
    end : str, optional
        结束日期，默认为 '20500101'，表示 2050年1月1日
    klt : int, optional
        行情之间的时间间隔
        可选示例如下
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt : int, optional
        复权方式，默认为 1
        可选示例如下
            不复权 : 0
            前复权 : 1
            后复权 : 2 
    tries : int, optional
        单个线程出错时重试次数, 默认为  3

    Returns
    -------
    Dict[str, pd.DataFrame]
        以 期货 secid 为 key，以 DataFrame 为值的 dict
    """

    dfs: Dict[str, pd.DataFrame] = {}
    total = len(secids)

    @multitasking.task
    @retry(tries=3, delay=1)
    def start(stock_code: str):
        _df = get_quote_history_single(
            stock_code, beg=beg, end=end, klt=klt, fqt=fqt)
        dfs[stock_code] = _df
        pbar.update(1)
        pbar.set_description_str(f'Processing: {stock_code}')

    pbar = tqdm(total=total)
    for stock_code in secids:
        start(stock_code)
    multitasking.wait_for_tasks()
    pbar.close()
    return dfs


def get_quote_history(secids: Union[str, List[str]],
                      beg: str = '19000101',
                      end: str = '20500101',
                      klt: int = 101,
                      fqt: int = 1) -> pd.DataFrame:
    """
    获取期货历史行情信息

    Parameters
    ----------
    secids : Union[str, List[str]]
        一个期货 secid，或者多个期货 secid构成的列表
    beg : str, optional
        开始日期，默认为 '19000101'，表示 1900年1月1日
    end : str, optional
        结束日期，默认为 '20500101'，表示 2050年1月1日
    klt : int, optional
        行情之间的时间间隔
        可选示例如下
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt : int, optional
        复权方式，默认为 1
        可选示例如下
            不复权 : 0
            前复权 : 1
            后复权 : 2 
    tries : int, optional
        单个线程出错时重试次数, 默认为  3

    Returns
    -------
    Dict[str, DataFrame]
        以 期货 secid 为 key，以 DataFrame 为值的 dict

    Returns
    -------
    DataFrame

    Raises
    ------
    TypeError
        当 secids 不符合类型要求时
    Examples
    --------
    >>> import efinance as ef
    >>> # 指定单个期货的 secid
    >>> secid = '115.ZCM'
    >>> ef.futures.get_quote_history(secid)
        期货名称 期货代码          日期     开盘     收盘     最高     最低     成交量           成交额    振幅   涨跌幅   涨跌额  换手率
    0     动力煤主力  ZCM  2015-05-18  440.0  437.6  440.2  437.6      64  2.806300e+06  0.00  0.00   0.0  0.0
    1     动力煤主力  ZCM  2015-05-19  436.0  437.0  437.6  436.0       6  2.621000e+05  0.36 -0.32  -1.4  0.0
    2     动力煤主力  ZCM  2015-05-20  436.8  435.8  437.0  434.8       8  3.487500e+05  0.50 -0.23  -1.0  0.0
    3     动力煤主力  ZCM  2015-05-21  438.0  443.2  446.8  437.8      37  1.631850e+06  2.06  1.65   7.2  0.0
    4     动力煤主力  ZCM  2015-05-22  439.2  441.4  443.8  439.2      34  1.502500e+06  1.04  0.09   0.4  0.0
    ...     ...  ...         ...    ...    ...    ...    ...     ...           ...   ...   ...   ...  ...
    1509  动力煤主力  ZCM  2021-07-27  897.0  892.4  915.8  888.0  109033  9.802067e+09  3.10 -0.53  -4.8  0.0
    1510  动力煤主力  ZCM  2021-07-28  892.4  902.4  909.6  890.4   89853  8.086770e+09  2.14  0.38   3.4  0.0
    1511  动力煤主力  ZCM  2021-07-29  902.6  918.6  919.0  900.4   83106  7.562646e+09  2.07  2.07  18.6  0.0
    1512  动力煤主力  ZCM  2021-07-30  918.6  927.2  943.0  906.2  129862  1.202003e+10  4.04  1.89  17.2  0.0
    1513  动力煤主力  ZCM  2021-08-02  898.0  870.0  898.0  852.4  101722  8.900675e+09  4.93 -6.01 -55.6  0.0

    >>> # 指定多个期货的 secid
    >>> secids = ['115.ZCM','115.ZC109']
    >>> futures_df = ef.futures.get_quote_history(secids)
    >>> type(futures_df)
    <class 'dict'>
    >>> futures_df.keys()
    dict_keys(['115.ZC109', '115.ZCM'])
    >>> futures_df['115.ZC109']
        期货名称   期货代码          日期     开盘     收盘     最高     最低     成交量           成交额    振幅   涨跌幅   涨跌额  换手率
    0    动力煤109  ZC109  2020-09-09  551.2  551.2  551.2  551.2       2  1.102400e+05  0.00  0.00   0.0  0.0
    1    动力煤109  ZC109  2020-09-10  548.6  545.0  549.8  545.0       6  3.289200e+05  0.87 -1.12  -6.2  0.0
    2    动力煤109  ZC109  2020-09-11  545.0  544.2  548.4  543.0       7  3.815000e+05  0.99 -0.73  -4.0  0.0
    3    动力煤109  ZC109  2020-09-14  546.0  550.4  550.4  546.0       7  3.843000e+05  0.81  0.99   5.4  0.0
    4    动力煤109  ZC109  2020-09-15  549.0  551.2  551.6  549.0      14  7.705600e+05  0.47  0.40   2.2  0.0
    ..      ...    ...         ...    ...    ...    ...    ...     ...           ...   ...   ...   ...  ...
    212  动力煤109  ZC109  2021-07-27  897.0  892.4  915.8  888.0  109033  9.802067e+09  3.10 -0.53  -4.8  0.0
    213  动力煤109  ZC109  2021-07-28  892.4  902.4  909.6  890.4   89853  8.086770e+09  2.14  0.38   3.4  0.0
    214  动力煤109  ZC109  2021-07-29  902.6  918.6  919.0  900.4   83106  7.562646e+09  2.07  2.07  18.6  0.0
    215  动力煤109  ZC109  2021-07-30  918.6  927.2  943.0  906.2  129862  1.202003e+10  4.04  1.89  17.2  0.0
    216  动力煤109  ZC109  2021-08-02  898.0  870.0  898.0  852.4  101722  8.900675e+09  4.93 -6.01 -55.6  0.0

    """

    if isinstance(secids, str):
        return get_quote_history_single(secids, beg=beg, end=end, klt=klt, fqt=fqt)
    elif hasattr(secids, '__iter__'):
        secids = list(secids)
        return get_quote_history_multi(secids, beg=beg, end=end, klt=klt, fqt=fqt)
    else:
        raise TypeError(
            '期货 secid 类型输入不正确！'
        )
