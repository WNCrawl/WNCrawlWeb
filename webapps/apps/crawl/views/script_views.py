import _thread
import datetime
import json, os, requests

import cv2
import numpy as np
from django.db import IntegrityError
from requests.exceptions import ConnectionError
from os.path import join
from django.http import HttpResponse
from django.forms.models import model_to_dict

from apps.crawl.response import JsonResponse
from server import db_conf
from server.common import scheduler_helper, wx_tools, engine_kit
from server.settings import PROJECTS_FOLDER
from apps.crawl.models.models import CrawlNode, CrawlProject, CrawlDeploy, Monitor, CrawlTask, CrawlScript, \
    CrawlScriptProgress
from apps.crawl.utils import engine_url, log_url, get_engine, process_html, generate_project, \
    get_output_error, bytes2str, get_engine_by_ip, get_general_engine
from apps.crawl import parser
from server.common.rich_result import Result
from server.common.page_helper import page_helper
from server.logging_conf import log_common
from server.db_conf import crawl_redis
from server.toolkit import encrypt_kit, time_kit, db_kit
import time
import base64

"""
    脚本管理逻辑
"""


def node_spider_list(request):
    """
    某个爬虫工程节点爬虫脚本分布列表
    :param request:
    :return:
    """
    if request.method == 'GET':
        project_id = request.GET.get("project_id")
        project_id = CrawlTask.objects.get(id=project_id).project_id
        deploys = CrawlDeploy.objects.filter(project_id=project_id)
        node_spiders = []
        for deploy in deploys:
            node_spider = []
            node = CrawlNode.objects.get(id=deploy.node_id)
            engine = get_engine(node)
            try:
                # spiders = engine.list_spiders(deploy.project_name)
                # 写入爬虫脚本表，这个根据性能需要考虑是否后台实时写入
                # new_data = {
                #     "name": "",
                #     "desc": "",
                #     "trigger": "",
                #     "hosts": "",
                #     "args": "",
                #     "type": 1,
                #     "project_id": project_id
                # }
                # CrawlScript.objects.create()
                scripts = CrawlScript.objects.filter(project_id=project_id)
                # spiders = [{'name': spider, 'id': index + 1} for index, spider in enumerate(spiders)]
                node_spider.append({"node": node, "scripts": scripts})
                node_spiders.append(node_spider)
            except ConnectionError:
                return JsonResponse(Result.fail("{}爬虫节点不能提供服务".format(node.node_name)))
        r = Result.success(node_spiders)
        return JsonResponse(r)


def list_scripts(request):
    """
    某个爬虫工程节点爬虫脚本分布列表
    :param request:
    :return:
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        size = data.get('size', 15)
        page = data.get('page', 1)
        task_name = data.get("task_name")
        task_id = data.get("task_id")
        script_name = data.get("script_name")

        scripts = CrawlScript.objects.filter(is_deleted=0)
        if task_id:
            scripts = scripts.filter(task_id=task_id)
        if script_name:
            scripts = scripts.filter(name__contains=script_name)
        if task_name:
            scripts = scripts.filter(task_name__contains=task_name)

        scripts = scripts.order_by("-id")
        total = scripts.count()
        response = page_helper(total, page, size, scripts)
        results = response.get('results')
        for result in results:
            result.__setitem__('hosts', ','.join(get_hosts_by_script_id(result.get('id'))))
        r = Result.success(response)
        return JsonResponse(r)


def spider_list(request, client_id, project_name):
    """
    获取某一个爬虫节点下某个工程的爬虫列表
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


def job_list(request, client_id, project_name):
    """
    获取某个节点上爬虫工程的任务列表
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
    获取任务日志
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :param spider_name: spider name
    :param job_id: job id
    :return: log of job
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        url = log_url(client.ip, client.port, project_name, spider_name, job_id)
        try:
            response = requests.get(url, timeout=5, headers={
                'Range': 'bytes=-1000'
            }, auth=(client.username, client.password) if client.auth else None)
            encoding = response.apparent_encoding
            if response.status_code == 404:
                return JsonResponse({'message': 'Log Not Found'}, status=404)
            text = response.content.decode(encoding, errors='replace')
            return HttpResponse(text)
        except requests.ConnectionError:
            return JsonResponse({'message': 'Load Log Error'}, status=500)


def job_cancel(request, client_id, project_name, job_id):
    """
    取消停止一个爬虫
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :param job_id: job id
    :return: json of cancel
    """
    if request.method == 'GET':
        node = CrawlNode.objects.get(id=client_id)
        try:
            engine = get_engine(node)
            result = engine.cancel(project_name, job_id)
            return JsonResponse(result)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'})


def edit_script_cfg(request):
    """
    编辑爬虫脚本配置
    :param request: request object
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            spider_name = data['spider_name']
            script_name = data['script_name']
            apply_to_all = data['applyToAll']
            task_id = data['project_id']

            script_args = []
            for p in data.get('params'):
                if isinstance(p['args'], str):
                    p['args'] = json.loads(p['args'])
                script_args.append(p)
                if p.get('trigger'):
                    result, message = scheduler_helper.verify_cron(p.get('trigger'))
                    if not result:
                        raise Exception('参数错误: {}'.format(message))

            update_kwargs = {
                "trigger": data.get('trigger'),
                "hosts": data.get('hosts'),
                "args": json.dumps(script_args)}


            # 批量设置当前任务的所有脚本
            if apply_to_all:
                crawl_scripts = CrawlScript.objects.filter(task_id=task_id)
                crawl_scripts.update(**update_kwargs)
            else:
                crawl_scripts = CrawlScript.objects.get(name=spider_name, task_id=task_id)
                crawl_scripts.trigger = data.get('trigger')
                crawl_scripts.hosts = data.get('hosts')
                crawl_scripts.args = json.dumps(script_args)
                crawl_scripts.save()

            if 'params' in data and data['params']:
                args = data['params']
                # 设置每个爬虫脚本的执行参数，不同调度批次的爬虫运行参数使用md5区分
                for arg in args:
                    if apply_to_all:
                        for script in crawl_scripts:
                            v_arg = encrypt_kit.md5(json.dumps(arg))
                            crawl_redis.set("args#{}#{}".format(script.name, v_arg), json.dumps(arg['args']))
                    else:
                        v_arg = encrypt_kit.md5(json.dumps(arg))
                        crawl_redis.set("args#{}#{}".format(spider_name, v_arg), json.dumps(arg['args']))

            r = Result.success("")
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def debug_script(request):
    """
    测试运行脚本
    :param request: request object
    :return:
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        project_name = data["project_name"]
        spider_name = data["spider_name"]

        project_base_path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
        project_path = join(project_base_path, project_name)

        # get_follow_requests_and_items(project_path, spider_name)

        # output = get_output_error(project_name, spider_name)
        _thread.start_new_thread(get_output_error, (project_name, spider_name))

        # r = Result.success(data=output)
        r = Result.success(None)
        return JsonResponse(r)


def find_debug_result(request):
    """
    查看测试执行结果
    :param request:
    :return:
    """
    work_path = os.getcwd()
    try:
        if request.method == 'GET':
            project_name = request.GET.get('project_name')
            spider_name = request.GET.get('spider_name')
            project_path = join(PROJECTS_FOLDER, project_name)
            os.chdir(project_path)
            if not os.path.exists("debug_folder"):
                r = Result.success(data='')
                return JsonResponse(r)
            input_file = open('./debug_folder/items/{}.json'.format(spider_name))
            all_text = input_file.read()
            input_file.close()
            r = Result.success({'content': all_text})
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)
    finally:
        os.chdir(work_path)


def find_debug_log(request):
    """
    查看测试执行日志
    :param request:
    :return:
    """
    work_path = os.getcwd()
    try:
        if request.method == 'GET':
            project_name = request.GET.get('project_name')
            spider_name = request.GET.get('spider_name')
            current_line = int(request.GET.get('current_line'))
            project_path = join(PROJECTS_FOLDER, project_name)
            os.chdir(project_path)
            if not os.path.exists("debug_folder"):
                r = Result.success(data='')
                return JsonResponse(r)
            input_file = open('./debug_folder/logs/{}.log'.format(spider_name), 'r', encoding='utf-8')
            lines = input_file.readlines()
            input_file.close()
            response = []
            for line in lines[(current_line - 1):]:
                data = {'current_line': current_line, 'data': line}
                response.append(data)
                current_line = current_line + 1
            r = Result.success(response)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)
    finally:
        os.chdir(work_path)


def format_debug_result(request):
    """
    格式化测试执行结果
    :param request:
    :return:
    """
    pass


def task_by_script_id(request, script_id):
    """
    根据脚本 id 获取任务
    :param script_id:
    :param request:
    :return:
    """
    work_path = os.getcwd()
    try:
        if request.method == 'GET':
            script = CrawlScript.objects.get(id=script_id)
            project = CrawlProject.objects.get(id=script.project_id)
            task = CrawlTask.objects.get(id=project.task_id)
            path = os.path.abspath(join(work_path, PROJECTS_FOLDER))
            script_name = script.name

            vo = model_to_dict(task)
            vo.__setitem__('path', path)
            vo.__setitem__('script_name', script.script_file)
            r = Result.success(vo)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)
    finally:
        os.chdir(work_path)


def list_task_progress(request):
    """
    爬虫任务进度
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            keyword = data.get('keyword')
            script_name = data.get('script_name')
            date = data.get('date')
            status = data.get('status')
            page = data.get('page', 1)
            size = data.get('size', 15)

            task_progress = CrawlScriptProgress.objects.filter(is_deleted=0).exclude(script_name='proxy')

            condition_date = datetime.datetime.today().strftime('%Y-%m-%d') if date == '' else date
            stat_task_progress = task_progress.filter(start_time__gte='{} 00:00:00'.format(condition_date),
                                                      start_time__lte='{} 23:59:59'.format(condition_date))
            running_cnt = stat_task_progress.filter(status=1).count()
            success_cnt = stat_task_progress.filter(status=2).count()
            fail_cnt = stat_task_progress.filter(status=-1).count()

            if keyword is not None and keyword != '':
                task_progress = task_progress.filter(task_name__icontains=keyword)
            if script_name is not None and script_name != '':
                task_progress = task_progress.filter(script_name__icontains=script_name)
            if date is not None and date != '':
                task_progress = task_progress.filter(start_time__gte='{} 00:00:00'.format(date),
                                                     start_time__lte='{} 23:59:59'.format(date))
            if status is not None:
                task_progress = task_progress.filter(status__in=status)
            task_progress = task_progress.order_by("-id")

            total = task_progress.count()
            pager = page_helper(total, page, size, task_progress, {'fail_cnt': fail_cnt,
                                                                   'running_cnt': running_cnt,
                                                                   'success_cnt': success_cnt})
            convert_task_progress = []
            results = pager.get('results')
            for result in results:
                result['run_time'] = time_kit.convert_ms(result.get('run_time'))
                result['script_id'] = CrawlScript.objects.get(task_name=result.get('task_name'),
                                                              name=result.get('script_name')).id
                convert_task_progress.append(result)
            pager['results'] = convert_task_progress

            r = Result.success(pager)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def collect_script_progress(request):
    """
    采集接收保存任务执行数据
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            script_name = data["script_name"]
            batch = data["batch"]
            script_progress = CrawlScriptProgress.objects.filter(script_name=script_name, batch=batch)
            arg_key = data.get('arg_key')
            if arg_key:
                data['arg'] = bytes.decode(crawl_redis.get('args#{}'.format(arg_key)))

            log_common.error('script_name: {}, batch_id: {}'.format(script_name, batch))

            if script_progress:
                log_common.error('update progress script_name:{}, batch_id: {}'.format(script_name, batch))
                sp = script_progress[0]
                data["task_name"] = sp.task_name
                data["id"] = sp.id

                if data['status'] == -1 and not data.get('msg') and sp.msg:
                    data['msg'] = sp.msg

                result = script_progress.update(**data)

                if data['status'] == -1:
                    user_alert_rel = CrawlUserAlertRel.objects.filter(alert_id=12, is_deleted=0)
                    user_ids = list(map(lambda x: str(x.user_id), user_alert_rel))
                    to_user = '|'.join(user_ids)
                    wx_tools.env_send_card_message(to_user, '爬虫异常', '爬虫: {} 发生异常'.format(script_name))
            else:
                try:
                    log_common.error('new progress script_name:{}, batch_id: {}'.format(script_name, batch))
                    css = CrawlScript.objects.filter(name=script_name, is_deleted=0)
                    if css:
                        cs = css[0]
                        data["task_name"] = cs.task_name
                        result = CrawlScriptProgress.objects.create(**data)
                    else:
                        log_common.warn("no find {} of task!".format(script_name))
                except IntegrityError as e:
                    log_common.error('>>>>>>>>>>>>>>>>>>> catch IntegrityError >>>>>>>>>>>>>>>>>>>>>')
                    # 处理并发情况下脚本上报两次的情况
                    script_progress = CrawlScriptProgress.objects.filter(script_name=script_name, batch=batch)
                    sp = script_progress[0]
                    data["task_name"] = sp.task_name
                    data["id"] = sp.id
                    result = script_progress.update(**data)
                    if data['status'] == -1:
                        user_alert_rel = CrawlUserAlertRel.objects.filter(alert_id=12, is_deleted=0)
                        user_ids = list(map(lambda x: x.user_id, user_alert_rel))
                        to_user = '|'.join(user_ids)
                        wx_tools.env_send_card_message(to_user, '爬虫异常', '爬虫: {} 发生异常'.format(script_name))
            r = Result.success({})
            return JsonResponse(r)
    except Exception as e:
        import traceback
        log_common.error('v3v3:上报数据异常，具体错误 = {}'.format(traceback.format_exc()))
        r = Result.fail(e)
        return JsonResponse(r)


def script_start(request):
    """
    启动脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data_scripts = json.loads(request.body.decode('utf-8'))

            if not data_scripts:
                return JsonResponse(Result.fail("没有指定脚本"))

            for data_script in data_scripts:
                _job_id = ''
                crawl_script = CrawlScript.objects.get(id=data_script['id'])
                host_list = get_hosts_by_script_id(crawl_script.id)
                for host in host_list:
                    engine = get_engine_by_ip(host)
                    if "args" in data_script and data_script["args"]:
                        for arg in data_script["args"]:
                            if 'dynamic_value' in arg:
                                script_arg = json.loads(arg)
                                sql = script_arg.get('dynamic_value')
                                result = db_kit.fetch_all_to_json(sql)
                                for r in result:
                                    if isinstance(arg, str):
                                        arg = json.loads(arg)
                                    arg['dynamic_value'] = r
                                    batch_id = encrypt_kit.md5(json.dumps(arg))
                                    args = {
                                        "redis": '{{"host":"{}","port": {},"db":1,"password":"{}"}}'.format(db_conf.redis_host,
                                                                                                            str(
                                                                                                                db_conf.redis_port),
                                                                                                            db_conf.redis_pwd),
                                        "batch_id": batch_id,
                                        "node": host,
                                        "args": arg
                                    }
                                    # _job_id = engine.schedule(crawl_script.project_name, crawl_script.name, **args)
                                    log_common.warn('>>>> 动态分割脚本启动 {}'.format(json.dumps(args)))
                                    _job_id = engine_kit.schedule(engine, crawl_script.project_name, crawl_script.name, **args)
                                    crawl_redis.set("args#{}".format(batch_id), json.dumps(arg))
                            else:
                                batch_id = encrypt_kit.md5(json.dumps(arg))
                                args = {
                                    "redis": '{{"host":"{}","port": {},"db":1,"password":"{}"}}'.format(
                                        db_conf.redis_host,
                                        str(
                                            db_conf.redis_port),
                                        db_conf.redis_pwd),
                                    "batch_id": batch_id,
                                    "node": host,
                                    "args": arg
                                }
                                # _job_id = engine.schedule(crawl_script.project_name, crawl_script.name, **args)
                                _job_id = engine_kit.schedule(engine, crawl_script.project_name, crawl_script.name,
                                                              **args)
                                crawl_redis.set("args#{}".format(batch_id), arg)
                    else:
                        ta = time.strftime('%Y-%m-%d %H:%M:%S')
                        batch_id = encrypt_kit.md5(ta)
                        args = {
                            "redis": '{{"host":"{}","port": {},"db":1,"password":"{}"}}'.format(db_conf.redis_host,
                                                                                                str(db_conf.redis_port),
                                                                                                db_conf.redis_pwd),
                            "batch_id": batch_id,
                            "node": host,
                            "args": '{}'
                        }
                        _job_id = engine_kit.schedule(engine, crawl_script.project_name, crawl_script.name, **args)
                        # _job_id = engine.schedule(crawl_script.project_name, crawl_script.name, **args)
                        crawl_redis.set("args#{}".format(batch_id), json.dumps('{}'))
                crawl_script.job_id = _job_id
                crawl_script.save()
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as err:
        r = Result.fail(err)
        return JsonResponse(r)


def script_stop(request):
    """
    启动脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data_scripts = json.loads(request.body.decode('utf-8'))

            if not data_scripts:
                return JsonResponse(Result.fail("没有指定脚本"))

            for data_script in data_scripts:
                crawl_script = CrawlScript.objects.get(id=data_script["id"])
                host_list = get_hosts_by_script_id(crawl_script.id)
                for host in host_list:
                    engine = get_engine_by_ip(host)

                    args = {
                        "redis": '{{"host":"{}","port": {},"db":1,"password":"{}"}}'.format(db_conf.redis_host,
                                                                                            str(db_conf.redis_port),
                                                                                            db_conf.redis_pwd),
                        "batch_id": ''
                    }
                    jobs = engine.cancel(crawl_script.project_name, crawl_script.name)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as err:
        r = Result.fail(err)
        return JsonResponse(r)


def job_cancel_all(request):
    """
    根据 script 停止所有节点上的脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            for d in data:
                script_id = d.get('id')
                script = CrawlScript.objects.get(id=script_id)
                project_name = script.project_name
                nodes = get_hosts_by_script_id(script.id)
                for node in nodes:
                    engine = get_engine_by_ip(node)
                    host = 'http://{}'.format(node)
                    url = '{}/listjobs.json?project={}'.format(host, project_name)
                    # url = 'http://120.27.210.65:6800/listjobs.json?project=proxy'
                    r = requests.get(url).json()

                    # 过滤掉不是这个脚本
                    running_task = list(filter(lambda x: x.get('spider') == script.name, r.get('running')))
                    pending_task = list(filter(lambda x: x.get('spider') == script.name, r.get('pending')))

                    running_id_list = list(map(lambda x: x.get('id'), running_task))
                    pending_id_list = list(map(lambda x: x.get('id'), pending_task))

                    stop_id_list = running_id_list + pending_id_list
                    for stop_id in stop_id_list:
                        result = engine.cancel(project_name, stop_id)
                        print(request)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def script_newest_log(request):
    """
    获取脚本最新日志
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            script_id = data.get('script_id')
            host_ip = data.get('host_ip')
            script = CrawlScript.objects.get(id=script_id)
            project_name = script.project_name
            spider_name = script.name
            job_id = script.job_id
            if not job_id:
                r = Result.success('暂无日志')
                return JsonResponse(r)

            url = 'http://{}/logs/{}/{}/{}.log'.format(host_ip, project_name, spider_name, job_id)
            response = requests.get(url)
            if response.status_code != 200:
                r = Result.success('暂无日志')
                return JsonResponse(r)
            log_content = response.content.decode('utf-8')
            r = Result.success({'message': log_content})
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def script_disable(request):
    """
    禁用脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            ids = data.get('ids')
            control_script(ids, 1)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def script_enable(request):
    """
    启用脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            ids = data.get('ids')
            control_script(ids, 0)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def script_remove(request):
    """
    删除脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            id = request.GET['id']
            CrawlScript.objects.get(id=id).delete()
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def control_script(ids, status):
    """
    控制脚本启用  0 启用 / 1 禁用
    :param ids:
    :param status:
    :return:
    """
    for script_id in ids:
        script = CrawlScript.objects.get(id=script_id)
        script.is_disable = int(status)
        script.save()


def get_hosts(request):
    """
    根据脚本 id 获取 hosts
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            script_id = request.GET.get('script_id')
            hosts = get_hosts_by_script_id(script_id)
            r = Result.success(hosts)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def get_hosts_by_script_id(script_id):
    crawl_script = CrawlScript.objects.get(id=script_id)
    host_list = []
    hosts = crawl_script.hosts
    if not hosts or hosts == '[]':
        node_ids = CrawlTask.objects.get(id=crawl_script.task_id).node_ids
        for node_id in json.loads(node_ids):
            node = CrawlNode.objects.get(id=node_id)
            host_list.append('{}:{}'.format(node.node_ip, node.node_port))
    else:
        host_list = eval(hosts)
    return host_list


def img_parser(request):
    """
    解析图片位置
    :param request:
    :return:
    """
    if request.method == 'POST':
        big_img_base64 = request.POST.get('bkg_file')
        small_img_base64 = request.POST.get('block_file')
        sha_md5 = request.POST.get('md5')
        path = os.path.abspath(join(os.getcwd(), "auto_login/snap_shoot"))
        if not os.path.exists(path):
            os.makedirs(path)
        bkg_file = os.path.join(path, "%s.png" % sha_md5)
        block_file = os.path.join(path, "block_%s.png" % sha_md5)

        save_base64_to_image(big_img_base64, bkg_file)
        save_base64_to_image(small_img_base64, block_file)

        x, y = analysis_location(bkg_file, block_file)
        response = {'x': int(x), 'y': int(y)}
        r = Result.success(data={'result': response})
        return JsonResponse(r)


def save_base64_to_image(data, file_path):
    """
    base64转图片文件
    :param data:
    :param file_path:
    :return:
    """
    image_data = base64.b64decode(data.split('base64,')[1])
    with open(file_path, 'wb') as f:
        f.write(image_data)
        f.close()


def analysis_location(bkg_file, block_file):
    """
    解析图片位置
    :param bkg_file:
    :param block_file:
    :return:
    """
    bkg_image = cv2.imread(bkg_file, 0)  # 读取背景图片
    block_image = cv2.imread(block_file, 0)  # 读取块图片
    temp_image = abs(255 - block_image)
    # cv2.Sobel(temp_image, temp_image, 1, 0, 3)
    # cv2.Sobel(bkg_image, bkg_image, 1, 0, 3)
    result = cv2.matchTemplate(temp_image, bkg_image, cv2.TM_CCOEFF_NORMED)
    y, x = np.unravel_index(result.argmax(), result.shape)
    return x, y
