import pandas as pd
from .config import (EASTMONEY_REQUEST_HEADERS,
                     EASTMONEY_BOND_QUOTE_FIELDS)
from ..config import MARET_NUMBER_DICT
import requests
from typing import List
from ..utils import to_numeric
import requests


def get_bond_table() -> pd.DataFrame:
    """
    获取可转债列表

    Returns
    -------
    DataFrame
        包含可转债一些基本信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.bond.get_bond_table()
        债券代码   债券名称    正股代码  正股名称 债券评级                 申购日期
    0   123120   隆华转债  300263  隆华科技  AA-  2021-07-30 00:00:00
    1   110081   闻泰转债  600745  闻泰科技  AA+  2021-07-28 00:00:00
    2   118001   金博转债  688598  金博股份   A+  2021-07-23 00:00:00
    3   123119   康泰转2  300601  康泰生物   AA  2021-07-15 00:00:00
    4   113627   太平转债  603877   太平鸟   AA  2021-07-15 00:00:00
    ..     ...    ...     ...   ...  ...                  ...
    80  110227   赤化转债  600227   圣济堂  AAA  2007-10-10 00:00:00
    81  126006  07深高债  600548   深高速  AAA  2007-10-09 00:00:00
    82  110971   恒源转债  600971  恒源煤电  AAA  2007-09-24 00:00:00
    83  110567   山鹰转债  600567  山鹰国际   AA  2007-09-05 00:00:00
    84  110026   中海转债  600026  中远海能  AAA  2007-07-02 00:00:00

    """
    page = 1
    dfs: List[pd.DataFrame] = []
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
        columns = {
            'SECURITY_CODE': '债券代码',
            'SECURITY_NAME_ABBR': '债券名称',
            'CONVERT_STOCK_CODE': '正股代码',
            'SECURITY_SHORT_NAME': '正股名称',
            'RATING': '债券评级',
            'PUBLIC_START_DATE': '申购日期',

        }
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
        债券代码  债券名称    涨跌幅      最新价     涨跌额      换手率 动态市盈率      成交量           成交额    昨日收盘         总市值        流通市值      行情ID 市场类型
    0    128093  百川转债  22.73    308.0    53.9  1231.99     -  2027056  5443504896.0   237.1   478796559   478796559  0.128093   深A
    1    110074  精达转债  17.36    259.0   38.04    93.64     -   530556  1312028976.0  219.16  1457252762  1457252762  1.110074   沪A
    2    113047  旗滨转债  16.36    195.0   26.98    29.48     -   442252   820405952.0  164.93  2878650000  2878650000  1.113047   沪A
    3    123089  九洲转2  15.38    156.0  20.698    186.2     -   677158  1019904000.0  134.58   564702298   564702298  0.123089   深A
    4    123074  隆利转债  15.03    196.6   24.91   1144.2     -  2379653  4380623616.0   165.7   396422482   396422482  0.123074   深A
    ..      ...   ...    ...      ...     ...      ...   ...      ...           ...     ...         ...         ...       ...  ...
    383  128108  蓝帆转债  -1.43  122.199  -1.748     7.99     -   121936   146871594.0  121.82  1831785652  1831785652  0.128108   深A
    384  110043  无锡转债   -1.5    119.0   -1.78     1.39     -    40634    47674406.0   118.7  3415662530  3415662530  1.110043   沪A
    385  128026  众兴转债  -1.63  121.898  -1.956    47.21     -   193308   231279838.0  119.82   482576233   482576233  0.128026   深A
    386  123065  宝莱转债   -1.7   112.35   -1.91     28.5     -    62381    69405273.0   112.6   242259344   242259344  0.123065   深A
    387  128053  尚荣转债   -2.8    142.0    -4.0   327.41     -   623980   867909216.0   143.0   264907729   264907729  0.128053   深A

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
