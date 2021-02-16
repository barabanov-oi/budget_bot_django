from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from notifimanager.models import Profile
from notifimanager.services.botcommand.commands import command_list

from queue import Queue
from telegram import Bot
from telegram import Update
from telegram.ext import Dispatcher
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import CallbackContext
from telegram import ParseMode

import json


# декоратор обработки исключений
def log_errors(f):

    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_message = f'Произошла ошибка: {e}'
            print(error_message)
            raise e

    return inner


# обработка входящих сообщений
@log_errors
def do_echo(update: Update, context: CallbackContext):
    chat_id = int(update.message.chat_id)
    text = update.message.text
    user_name = update.message.from_user.username
    # если в телеграме не указано имя пользователя, возвращается None, такой тип не может быть записан в БД (модель)
    if user_name == None:
        user_name = 'No name'

    profile, _ = Profile.objects.get_or_create(
        chat_id=chat_id,
        defaults={
            'name': user_name,
        }
    )
    command = text.split(' ')[0]
    if not profile.verify:
        if command == '/start':
            reply_text = f'Ваш chat_id <b>{chat_id}</b>.\nНеобходимо пройти верификацию.\nОтправьте на ' \
                         f'oleg.barabanov@mdp.digital письмо с темой:\n<i>Верификация {chat_id} для ' \
                         f'context_mdp_bot</i>\nЗапросы принимаются только с корпоративной почты.'
        else:
            reply_text = f'Ваш аккаунт не верифицирован. Отправьте запрос.\nВаш chat_id <b>{chat_id}</b>'
    else:
        if command in command_list:
            reply_text = command_list[command](profile_id=int(profile.id), params=text[len(command) + 1:].replace(' ',
                                                                                                                ''))
            print(reply_text)
        elif command == '/help':
            reply_text = 'На текущий момент доступны следующие команды:\n\n<b>yadd </b><i>логин(ы) ' \
                         'Яндекс.Директа</i>\nПривязывает логин(ы) к Вашему профилю для отправки уведомлений. ' \
                         'Несколько логинов необходимо указывать через запятую.\n\n<b>ydel </b><i>логин(ы) ' \
                         'Яндес.Директа</i>\nОтвязывает логин(ы) от Вашего профиля, уведомления по ним приходить не ' \
                         'будут. Несколько логинов необходимо указывать через запятую.\n\n<b>mylogins</b> - выводит ' \
                         'список привязанных логинов и остатки бюджетов по ним.'
        else:
            reply_text = 'Команда не найдена'

    update.message.reply_text(
        text=reply_text,
        parse_mode=ParseMode.HTML,
    )


def webhook(update, dispatcher):
    dispatcher.process_update(update)


# отключаем CSRF для обработчика вебхук, чтобы обработать запрос от сервера телеграм, т.к. этот запрос по умолчанию
# безопасный
@csrf_exempt
def webhook_handler(request):
    bot = Bot(settings.BOT_TOKEN)
    update_queue = Queue()
    dp = Dispatcher(bot, update_queue)
    message_handler = MessageHandler(Filters.text, do_echo)
    dp.add_handler(message_handler)

    # если получен POST-запрос с json, обработать его
    if (request.method == 'POST') and (request.META['CONTENT_TYPE'] == 'application/json'):
        json_data = request.body.decode('utf-8')
        json_data = json.loads(json_data)

        update_obj = Update.de_json(json_data, bot)
        webhook(update_obj, dp)

    return HttpResponse('Ok!')
