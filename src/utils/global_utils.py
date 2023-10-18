
def sql_obj_to_dict(sql_obj):
    d = dict()
    for col in sql_obj.__table__.columns:
        d[col.name] = getattr(sql_obj, col.name)
    return d


def sql_obj_list_to_dict_list(sql_obj_list):
    return [sql_obj_to_dict(sql_obj) for sql_obj in sql_obj_list]