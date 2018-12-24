from enum import Enum, unique


@unique
class Alert(Enum):
    erp_sync_exception = 1
    verify_code_exception = 2
    spider_exception = 12
    platform_exception = 13
