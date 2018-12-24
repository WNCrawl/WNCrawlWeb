# -*- coding: utf-8 -*-
from django.db.models import QuerySet

from server.toolkit import api_kit


class Result:

    @classmethod
    def success(cls, data):
        if isinstance(data, QuerySet) and not data:
            return api_kit.assemble_success(result_data=list())
        if not data:
            return api_kit.assemble_success()
        if isinstance(data, str):
            return api_kit.assemble_success(result_message=data)
        return api_kit.assemble_success(result_data=data)

    @classmethod
    def fail(cls, data):
        if isinstance(data, dict):
            return api_kit.assemble_fail(result_data=data)
        elif isinstance(data, list):
            return api_kit.assemble_fail(result_data=data)
        elif isinstance(data, str) or data is None:
            return api_kit.assemble_fail(result_message=data)
        elif isinstance(data, Exception):
            return api_kit.assemble_fail(result_message=str(data))


