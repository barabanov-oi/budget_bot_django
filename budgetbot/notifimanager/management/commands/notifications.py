from django.core.management.base import BaseCommand
from django.conf import settings
from telegram import Bot
from telegram.utils.request import Request
from telegram import ParseMode
from telegram.error import Unauthorized
from notifimanager.models import BalanceNotice
from notifimanager.models import YandexYestStat
from datetime import datetime


def send_messaga(message, chat_id):
    try:
        request = Request(
            connect_timeout=0.5,
            read_timeout=1.0,
        )
        bot = Bot(
            request=request,
            token=settings.BOT_TOKEN,
        )
        bot.send_message(chat_id, message, parse_mode=ParseMode.HTML)
    except Unauthorized:
        pass


class Command(BaseCommand):
    help = 'Рассылка оповещений'

    def handle(self, *args, **options):
        today = datetime.now()
        yest_spend = YandexYestStat.objects.filter(date=today, days__lte=settings.NOTIFI_DAYS).values_list(
            'login__login', 'spend', 'balance', 'days')
        if len(yest_spend) > 0:
            notify_login = [login[0] for login in yest_spend]
            profiles = BalanceNotice.objects.filter(directAccount__login__in=notify_login).values_list(
                'directAccount__login', 'profile__chat_id')
            # Словарь с параметрами аккаунтов
            logins_days = dict()
            for login in yest_spend:
                logins_days[login[0]] = {
                    'balance': login[2],
                    'days': login[3],
                }

            # Словарь с набором сообщений для уведомления пользователей
            messages = dict()
            for profile in profiles:
                balance = f'{logins_days[profile[0]]["balance"]:,}'.replace(',', ' ').replace('.', ',')
                message = f'\n<b>{profile[0]}</b> - {balance} руб. - ' \
                          f'{logins_days[profile[0]]["days"]} дн.'
                if profile[1] in messages:
                    messages[profile[1]] += message
                else:
                    messages[profile[1]] = '<b>Внимание!</b> Есть аккаунт(ы) с истекающим бюджетом.\n' + message

            for chat_id in messages.keys():
                send_messaga(messages[chat_id], chat_id)

