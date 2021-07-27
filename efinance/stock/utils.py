from typing import Union
import requests


def gen_secid(stock_code: str) -> str:
    """
    生成东方财富股票专用的 secid

    Parameters
    ----------
    stock_code : str
        6 位股票代码

    Returns
    -------
    str
        东方财富股票专用的 secid
    """
    if len(str(stock_code).strip()) == 0:
        raise Exception('股票代码应为 6 位数')

    seicd = gen_secid_plus(stock_code)
    if seicd is None:
        raise Exception(f'股票代码 {stock_code} 可能有误')
    return seicd


def gen_secid_plus(code: str) -> Union[str, None]:
    """
    调用接口生成 secid

    Parameters
    ----------
    code : str
        股票代码、债券代码、ETF 代码

    Returns
    -------
    Union[str,None]
        str : 第一个建议的 secid

        None : 当搜索不到结果时
    """
    url = 'https://searchapi.eastmoney.com/api/suggest/get'
    params = (
        ('input', f'{code}'),
        ('type', '14'),
        ('token', 'D43BF722C8E33BDC906FB84D85E326E8'),
        ('count', '1'))
    json_response = requests.get(url, params=params).json()
    items = json_response['QuotationCodeTable']['Data']
    if items is not None:
        return items[0]['QuoteID']
    return None
