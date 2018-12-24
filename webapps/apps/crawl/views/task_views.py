import sys
import traceback
from urllib.parse import unquote
import base64

from django.core.paginator import Paginator
from scrapy.utils.response import get_base_url
import json, os, requests, time, pytz, pymongo, string
from shutil import move, copy, rmtree
from requests.exceptions import ConnectionError
from os.path import join, exists, dirname
from django.shortcuts import render
from django.core.serializers import serialize
from django.http import HttpResponse
from django.forms.models import model_to_dict
from django.utils import timezone
from subprocess import Popen, PIPE, STDOUT
from apps.crawl.parser import get_start_requests
from apps.crawl.response import JsonResponse
from server.settings import PROJECTS_FOLDER
from server.settings import TIME_ZONE
from apps.user.models import CrawlUser
from apps.crawl.models.models import CrawlNode, CrawlProject, CrawlDeploy, Monitor, CrawlTask
from apps.crawl.build import build_project, find_egg
from apps.crawl.utils import IGNORES, is_valid_name, copy_tree, TEMPLATES_DIR, TEMPLATES_TO_RENDER, \
    render_template, get_traceback, engine_url, log_url, get_tree, get_engine, process_html, generate_project, \
    get_output_error, bytes2str
from apps.crawl import parser
from server.common.rich_result import Result
from server.common.page_helper import page_helper

"""
    任务管理逻辑
"""


def spider_list(request, client_id, project_name):
    """
    获取某一个爬虫节点下某个爬虫工程的爬虫列表
    :param request: request Object
    :param client_id: client id
    :param project_name: project name
    :return: json
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        engine = engine_url(client)
        try:
            spiders = engine.list_spiders(project_name)
            spiders = [{'name': spider, 'id': index + 1} for index, spider in enumerate(spiders)]
            return JsonResponse(spiders)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'}, status=500)


def spider_start(request, client_id, project_name, spider_name):
    """
    启动爬虫
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :param spider_name: spider name
    :return: json
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        engine = engine_url(client)
        try:
            job = engine.schedule(project_name, spider_name)
            return JsonResponse({'job': job})
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'}, status=500)


def project_list(request, client_id):
    """
    project deployed list on one client
    :param request: request object
    :param client_id: client id
    :return: json
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        engine = get_engine(client)
        try:
            projects = engine.list_projects()
            return JsonResponse(projects)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'}, status=500)


def project_configure(request, project_name):
    """
    get configuration
    :param request: request object
    :param project_name: project name
    :return: json
    """
    # get configuration
    if request.method == 'GET':
        project = CrawlProject.objects.get(name=project_name)
        project = model_to_dict(project)
        project['configuration'] = json.loads(project['configuration']) if project['configuration'] else None
        return JsonResponse(project)
    # update configuration
    elif request.method == 'POST':
        project = CrawlProject.objects.filter(name=project_name)
        data = json.loads(request.body)
        configuration = json.dumps(data.get('configuration'))
        project.update(**{'configuration': configuration})
        # execute generate cmd
        cmd = ' '.join(['gerapy', 'generate', project_name])
        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = bytes2str(p.stdout.read()), bytes2str(p.stderr.read())
        print('RETURN CODE', p.returncode)

        print('stdout', stdout)
        print('stderr', stderr)
        if not stderr:
            return JsonResponse({'status': '1'})
        else:
            return JsonResponse({'status': '0', 'message': stderr})


def job_list(request, client_id, project_name):
    """
    get job list of project from one client
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :return: list of jobs
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        engine = get_engine(client)
        try:
            result = engine.list_jobs(project_name)
            jobs = []
            statuses = ['pending', 'running', 'finished']
            for status in statuses:
                for job in result.get(status):
                    job['status'] = status
                    jobs.append(job)
            return JsonResponse(jobs)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'}, status=500)


def job_log(request, client_id, project_name, spider_name, job_id):
    """
    get log of jog
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :param spider_name: spider name
    :param job_id: job id
    :return: log of job
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        # get log url
        url = log_url(client.ip, client.port, project_name, spider_name, job_id)
        try:
            # get last 1000 bytes of log
            response = requests.get(url, timeout=5, headers={
                'Range': 'bytes=-1000'
            }, auth=(client.username, client.password) if client.auth else None)
            # Get encoding
            encoding = response.apparent_encoding
            # log not found
            if response.status_code == 404:
                return JsonResponse({'message': 'Log Not Found'}, status=404)
            # bytes to string
            text = response.content.decode(encoding, errors='replace')
            return HttpResponse(text)
        except requests.ConnectionError:
            return JsonResponse({'message': 'Load Log Error'}, status=500)


def job_cancel(request, client_id, project_name, job_id):
    """
    cancel a job
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :param job_id: job id
    :return: json of cancel
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        try:
            scrapyd = get_engine(client)
            result = scrapyd.cancel(project_name, job_id)
            return JsonResponse(result)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'})


def task_create(request):
    """
    创建任务
    :param request: request object
    :return: Bool
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))

            if len(CrawlTask.objects.filter(task_name=data['task_name'], is_deleted=0)) > 0:
                raise Exception('任务名称存在')

            data['creator_id'] = request.user_id
            task = CrawlTask.objects.create(**data)
            r = Result.success(model_to_dict(task))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def task_update(request, task_id):
    """
    修改任务
    :param request: request object
    :param task_id: task id
    :return: json
    """
    if request.method == 'POST':
        task = CrawlTask.objects.filter(id=task_id)
        data = json.loads(request.body.decode('utf-8'))
        task.update(**data)
        r = Result.success(model_to_dict(task[0]))
        return JsonResponse(r)


def task_remove(request, task_id):
    """
    删除任务
    :param request:
    :param task_id:
    :return:
    """
    if request.method == 'GET':
        task = CrawlTask.objects.get(id=task_id)
        task.is_deleted = 1
        task.save()
        if task.project_id != 0:
            project = CrawlProject.objects.get(id=task.project_id)
            project.is_deleted = 1
            project.save()
        r = Result.success(None)
        return JsonResponse(r)


def task_info(request, task_id):
    """
    获取任务信息
    :param request: request object
    :param task_id: task id
    :return: json
    """
    if request.method == 'GET':
        task = CrawlTask.objects.get(id=task_id)
        data = model_to_dict(task)
        data['created_at'] = task.created_at
        data['node_ids'] = json.loads(task.node_ids)
        data['creator'] = CrawlUser.objects.get(id=data['creator_id']).username
        r = Result.success(data)
        return JsonResponse(r)


def task_index(request):
    """
    任务列表，支持分页
    :param request:
    :return:
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        keyword = data.get('keyword')
        platform_ids = data.get('platform_id')
        size = data.get('size', 15)
        page = data.get('page', 1)
        is_deploy = data.get('is_deploy')
        tasks = CrawlTask.objects.filter(is_deleted=0)

        if keyword is not None:
            tasks = tasks.filter(task_name__icontains=keyword)
        if platform_ids:
            tasks = tasks.filter(platform_id__in=platform_ids)
        if is_deploy:
            tasks = tasks.filter(is_deploy__in=is_deploy)

        tasks = tasks.order_by("-id")
        total = tasks.count()
        r = Result.success(page_helper(total, page, size, tasks))
        return JsonResponse(r)


def task_deploy(request, task_id):
    """
    发布任务
    :param request:
    :param task_id:
    :return:
    """
    if request.method == 'GET':
        pass
