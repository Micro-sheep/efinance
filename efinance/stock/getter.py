from typing import Dict, List, Union
from jsonpath import jsonpath
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
                     EASTMONEY_STOCK_BASE_INFO_FIELDS)
from ..shared import session
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
    Series
        单只股票基本信息

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
    json_response = session.get(url,
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
        多只股票基本信息
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

        - ``Series`` : 包含单只股票基本信息(当 ``stock_codes`` 是字符串时)
        - ``DataFrane`` : 包含多只股票基本信息(当 ``stock_codes`` 是字符串列表时)

    Raises
    ------
    TypeError
        当 ``stock_codes`` 类型不符合要求时

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

    json_response = session.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params).json()
    klines: List[str] = jsonpath(json_response, '$..klines[:]')
    if not klines:
        columns.extend(['股票名称', '股票代码'])
        return pd.DataFrame(columns=columns)
    rows = [kline.split(',') for kline in klines]
    stock_name = json_response['data']['name']
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
                      fqt: int = 1) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    获取股票、ETF、债券的 K 线数据

    Parameters
    ----------
    stock_codes : Union[str,List[str]]
        股票、ETF、债券代码 或者 代码构成的列表
    beg : str, optional
        开始日期，默认为 ``'19000101'`` ，表示 1900年1月1日
    end : str, optional
        结束日期，默认为 ``'20500101'`` ，表示 2050年1月1日
    klt : int, optional
        行情之间的时间间隔，默认为 ``101`` ，可选示例如下

            - ``1`` : 分钟
            - ``5`` : 5 分钟
            - ``101`` : 日
            - ``102`` : 周
    fqt : int, optional
        复权方式，默认为 ``1`` ，可选示例如下

            - ``0`` : 不复权
            - ``1`` : 前复权
            - ``2`` : 后复权

    Returns
    -------
    Union[DataFrame, Dict[str, DataFrame]]
        股票、ETF、或者债券的 K 线数据

            - ``DataFrame`` : 当 ``stock_codes`` 是 ``str`` 时
            - ``Dict[str, DataFrame]`` : 当 ``stock_codes`` 是 ``List[str]`` 时
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
        沪深全市场A股上市公司的最新行情信息（涨跌幅、换手率等信息）

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_realtime_quotes()
            股票代码    股票名称     涨跌幅     最新价      最高      最低    涨跌额    换手率   动态市盈率     成交量          成交额    昨日收盘          总市值         流通市值      行情ID 市场类型
    0     301040     N中环  230.58   44.86    47.0   41.59  31.29  26.68   37.43   63249  270449440.0   13.57   4486000000   1063568738  0.301040   深A
    1     300170    汉得信息   20.06    8.56    8.56    7.15   1.43   3.85  106.52  309143  248553089.0    7.13   7567296355   6870207362  0.300170   深A
    2     300507    苏奥传感   20.02   11.51   11.51    10.5   1.92   3.96   59.52  107058  121818531.0    9.59   4935230130   3115078785  0.300507   深A
    3     688316  青云科技-U    20.0   83.63   83.63    70.0  13.94   6.87  -16.13    7440   60252880.0   69.69   3969261695    906141587  1.688316   沪A
    4     688682     霍莱沃    20.0  181.18  181.18  164.51   30.2   5.03  385.91    3781   67140458.0  150.98   6703660000   1361951077  1.688682   沪A
    ...      ...     ...     ...     ...     ...     ...    ...    ...     ...     ...          ...     ...          ...          ...       ...  ...
    4589  300529    健帆生物  -10.63   61.62   69.84   61.39  -7.33    1.3    40.0   66955  430949056.0   68.95  49605885008  31670304487  0.300529   深A
    4590  300118    东方日升  -10.91   18.04   19.73   17.66  -2.21    4.2   72.72  377588  695986288.0   20.25  16260533336  16226004776  0.300118   深A
    4591  688390     固德威  -11.15  501.99   545.0  485.55 -63.01    3.1  157.93    6494  333857920.0   565.0  44175120000  10514394398  1.688390   沪A
    4592  300511    雪榕生物   -11.8    6.95    7.33     6.9  -0.93   4.39    7.57  138677   97532444.0    7.88   3071284730   2195664516  0.300511   深A
    4593  300763    锦浪科技  -14.13  249.45   278.0  249.01 -41.04   2.97  129.67   31904  825647776.0  290.49  61758892365  26779236033  0.300763   深A

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
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    json_response = session.get(url,
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
        股票代码

    Returns
    -------
    DataFrame
        沪深市场单只股票历史单子流入流出数据

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_history_bill('600519')
        股票名称    股票代码          日期         主力净流入       小单净流入         中单净流入         大单净流入        超大单净流入  主力净流入占比  小单流入净占比  中单流入净占比  大单流入净占比  超大单流入净占比      收盘价   涨跌幅
    0    贵州茅台  600519  2021-03-04 -3.670272e+06  -2282056.0  5.952143e+06  1.461528e+09 -1.465199e+09    -0.03    -0.02     0.04    10.99    -11.02  2013.71 -5.05
    1    贵州茅台  600519  2021-03-05 -1.514880e+07  -1319066.0  1.646793e+07 -2.528896e+07  1.014016e+07    -0.12    -0.01     0.13    -0.19      0.08  2040.82  1.35
    2    贵州茅台  600519  2021-03-08 -8.001702e+08   -877074.0  8.010473e+08  5.670671e+08 -1.367237e+09    -6.29    -0.01     6.30     4.46    -10.75  1940.71 -4.91
    3    贵州茅台  600519  2021-03-09 -2.237770e+08  -6391767.0  2.301686e+08 -1.795013e+08 -4.427571e+07    -1.39    -0.04     1.43    -1.11     -0.27  1917.70 -1.19
    4    贵州茅台  600519  2021-03-10 -2.044173e+08  -1551798.0  2.059690e+08 -2.378506e+08  3.343331e+07    -2.02    -0.02     2.03    -2.35      0.33  1950.72  1.72
    ..    ...     ...         ...           ...         ...           ...           ...           ...      ...      ...      ...      ...       ...      ...   ...
    97   贵州茅台  600519  2021-07-26 -1.564233e+09  13142211.0  1.551091e+09 -1.270400e+08 -1.437193e+09    -8.74     0.07     8.67    -0.71     -8.03  1804.11 -5.05
    98   贵州茅台  600519  2021-07-27 -7.803296e+08 -10424715.0  7.907544e+08  6.725104e+07 -8.475807e+08    -5.12    -0.07     5.19     0.44     -5.56  1712.89 -5.06
    99   贵州茅台  600519  2021-07-28  3.997645e+08   2603511.0 -4.023677e+08  2.315648e+08  1.681997e+08     2.70     0.02    -2.72     1.57      1.14  1768.90  3.27
    100  贵州茅台  600519  2021-07-29 -9.209842e+08  -2312235.0  9.232964e+08 -3.959741e+08 -5.250101e+08    -8.15    -0.02     8.17    -3.50     -4.65  1749.79 -1.08
    101  贵州茅台  600519  2021-07-30 -1.524740e+09  -6020099.0  1.530761e+09  1.147248e+08 -1.639465e+09   -11.63    -0.05    11.68     0.88    -12.51  1678.99 -4.05

    """

    fields = list(EASTMONEY_HISTORY_BILL_FIELDS.keys())
    columns = list(EASTMONEY_HISTORY_BILL_FIELDS.values())
    fields2 = ",".join(fields)
    quote_id = get_quote_id(stock_code)
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
        columns.insert(0, '股票代码')
        columns.insert(0, '股票名称')
        return pd.DataFrame(columns=columns)
    rows = [kline.split(',') for kline in klines]
    stock_name = jsonpath(json_response, '$..name')[0]
    stock_code = quote_id.split('.')[-1]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '股票代码', [stock_code for _ in range(len(df))])
    df.insert(0, '股票名称', [stock_name for _ in range(len(df))])

    return df


@to_numeric
def get_today_bill(stock_code: str) -> pd.DataFrame:
    """
    获取单只股票最新交易日的日内分钟级单子流入流出数据

    Parameters
    ----------
    stock_code : str
        股票代码

    Returns
    -------
    DataFrame
        单只股票最新交易日的日内分钟级单子流入流出数据
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
    json_response = session.get(url,
                                headers=EASTMONEY_REQUEST_HEADERS,
                                params=params).json()
    columns = ['时间', '主力净流入', '小单净流入', '中单净流入', '大单净流入', '超大单净流入']
    stock_name = jsonpath(json_response, '$..name')[0]
    stock_code = quote_id.split('.')[-1]
    klines: List[str] = jsonpath(json_response, '$..klines[:]')
    if not klines:
        columns.insert(0, '股票代码')
        columns.insert(0, '股票名称')
        return pd.DataFrame(columns=columns)
    rows = [kline.split(',') for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '股票代码', [stock_code for _ in range(len(df))])
    df.insert(0, '股票名称', [stock_name for _ in range(len(df))])
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
        沪深市场多只股票的实时涨幅情况

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_latest_quote(['600519','300750'])
        股票代码  股票名称   涨跌幅      最新价       最高      最低    涨跌额   换手率   动态市盈率    成交量           成交额    昨日收盘            总市值           流通市值 市场类型
    0  600519  贵州茅台 -3.13  1700.09  1738.99  1688.8 -54.91  0.11   43.31  13373  2.299199e+09  1755.0  2135649317802  2135649317802   沪A
    1  300750  宁德时代 -2.21   539.80   556.00   531.0 -12.20  0.13  160.82  27011  1.458472e+09   552.0  1257198411520  1095654311636   深A

    Notes
    -----
    当需要获取多只沪深 A 股 的实时涨跌情况时，最好使用 ``efinance.stock.get_realtime_quptes``
    """
    if isinstance(stock_codes, str):
        stock_codes = [stock_codes]
    secids: List[str] = [get_quote_id(stock_code)
                         for stock_code in stock_codes]

    columns = EASTMONEY_QUOTE_FIELDS
    fields = ",".join(columns.keys())
    params = (
        ('OSVersion', '14.3'),
        ('appVersion', '6.3.8'),
        ('fields', fields),
        ('fltt', '2'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('secids', ",".join(secids)),
        ('serverVersion', '6.3.6'),
        ('version', '6.3.8'),
    )
    url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
    json_response = session.get(url,
                                headers=EASTMONEY_REQUEST_HEADERS,
                                params=params).json()

    rows = jsonpath(json_response, '$..diff[:]')
    if rows is None:
        return pd.DataFrame(columns=columns.values()).rename({
            '市场编号': '市场类型'
        })

    df = pd.DataFrame(rows)[columns.keys()].rename(columns=columns)
    df['市场类型'] = df['市场编号'].apply(lambda x: MARET_NUMBER_DICT.get(str(x)))
    del df['市场编号']
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
        最新 top 个前 10 大流通股东公开信息, 默认为  ``4``

    Returns
    -------
    DataFrame
        个股持仓占比前 10 的股东的一些信息

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

    def gen_fc(stock_code: str) -> str:
        """

        Parameters
        ----------
        stock_code : str
            股票代码

        Returns
        -------
        str
            指定格式的字符串
        """
        _type, stock_code = get_quote_id(stock_code).split('.')
        _type = int(_type)
        # 深市
        if _type == 0:
            return f'{stock_code}02'
        # 沪市
        return f'{stock_code}01'

    def get_public_dates(stock_code: str) -> List[str]:
        """
        获取指定股票公开股东信息的日期

        Parameters
        ----------
        stock_code : str
            股票代码

        Returns
        -------
        List[str]
            持仓公开日期列表
        """

        quote_id = get_quote_id(stock_code)
        stock_code = quote_id.split('.')[-1]
        fc = gen_fc(stock_code)
        data = {"fc": fc}
        url = 'https://emh5.eastmoney.com/api/GuBenGuDong/GetFirstRequest2Data'
        json_response = requests.post(
            url,  json=data).json()
        dates = jsonpath(json_response, f'$..BaoGaoQi')
        if not dates:
            return []
        return dates

    fields = {
        'GuDongDaiMa': '股东代码',
        'GuDongMingCheng': '股东名称',
        'ChiGuShu': '持股数',
        'ChiGuBiLi': '持股比例',
        'ZengJian': '增减',
        'BianDongBiLi': '变动率',

    }
    quote_id = get_quote_id(stock_code)
    stock_code = quote_id.split('.')[-1]
    fc = gen_fc(stock_code)
    dates = get_public_dates(stock_code)
    dfs: List[pd.DataFrame] = []
    empty_df = pd.DataFrame(columns=['股票代码', '日期']+list(fields.values()))

    for date in dates[:top]:
        data = {"fc": fc, "BaoGaoQi": date}
        url = 'https://emh5.eastmoney.com/api/GuBenGuDong/GetShiDaLiuTongGuDong'
        response = requests.post(url, json=data)
        response.encoding = 'utf-8'
        items: List[dict] = jsonpath(
            response.json(), f'$..ShiDaLiuTongGuDongList[:]')
        if not items:
            continue
        df = pd.DataFrame(items)
        df.rename(columns=fields, inplace=True)
        df.insert(0, '股票代码', [stock_code for _ in range(len(df))])
        df.insert(1, '更新日期', [date for _ in range(len(df))])
        del df['IsLink']
        dfs.append(df)
    if len(dfs) == 0:
        return empty_df
    return pd.concat(dfs, axis=0)
