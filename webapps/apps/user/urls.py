# coding=utf-8
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^(\d+)/edit_user', views.edit_user, name='edit_user'),
    url(r'^(\d+)/reset_pwd', views.reset_pwd, name='reset_pwd'),
    url(r'^(\d+)/remove_user', views.remove_user, name='remove_user'),
    url(r'^query_users', views.query_users, name='query_users'),
    url(r'^(\d+)/get_user', views.get_user, name='get_user'),

    url(r'^list_role', views.list_role, name='list_role'),
    url(r'^(\d+)/edit_role', views.edit_role, name='edit_role'),
    url(r'^create_role', views.create_role, name='create_role'),
    url(r'^(\d+)/query_role', views.query_role, name='query_role'),
    url(r'^query_permissions', views.query_permissions, name='query_permissions'),

    url(r'^login', views.login, name='login'),
    url(r'^create_user', views.create_user, name='create_user'),
    url(r'^(\d+)/get_profile', views.get_profile, name='get_profile'),
    url(r'^(\d+)/edit_profile', views.edit_profile, name='edit_profile'),
    url(r'^(\d+)/reset_profile_pwd', views.reset_profile_pwd, name='reset_profile_pwd'),

    url(r'^fetch_user_permissions', views.fetch_user_permissions, name='fetch_user_permissions'),

]
