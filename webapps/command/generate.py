import os


def generate(project):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapps.server.server.settings')
    # os.environ.setdefault('RUN_MAIN', 'true')
    import django
    django.setup()
    from webapps.apps.crawl.utils import generate_project
    generate_project(project)
