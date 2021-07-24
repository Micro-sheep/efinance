from .utils import update_local_futures_info
from typing import Dict, List, Union
import pandas as pd
import requests
from urllib.parse import urlencode
import multitasking
from tqdm import tqdm
from .config import EastmoneyHeaders, EastmoneyKlines
from retry import retry
from ..utils import to_numeric


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
        期货代码      期货名称       secid 归属交易所
    0       ZCM     动力煤主力     115.ZCM   郑商所
    1     ZC109    动力煤109   115.ZC109   郑商所
    2       bum    石油沥青主力     113.bum   上期所
    3    bu2109  石油沥青2109  113.bu2109   上期所
    4    bu2203  石油沥青2203  113.bu2203   上期所
    ..      ...       ...         ...   ...
    781   p2204   棕榈油2204   114.p2204   大商所
    782   p2203   棕榈油2203   114.p2203   大商所
    783   p2110   棕榈油2110   114.p2110   大商所
    784      pm     棕榈油主力      114.pm   大商所
    785   p2109   棕榈油2109   114.p2109   大商所
    [786 rows x 4 columns]
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
        'https://push2.eastmoney.com/api/qt/clist/get', headers=EastmoneyHeaders, params=params)
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

    fields = list(EastmoneyKlines.keys())
    columns = list(EastmoneyKlines.values())
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
        url, headers=EastmoneyHeaders).json()

    data = json_response['data']
    if data is None:
        print(secid, '无数据')
        return None
    # code = data['code']
    # name = data['name']
    klines = data['klines']

    rows = []
    for _kline in klines:

        kline = _kline.split(',')
        rows.append(kline)

    df = pd.DataFrame(rows, columns=columns)

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
    if total != 0:
        update_local_futures_info()

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
        日期     开盘     收盘     最高     最低     成交量            成交额    振幅    涨跌幅    涨跌额   换手率
    0     2015-05-18  440.0  437.6  440.2  437.6      64      2806300.0  0.00   0.00    0.0  0.00
    1     2015-05-19  436.0  437.0  437.6  436.0       6       262100.0  0.36  -0.32   -1.4  0.00
    2     2015-05-20  436.8  435.8  437.0  434.8       8       348750.0  0.50  -0.23   -1.0  0.00
    3     2015-05-21  438.0  443.2  446.8  437.8      37      1631850.0  2.06   1.65    7.2  0.00
    4     2015-05-22  439.2  441.4  443.8  439.2      34      1502500.0  1.04   0.09    0.4  0.00
    ...          ...    ...    ...    ...    ...     ...            ...   ...    ...    ...   ...
    1475  2021-06-08  800.2  819.2  821.0  791.0  201763  16270168320.0  3.72   1.56   12.6  0.00
    1476  2021-06-09  822.4  818.2  832.2  816.0  193464  15925956608.0  2.01   1.46   11.8  0.00
    1477  2021-06-10  818.0  803.4  828.4  801.2  168933  13805204736.0  3.30  -2.41  -19.8  0.00
    1478  2021-06-11  807.0  827.2  833.0  805.8  207762  16999086848.0  3.33   1.22   10.0  0.00
    1479  2021-06-15  847.0  849.2  853.6  830.0  140166  11827207168.0  2.88   3.79   31.0  0.00
    [1480 rows x 11 columns]
    >>> # 指定多个期货的 secid
    >>> secids = ['115.ZCM','115.ZC109']
    >>> ef.futures.get_quote_history(secids)
    {'115.ZCM':               日期     开盘     收盘     最高     最低     成交量            成交额    振幅    涨跌幅    涨跌额   换手率
    0     2015-05-18  440.0  437.6  440.2  437.6      64      2806300.0  0.00   0.00    0.0  0.00
    1     2015-05-19  436.0  437.0  437.6  436.0       6       262100.0  0.36  -0.32   -1.4  0.00
    2     2015-05-20  436.8  435.8  437.0  434.8       8       348750.0  0.50  -0.23   -1.0  0.00
    3     2015-05-21  438.0  443.2  446.8  437.8      37      1631850.0  2.06   1.65    7.2  0.00
    4     2015-05-22  439.2  441.4  443.8  439.2      34      1502500.0  1.04   0.09    0.4  0.00
    ...          ...    ...    ...    ...    ...     ...            ...   ...    ...    ...   ...
    1475  2021-06-08  800.2  819.2  821.0  791.0  201763  16270168320.0  3.72   1.56   12.6  0.00
    1476  2021-06-09  822.4  818.2  832.2  816.0  193464  15925956608.0  2.01   1.46   11.8  0.00
    1477  2021-06-10  818.0  803.4  828.4  801.2  168933  13805204736.0  3.30  -2.41  -19.8  0.00
    1478  2021-06-11  807.0  827.2  833.0  805.8  207762  16999086848.0  3.33   1.22   10.0  0.00
    1479  2021-06-15  847.0  849.2  853.6  830.0  140166  11827207168.0  2.88   3.79   31.0  0.00
    [1480 rows x 11 columns],
    '115.ZC109':              日期     开盘     收盘     最高     最低     成交量            成交额    振幅    涨跌幅    涨跌额   换手率
    0    2020-09-09  551.2  551.2  551.2  551.2       2       110240.0  0.00   0.00    0.0  0.00
    1    2020-09-10  548.6  545.0  549.8  545.0       6       328920.0  0.87  -1.12   -6.2  0.00
    2    2020-09-11  545.0  544.2  548.4  543.0       7       381500.0  0.99  -0.73   -4.0  0.00
    3    2020-09-14  546.0  550.4  550.4  546.0       7       384300.0  0.81   0.99    5.4  0.00
    4    2020-09-15  549.0  551.2  551.6  549.0      14       770560.0  0.47   0.40    2.2  0.00
    ..          ...    ...    ...    ...    ...     ...            ...   ...    ...    ...   ...
    178  2021-06-08  800.2  819.2  821.0  791.0  201763  16270168320.0  3.72   1.56   12.6  0.00
    179  2021-06-09  822.4  818.2  832.2  816.0  193464  15925956608.0  2.01   1.46   11.8  0.00
    180  2021-06-10  818.0  803.4  828.4  801.2  168933  13805204736.0  3.30  -2.41  -19.8  0.00
    181  2021-06-11  807.0  827.2  833.0  805.8  207762  16999086848.0  3.33   1.22   10.0  0.00
    182  2021-06-15  847.0  849.2  853.6  830.0  140166  11827207168.0  2.88   3.79   31.0  0.00
    [183 rows x 11 columns]}
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
