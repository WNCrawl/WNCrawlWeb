from django.db import connection, connections


def get_cursor(conn):
    if not conn:
        return connection.cursor()
    else:
        return conn.cursor()


def execute_sql(sql, conn=None):
    cursor = get_cursor(conn)
    raw_count = cursor.execute(sql)
    cursor.close()
    return raw_count


def insert_id(sql, conn=None):
    cursor = get_cursor(conn)
    raw_count = cursor.execute(sql)
    i_id = cursor.lastrowid
    cursor.close()
    return i_id


def execute_sql_with_params(sql, params, conn=None):
    cursor = get_cursor(conn)
    ret = cursor.execute(sql, params)
    cursor.close()
    return ret


def fetch_one(sql, conn=None):
    cursor = get_cursor(conn)
    cursor.execute(sql)
    row = cursor.fetchone()
    return row


def fetch_one_with_params(sql, params, conn=None):
    cursor = get_cursor(conn)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return row


def fetch_all_with_params(sql, params, conn=None):
    cursor = get_cursor(conn)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return rows


def fetch_all(sql, conn=None):
    cursor = get_cursor(conn)
    cursor.execute(sql)
    rows = cursor.fetchall()
    return rows


def fetch_all_by_column(sql, has_column=True, conn=None):
    cursor = get_cursor(conn)
    cursor.execute(sql)
    field_names = list()
    if has_column:
        field_names = [i[0] for i in cursor.description]
    rows = cursor.fetchall()
    return rows, field_names

def fetch_all_to_json(sql, conn=None):
    cursor = get_cursor(conn)
    cursor.execute(sql)
    return dictfetchall(cursor)


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def prepare_request_params(request):
    params_h = request.query_params
    post_params = request.data
    merged_params = {}
    for k in params_h:
        merged_params[k] = params_h[k]
    for k in post_params:
        merged_params[k] = post_params[k]
    return merged_params


def execute_dynamic_insert(table_name, insert_kvs):

    cols = []
    col_vals = []
    for col, col_val in insert_kvs.items():
        cols.append(col)
        col_vals.append(col_val)

    ins_list = ",".join(cols)
    param_list = ",".join(["%s" for _ in range(len(cols))])

    sql = "insert into %s (%s) values(%s)" % (table_name, ins_list, param_list)
    rows = execute_sql_with_params(sql, col_vals)
    return rows


def execute_dynamic_update(table_name, where_conditions, **update_kvs):

    update_cols = []
    col_vals = []
    update_col_params = []

    for col, col_val in update_kvs.items():
        # do not update col in where conditions
        if col in where_conditions:
            continue
        update_cols.append(col)
        col_vals.append(col_val)
        update_col_params.append('%s')

    update_list = ",".join(["=".join(k) for k in zip(update_cols,update_col_params)])

    where_cols = []
    where_col_params = []

    for col, col_val in where_conditions.items():
        where_cols.append(col)
        col_vals.append(col_val)
        where_col_params.append('%s')

    where_list = " and ".join(["=".join(s) for s in zip(where_cols, where_col_params)])
    sql = "update %s set %s where %s" % (table_name, update_list, where_list)
    rowcnt = execute_sql_with_params(sql, col_vals)
    return rowcnt


def execute_dynamic_replace(table_name, where_conditions, **kvs):
    row_cnt = execute_dynamic_update(table_name, where_conditions, **kvs)
    if row_cnt == 0:
        execute_dynamic_insert(table_name, **kvs)


def insert(sql, params):
    cur = connection.cursor()
    row_cnt = cur.execute(sql, params)
    cur.close()
    return row_cnt
