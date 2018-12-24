#!/usr/bin/env python
# encoding: utf-8

import time
import json
import logging
import threading
import hashlib
import os

from django.db import connections
from django.forms.models import model_to_dict
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from server.db_conf import crawl_redis, redis_host, redis_port, redis_pwd, redis_db_name, dlm
from apps.crawl.utils import get_engine_by_ip
from apps.sync.models import CrawlSyncTask
from server import db_conf
from server.logging_conf import log_common

logger = logging.getLogger(__name__)

db_time_format = "%Y-%m-%d %H:%M:%S"

executors = {
    'default': ThreadPoolExecutor(5)
}

redis_args = {
    'host': redis_host,
    'port': redis_port,
    'db': redis_db_name,
    'password': redis_pwd
}

redis_job_store = RedisJobStore(jobs_key='sync_apscheduler.jobs', run_times_key='sync_apscheduler.run_times', **redis_args)
scheduler = BackgroundScheduler(executors=executors)
scheduler.add_jobstore(redis_job_store, "default")

"""
erp数据同步任务分发

脚本任务调度粒度:
1.调度表达式
2.调度传入参数
3.执行节点
"""


def work_func(nodes, project, spider, md5_job, task_id):
    log_common.warn("当前同步任务执行节点:{}".format(json.dumps(nodes)))

    # apscheduler bug fix

    try:
        lock = dlm.lock("dlm#{}".format(md5_job), 1000*30)
        if lock:
            for node in nodes:
                # 这里检查运行节点的活跃健康
                engine = get_engine_by_ip(node)
                try:
                    args = {
                        "redis": '{{"host":"{}","port": {},"db":1,"password":"{}"}}'.format(db_conf.redis_host,
                                                                                            str(db_conf.redis_port),
                                                                                            db_conf.redis_pwd),
                        "batch_id": md5_job,
                        "task_id": task_id
                    }
                    jobs = engine.schedule(project, spider, **args)
                    task = CrawlSyncTask.objects.get(id=task_id)
                    task.job_id = jobs
                    task.save()
                    log_common.warning("{} ,{}:  {}；Jobs：{}".format(str(task_id), project, spider, jobs))
                except Exception as err:
                    import traceback
                    log_common.error("请发布任务到", err)
                    log_common.error("发布分发任务失败:{}".format(traceback.format_exc()))
        else:
            log_common.warning("batch:{} locked".format(md5_job))
    finally:
        pass


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
                # 新添加待调度的任务
                self.scheduler.remove_all_jobs()
                sync_task_models = CrawlSyncTask.objects.filter(is_deleted=0)
                if not sync_task_models:
                    log_common.warn('任务获取失败')
                    continue
                for sync_model in sync_task_models:
                    node_ports = eval(sync_model.execute_host)
                    if not sync_model.source_cfg:
                        continue
                    source_cfg = eval(sync_model.source_cfg)
                    target_cfg = eval(sync_model.target_cfg)

                    args = {
                        "conditions": source_cfg["source_condition"],
                        "path": target_cfg["target_path"],
                    }
                    trigger = sync_model.schedule_date
                    mix = "{}-{}-{}".format(trigger, sync_model.source_cfg, sync_model.target_cfg)
                    job_id = "{}-{}".format(str(sync_model.id), mix)
                    md5_job = md5(job_id)
                    crawl_redis.set("sync#cfg#{}".format(md5_job), json.dumps(args))
                    self.scheduler.add_job(work_func,
                                           trigger="cron",
                                           **eval(trigger),
                                           id=md5_job,
                                           args=[node_ports, "pro_sync_erp",
                                                 "erp_sync", md5_job, sync_model.id])
            except Exception as ex:
                import traceback
                log_common.error("调度数据同步任务失败", ex)
                log_common.error("调度数据同步任务失败 = {}".format(traceback.format_exc()))
            finally:
                connections.close_all()
                time.sleep(3 * 60)


register_events(scheduler)
# scheduler.start()
log_common.warn("同步数据任务加载")
add_work = CreateSchedulerWork(scheduler)
add_work.start()
