'''
Author: George Zhao
Date: 2022-10-11 11:12:44
LastEditors: George Zhao
LastEditTime: 2022-10-11 18:26:02
Description: Get MacroEco Data.
Email: ziyi19386@hotmail.com
Company: Personnal
Version: 1.0
'''
# %%
import typing
import requests
import pandas as pd
# %%


class ChoiseCenterFetcher:
    def __init__(self, params, annotation) -> None:
        self.params = params

        self.annotation = annotation

        # temp
        self.request = self.make_prerequest()
        self.response = None
        self.result = None
        pass

    def make_prerequest(self):
        return requests.Request(
            'GET',
            url='https://datacenter-web.eastmoney.com/api/data/v1/get',
            params=self.params,
            headers={
                'Accept': '*/*',
                'Accept-Language': 'en,zh-CN;q=0.9,zh-TW;q=0.8,zh;q=0.7',
                'Connection': 'keep-alive',
                'DNT': '1',
                'Referer': 'https://data.eastmoney.com/',
                'Sec-Fetch-Dest': 'script',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-site',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
        )

    def get(
        self,
        request: requests.Request = None,
        session_setting: dict = {
            "verify": requests.certs.where(),
            "timeout": (2, 60),
            "proxies": None,
            "allow_redirects": False
        },
        requestexceptionhandle: typing.Callable = None
    ):
        if request is None:
            request = self.request

        with requests.Session() as s:
            try:
                self.response = s.send(
                    request.prepare(),
                    **session_setting
                )
            except requests.RequestException as e:
                requestexceptionhandle(e)
        return self

    def handle(self):
        self.result = self.response.json()
        self.result = pd.DataFrame(self.result['result']['data'])
        self.result.set_index(pd.DatetimeIndex(
            self.result["REPORT_DATE"]), inplace=True, drop=True)
        self.result.drop(columns=['REPORT_DATE', ], inplace=True)
        return self


class GDPFetcher(ChoiseCenterFetcher):
    def __init__(self) -> None:
        super().__init__(
            params={
                'columns': 'REPORT_DATE,TIME,DOMESTICL_PRODUCT_BASE,FIRST_PRODUCT_BASE,SECOND_PRODUCT_BASE,THIRD_PRODUCT_BASE,SUM_SAME,FIRST_SAME,SECOND_SAME,THIRD_SAME',
                # 'pageNumber': '1',
                # 'pageSize': '2147483647',
                'sortColumns': 'REPORT_DATE',
                'sortTypes': '-1',
                'source': 'WEB',
                'client': 'WEB',
                'reportName': 'RPT_ECONOMY_GDP',
            },
            annotation={
                "key": "gdp",
                "name": "中国 国内生产总值(GDP)",
                "sokey": "国内生产总值",
                "text_dy": "国内生产总值，Gross Domestic Product，简称GDP，是指在一定时期内（一个季度或一年），一个国家或地区的经济中所生产出的全部最终产品和劳务的价值，常被公认为衡量国家经济状况的最佳指标。",
                "text_zyx": "非常高：国内生产总值GDP是核算体系中一个重要的综合性统计指标，也是中国新国民经济核算体系中的核心指标。它反映一国（或地区）的经济实力和市场规模。",
                "text_sjly": "国家统计局",
            }
        )


class CPIFetcher(ChoiseCenterFetcher):
    def __init__(self) -> None:
        super().__init__(
            params={
                'columns': 'REPORT_DATE,TIME,NATIONAL_SAME,NATIONAL_BASE,NATIONAL_SEQUENTIAL,NATIONAL_ACCUMULATE,CITY_SAME,CITY_BASE,CITY_SEQUENTIAL,CITY_ACCUMULATE,RURAL_SAME,RURAL_BASE,RURAL_SEQUENTIAL,RURAL_ACCUMULATE',
                # 'pageNumber': '1',
                # 'pageSize': '2147483647',
                'sortColumns': 'REPORT_DATE',
                'sortTypes': '-1',
                'source': 'WEB',
                'client': 'WEB',
                'reportName': 'RPT_ECONOMY_CPI',
            },
            annotation={
                "key": "cpi",
                "name": "居民消费价格指数(CPI)",
                "sokey": "居民消费价格指数",
                "text_dy": "消费物价指数，英文缩写为CPI，是根据与居民生活有关的产品及劳务价格统计出来的物价变动指标，通常作为观察通货膨胀水平的重要指标。",
                "text_zyx": "非常高：消费者物价指数（CPI）是金融市场的一个热门的经济指标。消费者物价指数决定着消费者花费多少来购买商品和服务，左右着商业经营的成本。而且，消费者物价指数影响制定政府的财政政策、金融政策。",
                "text_sjly": "国家统计局",
            }
        )


class ASSETINVESTFetcher(ChoiseCenterFetcher):
    def __init__(self) -> None:
        super().__init__(
            params={
                'columns': 'REPORT_DATE,TIME,BASE,BASE_SAME,BASE_SEQUENTIAL,BASE_ACCUMULATE',
                # 'pageNumber': '1',
                # 'pageSize': '2147483647',
                'sortColumns': 'REPORT_DATE',
                'sortTypes': '-1',
                'source': 'WEB',
                'client': 'WEB',
                'reportName': 'RPT_ECONOMY_ASSET_INVEST',
            },
            annotation={
                "key": "gdzctz",
                "name": "城镇固定资产投资",
                "sokey": "城镇固定资产投资",
                "text_dy": "固定资产投资是建造和购置固定资产的经济活动，即固定资产再生产活动。固定资产再生产过程包括固定资产更新（局部和全部更新）、改建、扩建、新建等活动。新的企业财务会计制度规定：固定资产局部更新的大修理作为日常生产活动的一部分，发生的大修理费用直接在成本中列支。",
                "text_zyx": "一般：固定资产投资是社会固定资产再生产的主要手段。",
                "text_sjly": "国家统计局",
            }
        )


class PPIFetcher(ChoiseCenterFetcher):
    def __init__(self) -> None:
        super().__init__(
            params={
                'columns': 'REPORT_DATE,TIME,BASE,BASE_SAME,BASE_ACCUMULATE',
                # 'pageNumber': '1',
                # 'pageSize': '2147483647',
                'sortColumns': 'REPORT_DATE',
                'sortTypes': '-1',
                'source': 'WEB',
                'client': 'WEB',
                'reportName': 'RPT_ECONOMY_PPI',
            },
            annotation={
                "key": "ppi",
                "name": "工业品出厂价格指数(PPI)",
                "sokey": "工业品出厂价格指数",
                "text_dy": "工业品出厂价格指数是反映全部工业产品出厂价格总水平的变动趋势和程度的相对数。",
                "text_zyx": "非常高：工业品出厂价格指数是衡量工业企业产品出厂价格变动趋势和变动程度的指数，是反映某一时期生产领域价格变动情况的重要经济指标，也是制定有关经济政策和国民经济核算的重要依据。",
                "text_sjly": "国家统计局",
            }
        )


def get_all_gdp():
    # Usage: get_all_gdp()
    return GDPFetcher().get().handle().result


def get_all_cpi():
    # Usage: get_all_cpi()
    return CPIFetcher().get().handle().result


def get_all_ppi():
    # Usage: get_all_ppi()
    return PPIFetcher().get().handle().result
