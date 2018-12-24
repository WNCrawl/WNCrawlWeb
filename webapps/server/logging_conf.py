# coding=utf-8

import os
from server import consts
import logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(pathname)s:%(lineno)s] %(message)s",
            'datefmt': "%Y/%m/%d %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, '../', consts.LOGGING_PATH, 'dt.error.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 20,
        },
        'crontab': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, '../', consts.LOGGING_PATH, 'dt.crontab.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 20,
        },
        'common': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, '../', consts.LOGGING_PATH, 'dt.common.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 20,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },

    },
    'loggers': {
        'django': {
            'handlers': ['null', ],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django_crontab.crontab': {
            'handlers': ['file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'crontab': {
            'handlers': ['crontab', ],
            'level': 'DEBUG',
        },
        'common': {
            'handlers': ['common', ],
            'level': 'DEBUG',
        },
    }
}

log_common = logging.getLogger('common')
log_crontab = logging.getLogger('crontab')
