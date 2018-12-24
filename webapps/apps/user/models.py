# Create your models here.
from django.db.models import Model, CharField, GenericIPAddressField, IntegerField, TextField, DateTimeField, \
    ManyToManyField, ForeignKey, DO_NOTHING, BooleanField, AutoField


class CrawlUser(Model):
    """
    用户表
    """
    class Meta:
        db_table = 'crawl_user'

    id = AutoField(auto_created=True, primary_key=True)
    username = CharField(max_length=255, null=True, blank=True)
    account = CharField(max_length=255, null=True, blank=True)
    mobile = CharField(max_length=255, null=True, blank=True)
    password = CharField(max_length=255, null=True, blank=True)
    wx_account = CharField(max_length=255, null=True, blank=True)
    alert_enable = IntegerField(default=0)
    comment = CharField(max_length=255, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
    is_deleted = IntegerField(default=0)


class CrawlRole(Model):
    """
    角色表
    """
    class Meta:
        db_table = 'crawl_role'

    id = AutoField(auto_created=True, primary_key=True)
    role_name = CharField(max_length=255, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
    is_deleted = IntegerField(default=0)


class CrawlPermission(Model):
    """
    权限表
    """
    class Meta:
        db_table = 'crawl_permission'

    id = IntegerField(auto_created=True, primary_key=True)
    permission_url = CharField(max_length=255, null=True, blank=True)
    permission_name = CharField(max_length=255, null=True, blank=True)
    parent_id = IntegerField(blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
    is_deleted = IntegerField(default=0)


class CrawlUserRoleRel(Model):
    """
    用户权限关系表
    """
    class Meta:
        db_table = 'crawl_user_role'

    id = IntegerField(auto_created=True, primary_key=True)
    user_id = IntegerField(blank=True)
    role_id = IntegerField(blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
    is_deleted = IntegerField(default=0)


class CrawlRolePermission(Model):
    """
    角色权限关系表
    """
    class Meta:
        db_table = 'crawl_role_permission'

    id = IntegerField(auto_created=True, primary_key=True)
    role_id = IntegerField(blank=True)
    permission_id = IntegerField(blank=True)
    created_at = DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = DateTimeField(auto_now=True, blank=True, null=True)
    is_deleted = IntegerField(default=0)
