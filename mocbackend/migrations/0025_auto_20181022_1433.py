# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-22 12:33
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0024_auto_20181018_1427'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='stageattributevalue',
            index_together=set([('attribute', 'entity'), ('deleted', 'published', 'id'), ('deleted', 'published', 'attribute', 'entity_entity'), ('deleted', 'attribute', 'value_string'), ('deleted', 'published', 'attribute', 'entity')]),
        ),
    ]
