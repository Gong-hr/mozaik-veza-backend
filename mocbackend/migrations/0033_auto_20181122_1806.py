# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-22 17:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0032_auto_20181122_1759'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='stagecollection',
            index_together=set([('deleted', 'published', 'source'), ('deleted', 'published', 'id'), ('deleted', 'published', 'string_id')]),
        ),
    ]