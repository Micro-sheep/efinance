from typing import Dict, List, Union

import multitasking
import pandas as pd
import requests

from ..common import get_deal_detail as get_deal_detail_for_bond
from ..common import get_history_bill as get_history_bill_for_bond
from ..common import get_quote_history as get_quote_history_for_bond
from ..common import get_realtime_quotes_by_fs
from ..common import get_today_bill as get_today_bill_for_bond
from ..common.config import EASTMONEY_REQUEST_HEADERS, FS_DICT, MagicConfig
from ..utils import get_quote_id, process_dataframe_and_series, to_numeric
from .config import EASTMONEY_BOND_BASE_INFO_FIELDS


@to_numeric
def get_base_info_single(bond_code: str) -> pd.Series:
    """
    获取单只债券基本信息

    Parameters
    ----------
    bond_code : str
        债券代码

    Returns
    -------
    Series
        债券的一些基本信息
    """
    columns = EASTMONEY_BOND_BASE_INFO_FIELDS
    params = (
        ('reportName', 'RPT_BOND_CB_LIST'),
        ('columns', 'ALL'),
        ('source', 'WEB'),
        ('client', 'WEB'),
        ('filter', f'(SECURITY_CODE="{bond_code}")'),
    )

    url = 'http://datacenter-web.eastmoney.com/api/data/v1/get'
    json_response = requests.get(
        url, headers=EASTMONEY_REQUEST_HEADERS, params=params
    ).json()
    if json_response['result'] is None:
        return pd.Series(index=columns.values(), dtype='object')
    items = json_response['result']['data']
    s = pd.Series(items[0]).rename(index=columns)
    s = s[columns.values()]
    return s


def get_base_info_multi(bond_codes: List[str]) -> pd.DataFrame:
    """
    获取多只债券基本信息

    Parameters
    ----------
    bond_codes : List[str]
        债券代码构成的字符串列表

    Returns
    -------
    DataFrame
        多只债券信息
    """
    ss = []

    @multitasking.task
    def start(bond_code: str) -> None:
        s = get_base_info_single(bond_code)
        ss.append(s)

    for bond_code in bond_codes:
        start(bond_code)
    multitasking.wait_for_tasks()
    df = pd.DataFrame(ss)
    return df


def get_base_info(bond_codes: Union[str, List[str]]) -> Union[pd.DataFrame, pd.Series]:
    """
    获取单只或多只债券基本信息

    Parameters
    ----------
    bond_codes : Union[str, List[str]]
        债券代码、名称 或者 债券代码、名称构成的列表

    Returns
    -------
    Union[DataFrame, Series]
        单只或多只债券基本信息

        - ``DataFrame`` : 当 ``bond_codes`` 是字符串列表时
        - ``Series`` : 当 ``bond_codes`` 是字符串时

    Examples
    --------
    >>> import efinance as ef
    >>> # 单只债券
    >>> ef.bond.get_base_info('123111')
    债券代码                                                    123111
    债券名称                                                      东财转3
    正股代码                                                    300059
    正股名称                                                      东方财富
    债券评级                                                       AA+
    申购日期                                       2021-04-07 00:00:00
    发行规模(亿)                                                    158
    网上发行中签率(%)                                             0.05877
    上市日期                                       2021-04-23 00:00:00
    到期日期                                       2027-04-07 00:00:00
    期限(年)                                                        6
    利率说明          第一年0.2%、第二年0.3%、第三年0.4%、第四年0.8%、第五年1.8%、第六年2.0%。
    dtype: object

    >>> 多只债券
    >>> bond_codes = ['123111','113050']
    >>> ef.bond.get_base_info(bond_codes)
        债券代码  债券名称    正股代码  正股名称  ...                 上市日期                 到期日期  期限(年)                                               利率说明
    0  113050  南银转债  601009  南京银行  ...  2021-07-01 00:00:00  2027-06-15 00:00:00      6  第一年0.20%、第二年0.40%、第三年0.70%、第四年1.20%
    、第五年1.70%、第...
    1  123111  东财转3  300059  东方财富  ...  2021-04-23 00:00:00  2027-04-07 00:00:00      6   第一年0.2%、第二年0.3%、第三年0.4%、第四年0.8%、第
    五年1.8%、第六年2.0%。

    """
    if isinstance(bond_codes, str):
        return get_base_info_single(bond_codes)
    elif hasattr(bond_codes, '__iter__'):
        return get_base_info_multi(bond_codes)


def get_all_base_info() -> pd.DataFrame:
    """
    获取全部债券基本信息列表

    Returns
    -------
    DataFrame
        债券一些基本信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_all_base_info()
        债券代码   债券名称    正股代码  正股名称 债券评级                 申购日期    发行规模(亿)  网上发行中签率(%)                 上市日期                 到期日期   期限(年)                                               利率说明
    0   123120   隆华转债  300263  隆华科技  AA-  2021-07-30 00:00:00   7.989283         NaN                 None  2027-07-30 00:00:00       6  第一年为0.40%、第二年为0.70%、第三年为1.00%、第四年为1.60%、第五年为2....
    1   110081   闻泰转债  600745  闻泰科技  AA+  2021-07-28 00:00:00  86.000000    0.044030                 None  2027-07-28 00:00:00       6  第一年0.10%、第二年0.20%、第三年0.30%、第四年1.50%、第五年1.80%、第...
    2   118001   金博转债  688598  金博股份   A+  2021-07-23 00:00:00   5.999010    0.001771                 None  2027-07-23 00:00:00       6  第一年0.50%、第二年0.70%、第三年1.20%、第四年1.80%、第五年2.40%、第...
    3   123119   康泰转2  300601  康泰生物   AA  2021-07-15 00:00:00  20.000000    0.014182                 None  2027-07-15 00:00:00       6  第一年为0.30%、第二年为0.50%、第三年为1.00%、第 四年为1.50%、第五年为1....
    4   113627   太平转债  603877   太平鸟   AA  2021-07-15 00:00:00   8.000000    0.000542                 None  2027-07-15 00:00:00       6  第一年0.30%、第二年0.50%、第三年1.00%、第四年1.50%、第五年1.80%、第...
    ..     ...    ...     ...   ...  ...                  ...        ...         ...                  ...                  ...     ...                                                ...
    80  110227   赤化转债  600227   圣济堂  AAA  2007-10-10 00:00:00   4.500000    0.158854  2007-10-23 00:00:00  2009-05-25 00:00:00  1.6192  票面利率和付息日期:本次发行的债券票面利率第一 年为1.5%、第二年为1.8%、第三年为2....
    81  126006  07深高债  600548   深高速  AAA  2007-10-09 00:00:00  15.000000    0.290304  2007-10-30 00:00:00  2013-10-09 00:00:00       6                                               None
    82  110971   恒源转债  600971  恒源煤电  AAA  2007-09-24 00:00:00   4.000000    5.311774  2007-10-12 00:00:00  2009-12-21 00:00:00  2.2484  票面利率为:第一年年利率1.5%,第二年年利率1.8%,第三年年利率2.1%,第四年年利率2...
    83  110567   山鹰转债  600567  山鹰国际   AA  2007-09-05 00:00:00   4.700000    0.496391  2007-09-17 00:00:00  2010-02-01 00:00:00  2.4055  票面利率和付息日期:本次发行的债券票面利率第一年为1.4%,第二年为1.7%,第三年为2....
    84  110026   中海转债  600026  中远海能  AAA  2007-07-02 00:00:00  20.000000    1.333453  2007-07-12 00:00:00  2008-03-27 00:00:00   0.737  票面利率:第一年为1.84%,第二年为2.05%,第三年为2.26%,第四年为2.47%,第...

    """
    page = 1
    dfs: List[pd.DataFrame] = []
    columns = EASTMONEY_BOND_BASE_INFO_FIELDS
    while 1:
        params = (
            ('sortColumns', 'SECURITY_CODE'),
            ('sortTypes', '-1'),
            ('pageSize', '500'),
            ('pageNumber', f'{page}'),
            ('reportName', 'RPT_BOND_CB_LIST'),
            ('columns', 'ALL'),
            ('source', 'WEB'),
            ('client', 'WEB'),
        )

        url = 'http://datacenter-web.eastmoney.com/api/data/v1/get'
        json_response = requests.get(
            url, headers=EASTMONEY_REQUEST_HEADERS, params=params
        ).json()
        if json_response['result'] is None:
            break
        data = json_response['result']['data']
        df = pd.DataFrame(data).rename(columns=columns)[columns.values()]
        dfs.append(df)
        page += 1

    df = pd.concat(dfs, ignore_index=True)
    return df


@process_dataframe_and_series(remove_columns_and_indexes=['市场编号'])
@to_numeric
def get_realtime_quotes(**kwargs) -> pd.DataFrame:
    """
    获取沪深市场全部债券实时行情信息

    Returns
    -------
    DataFrame
        沪深市场全部债券实时行情信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_realtime_quotes()
        债券代码  债券名称    涨跌幅      最新价       最高       最低      今开     涨跌额      换手率     量比 动态市盈率      成交量           成交额    昨日收盘         总市值        流通市值      行情ID 市场类型
    0    123051  今天转债  24.03   158.66    165.0    134.0   134.0   30.74   496.74  67.16     -  1388341  2185911136.0  127.92   443443594   443443594  0.123051   深A
    1    123042  银河转债  16.04  219.309    224.0   193.11   194.5  30.309  1833.99   1.34     -  3042265  6402014720.0   189.0   363794813   363794813  0.123042   深A
    2    113034  滨化转债  13.49   247.71   255.62    214.5   214.5   29.45   334.56   2.96     -  1585993  3798255024.0  218.26  1174284861  1174284861  1.113034   沪A
    3    128064  司尔转债  11.29   148.01   150.34  133.007  133.73   15.01   277.06   7.04     -   887301  1305800336.0   133.0   474009426   474009426  0.128064   深A
    4    113027  华钰转债   8.38   129.86    130.2    122.3   123.0   10.04    83.84   4.15     -   272641   346817120.0  119.82   422273164   422273164  1.113027   沪A
    ..      ...   ...    ...      ...      ...      ...     ...     ...      ...    ...   ...      ...           ...     ...         ...         ...       ...  ...
    390  113621  彤程转债  -4.45   188.57   198.22    188.0  196.01   -8.79    29.91   0.47     -   168709   326018848.0  197.36  1063693010  1063693010  1.113621   沪A
    391  128017  金禾转债  -4.86  182.676  204.989   182.61  195.16  -9.324    35.58    2.0     -   196375   375750768.0   192.0  1008366222  1008366222  0.128017   深A
    392  113548  石英转债  -5.16   250.22   267.57   246.56   262.3  -13.61   143.32   0.72     -   175893   452796304.0  263.83   307086749   307086749  1.113548   沪A
    393  128093  百川转债  -5.71  429.042   449.97  426.078   443.1 -25.958   426.86   0.36     -   693261  3032643232.0   455.0   696810974   696810974  0.128093   深A
    394  123066  赛意转债   -6.0   193.08  203.999   193.08   203.0  -12.32   323.13   0.22     -   133317   261546032.0   205.4    79660753    79660753  0.123066   深A

    """
    df = get_realtime_quotes_by_fs(FS_DICT['bond'], **kwargs)
    df.rename(columns={'代码': '债券代码', '名称': '债券名称'}, inplace=True)
    return df


def get_quote_history(
    bond_codes: Union[str, List[str]],
    beg: str = '19000101',
    end: str = '20500101',
    klt: int = 101,
    fqt: int = 1,
    **kwargs,
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    获取债券的 K 线数据

    Parameters
    ----------
    bond_codes : Union[str,List[str]]
        债券代码、名称 或者 代码、名称构成的列表
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
        债券的 K 线数据

        - ``DataFrame`` : 当 ``codes`` 是 ``str`` 时
        - ``Dict[str, DataFrame]`` : 当 ``bond_codes`` 是 ``List[str]`` 时

    Examples
    --------
    >>> import efinance as ef
    >>> # 获取单只债券日 K 行情
    >>> ef.bond.get_quote_history('123111')
        债券名称    债券代码          日期       开盘       收盘       最高       最低      成交量           成交额    振幅    涨跌幅     涨跌额    换手率
    0   东财转3  123111  2021-04-23  130.000  130.000  130.000  130.000  1836427  2.387355e+09  0.00  30.00  30.000  11.62
    1   东财转3  123111  2021-04-26  130.353  130.010  133.880  125.110  8610944  1.126033e+10  6.75   0.01   0.010  54.50
    2   东财转3  123111  2021-04-27  129.000  129.600  130.846  128.400  1820766  2.357472e+09  1.88  -0.32  -0.410  11.52
    3   东财转3  123111  2021-04-28  129.100  130.770  131.663  128.903  1467727  1.921641e+09  2.13   0.90   1.170   9.29
    4   东财转3  123111  2021-04-29  130.690  131.208  133.150  130.560  1156934  1.525974e+09  1.98   0.33   0.438   7.32
    ..   ...     ...         ...      ...      ...      ...      ...      ...           ...   ...    ...     ...    ...
    72  东财转3  123111  2021-08-09  159.600  159.300  162.990  158.690   596124  9.585751e+08  2.69  -0.34  -0.550   3.77
    73  东财转3  123111  2021-08-10  159.190  160.950  161.450  157.000   517237  8.234596e+08  2.79   1.04   1.650   3.27
    74  东财转3  123111  2021-08-11  161.110  159.850  162.300  159.400   298906  4.800711e+08  1.80  -0.68  -1.100   1.89
    75  东财转3  123111  2021-08-12  159.110  158.290  160.368  158.010   270641  4.298100e+08  1.48  -0.98  -1.560   1.71
    76  东财转3  123111  2021-08-13  158.000  158.358  160.290  157.850   250059  3.975513e+08  1.54   0.04   0.068   1.58

    """
    df = get_quote_history_for_bond(
        bond_codes, beg=beg, end=end, klt=klt, fqt=fqt, **kwargs
    )

    if isinstance(df, pd.DataFrame):

        df.rename(columns={'代码': '债券代码', '名称': '债券名称'}, inplace=True)
    elif isinstance(df, dict):
        for bond_code in df.keys():
            df[bond_code].rename(
                columns={'代码': '债券代码', '名称': '债券名称'}, inplace=True)
    return df


def get_history_bill(bond_code: str) -> pd.DataFrame:
    """
    获取单支债券的历史单子流入流出数据

    Parameters
    ----------
    bond_code : str
        债券代码

    Returns
    -------
    DataFrame
        沪深市场单只债券历史单子流入流出数据

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_history_bill('123111')

    """

    df = get_history_bill_for_bond(bond_code)
    df.rename(columns={'代码': '债券代码', '名称': '债券名称'}, inplace=True)
    return df


def get_today_bill(bond_code: str) -> pd.DataFrame:
    """
    获取单只债券最新交易日的日内分钟级单子流入流出数据

    Parameters
    ----------
    bond_code : str
        债券代码

    Returns
    -------
    DataFrame
        单只债券最新交易日的日内分钟级单子流入流出数据

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_today_bill('123111')
        债券名称    债券代码                时间      主力净流入     小单净流入      中单净流入       大单净流入     超大单净流入
    0    东财转3  123111  2021-08-13 09:31  -278046.0  319657.0   -41611.0   -278046.0        0.0
    1    东财转3  123111  2021-08-13 09:32  -988506.0  571643.0   416863.0   -988506.0        0.0
    2    东财转3  123111  2021-08-13 09:33  -990089.0  501980.0   488109.0   -990089.0        0.0
    3    东财转3  123111  2021-08-13 09:34 -1718728.0    9051.0  1709678.0  -1718728.0        0.0
    4    东财转3  123111  2021-08-13 09:35 -1653717.0 -133654.0  1787373.0  -1653717.0        0.0
    ..    ...     ...               ...        ...       ...        ...         ...        ...
    235  东财转3  123111  2021-08-13 14:56  5942063.0 -747717.0 -5194332.0  11700567.0 -5758504.0
    236  东财转3  123111  2021-08-13 14:57  5916755.0 -483170.0 -5433570.0  11963346.0 -6046591.0
    237  东财转3  123111  2021-08-13 14:58  5503692.0 -187241.0 -5316435.0  11757642.0 -6253950.0
    238  东财转3  123111  2021-08-13 14:59  5503692.0 -187241.0 -5316435.0  11757642.0 -6253950.0
    239  东财转3  123111  2021-08-13 15:00  5503692.0 -187241.0 -5316435.0  11757642.0 -6253950.0

    """
    df = get_today_bill_for_bond(bond_code)
    df.rename(columns={'代码': '债券代码', '名称': '债券名称'}, inplace=True)

    return df


def get_deal_detail(bond_code: str, max_count: int = 1000000, **kwargs) -> pd.DataFrame:
    """
    获取债券最新交易日成交明细

    Parameters
    ----------
    bond_code : str
        债券代码或者名称
    max_count : int, optional
        最近的最大数据条数, 默认为 ``1000000``

    Returns
    -------
    DataFrame
        债券最新交易日成交明细

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_deal_detail('113050')
        债券名称    债券代码        时间      昨收     成交价  成交量  单数
    0     南银转债  113050  09:15:30  122.44  122.60   21   0
    1     南银转债  113050  09:17:07  122.44  122.60   21   0
    2     南银转债  113050  09:20:52  122.44  122.60   21   0
    3     南银转债  113050  09:22:34  122.44  122.60   21   0
    4     南银转债  113050  09:23:35  122.44  122.56   21   0
    ...    ...     ...       ...     ...     ...  ...  ..
    1720  南银转债  113050  14:58:49  122.44  121.87    1   0
    1721  南银转债  113050  14:58:52  122.44  121.87    5   0
    1722  南银转债  113050  14:59:01  122.44  121.88    4   0
    1723  南银转债  113050  14:59:31  122.44  121.82  130   0
    1724  南银转债  113050  15:00:00  122.44  121.82   50   0

    """

    quote_id = ''
    if kwargs.get(MagicConfig.QUOTE_ID_MODE):
        quote_id = bond_code
    else:
        quote_id = get_quote_id(bond_code)
    columns = ['债券名称', '债券代码', '时间', '昨收', '成交价', '成交量', '单数']
    if not quote_id:
        return pd.DataFrame(columns=columns)
    df = get_deal_detail_for_bond(quote_id, max_count=max_count)
    df.rename(columns={'代码': '债券代码', '名称': '债券名称'}, inplace=True)
    return df
