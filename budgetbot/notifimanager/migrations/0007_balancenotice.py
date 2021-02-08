# Generated by Django 3.1.3 on 2020-11-20 06:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notifimanager', '0006_directaccount'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceNotice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('directAccount', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notifimanager.directaccount')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notifimanager.profile')),
            ],
        ),
    ]
