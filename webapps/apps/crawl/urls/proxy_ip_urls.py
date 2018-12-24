from django.conf.urls import url
from apps.crawl.views import proxy_ip_views

urlpatterns = [
    url(r'^list_proxy_ip', proxy_ip_views.list_proxy_ip, name='list_proxy_ip'),
    url(r'^(\d+)/get_proxy_ip', proxy_ip_views.get_proxy_ip, name='get_proxy_ip'),
    url(r'^create_proxy_ip', proxy_ip_views.create_proxy_ip, name='create_proxy_ip'),
    url(r'^(\d+)/update_proxy_ip', proxy_ip_views.update_proxy_ip, name='update_proxy_ip'),
    url(r'^(\d+)/remove_proxy_ip', proxy_ip_views.remove_proxy_ip, name='remove_proxy_ip'),
]
