# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-04-26 14:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0003_auto_20180408_1526'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stageattributetype',
            name='currency',
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='new_currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_value_changes_new_currency', to='mocbackend.StaticCurrency'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='old_currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_value_changes_old_currency', to='mocbackend.StaticCurrency'),
        ),
        migrations.AddField(
            model_name='stageattributevalue',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_values', to='mocbackend.StaticCurrency'),
        ),
    ]