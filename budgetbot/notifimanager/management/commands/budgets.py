from django.core.management.base import BaseCommand
from django.conf import settings

from telegram import Bot
from telegram.utils.request import Request

from notifimanager.models import DirectAccount
from notifimanager.models import YandexYestStat
from notifimanager.services.ydirectapi.ydirect import YClient
from notifimanager.services.botcommand.commands import command_list
from notifimanager.services.botcommand import add_on

from tapi_yandex_direct import YandexDirect

from datetime import datetime

def accountsStat(accounts_list, yconnect):
    return_data = {
        "budgets": {},
        "error": {},
        }
    for account in accounts_list:
        error, stat = yconnect.getStat(account)
        if not error:
            for row in stat.split(sep="\n")[1:-1]:
                col = row.split("\t")
                if account in return_data:
                    return_data["budgets"][account] += float(col[1])
                else:
                    return_data["budgets"][account] = float(col[1])
        else:
            return_data["error"][account] = stat["status_code"]

    return return_data


def mymodel():
    user = Profile.objects.filter(chat_id=11)
    print(user, type(user), len(user))


class Command(BaseCommand):
    help = 'Запись открута'

    def login_yest_spend(self, login_list: list):
        """
        Возвращает открут за вчерашний день и ошибки при получении статистики
        :param login_list: список логинов для получения статистики
        :return: возвращает словарь с открутом по логинам и ошибки (если они были)
        """
        spend = {}
        request_body = {
            'params': {
                'SelectionCriteria': {},
                'FieldNames': ['Cost'],
            },
        }
        direct = YClient(settings.YDIRECT_TOKEN)
        request = direct.getLoginReport(login_list, ('YESTERDAY', ), request_body)
        try:
            if len(request['data']) > 0:
                spend.update({
                    'yest_spend': dict(),
                })
                for key, value in request["data"]["report_data"]:
                    spend["yest_spend"][key] = int(value) / 1000000

                balance = direct.getClientBudget(list(spend["yest_spend"].keys()))
                spend.update({
                    'balance': balance["amounts"],
                })
                days = dict()
                for key in spend['yest_spend']:
                    try:
                        days[key] = round(float(spend['balance'][key]) / spend['yest_spend'][key], 0)
                    except KeyError:
                        days['errors'][key] = key
                    except ZeroDivisionError:
                        days[key] = 365

                spend.update({
                    'days': days,
                })
            else:
                spend['error'] = 'Ошибка при запросе к API\n'
                if 'errors' in request:
                    for key_error in request['errors'].keys():
                        spend['error'] += f'Код ошибки - {key_error}\n'
                        if 'err_response' in request['errors'][key_error]:
                            spend['error'] += request['errors'][key_error]['err_response']

        except KeyError:
            spend['error'] = f'При запросе к API произошла ошибка.\nСервер вернул - {request}'

        return spend

    def handle(self, *args, **options):
        accounts = DirectAccount.objects.filter(active=True)
        accounts_set = set([i[0] for i in list(accounts.values_list('login'))])
        today = datetime.now()
        yest_accounts = set([i[0] for i in YandexYestStat.objects.filter(date=today).values_list('login__login')])
        yest_accounts = accounts_set - yest_accounts
        message = ''
        if len(yest_accounts) != 0:
            spend = self.login_yest_spend(list(yest_accounts))
            if 'error' not in spend:
                yest_spend = []
                login_error = []
                for account in yest_accounts:
                    try:
                        yest_spend.append(
                            YandexYestStat(
                                login=accounts.get(login=account),
                                spend=spend["yest_spend"][account],
                                balance=spend["balance"][account],
                                days=spend["days"][account],
                            )
                        )
                    except KeyError:
                        login_error.append(account.login)

                YandexYestStat.objects.bulk_create(yest_spend)
                if len(login_error) > 0:
                    message = f'Данные за {today.strftime("%d.%m.%Y")} не получены:'
                    for login in login_error:
                        message += f'\n{login}'

                else:
                    message = f'Данные за {today.strftime("%d.%m.%Y")} по всем аккаунтам записаны'

            else:
                message = spend['error']

        if len(message) != 0:
            request = Request(
                connect_timeout=0.5,
                read_timeout=1.0,
            )
            bot = Bot(
                request=request,
                token=settings.BOT_TOKEN,
            )
            bot.send_message(settings.ADMIN_ID, message)
