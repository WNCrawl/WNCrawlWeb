# coding=utf-8
from django.conf.urls import url
from . import views
from apps.sync.scheduler import scheduler

urlpatterns = [

    # 数据同步 / 任务管理
    url(r'^list_task', views.sync_task_list, name='sync_task_list'),
    url(r'^create_task', views.sync_task_create, name='sync_task_create'),
    url(r'^(\d+)/update_task', views.sync_task_update, name='sync_task_update'),
    url(r'^remove_task/(\d+)', views.sync_task_delete, name='sync_task_delete'),
    url(r'^get_task/(\d+)', views.sync_task_find, name='sync_task_find'),
    url(r'^deploy', views.sync_task_deploy, name='sync_task_deploy'),

    # 数据同步 / 周期实例
    url(r'^list_instance', views.sync_instance_list, name='sync_instance_list'),
    url(r'^remove_instance', views.sync_instance_delete, name='sync_instance_list'),
    url(r'^create_instance', views.sync_instance_create, name='sync_instance_create'),
    url(r'^rerun_instance', views.sync_instance_rerun, name='sync_instance_rerun'),

    # 数据同步 / 补数据实例
    url(r'^list_data_instance', views.sync_data_instance_list, name='sync_data_instance_list'),
    url(r'^detail_data_instance/(\d+)', views.sync_data_instance_detail, name='sync_data_instance_detail'),
    url(r'^remove_data', views.sync_data_delete, name='sync_data_delete'),
    url(r'^(\d+)/kill_all_data', views.sync_data_kill_all, name='sync_data_kill_all'),
    url(r'^rerun_data', views.sync_data_rerun, name='sync_data_rerun'),
    url(r'^create_data', views.sync_data_create, name='sync_data_create'),

    url(r'^start', views.script_start, name='script_start'),
    url(r'^log', views.newest_log, name='newest_log'),
]
