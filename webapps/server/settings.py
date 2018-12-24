# -*- coding: utf-8 -*-
import configparser

from server.misc_conf import *
from server.db_conf import *
from server.logging_conf import *
from server.celery_conf import *


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY='xxxxx'

# JWT SECRET
JWT_SECRET='xxxxxx'

main_cf = configparser.ConfigParser()
main_cf.read(BASE_DIR + '/../conf/main.ini')
DEBUG = main_cf.getboolean('main', 'debug')
SESSION_COOKIE_DOMAIN = main_cf.get('main', 'session_cookie_domain')


ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'server',
    'apps',
    'django_apscheduler',
)

PROJECTS_FOLDER = 'projects'

WECHAT_SETTING = {
    'CORPID': main_cf.get('wechat', 'corp_id'),
    'AGENDID': main_cf.get('wechat', 'agent_id'),
    'SECRET': main_cf.get('wechat', 'secret')
}

OSS_SETTING = {
    'OSS_TEST_ACCESS_KEY_ID': main_cf.get('oss', 'access_key_id'),
    'OSS_TEST_ACCESS_KEY_SECRET': main_cf.get('oss', 'access_key_secret'),
    'OSS_TEST_BUCKET': main_cf.get('oss', 'bucket_name'),
    'OSS_TEST_ENDPOINT': main_cf.get('oss', 'endpoint')
}

# from server.loader_conf import *
