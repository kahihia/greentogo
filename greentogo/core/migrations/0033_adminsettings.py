# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-09-29 20:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_location_phase'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lowStockEmails', models.TextField(help_text='List of emails separated by commas (no spaces) for who should recieve alerts when stock is low at restaurants or high at return stations', max_length=1024)),
            ],
        ),
    ]
