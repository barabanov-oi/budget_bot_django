from django.core.management.base import BaseCommand
from django.conf import settings

from telegram import Bot
from telegram import Update
from telegram import ParseMode
from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from telegram.ext import CallbackContext
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater
from telegram.utils.request import Request

from notifimanager.models import Message
from notifimanager.models import Profile
from notifimanager.models import BalanceNotice
from notifimanager.services.botcommand.commands import command_list


def log_errors(f):

    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_message = f'Произошла ошибка: {e}'
            print(error_message)
            raise e

    return inner

@log_errors
def do_echo(update: Update, context: CallbackContext):
    chat_id = int(update.message.chat_id)
    text = update.message.text
    user_name = update.message.from_user.username
    # если в телеграме не указано имя пользователя, возвращается None, такой тип не может быть записан в БД (модель)
    if user_name == None: user_name = 'No name'
    profile, _ = Profile.objects.get_or_create(
        chat_id=chat_id,
        defaults={
            'name': user_name,
        }
    )
    if not profile.verify:
        reply_text = 'Ваш аккаунт не верифицирован. Отправьте запрос на верификацию'
    else:
        command = text.split(' ')[0]
        if command in command_list:
            reply_text = command_list[command](profile_id=profile.id, params=text[len(command) + 1:].replace(' ', ''))
            print(reply_text)
        else:
            reply_text = 'Команда не найдена'

    update.message.reply_text(
        text=reply_text,
        parse_mode=ParseMode.HTML,
    )


class Command(BaseCommand):
    help = 'Телеграм-бот'

    def handle(self, *args, **options):
        request = Request(
            connect_timeout=0.5,
            read_timeout=1.0,
        )
        bot = Bot (
            request=request,
            token=settings.BOT_TOKEN,
        )

        print(bot.getMe())
        # 2 -- обработчики
        updater = Updater(
            bot=bot,
            use_context=True,
        )
        message_handler = MessageHandler(Filters.text, do_echo)
        updater.dispatcher.add_handler(message_handler)

        # 3 -- запустить бесконечную обработку входящих сообщений
        updater.start_polling()
        updater.idle()