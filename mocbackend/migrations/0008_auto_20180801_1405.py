# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-01 12:05
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0007_auto_20180727_1226'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='stageentity',
            index_together=set([('linked_potentially_pep', 'deleted', 'published', 'public_id'), ('force_pep', 'deleted', 'published', 'id'), ('deleted', 'published', 'public_id'), ('force_pep', 'deleted', 'published', 'public_id'), ('linked_potentially_pep', 'deleted', 'published', 'id'), ('deleted', 'published', 'id')]),
        ),
    ]
