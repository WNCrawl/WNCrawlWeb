# coding=utf-8

import os
import configparser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

main_cf = configparser.ConfigParser()
main_cf.read(BASE_DIR + '/../conf/main.ini')

SESSION_COOKIE_DOMAIN = main_cf.get('main', 'session_cookie_domain')

ROOT_URLCONF = 'server.urls'

WSGI_APPLICATION = 'wsgi.application'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'server.middleware.auth.AuthMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),

    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}

REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DATETIME_FORMAT':'%Y-%m-%d %H:%M:%S',
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
             os.path.join(BASE_DIR, "templates"),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

DEFAULT_CHARSET = "UTF-8"

LOCALES = (
    ('en', u'English'),
    ('zh-hans', u'简体中文'),
)

STATIC_URL = '/static/'
STATIC_ROOT = '_static/'
# STATICFILES_DIRS = (
#     os.path.join(BASE_DIR, "static"),
# )

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'server/templates/static'),
)

