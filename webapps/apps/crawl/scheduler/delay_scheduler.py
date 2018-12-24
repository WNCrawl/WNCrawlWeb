import json
import threading
import time

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from apps.crawl.utils import get_general_engine
from server.common import engine_kit
from server.db_conf import crawl_redis, redis_host, redis_port, redis_pwd, redis_db_name
from server.logging_conf import log_common
from django_apscheduler.jobstores import register_events

redis_args = {
    'host': redis_host,
    'port': redis_port,
    'db': redis_db_name,
    'password': redis_pwd
}
executors = {
    'default': ThreadPoolExecutor(5)
}

redis_job_store = RedisJobStore(jobs_key='delay_apscheduler.jobs', run_times_key='delay_apscheduler.run_times', **redis_args)
scheduler = BackgroundScheduler(executors=executors)
scheduler.add_jobstore(redis_job_store, "default")


class DelayTaskSchedulerWork(threading.Thread):
    def __init__(self, scheduler):
        super(DelayTaskSchedulerWork, self).__init__()
        self.scheduler = scheduler
        self.setDaemon(True)

    def run(self):
        while True:
            try:
                while crawl_redis.llen('crawl_delay_queue') > 0:
                    log_common.info('当前延迟处理队列中存在{}个待执行延迟任务'.format(str(crawl_redis.llen('crawl_delay_queue'))))
                    arg = crawl_redis.blpop('crawl_delay_queue', timeout=3)
                    if arg:
                        run_arg = json.loads(arg[1])
                        project = run_arg.get('project')
                        spider = run_arg.get('spider')
                        host = run_arg.get('host')
                        port = run_arg.get('port')
                        args = run_arg.get('args')

                        engine = get_general_engine(host, port)
                        engine_kit.schedule(engine, project, spider, **args)
                    time.sleep(3)
            except Exception as e:
                log_common.error('>>>> [DelayTaskSchedulerWork] 调度出现异常', e)
            finally:
                time.sleep(7 * 60)


register_events(scheduler)
scheduler.start()
delay_work = DelayTaskSchedulerWork(scheduler)
delay_work.start()
