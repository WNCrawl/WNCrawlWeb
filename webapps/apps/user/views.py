# coding=utf-8
import json
import os
import random

from django.core.paginator import Paginator
from django.forms.models import model_to_dict
from django.db.models import Q
from django.http import HttpResponse

from apps.crawl.response import JsonResponse
from apps.user.models import CrawlPermission, CrawlRole, CrawlRolePermission, CrawlUser, CrawlUserRoleRel
from server.common import jwt_tools
from server.common.password_helper import random_password, password2md5
from server.common.rich_result import Result
from django.conf import settings
from server.common.page_helper import page_helper
from PIL import Image, ImageDraw, ImageFont

from server.db_conf import crawl_redis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_profile(request, user_id):
    """
    获取个人信息
    :param user_id:
    :param request:
    :return:
    """
    if request.method == 'GET':
        user = CrawlUser.objects.get(id=user_id)
        userD = model_to_dict(user)
        userD.__setitem__('created_at', user.created_at)
        r = Result.success(userD)
        return JsonResponse(r)


def edit_profile(request, user_id):
    """
    编辑个人信息（TODO 这里产品原型上缺少了告警设置，告警信息也可以编辑）
    :param user_id:
    :param request:
    :return:
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        CrawlUser.objects.filter(id=user_id).update(account=data.get('account'),
                                                    mobile=data.get('mobile'),
                                                    wx_account=data.get('wx_account'))
        r = Result.success(None)
        return JsonResponse(r)


def reset_profile_pwd(request, user_id):
    """
    重置个人密码
    :param user_id:
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            old_pwd = data.get('old_pwd')
            new_pwd = data.get('new_pwd')
            confirm_pwd = data.get('confirm_pwd')
            user = CrawlUser.objects.get(id=user_id)
            if confirm_pwd != new_pwd:
                raise Exception('两次密码输入不一致')
            db_pwd = user.password
            if db_pwd != password2md5(old_pwd):
                raise Exception('密码不正确')
            user.password = password2md5(new_pwd)
            user.save()
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def create_user(request):
    """
    创建用户
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('username')

            if CrawlUser.objects.filter(username=username, is_deleted=0):
                raise Exception('账号名存在')

            account = data.get('account')
            mobile = data.get('mobile')
            wx_account = data.get('wx_account')
            role_ids = data.get('role_ids')
            alert_options = data.get('alert_options')
            comment = data.get('comment')
            alert_enable = data.get('alert_enable', 0)
            password = random_password(6)
            user = CrawlUser.objects.create(account=account,
                                            username=username,
                                            mobile=mobile,
                                            comment=comment,
                                            wx_account=wx_account,
                                            password=password2md5(password),
                                            alert_enable=alert_enable)
            user_id = user.id
            for role_id in role_ids:
                CrawlUserRoleRel.objects.create(user_id=user_id,
                                                role_id=role_id)

            # 权限树写进 redis
            user_roles = CrawlUserRoleRel.objects.filter(user_id=user_id)
            crawl_redis.set('permission#user#{}'.format(user_id), build_permission_tree(user_roles))

            response = {'username': username,
                        'password': password}
            r = Result.success(response)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def edit_user(request, user_id):
    """
    修改用户
    :param user_id:
    :param request: request object
    :return: json
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        alert_options = data.get('alert_options')

        user = CrawlUser.objects.get(id=user_id)
        user.account = data.get('account')
        user.mobile = data.get('mobile', '')
        user.wx_account = data.get('wx_account')
        user.comment = data.get('comment', '')
        user.alert_enable = data.get('alert_enable', 0)
        user.save()

        role_ids = data.get('role_ids')

        CrawlUserRoleRel.objects.filter(user_id=user_id).update(is_deleted=1)
        for role_id in role_ids:
            CrawlUserRoleRel.objects.create(role_id=role_id,
                                            user_id=user_id)

        # 权限树写进 redis
        user_roles = CrawlUserRoleRel.objects.filter(user_id=user_id)
        crawl_redis.set('permission#user#{}'.format(user_id), json.dumps(build_permission_tree(user_roles)))

        r = Result.success(None)
        return JsonResponse(r)


def get_user(request, user_id):
    """
    获取一个用户
    :param request:
    :param user_id:
    :return:
    """
    if request.method == 'GET':
        user = CrawlUser.objects.get(id=user_id)
        user_role_rels = CrawlUserRoleRel.objects.filter(is_deleted=0, user_id=user_id)

        role_ids = []
        for user_role_rel in user_role_rels:
            role_ids.append(user_role_rel.role_id)
        alert_ids = []

        userD = model_to_dict(user)
        userD.__setitem__('role_ids', role_ids)
        userD.__setitem__('alert_ids', alert_ids)
        r = Result.success(userD)
        return JsonResponse(r)


def reset_pwd(request, user_id):
    """
    重置用户账号密码
    :param user_id:
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            new_pwd = data.get('new_pwd')
            confirm_pwd = data.get('confirm_pwd')
            if new_pwd != confirm_pwd:
                raise Exception('两次密码输入不一致')
            user = CrawlUser.objects.get(id=user_id)
            user.password = password2md5(new_pwd)
            user.save()
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def remove_user(request, user_id):
    """
    移除用户
    :param user_id:
    :param request:
    :return:
    """
    if request.method == 'GET':
        user = CrawlUser.objects.get(id=user_id)
        user.is_deleted = 1
        user.save()

        # 清除用户和角色之间关系
        CrawlUserRoleRel.objects.filter(user_id=user_id).update(is_deleted=1)
        r = Result.success(None)
        return JsonResponse(r)


def query_users(request):
    """
    查询搜索用户
    :param request:
    :return:
    """
    if request.method == 'GET':
        keyword = request.GET.get('keyword')
        size = request.GET.get('size', 15)
        page = request.GET.get('page', 1)
        users = CrawlUser.objects.filter(is_deleted=0)
        if keyword is not None:
            users = users.filter(Q(account__icontains=keyword) | Q(username__icontains=keyword))

        total = users.count()
        r = Result.success(page_helper(total, page, size, users))
        return JsonResponse(r)


def list_role(request):
    """
    角色列表
    :param request:
    :return:
    """
    if request.method == 'GET':
        page = request.GET.get('page', 1)
        size = request.GET.get('size', 15)

        response = []

        roles = CrawlRole.objects.filter(is_deleted=0)

        relsDict = CrawlPermission.objects.filter(is_deleted=0)

        for role in roles:
            rels = CrawlRolePermission.objects.filter(is_deleted=0, role_id=role.id)
            role_permissions = []
            for rel in rels:
                permissions = relsDict.get(id=rel.permission_id)
                role_permissions.append(model_to_dict(permissions).get('permission_name'))
                roleD = model_to_dict(role)
                roleD.__setitem__('permission', role_permissions)
            response.append(roleD)
        r = Result.success(response)
        return JsonResponse(r)


def query_role(request, role_id):
    """
    查询一个角色下面的权限
    :param request:
    :param role_id:
    :return:
    """
    if request.method == 'GET':
        ids = []
        rels = CrawlRolePermission.objects.filter(is_deleted=0,
                                                  role_id=role_id)
        for rel in rels:
            ids.append(rel.permission_id)
        r = Result.success({'permissions': ids})
        return JsonResponse(r)


def edit_role(request, role_id):
    """
    编辑角色
    :param role_id:
    :param request:
    :return:
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        permission_ids = data.get('permission_ids')
        CrawlRolePermission.objects.filter(role_id=role_id).update(is_deleted=1)
        for permission_id in permission_ids:
            CrawlRolePermission.objects.create(role_id=role_id,
                                               permission_id=permission_id)
        r = Result.success(None)
        return JsonResponse(r)


def create_role(request):
    """
    新增角色
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            role_name = data.get('role_name')
            if CrawlRole.objects.filter(role_name=role_name):
                raise Exception('角色名存在')
            role = CrawlRole.objects.create(role_name=role_name)
            permission_ids = data.get('permission_ids')
            for permission_id in permission_ids:
                CrawlRolePermission.objects.create(role_id=role.id,
                                                   permission_id=permission_id)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def query_permissions(request):
    """
    查询所有的权限点（按照两级结构）
    :param request:
    :return:
    """
    if request.method == 'GET':
        response = []
        temp = {}
        permissions = CrawlPermission.objects.filter(is_deleted=0).order_by('parent_id')
        for permission in permissions:
            permission_vo = model_to_dict(permission)
            permission_vo['children'] = []
            if permission_vo.get('parent_id') == 0 or permission_vo.get('parent_id') is None:
                temp[permission_vo.get('id')] = permission_vo
            else:
                temp[permission_vo.get('parent_id')].get('children').append(permission_vo)
        for item in temp:
            response.append(temp.get(item))
        r = Result.success(response)
        return JsonResponse(r)


def login(request):
    """
    登录（TODO 使用jwt）
    :param request:
    :return:
    """
    try:
        domain = settings.SESSION_COOKIE_DOMAIN
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('username').strip()
            password = data.get('password').strip()

            user = CrawlUser.objects.get(username=username)
            if not user:
                raise Exception('用户名或密码不正确')
            else:
                if password2md5(password) == user.password:
                    token = jwt_tools.encode_token(user.id, user.username)
                    r = Result.success(None)
                    response = JsonResponse(r)
                    response.set_cookie('dt_token', bytes.decode(token), domain=domain, max_age=60 * 60 * 24 * 30)
                    response.set_cookie('dt_user_id', user.id, domain=domain, max_age=60 * 60 * 24 * 30)
                    response.set_cookie('dt_username', user.username, domain=domain, max_age=60 * 60 * 24 * 30)
                    return response
                else:
                    raise Exception('用户名或密码不正确')
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def fetch_user_permissions(request):
    """
    获取用户菜单权限列表
    :param request:
    :return:
    """
    user_id = request.user_id
    user_roles = CrawlUserRoleRel.objects.filter(user_id=user_id, is_deleted=0)
    if not user_roles:
        return JsonResponse(Result.success(data={}))
    permission_tree = build_permission_tree(user_roles)
    crawl_redis.set('permission#user#{}'.format(user_id), json.dumps(permission_tree))
    r = Result.success(data=permission_tree)
    return JsonResponse(r)


def build_permission_tree(user_roles):
    all_permissions = list()
    for user_role in user_roles:
        role_permissions = CrawlRolePermission.objects.filter(role_id=user_role.role_id, is_deleted=0)
        for role_permission in role_permissions:
            permission = CrawlPermission.objects.get(id=role_permission.permission_id)
            all_permissions.append(permission)

    response = []
    swap = {}
    for permission in all_permissions:
        permission_vo = model_to_dict(permission)
        permission_vo['children'] = []
        if permission_vo.get('parent_id') == 0:
            swap[permission_vo.get('id')] = permission_vo
        else:
            if permission_vo.get('parent_id') in swap.keys():
                swap[permission_vo.get('parent_id')].get('children').append(permission_vo)
            else:
                parent_permission = CrawlPermission.objects.get(id=permission_vo.get('parent_id'))
                parent_permission_vo = model_to_dict(parent_permission)
                parent_permission_vo['children'] = []
                swap[parent_permission.id] = parent_permission_vo
                swap[permission_vo.get('parent_id')].get('children').append(permission_vo)

    for item in swap:
        response.append(swap.get(item))
    return response
