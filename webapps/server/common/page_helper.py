# -*- coding: utf-8 -*-
from django.forms.models import model_to_dict
from itertools import chain
from datetime import datetime, timedelta, timezone
from django.db.models import DateTimeField

tz_utc_8 = timezone(timedelta(hours=8))


def page_helper(total, page, size, results, extra=None):
    """
    分页工具
    :param size:
    :param total: 总记录数
    :param page: 当前分页数
    :param results: 当前页结果集
    :param extra:
    :return:
    """
    total = int(total)
    size = int(size)
    if total % size == 0:
        total_page = total / size
    else:
        total_page = int(total / size) + 1

    _from = size * (int(page) - 1)
    _to = size * (int(page))
    page_results = results[_from:_to]
    format_results = list()
    for page_result in page_results:
        format_results.append(to_dict(page_result))
    return {'total_elements': total,
            'page_size': size,
            'total_page': total_page,
            'current_page': int(page),
            'results': format_results,
            'extra': extra
            }


def to_dict(instance, fields=None, exclude=None):
    """
    fix model_to_dict datetime bug?
    """
    if isinstance(instance, dict):
        return instance

    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        value = f.value_from_object(instance)
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            if not getattr(f, 'editable', False):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
        data[f.name] = value
    return data


