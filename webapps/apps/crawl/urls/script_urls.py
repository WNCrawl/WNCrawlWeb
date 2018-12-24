from django.conf.urls import url
from apps.crawl.views import script_views

urlpatterns = [

    url(r'^(\d+)/project/(\S+)/spiders', script_views.spider_list, name='spider_list'),
    url(r'^node_spiders', script_views.node_spider_list, name='node_spiders'),
    url(r'^list_scripts', script_views.list_scripts, name='list_scripts'),
    url(r'^edit_script_cfg', script_views.edit_script_cfg, name='edit_script_cfg'),
    url(r'^debug_script', script_views.debug_script, name='debug_script'),
    url(r'^find_debug_result', script_views.find_debug_result, name='find_debug_result'),
    url(r'^find_debug_log', script_views.find_debug_log, name='find_debug_log'),
    url(r'^format_debug_result', script_views.format_debug_result, name='format_debug_result'),

    url(r'(\d+)/task', script_views.task_by_script_id, name='task_by_script_id'),

    url(r'^list_task_progress', script_views.list_task_progress, name='list_task_progress'),
    url(r'^collect_script_progress', script_views.collect_script_progress, name='collect_script_progress'),

    url(r'^start', script_views.script_start, name='script_start'),
    url(r'^stop', script_views.job_cancel_all, name='script_stop'),

    url(r'^get_host', script_views.get_hosts, name='get_hosts'),
    url(r'^log', script_views.script_newest_log, name='script_newest_log'),
    url(r'^disable', script_views.script_disable, name='script_disable'),
    url(r'^enable', script_views.script_enable, name='script_enable'),

    url(r'^remove', script_views.script_remove, name='script_remove'),

    url(r'^img_parser', script_views.img_parser, name='img_parser')
]
