# coding=utf-8
import json
import datetime
import os
import hashlib
import time
import requests
from os.path import join

from apps.crawl.build import find_egg, build_project
from server.settings import PROJECTS_FOLDER
from django.forms.models import model_to_dict
from django.db import transaction
from apps.crawl.utils import get_engine_by_ip
from apps.crawl.response import JsonResponse
from apps.sync.models import CrawlSyncTask, CrawlSyncInstance, CrawlSyncDataInstance, CrawlSyncData
from server.common.rich_result import Result
from server.common.page_helper import page_helper, to_dict
from server.toolkit import db_kit, time_kit
from server.db_conf import crawl_redis
from server.db_conf import redis_host,redis_port,redis_pwd
from apps.user.models import CrawlUser

def sync_task_list(request):
    """
    所有同步任务
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            keyword = request.GET.get('keyword', '')
            page = request.GET.get('page', 1)
            size = request.GET.get('size', 15)
            sync_tasks = CrawlSyncTask.objects.filter(is_deleted=0, task_name__icontains=keyword) \
                .order_by("-created_at")
            total = sync_tasks.count()
            response = page_helper(total, page, size, sync_tasks)
            results = response.get('results')
            output = []
            for r in results:
                if r['creator_id'] is not None and \
                        r['creator_id'] != '' and \
                        CrawlUser.objects.get(id=r['creator_id']):
                    r['creator_name'] = CrawlUser.objects.get(id=r['creator_id']).username
                else:
                    r['creator_name'] = '未知'
                output.append(r)
            response['results'] = output
            r = Result.success(response)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_task_find(request, sync_task_id):
    """
    查找同步任务
    :param request:
    :param sync_task_id:
    :return:
    """
    try:
        if request.method == 'GET':
            sync_task = to_dict(CrawlSyncTask.objects.get(id=sync_task_id, is_deleted=0))
            sync_task['creator_name'] = CrawlUser.objects.get(id=sync_task['creator_id']).username
            r = Result.success(sync_task)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_task_create(request):
    """
    创建同步任务
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            data['creator_id'] = request.user_id
            # 同步任务名称不可重复校验
            task_name = data.get("task_name")
            has_size = CrawlSyncTask.objects.filter(task_name=task_name, is_deleted=0)
            if has_size and len(has_size) > 0:
                return JsonResponse(Result.fail("该任务名称已存在"))

            if "/" in task_name:
                return JsonResponse(Result.fail("任务名称不能包含/等非法字符"))

            if data['source_cfg'] is not None:
                data['source_cfg'] = json.dumps(data['source_cfg'])
            sync_task = CrawlSyncTask.objects.create(**data)

            # 发布到节点
            # path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
            # project_path = join(path, 'pro_sync_erp')
            # # 检索打包egg文件
            # egg = find_egg(project_path)
            # if egg:
            #     build_project('pro_sync_erp')
            #     egg = find_egg(project_path)
            # if not egg:
            #     r = Result.success("没有打包文件")
            #     return JsonResponse(r)
            # egg_file = open(join(project_path, egg), 'rb')
            # execute_host = data.get("execute_host")
            # for host in execute_host:
            #     engine = get_engine_by_ip(host)
            #     engine.add_version('pro_sync_erp', int(time.time()), egg_file)
            r = Result.success(model_to_dict(sync_task))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_task_update(request, sync_task_id):
    """
    更新同步任务
    :param request:
    :param sync_task_id:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            data['source_cfg'] = json.dumps(data['source_cfg'], ensure_ascii=False)
            sync_task = CrawlSyncTask.objects.filter(id=sync_task_id).update(**data)

            r = Result.success(sync_task)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_task_deploy(request):
    """
    发布同步任务
    :param request:
    :return:
    """
    if request.method == 'POST':
        # 发布到节点
        path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
        project_path = join(path, 'pro_sync_erp')
        # 检索打包egg文件
        build_project('pro_sync_erp')
        egg = find_egg(project_path)
        if not egg:
            r = Result.success("没有打包文件")
            return JsonResponse(r)
        egg_file = open(join(project_path, egg), 'rb')

        task_conf_list = CrawlSyncTask.objects.filter(is_deleted=0)
        execute_host = []
        for task_conf in task_conf_list:
            host_list = eval(task_conf.execute_host)
            for host in host_list:
                if host not in execute_host:
                    execute_host.append(host)
        for host in execute_host:
            engine = get_engine_by_ip(host)
            engine.delete_project('pro_sync_erp')
            engine.add_version('pro_sync_erp', int(time.time()), egg_file)
        r = Result.success(None)
        return JsonResponse(r)


def sync_task_delete(request, sync_task_id):
    """
    删除同步逻辑(逻辑删除)
    :param request:
    :param sync_task_id:
    :return:
    """
    try:
        if request.method == 'GET':
            sync_task = CrawlSyncTask.objects.filter(id=sync_task_id).update(is_deleted=1)
            r = Result.success(sync_task)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_instance_list(request):
    """
    周期实例列表
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            keyword = data.get('keyword')
            task_id = data.get('task_id')
            status = data.get("sync_status")
            page = data.get('page', 1)
            size = data.get('size', 15)

            sync_instances = CrawlSyncInstance.objects.filter(is_deleted=0)
            static_dict = {}
            if status:
                sync_instances = sync_instances.filter(sync_status__in=status)
            if task_id:
                sync_instances = sync_instances.filter(task_id=task_id)
                static_dict['task_id'] = task_id

            success_cnt = sync_instances.filter(sync_status=2).count()
            running_cnt = sync_instances.filter(sync_status=1).count()
            wait_cnt = sync_instances.filter(sync_status=0).count()
            fail_cnt = sync_instances.filter(sync_status=3).count()

            if keyword:
                sync_instances = sync_instances.filter(task_name__icontains=keyword)

            sync_instances = sync_instances.order_by("-id")

            convert_sync_instance = []
            for sync_instance in sync_instances:
                sync_instance.__setattr__('cost_time', time_kit.convert_ms(sync_instance.cost_time))
                convert_sync_instance.append(sync_instance)
            total = sync_instances.count()

            r = Result.success(page_helper(total, page, size, sync_instances,
                                           {'success_cnt': success_cnt,
                                            'running_cnt': running_cnt,
                                            'wait_cnt': wait_cnt,
                                            'fail_cnt': fail_cnt}))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_instance_create(request):
    """
    创建周期实例
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            sync_id = data["sync_id"]
            task_id = data["task_id"]
            crawl_sync_task = CrawlSyncTask.objects.get(id=task_id)
            sync_instance = CrawlSyncInstance.objects.filter(sync_id=sync_id)
            if sync_instance:
                si = sync_instance[0]
                data["id"] = si.id
                data['task_name'] = crawl_sync_task.task_name
                result = sync_instance.update(**data)
            else:
                data['task_name'] = crawl_sync_task.task_name
                result = CrawlSyncInstance.objects.create(**data)
            r = Result.success({})
            return JsonResponse(r)
    except Exception as e:
        import traceback
        traceback.format_exc()
        r = Result.fail(e)
        return JsonResponse(r)


def sync_instance_delete(request):
    """
    删除周期实例
    :param request:
    :return:
    """
    try:
        with transaction.atomic():
            if request.method == 'POST':
                data = json.loads(request.body)
                if not data:
                    raise Exception('请选择需要删除的任务。')
                for instance_id in data:
                    sync_instance = CrawlSyncInstance.objects.get(id=instance_id)
                    if sync_instance.sync_status != 0 and sync_instance.sync_status != 1:
                        raise Exception('只有"等待运行"和"运行中"的任务可删除，请重新选择。')
                    sync_instance.is_deleted = 1
                    sync_instance.save()
                r = Result.success(None)
                return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_instance_rerun(request):
    """
    重跑周期实例任务
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            if not data:
                raise Exception('请选择需要重跑的任务')
            # for instance_id in data:
            # TODO 重跑
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_data_instance_list(request):
    """
    补数据实例列表
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            keyword = request.GET.get('keyword', '')
            biz_start_date = request.GET.get('biz_start_date')
            biz_end_date = request.GET.get('biz_end_date')
            page = request.GET.get('page', 1)
            size = request.GET.get('size', 15)
            sync_data_instances = CrawlSyncDataInstance.objects.filter(is_deleted=0,
                                                                       instance_name__icontains=keyword)
            if biz_start_date is not None and biz_end_date is not None and biz_start_date != '' and biz_end_date != '':
                sync_data_instances = sync_data_instances.filter(biz_start_date__gte=biz_start_date,
                                                                 biz_end_date__lte=biz_end_date)

            total = sync_data_instances.count()
            r = Result.success(page_helper(total, page, size, sync_data_instances))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_data_instance_detail(request, instance_id):
    """
    查找补数据实例
    :param instance_id:
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            keyword = request.GET.get('keyword', '')
            biz_start_date = request.GET.get('biz_start_date')
            biz_end_date = request.GET.get('biz_end_date')
            page = request.GET.get('page', 1)
            size = request.GET.get('size', 15)

            sync_data_instance = CrawlSyncDataInstance.objects.get(id=instance_id)
            sync_data = CrawlSyncData.objects.filter(is_deleted=0,
                                                     instance_id=instance_id)

            success_cnt = sync_data.filter(status=2).count()
            running_cnt = sync_data.filter(status=1).count()
            wait_cnt = sync_data.filter(status=0).count()
            fail_cnt = sync_data.filter(status=3).count()

            if keyword is not None:
                sync_data = sync_data.filter(task_name__icontains=keyword)

            if biz_start_date is not None and biz_end_date is not None and biz_start_date != '' and biz_end_date != '':
                sync_data = sync_data.filter(biz_date__gte=biz_start_date,
                                             biz_date__lte=biz_end_date)

            total = sync_data.count()
            r = Result.success(page_helper(total, page, size, sync_data, {'success_cnt': success_cnt,
                                                                          'running_cnt': running_cnt,
                                                                          'wait_cnt': wait_cnt,
                                                                          'fail_cnt': fail_cnt,
                                                                          'instance_name': sync_data_instance.instance_name}))
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_data_delete(request):
    """
    删除补数据实例
    :param request: 
    :return: 
    """
    try:
        with transaction.atomic():
            if request.method == 'POST':
                data = json.loads(request.body)
                if not data:
                    raise Exception('请选择需要删除的任务。')
                for data_id in data:
                    sync_data = CrawlSyncData.objects.get(id=data_id)
                    if sync_data.status != 0 and sync_data.status != 1:
                        raise Exception('只有"等待运行"和"运行中"的任务可删除，请重新选择。')
                    sync_data.is_deleted = 1
                    sync_data.save()
                r = Result.success(None)
                return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_data_kill_all(request, data_instance_id):
    """
    杀死所有补数据实例
    :param data_instance_id:
    :param request:
    :return:
    """
    try:
        if request.method == 'GET':
            data_list = CrawlSyncData.objects.filter(instance_id=data_instance_id)
            for data in data_list:
                if data.status == 0 and data.status == 1:
                    data.is_deleted = 1
                    data.save()
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_data_rerun(request):
    """
    重跑补数据实例
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            if not data:
                raise Exception('请选择需要重跑的任务')
            # TODO 重跑
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def sync_data_create(request):
    """
    新建补数据实例
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            sync_data_instance_name = data.get('instance_name')
            biz_start_date = data.get('biz_start_date')
            biz_end_date = data.get('biz_end_date')
            task_id = data.get('task_id')

            format_template = '%Y-%m-%d'
            start = datetime.datetime.strptime(biz_start_date, format_template)
            end = datetime.datetime.strptime(biz_end_date, format_template)
            date_range = (end - start).days

            for num in range(date_range):
                delta = datetime.timedelta(days=num)
                n_start = start + delta
                n_end = n_start + datetime.timedelta(days=1)
                instance = CrawlSyncDataInstance.objects.create(instance_name=sync_data_instance_name,
                                                                biz_start_date=n_start,
                                                                biz_end_date=n_end)

            sync_task = CrawlSyncTask.objects.get(id=task_id)

            CrawlSyncData.objects.create(task_name=sync_task.task_name,
                                         instance_id=instance.id,
                                         status=0,
                                         biz_date=biz_start_date,
                                         plan_date=biz_start_date,
                                         start_date=biz_start_date,
                                         end_date=biz_end_date)
            r = Result.success(None)
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)


def md5(md5_char):
    """
    md5算法
    :param md5_char:
    :return:
    """
    hash_md5 = hashlib.md5(md5_char.encode("utf-8"))
    return hash_md5.hexdigest()


def script_start(request):
    """
    启动脚本
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            sync_data = json.loads(request.body.decode('utf-8'))

            if not sync_data:
                return JsonResponse(Result.fail("没有指定同步任务"))

            crawl_sync_task = CrawlSyncTask.objects.get(id=sync_data['id'])
            if not crawl_sync_task:
                return JsonResponse(Result.fail("同步任务不存在"))

            node_ports = eval(crawl_sync_task.execute_host)
            if not crawl_sync_task.source_cfg:
                return JsonResponse(Result.fail("同步任务数据源配置为空"))

            trigger = crawl_sync_task.schedule_date
            source_cfg = eval(crawl_sync_task.source_cfg)
            target_cfg = eval(crawl_sync_task.target_cfg)

            mix = "{}-{}-{}".format(trigger, crawl_sync_task.source_cfg, crawl_sync_task.target_cfg)
            job_id = "{}-{}".format(str(crawl_sync_task.id), mix)
            md5_job = md5(job_id)

            ds = DataSource.objects.get(id=source_cfg['source_id'], is_deleted=0)
            if not ds:
                return JsonResponse(Result.fail("同步任务数据源不存在"))

            top_args = {
                "conditions": source_cfg["source_condition"],
                "path": target_cfg["target_path"],
                "ds": model_to_dict(ds)
            }
            crawl_redis.set("sync#cfg#{}".format(md5_job), json.dumps(top_args))

            for host in node_ports:
                engine = get_engine_by_ip(host)
                args = {
                    "redis": '{{"host":"{}","port": {},"db":1,"password":"{}"}}'.format(redis_host,
                                                                                        str(redis_port),
                                                                                        redis_pwd),
                    "batch_id": md5_job,
                    "task_id": crawl_sync_task.id
                }
                _job_id = engine.schedule('pro_sync_erp', 'erp_sync', **args)
                crawl_sync_task.job_id = _job_id
                crawl_sync_task.save()
        r = Result.success(None)
        return JsonResponse(r)
    except Exception as err:
        r = Result.fail(err)
        return JsonResponse(r)


def newest_log(request):
    """
    查看任务最新日志
    :param request:
    :return:
    """
    try:
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8'))
            # task_id = data.get('task_id')
            job_id = data.get('job_id')
            host_ip = data.get('host_ip')
            # crawl_sync_task = CrawlSyncTask.objects.get(id=task_id)
            url = 'http://{}/logs/pro_sync_erp/erp_sync/{}.log'.format(host_ip, job_id)
            response = requests.get(url)
            if response.status_code != 200:
                r = Result.success({'message': '暂无日志'})
                return JsonResponse(r)
            log_content = response.content.decode('utf-8')
            r = Result.success({'message': log_content})
            return JsonResponse(r)
    except Exception as e:
        r = Result.fail(e)
        return JsonResponse(r)

