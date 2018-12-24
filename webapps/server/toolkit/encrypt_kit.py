import hashlib


def md5(md5_char):
    """
    md5算法
    :param md5_char:
    :return:
    """
    if not md5_char:
        md5_char = ''
    hash_md5 = hashlib.md5(md5_char.encode("utf-8"))
    return hash_md5.hexdigest()