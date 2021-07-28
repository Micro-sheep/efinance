from typing import Dict, List, Union
from retry import retry
import pandas as pd
import requests
import multitasking
import signal
from tqdm import tqdm
from .utils import get_quote_id
from ..utils import to_numeric
from ..config import MARET_NUMBER_DICT
from .config import (EastmoneyKlines,
                     EastmoneyHeaders,
                     EastmoneyBills,
                     EastmoneyQuotes,
                     EastmoneyStockBaseInfo,
                     EastmoneyLatestQuote)

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
    fields = ",".join(EastmoneyStockBaseInfo.keys())
    params = (
        ('ut', 'fa5fd1943c7b386f172d6893dbfba10b'),
        ('invt', '2'),
        ('fltt', '2'),
        ('fields', fields),
        ('secid', get_quote_id(stock_code)),

    )
    url = 'http://push2.eastmoney.com/api/qt/stock/get'
    json_response = requests.get(url,
                                 headers=EastmoneyHeaders,
                                 params=params).json()

    s = pd.Series(json_response['data']).rename(index=EastmoneyStockBaseInfo)
    return s[EastmoneyStockBaseInfo.values()]


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
    市盈率(动)                 48.94
    市净率                    15.59
    所处行业                    酿酒行业
    总市值          2731853355660.0
    流通市值         2731853355660.0
    板块编号                  BK0477
    ROE                     8.29
    净利率                  54.1678
    净利润       13954462085.610001
    毛利率                  91.6763
    dtype: object
    >>> # 获取多只股票信息
    >>> ef.stock.get_base_info(['600519','300715'])
    股票代码  股票名称  市盈率(动)    市净率  所处行业           总市值          流通市值    板块编号   ROE      净利率           净利润      毛利率
    0  600519  贵州茅台   49.20  15.67  酿酒行业  2.745986e+12  2.745986e+12  BK0477  8.29  54.1678  1.395446e+10  91.6763
    1  300715  凯伦股份   34.34   5.35  水泥建材  7.437957e+09  6.594918e+09  BK0424  3.97  12.1659  5.415488e+07  32.8765


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

    fields = list(EastmoneyKlines.keys())
    columns = list(EastmoneyKlines.values())
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
        url, headers=EastmoneyHeaders, params=params).json()

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
    >>> # 获取单只给股票历史行情（日 k）
    >>> ef.stock.get_quote_history('600519')
      股票名称    股票代码          日期       开盘       收盘       最高       最低       成交量           成交额    振幅   涨跌幅    涨跌额    换手率
    0     贵州茅台  600519  2001-08-27   -89.74   -89.53   -89.08   -90.07  406318.0  1.410347e+09 -1.10  0.92   0.83  56.83
    1     贵州茅台  600519  2001-08-28   -89.64   -89.27   -89.24   -89.72  129647.0  4.634630e+08 -0.54  0.29   0.26  18.13
    2     贵州茅台  600519  2001-08-29   -89.24   -89.36   -89.24   -89.42   53252.0  1.946890e+08 -0.20 -0.10  -0.09   7.45
    3     贵州茅台  600519  2001-08-30   -89.38   -89.22   -89.14   -89.44   48013.0  1.775580e+08 -0.34  0.16   0.14   6.72
    4     贵州茅台  600519  2001-08-31   -89.21   -89.24   -89.12   -89.28   23231.0  8.623100e+07 -0.18 -0.02  -0.02   3.25
    ...    ...     ...         ...      ...      ...      ...      ...       ...           ...   ...   ...    ...    ...
    4755  贵州茅台  600519  2021-07-22  1960.00  1940.01  1973.90  1938.96   39090.0  7.619077e+09  1.77 -1.47 -28.99   0.31
    4756  贵州茅台  600519  2021-07-23  1937.82  1900.00  1937.82  1895.09   47585.0  9.057762e+09  2.20 -2.06 -40.01   0.38
    4757  贵州茅台  600519  2021-07-26  1879.00  1804.11  1879.00  1780.00   98619.0  1.789436e+10  5.21 -5.05 -95.89   0.79
    4758  贵州茅台  600519  2021-07-27  1803.00  1712.89  1810.00  1703.00   86577.0  1.523081e+10  5.93 -5.06 -91.22   0.69
    4759  贵州茅台  600519  2021-07-28  1703.00  1768.90  1788.20  1682.12   85369.0  1.479247e+10  6.19  3.27  56.01   0.68
    [4760 rows x 13 columns]
    >>> # 获取多只股票历史行情
    >>> ef.stock.get_quote_history(['600519','300750'])
    {'300750':      股票名称    股票代码          日期      开盘      收盘      最高      最低       成交量           成交额     振幅    涨跌幅    涨跌额   换手率
    0    宁德时代  300750  2018-06-11   29.57   35.60   35.60   29.57     788.0  2.845471e+06  24.57  45.07  11.06  0.04
    1    宁德时代  300750  2018-06-12   39.22   39.22   39.22   39.22     266.0  1.058375e+06   0.00  10.17   3.62  0.01
    2    宁德时代  300750  2018-06-13   43.20   43.20   43.20   43.20     450.0  1.972314e+06   0.00  10.15   3.98  0.02
    3    宁德时代  300750  2018-06-14   47.58   47.58   47.58   47.58     743.0  3.578184e+06   0.00  10.14   4.38  0.03
    4    宁德时代  300750  2018-06-15   52.40   52.40   52.40   52.40    2565.0  1.359503e+07   0.00  10.13   4.82  0.12
    ..    ...     ...         ...     ...     ...     ...     ...       ...           ...    ...    ...    ...   ...
    758  宁德时代  300750  2021-07-22  556.60  557.08  563.69  545.69  108836.0  6.027459e+09   3.24   0.23   1.30  0.54
    759  宁德时代  300750  2021-07-23  555.00  547.01  563.99  546.00   93329.0  5.157402e+09   3.23  -1.81 -10.07  0.46
    760  宁德时代  300750  2021-07-26  544.00  539.78  552.93  522.50  127290.0  6.852322e+09   5.56  -1.32  -7.23  0.63
    761  宁德时代  300750  2021-07-27  543.02  495.00  559.19  495.00  178460.0  9.419313e+09  11.89  -8.30 -44.78  0.88
    762  宁德时代  300750  2021-07-28  496.00  525.05  533.30  496.00  217247.0  1.122167e+10   7.54   6.07  30.05  1.07
    [763 rows x 13 columns],
    '600519':       股票名称    股票代码          日期       开盘       收盘       最高       最低       成交量           成交额    振幅   涨跌幅    涨跌额    换手率
    0     贵州茅台  600519  2001-08-27   -89.74   -89.53   -89.08   -90.07  406318.0  1.410347e+09 -1.10  0.92   0.83  56.83
    1     贵州茅台  600519  2001-08-28   -89.64   -89.27   -89.24   -89.72  129647.0  4.634630e+08 -0.54  0.29   0.26  18.13
    2     贵州茅台  600519  2001-08-29   -89.24   -89.36   -89.24   -89.42   53252.0  1.946890e+08 -0.20 -0.10  -0.09   7.45
    3     贵州茅台  600519  2001-08-30   -89.38   -89.22   -89.14   -89.44   48013.0  1.775580e+08 -0.34  0.16   0.14   6.72
    4     贵州茅台  600519  2001-08-31   -89.21   -89.24   -89.12   -89.28   23231.0  8.623100e+07 -0.18 -0.02  -0.02   3.25
    ...    ...     ...         ...      ...      ...      ...      ...       ...           ...   ...   ...    ...    ...
    4755  贵州茅台  600519  2021-07-22  1960.00  1940.01  1973.90  1938.96   39090.0  7.619077e+09  1.77 -1.47 -28.99   0.31
    4756  贵州茅台  600519  2021-07-23  1937.82  1900.00  1937.82  1895.09   47585.0  9.057762e+09  2.20 -2.06 -40.01   0.38
    4757  贵州茅台  600519  2021-07-26  1879.00  1804.11  1879.00  1780.00   98619.0  1.789436e+10  5.21 -5.05 -95.89   0.79
    4758  贵州茅台  600519  2021-07-27  1803.00  1712.89  1810.00  1703.00   86577.0  1.523081e+10  5.93 -5.06 -91.22   0.69
    4759  贵州茅台  600519  2021-07-28  1703.00  1768.90  1788.20  1682.12   85369.0  1.479247e+10  6.19  3.27  56.01   0.68
    [4760 rows x 13 columns]}
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
        股票代码  股票名称     涨跌幅    最新价    涨跌额    换手率   动态市盈率        成交量           成交额   昨日收盘            总市值          流通市值      行情ID 市场类型
    0     688718  N唯赛勃  586.84  46.18  34.33   89.6  103.41   316228.0  1249689424.0   5.85   6981451350.0  1418121760.0  1.688718   沪A
    1     301035   N润丰   73.59   52.0  16.22  56.82   27.48   372147.0  1495134688.0  22.04  10566646800.0  2505672078.0  0.301035   深A
    2     301024   N霍普   49.05  100.0   23.8  49.48   83.63    52448.0   422392992.0  48.52   3065644800.0   766592000.0  0.301024   深A
    3     300252   金信诺   20.05  10.48   1.75   9.61  445.01   395553.0   399645072.0   8.73   6051978180.0  4311519663.0  0.300252   深A
    4     300570   太辰光   20.02  20.08   3.35  16.91   52.37   324360.0   616786960.0  16.73   4618335744.0  3852378441.0  0.300570   深A
    ...      ...   ...     ...    ...    ...    ...     ...        ...           ...    ...            ...           ...       ...  ...
    4579  300617  安靠智电  -12.26   48.2  -6.03   6.64   32.86    43011.0   192835444.0   49.2   7258892435.0  2794735359.0  0.300617   深A
    4580  300311   任子行  -14.61  11.18  -1.67  28.13  -73.55  1435910.0  1434059584.0  11.43   6574630264.0  4981700313.0  0.300311   深A
    4581  300561  汇金科技  -15.83   11.0  -1.96   8.56   137.6   149574.0   156322773.0  12.38   3419696943.0  1821138651.0  0.300561   深A
    4582  688100  威胜信息  -16.05  26.67  -4.28   2.98   52.69    49039.0   117508031.0  26.67  11195000000.0  3682099692.0  1.688100   沪A
    4583  688296  和达科技  -19.32   29.0   -6.3  38.14 -121.97    93098.0   249574905.0  32.61   2825514040.0   642280825.0  1.688296   沪A
    [4584 rows x 14 columns]
    """

    fields = ",".join(EastmoneyQuotes.keys())
    columns = list(EastmoneyQuotes.values())
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
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    json_response = requests.get(url,
                                 headers=EastmoneyHeaders,
                                 params=params).json()
    df = (pd.DataFrame(json_response['data']['diff'])
          .rename(columns=EastmoneyQuotes)
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
        日期       主力净流入       小单净流入       中单净流入         大单净流入         超大单净流入 主力净流入占比 小单流入净占比 中单流入净占比 大单流入净占比 超大单流入净占比      收盘价    涨跌幅
    0    2021-01-11   2533120.0  -6824244.0   4291064.0  -472681984.0    475215104.0    0.02   -0.06    0.04   -4.39     4.41  2099.73   0.47
    1    2021-01-12   6585120.0  -3120619.0  -3464550.0  -630365696.0    636950816.0    0.07   -0.04   -0.04   -7.16     7.24  2160.90   2.91
    2    2021-01-13  -2533248.0   -937719.0   3471030.0   475560016.0   -478093264.0   -0.03   -0.01    0.05    6.41    -6.44  2164.00   0.14
    3    2021-01-14  -4768592.0  -2050142.0   6818709.0   740699392.0   -745467984.0   -0.06   -0.03    0.09    9.59    -9.65  2134.00  -1.39
    4    2021-01-15  -8642048.0  -4172436.0  12814373.0   132030464.0   -140672512.0   -0.07   -0.03    0.10    1.07    -1.14  2082.00  -2.44
    ..          ...         ...         ...         ...           ...            ...     ...     ...     ...     ...      ...      ...    ...
    96   2021-06-07  -5206912.0    356385.0   4850539.0   -86535248.0     81328336.0   -0.09    0.01    0.08   -1.50     1.41  2271.00   0.87
    97   2021-06-08  -6469056.0  -9567962.0  16036913.0  1060995328.0  -1067464384.0   -0.06   -0.09    0.15   10.12   -10.19  2191.00  -3.52
    98   2021-06-09   3725968.0     88891.0  -3814859.0   280492656.0   -276766688.0    0.07    0.00   -0.07    5.02    -4.95  2199.50   0.39
    99   2021-06-10   3726096.0   1530221.0  -5256314.0   136356048.0   -132629952.0    0.07    0.03   -0.09    2.39    -2.32  2238.48   1.77
    100  2021-06-11   7634576.0   -770025.0  -6864556.0  -176945392.0    184579968.0    0.10   -0.01   -0.09   -2.35     2.46  2178.81  -2.67
    [101 rows x 13 columns]
    """

    fields = list(EastmoneyBills.keys())
    columns = list(EastmoneyBills.values())
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
                                 headers=EastmoneyHeaders,
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
        股票代码                时间       主力净流入      小单净流入      中单净流入        大单净流入        超大单净流入
    0   600519  2021-06-15 09:31   -308042.0        0.0   308043.0  -18484264.0    18176222.0
    1   600519  2021-06-15 09:32  -1594317.0        0.0  1594317.0   -4394364.0     2800047.0
    2   600519  2021-06-15 09:33  -1535051.0        0.0  1535050.0  -21109538.0    19574487.0
    3   600519  2021-06-15 09:34  -1535051.0        0.0  1535050.0  -15839506.0    14304455.0
    4   600519  2021-06-15 09:35  -1253496.0        0.0  1253495.0  -19738272.0    18484776.0
    ..     ...               ...         ...        ...        ...          ...           ...
    91  600519  2021-06-15 11:02  -5084126.0  -813197.0  5897325.0  143132755.0  -148216881.0
    92  600519  2021-06-15 11:03  -4694051.0  -813197.0  5507250.0  134588811.0  -139282862.0
    93  600519  2021-06-15 11:04  -4913204.0  -813197.0  5726403.0  130204858.0  -135118062.0
    94  600519  2021-06-15 11:05  -4913204.0  -813197.0  5726403.0  128451226.0  -133364430.0
    95  600519  2021-06-15 11:06  -4913204.0  -813197.0  5726403.0  126258794.0  -131171998.0
    [96 rows x 7 columns]
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
                                 headers=EastmoneyHeaders,
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
    columns = EastmoneyLatestQuote
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
                            headers=EastmoneyHeaders,
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
