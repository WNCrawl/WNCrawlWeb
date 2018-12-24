# -*- coding: utf-8 -*-

from django.conf.urls import url, include
from django.contrib import admin
from server.loader_conf import *

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/user/', include('apps.user.urls')),
    url(r'^api/sync/', include('apps.sync.urls')),
    url(r'^api/crawl/ip/', include('apps.crawl.urls.proxy_ip_urls')),

    url(r'^api/node/', include('apps.crawl.urls.node_urls')),
    url(r'^api/project/', include('apps.crawl.urls.project_urls')),
    url(r'^api/script/', include('apps.crawl.urls.script_urls')),
    url(r'^api/task/', include('apps.crawl.urls.task_urls')),
    url(r'^api/user/', include('apps.user.urls')),
]
