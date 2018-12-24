import json, os, requests
from requests.exceptions import ConnectionError
from os.path import join
from django.core.serializers import serialize
from django.http import HttpResponse
from django.forms.models import model_to_dict
from apps.crawl.response import JsonResponse
from server.settings import PROJECTS_FOLDER
from apps.crawl.models.models import CrawlNode, CrawlDeploy
from apps.crawl.utils import IGNORES, engine_url, get_engine
from server.common.rich_result import Result
from server.common.page_helper import to_dict, page_helper
from server.logging_conf import log_common


def index_status(request):
    """
    统计工程状态
    :param request: request object
    :return: json
    """
    work_path = os.getcwd()
    try:
        if request.method == 'GET':
            nodes = CrawlNode.objects.all()
            data = {
                'success': 0,
                'error': 0,
                'project': 0,
            }
            for client in nodes:
                try:
                    requests.get(engine_url(client.ip, client.port), timeout=1)
                    data['success'] += 1
                except ConnectionError:
                    data['error'] += 1
            path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
            files = os.listdir(path)
            for file in files:
                if os.path.isdir(join(path, file)) and file not in IGNORES:
                    data['project'] += 1
            return JsonResponse(data)
    except Exception as e:
        return JsonResponse(Result.fail(e))
    finally:
        os.chdir(work_path)


def node_index(request):
    """
    获取节点列表
    :param request: request object
    :return: client list
    """
    if request.method == 'GET':
        data = CrawlNode.objects.filter(is_deleted=0).order_by('-id')
        r = Result.success(data)
        return JsonResponse(r)


def node_info(request, client_id):
    """
    获取爬虫节点信息
    :param request: request object
    :param id: client id
    :return: json
    """
    if request.method == 'GET':
        data = model_to_dict(CrawlNode.objects.get(id=client_id))
        r = Result.success(data=data)
        return JsonResponse(r)


def node_status(request, node_id):
    """
    获取某个爬虫节点的状态
    :param request: request object
    :param node_id: node_id id
    :return: json
    """
    if request.method == 'GET':
        # get client object
        client = CrawlNode.objects.get(id=node_id)
        try:
            requests.get(engine_url(client.ip, client.port), timeout=3)
            return JsonResponse(Result.success(""))
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'}, status=500)


def node_update(request, client_id):
    """
    修改爬虫节点信息
    :param request: request object
    :param client_id: client id
    :return: json
    """
    if request.method == 'POST':
        client = CrawlNode.objects.filter(id=client_id)
        data = json.loads(request.body)
        client.update(**data)
        return JsonResponse(model_to_dict(CrawlNode.objects.get(id=client_id)))


def node_create(request):
    """
    创建爬虫节点
    :param request: request object
    :return: json
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        cn = CrawlNode.objects.filter(node_ip=data["node_ip"]).last()
        if not cn:
            node = CrawlNode.objects.create(**data)
            r = Result.success(model_to_dict(node))
            return JsonResponse(r)
        else:
            # 更改心跳时间，表示节点存活
            return JsonResponse(Result.fail('节点已存在'))


def node_remove(request, client_id):
    """
    删除节点
    :param request: request object
    :param client_id: client id
    :return: json
    """
    if request.method == 'POST':
        client = CrawlNode.objects.get(id=client_id)
        # delete deploy
        CrawlDeploy.objects.filter(node_id=client_id).delete()
        # delete client
        CrawlNode.objects.filter(id=client_id).delete()
        return JsonResponse({'result': '1'})


def project_list(request, node_id):
    """
    获取某个node节点上的爬虫工程
    :param request: request object
    :param node_id: node_id
    :return: json
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=node_id)
        engine = get_engine(client)
        try:
            projects = engine.list_projects()
            JsonResponse(Result.success(data=projects))
        except ConnectionError:
            return JsonResponse(Result.fail())


def node_manager(request):
    if request.method == 'GET':
        page = request.GET.get('page', 1)
        size = request.GET.get('size', 15)
        nodes = list(CrawlNode.objects.filter(is_deleted=0))
        total = len(nodes)
        output_nodes = []
        for client in nodes:
            # node_url = engine_url(client.node_ip, client.node_port)
            # node_url = engine_url('120.27.210.65', '6800')
            client_d = to_dict(client)
            output_nodes.append(client_d)
        r = Result.success(page_helper(total, page, size, output_nodes))
        return JsonResponse(r)


def node_spider_info(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        node_url = engine_url(data['node_ip'], data['node_port'])
        client_d = {}
        try:
            client_d['status'] = 'disconnect'
            client_d['projects_count'] = 0
            client_d['projects'] = []
            client_d['spiders_count'] = client_d['pending'] = client_d['running'] = client_d['finished'] = 0
            response = requests.get(node_url + '/listprojects.json', timeout=2)
            if response:
                info = json.loads(response.text)
                client_d['projects_count'] = len(info['projects'])
                client_d['projects'] = info['projects']
                client_d['status'] = info['status']
                for project in info['projects']:
                    project_info = json.loads(
                        requests.get(node_url + '/listspiders.json?project=' + project, timeout=2).text)
                    client_d['spiders_count'] = client_d['spiders_count'] + len(project_info['spiders'])
                    project_info = json.loads(
                        requests.get(node_url + '/listjobs.json?project=' + project, timeout=2).text)
                    client_d['pending'] = client_d['pending'] + len(project_info['pending'])
                    client_d['running'] = client_d['running'] + len(project_info['running'])
                    client_d['finished'] = client_d['running'] + len(project_info['finished'])
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.HTTPError) as e:
            log_common.error(e)
        r = Result.success(client_d)
        return JsonResponse(r)
