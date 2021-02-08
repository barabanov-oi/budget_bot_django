# Generated by Django 3.1.3 on 2020-11-11 06:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifimanager', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'Профиль', 'verbose_name_plural': 'Профили'},
        ),
        migrations.AddField(
            model_name='user',
            name='verify',
            field=models.BooleanField(choices=[(True, 'Да'), (False, 'Нет')], default=False, verbose_name='Верификация'),
        ),
    ]
