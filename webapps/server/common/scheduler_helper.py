import uuid

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

executors = {
    'default': ThreadPoolExecutor(20)
}
scheduler = BackgroundScheduler(executors=executors)
scheduler.add_jobstore(DjangoJobStore(), "default")


def verify_cron(expression):
    try:
        task_id = str(uuid.uuid1())
        scheduler.add_job(test_params,
                          trigger='cron',
                          **expression,
                          id=task_id)
        scheduler.remove_job(task_id)
        return True, None
    except Exception as e:
        return False, e


def test_params():
    pass
