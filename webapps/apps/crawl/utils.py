import fnmatch
import re
from copy import deepcopy
import subprocess
from subprocess import Popen, PIPE, STDOUT
from os.path import abspath
from shutil import ignore_patterns, copy2, copystat

import requests
from jinja2 import Template
from scrapyd_api import ScrapydAPI
from bs4 import BeautifulSoup
import traceback
import json, os, string
from shutil import move, copy, rmtree
from os.path import join, exists, dirname
from django.forms.models import model_to_dict
from django.utils import timezone

from apps.crawl.models.models import CrawlScript
from server import db_conf
from server.settings import PROJECTS_FOLDER

IGNORES = ['.git/', '*.pyc', '.DS_Store', '.idea/', '*.egg', '*.egg-info/', '*.egg-info', 'build/']

TEMPLATES_DIR = join(dirname(dirname(dirname(abspath(__file__)))), 'templates')

TEMPLATES_TO_RENDER = (
    ('scrapy.cfg',),
    ('${project_name}', 'settings.py.tmpl'),
    ('${project_name}', 'items.py.tmpl'),
    ('${project_name}', 'pipelines.py.tmpl'),
    ('${project_name}', 'middlewares.py.tmpl'),
)

NO_REFERRER = '<meta name="referrer" content="never">'
BASE = '<base href="{href}">'


def get_engine_by_ip(node):
    node_arr = node.split(':')
    check_engine_status(node_arr[0], node_arr[1])
    return ScrapydAPI(engine_url(node_arr[0], node_arr[1]), timeout=30)


def get_general_engine(host, port):
    check_engine_status(host, port)
    return ScrapydAPI(engine_url(host, port), timeout=30)


def get_engine(node):
    if not node.auth:
        check_engine_status(node.node_ip, node.node_port)
        return ScrapydAPI(engine_url(node.node_ip, node.node_port), timeout=30)
    return ScrapydAPI(engine_url(node.node_ip, node.node_port), auth=(node.username, node.password), timeout=30)


def get_simple_engine(node_ip, node_port):
    check_engine_status(node_ip, node_port)
    return ScrapydAPI(engine_url(node_ip, node_port), timeout=30)


def check_engine_status(node_ip, node_port):
    try:
        url = 'http://{}:{}/daemonstatus.json'.format(node_ip, node_port)
        r = requests.get(url)
        if 200 != r.status_code:
            raise Exception('连接节点 {}:{} 失败'.format(node_ip, node_port))
        if 'ok' != r.json().get('status'):
            raise Exception('节点 {}:{} 状态异常'.format(node_ip, node_port))
    except Exception as e:
        raise Exception('连接节点 {}:{} 失败'.format(node_ip, node_port))


def engine_url(ip, port):
    """
    获取engine_url
    :param ip: host
    :param port: port
    :return: string
    """
    url = 'http://{ip}:{port}'.format(ip=ip, port=port)
    return url


def log_url(ip, port, project, spider, job):
    """
    get log url
    :param ip: host
    :param port: port
    :param project: project
    :param spider: spider
    :param job: job
    :return: string
    """
    url = 'http://{ip}:{port}/logs/{project}/{spider}/{job}.log'.format(ip=ip, port=port, project=project,
                                                                        spider=spider, job=job)
    return url


def ignored(ignores, path, file):
    """
    judge if the file is ignored
    :param ignores: ignored list
    :param path: file path
    :param file: file name
    :return: bool
    """
    file_name = join(path, file)
    for ignore in ignores:
        if '/' in ignore and ignore.rstrip('/') in file_name:
            return True
        if fnmatch.fnmatch(file_name, ignore):
            return True
        if file == ignore:
            return True
    return False


def is_valid_name(project_name):
    """
    judge name is valid
    :param project_name:
    :return:
    """
    if not re.search(r'^[_a-zA-Z]\w*$', project_name):
        print('Error: Project Name must begin with a letter and contain only letters, numbers and underscores')
        return False
    return True


def copy_tree(src, dst):
    """
    copy tree
    :param src:
    :param dst:
    :return:
    """
    ignore = ignore_patterns(*IGNORES)
    names = os.listdir(src)
    ignored_names = ignore(src, names)
    if not os.path.exists(dst):
        os.makedirs(dst)
    
    for name in names:
        if name in ignored_names:
            continue
        
        src_name = os.path.join(src, name)
        dst_name = os.path.join(dst, name)
        if os.path.isdir(src_name):
            copy_tree(src_name, dst_name)
        else:
            copy2(src_name, dst_name)
    copystat(src, dst)


def get_tree(path, ignores=IGNORES):
    """
    获取目录树结构
    :param path: Folder path
    :param ignores: Ignore files
    :return: Json
    """
    result = []
    for file in os.listdir(path):
        if os.path.isdir(join(path, file)):
            if not ignored(ignores, path, file):
                children = get_tree(join(path, file), ignores)
                if children:
                    result.append({
                        'label': file,
                        'children': children,
                        'path': path
                    })
        else:
            if not ignored(ignores, path, file):
                result.append({'label': file, 'path': path})
    return result


def render_template(tpl_file, dst_file, *args, **kwargs):
    """
    render template
    :param tpl_file: Template file name
    :param dst_file: Destination file name
    :param args: args
    :param kwargs: kwargs
    :return: None
    """
    vars = dict(*args, **kwargs)
    template = Template(open(tpl_file, encoding='utf-8').read())
    os.remove(tpl_file)
    result = template.render(vars)
    open(dst_file, 'w', encoding='utf-8').write(result)


def get_traceback():
    """
    get last line of error
    :return: String
    """
    info = traceback.format_exc(limit=1)
    if info:
        info = info.splitlines()
        info = list(filter(lambda x: x, info))
        if len(info):
            return info[-1]
        return None
    return info


def process_request(request):
    """
    process request
    :param request:
    :return:
    """
    return {
        'url': request.url,
        'method': request.method,
        'meta': request.meta,
        'headers': request.headers,
        'callback': request.callback
    }


def process_response(response):
    """
    process response to dict
    :param response:
    :return:
    """
    return {
        'html': response.text,
        'url': response.url,
        'status': response.status
    }


def process_item(item):
    return dict(item)


def process_html(html, base_url):
    """
    process html, add some tricks such as no referrer
    :param html: source html
    :return: processed html
    """
    dom = BeautifulSoup(html, 'lxml')
    dom.find('head').insert(0, BeautifulSoup(NO_REFERRER, 'lxml'))
    dom.find('head').insert(0, BeautifulSoup(BASE.format(href=base_url), 'lxml'))
    html = str(dom)
    # html = unescape(html)
    return html


def get_output_error(project_name, spider_name):
    """
    get scrapy runtime error
    :param project_name: project name
    :param spider_name: spider name
    :return: output, error
    """
    work_cwd = os.getcwd()
    project_base_path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
    project_path = join(project_base_path, project_name)
    try:
        os.chdir(project_path)
        if not os.path.exists("debug_folder"):
            os.makedirs("debug_folder")
            os.makedirs(join("debug_folder", "logs"))
            os.makedirs(join("debug_folder", "items"))
        redis_cfg = '{{"host": "{}", "port": {}, "db": 1, "password": "{}"}}'.\
            format(db_conf.redis_host, db_conf.redis_port, db_conf.redis_pwd)
        # 判断是否设置过运行参数，不是所有的爬虫脚本都要设置运行参数
        crawl_script = CrawlScript.objects.get(name=spider_name, is_deleted=0)
        args = ""
        if crawl_script and crawl_script.args:
            args = eval(CrawlScript.objects.get(name=spider_name, is_deleted=0).args)[0]
            if args:
                args = args['args']
        cmd = ' '.join(['scrapy', 'crawl', spider_name,
                        "-s LOG_FILE=./debug_folder/logs/{}.log".format(spider_name),
                        "-o ./debug_folder/items/{}.json".format(spider_name),
                        "-a redis='{}'".format(redis_cfg),
                        "-a args='{}'".format(args)])

        p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        output = p.stdout.read()
        if isinstance(output, bytes):
            output = output.decode('utf-8')
        return output
    finally:
        os.chdir(work_cwd)


def get_items_configuration(configuration):
    """
    get items configuration including allowed_spiders and tables or collections
    :param configuration: configuration data
    :return: items
    """
    configuration = deepcopy(configuration)
    items = configuration.get('items')
    spiders = configuration.get('spiders')
    for spider in spiders:
        # MongoDB
        mongodb_collection_map = spider.get('storage').get('mongodb').get('collections')
        for mongodb_collection_map_item in mongodb_collection_map:
            collection = mongodb_collection_map_item.get('collection')
            item_name = mongodb_collection_map_item.get('item')
            for item in items:
                if item.get('name') == item_name:
                    allowed_spiders = item.get('mongodb_spiders', set())
                    allowed_spiders.add(spider.get('name'))
                    mongodb_collections = item.get('mongodb_collections', set())
                    mongodb_collections.add(collection)
                    item['mongodb_spiders'], item['mongodb_collections'] = allowed_spiders, mongodb_collections
        
        # MySQL
        mysql_table_map = spider.get('storage').get('mysql').get('tables')
        for mysql_table_map_item in mysql_table_map:
            collection = mysql_table_map_item.get('table')
            item_name = mysql_table_map_item.get('item')
            for item in items:
                if item.get('name') == item_name:
                    allowed_spiders = item.get('mysql_spiders', set())
                    allowed_spiders.add(spider.get('name'))
                    mysql_tables = item.get('mysql_tables', set())
                    mysql_tables.add(collection)
                    item['mysql_spiders'], item['mysql_tables'] = allowed_spiders, mysql_tables
    # transfer attr
    attrs = ['mongodb_spiders', 'mongodb_collections', 'mysql_spiders', 'mysql_tables']
    for item in items:
        for attr in attrs:
            if item.get(attr):
                item[attr] = list(item[attr])
    return items


def generate_project(project_name):
    """
    根据配置创建工程模板代码也可以创建通用的工程代码
    :param project_name: project name
    :return: project data
    """
    work_path = os.getcwd()
    project_dir = join(os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER)), project_name)

    copy_tree(join(TEMPLATES_DIR, 'project'), project_dir)
    move(join(PROJECTS_FOLDER, project_name, 'module'), join(project_dir, project_name))
    for paths in TEMPLATES_TO_RENDER:
        path = join(*paths)
        tpl_file = join(project_dir, string.Template(path).substitute(project_name=project_name))
        vars = {
            'project_name': project_name,
        }
        render_template(tpl_file, tpl_file.rstrip('.tmpl'), **vars)
    source_tpl_file = join(TEMPLATES_DIR, 'spiders', 'basic.tmpl')
    new_tpl_file = join(PROJECTS_FOLDER, project_name, project_name, 'spiders', 'basic.tmpl')
    spider_file = "%s.py" % join(PROJECTS_FOLDER, project_name, project_name, 'spiders', "demo")
    copy(source_tpl_file, new_tpl_file)
    render_template(new_tpl_file, spider_file, spider="demo", project_name=project_name)
    os.chdir(work_path)


def bytes2str(data):
    """
    bytes2str
    :param data: origin data
    :return: str
    """
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    data = data.strip()
    return data
