"""
[efinance](https://github.com/Micro-sheep/efinance) 是由个人打造的用于获取股票、基金、期货数据的免费开源 Python 库，使用它你可以很方便地获取数据以便更好地服务于个人的交易系统需求。

"""

from efinance.api import (stock,
                          fund,
                          futures)
__all__ = ['stock', 'fund', 'futures']
