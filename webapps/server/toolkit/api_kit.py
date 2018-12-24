# -*- coding: utf-8 -*-


def assemble_success(result_code=1, result_message='done', result_data={}):
    return {"result_code": result_code, "result_message": result_message, "data": result_data,
            "result": True}


def assemble_fail(result_code=-1, result_message='fail', result_data={}):
    return {"result_code": result_code, "result_message": result_message, "data": result_data,
            "result": False}
