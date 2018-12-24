import sys
import os
import glob
import tempfile
import shutil
from server.settings import PROJECTS_FOLDER
from apps.crawl.config import config
from os.path import join
from subprocess import check_call
from scrapy.utils.python import retry_on_eintr
from server.logging_conf import log_common


def build_project(project, include_data=False):
    egg = build_egg(project, include_data=include_data)
    return egg


_SETUP_PY_DATA_TEMPLATE = \
    """# Automatically created by: WNCrawlAdmin
from setuptools import setup, find_packages
setup(
    name='%(project)s',
    version='1.0',
    packages=find_packages(),
    data_files=[('', ['chromedriver']), ],
    entry_points={'scrapy':['settings=%(settings)s']},
)"""


_SETUP_PY_TEMPLATE = \
    """# Automatically created by: DtCrawlAdmin
from setuptools import setup, find_packages
setup(
    name='%(project)s',
    version='1.0',
    packages=find_packages(),
    entry_points={'scrapy':['settings=%(settings)s']},
)"""


def build_egg(project, include_data=False):
    """
    构建egg包
    :param project:
    :param include_data
    :return:
    """
    work_path = os.getcwd()
    try:
        path = os.path.abspath(join(os.getcwd(), PROJECTS_FOLDER))
        project_path = join(path, project)
        os.chdir(project_path)
        settings = config(project_path, 'settings', 'default')
        if include_data:
            create_data_setup_py(project_path, settings=settings, project=project)
        else:
            create_default_setup_py(project_path, settings=settings, project=project)

        d = tempfile.mkdtemp(prefix="dt-")
        o = open(os.path.join(d, "stdout"), "wb")
        e = open(os.path.join(d, "stderr"), "wb")
        retry_on_eintr(check_call, ['python', 'setup.py', 'clean', '-a', 'bdist_egg', '-d', d],
                       stdout=o, stderr=e)

        # retry_on_eintr(check_call, [sys.executable, 'setup.py', 'clean', '-a', 'bdist_egg', '-d', d],
        #                stdout=o, stderr=e)

        o.close()
        e.close()
        egg = glob.glob(os.path.join(d, '*.egg'))[0]
        # Delete Origin file
        if find_egg(project_path):
            os.remove(join(project_path, find_egg(project_path)))
        shutil.move(egg, project_path)
        return join(project_path, find_egg(project_path))
    except Exception as e:
        import traceback
        log_common.error(">build_egg ", e)
        log_common.error(">build_egg  = {}", traceback.format_exc())
    finally:
        os.chdir(work_path)


def find_egg(path):
    items = os.listdir(path)
    for name in items:
        if name.endswith(".egg"):
            return name
    return None


def create_default_setup_py(path, **kwargs):
    with open(join(path, 'setup.py'), 'w', encoding='utf-8') as f:
        file = _SETUP_PY_TEMPLATE % kwargs
        f.write(file)
        f.close()


def create_data_setup_py(path, **kwargs):
    """
    hook 对于需要打包文件，可以扩展此方法
    :param path:
    :param kwargs:
    :return:
    """
    with open(join(path, 'setup.py'), 'w', encoding='utf-8') as f:
        file = _SETUP_PY_DATA_TEMPLATE % kwargs
        f.write(file)
        f.close()
