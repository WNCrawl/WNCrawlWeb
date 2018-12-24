#!/usr/bin/env python
# encoding: utf-8
import datetime
import time
import json
import logging
import threading
import hashlib
import uuid

from apscheduler.jobstores.memory import MemoryJobStore
from django.db import connections

from server import db_conf
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore

from server.common import engine_kit
from server.common.alert_exception import AlertException
from server.db_conf import crawl_redis, redis_host, redis_port, redis_pwd, redis_db_name, dlm, sql_config
from apps.crawl.models.models import CrawlScript, CrawlProject, CrawlTask, CrawlNode
from apps.crawl.utils import get_engine_by_ip, get_general_engine
from server.logging_conf import log_common
from server.common.alert_enum import Alert
from server.toolkit import db_kit

db_time_format = "%Y-%m-%d %H:%M:%S"

redis_args = {
    'host': redis_host,
    'port': redis_port,
    'db': redis_db_name,
    'password': redis_pwd
}
executors = {
    'default': ThreadPoolExecutor(30)
}

redis_job_store = RedisJobStore(jobs_key='crawl_apscheduler.jobs', run_times_key='crawl_apscheduler.run_times', **redis_args)
scheduler = BackgroundScheduler(executors=executors)
scheduler.add_jobstore(MemoryJobStore(), "default")


"""
爬虫任务分发

脚本任务调度粒度:
1.调度表达式
2.调度传入参数
3.执行节点
"""


def work_func(nodes, project, spider, batch_id):
    log_common.warning("project: {}:  spider:{}  batch:{}".format(project, spider, batch_id))
    try:
        lock = dlm.lock("dlm#{}".format(batch_id), 1000 * 30)
        if lock:
            for node in nodes:
                # 这里检查运行节点的活跃健康
                engine = get_engine_by_ip(node)
                args = {
                    "redis": '{{"host":"{}","port": {},"db":{},"password":"{}"}}'.format(db_conf.redis_host,
                                                                                         str(db_conf.redis_port),
                                                                                         str(db_conf.redis_db_name),
                                                                                         db_conf.redis_pwd),
                    "batch_id": batch_id,
                    "node": node
                }
                try:
                    # jobs = engine.schedule(project, spider, **args)
                    jobs = engine_kit.schedule(engine, project, spider, **args)
                    script = CrawlScript.objects.get(name=spider, project_name=project)
                    script.job_id = jobs
                    script.save()
                    log_common.warning("{}:  {}；Jobs：{}".format(project, spider, jobs))
                except Exception as err:
                    log_common.warning("start task", err)
                    log_common.warning("请发布任务到：{}".format(node))
        else:
            log_common.warning("batch:{} locked".format(batch_id))
    except Exception as e:
        log_common.warn(e)
        raise AlertException(Alert.platform_exception, '{} 运行失败\n原因: {}'.format(spider, str(e)))
    finally:
        pass
        # dlm.unlock(lock)


def schedule_fix_data(nodes, project, spider, spider_id, script_args, job_id, fix_type=0):
    """
    调度补数据逻辑
    :return:
    """
    if isinstance(script_args, str):
        script_args = eval(script_args)
    start_date = script_args.get('conditions').get('start_date')
    end_date = script_args.get('conditions').get('end_date')
    date_list = parse_date(start_date, end_date, fix_type)
    # 只考虑第一台主机
    node = nodes[0]
    engine = get_engine_by_ip(node)

    is_first = True
    index = 0
    last_batch_id = ''

    pub = crawl_redis.pubsub()
    while index < len(date_list):
        pub.subscribe(job_id)
        message = pub.parse_response()
        if is_first or (pub and message[2] != 1 and (message[2]).decode('utf-8') == last_batch_id):
            mix = "{}-{}".format(json.dumps(date_list[index]), json.dumps(script_args))
            batch_id = "fix-{}-{}".format(str(spider_id), md5(mix))
            is_first = False
            last_batch_id = batch_id

            day_type = ''
            if fix_type == 1:
                day_type = 'day'
            elif fix_type == 2:
                day_type = 'week'
            elif fix_type == 3:
                day_type = 'month'

            log_common.warning("project: {}:  spider:{}  batch:{}  trigger: {}".format(project, spider, batch_id, json.dumps(date_list[index])))

            condition = {
                'conditions': {
                    'date_type': day_type,
                    'start_date': date_list[index].get('start_date'),
                    'end_date': date_list[index].get('end_date')
                }
            }

            lock = dlm.lock("dlm#{}".format(batch_id), 1000 * 30)
            if lock:
                index = index + 1
                crawl_redis.set("args#{}".format(batch_id), json.dumps(condition))
                args = {
                    "redis": '{{"host":"{}","port": {},"db":{},"password":"{}"}}'.format(db_conf.redis_host,
                                                                                         str(db_conf.redis_port),
                                                                                         str(db_conf.redis_db_name),
                                                                                         db_conf.redis_pwd),
                    "batch_id": batch_id,
                    "node": node,
                    "fix_id": job_id
                }
                jobs = engine.schedule(project, spider, **args)
                script = CrawlScript.objects.get(name=spider, project_name=project)
                script.job_id = jobs
                script.save()
                log_common.warning("补数据任务{}:  {}；Jobs：{}".format(project, spider, jobs))
            else:
                log_common.warning("batch:{} locked".format(batch_id))


def datetime_to_string(datetime):
    return datetime.strftime('%Y-%m-%d')


def parse_date(start_date, end_date, fix_type):
    start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    date_list = []
    one_day = datetime.timedelta(days=1)
    # 按日解析
    if fix_type == 1:
        while start <= end:
            date_dict = {'start_date': datetime_to_string(start),
                         'end_date': datetime_to_string(start)}
            start = start + one_day
            date_list.append(date_dict)
    # 按周解析
    if fix_type == 2:
        seven_day = datetime.timedelta(days=7)
        while start < end:
            date_dict = {'start_date': datetime_to_string(start),
                         'end_date': datetime_to_string(start + seven_day - one_day)}
            start = start + seven_day
            date_list.append(date_dict)
    # 按月解析
    if fix_type == 3:
        while start < end:
            if start.month in (1, 3, 5, 7, 8, 10, 12):
                timedelta = 31
            elif start.month in (4, 6, 9, 11):
                timedelta = 30
            elif (start.year % 4) == 0 and (start.year % 100) != 0 or (start.year % 400) == 0:
                timedelta = 29
            else:
                timedelta = 28
            one_month = datetime.timedelta(days=timedelta)
            date_dict = {'start_date': datetime_to_string(start),
                         'end_date': datetime_to_string(start + one_month - one_day)}
            start = start + one_month
            date_list.append(date_dict)
    return date_list


def md5(md5_char):
    """
    md5算法
    :param md5_char:
    :return:
    """
    hash_md5 = hashlib.md5(md5_char.encode("utf-8"))
    return hash_md5.hexdigest()


class CreateSchedulerWork(threading.Thread):
    def __init__(self, scheduler):
        super(CreateSchedulerWork, self).__init__()
        self.scheduler = scheduler
        self.setDaemon(True)
    
    def run(self):
        while True:
            try:
                # 清理所有任务
                # self.scheduler.remove_all_jobs()
                log_common.warn('*********** 刷新调度器 **********')
                redis_jobs = self.scheduler.get_jobs()
                redis_job_ids = [rj.id for rj in redis_jobs]
                db_job_ids = []

                script_models = CrawlScript.objects.filter(is_deleted=0, is_disable=0)
                for script_model in script_models:
                    node_list = []
                    if not script_model.hosts or script_model.hosts == '[]':
                        project = CrawlProject.objects.get(id=script_model.project_id)
                        task = CrawlTask.objects.get(id=project.task_id)
                        for node_id in json.loads(task.node_ids):
                            node = CrawlNode.objects.get(id=node_id)
                            node_list.append('{}:{}'.format(node.node_ip, node.node_port))
                    else:
                        node_list = eval(script_model.hosts)
                    json_args = []
                    if script_model.args:
                        json_args = eval(script_model.args)
                    for json_arg in json_args:
                        script_args = json_arg["args"]
                        script_triggers = json_arg["trigger"]
                        fix_type = json_arg["fix_type"]

                        try:
                            if script_triggers:
                                # 补数据逻辑
                                if fix_type in (1, 2, 3):
                                    run_date = json_arg['fix_date']
                                    mix = "{}-{}".format(json.dumps(script_triggers), json.dumps(script_args))
                                    job_id = "fix-{}-{}".format(str(script_model.id), md5(mix))
                                    log_common.warn('添加补数据调度任务: {}'.format(script_model.id))
                                    # 立即测试
                                    # schedule_fix_data(node_list, script_model.project_name, script_model.name, script_model.id, script_args, job_id, fix_type)

                                    # 正常逻辑
                                    db_job_ids.append(job_id)
                                    if datetime.datetime.strptime(run_date, '%Y-%m-%d %H:%M:%S') >= datetime.datetime.now() and job_id not in redis_job_ids:
                                        self.scheduler.add_job(schedule_fix_data,
                                                               'date',
                                                               run_date=run_date,
                                                               id=job_id,
                                                               args=[node_list, script_model.project_name,
                                                                     script_model.name, script_model.id,
                                                                     script_args, job_id, fix_type],
                                                               misfire_grace_time=60)
                                else:
                                    # 动态参数
                                    if json_arg.get('dynamic_value'):
                                        sql = json_arg.get('dynamic_value')
                                        result = db_kit.fetch_all_to_json(sql)
                                        for r in result:
                                            script_args['dynamic_value'] = r
                                            log_common.warn('>>>> 动态切割参数调度 {}, args: {}'.format(script_model.name, script_args))
                                            mix = "{}-{}".format(json.dumps(script_triggers), json.dumps(script_args))
                                            job_id = "{}-{}".format(str(script_model.id), md5(mix))
                                            log_common.warn("args#{}".format(job_id))
                                            crawl_redis.set("args#{}".format(job_id), json.dumps(script_args))
                                            # log_common.warn('添加调度任务: {}'.format(script_model.id))
                                            db_job_ids.append(job_id)
                                            if job_id not in redis_job_ids:
                                                self.scheduler.add_job(work_func,
                                                                       trigger="cron",
                                                                       **script_triggers,
                                                                       id=job_id,
                                                                       args=[node_list, script_model.project_name,
                                                                             script_model.name, job_id],
                                                                       misfire_grace_time=60)
                                    else:
                                        mix = "{}-{}".format(json.dumps(script_triggers), json.dumps(script_args))
                                        job_id = "{}-{}".format(str(script_model.id), md5(mix))
                                        crawl_redis.set("args#{}".format(job_id), json.dumps(script_args))
                                        log_common.warn('添加调度任务: {}'.format(script_model.id))
                                        db_job_ids.append(job_id)
                                        if job_id not in redis_job_ids:
                                            self.scheduler.add_job(work_func,
                                                                   trigger="cron",
                                                                   **script_triggers,
                                                                   id=job_id,
                                                                   args=[node_list, script_model.project_name,
                                                                         script_model.name, job_id],
                                                                   misfire_grace_time=60)
                        except Exception as e:
                            log_common.warn(">>>> 添加报错任务报错: ", e)
                            continue

                c_ids = [i for i in redis_job_ids if i not in db_job_ids]
                for c_id in c_ids:
                    self.scheduler.remove_job(c_id)
                    log_common.warn('移除差异任务: {}'.format(c_id))
                db_job_ids.clear()
            except Exception as ex:
                log_common.warn(ex)
                continue
            finally:
                connections.close_all()
                time.sleep(7 * 60)


register_events(scheduler)
scheduler.start()
log_common.warning("scheduler start")
add_work = CreateSchedulerWork(scheduler)
add_work.start()

# register_events(delay_scheduler)
# delay_scheduler.start()



# sct = ScheduleCrawlThread()
# sct.start()

