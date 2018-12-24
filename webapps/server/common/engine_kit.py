import json
import time

from apps.crawl.models.models import CrawlTask
from server.db_conf import crawl_redis
from server.logging_conf import log_common


def schedule(engine, project, spider, **args):
    time.sleep(3)
    running_task = len(engine.list_jobs(project).get('running'))
    pending_task = len(engine.list_jobs(project).get('pending'))
    current_count = running_task + pending_task
    task = CrawlTask.objects.get(project_name=project, is_deleted=0)
    max_count = 5 if not task.spider_concurrency else task.spider_concurrency
    jobs = ''
    if current_count > int(max_count):
        # 写进延迟运行队列
        host_arr = get_host_by_engine(engine)
        arg = {
            'project': project,
            'spider': spider,
            'args': args,
            'host': host_arr[0],
            'port': host_arr[1]
        }
        log_common.warn('添加到延迟队列=> project: {}, spider: {}, host: {}, port: {}'.format(project, spider,
                                                                                       host_arr[0], host_arr[1]))
        crawl_redis.rpush('crawl_delay_queue', json.dumps(arg))
    else:
        jobs = engine.schedule(project, spider, **args)
    return jobs


def get_host_by_engine(engine):
    host_info = engine.target.replace('https://', '').replace('http://', '')
    host_arr = host_info.split(':')
    if len(host_arr) == 2:
        return host_arr[0], host_arr[1]
    else:
        raise Exception('IP解析失败')
