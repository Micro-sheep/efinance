from urllib.parse import urlencode
import pandas as pd
import requests
from .utils import gen_secid, threadmethod
from queue import Queue
from typing import List, Union, Dict
from .config import EastmoneyKlines, EastmoneyHeaders, EastmoneyRank, EastmoneyBills

def get_k_history(stock_code: str, beg: str = '19000101', end: str = '20500101', klt: int = 101, fqt: int = 1) -> pd.DataFrame:
    '''
    获取k线数据

    Parameters
    ----------
    stock_code : 6 位股票代码
    beg : 开始日期 例如 20200101
    end : 结束日期 例如 20200201
    klt : k线间距 默认为 101 即日k
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt: 复权方式
            不复权 : 0
            前复权 : 1
            后复权 : 2 

    Return
    ------
    DateFrame : 包含股票k线数据

    '''

    fields = list(EastmoneyKlines.keys())
    columns = list(EastmoneyKlines.values())
    fields2 = ",".join(fields)
    secid = gen_secid(stock_code)
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
    data = json_response.get('data')
    if data is None:
        return pd.DataFrame(columns=columns)
    # code = data['code']
    # 股票名称
    # name = data['name']
    klines = data['klines']

    rows = []
    for _kline in klines:

        kline = _kline.split(',')
        rows.append(kline)

    df = pd.DataFrame(rows, columns=columns)
    df.insert(0,'股票代码',[stock_code for _ in range(len(df))])
    return df


def get_k_historys(stock_codes: Union[str, List[str]],  beg: str = '19000101', end: str = '20500101', klt: int = 101, fqt: int = 1) -> Dict[str,pd.DataFrame]:
    '''
    获取k线数据

    Parameters
    ----------
    stock_code : 6 位股票代码 或者多个代码构成的列表
    beg : 开始日期 例如 20200101
    end : 结束日期 例如 20200201
    klt : k线间距 默认为 101 即日k
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt: 复权方式
            不复权 : 0
            前复权 : 1
            后复权 : 2 

    Return
    ------
    DateFrame : 包含股票k线数据
    Dict[stock_code,DataFrame] : 包含股票k线数据 的 DataFrame 字典

    '''
    if isinstance(stock_codes, str):
        df = get_k_history(
            stock_codes, beg=beg, end=end, klt=klt, fqt=fqt)

        return df

    Q = Queue()
    for stock_code in stock_codes:

        Q.put(stock_code) 
    dfs = {}
    @threadmethod
    def start():
        while not Q.empty():
            stock_code = Q.get()
            try:
                _df = get_k_history(stock_code, beg, end)
                _df.insert(0,'股票代码',[stock_code for _ in range(len(df))])
                dfs[stock_code] = _df

            except:
                Q.put(stock_code)

    start()
    return dfs


def get_real_rank() -> pd.DataFrame:
    '''
    获取实时排行榜

    Parameters
    ----------
    无

    Return
    ------
    DataFrame : 包含 A 股市场全部股票的当日实时涨跌情况
    '''
    fields = ",".join(EastmoneyRank.keys())
    columns = list(EastmoneyRank.values())
    params = (
        ('pn', '1'),
        ('pz', '200000'),
        ('po', '1'),
        ('np', '1'),
        ('fltt', '2'),
        ('invt', '2'),
        ('fid', 'f3'),
        ('fs', 'm:0 t:6,m:0 t:13,m:0 t:80,m:1 t:2,m:1 t:23'),
        ('fields', fields),
    )

    json_response = requests.get(
        'http://19.push2.eastmoney.com/api/qt/clist/get', headers=EastmoneyHeaders, params=params).json()

    data = json_response.get('data')
    if data is None:
        return pd.DataFrame(columns=columns)

    rows = data['diff']
    df = pd.DataFrame(rows).rename(columns=EastmoneyRank)
    return df


def get_history_bill(stock_code: str) -> pd.DataFrame:
    '''


    Parameters
    ----------
    code: 6 位股票代码

    Return
    ------
    DataFrame : 包含指定股票的历史单子数据

    '''

    fields = list(EastmoneyBills.keys())
    columns = list(EastmoneyBills.values())
    fields2 = ",".join(fields)
    secid = gen_secid(stock_code)
    params = (
        ('lmt', '100000'),
        ('klt', '101'),
        ('secid', secid),
        ('fields1', 'f1,f2,f3,f7'),
        ('fields2', fields2),

    )

    json_response = requests.get('http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get',
                                 headers=EastmoneyHeaders, params=params).json()

    data = json_response.get('data')
    if data is None:
        return pd.DataFrame(columns=columns)
    klines = data['klines']
    rows = []
    for _kline in klines:
        kline = _kline.split(',')
        rows.append(kline)
    df = pd.DataFrame(rows, columns=columns)

    return df


def get_today_bill(stock_code: str) -> pd.DataFrame:
    '''
    获取超大单 大单 主力流入数据
    Parameters
    ----------
    stock_code : 6 位股票代码

    Return
    ------
    DataFrame : 包含指定股票全部日单子数据

    '''
    params = (
        ('lmt', '0'),
        ('klt', '1'),
        ('secid', gen_secid(stock_code)),
        ('fields1', 'f1,f2,f3,f7'),
        ('fields2', 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63'),
        ('ut', 'b2884a393a59ad64002292a3e90d46a5'),
    )

    json_response = requests.get('http://push2.eastmoney.com/api/qt/stock/fflow/kline/get',
                                 headers=EastmoneyHeaders, params=params).json()
    data = json_response['data']

    klines = data['klines']
    columns = ['时间', '主力净流入', '小单净流入', '中单净流入', '大单净流入', '超大单净流入']
    rows = []
    for _kline in klines:
        kline = _kline.split(',')
        rows.append(kline)
    df = pd.DataFrame(rows, columns=columns)
    return df


def get_latest_stock_info(stock_codes: List[str]) -> pd.DataFrame:
    '''
    Parameters
    ----------
    stock_codes 多只股票代码列表

    Return
    ------   
    DataFrame : 多只股票涨跌情况
    '''
    secids = ",".join([gen_secid(code) for code in stock_codes])
    params = (
        ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('OSVersion', '14.3'),
        ('appVersion', '6.3.8'),
        ('cToken', 'a6hdhrfejje88ruaeduau1rdufna1e--.6'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('fields', 'f1,f2,f3,f4,f12,f13,f14,f292'),
        ('fltt', '2'),
        ('passportid', '3061335960830820'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('secids', secids),
        ('serverVersion', '6.3.6'),
        ('uToken', 'a166hhqnrajucnfcjkfkeducanekj1dd1cc2a-e9.6'),
        ('userId', 'f8d95b2330d84d9e804e7f28a802d809'),
        ('ut', '94dd9fba6f4581ffc558a7b1a7c2b8a3'),
        ('version', '6.3.8'),
    )

    response = requests.get(
        'https://push2.eastmoney.com/api/qt/ulist.np/get', headers=EastmoneyHeaders, params=params)
    columns = {
        'f2': '最新价',
        'f3': '最新涨跌幅',
        'f12': '股票代码',
        'f14': '股票简称'
    }
    data = response.json()['data']
    if data is None:

        return pd.DataFrame(columns=columns.values())
    diff = data['diff']
    df = pd.DataFrame(diff)[columns.keys()].rename(columns=columns)
    return df
