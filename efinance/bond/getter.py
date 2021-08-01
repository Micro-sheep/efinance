import multitasking
import pandas as pd
from .config import (EASTMONEY_REQUEST_HEADERS,
                     EASTMONEY_BOND_QUOTE_FIELDS,
                     EASTMONEY_BOND_BASE_INFO_FIELDS)
from ..config import MARET_NUMBER_DICT
import requests
from typing import List, Union
from ..utils import to_numeric
import requests


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
    json_response = requests.get(url,
                                 headers=EASTMONEY_REQUEST_HEADERS,
                                 params=params).json()
    if json_response['result'] is None:
        return pd.Series(index=columns.values())
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
    获取单只或多只可转债基本信息

    Parameters
    ----------
    bond_codes : Union[str, List[str]]
        可转债代码或者可转债代码构成的字符串列表

    Returns
    -------
    Union[DataFrame, Series]
        DataFrame : 当 bond_codes 是字符串列表时
        Series : 当 bond_codes 是字符串时

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
    获取全部可转债基本信息列表

    Returns
    -------
    DataFrame
        包含可转债一些基本信息

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
    80  110227   赤化转债  600227   圣济堂  AAA  2007-10-10 00:00:00   4.500000    0.158854  2007-10-23 00:00:00  2009-05-25 00:00:00  1.6192  票面利率和付息日期:本次发行的可转债票面利率第一 年为1.5%、第二年为1.8%、第三年为2....
    81  126006  07深高债  600548   深高速  AAA  2007-10-09 00:00:00  15.000000    0.290304  2007-10-30 00:00:00  2013-10-09 00:00:00       6                                               None
    82  110971   恒源转债  600971  恒源煤电  AAA  2007-09-24 00:00:00   4.000000    5.311774  2007-10-12 00:00:00  2009-12-21 00:00:00  2.2484  票面利率为:第一年年利率1.5%,第二年年利率1.8%,第三年年利率2.1%,第四年年利率2...
    83  110567   山鹰转债  600567  山鹰国际   AA  2007-09-05 00:00:00   4.700000    0.496391  2007-09-17 00:00:00  2010-02-01 00:00:00  2.4055  票面利率和付息日期:本次发行的可转债票面利率第一年为1.4%,第二年为1.7%,第三年为2....
    84  110026   中海转债  600026  中远海能  AAA  2007-07-02 00:00:00  20.000000    1.333453  2007-07-12 00:00:00  2008-03-27 00:00:00   0.737  票面利率:第一年为1.84%,第二年为2.05%,第三年为2.26%,第四年为2.47%,第...

    """
    page = 1
    dfs: List[pd.DataFrame] = []
    columns = EASTMONEY_BOND_BASE_INFO_FIELDS
    while 1:
        params = (
            ('sortColumns', 'PUBLIC_START_DATE'),
            ('sortTypes', '-1'),
            ('pageSize', '500'),
            ('pageNumber', f'{page}'),
            ('reportName', 'RPT_BOND_CB_LIST'),
            ('columns', 'ALL'),
            ('source', 'WEB'),
            ('client', 'WEB'),
        )

        url = 'http://datacenter-web.eastmoney.com/api/data/v1/get'
        json_response = requests.get(url,
                                     headers=EASTMONEY_REQUEST_HEADERS,
                                     params=params).json()
        if json_response['result'] is None:
            break
        data = json_response['result']['data']
        df = pd.DataFrame(data).rename(
            columns=columns)[columns.values()]
        dfs.append(df)
        page += 1

    df = pd.concat(dfs)
    return df


@to_numeric
def get_realtime_quotes() -> pd.DataFrame:
    """
    获取沪深市场全部可转债行情信息

    Returns
    -------
    DataFrame
        沪深市场全部可转债行情信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_realtime_quotes()
        债券代码  债券名称    涨跌幅      最新价       最高       最低     涨跌额     换手率 动态市盈率     成交量           成交额     昨日收盘         总市值        流通市值      行情ID 市场类型
    0    123015  蓝盾转债  12.01  196.016    205.0    175.5  21.016  289.73     -  290382   562644960.0    175.0   196453900   196453900  0.123015   深A
    1    123077  汉得转债   9.81  115.744  122.971  105.401  10.344   27.31     -  255938   300981808.0    105.4  1084524984  1084524984  0.123077   深A
    2    123066  赛意转债    9.6  235.636    245.8    225.0  20.636  445.13     -  429894  1024109200.0    215.0   227571122   227571122  0.123066   深A
    3    128093  百川转债   7.97  361.703    367.9    335.5  26.703  331.33     -  538541  1911599200.0    335.0   587911694   587911694  0.128093   深A
    4    128082  华锋转债   6.96  157.836  163.769  147.089  10.264   95.79     -  210268   330316704.0  147.572   346459017   346459017  0.128082   深A
    ..      ...   ...    ...      ...      ...      ...     ...     ...   ...     ...           ...      ...         ...         ...       ...  ...
    383  123070  鹏辉转债  -3.71  176.686  179.799  174.471  -6.814   17.18     -  134937   239316754.0    183.5  1387967297  1387967297  0.123070   深A
    384  123027  蓝晓转债  -3.95  340.972  352.825  340.078 -14.027   39.08     -   41841   144141944.0  354.999   365040191   365040191  0.123027   深A
    385  113621  彤程转债  -4.25   217.37    222.5   214.41   -9.65    10.7     -   85599   187087584.0   227.02  1739351266  1739351266  1.113621   沪A
    386  123047  久吾转债  -4.84    308.3   319.52  305.382  -15.67   113.0     -  178692   554491376.0   323.97   487547470   487547470  0.123047   深A
    387  123087  明电转债  -4.93  150.801    169.0  150.302  -7.828  113.41     -  501561   789441584.0  158.629   666950599   666950599  0.123087   深A
    """
    params = (
        ('fields', ','.join(EASTMONEY_BOND_QUOTE_FIELDS)),
        ('np', '1'),
        ('fltt', '2'),
        ('invt', '2'),
        ('pn', '1'),
        ('fs', 'b:MK0354'),
        ('fid', 'f3'),
        ('po', '1'),
        ('pz', '100000'),
    )
    url = 'https://12.push2.eastmoney.com/api/qt/clist/get'
    response = requests.get(url,
                            headers=EASTMONEY_REQUEST_HEADERS,
                            params=params)
    json_response = response.json()
    df = (pd.DataFrame(json_response['data']['diff'])
            .rename(columns=EASTMONEY_BOND_QUOTE_FIELDS)
          [EASTMONEY_BOND_QUOTE_FIELDS.values()])
    df['行情ID'] = df['市场编号'].astype(str)+'.'+df['债券代码'].astype(str)
    df['市场类型'] = df['市场编号'].astype(str).apply(
        lambda x: MARET_NUMBER_DICT.get(str(x)))
    del df['市场编号']
    return df
