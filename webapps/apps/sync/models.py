# Create your models here.
from django.db.models import Model, CharField, GenericIPAddressField, IntegerField, TextField, DateTimeField, \
    ManyToManyField, ForeignKey, DO_NOTHING, BooleanField, AutoField
import datetime


class CrawlSyncTask(Model):
    class Meta:
        db_table = 'crawl_sync_cfg'

    id = AutoField(auto_created=True, primary_key=True)
    task_name = CharField(max_length=255, null=True, blank=True)
    task_desc = CharField(max_length=255, null=True, blank=True)
    execute_host = CharField(max_length=255, null=True, blank=True)
    source_cfg = CharField(max_length=1024, null=True, blank=True)
    target_cfg = CharField(max_length=255, null=True, blank=True)
    effect_date = DateTimeField(null=True, blank=True)
    schedule_cycle = IntegerField(blank=True)
    schedule_date = CharField(max_length=255, null=True, blank=True)
    job_id = CharField(max_length=255, null=True, blank=True)
    is_deleted = IntegerField(default=0, blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    modified_at = DateTimeField(auto_now=True, blank=True, null=True)
    creator_id = IntegerField(null=True, blank=True)

    def to_dict(self):
        opts = self._meta
        data = {}
        for f in opts.concrete_fields:
            value = f.value_from_object(self)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            data[f.name] = value
        return data


class CrawlSyncInstance(Model):
    class Meta:
        db_table = 'crawl_sync_instance'

    id = AutoField(auto_created=True, primary_key=True)
    sync_id = CharField(max_length=255, null=True, blank=True)
    # 0 等待运行、1 运行中、2 成功、3 失败
    sync_status = IntegerField(blank=True)
    task_id = IntegerField(blank=True)
    message = CharField(max_length=255, null=True, blank=True)
    scheduling_cycle = CharField(max_length=255, null=True, blank=True)
    task_name = CharField(max_length=255, null=True, blank=True)
    biz_date = DateTimeField(null=True, blank=True)
    plan_date = DateTimeField(null=True, blank=True)
    start_date = CharField(max_length=255, null=True, blank=True)
    end_date = CharField(max_length=255, null=True, blank=True)
    cost_time = IntegerField(blank=True)
    sync_cnt = IntegerField(blank=True)
    oss_url = CharField(max_length=1024, null=True, blank=True)
    is_deleted = IntegerField(default=0)
    created_at = DateTimeField(blank=True, null=True)
    modified_at = DateTimeField(blank=True, null=True)


class CrawlSyncDataInstance(Model):
    class Meta:
        db_table = 'crawl_sync_data_instance'

    id = AutoField(auto_created=True, primary_key=True)
    instance_name = CharField(max_length=255, null=True, blank=True)
    biz_start_date = DateTimeField(null=True, blank=True)
    biz_end_date = DateTimeField(null=True, blank=True)
    modifier_id = IntegerField(blank=True)
    modifier = CharField(max_length=255, null=True, blank=True)
    is_deleted = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    modified_at = DateTimeField(auto_now=True, blank=True, null=True)


class CrawlSyncData(Model):
    class Meta:
        db_table = 'crawl_sync_data'

    id = AutoField(auto_created=True, primary_key=True)
    task_name = CharField(max_length=255, null=True, blank=True)
    instance_id = IntegerField(blank=True)
    # 0 等待运行、1 运行中、2 成功、3 失败
    status = IntegerField(blank=True)
    message = CharField(max_length=255, null=True, blank=True)
    biz_date = DateTimeField(null=True, blank=True)
    plan_date = DateTimeField(null=True, blank=True)
    start_date = DateTimeField(null=True, blank=True)
    end_date = DateTimeField(null=True, blank=True)
    run_time = IntegerField(blank=True)
    sync_data_cnt = IntegerField(blank=True)
    is_deleted = IntegerField(blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    modified_at = DateTimeField(auto_now=True, blank=True, null=True)
