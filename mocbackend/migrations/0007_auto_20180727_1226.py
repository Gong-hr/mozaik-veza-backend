# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-07-27 11:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0006_auto_20180724_1721'),
    ]

    operations = [
        migrations.AddField(
            model_name='stageentity',
            name='internal_slug',
            field=models.CharField(max_length=128),
        ),
        migrations.AddField(
            model_name='stageentity',
            name='internal_slug_count',
            field=models.BigIntegerField(),
        ),
        migrations.AlterField(
            model_name='stageattributevalue',
            name='value_string',
            field=models.CharField(blank=True, db_index=True, max_length=512, null=True),
        ),
        migrations.AlterIndexTogether(
            name='stageentity',
            index_together=set([('force_pep', 'deleted', 'published', 'public_id'), ('internal_slug', 'internal_slug_count'), ('deleted', 'published', 'public_id'), ('force_pep', 'deleted', 'published', 'id'), ('linked_potentially_pep', 'deleted', 'published', 'id'), ('deleted', 'published', 'id'), ('linked_potentially_pep', 'deleted', 'published', 'public_id')]),
        ),
    ]
