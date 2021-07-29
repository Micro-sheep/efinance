import os
import re
from retry import retry
from typing import List, Union
import pandas as pd
import requests
from tqdm import tqdm
import multitasking
import signal
from .config import EastmoneyFundHeaders
from ..utils import to_numeric
signal.signal(signal.SIGINT, multitasking.killall)


@to_numeric
def get_quote_history(fund_code: str, pz: int = 40000) -> pd.DataFrame:
    """
    根据基金代码和要获取的页码抓取基金净值信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    pz : int, optional
        页码, 默认为 40000 以获取全部历史数据

    Returns
    -------
    DataFrame
        包含基金历史净值等数据

    Examples
    --------
    >>> import efinance as ef
    >>> ef.fund.get_quote_history('161725')
        日期    单位净值    累计净值     涨跌幅
    0    2021-06-11  1.5188  3.1499   -3.09
    1    2021-06-10  1.5673  3.1984    1.69
    2    2021-06-09  1.5412  3.1723    0.11
    3    2021-06-08  1.5395  3.1706    -6.5
    4    2021-06-07  1.6466  3.2777    1.61
    ...         ...     ...     ...     ...
    1469 2015-06-08  1.0380  1.0380  2.5692
    1470 2015-06-05  1.0120  1.0120  1.5045
    1471 2015-06-04  0.9970  0.9970      --
    1472 2015-05-29  0.9950  0.9950      --
    1473 2015-05-27  1.0000  1.0000      --
    
    """

    data = {
        'FCODE': f'{fund_code}',
        'IsShareNet': 'true',
        'MobileKey': '1',
        'appType': 'ttjj',
        'appVersion': '6.2.8',
        'cToken': '1',
        'deviceid': '1',
        'pageIndex': '1',
        'pageSize': f'{pz}',
        'plat': 'Iphone',
        'product': 'EFund',
        'serverVersion': '6.2.8',
        'uToken': '1',
        'userId': '1',
        'version': '6.2.8'
    }
    url = 'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNHisNetList'
    json_response = requests.get(
        url, headers=EastmoneyFundHeaders, data=data).json()
    rows = []
    columns = ['日期', '单位净值', '累计净值', '涨跌幅']
    if json_response is None:
        return pd.DataFrame(rows, columns=columns)
    datas = json_response['Datas']
    if len(datas) == 0:
        return pd.DataFrame(rows, columns=columns)
    rows = []
    for stock in datas:
        date = stock['FSRQ']
        rows.append({
            '日期': date,
            '单位净值': stock['DWJZ'],
            '累计净值': stock['LJJZ'],
            '涨跌幅': stock['JZZZL']
        })

    df = pd.DataFrame(rows)
    df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')

    df['累计净值'] = pd.to_numeric(df['累计净值'], errors='coerce')

    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    return df


@to_numeric
def get_realtime_increase_rate(fund_codes: Union[List[str], str]) -> pd.DataFrame:
    """
    获取基金实时估算涨跌幅度

    Parameters
    ----------
    fund_codes : Union[List[str], str]
        6 位基金代码或者 6 位基金代码构成的字符串列表

    Returns
    -------
    DataFrame
        单只或者多只基金实时估算涨跌情况
    Examples
    --------
    >>> import efinance as ef
    >>> # 单只基金
    >>> ef.fund.get_realtime_increase_rate('161725')
        基金代码              名称  估算涨跌幅              估算时间
    0  161725  招商中证白酒指数(LOF)A  -0.64  2021-06-15 11:13
    >>> # 多只基金
    >>> ef.fund.get_realtime_increase_rate(['161725','005827'])
        基金代码              名称  估算涨跌幅              估算时间
    0  161725  招商中证白酒指数(LOF)A  -0.60  2021-06-15 11:16
    1  005827       易方达蓝筹精选混合  -1.36  2021-06-15 11:16
    """

    if not isinstance(fund_codes, list):
        fund_codes = [fund_codes]
    data = {
        'pageIndex': '1',
        'pageSize': '300000',
        'Sort': '',
        'Fcodes': ",".join(fund_codes),
        'SortColumn': '',
        'IsShowSE': 'false',
        'P': 'F',
        'deviceid': '3EA024C2-7F22-408B-95E4-383D38160FB3',
        'plat': 'Iphone',
        'product': 'EFund',
        'version': '6.2.8',
    }

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo', headers=EastmoneyFundHeaders, data=data).json()
    data_list = json_response['Datas']

    columns = ['基金代码', '名称', '估算涨跌幅', '估算时间']
    rows = []
    for fund in data_list:
        code = fund['FCODE']
        name = fund['SHORTNAME']
        rate = fund['GSZZL']
        gztime = fund['GZTIME']
        rows.append([code, name, rate, gztime])
    df = pd.DataFrame(rows, columns=columns)
    return df


def get_fund_codes(ft: str = None) -> pd.DataFrame:
    """
    获取天天基金网公开的全部公墓基金名单

    Parameters
    ----------
    ft : str, optional
        基金类型
            'zq' : 债券类型基金
            'gp' : 股票类型基金
            None : 全部

    Returns
    -------
    DataFrame
        包含天天基金网基金名单数据

    Examples
    --------
    >>> import efinance as ef
    >>> # 全部类型的基金
    >>> ef.fund.get_fund_codes()
    >>> # 股票型基金
    >>> ef.fund.get_fund_codes(ft = 'gp')
        基金代码                  基金简称
    0     003834              华夏能源革新股票
    1     005669            前海开源公用事业股票
    2     004040             金鹰医疗健康产业A
    3     517793                 1.20%
    4     004041             金鹰医疗健康产业C
    ...      ...                   ...
    1981  012503      国泰中证环保产业50ETF联接A
    1982  012517  国泰中证细分机械设备产业主题ETF联接C
    1983  012600             中银内核驱动股票C
    1984  011043             国泰价值先锋股票C
    1985  012516  国泰中证细分机械设备产业主题ETF联接A
    [1986 rows x 2 columns]
    """

    params = [
        ('op', 'ph'),
        ('dt', 'kf'),
        ('rs', ''),
        ('gs', '0'),
        ('sc', '6yzf'),
        ('st', 'desc'),
        ('qdii', ''),
        ('tabSubtype', ',,,,,'),
        ('pi', '1'),
        ('pn', '50000'),
        ('dx', '1'),
        ('v', '0.09350685300919159'),
    ]
    headers = {
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
        'Accept': '*/*',
        'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }
    if ft is not None and ft in ['gp', 'zq']:
        params.append(('ft', ft))

    response = requests.get(
        'http://fund.eastmoney.com/data/rankhandler.aspx', headers=headers, params=params)
    results = re.findall('(\d{6}),(.*?),', response.text)
    columns = ['基金代码', '基金简称']
    results = re.findall('(\d{6}),(.*?),', response.text)
    df = pd.DataFrame(results, columns=columns)
    return df


@to_numeric
def get_inverst_position(fund_code: str, dates: Union[str, List[str]] = None) -> pd.DataFrame:
    """
    获取基金持仓占比信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    dates : Union[str, List[str]], optional
        日期或日期组成的列表
        例如：
            None : 表示最新公开持仓数据的日期
            '2020-09-30' 表示指定日期数据

    Returns
    -------
    DataFrame
        包含指定基金特定日期的公开持仓信息
    Examples
    --------
    >>> import efinance as ef
    >>> # 获取最新公开的持仓数据
    >>> ef.fund.get_inverst_position('161725')
     基金代码    股票代码  股票简称   持仓占比  较上期变化        公开日期
    0  161725  000858   五粮液  14.88   1.45  2021-06-30
    1  161725  600519  贵州茅台  14.16  -0.86  2021-06-30
    2  161725  600809  山西汾酒  14.03  -0.83  2021-06-30
    3  161725  000568  泸州老窖  13.02  -2.96  2021-06-30
    4  161725  002304  洋河股份  12.72   1.31  2021-06-30
    5  161725  000799   酒鬼酒   5.77   1.34  2021-06-30
    6  161725  603369   今世缘   3.46  -0.48  2021-06-30
    7  161725  000596  古井贡酒   2.81  -0.29  2021-06-30
    8  161725  600779   水井坊   2.52   2.52  2021-06-30
    9  161725  603589   口子窖   2.48  -0.38  2021-06-30
    >>> # 获取近 2 个公开持仓日数据
    >>> public_dates = ef.fund.get_public_dates('161725')
    >>> ef.fund.get_inverst_postion('161725',public_dates[:2])
        基金代码    股票代码  股票简称   持仓占比  较上期变化        公开日期
    0  161725  000568  泸州老窖  15.98   1.27  2021-03-31
    1  161725  600519  贵州茅台  15.02   2.35  2021-03-31
    2  161725  600809  山西汾酒  14.86  -0.37  2021-03-31
    3  161725  000858   五粮液  13.43   0.54  2021-03-31
    4  161725  002304  洋河股份  11.41  -2.21  2021-03-31
    5  161725  000799   酒鬼酒   4.43  -0.15  2021-03-31
    6  161725  603369   今世缘   3.94  -0.09  2021-03-31
    7  161725  000860  顺鑫农业   3.12   -0.7  2021-03-31
    8  161725  000596  古井贡酒    3.1  -0.15  2021-03-31
    9  161725  603589   口子窖   2.86   0.21  2021-03-31
    0  161725  600809  山西汾酒  15.23   0.62  2021-01-08
    1  161725  000568  泸州老窖  14.71    0.8  2021-01-08
    2  161725  002304  洋河股份  13.62  -0.43  2021-01-08
    3  161725  000858   五粮液  12.89   0.19  2021-01-08
    4  161725  600519  贵州茅台  12.67  -0.32  2021-01-08
    5  161725  000799   酒鬼酒   4.58   0.59  2021-01-08
    6  161725  603369   今世缘   4.03   0.03  2021-01-08
    7  161725  000860  顺鑫农业   3.82  -0.35  2021-01-08
    8  161725  000596  古井贡酒   3.25   -0.2  2021-01-08
    9  161725  603589   口子窖   2.65  -0.12  2021-01-08
    """

    columns = {
        'GPDM': '股票代码',
        'GPJC': '股票简称',
        'JZBL': '持仓占比',
        'PCTNVCHG': '较上期变化',
    }
    df = pd.DataFrame(columns=columns.values())
    if not isinstance(dates, List):
        dates = [dates]
    if dates is None:
        dates = [None]
    for date in dates:
        params = [
            ('FCODE', fund_code),
            ('OSVersion', '14.3'),
            ('appType', 'ttjj'),
            ('appVersion', '6.2.8'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.2.8'),
            ('version', '6.2.8'),
        ]
        if date is not None:
            params.append(('DATE', date))
        params = tuple(params)
        response = requests.get('https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition',
                                headers=EastmoneyFundHeaders, params=params)
        stocks = response.json()['Datas']['fundStocks']

        if stocks is None or len(stocks) == 0:
            continue
        date = response.json()['Expansion']
        _df = pd.DataFrame(stocks)
        _df = _df[list(columns.keys())].rename(columns=columns)
        _df['公开日期'] = [date for _ in range(len(_df))]
        df = pd.concat([df, _df], axis=0)
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    return df


@to_numeric
def get_period_change(fund_code: str) -> pd.DataFrame:
    """
    获取基金阶段涨跌幅度

    Parameters
    ----------
    fund_code : str
        6 位基金代码

    Returns
    -------
    DataFrame
        包含指定基金的阶段涨跌数据
    Examples
    --------
    >>> import efinance as ef
    >>> ef.fund.get_period_change('161725')
        基金代码     收益率   同类平均  同类排行  同类总数   时间段
    0  161725   -6.28   0.07  1408  1409   近一周
    1  161725   10.85   5.82   178  1382   近一月
    2  161725   25.32   7.10    20  1332   近三月
    3  161725   22.93  10.39    79  1223   近六月
    4  161725  103.76  33.58     7  1118   近一年
    5  161725  166.59  55.42     9   796   近两年
    6  161725  187.50  48.17     2   611   近三年
    7  161725  519.44  61.62     1   389   近五年
    8  161725    6.46   5.03   423  1243  今年以来
    9  161725  477.00                     成立以来
    """

    params = (
        ('AppVersion', '6.3.8'),
        ('FCODE', fund_code),
        ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('OSVersion', '14.3'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('passportid', '3061335960830820'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('version', '6.3.6'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNPeriodIncrease', headers=EastmoneyFundHeaders, params=params).json()
    columns = {

        'syl': '收益率',
        'avg': '同类平均',
        'rank': '同类排行',
        'sc': '同类总数',
        'title': '时间段'

    }
    titles = {'Z': '近一周',
              'Y': '近一月',
              '3Y': '近三月',
              '6Y': '近六月',
              '1N': '近一年',
              '2Y': '近两年',
              '3N': '近三年',
              '5N': '近五年',
              'JN': '今年以来',
              'LN': '成立以来'}
    # 发行时间
    ESTABDATE = json_response['Expansion']['ESTABDATE']
    df = pd.DataFrame(json_response['Datas'])

    df = df[list(columns.keys())].rename(columns=columns)
    df['时间段'] = titles.values()
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    return df


def get_public_dates(fund_code: str) -> List[str]:
    """
    获取历史上更新持仓情况的日期列表

    Parameters
    ----------
    fund_code : str
        6 位基金代码

    Returns
    -------
    List[str]
        指定基金公开持仓的日期列表
    Examples
    --------
    >>> import efinance as ef
    >>> public_dates = ef.fund.get_public_dates('161725')
    >>> # 展示前 5 个
    >>> public_dates[:5]
    ['2021-03-31', '2021-01-08', '2020-12-31', '2020-09-30', '2020-06-30']
    """

    params = (
        ('FCODE', fund_code),
        ('OSVersion', '14.3'),
        ('appVersion', '6.3.8'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('serverVersion', '6.3.6'),
        ('version', '6.3.8'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNIVInfoMultiple', headers=EastmoneyFundHeaders, params=params).json()
    if json_response['Datas'] is None:
        return []
    return json_response['Datas']


@to_numeric
def get_types_persentage(fund_code: str,
                         dates: Union[List[str], str, None] = None) -> pd.DataFrame:
    """
    获取指定基金不同类型占比信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    dates : Union[List[str], str, None]
        可选值类型示例如下(后面有获取 dates 的例子)

            None : 最新公开持仓数据的日期

            '2020-09-30' 指定日期数据

    Returns
    -------
    DataFrame
        指定基金的在不同日期的不同类型持仓占比信息

    Examples
    --------
    >>> import efinance as ef
    >>> # 获取持仓公开日期
    >>> public_dates = ef.fund.get_public_dates('005827')
    >>> # 取前两个公开持仓日期
    >>> dates = public_dates[:2]
    >>> ef.fund.get_types_persentage('005827',dates)
        基金代码   股票比重 债券比重  现金比重         总规模(亿元) 其他比重
    0  005827   94.4   --  6.06  880.1570625231    0
    0  005827  94.09   --  7.63   677.007455712    0

    """

    columns = {
        'GP': '股票比重',
        'ZQ': '债券比重',
        'HB': '现金比重',
        'JZC': '总规模(亿元)',
        'QT': '其他比重'
    }
    df = pd.DataFrame(columns=columns.values())
    if not isinstance(dates, List):
        dates = [dates]
    elif dates is None:
        dates = [None]
    for date in dates:
        params = [
            ('FCODE', fund_code),
            ('OSVersion', '14.3'),
            ('appVersion', '6.3.8'),
            ('deviceid', '3EA024C2-7F21-408B-95E4-383D38160FB3'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.3.6'),
            ('version', '6.3.8'),
        ]
        if date is not None:
            params.append(('DATE', date))
        params = tuple(params)
        json_response = requests.get(
            'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNAssetAllocationNew',  params=params).json()

        if len(json_response['Datas']) == 0:
            continue
        _df = pd.DataFrame(json_response['Datas'])[columns.keys()]
        _df = _df.rename(columns=columns)
        df = pd.concat([df, _df], axis=0)
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    return df


@to_numeric
def get_base_info_single(fund_code: str) -> pd.Series:
    """
    获取基金的一些基本信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码

    Returns
    -------
    Series
        包含基金的一些基本信息
    """

    params = (
        ('FCODE', fund_code),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('version', '6.3.8'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNNBasicInformation', headers=EastmoneyFundHeaders, params=params).json()
    columns = {
        'FCODE': '基金代码',
        'SHORTNAME': '基金简称',
        'ESTABDATE': '成立日期',
        'RZDF': '涨跌幅',
        'DWJZ': '最新净值',
        'JJGS': '基金公司',
        'FSRQ': '净值更新日期',
        'COMMENTS': '简介',
    }
    s = pd.Series(json_response['Datas']).rename(index=columns)
    s = s.apply(lambda x: x.replace('\n', ' ').strip()
                if isinstance(x, str) else x)
    return s


def get_base_info_muliti(fund_codes: List[str]) -> pd.Series:
    """
    获取多只基金基本信息

    Parameters
    ----------
    fund_codes : List[str]
        6 位基金代码列表

    Returns
    -------
    Series
        包含多只基金基本信息
    """

    ss = []

    @multitasking.task
    @retry(tries=3, delay=1)
    def start(fund_code: str) -> None:
        s = get_base_info_single(fund_code)
        ss.append(s)
        bar.update()
        bar.set_description(f'processing {fund_code}')
    bar = tqdm(total=len(fund_codes))
    for fund_code in fund_codes:
        start(fund_code)
    multitasking.wait_for_tasks()
    df = pd.DataFrame(ss)
    return df


def get_base_info(fund_codes: Union[str, List[str]]) -> Union[pd.Series, pd.DataFrame]:
    """
    获取基金的一些基本信息

    Parameters
    ----------
    fund_codes : Union[str, List[str]]
        6 位基金代码 或多个 6 位 基金代码构成的列表

    Returns
    -------
    Union[pd.Series, pd.DataFrame]
        Series : 包含单只基金基本信息(当 fund_codes 是字符串时)
        DataFrane : 包含多只股票基本信息(当 fund_codes 是字符串列表时)

    Raises
    ------
    TypeError
        当 fund_codes 类型不符合要求时
    Examples
    --------
    >>> import efinance as ef
    >>> # 获取单只基金基本信息
    >>> ef.fund.get_base_info('161725')
    基金代码                                                161725
    基金简称                                        招商中证白酒指数(LOF)A
    FTYPE                                                 股票指数
    FEATURE                                    020,050,051,054
    BFUNDTYPE                                              001
                                        ...
    HSGRT                                                0.10%
    BENCH                 中证白酒指数收益率*95%+金融机构人民币活期存款基准利率(税后)*5%
    FINSALES                                                 0
    INVESTMENTIDEAR                                         --
    INVESTMENTIDEARIMG                                      --
    Length: 118, dtype: object
    >>> # 获取多只基金基本信息
    >>> ef.fund.get_base_info(['161725','005827'])
        基金代码            基金简称 FTYPE  ... FINSALES INVESTMENTIDEAR INVESTMENTIDEARIMG
    0  005827       易方达蓝筹精选混合   混合型  ...        0              --                 --
    1  161725  招商中证白酒指数(LOF)A  股票指数  ...        0              --                 --
    """

    if isinstance(fund_codes, str):
        return get_base_info_single(fund_codes)
    elif hasattr(fund_codes, '__iter__'):
        return get_base_info_muliti(fund_codes)
    raise TypeError(f'所给的 {fund_codes} 不符合参数要求')


@to_numeric
def get_industry_distribution(fund_code: str, dates: Union[str, List[str]] = None) -> pd.DataFrame:
    """
    获取指定基金行业分布信息

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    dates : Union[str, List[str]], optional
        日期
        可选值类型示例如下
            None : 最新公开日期
            '2020-01-01' : 一个公开持仓日期
            ['2020-12-31' ,'2019-12-31'] : 多个公开持仓日期

    Returns
    -------
    DataFrame
        包含指定基金行业持仓信息

    Examples
    --------
    >>> import efinance as ef
    >>> # 获取持仓公开日期
    >>> public_dates = ef.fund.get_public_dates('161725')
    >>> # 取前一个公开持仓日期
    >>> dates = public_dates[:1]
    >>> ef.fund.get_industry_distribution('161725',dates)
        基金代码              行业名称   持仓比例        公布日期              市值
    0   161725               制造业  94.92  2021-03-31  4737709.835521
    1   161725               金融业   0.01  2021-03-31      554.417158
    2   161725            批发和零售业      0  2021-03-31        3.307382
    3   161725   信息传输、软件和信息技术服务业      0  2021-03-31      121.184075
    4   161725              房地产业      0  2021-03-31         1.02003
    5   161725        科学研究和技术服务业      0  2021-03-31         1.87866
    6   161725  电力、热力、燃气及水生产和供应业      0  2021-03-31        2.403612
    7   161725     水利、环境和公共设施管理业      0  2021-03-31        3.339202
    8   161725          农、林、牧、渔业     --  2021-03-31              --
    9   161725            住宿和餐饮业     --  2021-03-31              --
    10  161725               采矿业     --  2021-03-31              --
    11  161725          租赁和商务服务业     --  2021-03-31              --
    12  161725       交通运输、仓储和邮政业     --  2021-03-31              --
    13  161725               建筑业     --  2021-03-31              --
    14  161725     居民服务、修理和其他服务业     --  2021-03-31              --
    15  161725                教育     --  2021-03-31              --
    16  161725           卫生和社会工作     --  2021-03-31              --
    17  161725         文化、体育和娱乐业     --  2021-03-31              --
    18  161725                综合     --  2021-03-31              --
    19  161725                合计  94.94  2021-03-31   4738397.38564
    """

    columns = {
        'HYMC': '行业名称',
        'ZJZBL': '持仓比例',
        'FSRQ': '公布日期',
        'SZ': '市值'
    }
    df = pd.DataFrame(columns=columns.values())
    if isinstance(dates, str):
        dates = [dates]
    elif dates is None:
        dates = [None]
    for date in dates:

        params = [

            ('FCODE', fund_code),
            ('OSVersion', '14.4'),
            ('appVersion', '6.3.8'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.3.6'),
            ('version', '6.3.8'),
        ]
        if date is not None:
            params.append(('DATE', date))

        response = requests.get('https://fundmobapi.eastmoney.com/FundMNewApi/FundMNSectorAllocation',
                                headers=EastmoneyFundHeaders, params=params)
        datas = response.json()['Datas']

        _df = pd.DataFrame(datas)
        _df = _df.rename(columns=columns)
        df = pd.concat([df, _df], axis=0)
    df.insert(0, '基金代码', [fund_code for _ in range(len(df))])
    df = df.drop_duplicates()
    return df


def get_pdf_reports(fund_code: str, max_count: int = 12, save_dir: str = 'pdf') -> None:
    """
    根据基金代码获取其全部 pdf 报告

    Parameters
    ----------
    fund_code : str
        6 位基金代码
    max_count : int, optional
        要获取的最大个数个 pdf(从最新的的开始数), 默认为 12
    save_dir : str, optional
        pdf 保存的文件夹路径, 默认为 'pdf'
    Examples
    --------
    >>> import efinance as ef
    >>> # 获取基金代码为 161725 的基金最新的两个 pdf 报道文件
    >>> ef.fund.get_pdf_reports('161725',max_count = 2)
    161725 的 pdf 文件已存储到文件夹 pdf/161725 中
    """

    headers = {
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36 Edg/89.0.774.77',
        'Accept': '*/*',
        'Referer': 'http://fundf10.eastmoney.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }

    @multitasking.task
    @retry(tries=3, delay=1)
    def download_file(fund_code: str, url: str, filename: str, file_type='.pdf') -> None:
        """
        根据文件名、文件直链等参数下载文件

        Parameters
        ----------
        fund_code : str
            6 位基金代码
        url : str
            下载连接
        filename : str
            文件后缀名
        file_type : str, optional
            文件类型, 默认为 '.pdf'
        """

        bar.set_description(f'processing {fund_code}')
        fund_code = str(fund_code)
        if not os.path.exists(save_dir+'/'+fund_code):
            os.mkdir(save_dir+'/'+fund_code)
        response = requests.get(url, headers=headers)
        path = f'{save_dir}/{fund_code}/{filename}{file_type}'
        with open(path, 'wb') as f:
            f.write(response.content)
        if os.path.getsize(path) == 0:
            os.remove(path)
            return
        bar.update(1)
    params = (
        ('fundcode', fund_code),
        ('pageIndex', '1'),
        ('pageSize', '200000'),
        ('type', '3'),
    )

    json_response = requests.get(
        'http://api.fund.eastmoney.com/f10/JJGG', headers=headers, params=params).json()

    base_link = 'http://pdf.dfcfw.com/pdf/H2_{}_1.pdf'

    bar = tqdm(total=min(max_count, len(json_response['Data'])))
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    for item in json_response['Data'][-max_count:]:

        title = item['TITLE']
        download_url = base_link.format(item['ID'])
        download_file(fund_code, download_url, title)
    multitasking.wait_for_tasks()
    bar.close()
    print(f'{fund_code} 的 pdf 文件已存储到文件夹 {save_dir}/{fund_code} 中')
