from django.conf.urls import url
from apps.crawl.views import project_views

urlpatterns = [

    url(r'^index', project_views.project_index, name='project_index'),
    url(r'^create', project_views.project_create, name='project_create'),

    url(r'^(\S+)/tree', project_views.project_tree, name='project_tree'),
    url(r'^(\S+)/remove', project_views.project_remove, name='project_remove'),

    url(r'^file/rename', project_views.project_file_rename, name='project_file_rename'),
    url(r'^file/delete', project_views.project_file_delete, name='project_file_delete'),
    url(r'^file/create', project_views.project_file_create, name='project_file_create'),
    url(r'^file/update', project_views.project_file_update, name='project_file_update'),
    url(r'^file/read', project_views.project_file_read, name='project_file_read'),

    url(r'^(\S+)/build', project_views.project_build, name='project_build'),

    url(r'^(\S+)/task_deploy', project_views.task_deploy, name='task_deploy'),

]
