from django.conf.urls import url
from apps.crawl.views import task_views
# from apps.crawl.scheduler import scheduler, delay_scheduler

urlpatterns = [

    url(r'^task_index', task_views.task_index, name='task_index'),
    url(r'^create_task', task_views.task_create, name='task_create'),
    url(r'^(\d+)/update', task_views.task_update, name='task_update'),
    url(r'^(\d+)/info', task_views.task_info, name='task_info'),
    url(r'^(\d+)/remove', task_views.task_remove, name='task_remove'),
]
