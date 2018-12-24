# coding=utf-8

from datetime import timedelta
import os
import configparser
from server.settings import log_common

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


main_cf = configparser.ConfigParser()
main_cf.read(BASE_DIR + '/../conf/main.ini')


CELERY_RESULT_BACKEND = 'db+sqlite:///' + os.path.join(BASE_DIR, '../run/celery_results.sqlite')
CELERY_TIMEZONE = 'UTC'


