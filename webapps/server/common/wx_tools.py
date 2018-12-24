import urllib.request
import requests
import urllib.parse
import json

from server.db_conf import crawl_redis
from server.settings import WECHAT_SETTING

# 普通微信
WX_SERVER_URL = 'https://api.weixin.qq.com/cgi-bin/'
GET_ACCESS_TOKEN = WX_SERVER_URL + 'token?grant_type=client_credential&appid=%(appid)s&secret=%(secret)s'
SEND_MESSAGE = WX_SERVER_URL + 'message/template/send?access_token=%(access_token)s'

# 企业微信
ENV_WX_SERVER_URL = 'https://qyapi.weixin.qq.com/cgi-bin/'
ENV_GET_ACCESS_TOKEN = ENV_WX_SERVER_URL + 'gettoken?corpid=%(corpid)s&corpsecret=%(secret)s'
ENV_SEND_MESSAGE = ENV_WX_SERVER_URL + 'message/send?access_token=%(access_token)s'


def get_access_token(appid, secret):
    access_token = crawl_redis.get('wx_access_token')
    if access_token is not None:
        return bytes.decode(access_token)
    else:
        http_response = urllib.request.urlopen(GET_ACCESS_TOKEN % {'appid': appid, 'secret': secret})
        response = json.loads(http_response.read())
        access_token = response.get('access_token')
        crawl_redis.set('wx_access_token', access_token, 7100)
        return access_token


def send_template_message(access_token, template_id, wx_account, body, jump_url=''):
    url = SEND_MESSAGE % {'access_token': access_token}
    headers = {'Content-Type': 'application/json'}
    body = {'touser': wx_account,
            'template_id': template_id,
            'url': jump_url,
            'topcolor': '##FF0000',
            'data': body}
    data = json.dumps(body).encode(encoding='utf-8')
    request = urllib.request.Request(url=url, headers=headers, data=data)
    http_response = urllib.request.urlopen(request)
    response = json.loads(http_response.read())
    if response.get('errcode') == 0:
        return True
    else:
        return False


def env_get_access_token(corpid, secret):
    access_token = crawl_redis.get('env_wx_access_token')
    if access_token is not None:
        return bytes.decode(access_token)
    else:
        r = requests.get(ENV_GET_ACCESS_TOKEN % {'corpid': corpid, 'secret': secret})
        response = r.json()
        access_token = response.get('access_token')
        expires_in = int(response.get('expires_in'))
        crawl_redis.set('env_wx_access_token', access_token, expires_in - 100)
        return access_token


def env_send_card_message(to_user, title, desc, url='http://127.0.0.1/', btn_txt='点击查看'):
    data = {'title': title,
            'description': desc,
            'url': url,
            'btntxt': btn_txt}
    return env_send_message(to_user, 'textcard', data)


def env_send_message(to_user, msg_type, data):
    access_token = env_get_access_token(WECHAT_SETTING['CORPID'], WECHAT_SETTING['SECRET'])
    url = ENV_SEND_MESSAGE % {'access_token': access_token}
    body = {'touser': to_user,
            'msgtype': msg_type,
            'agentid': int(WECHAT_SETTING['AGENDID']),
            msg_type: data}
    r = requests.post(url=url, json=body)
    response = r.json()
    return response['errcode'] == 0

