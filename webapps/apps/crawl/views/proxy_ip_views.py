import json

from django.core.paginator import Paginator
from django.forms import model_to_dict

from apps.crawl.models.models import CrawlProxyIP
from server.common.rich_result import Result
from server.common.page_helper import page_helper
from apps.crawl.response import JsonResponse


def list_proxy_ip(request):
    """
    所有代理 ip
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            keyword = data.get('keyword')
            page = data.get('page', 1)
            size = data.get('size', 15)
            ip_type = data.get('ip_type')
            status = request.GET.get('status')
            proxy_ips = CrawlProxyIP.objects.filter(is_deleted=0)
            if keyword is not None:
                proxy_ips = proxy_ips.filter(ip__icontains=keyword)
            if ip_type is not None:
                proxy_ips = proxy_ips.filter(ip_type=ip_type)
            if status is not None:
                proxy_ips = proxy_ips.filter(status=status)
            total = proxy_ips.count()
            r = Result.success(page_helper(total, page, size, proxy_ips))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def get_proxy_ip(request, proxy_ip_id):
    """
    获取一个代理 ip
    :param request:
    :param proxy_ip_id:
    :return:
    """
    try:
        if request.method == 'GET':
            proxy_ip = CrawlProxyIP.objects.get(id=proxy_ip_id)
            r = Result.success(model_to_dict(proxy_ip))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def create_proxy_ip(request):
    """
    创建代理 ip
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            CrawlProxyIP.objects.create(**data)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def update_proxy_ip(request, proxy_ip_id):
    """
    编辑代理 ip
    :param proxy_ip_id:
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            CrawlProxyIP.objects.filter(id=proxy_ip_id).update(source=data.get('source'),
                                                               ip=data.get('ip'),
                                                               port=data.get('port'),
                                                               ip_type=data.get('ip_type'))
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def remove_proxy_ip(request, proxy_ip_id):
    """
    删除代理 ip
    :param request:
    :param proxy_ip_id:
    :return:
    """
    try:
        if request.method == 'GET':
            proxy_ip = CrawlProxyIP.objects.get(id=proxy_ip_id)
            proxy_ip.is_deleted = 1
            proxy_ip.save()
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)
