# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-22 18:03
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0033_auto_20181122_1806'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='logchangeset',
            index_together=set([('deleted', 'published', 'created_at', 'collection'), ('deleted', 'published', 'collection', 'created_at', 'id')]),
        ),
    ]