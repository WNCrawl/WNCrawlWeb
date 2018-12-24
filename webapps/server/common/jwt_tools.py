# -*- coding: utf-8 -*-

import jwt
import datetime
import time

from django.conf import settings


def encode_token(user_id, user_name, deadline=None):
    if not deadline:
        deadline = (datetime.datetime.now() + datetime.timedelta(days=7)).replace(hour=19)
    exp = deadline
    ret = {
        'user_id': str(user_id),
        'user_name': user_name,
        'exp': exp
    }
    return jwt.encode(ret, settings.JWT_SECRET, algorithm='HS256')


def decode_token(token):
    res = jwt.decode(token, settings.JWT_SECRET, algorithms='HS256')
    return res


def verify(res):
    now = int(time.time())
    return res.get('exp') > now
