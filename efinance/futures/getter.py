from typing import List, Union

import pandas as pd

from ..common import get_deal_detail as get_deal_detail_for_futures
from ..common import get_quote_history as get_quote_history_for_futures
from ..common import get_realtime_quotes_by_fs
from ..common.config import FS_DICT
from ..utils import process_dataframe_and_series


def get_futures_base_info() -> pd.DataFrame:
    """
    获取四个交易所全部期货基本信息

    Returns
    -------
    DataFrame
        四个交易所全部期货一些基本信息

    Examples
    --------
    >>> import efinance as ef
    >>> ef.futures.get_futures_base_info()
        期货代码      期货名称        行情ID       市场类型
    0       ZCM     动力煤主力     115.ZCM        郑商所
    1     ZC201    动力煤201   115.ZC201        郑商所
    2        jm      焦炭主力      114.jm        大商所
    3     j2201    焦炭2201   114.j2201        大商所
    4       jmm      焦煤主力     114.jmm        大商所
    ..      ...       ...         ...        ...
    846  jm2109    焦煤2109  114.jm2109        大商所
    847  071108    IH2108    8.071108        中金所
    848  070131   IH次主力合约    8.070131        中金所
    849  070120    IH当月连续     8.07012        中金所
    850  lu2109  低硫燃油2109  142.lu2109  上海能源期货交易所

    Notes
    -----
    这里的 行情ID 主要作用是为使用函数 ``efinance.futures.get_quote_history``
    获取期货行情信息提供参数
    """
    columns = ["期货代码", "期货名称", "行情ID", "市场类型"]
    df = get_realtime_quotes()
    df = df[columns]
    return df


def get_quote_history(
    quote_ids: Union[str, List[str]],
    beg: str = "19000101",
    end: str = "20500101",
    klt: int = 101,
    fqt: int = 1,
    **kwargs
) -> pd.DataFrame:
    """
    获取期货历史行情信息

    Parameters
    ----------
    quote_ids : Union[str, List[str]]
        一个期货 或者多个期货 行情ID 构成的列表
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
        期货的 K 线数据

        - ``DataFrame`` : 当 ``secids`` 是 ``str`` 时
        - ``Dict[str, DataFrame]`` : 当 ``quote_ids`` 是 ``List[str]`` 时

    Examples
    --------
    >>> import efinance as ef
    >>> # 获取全部期货行情ID列表
    >>> quote_ids = ef.futures.get_realtime_quotes()['行情ID']
    >>> # 指定单个期货的行情ID(以上面获得到的行情ID列表为例)
    >>> quote_id = quote_ids[0]
    >>> # 查看第一个行情ID
    >>> quote_ids[0]
    '115.ZCM'
    >>> # 获取第行情ID为第一个的期货日 K 线数据
    >>> ef.futures.get_quote_history(quote_id)
        期货代码   期货名称          日期     开盘     收盘     最高     最低    成交量           成交额    振幅   涨跌幅   涨跌额  换手率
    0     ZCM  动力煤主力  2015-05-18  440.0  437.6  440.2  437.6     64  2.806300e+06  0.00  0.00   0.0  0.0
    1     ZCM  动力煤主力  2015-05-19  436.0  437.0  437.6  436.0      6  2.621000e+05  0.36 -0.32  -1.4  0.0
    2     ZCM  动力煤主力  2015-05-20  436.8  435.8  437.0  434.8      8  3.487500e+05  0.50 -0.23  -1.0  0.0
    3     ZCM  动力煤主力  2015-05-21  438.0  443.2  446.8  437.8     37  1.631850e+06  2.06  1.65   7.2  0.0
    4     ZCM  动力煤主力  2015-05-22  439.2  441.4  443.8  439.2     34  1.502500e+06  1.04  0.09   0.4  0.0
    ...   ...    ...         ...    ...    ...    ...    ...    ...           ...   ...   ...   ...  ...
    1524  ZCM  动力煤主力  2021-08-17  755.0  770.8  776.0  750.6  82373  6.288355e+09  3.25 -1.26  -9.8  0.0
    1525  ZCM  动力煤主力  2021-08-18  770.8  776.8  785.8  766.0  77392  6.016454e+09  2.59  1.76  13.4  0.0
    1526  ZCM  动力煤主力  2021-08-19  776.8  777.6  798.0  764.6  97229  7.597474e+09  4.30  0.03   0.2  0.0
    1527  ZCM  动力煤主力  2021-08-20  778.0  793.0  795.0  775.2  70549  5.553617e+09  2.53  1.48  11.6  0.0
    1528  ZCM  动力煤主力  2021-08-23  796.8  836.6  843.8  796.8  82954  6.850341e+09  5.97  6.28  49.4  0.0

    >>> # 指定多个期货的 行情ID
    >>> quote_ids = ['115.ZCM','115.ZC109']
    >>> futures_df = ef.futures.get_quote_history(quote_ids)
    >>> type(futures_df)
    <class 'dict'>
    >>> futures_df.keys()
    dict_keys(['115.ZC109', '115.ZCM'])
    >>> futures_df['115.ZCM']
        期货名称 期货代码          日期     开盘     收盘     最高     最低    成交量           成交额    振幅   涨跌幅   涨跌额  换手率
    0     动力煤主力  ZCM  2015-05-18  440.0  437.6  440.2  437.6     64  2.806300e+06  0.00  0.00   0.0  0.0
    1     动力煤主力  ZCM  2015-05-19  436.0  437.0  437.6  436.0      6  2.621000e+05  0.36 -0.32  -1.4  0.0
    2     动力煤主力  ZCM  2015-05-20  436.8  435.8  437.0  434.8      8  3.487500e+05  0.50 -0.23  -1.0  0.0
    3     动力煤主力  ZCM  2015-05-21  438.0  443.2  446.8  437.8     37  1.631850e+06  2.06  1.65   7.2  0.0
    4     动力煤主力  ZCM  2015-05-22  439.2  441.4  443.8  439.2     34  1.502500e+06  1.04  0.09   0.4  0.0
    ...     ...  ...         ...    ...    ...    ...    ...    ...           ...   ...   ...   ...  ...
    1524  动力煤主力  ZCM  2021-08-17  755.0  770.8  776.0  750.6  82373  6.288355e+09  3.25 -1.26  -9.8  0.0
    1525  动力煤主力  ZCM  2021-08-18  770.8  776.8  785.8  766.0  77392  6.016454e+09  2.59  1.76  13.4  0.0
    1526  动力煤主力  ZCM  2021-08-19  776.8  777.6  798.0  764.6  97229  7.597474e+09  4.30  0.03   0.2  0.0
    1527  动力煤主力  ZCM  2021-08-20  778.0  793.0  795.0  775.2  70549  5.553617e+09  2.53  1.48  11.6  0.0
    1528  动力煤主力  ZCM  2021-08-23  796.8  836.6  843.8  796.8  82954  6.850341e+09  5.97  6.28  49.4  0.0

    """
    df = get_quote_history_for_futures(
        quote_ids, beg=beg, end=end, klt=klt, fqt=fqt, quote_id_mode=True
    )
    if isinstance(df, pd.DataFrame):

        df.rename(columns={"代码": "期货代码", "名称": "期货名称"}, inplace=True)
    elif isinstance(df, dict):
        for stock_code in df.keys():
            df[stock_code].rename(
                columns={"代码": "期货代码", "名称": "期货名称"}, inplace=True
            )
            # NOTE 扩展接口 设定此关键词即返回 DataFrame 而不是 dict
        if kwargs.get("return_df"):
            df: pd.DataFrame = pd.concat(df, axis=0, ignore_index=True)
    return df


@process_dataframe_and_series(remove_columns_and_indexes=["市场编号"])
def get_realtime_quotes() -> pd.DataFrame:
    """
    获取期货最新行情总体情况

    Returns
    -------
    DataFrame
        期货市场的最新行情信息（涨跌幅、换手率等信息）

    Examples
    --------
    >>> import efinance as ef
    >>> ef.futures.get_realtime_quotes()
        期货代码      期货名称   涨跌幅     最新价      最高      最低      今开    涨跌额 换手率    量比 动态市盈率     成交量            成交额    昨日收盘     总市值 流通市值        行情ID       市场类型
    0       ZCM     动力煤主力  6.28   836.6   843.8   796.8   796.8   49.4   -  2.82     -   82954   6850341376.0   793.0       -    -     115.ZCM        郑商所
    1     ZC201    动力煤201  6.28   836.6   843.8   796.8   796.8   49.4   -  2.82     -   82954   6850341376.0   793.0       -    -   115.ZC201        郑商所
    2        jm      焦炭主力  5.39  2980.0  2982.0  2833.0  2834.0  152.5   -   1.4     -  166433  48567923456.0  2830.5       -    -      114.jm        大商所
    3     j2201    焦炭2201  5.39  2980.0  2982.0  2833.0  2834.0  152.5   -   1.4     -  166433  48567923456.0  2830.5       -    -   114.j2201        大商所
    4       jmm      焦煤主力   5.0  2354.0  2360.0  2221.0  2221.0  112.0   -  1.42     -  238671  32924591872.0  2238.0       -    -     114.jmm        大商所
    ..      ...       ...   ...     ...     ...     ...     ...    ...  ..   ...   ...     ...            ...     ...     ...  ...         ...        ...
    846  jm2109    焦煤2109 -2.28  2748.0  2882.5  2688.0  2845.0  -64.0   -  1.85     -   34029   5656982528.0  2866.0       -    -  114.jm2109        大商所
    847  071108    IH2108 -2.52  3060.0  3130.0  3043.0  3111.2  -79.0   -  0.39     -   14384  13315567616.0  3139.2  918000    -    8.071108        中金所
    848  070131   IH次主力合约 -2.52  3060.0  3130.0  3043.0  3111.2  -79.0   -  0.57     -   14384  13315567616.0  3139.2  918000    -    8.070131        中金所
    849  070120    IH当月连续 -2.52  3060.0  3130.0  3043.0  3111.2  -79.0   -  0.39     -   14384  13315567616.0  3139.2  918000    -    8.070120        中金所
    850  lu2109  低硫燃油2109 -3.79  3123.0  3127.0  3121.0  3121.0 -123.0   -     -     -      22       687420.0  3143.0       -    -  142.lu2109  上海能源期货交易所

    Notes
    -----
    如果不记得行情ID,则可以调用函数 ``efinance.futures.get_realtime_quotes`` 获取
    接着便可以使用函数 ``efinance.futures.get_quote_history``
    来获取期货 K 线数据

    """
    fs = FS_DICT["futures"]
    df = get_realtime_quotes_by_fs(fs)
    df = df.rename(columns={"代码": "期货代码", "名称": "期货名称"})
    return df


def get_deal_detail(quote_id: str, max_count: int = 1000000) -> pd.DataFrame:
    """
    获取期货最新交易日成交明细

    Parameters
    ----------
    quote_id : str
        期货行情ID
    max_count : int, optional
        最大返回条数,  默认为 ``1000000``

    Returns
    -------
    DataFrame
        期货最新交易日成交明细

    Notes
    -----
    行情ID 格式参考 ``efinance.futures.get_futures_base_info`` 中得到的数据

    Examples
    --------
    >>> import efinance as ef
    >>> ef.futures.get_deal_detail('115.ZCM',3)
        期货名称 期货代码        时间   昨收    成交价  成交量     单数
    0  动力煤主力  ZCM  21:00:00  0.0  879.0   23    0.0
    1  动力煤主力  ZCM  21:00:00  0.0  879.0    0 -373.0
    2  动力煤主力  ZCM  21:00:00  0.0  879.0    0    0.0

    """
    df = get_deal_detail_for_futures(quote_id, max_count=max_count)
    df.rename(columns={"代码": "期货代码", "名称": "期货名称"}, inplace=True)
    return df
