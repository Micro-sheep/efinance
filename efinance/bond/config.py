from pathlib import Path

HERE = Path(__file__).parent

# 债券基本信息表头
EASTMONEY_BOND_BASE_INFO_FIELDS = {
    "SECURITY_CODE": "债券代码",
    "SECURITY_NAME_ABBR": "债券名称",
    "CONVERT_STOCK_CODE": "正股代码",
    "SECURITY_SHORT_NAME": "正股名称",
    "RATING": "债券评级",
    "PUBLIC_START_DATE": "申购日期",
    "ACTUAL_ISSUE_SCALE": "发行规模(亿)",
    "ONLINE_GENERAL_LWR": "网上发行中签率(%)",
    "LISTING_DATE": "上市日期",
    "EXPIRE_DATE": "到期日期",
    "BOND_EXPIRE": "期限(年)",
    "INTEREST_RATE_EXPLAIN": "利率说明",
}
