# -*- coding: utf-8 -*-
import random
import hashlib


def random_password(length):
    seed = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    sa = []
    for i in range(length):
        sa.append(random.choice(seed))
    return ''.join(sa)


def password2md5(password):
    md5_str = hashlib.md5(password.encode('utf-8')).hexdigest()
    return md5_str
