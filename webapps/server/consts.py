# -*- coding: utf-8 -*-
import os
import configparser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
############

KEY_OPENID = ''
KEY_UNIONID = ''

IDKEY=0x3c95afde

## 验证码格式
OSS_FORMAT = 'jpeg'

############
ALIYUN_API_ECS = 'https://ecs.aliyuncs.com'
SMTP_SERVER = 'smtp.mxhichina.com'
SMTP_PASSWORD = 'S@dtstack2016'
SMTP_SUPPORT_USER = 'support@dtstack.com'


EXPIRE_DAYS = 15
#CPU警戒线，超过这个就算异常
CPU_WARNING_LEVEL = 80
SESSION_WARNING_LEVEL = 0.8

# 日志存放路径
LOGGING_PATH = 'logs'

ALI_DAYU_KEY = '23306572'
ALI_DAYU_SECRET = '9536232124578eaec732c79140b89c28'

#默认页面大小 20
DEFAULT_PAGE_SIZE = 20
#默认页码 1
DEFAULT_PAGE = 1


main_cf = configparser.ConfigParser()
main_cf.read(BASE_DIR + '/../conf/local.ini')

ELASTICSEARCH_LOG_TYPE = 'logs'
ELASTICSEARCH = "139.196.11.146:9200"


