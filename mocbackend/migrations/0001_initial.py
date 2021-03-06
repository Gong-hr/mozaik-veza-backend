# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-02-27 20:07
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='KeyValue',
            fields=[
                ('key', models.CharField(max_length=512, primary_key=True, serialize=False)),
                ('value', models.CharField(db_index=True, max_length=512)),
                ('raw_data', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'mocbackend_key_value',
            },
        ),
        migrations.CreateModel(
            name='LogAttributeValueChange',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('old_valid_from', models.DateField(blank=True, null=True)),
                ('new_valid_from', models.DateField(blank=True, null=True)),
                ('old_valid_to', models.DateField(blank=True, null=True)),
                ('new_valid_to', models.DateField(blank=True, null=True)),
                ('old_value_boolean', models.NullBooleanField()),
                ('new_value_boolean', models.NullBooleanField()),
                ('old_value_int', models.BigIntegerField(blank=True, null=True)),
                ('new_value_int', models.BigIntegerField(blank=True, null=True)),
                ('old_value_fixed_point', models.BigIntegerField(blank=True, null=True)),
                ('new_value_fixed_point', models.BigIntegerField(blank=True, null=True)),
                ('old_value_floating_point', models.FloatField(blank=True, null=True)),
                ('new_value_floating_point', models.FloatField(blank=True, null=True)),
                ('old_value_string', models.CharField(blank=True, max_length=512, null=True)),
                ('new_value_string', models.CharField(blank=True, max_length=512, null=True)),
                ('old_value_text', models.TextField(blank=True, null=True)),
                ('new_value_text', models.TextField(blank=True, null=True)),
                ('old_value_datetime', models.DateTimeField(blank=True, null=True)),
                ('new_value_datetime', models.DateTimeField(blank=True, null=True)),
                ('old_value_date', models.DateField(blank=True, null=True)),
                ('new_value_date', models.DateField(blank=True, null=True)),
                ('old_value_geo_lat', models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ('new_value_geo_lat', models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ('old_value_geo_lon', models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ('new_value_geo_lon', models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ('old_value_range_int_from', models.BigIntegerField(blank=True, null=True)),
                ('new_value_range_int_from', models.BigIntegerField(blank=True, null=True)),
                ('old_value_range_int_to', models.BigIntegerField(blank=True, null=True)),
                ('new_value_range_int_to', models.BigIntegerField(blank=True, null=True)),
                ('old_value_range_fixed_point_from', models.BigIntegerField(blank=True, null=True)),
                ('new_value_range_fixed_point_from', models.BigIntegerField(blank=True, null=True)),
                ('old_value_range_fixed_point_to', models.BigIntegerField(blank=True, null=True)),
                ('new_value_range_fixed_point_to', models.BigIntegerField(blank=True, null=True)),
                ('old_value_range_floating_point_from', models.FloatField(blank=True, null=True)),
                ('new_value_range_floating_point_from', models.FloatField(blank=True, null=True)),
                ('old_value_range_floating_point_to', models.FloatField(blank=True, null=True)),
                ('new_value_range_floating_point_to', models.FloatField(blank=True, null=True)),
                ('old_value_range_datetime_from', models.DateTimeField(blank=True, null=True)),
                ('new_value_range_datetime_from', models.DateTimeField(blank=True, null=True)),
                ('old_value_range_datetime_to', models.DateTimeField(blank=True, null=True)),
                ('new_value_range_datetime_to', models.DateTimeField(blank=True, null=True)),
                ('old_value_range_date_from', models.DateField(blank=True, null=True)),
                ('new_value_range_date_from', models.DateField(blank=True, null=True)),
                ('old_value_range_date_to', models.DateField(blank=True, null=True)),
                ('new_value_range_date_to', models.DateField(blank=True, null=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Attribute Value Change',
                'verbose_name_plural': 'Attributes Values Changes',
                'db_table': 'mocbackend_log_attribute_value_change',
            },
        ),
        migrations.CreateModel(
            name='LogChangeset',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Changeset',
                'verbose_name_plural': 'Changesets',
                'db_table': 'mocbackend_log_changeset',
            },
        ),
        migrations.CreateModel(
            name='LogEntityEntityChange',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('old_valid_from', models.DateField(blank=True, null=True)),
                ('new_valid_from', models.DateField(blank=True, null=True)),
                ('old_valid_to', models.DateField(blank=True, null=True)),
                ('new_valid_to', models.DateField(blank=True, null=True)),
                ('transaction_amount', models.DecimalField(blank=True, decimal_places=4, max_digits=22, null=True)),
                ('transaction_date', models.DateField(blank=True, null=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Entity Connection Change',
                'verbose_name_plural': 'Entities Connections Changes',
                'db_table': 'mocbackend_log_entity_entity_change',
            },
        ),
        migrations.CreateModel(
            name='StageAttribute',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64)),
                ('is_required', models.BooleanField(default=False)),
                ('is_unique', models.BooleanField(default=False)),
                ('default_value', models.CharField(blank=True, max_length=512, null=True)),
                ('order_number', models.IntegerField(default=10000)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name_plural': 'Attributes',
                'db_table': 'mocbackend_stage_attribute',
                'verbose_name': 'Attribute',
            },
        ),
        migrations.CreateModel(
            name='StageAttributeType',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('is_multivalue', models.BooleanField(default=False)),
                ('permited_values', models.TextField(blank=True, null=True)),
                ('fixed_point_decimal_places', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('range_floating_point_from_inclusive', models.NullBooleanField()),
                ('range_floating_point_to_inclusive', models.NullBooleanField()),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Attribute Type',
                'verbose_name_plural': 'Attribute Types',
                'db_table': 'mocbackend_stage_attribute_type',
            },
        ),
        migrations.CreateModel(
            name='StageAttributeValue',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('value_boolean', models.NullBooleanField()),
                ('value_int', models.BigIntegerField(blank=True, null=True)),
                ('value_fixed_point', models.BigIntegerField(blank=True, null=True)),
                ('value_floating_point', models.FloatField(blank=True, null=True)),
                ('value_string', models.CharField(blank=True, max_length=512, null=True)),
                ('value_text', models.TextField(blank=True, null=True)),
                ('value_datetime', models.DateTimeField(blank=True, null=True)),
                ('value_date', models.DateField(blank=True, null=True)),
                ('value_geo_lat', models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
                ('value_geo_lon', models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True, validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
                ('value_range_int_from', models.BigIntegerField(blank=True, null=True)),
                ('value_range_int_to', models.BigIntegerField(blank=True, null=True)),
                ('value_range_fixed_point_from', models.BigIntegerField(blank=True, null=True)),
                ('value_range_fixed_point_to', models.BigIntegerField(blank=True, null=True)),
                ('value_range_floating_point_from', models.FloatField(blank=True, null=True)),
                ('value_range_floating_point_to', models.FloatField(blank=True, null=True)),
                ('value_range_datetime_from', models.DateTimeField(blank=True, null=True)),
                ('value_range_datetime_to', models.DateTimeField(blank=True, null=True)),
                ('value_range_date_from', models.DateField(blank=True, null=True)),
                ('value_range_date_to', models.DateField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
                ('attribute', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attribute_values', to='mocbackend.StageAttribute')),
            ],
            options={
                'verbose_name': 'Attribute Value',
                'verbose_name_plural': 'Attributes Values',
                'db_table': 'mocbackend_stage_attribute_value',
            },
        ),
        migrations.CreateModel(
            name='StageAttributeValueCollection',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_to', models.DateField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
                ('attribute_value', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attribute_value_collections', to='mocbackend.StageAttributeValue')),
            ],
            options={
                'db_table': 'mocbackend_stage_attribute_value_collection',
            },
        ),
        migrations.CreateModel(
            name='StageCodebook',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('is_closed', models.BooleanField(default=False)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Codebook',
                'verbose_name_plural': 'Codebooks',
                'db_table': 'mocbackend_stage_codebook',
            },
        ),
        migrations.CreateModel(
            name='StageCodebookValue',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('value', models.CharField(max_length=512)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
                ('codebook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='codebook_values', to='mocbackend.StageCodebook')),
            ],
            options={
                'verbose_name_plural': 'Codebooks Values',
                'db_table': 'mocbackend_stage_codebook_value',
                'verbose_name': 'Codebook Value',
            },
        ),
        migrations.CreateModel(
            name='StageCollection',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Collection',
                'verbose_name_plural': 'Collections',
                'db_table': 'mocbackend_stage_collection',
            },
        ),
        migrations.CreateModel(
            name='StageEntity',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('public_id', models.CharField(max_length=64, unique=True, verbose_name='Public ID')),
                ('linked_potentially_pep', models.BooleanField(default=False)),
                ('force_pep', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Entity',
                'verbose_name_plural': 'Entities',
                'db_table': 'mocbackend_stage_entity',
            },
        ),
        migrations.CreateModel(
            name='StageEntityEntity',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('transaction_amount', models.DecimalField(blank=True, decimal_places=4, max_digits=22, null=True)),
                ('transaction_date', models.DateField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name_plural': 'Entities Connections',
                'db_table': 'mocbackend_stage_entity_entity',
                'verbose_name': 'Entity Connection',
            },
        ),
        migrations.CreateModel(
            name='StageEntityEntityCollection',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_to', models.DateField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entity_entity_collections', to='mocbackend.StageCollection')),
                ('entity_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entity_entity_collections', to='mocbackend.StageEntityEntity')),
            ],
            options={
                'db_table': 'mocbackend_stage_entity_entity_collection',
            },
        ),
        migrations.CreateModel(
            name='StageSource',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('address', models.CharField(blank=True, max_length=64, null=True)),
                ('quality', models.SmallIntegerField(default=0)),
                ('contact', models.TextField(blank=True, null=True)),
                ('note', models.TextField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False, verbose_name='Soft Deleted')),
            ],
            options={
                'verbose_name': 'Source',
                'verbose_name_plural': 'Sources',
                'db_table': 'mocbackend_stage_source',
            },
        ),
        migrations.CreateModel(
            name='StaticChangeType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'Change Type',
                'verbose_name_plural': 'Change Types',
                'db_table': 'mocbackend_static_change_type',
            },
        ),
        migrations.CreateModel(
            name='StaticCollectionType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'Collection Type',
                'verbose_name_plural': 'Collection Types',
                'db_table': 'mocbackend_static_collection_type',
            },
        ),
        migrations.CreateModel(
            name='StaticConnectionType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=128)),
                ('reverse_name', models.CharField(max_length=64)),
                ('potentially_pep', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name_plural': 'Connection Types',
                'db_table': 'mocbackend_static_connection_type',
                'verbose_name': 'Connection Type',
            },
        ),
        migrations.CreateModel(
            name='StaticConnectionTypeCategory',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'Connection Type Category',
                'verbose_name_plural': 'Connection Type Categories',
                'db_table': 'mocbackend_static_connection_type_category',
            },
        ),
        migrations.CreateModel(
            name='StaticCurrency',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=3, unique=True)),
                ('sign', models.CharField(max_length=8)),
                ('sign_before_value', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Currency',
                'verbose_name_plural': 'Currencies',
                'db_table': 'mocbackend_static_currency',
            },
        ),
        migrations.CreateModel(
            name='StaticDataType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'Data Type',
                'verbose_name_plural': 'Data Types',
                'db_table': 'mocbackend_static_data_type',
            },
        ),
        migrations.CreateModel(
            name='StaticEntityType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'Entity Type',
                'verbose_name_plural': 'Entity Types',
                'db_table': 'mocbackend_static_entity_type',
            },
        ),
        migrations.CreateModel(
            name='StaticSourceType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('string_id', models.CharField(max_length=64, unique=True, verbose_name='String ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'Source Type',
                'verbose_name_plural': 'Source Types',
                'db_table': 'mocbackend_static_source_type',
            },
        ),
        migrations.AddField(
            model_name='staticconnectiontype',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='connection_types', to='mocbackend.StaticConnectionTypeCategory'),
        ),
        migrations.AddField(
            model_name='stagesource',
            name='source_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sources', to='mocbackend.StaticSourceType'),
        ),
        migrations.AddField(
            model_name='stageentityentity',
            name='connection_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='connections', to='mocbackend.StaticConnectionType'),
        ),
        migrations.AddField(
            model_name='stageentityentity',
            name='entity_a',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reverse_connections', to='mocbackend.StageEntity', verbose_name='Entity'),
        ),
        migrations.AddField(
            model_name='stageentityentity',
            name='entity_b',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections', to='mocbackend.StageEntity', verbose_name='Entity'),
        ),
        migrations.AddField(
            model_name='stageentityentity',
            name='from_collections',
            field=models.ManyToManyField(related_name='entity_entities', through='mocbackend.StageEntityEntityCollection', to='mocbackend.StageCollection'),
        ),
        migrations.AddField(
            model_name='stageentityentity',
            name='transaction_currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='connections', to='mocbackend.StaticCurrency'),
        ),
        migrations.AddField(
            model_name='stageentity',
            name='entity_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entities', to='mocbackend.StaticEntityType'),
        ),
        migrations.AddField(
            model_name='stagecollection',
            name='collection_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='collections', to='mocbackend.StaticCollectionType'),
        ),
        migrations.AddField(
            model_name='stagecollection',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collections', to='mocbackend.StageSource'),
        ),
        migrations.AlterIndexTogether(
            name='stagecodebook',
            index_together=set([('deleted', 'published', 'string_id'), ('deleted', 'published', 'id')]),
        ),
        migrations.AddField(
            model_name='stageattributevaluecollection',
            name='collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attribute_value_collections', to='mocbackend.StageCollection'),
        ),
        migrations.AddField(
            model_name='stageattributevalue',
            name='entity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attribute_values', to='mocbackend.StageEntity'),
        ),
        migrations.AddField(
            model_name='stageattributevalue',
            name='entity_entity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attribute_values', to='mocbackend.StageEntityEntity'),
        ),
        migrations.AddField(
            model_name='stageattributevalue',
            name='from_collections',
            field=models.ManyToManyField(related_name='attribute_values', through='mocbackend.StageAttributeValueCollection', to='mocbackend.StageCollection'),
        ),
        migrations.AddField(
            model_name='stageattributevalue',
            name='value_codebook_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_values', to='mocbackend.StageCodebookValue'),
        ),
        migrations.AddField(
            model_name='stageattributetype',
            name='codebook',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_types', to='mocbackend.StageCodebook'),
        ),
        migrations.AddField(
            model_name='stageattributetype',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_types', to='mocbackend.StaticCurrency'),
        ),
        migrations.AddField(
            model_name='stageattributetype',
            name='data_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attribute_types', to='mocbackend.StaticDataType'),
        ),
        migrations.AddField(
            model_name='stageattribute',
            name='attribute_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attributes', to='mocbackend.StageAttributeType'),
        ),
        migrations.AddField(
            model_name='stageattribute',
            name='collection',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attributes', to='mocbackend.StageCollection'),
        ),
        migrations.AddField(
            model_name='stageattribute',
            name='entity_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attributes', to='mocbackend.StaticEntityType'),
        ),
        migrations.AddField(
            model_name='logentityentitychange',
            name='change_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entity_entity_changes', to='mocbackend.StaticChangeType'),
        ),
        migrations.AddField(
            model_name='logentityentitychange',
            name='changeset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entity_entity_changes', to='mocbackend.LogChangeset'),
        ),
        migrations.AddField(
            model_name='logentityentitychange',
            name='connection_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entity_entity_changes', to='mocbackend.StaticConnectionType'),
        ),
        migrations.AddField(
            model_name='logentityentitychange',
            name='entity_a',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reverse_entity_entity_changes', to='mocbackend.StageEntity', verbose_name='Entity'),
        ),
        migrations.AddField(
            model_name='logentityentitychange',
            name='entity_b',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entity_entity_changes', to='mocbackend.StageEntity', verbose_name='Entity'),
        ),
        migrations.AddField(
            model_name='logentityentitychange',
            name='transaction_currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='entity_entity_changes', to='mocbackend.StaticCurrency'),
        ),
        migrations.AddField(
            model_name='logchangeset',
            name='collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='changesets', to='mocbackend.StageCollection'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='attribute',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attribute_value_changes', to='mocbackend.StageAttribute'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='change_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attribute_value_changes', to='mocbackend.StaticChangeType'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='changeset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attribute_value_changes', to='mocbackend.LogChangeset'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='entity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attribute_value_changes', to='mocbackend.StageEntity'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='entity_entity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attribute_value_changes', to='mocbackend.StageEntityEntity'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='new_value_codebook_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_value_changes_codebook_item_new_values', to='mocbackend.StageCodebookValue'),
        ),
        migrations.AddField(
            model_name='logattributevaluechange',
            name='old_value_codebook_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='attribute_value_changes_codebook_item_old_values', to='mocbackend.StageCodebookValue'),
        ),
        migrations.AlterUniqueTogether(
            name='staticconnectiontype',
            unique_together=set([('name', 'reverse_name')]),
        ),
        migrations.AlterIndexTogether(
            name='staticconnectiontype',
            index_together=set([('potentially_pep', 'id'), ('potentially_pep', 'string_id')]),
        ),
        migrations.AlterIndexTogether(
            name='stagesource',
            index_together=set([('deleted', 'published', 'string_id'), ('deleted', 'published', 'id')]),
        ),
        migrations.AlterUniqueTogether(
            name='stageentityentitycollection',
            unique_together=set([('entity_entity', 'collection')]),
        ),
        migrations.AlterIndexTogether(
            name='stageentityentitycollection',
            index_together=set([('deleted', 'published', 'entity_entity', 'collection')]),
        ),
        migrations.AlterUniqueTogether(
            name='stageentityentity',
            unique_together=set([('entity_a', 'entity_b', 'connection_type', 'transaction_amount', 'transaction_currency', 'transaction_date')]),
        ),
        migrations.AlterIndexTogether(
            name='stageentityentity',
            index_together=set([('deleted', 'published', 'entity_a', 'entity_b', 'connection_type'), ('deleted', 'published', 'entity_b', 'entity_a', 'connection_type')]),
        ),
        migrations.AlterIndexTogether(
            name='stageentity',
            index_together=set([('deleted', 'published', 'public_id'), ('force_pep', 'deleted', 'published', 'id'), ('linked_potentially_pep', 'deleted', 'published', 'public_id'), ('deleted', 'published', 'id'), ('force_pep', 'deleted', 'published', 'public_id'), ('linked_potentially_pep', 'deleted', 'published', 'id')]),
        ),
        migrations.AlterIndexTogether(
            name='stagecollection',
            index_together=set([('deleted', 'published', 'string_id'), ('deleted', 'published', 'id')]),
        ),
        migrations.AlterUniqueTogether(
            name='stagecodebookvalue',
            unique_together=set([('codebook', 'value')]),
        ),
        migrations.AlterIndexTogether(
            name='stagecodebookvalue',
            index_together=set([('deleted', 'published', 'codebook'), ('deleted', 'published', 'id'), ('deleted', 'published', 'codebook', 'id')]),
        ),
        migrations.AlterUniqueTogether(
            name='stageattributevaluecollection',
            unique_together=set([('attribute_value', 'collection')]),
        ),
        migrations.AlterIndexTogether(
            name='stageattributevaluecollection',
            index_together=set([('deleted', 'published', 'attribute_value', 'collection')]),
        ),
        migrations.AlterIndexTogether(
            name='stageattributevalue',
            index_together=set([('deleted', 'published', 'attribute', 'entity_entity'), ('deleted', 'published', 'id'), ('deleted', 'published', 'attribute', 'entity')]),
        ),
        migrations.AlterIndexTogether(
            name='stageattributetype',
            index_together=set([('deleted', 'published', 'string_id'), ('deleted', 'published', 'id')]),
        ),
        migrations.AlterUniqueTogether(
            name='stageattribute',
            unique_together=set([('name', 'collection'), ('name', 'entity_type')]),
        ),
        migrations.AlterIndexTogether(
            name='stageattribute',
            index_together=set([('deleted', 'published', 'collection', 'string_id'), ('deleted', 'published', 'entity_type', 'order_number'), ('deleted', 'published', 'string_id'), ('deleted', 'published', 'entity_type', 'id'), ('deleted', 'published', 'entity_type', 'string_id'), ('deleted', 'published', 'id'), ('deleted', 'published', 'collection', 'order_number'), ('deleted', 'published', 'collection', 'id')]),
        ),
        migrations.AlterIndexTogether(
            name='logentityentitychange',
            index_together=set([('deleted', 'published', 'entity_a', 'entity_b', 'connection_type', 'transaction_date', 'transaction_currency', 'transaction_amount'), ('deleted', 'published', 'id')]),
        ),
        migrations.AlterIndexTogether(
            name='logchangeset',
            index_together=set([('deleted', 'published', 'created_at', 'collection')]),
        ),
        migrations.AlterIndexTogether(
            name='logattributevaluechange',
            index_together=set([('deleted', 'published', 'attribute', 'entity_entity'), ('deleted', 'published', 'id'), ('deleted', 'published', 'attribute', 'entity')]),
        ),
    ]
