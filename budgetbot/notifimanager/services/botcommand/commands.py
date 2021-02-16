from notifimanager.services.ydirectapi.ydirect import YClient
from notifimanager.models import DirectAccount
from notifimanager.models import BalanceNotice
from notifimanager.models import Profile
from . import add_on

from django.conf import settings

command_list = {

}


def ylogin_list(profile_id: int):
    '''
    Возвращает список логинов, привязанных к клиенту
    :param profile_id: идентификатор клиента (chat id)
    :return: список логинов
    '''
    return list(BalanceNotice.objects.filter(profile__id=profile_id).values_list('directAccount__login',
                                                                                         flat=True))


def yaddLogin(params: str, profile_id: int, msg_format=True):
    """
    Удаляет пробелы из переданной строки, извлекает из неё список логинов.
    Проверяет наличие логина/логинов в БД и аккаунте Яндекс.Директ, добавляет (при необходимости) и привязывает их к
    пользователю.
    :param login_list: строка с логинами, разделёнными запятыми
    :param profile: профиль пользователя
    :param msg_format: флаг формата сообщения
    :return: словарь с результатами обработки команды.
    """
    return_data = {}
    profile, _ = Profile.objects.get_or_create(
        chat_id=int(profile_id),
    )
    # список для активированных логинов
    activate_logins = []
    # получаем список переданных логинов
    logins = list(set(params.replace(' ', '').split(',')))
    # получаем список ранее привязанных логинов
    user_login = set(BalanceNotice.objects.filter(profile__id=profile_id).values_list('directAccount__login',
                                                                                         flat=True))
    # получаем пересечение множеств переданных и привязанных логинов
    # в user_login остаются ранее привязанные логины
    user_login.intersection_update(set(logins))
    # исключаем из запроса ранее привязанные логины
    logins = list(set(logins) - user_login)
    # проверяем наличие логинов из запроса в общей базе
    added_logins = DirectAccount.objects.filter(login__in=logins) #.values_list('login', flat=True)
    if len(added_logins) > 0:
        if len(added_logins.filter(active=False)) > 0:
            added_logins.filter(active=False).update(active=True)

        added_logins = list(added_logins.values_list('login', flat=True))
        activate_logins.extend(added_logins)
        logins = list(set(logins) - set(added_logins))

    if len(logins) > 0:
        direct = YClient(settings.YDIRECT_TOKEN)
        client_budgets = direct.getClientBudget(logins)
        if 'amounts' in client_budgets:
            amount_logins = [key for key in client_budgets['amounts']]
            for login in amount_logins:
                login_obj, _ = DirectAccount.objects.get_or_create(
                    login=login,
                )

            activate_logins.extend(amount_logins)
            return_data["added_login"] = amount_logins

        if 'ActionsErrors' in client_budgets:
            return_data['api_error'] = client_budgets['ActionsErrors']

        if 'Error' in client_budgets:
            return_data['login_error'] = client_budgets['Error']['Logins']

    if msg_format:
        message = ''
        # если пересечение не пустое, добавляем сообщение, что есть ранее привязанные логины
        if len(user_login) > 0:
            plural = add_on.plural_sfx(user_login)
            message += f'Логин{plural} привязан{plural} ранее\n{", ".join(list(user_login))}\n'

        if len(activate_logins) > 0:
            login_ids = DirectAccount.objects.filter(login__in=added_logins)
            login_ids = list(login_ids.values_list('pk', flat=True))
            for pk in login_ids:
                _, created = BalanceNotice.objects.get_or_create(
                    profile_id=profile.chat_id,
                    directAccount_id=pk,
                )
            plural = add_on.plural_sfx(activate_logins)
            message += f"Добавлен{plural} логин" \
                       f"{plural}: " \
                       f"{', '.join(activate_logins)}\n"

        if 'api_error' in return_data:
            for error in return_data['api_error']:
                message += f"{add_on.list_to_str(return_data['api_error'][error]['logins'])} - " \
                           f"{return_data['api_error'][error]['desc']}\n"
                if message.endswith(' - \n'): message = f"{message[:-4]}\n"

        if 'login_error' in return_data:
            message += f"Ошибка при обращении к API Директа для {', '.join(return_data['login_error'])}"

        return message[:-1]

    return return_data


def my_logins(profile_id: int, params: str):
    """
    Функция возвращает список логинов, привязанных к аккаунту, либо False, если ни одного логина не привязано
    :param profile_id: ID пользователя в базе
    :param params: параметры запроса
    :return: список логинов либо False
    """
    logins_list = ylogin_list(profile_id)
    if len(logins_list) == 0:
        msg_text = 'Нет привязанных аккаунтов'
    else:
        direct = YClient(settings.YDIRECT_TOKEN)
        balance = direct.getClientBudget(logins_list)
        if 'amounts' in balance:
            if len(balance['amounts']) == len(logins_list):
                balance = balance['amounts']
            else:
                no_balance = set(logins_list) - set(list(balance['amounts']))
                balance['amount'].update(
                    dict.fromkeys(list(no_balance), '-')
                )
        else:
            balance = dict.fromkeys(logins_list, '-')

        msg_text = '<b>Логин\t-\tОстаток</b>\n\n'
        print(balance)
        for key, value in balance.items():
            value = f'{float(value):,}'.replace(',', ' ')
            print(value)
            msg_text += f"{key} - <b>{value} руб.</b>\n"

    return msg_text


def ydel(profile_id: int, params: str):
    msg = ''
    # список привязанных логинов
    user_logins = set(BalanceNotice.objects.filter(profile__id=profile_id).values_list('directAccount__login',
                                                                                         flat=True))
    # логины из команды
    command_logins = set(params.split(',')) - {',', ''}
    # удаляем пустые значения (если в конце или начале запроса запятые)

    # логины, привязанные к другим пользователям
    other_logins = set(BalanceNotice.objects.exclude(profile__id=profile_id).values_list('directAccount__login',
                                                                                       flat=True))
    bad_logins = set(command_logins - user_logins)
    if len(bad_logins) > 0:
        msg += f'Не привязан(ы) к Вашему профилю:\n<b>{", ".join(list(bad_logins))}.</b>'
        command_logins = command_logins - bad_logins

    # если остались логины привязанные к профилю, удаляем привязку, иначе добавляем сообщение, что логинов на
    # удаление нет
    if len(command_logins) > 0:
        BalanceNotice.objects.filter(profile__id=profile_id, directAccount__login__in=list(command_logins)).delete()
        msg += f'\nУдален(ы): <b>{", ".join(list(command_logins))}</b>.'
    else:
        msg += '\nНа удаление нет логинов, привязанных к Вашему профилю'

    # из логинов пользователя вычитаем логины остальных пользователей, чтобы отключить активность по логину
    command_logins = command_logins - other_logins
    if len(command_logins) > 0:
        DirectAccount.objects.filter(login__in=list(command_logins)).update(active=False)

    return msg


command_list = {
    'mylogins': my_logins,
    'ydel': ydel,
    'yadd': yaddLogin,
}