from typing import Dict, List, Union
from retry import retry
import pandas as pd
import requests
import multitasking
import signal
from tqdm import tqdm
from .utils import (gen_secid,
                    get_stock_market_type,
                    update_local_market_stocks_info)
from ..utils import to_numeric
from .config import (EastmoneyKlines,
                     EastmoneyHeaders,
                     EastmoneyBills,
                     EastmoneyQuotes,
                     EastmoneyStockBaseInfo)

signal.signal(signal.SIGINT, multitasking.killall)


@to_numeric
def get_base_info_single(stock_code: str) -> pd.Series:
    """
    获取单股票基本信息

    Parameters
    ----------
    stock_code : str
        6 位股票代码

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
        ('secid', gen_secid(stock_code)),

    )

    json_response = requests.get('http://push2.eastmoney.com/api/qt/stock/get',
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
        6 位股票代码列表

    Returns
    -------
    DataFrame
        包含多只股票基本信息
    """

    ss = []

    @multitasking.task
    @retry(tries=3, delay=1)
    def start(stock_code: str):
        s = get_base_info_single(stock_code)
        ss.append(s)
        bar.update()
        bar.set_description(f'processing {stock_code}')
    bar = tqdm(total=len(stock_codes))
    for stock_code in stock_codes:
        start(stock_code)
    multitasking.wait_for_tasks()
    df = pd.DataFrame(ss)
    return df


@to_numeric
def get_base_info(stock_codes: Union[str, List[str]]) -> Union[pd.Series, pd.DataFrame]:
    """
    Parameters
    ----------
    stock_codes : Union[str, List[str]]
        6 位股票代码 或 6 位股票代码构成的列表

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
    市盈率                    15.59
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
    股票代码  股票名称  市盈率(动)    市盈率  所处行业           总市值          流通市值    板块编号   ROE      净利率           净利润      毛利率
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
                             klt: int = 101, fqt: int = 1) -> pd.DataFrame:
    """
    获取单只股票k线数据

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

    Returns
    -------
    DataFrame
        包含股票k线数据
    """

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

    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'

    json_response = requests.get(
        url, headers=EastmoneyHeaders, params=params).json()

    data = json_response.get('data')
    if data is None:
        return pd.DataFrame(columns=columns)
    # 股票名称
    stock_name = data['name']
    klines: List[str] = data['klines']
    rows = [kline.split(',') for kline in klines]
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
    if total != 0:
        update_local_market_stocks_info()

    @multitasking.task
    @retry(tries=3, delay=1)
    def start(stock_code: str):
        _df = get_quote_history_single(
            stock_code, beg=beg, end=end, klt=klt, fqt=fqt)
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
    获取k线数据

    Parameters
    ----------
    stock_codes : Union[str,List[str]]
        6 位股票代码 或者 6 位股票代码构成的列表
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
        股票名称    股票代码          日期       开盘       收盘       最高       最低     成交量             成交额     振幅    涨跌幅     涨跌额    换手率
    0     贵州茅台  600519  2001-08-27   -70.44   -70.24   -69.79   -70.77  406318   1410347000.00  -1.38   1.15    0.82  56.83
    1     贵州茅台  600519  2001-08-28   -70.35   -69.97   -69.95   -70.42  129647    463463000.00  -0.67   0.38    0.27  18.13
    2     贵州茅台  600519  2001-08-29   -69.95   -70.07   -69.95   -70.13   53252    194689000.00  -0.26  -0.14   -0.10   7.45
    3     贵州茅台  600519  2001-08-30   -70.09   -69.93   -69.85   -70.15   48013    177558000.00  -0.43   0.20    0.14   6.72
    4     贵州茅台  600519  2001-08-31   -69.92   -69.94   -69.82   -69.99   23231     86231000.00  -0.24  -0.01   -0.01   3.25
    ...    ...     ...         ...      ...      ...      ...      ...     ...             ...    ...    ...     ...    ...
    4724  贵州茅台  600519  2021-06-08  2260.00  2191.00  2279.99  2161.15   47314  10479943168.00   5.23  -3.52  -80.00   0.38
    4725  贵州茅台  600519  2021-06-09  2192.00  2199.50  2214.00  2160.11   25502   5591378944.00   2.46   0.39    8.50   0.20
    4726  贵州茅台  600519  2021-06-10  2195.00  2238.48  2251.37  2190.08   25567   5707338496.00   2.79   1.77   38.98   0.20
    4727  贵州茅台  600519  2021-06-11  2239.00  2178.81  2244.00  2178.81   33971   7513797120.00   2.91  -2.67  -59.67   0.27
    4728  贵州茅台  600519  2021-06-15  2195.10  2186.60  2208.88  2148.00   19079   4157285376.00   2.79   0.36    7.79   0.15
    >>> # 获取多只给股票历史行情（日 k）
    >>> ef.stock.get_quote_history(['600519','300750'])
    {'300750':      股票名称    股票代码          日期      开盘      收盘      最高      最低     成交量            成交额     振幅    涨跌幅    涨跌额   换手率
    0    宁德时代  300750  2018-06-11   29.81   35.84   35.84   29.81     788     2845471.00  24.33  44.63  11.06  0.04
    1    宁德时代  300750  2018-06-12   39.46   39.46   39.46   39.46     266     1058375.00   0.00  10.10   3.62  0.01
    2    宁德时代  300750  2018-06-13   43.44   43.44   43.44   43.44     450     1972314.00   0.00  10.09   3.98  0.02
    3    宁德时代  300750  2018-06-14   47.82   47.82   47.82   47.82     743     3578184.00   0.00  10.08   4.38  0.03
    4    宁德时代  300750  2018-06-15   52.64   52.64   52.64   52.64    2565    13595030.00   0.00  10.08   4.82  0.12
    ..    ...     ...         ...     ...     ...     ...     ...     ...            ...    ...    ...    ...   ...
    727  宁德时代  300750  2021-06-08  404.00  409.59  424.85  404.00  166317  6887633920.00   5.12   0.51   2.09  1.23
    728  宁德时代  300750  2021-06-09  409.00  409.37  416.00  403.00   93582  3829137536.00   3.17  -0.05  -0.22  0.69
    729  宁德时代  300750  2021-06-10  410.09  434.63  444.66  410.09  193502  8400201728.00   8.44   6.17  25.26  1.43
    730  宁德时代  300750  2021-06-11  443.00  451.98  457.84  430.06  197961  8816469248.00   6.39   3.99  17.35  0.86
    731  宁德时代  300750  2021-06-15  453.00  445.31  455.90  435.50   62061  2761012304.00   4.51  -1.48  -6.67  0.27
    [732 rows x 13 columns],
    '600519':       股票名称    股票代码          日期       开盘       收盘       最高       最低     成交量             成交额     振幅    涨跌幅     涨跌额    换手率
    0     贵州茅台  600519  2001-08-27   -70.44   -70.24   -69.79   -70.77  406318   1410347000.00  -1.38   1.15    0.82  56.83
    1     贵州茅台  600519  2001-08-28   -70.35   -69.97   -69.95   -70.42  129647    463463000.00  -0.67   0.38    0.27  18.13
    2     贵州茅台  600519  2001-08-29   -69.95   -70.07   -69.95   -70.13   53252    194689000.00  -0.26  -0.14   -0.10   7.45
    3     贵州茅台  600519  2001-08-30   -70.09   -69.93   -69.85   -70.15   48013    177558000.00  -0.43   0.20    0.14   6.72
    4     贵州茅台  600519  2001-08-31   -69.92   -69.94   -69.82   -69.99   23231     86231000.00  -0.24  -0.01   -0.01   3.25
    ...    ...     ...         ...      ...      ...      ...      ...     ...             ...    ...    ...     ...    ...
    4724  贵州茅台  600519  2021-06-08  2260.00  2191.00  2279.99  2161.15   47314  10479943168.00   5.23  -3.52  -80.00   0.38
    4725  贵州茅台  600519  2021-06-09  2192.00  2199.50  2214.00  2160.11   25502   5591378944.00   2.46   0.39    8.50   0.20
    4726  贵州茅台  600519  2021-06-10  2195.00  2238.48  2251.37  2190.08   25567   5707338496.00   2.79   1.77   38.98   0.20
    4727  贵州茅台  600519  2021-06-11  2239.00  2178.81  2244.00  2178.81   33971   7513797120.00   2.91  -2.67  -59.67   0.27
    4728  贵州茅台  600519  2021-06-15  2195.10  2192.15  2208.88  2148.00   19325   4211086880.00   2.79   0.61   13.34   0.15
    [4729 rows x 13 columns]}
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
        包含沪深全市场上市公司的最新行情信息（涨跌幅、换手率等信息）

    Examples
    --------
    >>> import efinance as ef
    >>> ef.stock.get_realtime_quotes()
        股票代码  沪/深  股票名称     涨跌幅    最新价    涨跌额    换手率    动态市盈率     成交量          成交额   昨日收盘          总市值        流通市值
    0     301026    0   N浩通  482.25  120.0  86.95   22.6    41.88   54650  589243856.0  18.03  11897733403  2538239824
    1     688501    1   N青达  171.05   30.8  18.08   15.6  1738.65   33557   95991961.0  10.57   2712295500   616379337
    2     688590    1  新致软件   13.88  24.58   2.92   9.44    99.18   36513   85568664.0  21.04   4361253829   926767050
    3     300141    0  和顺电气   12.77  12.78   1.36   7.85    457.5  130063  156199019.0  10.65   3049154046  1988740932
    4     300061    0  旗天科技   12.27   9.87   1.06   5.33   -99.24  290239  276575712.0   8.64   6411158983  5278000424
    ...      ...  ...   ...     ...    ...    ...    ...      ...     ...          ...    ...          ...         ...
    4565  603518    1  锦泓集团   -9.98  21.74  -2.41   0.09    16.39    2600    5652400.0  24.15   6205243743  6152967370
    4566  002847    0  盐津铺子   -10.0  77.48  -8.61   0.09    30.55     969    7507812.0  86.09  10022812800  8778099854
    4567  002647    0  仁东控股  -10.03   8.52  -0.95   0.35  -128.89   19789   16860228.0   9.47   4770660258  4770660258
    4568  300719    0  安达维尔  -11.36   14.0  -1.67   2.36  -592.87   42761   56988503.0   14.7   3310001128  2360073500
    4569  301027    0   C华蓝  -14.23  28.88  -4.18  11.05    35.78   38584  101747921.0  29.38   3704400000   879549275
    [4570 rows x 13 columns]
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
        ('fields', fields),

    )

    json_response = requests.get(
        'http://76.push2.eastmoney.com/api/qt/clist/get',
        headers=EastmoneyHeaders,
        params=params).json()
    df = (pd.DataFrame(json_response['data']['diff'])
          .rename(columns=EastmoneyQuotes)
          [columns])
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
        6 位股票代码

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
    klines: List[str] = data['klines']
    rows = [kline.split(',') for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    df.insert(0, '股票代码', [stock_code for _ in range(len(df))])
    return df


@to_numeric
def get_latest_stock_info(stock_codes: List[str]) -> pd.DataFrame:
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
    >>> ef.stock.get_latest_stock_info(['600519','300750'])
        最新价  最新涨跌幅    股票代码  股票简称
    0  2192.00   0.61  600519  贵州茅台
    1   443.03  -1.98  300750  宁德时代
    """

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


@to_numeric
def get_top10_stock_holder_info(stock_code: str, top: int = 4) -> pd.DataFrame:
    """
    获取沪深市场指定股票前十大股东信息

    Parameters
    ----------
    stock_code : str
        6 位股票代码
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

    def gen_fc(stock_code: str) -> str:
        """
        生成东方财富专用的东西

        Parameters
        ----------
        stock_code : str
            6 位股票代码

        Returns
        -------
        str
            指定格式的字符串
        """

        # 沪市指数
        _type = get_stock_market_type(stock_code)
        _type = int(_type)
        # 深市
        if _type == 0:
            return f'{stock_code}02'
        # 沪市
        return f'{stock_code}01'

    def get_public_dates(stock_code: str, top: int = 4) -> List[str]:
        """
        获取指定股票公开股东信息的日期

        Parameters
        ----------
        stock_code : str
            6 位 A 股股票代码
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
        fc = gen_fc(stock_code)
        data = {"fc": fc}
        response = requests.post(
            'https://emh5.eastmoney.com/api/GuBenGuDong/GetFirstRequest2Data', headers=headers, json=data)
        items: list[dict] = response.json()[
            'Result']['SDLTGDBGQ']
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
        response = requests.post(
            'https://emh5.eastmoney.com/api/GuBenGuDong/GetShiDaLiuTongGuDong',
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
