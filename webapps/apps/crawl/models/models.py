# coding=utf-8

from django.db.models import Model, CharField, GenericIPAddressField, IntegerField, TextField, DateTimeField, \
    ManyToManyField, ForeignKey, DO_NOTHING, BooleanField, AutoField


class CrawlNode(Model):
    """
    爬虫节点 （与DtCrawlEngine对应）
    """
    class Meta:
        db_table = 'crawl_node'

    id = IntegerField(auto_created=True, primary_key=True)
    node_name = CharField(max_length=255, default=None)
    node_ip = CharField(max_length=255, blank=True, null=True)
    node_port = IntegerField(default=6800, blank=True, null=True)
    node_description = TextField(blank=True, null=True)
    auth = IntegerField(default=0, blank=True, null=True)
    username = CharField(max_length=255, blank=True, null=True)
    password = CharField(max_length=255, blank=True, null=True)
    is_deleted = IntegerField(default=0)
    node_type = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)


class CrawlProject(Model):
    """
    爬虫工程
    """

    class Meta:
        db_table = 'crawl_project'

    id = AutoField(auto_created=True, primary_key=True)
    name = CharField(max_length=255, default=None)
    description = CharField(max_length=255, null=True, blank=True)
    egg = CharField(max_length=255, null=True, blank=True)
    configuration = TextField(blank=True, null=True)
    configurable = IntegerField(default=0, blank=True)
    task_id = IntegerField(default=0, blank=True)
    built_at = DateTimeField(default=None, blank=True, null=True)
    generated_at = DateTimeField(default=None, blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
    is_deleted = IntegerField(default=0)


class CrawlScript(Model):
    """
    爬虫脚本
    +------------+------------------+------+-----+---------+----------------+
    | Field      | Type             | Null | Key | Default | Extra          |
    +------------+------------------+------+-----+---------+----------------+
    | id         | int(11) unsigned | NO   | PRI | NULL    | auto_increment |
    | created_at | datetime         | YES  |     | NULL    |                |
    | updated_at | datetime         | YES  |     | NULL    |                |
    | is_deleted | int(1)           | YES  |     | NULL    |                |
    | trigger    | varchar(255)     | YES  |     | NULL    |                |
    | name       | varchar(255)     | YES  |     | NULL    |                |
    | args       | varchar(255)     | YES  |     | NULL    |                |
    | desc       | varchar(255)     | YES  |     | NULL    |                |
    | project_id | int(11)          | YES  |     | NULL    |                |
    | type       | int(11)          | YES  |     | NULL    |                |
    +------------+------------------+------+-----+---------+----------------+
    """

    class Meta:
        db_table = 'crawl_script'

    id = IntegerField(auto_created=True, primary_key=True)
    name = CharField(max_length=255, default=None)
    desc = CharField(max_length=255, null=True, blank=True)
    trigger = CharField(max_length=255, null=True, blank=True)
    hosts = CharField(max_length=255, null=True, blank=True)
    args = TextField(blank=True, null=True)
    use_proxy = IntegerField(default=0)
    type = IntegerField(default=0, blank=True)
    project_id = IntegerField(default=0, blank=True)
    task_id = IntegerField(default=0, blank=True)
    task_name = CharField(max_length=255, null=True, blank=True)
    script_file = CharField(max_length=100, null=True, blank=True)
    project_name = CharField(max_length=255, null=True, blank=True)
    job_id = CharField(max_length=255, null=True, blank=True)
    path = CharField(max_length=2048, null=True, blank=True)
    is_disable = IntegerField(default=0)
    is_deleted = IntegerField(default=0)
    updated_at = DateTimeField(default=None, blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)


class CrawlDeploy(Model):
    """
    爬虫发布记录（爬虫脚本）
    """
    class Meta:
        db_table = 'crawl_deploy'

    id = IntegerField(auto_created=True, primary_key=True)
    node_id = IntegerField(default=0)
    project_id = IntegerField(default=0)
    project_name = CharField(max_length=255, blank=True, null=True)
    description = CharField(max_length=255, blank=True, null=True)
    deployed_at = DateTimeField(default=None, blank=True, null=True)
    is_deleted = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)


class Monitor(Model):
    name = CharField(max_length=255, default=None)
    description = CharField(max_length=255, null=True, blank=True)
    type = CharField(max_length=255, null=True, blank=True)
    configuration = TextField(null=True, blank=True)
    project = ForeignKey(CrawlProject, blank=True, null=True, on_delete=DO_NOTHING)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)


class CrawlTask(Model):
    """
    任务表
    """

    class Meta:
        db_table = 'crawl_task'

    id = AutoField(auto_created=True, primary_key=True)
    task_name = CharField(max_length=255, null=True, blank=True)
    project_name = CharField(max_length=255, null=True, blank=True)
    platform_name = CharField(max_length=255, null=True, blank=True)
    description = CharField(max_length=255, null=True, blank=True)
    project_id = IntegerField(default=0)
    platform_id = CharField(max_length=255, null=True, blank=True)
    task_type = IntegerField(default=0)
    is_deploy = IntegerField(default=0)
    is_deleted = IntegerField(default=0)
    spider_concurrency = CharField(max_length=2048, null=True, blank=True)
    node_ids = CharField(max_length=255, null=True, blank=True)
    status = IntegerField(default=0)
    creator_id = IntegerField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True, editable=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)


class CrawlTaskInstance(Model):

    class Meta:
        db_table = 'crawl_task_instance'

    clients = TextField(null=True, blank=True)
    project = CharField(max_length=255, null=True, blank=True)
    spider = CharField(max_length=255, null=True, blank=True)
    name = CharField(max_length=255, null=True, blank=True)
    args = TextField(null=True, blank=True)
    description = TextField(null=True, blank=True)
    is_deleted = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)


class CrawlProxyIP(Model):

    class Meta:
        db_table = 'crawl_proxy_ip'
    id = AutoField(auto_created=True, primary_key=True)
    source = CharField(max_length=255, null=True, blank=True)
    ip = CharField(max_length=255, null=True, blank=True)
    port = CharField(max_length=255, null=True, blank=True)
    # 1 短效 2长效
    ip_type = IntegerField(default=0)
    # 0 未使用 1 使用中 2已停用
    status = IntegerField(default=0)
    last_at = DateTimeField(blank=True, null=True)
    is_deleted = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)


class CrawlScriptProgress(Model):
    """
    任务脚本执行数据
    """
    class Meta:
        db_table = 'crawl_script_progress'
    id = AutoField(auto_created=True, primary_key=True)
    batch = CharField(max_length=255, null=True, blank=True, unique=True)
    task_name = CharField(max_length=255, null=True, blank=True)
    script_name = CharField(max_length=255, null=True, blank=True)
    status = IntegerField(default=0)
    start_time = CharField(max_length=255, null=True, blank=True)
    end_time = CharField(max_length=255, null=True, blank=True)
    run_time = IntegerField(default=0)
    get_cnt = IntegerField(default=0)
    request_cnt = IntegerField(default=0)
    oss_url = CharField(max_length=255, null=True, blank=True)
    msg = CharField(max_length=255, null=True, blank=True)
    node = CharField(max_length=255, null=True, blank=True)
    arg = CharField(max_length=255, null=True, blank=True)
    arg_key = CharField(max_length=255, null=True, blank=True)
    is_deleted = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
