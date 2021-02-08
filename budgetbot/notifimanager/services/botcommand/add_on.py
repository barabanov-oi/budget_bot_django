def list_to_str(list: list):
    str_list = list[0]
    if len(list) > 1:
        for l in list[1:]:
            str_list += f', {l}'

    return str_list

def plural_sfx(list: list, suffix='ы'):
    """
    Возвращает суффикс для множественного числа
    :param list: список
    :param suffix: окончание для множественного числа
    :return: str: пустая строка или suffix
    """
    if len(list) > 1: return suffix

    return ''