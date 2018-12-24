# coding=utf-8
from django.conf.urls import url
from apps.crawl.views import node_views

urlpatterns = [

    url(r'^status$', node_views.index_status, name='index_status'),
    url(r'^index_node', node_views.node_index, name='node_index'),
    url(r'^create_node', node_views.node_create, name='node_create'),
    url(r'^(\d+)/$', node_views.node_info, name='node_info'),
    url(r'^(\d+)/status', node_views.node_status, name='node_status'),
    url(r'^(\d+)/update', node_views.node_update, name='node_update'),
    url(r'^(\d+)/remove', node_views.node_remove, name='node_remove'),
    url(r'^(\d+)/projects', node_views.project_list, name='project_list'),
    url(r'^node_manager', node_views.node_manager, name='node_manager'),
    url(r'^node_spider_info', node_views.node_spider_info, name='node_spider_info')

]
