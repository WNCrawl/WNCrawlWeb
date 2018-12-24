# coding=utf-8
"""
本loader主要为爬虫脚本做数据加载
"""
from apps.crawl.models.models import CrawlProxyIP, CrawlScript, CrawlProject, CrawlTask, CrawlNode
from server.db_conf import *
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from server.logging_conf import log_common

db_time_format = "%Y-%m-%d %H:%M:%S"

executors = {
    'default': ThreadPoolExecutor(2)
}
scheduler = BackgroundScheduler(executors=executors)
scheduler.add_jobstore(MemoryJobStore(), "default")
scheduler.start()

# 加载前端爬虫店铺数据


def load_cfg_data():
    pass


def time_task():
    log_common.warn("加载爬虫脚本数据~~~~")
    load_cfg_data()
    load_auto()


def load_auto():
    script_list = CrawlScript.objects.filter(project_name='auto_login', is_deleted=0)
    for script in script_list:
        if not script.hosts or script.hosts == '[]':
            project = CrawlProject.objects.get(id=script.project_id)
            task = CrawlTask.objects.get(id=project.task_id)
            if task.node_ids:
                node_id = json.loads(task.node_ids)[0]
                node = CrawlNode.objects.get(id=node_id)
                crawl_redis.set('auto#spider#{}'.format(script.name), json.dumps({'ip': node.node_ip,
                                                                                  'port': node.node_port}))
        else:
            node = eval(script.hosts)[0].split(':')
            crawl_redis.set('auto#spider#{}'.format(script.name), json.dumps({'ip': node[0], 'port': node[1]}))


cron = {
    "minute": "*/5",
}
load_cfg_data()
load_auto()
scheduler.add_job(time_task, "cron", **cron)
register_events(scheduler)
