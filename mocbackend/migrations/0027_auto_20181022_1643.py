# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-22 14:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0026_auto_20181022_1539'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='stageattributevalue',
            index_together=set([('deleted', 'published', 'attribute', 'entity_entity'), ('entity_entity', 'attribute'), ('deleted', 'published', 'attribute', 'entity'), ('deleted', 'published', 'id'), ('entity', 'attribute'), ('deleted', 'attribute', 'value_string')]),
        ),
    ]
