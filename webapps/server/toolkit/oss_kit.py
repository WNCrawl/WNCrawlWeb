# -*- coding: utf-8 -*-
import os
from datetime import datetime

import oss2

from server.settings import OSS_SETTING

"""
阿里云oss—python-sdk使用
"""

access_key_id = os.getenv('OSS_TEST_ACCESS_KEY_ID', OSS_SETTING['OSS_TEST_ACCESS_KEY_ID'])
access_key_secret = os.getenv('OSS_TEST_ACCESS_KEY_SECRET', OSS_SETTING['OSS_TEST_ACCESS_KEY_SECRET'])
bucket_name = os.getenv('OSS_TEST_BUCKET', OSS_SETTING['OSS_TEST_BUCKET'])
endpoint = os.getenv('OSS_TEST_ENDPOINT', OSS_SETTING['OSS_TEST_ENDPOINT'])

oss_url_prefix = os.getenv('OSS_TEST_ENDPOINT', 'https://{}.{}'.format(bucket_name, endpoint))

bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name)


def put_object_line(script_identity="", line=""):
    """
    新建内容
    :param script_identity
    :param line:
    :return:
    """
    date = datetime.now()
    ymd = date.strftime("%Y_%m_%d")
    now = date.strftime("%Y_%m_%d_%H_%M_%S")
    # 设置meta信息
    oss_bucket_path = "{}/{}_{}.csv".format(ymd, script_identity, now)
    bucket.put_object(oss_bucket_path, line)


def put_object_lines(script_identity="", lines=[]):
    """
    新增多行内容
    :param script_identity:
    :param lines:
    :return:
    """
    date = datetime.now()
    ymd = date.strftime("%Y_%m_%d")
    now = date.strftime("%Y_%m_%d_%H_%M_%S")
    # 设置meta信息
    headers = ""
    rows = []
    for line in lines:
        headers = ",".join(line.keys())
        rows.append(",".join(line.values()))
    body = "\n".join(rows)
    content = "{}\n{}".format(headers, body)
    oss_bucket_path = "{}/{}_{}.csv".format(ymd, script_identity, now)
    print(oss_bucket_path)
    bucket.put_object(oss_bucket_path, content)


def append_object_line(script_identity="", content=""):
    """
    追加内容
    :param script_identity:
    :param content:
    :return:
    """
    pass


def append_object_lines(script_identity="", content=""):
    """
    追加多行内容
    :param script_identity:
    :param content:
    :return:
    """
    pass


# def put_object_file(script_identity="", file=""):
#     """
#     文件上传内容
#     :param script_identity:
#     :param file:
#     :return:
#     """
#     date = datetime.now()
#     ymd = date.strftime("%Y%m%d")
#     now = date.strftime("%Y%m%d%H%M%S")
#     # 设置meta信息
#     oss_bucket_path = "/{}/{}_{}.csv".format(ymd, script_identity, now)
#     with open(oss2.to_unicode(file), 'rb') as fs:
#         bucket.put_object(oss_bucket_path, fs)


def put_object_file(path='', file=None):
    """
    上传文件
    :param path:
    :param file:
    :return:
    """
    oss_bucket_path = path + file.name
    bucket.put_object(oss_bucket_path, file)


def put_object_png(script_identity="", png=""):
    """
    上传图片
    :param script_identity:
    :param png:
    :return:
    """
    date = datetime.now()
    now = date.strftime("%Y%m%d%H%M%S")
    # 设置meta信息
    oss_bucket_path = "png/{}/{}_{}.png".format(script_identity, script_identity, now)
    with open(oss2.to_unicode(png), 'rb') as fs:
        bucket.put_object(oss_bucket_path, fs)
    return bucket.sign_url('GET', oss_bucket_path, 60 * 5)


def get_object_list(path=''):
    """
    获取文件列表
    :param path:
    :return:
    """
    return bucket.list_objects(path)


def get_object_to_file(remote_path, local_path):
    bucket.get_object_to_file(remote_path, local_path)
