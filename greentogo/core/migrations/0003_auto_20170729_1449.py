# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-29 14:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20170722_1942'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='plan',
            options={'ordering': ['amount', 'number_of_boxes']},
        ),
    ]
