# -*- coding: utf-8 -*-


def convert_ms(ms):
    if not ms:
        return 0
    ms = int(ms)
    hms = ''
    if int(ms / 3600000) != 0:
        hms = hms + str(int(ms / 3600000)) + '小时'
    if int((ms % 3600000) / 60000) != 0:
        hms = hms + str(int((ms % 3600000) / 60000)) + '分钟'
    hms = hms + str(int((ms % 60000) / 1000)) + '秒'
    return hms
