def merge(dict1, dict2):
    """
    Merge two dictionaries.
    :param dict1:
    :param dict2:
    :return:
    """
    for k in dict2:
        if k in dict1 and isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
            merge(dict1[k], dict2[k])
        else:
            dict1[k] = dict2[k]
