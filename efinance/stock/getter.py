from typing import Dict, List, Union
from retry import retry
import pandas as pd
import requests
import multitasking
import signal
from tqdm import tqdm
from ..utils import to_numeric, get_quote_id
from ..config import MARET_NUMBER_DICT
from .config import (EASTMONEY_KLINE_FIELDS,
                     EASTMONEY_REQUEST_HEADERS,
                     EASTMONEY_HISTORY_BILL_FIELDS,
                     EASTMONEY_QUOTE_FIELDS,
                     EASTMONEY_STOCK_BASE_INFO_FIELDS,
                     EASTMONEY_LATEST_QUOTE_FIELDS)

signal.signal(signal.SIGINT, multitasking.killall)


@to_numeric
def get_base_info_single(stock_code: str) -> pd.Series:
    """
    获取单股票基本信息

    Parameters
    ----------
    stock_code : str
        股票代码

    Returns
    -------
    Series : 包含单只股票基本信息

    """
    fields = ",".join(EASTMONEY_STOCK_BASE_INFO_FIELDS.keys())
    params = (
        ('ut', 'fa5fd1943c7b386f172d6893dbfba10b'),
        ('invt', '2'),
        ('fltt', '2'),
        ('fields', fields),
        ('secid', get_quote_id(stock_code)),

    )
    url = 'http://push2.eastmoney.com/api/qt/stock/get'
    json_response = requests.get(url,
                                 headers=EASTMONEY_REQUEST_HEADERS,
                                 params=params).json()

    s = pd.Series(json_response['data']).rename(
        index=EASTMONEY_STOCK_BASE_INFO_FIELDS)
    return s[EASTMONEY_STOCK_BASE_INFO_FIELDS.values()]


def get_base_info_muliti(stock_codes: List[str]) -> pd.DataFrame:
    """
    获取股票多只基本信息

    Parameters
    ----------
    stock_codes : List[str]
        股票代码列表

    Returns
    -------
    DataFrame
        包含多只股票基本信息
    """

    @multitasking.task
    @retry(tries=3, delay=1)
    def start(stock_code: str):
        s = get_base_info_single(stock_code)
        dfs.append(s)
        pbar.update()
        pbar.set_description(f'Processing {stock_code}')
    dfs: List[pd.DataFrame] = []
    pbar = tqdm(total=len(stock_codes))
    for stock_code in stock_codes:
        start(stock_code)
    multitasking.wait_for_tasks()
    df = pd.DataFrame(dfs)
    return df


@to_numeric
def get_base_info(stock_codes: Union[str, List[str]]) -> Union[pd.Series, pd.DataFrame]:
    """
    Parameters
    ----------
    stock_codes : Union[str, List[str]]
        股票代码或股票代码构成的列表

    Returns
    -------
    Union[Series, DataFrame]
        Series 
            包含单只股票基本信息(当 stock_codes 是字符串时)
        DataFrane
            包含多只股票基本信息(当 stock_codes 是字符串列表时)

    Raises
    ------
    TypeError
        当 stock_codes 类型不符合要求时

    Examples
    --------
    >>> import efinance as ef
    >>> # 获取单只股票信息
    >>> ef.stock.get_base_info('600519')
    股票代码                  600519
    股票名称                    贵州茅台
    市盈率(动)                 39.38
    市净率                    12.54
    所处行业                    酿酒行业
    总市值          2198082348462.0
    流通市值         2198082348462.0
    板块编号                  BK0477
    ROE                     8.29
    净利率                  54.1678
    净利润       13954462085.610001
    毛利率                  91.6763
    dtype: object
    
    >>> # 获取多只股票信息
    >>> ef.stock.get_base_info(['600519','300715'])
        股票代码  股票名称  市盈率(动)    市净率  所处行业           总市值          流通市值    板块编号   ROE      净利率           净利润      毛利率
    0  300715  凯伦股份   42.29   3.12  水泥建材  9.160864e+09  6.397043e+09  BK0424  3.97  12.1659  5.415488e+07  32.8765
    1  600519  贵州茅台   39.38  12.54  酿酒行业  2.198082e+12  2.198082e+12  BK0477  8.29  54.1678  1.395446e+10  91.6763

    """

    if isinstance(stock_codes, str):
        return get_base_info_single(stock_codes)
    elif hasattr(stock_codes, '__iter__'):
        return get_base_info_muliti(stock_codes)
    raise TypeError(f'所给的 {stock_codes} 不符合参数要求')


@to_numeric
def get_quote_history_single(stock_code: str,
                             beg: str = '19000101',
                             end: str = '20500101',
                             klt: int = 101,
                             fqt: int = 1) -> pd.DataFrame:
    """
    获取单只股票k线数据

    Parameters
    ----------
    stock_code : str
        股票代码
    beg : str, optional
        开始日期 例如 20200101
    end : str, optional
        结束日期 例如 20200201
    klt : int, optional
        k线间距 默认为 101 即日k
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt : int, optional
        复权方式
            不复权 : 0
            前复权 : 1
            后复权 : 2 

    Returns
    -------
    DataFrame
        包含股票k线数据
    """

    fields = list(EASTMONEY_KLINE_FIELDS.keys())
    columns = list(EASTMONEY_KLINE_FIELDS.values())
    fields2 = ",".join(fields)
    quote_id = get_quote_id(stock_code)
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

    json_response = requests.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params).json()
    data = json_response.get('data')
    if data is None:
        columns.extend(['股票名称', '股票代码'])
        return pd.DataFrame(columns=columns)
    klines: List[str] = data['klines']
    rows = [kline.split(',') for kline in klines]
    stock_name = data['name']
    stock_code = quote_id.split('.')[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '股票代码', [stock_code] * len(df))
    df.insert(0, '股票名称', [stock_name] * len(df))

    return df


def get_quote_history_multi(stock_codes: List[str],
                            beg: str = '19000101',
                            end: str = '20500101',
                            klt: int = 101,
                            fqt: int = 1,
                            tries: int = 3) -> Dict[str, pd.DataFrame]:
    """
    获取多只股票历史行情信息

    Parameters
    ----------
    stock_code : str
        6 位股票代码
    beg : str, optional
        开始日期 例如 20200101
    end : str, optional
        结束日期 例如 20200201
    klt : int, optional
        k线间距 默认为 101 即日k
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt : int, optional
        复权方式
            不复权 : 0
            前复权 : 1
            后复权 : 2 
    tries : int, optional
        失败某个线程出错时重试次数

    Returns
    -------
    Dict[str, DataFrame]
        以 股票代码为 key，以 DataFrame 为 value 的 dict
    """

    dfs: Dict[str, pd.DataFrame] = {}
    total = len(stock_codes)

    @multitasking.task
    @retry(tries=tries, delay=1)
    def start(stock_code: str):
        _df = get_quote_history_single(
            stock_code,
            beg=beg,
            end=end,
            klt=klt,
            fqt=fqt)
        dfs[stock_code] = _df
        pbar.update(1)
        pbar.set_description_str(f'Processing: {stock_code}')

    pbar = tqdm(total=total)
    for stock_code in stock_codes:
        start(stock_code)
    multitasking.wait_for_tasks()
    pbar.close()
    return dfs


def get_quote_history(stock_codes: Union[str, List[str]],
                      beg: str = '19000101',
                      end: str = '20500101',
                      klt: int = 101,
                      fqt: int = 1) -> pd.DataFrame:
    """
    获取股票、ETF、债券的 K 线数据

    Parameters
    ----------
    stock_codes : Union[str,List[str]]
        股票、ETF、债券代码 或者 代码构成的列表
    beg : str, optional
        开始日期 例如 20200101
    end : str, optional
        结束日期 例如 20200201
    klt : int, optional
        k线间距 默认为 101 即日k
            klt : 1 1 分钟
            klt : 5 5 分钟
            klt : 101 日
            klt : 102 周
    fqt : int, optional
        复权方式
            不复权 : 0
            前复权 : 1
            后复权 : 2 

    Returns
    -------
    DataFrame
        包含股票k线数据

    Examples
    --------
    >>> import efinance as ef
    >>> # 获取单只股票日 K 行情数据
    >>> ef.stock.get_quote_history('600519')
        股票名称    股票代码          日期       开盘       收盘       最高       最低     成交量           成交额    振幅   涨跌幅    涨跌额    换手率
    0     贵州茅台  600519  2001-08-27   -89.74   -89.53   -89.08   -90.07  406318  1.410347e+09 -1.10  0.92   0.83  56.83
    1     贵州茅台  600519  2001-08-28   -89.64   -89.27   -89.24   -89.72  129647  4.634630e+08 -0.54  0.29   0.26  18.13
    2     贵州茅台  600519  2001-08-29   -89.24   -89.36   -89.24   -89.42   53252  1.946890e+08 -0.20 -0.10  -0.09   7.45
    3     贵州茅台  600519  2001-08-30   -89.38   -89.22   -89.14   -89.44   48013  1.775580e+08 -0.34  0.16   0.14   6.72
    4     贵州茅台  600519  2001-08-31   -89.21   -89.24   -89.12   -89.28   23231  8.623100e+07 -0.18 -0.02  -0.02   3.25
    ...    ...     ...         ...      ...      ...      ...      ...     ...           ...   ...   ...    ...    ...
    4756  贵州茅台  600519  2021-07-23  1937.82  1900.00  1937.82  1895.09   47585  9.057762e+09  2.20 -2.06 -40.01   0.38
    4757  贵州茅台  600519  2021-07-26  1879.00  1804.11  1879.00  1780.00   98619  1.789436e+10  5.21 -5.05 -95.89   0.79
    4758  贵州茅台  600519  2021-07-27  1803.00  1712.89  1810.00  1703.00   86577  1.523081e+10  5.93 -5.06 -91.22   0.69
    4759  贵州茅台  600519  2021-07-28  1703.00  1768.90  1788.20  1682.12   85369  1.479247e+10  6.19  3.27  56.01   0.68
    4760  贵州茅台  600519  2021-07-29  1810.01  1749.79  1823.00  1734.34   63864  1.129957e+10  5.01 -1.08 -19.11   0.51

    >>> # 获取多只股票历史行情
    >>> stock_df = ef.stock.get_quote_history(['600519','300750'])
    >>> type(stock_df)
    <class 'dict'>
    >>> stock_df.keys()
    dict_keys(['300750', '600519'])
    >>> stock_df['600519']
        股票名称    股票代码          日期       开盘       收盘       最高       最低     成交量           成交额    振幅   涨跌幅    涨跌额    换手率
    0     贵州茅台  600519  2001-08-27   -89.74   -89.53   -89.08   -90.07  406318  1.410347e+09 -1.10  0.92   0.83  56.83
    1     贵州茅台  600519  2001-08-28   -89.64   -89.27   -89.24   -89.72  129647  4.634630e+08 -0.54  0.29   0.26  18.13
    2     贵州茅台  600519  2001-08-29   -89.24   -89.36   -89.24   -89.42   53252  1.946890e+08 -0.20 -0.10  -0.09   7.45
    3     贵州茅台  600519  2001-08-30   -89.38   -89.22   -89.14   -89.44   48013  1.775580e+08 -0.34  0.16   0.14   6.72
    4     贵州茅台  600519  2001-08-31   -89.21   -89.24   -89.12   -89.28   23231  8.623100e+07 -0.18 -0.02  -0.02   3.25
    ...    ...     ...         ...      ...      ...      ...      ...     ...           ...   ...   ...    ...    ...
    4756  贵州茅台  600519  2021-07-23  1937.82  1900.00  1937.82  1895.09   47585  9.057762e+09  2.20 -2.06 -40.01   0.38
    4757  贵州茅台  600519  2021-07-26  1879.00  1804.11  1879.00  1780.00   98619  1.789436e+10  5.21 -5.05 -95.89   0.79
    4758  贵州茅台  600519  2021-07-27  1803.00  1712.89  1810.00  1703.00   86577  1.523081e+10  5.93 -5.06 -91.22   0.69
    4759  贵州茅台  600519  2021-07-28  1703.00  1768.90  1788.20  1682.12   85369  1.479247e+10  6.19  3.27  56.01   0.68
    4760  贵州茅台  600519  2021-07-29  1810.01  1749.79  1823.00  1734.34   63864  1.129957e+10  5.01 -1.08 -19.11   0.51
    """

    if isinstance(stock_codes, str):
        return get_quote_history_single(stock_codes,
                                        beg=beg,
                                        end=end,
                                        klt=klt,
                                        fqt=fqt)
    elif hasattr(stock_codes, '__iter__'):
        stock_codes = list(stock_codes)
        return get_quote_history_multi(stock_codes,
                                       beg=beg,
                                       end=end,
                                       klt=klt,
                                       fqt=fqt)
    else:
        raise TypeError(
            '股票代码类型数据输入不正确！'
        )


@to_numeric
def get_realtime_quotes() -> pd.DataFrame:
    """
    获取沪深市场最新行情总体情况

    Returns
    -------
    DataFrame
        包含沪深全市场A股上市公司的最新行情信息（涨跌幅、换手率等信息）

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_realtime_quotes()
            股票代码  股票名称     涨跌幅     最新价    涨跌额    换手率   动态市盈率     成交量           成交额    昨日收盘           总市值          流通市值      行情ID 市场类型
    0     688071   N华依  213.18    50.0  29.27  86.37 -223.37  128096   542717248.0   13.73    3132325282     637715370  1.688071   沪A
    1     301036   N双乐  116.68   54.47  27.28  64.85   28.53  153762   737806128.0   23.38    5066000000    1201150930  0.301036   深A
    2     001210   N金房   43.98   40.33  12.32   1.06     8.8    2416     9698603.0   28.01    3659869945     915087700  0.001210   深A
    3     688296  和达科技   24.97   33.96   6.57  47.65 -152.43  116333   364964624.0   26.31    3531087101     802667941  1.688296   沪A
    4     300506   名家汇   20.07    7.36   1.23  13.85   23.52  689062   486375616.0    6.13    4821136911    3662128367  0.300506   深A
    ...      ...   ...     ...     ...    ...    ...     ...     ...           ...     ...           ...           ...       ...  ...
    4582  002311  海大集团   -6.24    69.1  -4.26   1.35   34.71  224419  1454515184.0    68.3  106380754346  106155119205  0.002311   深A
    4583  301035   C润丰    -6.3   36.66  -2.41  38.72   25.75  253566   897378480.0   38.26    9901053000    2347839623  0.301035   深A
    4584  600702  舍得酒业   -6.39  221.96 -13.73    6.6   55.99  218947  4498078720.0  214.98   67619134625   66717802288  1.600702   沪A
    4585  600260  凯乐科技   -9.91    5.09  -0.56   1.18    6.69  116999    59552491.0    5.65    5075652410    5063970035  1.600260   沪A
    4586  301024   C霍普  -15.04   64.91 -10.88  39.29   71.05   41647   258630776.0   72.32    2604441600     651264000  0.301024   深A
    """

    fields = ",".join(EASTMONEY_QUOTE_FIELDS.keys())
    columns = list(EASTMONEY_QUOTE_FIELDS.values())
    params = (
        ('pn', '1'),
        ('pz', '1000000'),
        ('po', '1'),
        ('np', '1'),
        ('fltt', '2'),
        ('invt', '2'),
        ('fid', 'f3'),
        ('fs', 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23'),
        ('fields', fields)
    )
    # TODO 修改该接口，使得实时性更佳
    url = 'http://12.push2.eastmoney.com/api/qt/clist/get'
    json_response = requests.get(url,
                                 headers=EASTMONEY_REQUEST_HEADERS,
                                 params=params).json()
    df = (pd.DataFrame(json_response['data']['diff'])
          .rename(columns=EASTMONEY_QUOTE_FIELDS)
          [columns])
    df['行情ID'] = df['市场编号'].astype(str)+'.'+df['股票代码'].astype(str)
    df['市场类型'] = df['市场编号'].astype(str).apply(
        lambda x: MARET_NUMBER_DICT.get(str(x)))
    del df['市场编号']
    return df


@to_numeric
def get_history_bill(stock_code: str) -> pd.DataFrame:
    """
    获取单只股票历史单子流入流出数据

    Parameters
    ----------
    stock_code : str
        6 位股票代码

    Returns
    -------
    DataFrame
        包含沪深市场单只股票历史单子流入流出数据

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_history_bill('600519')
                日期         主力净流入       小单净流入         中单净流入         大单净流入        超大单净流入  主力净流入占比  小单流入净占比  中单流入净占比  大单流入净占比  超大单流入净占比      收盘价   涨跌幅
    0    2021-03-03  1.273400e+07   -283810.0 -1.245021e+07 -6.085768e+08  6.213108e+08     0.11    -0.00    -0.11    -5.35      5.47  2120.71  4.02
    1    2021-03-04 -3.670272e+06  -2282056.0  5.952143e+06  1.461528e+09 -1.465199e+09    -0.03    -0.02     0.04    10.99    -11.02  2013.71 -5.05
    2    2021-03-05 -1.514880e+07  -1319066.0  1.646793e+07 -2.528896e+07  1.014016e+07    -0.12    -0.01     0.13    -0.19      0.08  2040.82  1.35
    3    2021-03-08 -8.001702e+08   -877074.0  8.010473e+08  5.670671e+08 -1.367237e+09    -6.29    -0.01     6.30     4.46    -10.75  1940.71 -4.91
    4    2021-03-09 -2.237770e+08  -6391767.0  2.301686e+08 -1.795013e+08 -4.427571e+07    -1.39    -0.04     1.43    -1.11     -0.27  1917.70 -1.19
    ..          ...           ...         ...           ...           ...           ...      ...      ...      ...      ...       ...      ...   ...
    97   2021-07-23 -4.748689e+08   1443137.0  4.734257e+08 -2.773973e+08 -1.974716e+08    -5.24     0.02     5.23    -3.06     -2.18  1900.00 -2.06
    98   2021-07-26 -1.564233e+09  13142211.0  1.551091e+09 -1.270400e+08 -1.437193e+09    -8.74     0.07     8.67    -0.71     -8.03  1804.11 -5.05
    99   2021-07-27 -7.803296e+08 -10424715.0  7.907544e+08  6.725104e+07 -8.475807e+08    -5.12    -0.07     5.19     0.44     -5.56  1712.89 -5.06
    100  2021-07-28  3.997645e+08   2603511.0 -4.023677e+08  2.315648e+08  1.681997e+08     2.70     0.02    -2.72     1.57      1.14  1768.90  3.27
    101  2021-07-29 -9.209842e+08  -2312235.0  9.232964e+08 -3.959741e+08 -5.250101e+08    -8.15    -0.02     8.17    -3.50     -4.65  1749.79 -1.08

    """

    fields = list(EASTMONEY_HISTORY_BILL_FIELDS.keys())
    columns = list(EASTMONEY_HISTORY_BILL_FIELDS.values())
    fields2 = ",".join(fields)
    secid = get_quote_id(stock_code)
    params = (
        ('lmt', '100000'),
        ('klt', '101'),
        ('secid', secid),
        ('fields1', 'f1,f2,f3,f7'),
        ('fields2', fields2),

    )
    url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get'
    json_response = requests.get(url,
                                 headers=EASTMONEY_REQUEST_HEADERS,
                                 params=params).json()

    data = json_response.get('data')
    if data is None:
        return pd.DataFrame(columns=columns)
    klines: List[str] = data['klines']
    rows = [kline.split(',') for kline in klines]
    df = pd.DataFrame(rows, columns=columns)

    return df


@to_numeric
def get_today_bill(stock_code: str) -> pd.DataFrame:
    """
    获取最新交易日单只股票最新交易日单子流入流出数据

    Parameters
    ----------
    stock_code : str
        股票代码

    Returns
    -------
    DataFrame
        包含沪深市场单只股票最新交易日的单子流入流出数据
    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_today_bill('600519')
        股票代码                时间        主力净流入      小单净流入        中单净流入        大单净流入       超大单净流入
    0    600519  2021-07-29 09:31   -3261705.0  -389320.0    3651025.0  -12529658.0    9267953.0
    1    600519  2021-07-29 09:32    6437999.0  -606994.0   -5831006.0  -42615994.0   49053993.0
    2    600519  2021-07-29 09:33   13179707.0  -606994.0  -12572715.0  -85059118.0   98238825.0
    3    600519  2021-07-29 09:34   15385244.0  -970615.0  -14414632.0  -86865209.0  102250453.0
    4    600519  2021-07-29 09:35    7853716.0  -970615.0   -6883104.0  -75692436.0   83546152.0
    ..      ...               ...          ...        ...          ...          ...          ...
    235  600519  2021-07-29 14:56 -918956019.0 -1299630.0  920255661.0 -397127393.0 -521828626.0
    236  600519  2021-07-29 14:57 -920977761.0 -2319213.0  923296987.0 -397014702.0 -523963059.0
    237  600519  2021-07-29 14:58 -920984196.0 -2312233.0  923296442.0 -395974137.0 -525010059.0
    238  600519  2021-07-29 14:59 -920984196.0 -2312233.0  923296442.0 -395974137.0 -525010059.0
    239  600519  2021-07-29 15:00 -920984196.0 -2312233.0  923296442.0 -395974137.0 -525010059.0

    """
    quote_id = get_quote_id(stock_code)
    params = (
        ('lmt', '0'),
        ('klt', '1'),
        ('secid', quote_id),
        ('fields1', 'f1,f2,f3,f7'),
        ('fields2', 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63'),
    )
    url = 'http://push2.eastmoney.com/api/qt/stock/fflow/kline/get'
    json_response = requests.get(url,
                                 headers=EASTMONEY_REQUEST_HEADERS,
                                 params=params).json()
    data = json_response['data']
    klines = data['klines']
    columns = ['时间', '主力净流入', '小单净流入', '中单净流入', '大单净流入', '超大单净流入']
    klines: List[str] = data['klines']
    rows = [kline.split(',') for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '股票代码', [quote_id.split('.')[-1] for _ in range(len(df))])
    return df


@to_numeric
def get_latest_quote(stock_codes: List[str]) -> pd.DataFrame:
    """
    获取沪深市场多只股票的实时涨幅情况

    Parameters
    ----------
    stock_codes : List[str]
        多只股票代码列表

    Returns
    -------
    DataFrame
        包含沪深市场多只股票的实时涨幅情况

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_latest_quote(['600519','300750'])
        股票代码  股票名称            日期            开盘            收盘            最高            最低           成交量        成交额            振幅        涨跌幅           涨跌额        换手率
    0  600519  贵州茅台  1.858496e+11  1.597864e+10  5.296600e+09  3.272842e+10  3.232885e+10  3.995697e+08  15.207088  1.752743e+11  81.440261  1.374964e+09   1.094545
    1  300750  宁德时代  1.206223e+11  2.076009e+10  2.527780e+09  1.019879e+11  6.687712e+10  3.511077e+10  58.840670  6.564424e+10  37.872642  4.138079e+10  17.767560
    """
    if isinstance(stock_codes, str):
        stock_codes = [stock_codes]

    secids = ",".join([get_quote_id(code) for code in stock_codes])
    columns = EASTMONEY_LATEST_QUOTE_FIELDS
    fields = ",".join(columns.keys())
    params = (
        ('OSVersion', '14.3'),
        ('appVersion', '6.3.8'),
        ('fields', fields),
        ('fltt', '2'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('secids', secids),
        ('serverVersion', '6.3.6'),
        ('version', '6.3.8'),
    )
    url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
    response = requests.get(url,
                            headers=EASTMONEY_REQUEST_HEADERS,
                            params=params)

    data = response.json()['data']
    if data is None:
        return pd.DataFrame(columns=columns.values())
    diff = data['diff']
    df = pd.DataFrame(diff)[columns.keys()].rename(columns=columns)
    return df


@to_numeric
def get_top10_stock_holder_info(stock_code: str,
                                top: int = 4) -> pd.DataFrame:
    """
    获取沪深市场指定股票前十大股东信息

    Parameters
    ----------
    stock_code : str
        股票代码
    top : int, optional
        最新 top 个前 10 大流通股东公开信息, 默认为 4

    Returns
    -------
    DataFrame
        包含个股持仓占比前 10 的股东的一些信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_top10_stock_holder_info('600519',top = 1)
        股票代码        更新日期      股东代码                                股东名称     持股数    持股比例       增减     变动率
    0  600519  2021-03-31  80010298                  中国贵州茅台酒厂(集团)有限责任公司  6.783亿  54.00%       不变      --
    1  600519  2021-03-31  80637337                          香港中央结算有限公司   9594万   7.64%  -841.1万  -8.06%
    2  600519  2021-03-31  80732941                     贵州省国有资本运营有限责任公司   5700万   4.54%  -182.7万  -3.11%
    3  600519  2021-03-31  80010302                      贵州茅台酒厂集团技术开发公司   2781万   2.21%       不变      --
    4  600519  2021-03-31  80475097                      中央汇金资产管理有限责任公司   1079万   0.86%       不变      --
    5  600519  2021-03-31  80188285                        中国证券金融股份有限公司  803.9万   0.64%      -91   0.00%
    6  600519  2021-03-31  78043999      深圳市金汇荣盛财富管理有限公司-金汇荣盛三号私募证券投资基金  502.1万   0.40%       不变      --
    7  600519  2021-03-31  70400207  中国人寿保险股份有限公司-传统-普通保险产品-005L-CT001沪  434.1万   0.35%   44.72万  11.48%
    8  600519  2021-03-31    005827         中国银行股份有限公司-易方达蓝筹精选混合型证券投资基金    432万   0.34%       新进      --
    9  600519  2021-03-31  78083830      珠海市瑞丰汇邦资产管理有限公司-瑞丰汇邦三号私募证券投资基金  416.1万   0.33%       不变      --
    """

    def gen_fc(quote_id: str) -> str:
        """

        Parameters
        ----------
        quote_id : str
            行情ID

        Returns
        -------
        str
            指定格式的字符串
        """

        _type = quote_id.split('.')[0]
        _type = int(_type)
        # 深市
        if _type == 0:
            return f'{stock_code}02'
        # 沪市
        return f'{stock_code}01'

    def get_public_dates(stock_code: str,
                         top: int = 4) -> List[str]:
        """
        获取指定股票公开股东信息的日期

        Parameters
        ----------
        stock_code : str
            股票代码
        top : int, optional
            最新的 top 个日期, 默认为 4

        Returns
        -------
        List[str]
            持仓公开日期列表
        """

        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 color=b eastmoney_ios appversion_9.3 pkg=com.eastmoney.iphone mainBagVersion=9.3 statusBarHeight=20.000000 titleBarHeight=44.000000 density=2.000000 fontsize=3',
            'Content-Type': 'application/json;charset=utf-8',
            'Host': 'emh5.eastmoney.com',
            'Origin': 'null',
            'Cache-Control': 'public',
        }
        quote_id = get_quote_id(stock_code)
        stock_code = quote_id.split('.')[-1]
        fc = gen_fc(stock_code)
        data = {"fc": fc}
        url = 'https://emh5.eastmoney.com/api/GuBenGuDong/GetFirstRequest2Data'
        json_response = requests.post(
            url, headers=headers, json=data).json()
        items: list[dict] = json_response['Result']['SDLTGDBGQ']
        items = items.get('ShiDaLiuTongGuDongBaoGaoQiList')
        if items is None:
            return []
        df = pd.DataFrame(items)
        if 'BaoGaoQi' not in df:
            return []
        dates = df['BaoGaoQi'][:top]
        return dates

    fields = {
        'GuDongDaiMa': '股东代码',
        'GuDongMingCheng': '股东名称',
        'ChiGuShu': '持股数',
        'ChiGuBiLi': '持股比例',
        'ZengJian': '增减',
        'BianDongBiLi': '变动率',

    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 color=b eastmoney_ios appversion_9.3 pkg=com.eastmoney.iphone mainBagVersion=9.3 statusBarHeight=20.000000 titleBarHeight=44.000000 density=2.000000 fontsize=3',
        'Content-Type': 'application/json;charset=utf-8',
        'Host': 'emh5.eastmoney.com',
        'Origin': 'null',
        'Cache-Control': 'public',
    }
    fc = gen_fc(stock_code)
    dates = get_public_dates(stock_code)
    dfs: List[pd.DataFrame] = []
    for date in dates[:top]:
        data = {"fc": fc, "BaoGaoQi": date}
        url = 'https://emh5.eastmoney.com/api/GuBenGuDong/GetShiDaLiuTongGuDong'
        response = requests.post(url,
                                 headers=headers,
                                 json=data)
        response.encoding = 'utf-8'

        try:
            items: list[dict] = response.json(
            )['Result']['ShiDaLiuTongGuDongList']

        except:
            df = pd.DataFrame(columns=fields.values())
            df.insert(0, '股票代码', [stock_code for _ in range(len(df))])
            df.insert(1, '更新日期', [date for _ in range(len(df))])
            return df
        df = pd.DataFrame(items)
        df.rename(columns=fields, inplace=True)
        df.insert(0, '股票代码', [stock_code for _ in range(len(df))])
        df.insert(1, '更新日期', [date for _ in range(len(df))])
        del df['IsLink']
        dfs.append(df)

    return pd.concat(dfs, axis=0)
