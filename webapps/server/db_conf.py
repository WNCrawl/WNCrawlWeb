# coding=utf-8

import os
import configparser
import redis
import json
from redlock import Redlock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

main_cf = configparser.ConfigParser()
main_cf.read(BASE_DIR + '/../conf/main.ini')

ALLOWED_HOSTS = ['*']

mysql_host = main_cf.get('db', 'crawl_db_host')
mysql_port = main_cf.get('db', 'crawl_db_port')
mysql_user = main_cf.get('db', 'crawl_db_user')
mysql_pwd = main_cf.get('db', 'crawl_db_pwd')
mysql_name = main_cf.get('db', 'crawl_db_name')

redis_host = main_cf.get('redis', 'redis_db_host')
redis_port = main_cf.get('redis', 'redis_db_port')
redis_pwd = main_cf.get('redis', 'redis_db_pwd')
redis_db_name = main_cf.get('redis', 'redis_db_name')

crawl_redis = redis.StrictRedis(host=redis_host,
                                port=redis_port,
                                db=redis_db_name,
                                password=redis_pwd)

dlm = Redlock([{"host": redis_host, "port": redis_port, "db": 2,
                "password": redis_pwd}, ])


alert_url = main_cf.get('cfg_alert', 'alert_http')
crawl_redis.set('cfg#alert_url', alert_url+"/api/alert/send_alert")
#
crawl_redis.set('cfg#alert_sns_url', alert_url+"/api/wechat/h5.html")
# 上报任务进度
crawl_redis.set('cfg#report_script_url', alert_url+"/api/script/collect_script_progress")
# 数据同步任务进度
crawl_redis.set('sync#sync_data_url', alert_url+"/api/sync/create_instance")
# 爬虫平台地址
crawl_redis.set('admin#host', alert_url)
# 数据同步配置
sql_config = {
        'host': mysql_host,
        'port': mysql_port,
        'database': mysql_name,
        'user': mysql_user,
        'password': mysql_pwd,
        'charset': 'utf8',
        'use_unicode': True,
        'get_warnings': True,
    }
crawl_redis.set('cfg#mysql', json.dumps(sql_config))


DATABASES = {
    'default': {
        'ENGINE': 'mysql.connector.django',
        'HOST': mysql_host,
        'PORT': mysql_port,
        'NAME': mysql_name,
        'USER': mysql_user,
        'PASSWORD': mysql_pwd,
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'charset': 'utf8', 'use_pure': True},
    }
}

