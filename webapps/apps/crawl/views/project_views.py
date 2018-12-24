# coding=utf-8
import json, os, requests, time, pytz
from shutil import move, copy, rmtree
from requests.exceptions import ConnectionError
from os.path import join, exists
from django.shortcuts import render
from django.core.serializers import serialize
from django.http import HttpResponse
from django.forms.models import model_to_dict
from django.utils import timezone
from subprocess import Popen, PIPE, STDOUT
from apps.crawl.parser import get_start_requests, detect_project_spiders
from apps.crawl.response import JsonResponse
from server.settings import PROJECTS_FOLDER
from server.settings import TIME_ZONE
from apps.crawl.models.models import CrawlNode, CrawlProject, CrawlDeploy, Monitor, CrawlTask, CrawlScript
from apps.crawl.build import build_project, find_egg
from apps.crawl.utils import IGNORES, is_valid_name, copy_tree, TEMPLATES_DIR, TEMPLATES_TO_RENDER, \
    render_template, get_traceback, engine_url, log_url, get_tree, get_engine, process_html, generate_project, \
    get_output_error, bytes2str
from apps.crawl import parser
from server.common.rich_result import Result
from server.logging_conf import log_common


def index_status(request):
    """
    统计工程状态
    :param request: request object
    :return: json
    """
    if request.method == 'GET':
        work_path = os.getcwd()
        try:
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
            r = Result.fail(e)
            return JsonResponse(r)
        finally:
            os.chdir(work_path)


def spider_list(request, client_id, project_name):
    """
    get spider list from one client
    :param request: request Object
    :param client_id: client id
    :param project_name: project name
    :return: json
    """
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        engine = get_engine(client)
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
        scrapyd = get_engine(client)
        try:
            job = scrapyd.schedule(project_name, spider_name)
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
        scrapyd = get_engine(client)
        try:
            projects = scrapyd.list_projects()
            return JsonResponse(projects)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'}, status=500)


def project_index(request):
    """
    工程列表(自动识别目录下爬虫工程，该版本没有使用到)
    :param request: request object
    :return: json
    """
    work_path = os.getcwd()
    try:
        if request.method == 'GET':
            path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
            files = os.listdir(path)
            project_lists = []
            for file in files:
                if os.path.isdir(join(path, file)) and file not in IGNORES:
                    project_list.append({'name': file})
            return JsonResponse(project_lists)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)
    finally:
        os.chdir(work_path)


def project_tree(request, project_name):
    """
    获取爬虫工程树形数据
    :param request: request object
    :param project_name: project name
    :return: json of tree
    """
    work_cwd = os.getcwd()
    try:
        if request.method == 'GET':
            path = os.path.abspath(join(work_cwd, PROJECTS_FOLDER))
            tree = get_tree(join(path, project_name))
            r = Result.success(tree)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)
    finally:
        os.chdir(work_cwd)


def project_create(request):
    """
    创建爬虫工程
    :param request: request object
    :return: json
    """
    if request.method == 'POST':
        work_path = os.getcwd()
        try:
            data = json.loads(request.body.decode('utf-8'))
            data['configurable'] = 1
            project, result = CrawlProject.objects.update_or_create(**data)
            path = join(os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER)), data['name'])

            if exists(path):
                return JsonResponse(Result.fail(data="该工程已存在"))
            # 这里判断该工程目录是否存在，如果存在则不创建，直接返回
            os.mkdir(path)
            # 根据模板创建爬虫工程，验证工程名称
            if "name" not in data or "description" not in data:
                return JsonResponse(Result.fail(data="请输入工程名称和描述"))

            project_name = data["name"]
            project_description = data['description']

            generate_project(project_name)
            task_id = data.get('task_id')
            CrawlTask.objects.filter(id=task_id).update(project_name=project_name,
                                                        project_id=project.id,
                                                        description=project_description)

            r = Result.success(data=model_to_dict(project))
            return JsonResponse(r)
        except Exception as e:
            r = Result.fail(e)
            return JsonResponse(r)
        finally:
            os.chdir(work_path)


def project_remove(request, project_name):
    """
    从数据库和磁盘上移除爬虫工程
    :param request: request object
    :param project_name: project name
    :return: result of remove
    """
    if request.method == 'POST':
        work_path = os.getcwd()
        try:
            project = CrawlProject.objects.get(name=project_name)
            CrawlProject.objects.filter(project=project).delete()
            result = CrawlProject.objects.filter(name=project_name).delete()
            path = join(os.path.abspath(os.getcwd()), PROJECTS_FOLDER)
            project_path = join(path, project_name)
            if exists(project_path):
                rmtree(project_path)
            return JsonResponse({'result': result})
        except Exception as e:
            r = Result.fail(e)
            return JsonResponse(r)
        finally:
            os.chdir(work_path)


def project_version(request, client_id, project_name):
    """
    get project deploy version
    :param request: request object
    :param client_id: client id
    :param project_name: project name
    :return: deploy version of project
    """
    if request.method == 'GET':
        # get client and project model
        client = CrawlNode.objects.get(id=client_id)
        project = CrawlProject.objects.get(name=project_name)
        engine = get_engine(client)
        # if deploy info exists in db, return it
        if CrawlDeploy.objects.filter(client=client, project=project):
            deploy = CrawlDeploy.objects.get(client=client, project=project)
        # if deploy info does not exists in db, create deploy info
        else:
            try:
                versions = engine.list_versions(project_name)
            except ConnectionError:
                return JsonResponse({'message': 'Connect Error'}, status=500)
            if len(versions) > 0:
                version = versions[-1]
                deployed_at = timezone.datetime.fromtimestamp(int(version), tz=pytz.timezone(TIME_ZONE))
            else:
                deployed_at = None
            deploy, result = CrawlDeploy.objects.update_or_create(client=client, project=project,
                                                                  deployed_at=deployed_at)
        # return deploy json info
        return JsonResponse(model_to_dict(deploy))


def project_deploy(request, project_name):
    """
    发布爬虫工程
    :param request: request object
    :param project_name: project name
    :return: json of deploy result
    """
    if request.method == 'POST':
        path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
        project_path = join(path, project_name)
        # 检索打包egg文件
        egg = find_egg(project_path)
        if not egg:
            r = Result.success("没有打包文件")
            return JsonResponse(r)
        egg_file = open(join(project_path, egg), 'rb')

        data = json.loads(request.body.decode('utf-8'))
        node_ids = data["node_ids"]

        nodes = CrawlNode.objects.filter(id__in=node_ids)
        project = CrawlProject.objects.get(name=project_name)
        for node in nodes:
            engine = get_engine(node)
            engine.add_version(project_name, int(time.time()), egg_file.read())
            deployed_at = timezone.now()
            CrawlDeploy.objects.filter(node_id=node.id, project_id=project.id).delete()  # 这里逻辑删除
            deploy, result = CrawlDeploy.objects.update_or_create(node_id=node.id, project_id=project.id,
                                                                  deployed_at=deployed_at,
                                                                  description=project.description)
        r = Result.success("")
        return JsonResponse(r)


def task_deploy(request, project_name):
    try:
        log_common.info('进入发布方法')
        work_path = os.getcwd()
        if request.method == 'GET':
            log_common.info('开始发布逻辑')
            path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
            project_path = join(path, project_name)
            # 检索打包egg文件
            egg = find_egg(project_path)
            if not egg:
                raise Exception('没有打包文件')
            egg_file = open(join(project_path, egg), 'rb')
            egg_file_content = egg_file.read()

            project = CrawlProject.objects.get(name=project_name, is_deleted=0)
            task = CrawlTask.objects.get(id=project.task_id)
            task.is_deploy = 1
            task.save()
            for node_id in json.loads(task.node_ids):
                node = CrawlNode.objects.get(id=node_id)
                engine = get_engine(node)
                log_common.info('{}: 准备发布{}'.format(node.node_ip, project_name))
                engine.add_version(project_name, int(time.time()), egg_file_content)
                log_common.info('{}: 发布成功{}'.format(node.node_ip, project_name))
                # update deploy info
                deployed_at = timezone.now()
                CrawlDeploy.objects.filter(node_id=node.id, project_id=project.id).update(is_deleted=1)
                deploy, result = CrawlDeploy.objects.update_or_create(node_id=node.id, project_id=project.id,
                                                                      deployed_at=deployed_at,
                                                                      description=project.description)
            r = Result.success("")
            return JsonResponse(r)
    except Exception as e:
        import traceback
        log_common.error("task_deploy => ", e)
        log_common.error("task_deploy => {}".format(traceback.format_exc()))
        r = Result.fail(e)
        return JsonResponse(r)
    finally:
        os.chdir(work_path)


def project_build(request, project_name):
    """
    爬虫工程编译打包
    :param request: request object
    :param project_name: project name
    :return: json
    """
    path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
    project_path = join(path, project_name)
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        description = data['description']
        build_project(project_name, include_data=False if project_name != 'auto_login' else True)
        egg = find_egg(project_path)
        if not egg:
            return JsonResponse(Result.fail("编译打包失败"))
        built_at = timezone.now()
        if not CrawlProject.objects.filter(name=project_name):
            CrawlProject(name=project_name, description=description, built_at=built_at, egg=egg).save()
            model = CrawlProject.objects.get(name=project_name)
        else:
            model = CrawlProject.objects.get(name=project_name, is_deleted=0)
            model.built_at = built_at
            model.egg = egg
            model.description = description
            model.save()
        data = model_to_dict(model)
        r = Result.success(data)
        return JsonResponse(r)


def project_file_read(request):
    """
    获取爬虫工程文件
    :param request: request object
    :return: file content
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            path = join(data['path'], data['label'])
            project_id = data.get('project_id')
            project_name = data.get("project_name")

            project_base_path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
            project_path = join(project_base_path, project_name)
            label = data.get('label')

            is_spider = 0
            _spider_name = ""
            project_spiders = detect_project_spiders(project_path)
            for spider_name, spider_path in project_spiders.items():
                spider_real_path = spider_path.replace('.', '/', spider_path.count('.') - 1)
                if path.endswith(spider_real_path):
                    is_spider = 1
                    _spider_name = spider_name
                    break

            script = CrawlScript.objects.filter(project_id=project_id, name=_spider_name)
            if not script and _spider_name:
                crawl_task = CrawlTask.objects.get(project_id=project_id)
                script_data = {
                    "name": _spider_name,
                    "project_id": project_id,
                    "task_id": crawl_task.id,
                    "task_name": crawl_task.task_name,
                    "project_name": crawl_task.project_name,
                    "type": 0,
                    "script_file": label,
                    "path": data['path']
                }
                CrawlScript.objects.create(**script_data)
            else:
                if is_spider == 1 and (script[0].path is None or script[0].path == ''):
                    script[0].path = data['path']
                    script[0].save()
            with open(path, 'rb') as f:
                if len(script) is not 0:
                    vo = {'content': f.read().decode('utf-8'),
                          'name': data['label'],
                          'is_spider': is_spider,
                          'trigger': script[0].trigger,
                          'hosts': script[0].hosts,
                          'params': script[0].args,
                          'spider_name': _spider_name,
                          'use_proxy': script[0].use_proxy,
                          }
                else:
                    vo = {'content': f.read().decode('utf-8'),
                          'name': data['label'],
                          'is_spider': is_spider,
                          'trigger': '',
                          'hosts': '',
                          'params': '',
                          'spider_name': _spider_name,
                          'use_proxy': '',
                          }
                r = Result.success(vo)
                return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def project_file_update(request):
    """
    修改爬虫工程文件
    :param request: request object
    :return: result of update
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        path = join(data['path'], data['label'])
        code = data['code']
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
            r = Result.success("")
            return JsonResponse(r)


def project_file_create(request):
    """
    创建爬虫工程文件
    :param request: request object
    :return: result of create
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        path = join(data['path'], data['name'])
        open(path, 'w', encoding='utf-8').close()
        r = Result.success("")
        return JsonResponse(r)


def project_file_delete(request):
    """
    删除爬虫工程文件
    :param request: request object
    :return: result of delete
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        path = join(data['path'], data['label'])
        os.remove(path)
        return JsonResponse(Result.success(""))


def project_file_rename(request):
    """
    重命名爬虫工程文件
    :param request: request object
    :return: result of rename
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        pre = join(data['path'], data['pre'])
        new = join(data['path'], data['new'])
        os.rename(pre, new)
        return JsonResponse(Result.success(""))


def del_version(request, client_id, project, version):
    """
    删除指定版本的爬虫工程
    :param request:
    :param client_id:
    :param project:
    :param version:
    :return:
    """
    if request.method == 'GET':
        node = CrawlNode.objects.get(id=client_id)
        try:
            engine = get_engine(node)
            result = engine.delete_version(project=project, version=version)
            return JsonResponse(result)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'})


def del_project(request, client_id, project):
    if request.method == 'GET':
        client = CrawlNode.objects.get(id=client_id)
        try:
            scrapyd = get_engine(client)
            result = scrapyd.delete_project(project=project)
            return JsonResponse(result)
        except ConnectionError:
            return JsonResponse({'message': 'Connect Error'})


def task_create(request):
    """
    创建任务
    :param request: request object
    :return: Bool
    """
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        task = CrawlTask.objects.create(**data)
        r = Result.success(model_to_dict(task))
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
        data = json.loads(request.body)
        data['clients'] = json.dumps(data.get('clients'))
        data['configuration'] = json.dumps(data.get('configuration'))
        data['success'] = 0
        task.update(**data)
        return JsonResponse(model_to_dict(CrawlTask.objects.get(id=task_id)))


def task_remove(request, task_id):
    """
    删除任务
    :param request:
    :param task_id:
    :return:
    """
    if request.method == 'POST':
        try:
            CrawlTask.objects.filter(id=task_id).delete()
            return JsonResponse({'result': '1'})
        except:
            # TODO 日志
            return JsonResponse({'result': '0'})


def task_info(request, task_id):
    """
    get task info
    :param request: request object
    :param task_id: task id
    :return: json
    """
    if request.method == 'GET':
        task = CrawlTask.objects.get(id=task_id)
        data = model_to_dict(task)
        print(data)
        data['clients'] = json.loads(data.get('clients'))
        data['configuration'] = json.loads(data.get('configuration'))
        return JsonResponse({'data': data})
