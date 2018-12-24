# coding=utf-8
from django.utils.deprecation import MiddlewareMixin
from jwt import ExpiredSignatureError

from apps.crawl.response import JsonResponse
from server.common import jwt_tools
from server.common.rich_result import Result
from server.settings import DEBUG
from server.db_conf import crawl_redis
import json


class AuthMiddleware(MiddlewareMixin):
    """
    鉴权
    """
    white_list = [
        '/api/user/login',
        '/api/wechat/get_env_access_token',
        '/api/script/collect_script_progress',
        '/api/sync/create_instance',
        '/api/alert/send_alert',
        '/api/wechat/monitor_redis',
        '/api/script/img_parser',
        '/api/wechat/h5.html',
        '/api/wechat/report_sns'
    ]

    public_permisson = [
        '/api/user/fetch_user_permissions'
    ]

    def process_request(self, request):
        try:
            if DEBUG:
                return
            if request.path in self.white_list:
                return

            dt_token = request.COOKIES.get('dt_token')
            dt_user_id = request.COOKIES.get('dt_user_id')
            dt_username = request.COOKIES.get('dt_username')

            if not dt_token:
                return JsonResponse(Result.fail("缺少token"), status=403)

            res = jwt_tools.decode_token(dt_token)
            if not jwt_tools.verify(res):
                return JsonResponse(Result.fail("非法token"), status=403)

            # 检查权限
            if not self.filter_auth(dt_user_id, dt_username, request.path):
                r = Result.fail("无权限访问该资源")
                return JsonResponse(r, status=403)

            request.user_id = dt_user_id
            request.user_name = dt_username
        except ExpiredSignatureError as e:
            r = Result.fail("登录过期")
            return JsonResponse(r, status=403)
        except Exception as e:
            r = Result.fail("非法登录")
            return JsonResponse(r, status=403)

    def filter_auth(self, user_id, user_name, current_req):
        """
        权限检查
        :param user_id:
        :param user_name
        :param current_req:
        :return:
        """
        return True

        # if "admin" == user_name: # admin为超级用户，默认不做权限校验
        #         #     return True
        #         #
        #         # role_permissions = crawl_redis.get("permission#user#{}".format(str(user_id)))
        #         # if role_permissions:
        #         #     tree_json = eval(role_permissions)
        #         #     for permission in tree_json:
        #         #         if (permission['permission_url'] in current_req) or current_req in self.public_permisson:
        #         #             return True
        #         # return False
