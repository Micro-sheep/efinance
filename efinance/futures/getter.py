from .utils import update_local_futures_info
from typing import Dict, List, Union
import pandas as pd
import requests
from urllib.parse import urlencode
import multitasking
from tqdm import tqdm
from .config import EastmoneyHeaders, EastmoneyKlines
from retry import retry


def get_futures_base_info() -> pd.DataFrame:
    """
    获取四个交易所全部期货基本信息

    Returns
    -------
    DataFrame
        四个交易所全部期货基本信息
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

    @retry(tries=tries)
    @multitasking.task
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
    Dict[str, pd.DataFrame]
        以 期货 secid 为 key，以 DataFrame 为值的 dict

    Returns
    -------
    pd.DataFrame
        [description]

    Raises
    ------
    TypeError
        当 secids 不符合类型要求时
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
