# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-13 17:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0028_auto_20181024_1517'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stageentity',
            name='internal_slug',
            field=models.CharField(db_index=True, max_length=128),
        ),
        migrations.AlterIndexTogether(
            name='stageattribute',
            index_together=set([('deleted', 'published', 'attribute', 'id'), ('deleted', 'published', 'collection', 'id'), ('deleted', 'published', 'attribute', 'string_id'), ('deleted', 'published', 'collection', 'string_id'), ('deleted', 'published', 'entity_type', 'string_id'), ('deleted', 'published', 'order_number'), ('deleted', 'published', 'entity_type', 'id'), ('deleted', 'published', 'string_id'), ('deleted', 'published', 'entity_type', 'order_number'), ('deleted', 'published', 'id'), ('string_id', 'attribute'), ('deleted', 'string_id', 'attribute', 'attribute_type'), ('deleted', 'published', 'attribute', 'order_number'), ('deleted', 'published', 'collection', 'order_number')]),
        ),
        migrations.AlterIndexTogether(
            name='stageattributevalue',
            index_together=set([('attribute', 'entity', 'entity_entity', 'value_codebook_item'), ('attribute', 'value_codebook_item'), ('attribute', 'entity', 'value_codebook_item'), ('attribute', 'entity_entity', 'value_codebook_item'), ('attribute', 'value_string')]),
        ),
        migrations.AlterIndexTogether(
            name='stageattributevaluecollection',
            index_together=set([('deleted', 'published', 'attribute_value', 'collection'), ('deleted', 'published', 'collection')]),
        ),
        migrations.AlterIndexTogether(
            name='stageentity',
            index_together=set([('deleted', 'published', 'public_id'), ('deleted', 'published', 'id'), ('linked_potentially_pep', 'deleted', 'published', 'id'), ('linked_potentially_pep', 'deleted', 'published', 'public_id'), ('force_pep', 'deleted', 'published', 'public_id'), ('force_pep', 'deleted', 'published', 'id')]),
        ),
        migrations.AlterIndexTogether(
            name='stageentityentity',
            index_together=set([('deleted', 'published', 'entity_a', 'entity_b', 'connection_type', 'valid_from', 'valid_to', 'transaction_amount', 'transaction_currency', 'transaction_date'), ('deleted', 'published', 'entity_b', 'entity_a', 'connection_type', 'valid_from', 'valid_to', 'transaction_amount', 'transaction_currency', 'transaction_date')]),
        ),
    ]
