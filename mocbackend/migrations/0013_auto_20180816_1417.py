# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-08-16 12:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mocbackend', '0012_auto_20180810_1457'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userentity',
            name='backend_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_entities', to='mocbackend.UserInfo'),
        ),
        migrations.AlterField(
            model_name='userentity',
            name='entity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_entities', to='mocbackend.StageEntity'),
        ),
    ]
