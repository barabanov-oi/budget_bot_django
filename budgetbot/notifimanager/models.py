from django.db import models
from django.conf import settings

from telegram import Bot
from telegram.utils.request import Request


class Profile(models.Model):

    chat_id = models.PositiveBigIntegerField(
        verbose_name='ID пользователя',
        unique=True,
    )
    name = models.CharField(
        verbose_name='Имя пользователя',
        max_length=50,
    )
    email = models.CharField(
        verbose_name='E-mail пользователя',
        max_length=70,
        default='Not specified',
    )
    verify = models.BooleanField(
        verbose_name='Верификация',
        choices=((True, 'Да'), (False, 'Нет')),
        default=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.was_veryfy = self.verify

    def save(self, *args, **kwargs):
        if self.was_veryfy == False and self.verify==True:
            message = 'Ваш аккаунт верифицирован, Вы можете отправлять команды боту!\n' \
                      'Чтобы получить список актуальных команд используйте /help'
        elif self.was_veryfy == True and self.verify == False:
            message = 'Ваш аккаунт заблокирован, Вы больше не можете пользоваться ботом.\nДля восстановления доступа обратитесь к администратору'
        try:
            request = Request(
                connect_timeout=0.5,
                read_timeout=1.0,
            )
            bot = Bot(
                request=request,
                token=settings.BOT_TOKEN,
            )
            bot.send_message(chat_id=self.chat_id, text=message)

        except NameError:
            pass

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.chat_id} - {self.name}"

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


class Message(models.Model):
    profile = models.ForeignKey(
        Profile,
        verbose_name='Профиль',
        on_delete=models.PROTECT,
    )
    text = models.TextField(
        verbose_name='Текст',
    )
    received = models.DateTimeField(
        verbose_name='Получено',
        auto_now_add=True,
    )

    def __str__(self):
        return f"Сообщение от {self.profile}"

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'


class DirectAccount(models.Model):
    login = models.CharField(
        verbose_name='Логин клиента',
        max_length=50,
    )
    active = models.BooleanField(
        verbose_name='Активность',
        choices=(
            (True, 'Активен'),
            (False, 'Не активен')
        ),
        default=True,
    )

    def __str__(self):
        return self.login


class BalanceNotice(models.Model):
    profile = models.ForeignKey(
        'Profile',
        on_delete=models.CASCADE,
    )
    directAccount = models.ForeignKey(
        'DirectAccount',
        on_delete=models.CASCADE,
    )


class YandexYestStat(models.Model):
    login = models.ForeignKey(
        'DirectAccount',
        on_delete=models.CASCADE,
    )
    date = models.DateField(
        auto_now=True,
        verbose_name='Дата',
    )
    spend = models.FloatField(
        verbose_name='Открут за вчерашний день',
    )
    balance = models.FloatField(
        verbose_name='Остаток бюджета',
    )
    days = models.PositiveIntegerField(
        verbose_name='Дней до израсходованиия бюджета',
    )