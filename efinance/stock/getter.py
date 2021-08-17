import rich
from jsonpath import jsonpath
from retry import retry
import pandas as pd
import requests
import multitasking
import signal
from tqdm import tqdm
from typing import (Dict,
                    List,
                    Union)
from ..shared import session
from ..common import get_quote_history as get_quote_history_for_stock
from ..common import get_history_bill as get_history_bill_for_stock
from ..common import get_today_bill as get_today_bill_for_stock
from ..common import get_realtime_quotes_by_fs
from ..utils import (to_numeric,
                     get_quote_id)
from .config import EASTMONEY_STOCK_BASE_INFO_FIELDS
from ..common.config import (
    FS_DICT,
    MARKET_NUMBER_DICT,
    EASTMONEY_REQUEST_HEADERS,
    EASTMONEY_QUOTE_FIELDS
)

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
        pbar.set_description(f'Processing => {stock_code}')
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


def get_quote_history(stock_codes: Union[str, List[str]],
                      beg: str = '19000101',
                      end: str = '20500101',
                      klt: int = 101,
                      fqt: int = 1) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    获取股票的 K 线数据

    Parameters
    ----------
    stock_codes : Union[str,List[str]]
        股票代码、名称 或者 股票代码、名称构成的列表
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
        股票的 K 线数据

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
    df = get_quote_history_for_stock(
        stock_codes,
        beg=beg,
        end=end,
        klt=klt,
        fqt=fqt

    )
    if isinstance(df, pd.DataFrame):

        df.rename(columns={'代码': '股票代码',
                           '名称': '股票名称'
                           },
                  inplace=True)
    elif isinstance(df, dict):
        for stock_code in df.keys():
            df[stock_code].rename(columns={'代码': '股票代码',
                                           '名称': '股票名称'
                                           },
                                  inplace=True)

    return df


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
            股票代码   股票名称     涨跌幅     最新价      最高      最低      今开     涨跌额    换手率    量比    动态市盈率     成交量           成交额   昨日收盘           总市值         流通市值      行情ID 市场类型
    0     688787    N海天  277.59  139.48  172.39  139.25  171.66  102.54  85.62     -    78.93   74519  1110318832.0  36.94    5969744000   1213908667  1.688787   沪A
    1     301045    N天禄  149.34   39.42   48.95    39.2   48.95   23.61  66.66     -    37.81  163061   683878656.0  15.81    4066344240    964237089  0.301045   深A
    2     300532   今天国际   20.04   12.16   12.16   10.69   10.69    2.03   8.85  3.02   -22.72  144795   171535181.0  10.13    3322510580   1989333440  0.300532   深A
    3     300600   国瑞科技   20.02   13.19   13.19   11.11   11.41     2.2  18.61  2.82   218.75  423779   541164432.0  10.99    3915421427   3003665117  0.300600   深A
    4     300985   致远新能   20.01   47.08   47.08    36.8    39.4    7.85  66.65  2.17    58.37  210697   897370992.0  39.23    6277336472   1488300116  0.300985   深A
    ...      ...    ...     ...     ...     ...     ...     ...     ...    ...   ...      ...     ...           ...    ...           ...          ...       ...  ...
    4598  603186   华正新材   -10.0   43.27   44.09   43.27   43.99   -4.81   1.98  0.48    25.24   27697   120486294.0  48.08    6146300650   6063519472  1.603186   沪A
    4599  688185  康希诺-U  -10.11   476.4  534.94  460.13   530.0   -53.6   6.02  2.74 -2088.07   40239  1960540832.0  530.0  117885131884  31831479215  1.688185   沪A
    4600  688148   芳源股份  -10.57    31.3   34.39    31.3    33.9    -3.7  26.07  0.56   220.01  188415   620632512.0   35.0   15923562000   2261706043  1.688148   沪A
    4601  300034   钢研高纳  -10.96   43.12   46.81   42.88    46.5   -5.31   7.45  1.77    59.49  323226  1441101824.0  48.43   20959281094  18706911861  0.300034   深A
    4602  300712   永福股份  -13.71    96.9  110.94    95.4   109.0   -15.4   6.96  1.26   511.21  126705  1265152928.0  112.3   17645877600  17645877600  0.300712   深A
    """
    fs = FS_DICT['stock']
    df = get_realtime_quotes_by_fs(fs)
    df = df.rename(columns={'代码': '股票代码',
                            '名称': '股票名称'
                            })
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
    df = get_history_bill_for_stock(stock_code)
    df.rename(columns={
        '代码': '股票代码',
        '名称': '股票名称'
    }, inplace=True)
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
    df = get_today_bill_for_stock(stock_code)
    df.rename(columns={
        '代码': '股票代码',
        '名称': '股票名称'
    }, inplace=True)
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
        沪深市场、港股、美股多只股票的实时涨幅情况

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_latest_quote(['600519','300750'])
        股票代码  股票名称   涨跌幅      最新价      最高      最低      今开    涨跌额   换手率    量比   动态市盈率     成交量           成交额    昨日收盘            总市值           流通市值 市场类型
    0  600519  贵州茅台  0.59  1700.04  1713.0  1679.0  1690.0  10.04  0.30  0.72   43.31   37905  6.418413e+09  1690.0  2135586507912  2135586507912   沪A
    1  300750  宁德时代  0.01   502.05   529.9   480.0   480.0   0.05  1.37  1.75  149.57  277258  1.408545e+10   502.0  1169278366994  1019031580505   深A

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
    df['市场类型'] = df['市场编号'].apply(lambda x: MARKET_NUMBER_DICT.get(str(x)))
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
            公开日期列表
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
    return pd.concat(dfs, axis=0, ignore_index=True)


def get_all_report_dates() -> pd.DataFrame:
    """
    获取沪深市场的全部股票报告期信息

    Returns
    -------
    DataFrame
        沪深市场的全部股票报告期信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_all_report_dates()
            报告日期       季报名称
    0   2021-06-30  2021年 半年报
    1   2021-03-31  2021年 一季报
    2   2020-12-31   2020年 年报
    3   2020-09-30  2020年 三季报
    4   2020-06-30  2020年 半年报
    5   2020-03-31  2020年 一季报
    6   2019-12-31   2019年 年报
    7   2019-09-30  2019年 三季报
    8   2019-06-30  2019年 半年报
    9   2019-03-31  2019年 一季报
    10  2018-12-31   2018年 年报
    11  2018-09-30  2018年 三季报
    12  2018-06-30  2018年 半年报
    13  2018-03-31  2018年 一季报
    14  2017-12-31   2017年 年报
    15  2017-09-30  2017年 三季报
    16  2017-06-30  2017年 半年报
    17  2017-03-31  2017年 一季报
    18  2016-12-31   2016年 年报
    19  2016-09-30  2016年 三季报
    20  2016-06-30  2016年 半年报
    21  2016-03-31  2016年 一季报
    22  2015-12-31   2015年 年报
    24  2015-06-30  2015年 半年报
    25  2015-03-31  2015年 一季报
    26  2014-12-31   2014年 年报
    27  2014-09-30  2014年 三季报
    28  2014-06-30  2014年 半年报
    29  2014-03-31  2014年 一季报
    30  2013-12-31   2013年 年报
    31  2013-09-30  2013年 三季报
    32  2013-06-30  2013年 半年报
    33  2013-03-31  2013年 一季报
    34  2012-12-31   2012年 年报
    35  2012-09-30  2012年 三季报
    36  2012-06-30  2012年 半年报
    37  2012-03-31  2012年 一季报
    38  2011-12-31   2011年 年报
    39  2011-09-30  2011年 三季报

    """
    fields = {
        'REPORT_DATE': '报告日期',
        'DATATYPE': '季报名称'
    }
    params = (
        ('type', 'RPT_LICO_FN_CPD_BBBQ'),
        ('sty', ','.join(fields.keys())),
        ('p', '1'),
        ('ps', '2000'),

    )
    url = 'https://datacenter.eastmoney.com/securities/api/data/get'
    response = requests.get(
        url,
        headers=EASTMONEY_REQUEST_HEADERS,
        params=params)
    items = jsonpath(response.json(), '$..data[:]')
    if not items:
        pd.DataFrame(columns=fields.values())
    df = pd.DataFrame(items)
    df = df.rename(columns=fields)
    df['报告日期'] = df['报告日期'].apply(lambda x: x.split()[0])
    return df


@to_numeric
def get_all_company_performance(date: str = None) -> pd.DataFrame:
    """
    获取沪深市场股票某一季度的表现情况

    Parameters
    ----------
    date : str, optional
        报告发布日期 部分可选示例如下(默认为 ``None``)

        - ``None`` : 最新季报
        - ``'2021-06-30'`` : 2021 年 Q2 季度报
        - ``'2021-03-31'`` : 2021 年 Q1 季度报

    Returns
    -------
    DataFrame
        获取沪深市场股票某一季度的表现情况

    Examples
    ---------
    >>> import efinance as ef
    >>> # 获取最新季度业绩表现
    >>> ef.stock.get_all_company_performance()
        股票代码  股票名称                  公告日     报告期    每股收益          营业收入     营业收入同比         归属净利润     归属净利润同比       报告名称
    0    000088   盐田港  2021-08-14 00:00:00  2021Q2  0.1017  3.090672e+08  34.504030  2.287045e+08   49.990304  2021年 半年报
    1    000151  中成股份  2021-08-14 00:00:00  2021Q2 -0.1342  1.830535e+08 -53.288271 -3.971708e+07 -577.129395  2021年 半年报
    2    000417  合肥百货  2021-08-14 00:00:00  2021Q2  0.1775  3.228833e+09   1.191328  1.383911e+08   43.895890  2021年 半年报
    3    000420  吉林化纤  2021-08-14 00:00:00  2021Q2  0.0188  1.679051e+09  65.706084  4.076899e+07  150.071201  2021年 半年报
    4    000534  万泽股份  2021-08-14 00:00:00  2021Q2  0.1298  2.800442e+08  21.239236  6.411993e+07   30.715838  2021年 半年报
    ..      ...   ...                  ...     ...     ...           ...        ...           ...         ...        ...
    571  002261  拓维信息  2021-07-15 00:00:00  2021Q2  0.0550  8.901777e+08  47.505282  6.071063e+07   68.323793  2021年 半年报
    572  600644  乐山电力  2021-07-15 00:00:00  2021Q2     NaN  1.257030e+09  18.079648  8.379727e+07  -14.303494  2021年 半年报
    573  603100  川仪股份  2021-07-15 00:00:00  2021Q2  0.7700  2.536000e+09  42.040204  3.040000e+08  273.372636  2021年 半年报
    574  601952  苏垦农发  2021-07-13 00:00:00  2021Q2  0.2400  4.544138e+09  11.754570  3.278197e+08    1.156936  2021年 半年报
    575  601568  北元集团  2021-07-09 00:00:00  2021Q2  0.3200  6.031506e+09  32.543303  1.167989e+09   61.053739  2021年 半年报

    >>> # 获取指定日期的季度业绩表现
    >>> ef.stock.get_all_company_performance('2020-03-31')
            股票代码   股票名称                  公告日     报告期    每股收益          营业收入     营业收入同比         归属净利润     归属净利润同比       报告名称
    0     600593  *ST圣亚  2021-04-30 00:00:00  2020Q1 -0.1848  1.320271e+07 -63.791831 -2.379923e+07  -46.022446  2020年 一季报
    1     601399   国机重装  2021-04-21 00:00:00  2020Q1  0.0003  1.825720e+09  -3.353096  2.247111e+06  -85.692860  2020年 一季报
    2     600865   百大集团  2020-12-30 00:00:00  2020Q1 -0.0200  5.444501e+07 -75.773146 -7.476827e+06 -113.174025  2020年 一季报
    3     600145  *ST新亿  2020-08-29 00:00:00  2020Q1  0.0014  3.907396e+06 -11.812618  2.174314e+06  236.963620  2020年 一季报
    4     600226   ST瀚叶  2020-06-30 00:00:00  2020Q1  0.0100  1.471848e+08 -33.907527  2.185664e+07  -73.691756  2020年 一季报
    ...      ...    ...                  ...     ...     ...           ...        ...           ...         ...        ...
    3864  002838   道恩股份  2020-04-09 00:00:00  2020Q1  0.1700  6.191659e+08  -8.019810  6.939886e+07   91.601624  2020年 一季报
    3865  603186   华正新材  2020-04-09 00:00:00  2020Q1  0.1400  4.117502e+08  -6.844813  1.763252e+07   18.870055  2020年 一季报
    3866  002007   华兰生物  2020-04-08 00:00:00  2020Q1  0.1354  6.775414e+08  -2.622289  2.472864e+08   -4.708821  2020年 一季报
    3867  002913    奥士康  2020-04-08 00:00:00  2020Q1  0.1700  4.898977e+08  -3.883035  2.524717e+07  -47.239162  2020年 一季报
    3868  600396   金山股份  2020-04-08 00:00:00  2020Q1  0.1275  2.023133e+09   0.518504  1.878432e+08  114.304022  2020年 一季报

    Notes
    -----
    当输入的日期不正确时，会输出可选的日期列表。
    你也可以通过函数 ``efinance.stock.get_all_report_dates`` 来获取可选日期

    """
    fields = {
        'SECURITY_CODE': '股票代码',
        'SECURITY_NAME_ABBR': '股票名称',
        'NOTICE_DATE': '公告日',
        'REPORTDATEWZ': '报告期',
        'BASIC_EPS': '每股收益',
        'TOTAL_OPERATE_INCOME': '营业收入',
        'TOTAL_OPERATE_INCOME_TQ': '营业收入同比',
        'PARENT_NETPROFIT': '归属净利润',
        'PARENT_NETPROFIT_TQ': '归属净利润同比',
        'REPORTDATEYW': '报告名称',
        # 'ISNEW':'是否最新'

    }
    dates = get_all_report_dates()['报告日期'].to_list()
    if date is None:
        date = dates[0]
    if date not in dates:
        rich.print('日期输入有误，可选日期如下:')
        rich.print(dates)
        return pd.DataFrame(columns=fields.values())

    date = f"(REPORTDATE=\'{date}\')"
    page = 1
    dfs: List[pd.DataFrame] = []
    while 1:
        params = (
            ('type', 'RPT_LICO_FN_CPD_BB'),
            ('source', 'DataCenter'),
            ('sty', 'SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_MARKET,REPORTDATE,REPORTDATEWZ,REPORTDATEYW,BASIC_EPS,TOTAL_OPERATE_INCOME,TOTAL_OPERATE_INCOME_TQ,PARENT_NETPROFIT,PARENT_NETPROFIT_TQ,ISNEW,NOTICE_DATE'),
            ('p', f'{page}'),
            ('ps', '500'),
            ('sr', '-1,1'),
            ('st', 'NOTICE_DATE,SECURITY_CODE'),
            ('filter',
             f'{date}(TRADE_MARKET in (0101,0102,0201,0202,0120,0220))'),
        )
        url = 'https://datacenter.eastmoney.com/securities/api/data/get'
        response = session.get(url,
                               headers=EASTMONEY_REQUEST_HEADERS,
                               params=params)
        items = jsonpath(response.json(), '$..data[:]')
        if not items:
            break
        df = pd.DataFrame(items)
        dfs.append(df)
        page += 1
    df = pd.concat(dfs, axis=0, ignore_index=True)
    df = df.rename(columns=fields)[fields.values()]
    return df
