from itertools import chain

from ckeditor import fields
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.formats import number_format, date_format
from django.utils.timezone import localtime

from mocbackend import helpers, const
from mocbackend.databases import ElasticsearchDB, Neo4jDB


def model_to_dict(instance, fields=None, exclude=None):
    """
    Return a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.
    ``fields`` is an optional list of field names. If provided, return only the
    named.
    ``exclude`` is an optional list of field names. If provided, exclude the
    named from the returned dict, even if they are listed in the ``fields``
    argument.
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        data[f.name] = f.value_from_object(instance)
    return data

class ModelDiffMixin(object):
    __blank_obj_initial = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__initial = self._dict

    @property
    def _dict(self):
        return model_to_dict(self, fields=[field.name for field in self._meta.fields])

    @property
    def diff(self):
        if self._state.adding:
            if self.__blank_obj_initial is None:
                blank_obj = type(self)()
                self.__blank_obj_initial = model_to_dict(blank_obj,
                                                         fields=[field.name for field in blank_obj._meta.fields])
            initial = self.__blank_obj_initial
        else:
            initial = self.__initial
        current = self._dict
        diffs = [(k, (v, current[k])) for k, v in initial.items() if v != current[k]]
        return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return self.diff.keys()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.__initial = self._dict


class StaticChangeType(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = 'mocbackend_static_change_type'
        verbose_name = 'Change Type'
        verbose_name_plural = 'Change Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in self.attribute_value_changes.all():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in self.entity_entity_changes.all():
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)


class StaticCollectionType(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = 'mocbackend_static_collection_type'
        verbose_name = 'Collection Type'
        verbose_name_plural = 'Collection Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        processed_attribute_value_changes = set()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                changeset__collection__collection_type=self):
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__collection__collection_type=self):
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                changeset__collection__collection_type=self):
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)


class StaticConnectionTypeCategory(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = 'mocbackend_static_connection_type_category'
        verbose_name = 'Connection Type Category'
        verbose_name_plural = 'Connection Type Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            es = ElasticsearchDB.get_db()
            es.put_entity_connection_type_category_count_mapping(connection_type_category=self)
        elif has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_connection_type_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        for entity_entity in StageEntityEntity.objects.filter(connection_type__category=self):
            es.q_update_connection(entity_entity=entity_entity, calculate_count=True)
            neo4j.q_update_connection(entity_entity=entity_entity)

    def update_connection_type_index(self):
        es = ElasticsearchDB.get_db()
        for connection_type in self.connection_types.all():
            es.q_update_connection_type(connection_type=connection_type)


class StaticConnectionType(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=128)
    reverse_name = models.CharField(max_length=128)
    potentially_pep = models.BooleanField(default=False)
    category = models.ForeignKey(StaticConnectionTypeCategory, on_delete=models.PROTECT,
                                 related_name='connection_types')

    class Meta:
        db_table = 'mocbackend_static_connection_type'
        index_together = [
            ('potentially_pep', 'id'),
            ('potentially_pep', 'string_id')
        ]
        unique_together = [
            ('name', 'reverse_name')
        ]
        verbose_name = 'Connection Type'
        verbose_name_plural = 'Connection Types'

    def __str__(self):
        return self.name + ' / ' + self.reverse_name

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        has_changed = self.has_changed
        adding = self._state.adding
        old_connection_type = None
        if not adding and 'string_id' in changed_fields:
            old_connection_type = StaticConnectionType.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        if adding:
            es.q_add_connection_type(connection_type=self)
        elif 'string_id' in changed_fields:
            es.q_delete_connection_type(connection_type=old_connection_type)
            es.q_add_connection_type(connection_type=self)
        elif 'name' in changed_fields or 'reverse_name' in changed_fields or 'category' in changed_fields:
            es.q_update_connection_type(connection_type=self)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        es.q_delete_connection_type(connection_type=self)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        for entity_entity in self.connections.all():
            es.q_update_connection(entity_entity=entity_entity, calculate_count=True)
            neo4j.q_update_connection(entity_entity=entity_entity)


class StaticCurrency(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=3, unique=True)
    sign = models.CharField(max_length=8)
    sign_before_value = models.BooleanField(default=False)

    class Meta:
        db_table = 'mocbackend_static_currency'
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        processed_entities = set()
        processed_connections = set()
        for attribute_value in self.attribute_values.all():
            if attribute_value.entity is not None:
                if attribute_value.entity not in processed_entities:
                    processed_entities.add(attribute_value.entity)
                    es.q_update_entity(entity=attribute_value.entity, update_connections=False)
            elif attribute_value.entity_entity is not None:
                if attribute_value.entity_entity not in processed_connections:
                    processed_connections.add(attribute_value.entity_entity)
                    es.q_update_connection(entity_entity=attribute_value.entity_entity, calculate_count=False)
        for entity_entity in self.connections.all():
            if entity_entity not in processed_connections:
                processed_connections.add(entity_entity)
                es.q_update_connection(entity_entity=entity_entity, calculate_count=False)
                neo4j.q_update_connection(entity_entity=entity_entity)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        processed_attribute_value_changes = set()
        for attribute_value_change in self.attribute_value_changes_old_currency.all():
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in self.attribute_value_changes_new_currency.all():
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)


class StaticDataType(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = 'mocbackend_static_data_type'
        verbose_name = 'Data Type'
        verbose_name_plural = 'Data Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)

    def update_attribute_index(self):
        es = ElasticsearchDB.get_db()
        processed_attributes = set()
        for attribute in StageAttribute.objects.filter(attribute_type__data_type=self):
            root_attribute = helpers.get_root_attribute(attribute=attribute)
            if root_attribute not in processed_attributes:
                processed_attributes.add(root_attribute)
                es.q_update_attribute(attribute=root_attribute)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__attribute_type__data_type=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)


class StaticSourceType(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = 'mocbackend_static_source_type'
        verbose_name = 'Source Type'
        verbose_name_plural = 'Source Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        processed_attribute_value_changes = set()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                changeset__collection__source__source_type=self):
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__collection__source__source_type=self):
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                changeset__collection__source__source_type=self):
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)


class StageCodebook(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)
    is_closed = models.BooleanField(default=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_stage_codebook'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'string_id'),
        ]
        verbose_name = 'Codebook'
        verbose_name_plural = 'Codebooks'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attributes, ttl=-1)
        else:
            if not adding and (
                    'string_id' in changed_fields or 'name' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_index, ttl=-1)
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            if not adding:
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_index, ttl=-1)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_codebook_value_index, ttl=-1)

    def delete(self, *args, **kwargs):
        codebook_values = self.codebook_values.all()
        len(codebook_values)
        super().delete(*args, **kwargs)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_codebook_value_index, codebook_values=codebook_values, ttl=-1)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        for entity in StageEntity.objects.filter(attribute_values__value_codebook_item__codebook=self).distinct():
            es.q_update_entity(entity=entity, update_connections=False)
        for entity_entity in StageEntityEntity.objects.filter(
                attribute_values__value_codebook_item__codebook=self).distinct():
            es.q_update_connection(entity_entity=entity_entity, calculate_count=False)
        for entity in StageEntity.objects.filter(attribute_values__attribute__attribute_type__codebook=self,
                                                 attribute_values__attribute__string_id='legal_entity_entity_type').distinct():
            neo4j.q_update_entity(entity=entity, update_connections=False)

    def update_attributes(self):
        for attribute in StageAttribute.objects.filter(attribute_type__codebook=self):
            attribute.save()

    def update_attribute_index(self):
        es = ElasticsearchDB.get_db()
        processed_attributes = set()
        for attribute in StageAttribute.objects.filter(attribute_type__codebook=self):
            root_attribute = helpers.get_root_attribute(attribute=attribute)
            if root_attribute not in processed_attributes:
                processed_attributes.add(root_attribute)
                es.q_update_attribute(attribute=root_attribute)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__attribute_type__codebook=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        '''
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                old_value_codebook_item__codebook=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                new_value_codebook_item__codebook=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        '''

    def update_codebook_value_index(self):
        es = ElasticsearchDB.get_db()
        for codebook_value in self.codebook_values.all():
            es.q_update_codebook_value(codebook_value=codebook_value)

    def delete_codebook_value_index(self, codebook_values):
        es = ElasticsearchDB.get_db()
        for codebook_value in codebook_values:
            es.q_delete_codebook_value(codebook_value=codebook_value)


class StageSource(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(null=True, blank=True)
    source_type = models.ForeignKey(StaticSourceType, on_delete=models.PROTECT, related_name='sources')
    address = models.CharField(max_length=64, null=True, blank=True)
    quality = models.SmallIntegerField(default=0)
    contact = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    last_in_log = models.DateTimeField(null=True, default=None, blank=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_stage_source'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'string_id'),
        ]
        verbose_name = 'Source'
        verbose_name_plural = 'Sources'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attributes, ttl=-1)
        else:
            if not adding and (
                    'string_id' in changed_fields or 'name' in changed_fields or 'source_type' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_value_log_index2, ttl=-1)
            if not adding and (
                    'string_id' in changed_fields or 'name' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_index, ttl=-1)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields or 'description' in changed_fields or 'quality' in changed_fields or 'source_type' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index3, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index3, ttl=-1)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def delete(self, *args, **kwargs):
        collections = self.collections.all().prefetch_related(Prefetch('attribute_value_collections')).prefetch_related(
            'entity_entity_collections')
        len(collections)
        attribute_value_changes = LogAttributeValueChange.objects.filter(changeset__collection__source=self)
        len(attribute_value_changes)
        entity_entity_changes = LogEntityEntityChange.objects.filter(changeset__collection__source=self)
        len(entity_entity_changes)
        super().delete(*args, **kwargs)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.update_index, collections=collections, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_entity_entity_log_index, entity_entity_changes=entity_entity_changes, ttl=-1)

    def update_index(self, collections=None):
        if collections is None:
            collections = self.collections.all().prefetch_related(
                Prefetch('attribute_value_collections')).prefetch_related('entity_entity_collections')
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        processed_entities = set()
        processed_connections = set()
        neo4j_attributes = ['person_first_name', 'person_last_name', 'legal_entity_name', 'legal_entity_entity_type',
                            'real_estate_name', 'movable_name', 'savings_name']
        for collection in collections:
            for attribute_value_collection in collection.attribute_value_collections.all():
                if attribute_value_collection.attribute_value.entity is not None:
                    if attribute_value_collection.attribute_value.entity not in processed_entities:
                        processed_entities.add(attribute_value_collection.attribute_value.entity)
                        es.q_update_entity(entity=attribute_value_collection.attribute_value.entity,
                                           update_connections=False)
                        if attribute_value_collection.attribute_value.attribute.string_id in neo4j_attributes:
                            neo4j.q_update_entity(entity=attribute_value_collection.attribute_value.entity,
                                                  update_connections=False)
                elif attribute_value_collection.attribute_value.entity_entity is not None:
                    if attribute_value_collection.attribute_value.entity_entity not in processed_connections:
                        processed_connections.add(attribute_value_collection.attribute_value.entity_entity)
                        es.q_update_connection(entity_entity=attribute_value_collection.attribute_value.entity_entity,
                                               calculate_count=False)
            for entity_entity_collection in collection.entity_entity_collections.all():
                if entity_entity_collection.entity_entity not in processed_connections:
                    processed_connections.add(entity_entity_collection.entity_entity)
                    es.q_update_connection(entity_entity=entity_entity_collection.entity_entity, calculate_count=True)
                    neo4j.q_update_connection(entity_entity=entity_entity_collection.entity_entity)

    def update_attributes(self):
        for attribute in StageAttribute.objects.filter(collection=self):
            attribute.save()

    def update_attribute_index(self):
        es = ElasticsearchDB.get_db()
        for attribute in StageAttribute.objects.filter(collection__source=self, attribute=None):
            es.q_update_attribute(attribute=attribute)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                changeset__collection__source=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_attribute_value_log_index2(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__collection__source=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_attribute_value_log_index3(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                entity_entity__entity_entity_collections__collection__source=self).distinct():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_delete_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                changeset__collection__source=self):
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def update_entity_entity_log_index3(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                entity_entity__entity_entity_collections__collection__source=self).distinct():
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def delete_entity_entity_log_index(self, entity_entity_changes):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in entity_entity_changes:
            es.q_delete_entity_entity_change(entity_entity_change=entity_entity_change)


class StageCodebookValue(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    codebook = models.ForeignKey(StageCodebook, on_delete=models.CASCADE, related_name='codebook_values',
                                 limit_choices_to=Q(deleted=False))
    value = models.CharField(max_length=512)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_stage_codebook_value'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'codebook'),
            ('deleted', 'published', 'codebook', 'id'),
        ]
        unique_together = [
            ('codebook', 'value')
        ]
        verbose_name = 'Codebook Value'
        verbose_name_plural = 'Codebooks Values'

    def __str__(self):
        return self.value

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)
        if adding:
            es.q_add_codebook_value(codebook_value=self)
        elif has_changed:
            es.q_update_codebook_value(codebook_value=self)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        processed_entities = set()
        processed_connections = set()
        for attribute_value in self.attribute_values.all():
            if attribute_value.entity is not None:
                if attribute_value.entity not in processed_entities:
                    processed_entities.add(attribute_value.entity)
                    es.q_update_entity(entity=attribute_value.entity, update_connections=False)
                    if attribute_value.attribute.string_id == 'legal_entity_entity_type':
                        neo4j.q_update_entity(entity=attribute_value.entity, update_connections=False)
            elif attribute_value.entity_entity is not None:
                if attribute_value.entity_entity not in processed_connections:
                    processed_connections.add(attribute_value.entity_entity)
                    es.q_update_connection(entity_entity=attribute_value.entity_entity, calculate_count=False)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        processed_attribute_value_changes = set()
        for attribute_value_change in self.attribute_value_changes_codebook_item_old_values.all():
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in self.attribute_value_changes_codebook_item_new_values.all():
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)


class StageCollection(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)
    source = models.ForeignKey(StageSource, on_delete=models.CASCADE, related_name='collections',
                               limit_choices_to=Q(deleted=False))
    collection_type = models.ForeignKey(StaticCollectionType, on_delete=models.PROTECT, related_name='collections')
    description = models.TextField(null=True, blank=True)
    quality = models.SmallIntegerField(default=0)
    last_in_log = models.DateTimeField(null=True, default=None, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_stage_collection'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'string_id'),
            ('deleted', 'published', 'source'),
        ]
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        adding = self._state.adding
        old_source = None
        if not adding and 'source' in changed_fields:
            old_source = StageCollection.objects.get(pk=self.pk).source
        super().save(*args, **kwargs)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields or old_source is not None):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_last_in_log_on_update, old_source=old_source, ttl=-1)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attributes, ttl=-1)
        else:
            if not adding and (
                    'string_id' in changed_fields or 'name' in changed_fields or 'collection_type' in changed_fields or 'source' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_value_log_index2, ttl=-1)
            if not adding and (
                    'string_id' in changed_fields or 'name' in changed_fields or 'source' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_index, ttl=-1)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields or 'description' in changed_fields or 'quality' in changed_fields or 'collection_type' in changed_fields or 'source' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index3, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index3, ttl=-1)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields or 'source' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def delete(self, *args, **kwargs):
        attribute_value_collections = self.attribute_value_collections.all()
        len(attribute_value_collections)
        entity_entity_collections = self.entity_entity_collections.all()
        len(entity_entity_collections)
        attribute_value_changes = LogAttributeValueChange.objects.filter(changeset__collection=self)
        len(attribute_value_changes)
        entity_entity_changes = LogEntityEntityChange.objects.filter(changeset__collection=self)
        len(entity_entity_changes)
        source = self.source
        super().delete(*args, **kwargs)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.update_last_in_log_on_delete, source=source, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.update_index, attribute_value_collections=attribute_value_collections,
                      entity_entity_collections=entity_entity_collections, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_entity_entity_log_index, entity_entity_changes=entity_entity_changes, ttl=-1)

    def update_last_in_log_on_update(self, old_source):
        source = self.source
        if not self.deleted and self.published:
            if self.last_in_log is not None and (
                    source.last_in_log is None or self.last_in_log > source.last_in_log):
                source.last_in_log = self.last_in_log
        else:
            for collection in source.collections.filter(deleted=False, published=True):
                if collection.last_in_log is not None and (
                        source.last_in_log is None or collection.last_in_log > source.last_in_log):
                    source.last_in_log = collection.last_in_log

        if source.has_changed:
            source.save()

        if old_source is not None:
            for collection in old_source.collections.filter(deleted=False, published=True):
                if collection.last_in_log is not None and (
                        old_source.last_in_log is None or collection.last_in_log > old_source.last_in_log):
                    old_source.last_in_log = collection.last_in_log

            if old_source.has_changed:
                old_source.save()

    def update_last_in_log_on_delete(self, source):
        for collection in source.collections.filter(deleted=False, published=True):
            if collection.last_in_log is not None and (
                    source.last_in_log is None or collection.last_in_log > source.last_in_log):
                source.last_in_log = collection.last_in_log

        if source.has_changed:
            source.save()

    def update_index(self, attribute_value_collections=None, entity_entity_collections=None):
        if attribute_value_collections is None:
            attribute_value_collections = self.attribute_value_collections.all()
        if entity_entity_collections is None:
            entity_entity_collections = self.entity_entity_collections.all()
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        processed_entities = set()
        processed_connections = set()
        neo4j_attributes = ['person_first_name', 'person_last_name', 'legal_entity_name', 'legal_entity_entity_type',
                            'real_estate_name', 'movable_name', 'savings_name']
        for attribute_value_collection in attribute_value_collections:
            if attribute_value_collection.attribute_value.entity is not None:
                if attribute_value_collection.attribute_value.entity not in processed_entities:
                    processed_entities.add(attribute_value_collection.attribute_value.entity)
                    es.q_update_entity(entity=attribute_value_collection.attribute_value.entity,
                                       update_connections=False)
                    if attribute_value_collection.attribute_value.attribute.string_id in neo4j_attributes:
                        neo4j.q_update_entity(entity=attribute_value_collection.attribute_value.entity,
                                              update_connections=False)
            elif attribute_value_collection.attribute_value.entity_entity is not None:
                if attribute_value_collection.attribute_value.entity_entity not in processed_connections:
                    processed_connections.add(attribute_value_collection.attribute_value.entity_entity)
                    es.q_update_connection(entity_entity=attribute_value_collection.attribute_value.entity_entity,
                                           calculate_count=False)
        for entity_entity_collection in entity_entity_collections:
            if entity_entity_collection.entity_entity not in processed_connections:
                processed_connections.add(entity_entity_collection.entity_entity)
                es.q_update_connection(entity_entity=entity_entity_collection.entity_entity, calculate_count=True)
                neo4j.q_update_connection(entity_entity=entity_entity_collection.entity_entity)

    def update_attributes(self):
        for attribute in StageAttribute.objects.filter(collection=self):
            attribute.save()

    def update_attribute_index(self):
        es = ElasticsearchDB.get_db()
        for attribute in self.attributes.filter(attribute=None):
            es.q_update_attribute(attribute=attribute)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                changeset__collection=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_attribute_value_log_index2(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__collection=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_attribute_value_log_index3(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                entity_entity__entity_entity_collections__collection=self).distinct():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_delete_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                changeset__collection=self):
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def update_entity_entity_log_index3(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                entity_entity__entity_entity_collections__collection=self).distinct():
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def delete_entity_entity_log_index(self, entity_entity_changes):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in entity_entity_changes:
            es.q_delete_entity_entity_change(entity_entity_change=entity_entity_change)


class LogChangeset(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    collection = models.ForeignKey(StageCollection, on_delete=models.CASCADE, related_name='changesets',
                                   limit_choices_to=Q(deleted=False, source__deleted=False))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_log_changeset'
        index_together = [
            ('deleted', 'published', 'created_at', 'collection'),
            ('deleted', 'published', 'collection', 'created_at', 'id'),
        ]
        verbose_name = 'Changeset'
        verbose_name_plural = 'Changesets'

    def __str__(self):
        return date_format(localtime(self.created_at), 'DATETIME_FORMAT') + ', ' + self.collection.name

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        has_changed = self.has_changed
        adding = self._state.adding
        old_collection = None
        if not adding and 'collection' in changed_fields:
            old_collection = LogChangeset.objects.get(pk=self.pk).collection
        super().save(*args, **kwargs)
        if adding:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_last_in_log_on_create, ttl=-1)
        else:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_last_in_log_on_update, old_collection=old_collection, ttl=-1)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)

    def delete(self, *args, **kwargs):
        collection = self.collection
        attribute_value_changes = LogAttributeValueChange.objects.filter(changeset=self)
        len(attribute_value_changes)
        entity_entity_changes = LogEntityEntityChange.objects.filter(changeset=self)
        len(entity_entity_changes)
        super().delete(*args, **kwargs)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.update_last_in_log_on_delete, collection=collection, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_entity_entity_log_index, entity_entity_changes=entity_entity_changes, ttl=-1)

    def update_last_in_log_on_create(self):
        if not self.deleted and self.published:
            collection = self.collection
            if collection.last_in_log is None or self.created_at > collection.last_in_log:
                collection.last_in_log = self.created_at
                collection.save()
            source = collection.source
            if source.last_in_log is None or self.created_at > source.last_in_log:
                source.last_in_log = self.created_at
                source.save()

    def update_last_in_log_on_update(self, old_collection):
        collection = self.collection
        source = collection.source
        if not self.deleted and self.published:
            if collection.last_in_log is None or self.created_at > collection.last_in_log:
                collection.last_in_log = self.created_at
                collection.save()
            if source.last_in_log is None or self.created_at > source.last_in_log:
                source.last_in_log = self.created_at
                source.save()
        else:
            latest = LogChangeset.objects.filter(deleted=False, published=True, collection=collection).order_by(
                '-created_at', '-id').first()

            collection.last_in_log = latest if latest is None else latest.created_at
            collection.save()

            for collection in source.collections.filter(deleted=False, published=True):
                if collection.last_in_log is not None and (
                        source.last_in_log is None or collection.last_in_log > source.last_in_log):
                    source.last_in_log = collection.last_in_log

            if source.has_changed:
                source.save()

        if old_collection is not None:
            latest = LogChangeset.objects.filter(deleted=False, published=True,
                                                 collection=old_collection).order_by('-created_at',
                                                                                     '-id').first()
            old_collection.last_in_log = latest if latest is None else latest.created_at
            old_collection.save()

            old_source = old_collection.source
            for collection in old_source.collections.filter(deleted=False, published=True):
                if collection.last_in_log is not None and (
                        old_source.last_in_log is None or collection.last_in_log > old_source.last_in_log):
                    old_source.last_in_log = collection.last_in_log

            if old_source.has_changed:
                old_source.save()

    def update_last_in_log_on_delete(self, collection):
        source = collection.source
        latest = LogChangeset.objects.filter(deleted=False, published=True, collection=collection).order_by(
            '-created_at', '-id').first()

        collection.last_in_log = latest if latest is None else latest.created_at
        collection.save()

        for collection in source.collections.filter(deleted=False, published=True):
            if collection.last_in_log is not None and (
                    source.last_in_log is None or collection.last_in_log > source.last_in_log):
                source.last_in_log = collection.last_in_log

        if source.has_changed:
            source.save()

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in self.attribute_value_changes.all():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_delete_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in self.entity_entity_changes.all():
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def delete_entity_entity_log_index(self, entity_entity_changes):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in entity_entity_changes:
            es.q_delete_entity_entity_change(entity_entity_change=entity_entity_change)


class StageAttributeType(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)
    data_type = models.ForeignKey(StaticDataType, on_delete=models.PROTECT, related_name='attribute_types')
    is_multivalue = models.BooleanField(default=False)
    codebook = models.ForeignKey(StageCodebook, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='attribute_types', limit_choices_to=Q(deleted=False))
    permited_values = models.TextField(null=True, blank=True)
    fixed_point_decimal_places = models.PositiveSmallIntegerField(null=True, blank=True)
    range_floating_point_from_inclusive = models.NullBooleanField(null=True, blank=True)
    range_floating_point_to_inclusive = models.NullBooleanField(null=True, blank=True)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted', db_index=True)

    class Meta:
        db_table = 'mocbackend_stage_attribute_type'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'string_id'),
        ]
        verbose_name = 'Attribute Type'
        verbose_name_plural = 'Attribute Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and ('published' in changed_fields or 'deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attributes, ttl=-1)
        else:
            if not adding and (
                    'string_id' in changed_fields or 'name' in changed_fields or 'data_type' in changed_fields or 'codebook' in changed_fields or 'fixed_point_decimal_places' in changed_fields or 'range_floating_point_from_inclusive' in changed_fields or 'range_floating_point_to_inclusive' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_index, ttl=-1)
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            if not adding and ('data_type' in changed_fields):
                queue = helpers.get_queue(queue='db', default_timeout='60m')
                queue.enqueue(self.update_index, ttl=-1)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        for entity in StageEntity.objects.filter(attribute_values__attribute__attribute_type=self).distinct():
            es.q_update_entity(entity=entity, update_connections=False)
        for entity_entity in StageEntityEntity.objects.filter(
                attribute_values__attribute__attribute_type=self).distinct():
            es.q_update_connection(entity_entity=entity_entity, calculate_count=False)

        for entity in StageEntity.objects.filter(
                Q(attribute_values__attribute__attribute_type=self) & (
                        Q(attribute_values__attribute__string_id='legal_entity_entity_type') | Q(
                    attribute_values__attribute__string_id='person_first_name') | Q(
                    attribute_values__attribute__string_id='person_last_name') | Q(
                    attribute_values__attribute__string_id='legal_entity_name') | Q(
                    attribute_values__attribute__string_id='real_estate_name') | Q(
                    attribute_values__attribute__string_id='movable_name') | Q(
                    attribute_values__attribute__string_id='savings_name'))).distinct():
            neo4j.q_update_entity(entity=entity, update_connections=False)

    def update_attributes(self):
        for attribute in self.attributes.all():
            attribute.save()

    def update_attribute_index(self):
        es = ElasticsearchDB.get_db()
        processed_attributes = set()
        for attribute in self.attributes.all():
            root_attribute = helpers.get_root_attribute(attribute=attribute)
            if root_attribute not in processed_attributes:
                processed_attributes.add(root_attribute)
                es.q_update_attribute(attribute=attribute)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__attribute_type=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)


class StaticEntityType(ModelDiffMixin, models.Model):
    id = models.AutoField(primary_key=True)
    string_id = models.CharField(max_length=64, unique=True, verbose_name='String ID')
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = 'mocbackend_static_entity_type'
        verbose_name = 'Entity Type'
        verbose_name_plural = 'Entity Types'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and has_changed:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def update_index(self):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        for entity in self.entities.all():
            es.q_update_entity(entity=entity, update_connections=True)
            neo4j.q_update_entity(entity=entity, update_connections=False)

    def update_attribute_index(self):
        es = ElasticsearchDB.get_db()
        for attribute in self.attributes.all():
            es.q_update_attribute(attribute=attribute)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                attribute__entity_type=self):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)


class StageAttribute(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    string_id = models.CharField(max_length=64, verbose_name='String ID', unique=True)
    name = models.CharField(max_length=128)
    entity_type = models.ForeignKey(StaticEntityType, on_delete=models.PROTECT, related_name='attributes', null=True,
                                    blank=True)
    collection = models.ForeignKey(StageCollection, on_delete=models.PROTECT, related_name='attributes',
                                   limit_choices_to=Q(deleted=False, source__deleted=False), null=True, blank=True)
    attribute = models.ForeignKey('StageAttribute', on_delete=models.CASCADE, related_name='attributes',
                                  limit_choices_to=Q(finally_deleted=False,
                                                     attribute_type__data_type__string_id='complex'), null=True,
                                  blank=True)
    attribute_type = models.ForeignKey(StageAttributeType, on_delete=models.PROTECT, related_name='attributes',
                                       limit_choices_to=Q(deleted=False) & (
                                               Q(codebook=None) | Q(codebook__deleted=False)))
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    default_value = models.CharField(max_length=512, null=True, blank=True)
    order_number = models.IntegerField(default=10000, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')
    all_parents_published = models.BooleanField(default=True, editable=False)
    any_parent_deleted = models.BooleanField(default=False, editable=False)
    all_related_published = models.BooleanField(default=True, editable=False)
    any_related_deleted = models.BooleanField(default=False, editable=False)
    all_parents_all_related_published = models.BooleanField(default=True, editable=False)
    any_parent_any_related_deleted = models.BooleanField(default=False, editable=False)
    finally_published = models.BooleanField(default=True, editable=False)
    finally_deleted = models.BooleanField(default=False, editable=False)

    _parent_saved = False

    class Meta:
        db_table = 'mocbackend_stage_attribute'
        index_together = [
            ('finally_deleted', 'finally_published', 'id'),
            ('finally_deleted', 'finally_published', 'string_id'),
            ('finally_deleted', 'finally_published', 'entity_type', 'id'),
            ('finally_deleted', 'finally_published', 'entity_type', 'string_id'),
            ('finally_deleted', 'finally_published', 'collection', 'id'),
            ('finally_deleted', 'finally_published', 'collection', 'string_id'),
            ('finally_deleted', 'finally_published', 'attribute', 'id'),
            ('finally_deleted', 'finally_published', 'attribute', 'string_id'),
            ('finally_deleted', 'finally_published', 'entity_type', 'order_number'),
            ('finally_deleted', 'finally_published', 'collection', 'order_number'),
            ('finally_deleted', 'finally_published', 'attribute', 'order_number'),
            ('finally_deleted', 'finally_published', 'order_number'),
            ('finally_deleted', 'string_id', 'attribute', 'attribute_type'),
            ('string_id', 'attribute'),
            ('entity_type', 'attribute_type'),
            ('collection', 'attribute'),
        ]
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.any_related_deleted = self.attribute_type.deleted or (
                self.attribute_type.codebook is not None and self.attribute_type.codebook.deleted) or (
                                           self.collection is not None and (
                                           self.collection.deleted or self.collection.source.deleted))
        self.all_related_published = self.attribute_type.published and (
                self.attribute_type.codebook is None or self.attribute_type.codebook.published) and (
                                             self.collection is None or (
                                             self.collection.published and self.collection.source.published))
        if self.attribute is not None:
            self.any_parent_deleted = self.attribute.deleted or self.attribute.any_parent_deleted
            self.all_parents_published = self.attribute.published and self.attribute.all_parents_published
            self.any_parent_any_related_deleted = self.attribute.any_related_deleted or self.attribute.any_parent_any_related_deleted
            self.all_parents_all_related_published = self.attribute.all_related_published and self.attribute.all_parents_all_related_published
        else:
            self.any_parent_deleted = False
            self.all_parents_published = True
            self.any_parent_any_related_deleted = False
            self.all_parents_all_related_published = True
        self.finally_deleted = self.deleted or self.any_parent_deleted or self.any_related_deleted or self.any_parent_any_related_deleted
        self.finally_published = self.published and self.all_parents_published and self.all_related_published and self.all_parents_all_related_published
        changed_fields = self.changed_fields
        adding = self._state.adding
        old_attribute = None
        if not adding and ('attribute' in changed_fields or ('string_id' in changed_fields and self.attribute is None)):
            old_attribute = StageAttribute.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.subsave, adding=adding, changed_fields=list(changed_fields), old_attribute=old_attribute, ttl=-1)

    def subsave(self, adding, changed_fields, old_attribute):
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'any_parent_deleted' in changed_fields or 'all_parents_published' in changed_fields or 'all_related_published' in changed_fields or 'any_related_deleted' in changed_fields or 'all_parents_all_related_published' in changed_fields or 'any_parent_any_related_deleted' in changed_fields or 'finally_published' in changed_fields or 'finally_deleted' in changed_fields):
            for attribute in self.attributes.all():
                attribute.any_parent_deleted = self.deleted or self.any_parent_deleted
                attribute.all_parents_published = self.published and self.all_parents_published
                attribute.any_parent_any_related_deleted = self.any_related_deleted or self.any_parent_any_related_deleted
                attribute.all_parents_all_related_published = self.all_related_published and self.all_parents_all_related_published
                attribute.finally_deleted = attribute.deleted or attribute.any_parent_deleted or attribute.any_related_deleted or attribute.any_parent_any_related_deleted
                attribute.finally_published = attribute.published and attribute.all_parents_published and attribute.all_related_published and attribute.all_parents_all_related_published
                attribute._parent_saved = True
                attribute.save()
        es = ElasticsearchDB.get_db()
        if adding:
            es.q_add_attribute(attribute=self)
            es.put_attribute_mapping(attribute=self)
        if not adding and not self._parent_saved and (
                'published' in changed_fields or 'deleted' in changed_fields or 'any_parent_deleted' in changed_fields or 'all_parents_published' in changed_fields or 'all_related_published' in changed_fields or 'any_related_deleted' in changed_fields or 'all_parents_all_related_published' in changed_fields or 'any_parent_any_related_deleted' in changed_fields or 'finally_published' in changed_fields or 'finally_deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields or 'entity_type' in changed_fields or 'collection' in changed_fields or 'attribute' in changed_fields or 'attribute_type' in changed_fields or 'order_number' in changed_fields):
            if old_attribute is not None:
                if 'attribute' in changed_fields:
                    if old_attribute.attribute is not None and self.attribute is not None:
                        es.q_update_attribute(attribute=old_attribute)
                        es.q_update_attribute(attribute=self)
                    elif old_attribute.attribute is None and self.attribute is not None:
                        es.q_delete_attribute(attribute=old_attribute)
                        es.q_update_attribute(attribute=self)
                    elif old_attribute.attribute is not None and self.attribute is None:
                        es.q_update_attribute(attribute=old_attribute)
                        es.q_add_attribute(attribute=self)
                elif 'string_id' and changed_fields and self.attribute is None:
                    es.q_delete_attribute(attribute=old_attribute)
                    es.q_add_attribute(attribute=self)
            else:
                es.q_update_attribute(attribute=self)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'any_parent_deleted' in changed_fields or 'all_parents_published' in changed_fields or 'all_related_published' in changed_fields or 'any_related_deleted' in changed_fields or 'all_parents_all_related_published' in changed_fields or 'any_parent_any_related_deleted' in changed_fields or 'finally_published' in changed_fields or 'finally_deleted' in changed_fields or 'string_id' in changed_fields or 'name' in changed_fields or 'entity_type' in changed_fields or 'collection' in changed_fields or 'attribute_type' in changed_fields or 'order_number' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
        if not self._parent_saved and (
                'published' in changed_fields or 'deleted' in changed_fields or 'any_parent_deleted' in changed_fields or 'all_parents_published' in changed_fields or 'all_related_published' in changed_fields or 'any_related_deleted' in changed_fields or 'all_parents_all_related_published' in changed_fields or 'any_parent_any_related_deleted' in changed_fields or 'finally_published' in changed_fields or 'finally_deleted' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_index, ttl=-1)

    def delete(self, *args, **kwargs):
        attribute_values_array = StageAttribute.get_attribute_values_as_list(attribute=self)
        root_attribute = helpers.get_root_attribute(self)
        attributes_list = StageAttribute.get_all_subattributes_as_list(attribute=self) + [self]
        attribute_value_changes = LogAttributeValueChange.objects.filter(attribute__in=attributes_list)
        len(attribute_value_changes)
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        es.delete_attribute_mapping(attribute=self)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.update_index_delete, attribute_values_array=attribute_values_array, ttl=-1)
        if self.attribute is None:
            es.q_delete_attribute(attribute=self)
        else:
            es.q_update_attribute(attribute=root_attribute)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)

    @staticmethod
    def get_all_subattributes_as_list(attribute):
        ret = []
        sub_attributes = attribute.attributes.all()
        if len(sub_attributes) > 0:
            ret = list(sub_attributes)
            for inner_attribute in attribute.attributes.all():
                ret = ret + StageAttribute.get_all_subattributes_as_list(attribute=inner_attribute)
        return ret

    @staticmethod
    def get_attribute_values_as_list(attribute):
        ret = []
        attribute_values = attribute.attribute_values.all()
        if len(attribute_values) > 0:
            ret = list(attribute_values)
        for subattribute in attribute.attributes.all():
            ret = ret + StageAttribute.get_attribute_values_as_list(attribute=subattribute)
        return ret

    def update_index(self):
        attribute_values_array = StageAttribute.get_attribute_values_as_list(attribute=self)
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        processed_entities = set()
        processed_connections = set()
        neo4j_attributes = ['person_first_name', 'person_last_name', 'legal_entity_name', 'legal_entity_entity_type',
                            'real_estate_name', 'movable_name', 'savings_name']
        for attribute_value in attribute_values_array:
            if attribute_value.entity is not None:
                if attribute_value.entity not in processed_entities:
                    processed_entities.add(attribute_value.entity)
                    es.q_update_entity(entity=attribute_value.entity, update_connections=False)
                    if attribute_value.attribute in neo4j_attributes:
                        neo4j.q_update_entity(entity=attribute_value.entity, update_connections=False)
            elif attribute_value.entity_entity is not None:
                if attribute_value.entity_entity not in processed_connections:
                    processed_connections.add(attribute_value.entity_entity)
                    es.q_update_connection(entity_entity=attribute_value.entity_entity, calculate_count=False)

    def update_index_delete(self, attribute_values_array):
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        processed_entities = set()
        processed_connections = set()
        neo4j_attributes = ['person_first_name', 'person_last_name', 'legal_entity_name', 'legal_entity_entity_type',
                            'real_estate_name', 'movable_name', 'savings_name']
        for attribute_value in attribute_values_array:
            if attribute_value.entity is not None:
                if attribute_value.entity not in processed_entities:
                    processed_entities.add(attribute_value.entity)
                    es.q_update_entity(entity=attribute_value.entity, update_connections=False)
                    if attribute_value.attribute.string_id in neo4j_attributes:
                        neo4j.q_update_entity(entity=attribute_value.entity, update_connections=False)
            elif attribute_value.entity_entity is not None:
                if attribute_value.entity_entity not in processed_connections:
                    processed_connections.add(attribute_value.entity_entity)
                    es.q_update_connection(entity_entity=attribute_value.entity_entity, calculate_count=False)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in self.attribute_value_changes.all():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_delete_attribute_value_change(attribute_value_change=attribute_value_change)


class StageEntity(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(max_length=128, unique=True, verbose_name='Public ID')
    entity_type = models.ForeignKey(StaticEntityType, on_delete=models.PROTECT, related_name='entities')
    linked_potentially_pep = models.BooleanField(default=False)
    force_pep = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, db_index=True, verbose_name='Soft Deleted')
    internal_slug = models.CharField(max_length=128, db_index=True)
    internal_slug_count = models.BigIntegerField()

    _save_only_in_db = True

    class Meta:
        db_table = 'mocbackend_stage_entity'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'public_id'),
            ('linked_potentially_pep', 'deleted', 'published', 'id'),
            ('linked_potentially_pep', 'deleted', 'published', 'public_id'),
            ('force_pep', 'deleted', 'published', 'id'),
            ('force_pep', 'deleted', 'published', 'public_id'),
        ]
        unique_together = [
            ('internal_slug', 'internal_slug_count'),
        ]
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'

    def __str__(self):
        return self.public_id

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and 'published' in changed_fields or 'deleted' in changed_fields or 'public_id' in changed_fields:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
        if not adding and 'published' in changed_fields or 'deleted' in changed_fields:
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)
        if not self._save_only_in_db:
            es = ElasticsearchDB.get_db()
            neo4j = Neo4jDB.get_db()
            if adding:
                es.q_add_entity(entity=self, overwrite=False, add_connections=True)
                neo4j.q_add_entity(entity=self, overwrite=False, add_connections=True)
            elif 'published' in changed_fields or 'deleted' in changed_fields or 'public_id' in changed_fields or 'entity_type' in changed_fields or 'linked_potentially_pep' in changed_fields or 'force_pep' in changed_fields:
                es.q_update_entity(entity=self, update_connections=True)
                neo4j.q_update_entity(entity=self, update_connections=False)

    def delete(self, *args, **kwargs):
        attribute_value_changes = LogAttributeValueChange.objects.filter(entity=self)
        len(attribute_value_changes)
        attribute_value_changes2 = LogAttributeValueChange.objects.filter(
            Q(entity_entity__entity_a=self) | Q(entity_entity__entity_b=self))
        len(attribute_value_changes2)
        entity_entity_changes = LogEntityEntityChange.objects.filter(
            Q(entity_entity__entity_a=self) | Q(entity_entity__entity_b=self))
        len(entity_entity_changes)
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        es.q_delete_entity(entity=self, delete_all=True)
        neo4j.q_delete_entity(entity=self)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes2, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_entity_entity_log_index, entity_entity_changes=entity_entity_changes, ttl=-1)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in self.attribute_value_changes.all():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                Q(entity_entity__entity_a=self) | Q(entity_entity__entity_b=self)):
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_delete_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                Q(entity_entity__entity_a=self) | Q(entity_entity__entity_b=self)):
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def delete_entity_entity_log_index(self, entity_entity_changes):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in entity_entity_changes:
            es.q_delete_entity_entity_change(entity_entity_change=entity_entity_change)


class StageEntityEntity(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    entity_a = models.ForeignKey(StageEntity, on_delete=models.CASCADE, related_name='reverse_connections',
                                 verbose_name='Entity',
                                 limit_choices_to=Q(deleted=False))
    entity_b = models.ForeignKey(StageEntity, on_delete=models.CASCADE, related_name='connections',
                                 verbose_name='Entity',
                                 limit_choices_to=Q(deleted=False))
    connection_type = models.ForeignKey(StaticConnectionType, on_delete=models.PROTECT, related_name='connections')
    transaction_amount = models.DecimalField(max_digits=22, decimal_places=4, null=True, blank=True)
    transaction_currency = models.ForeignKey(StaticCurrency, on_delete=models.PROTECT, null=True, blank=True,
                                             related_name='connections')
    transaction_date = models.DateField(null=True, blank=True)
    from_collections = models.ManyToManyField(StageCollection, through='StageEntityEntityCollection',
                                              related_name='entity_entities')
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    _save_only_in_db = True

    class Meta:
        db_table = 'mocbackend_stage_entity_entity'
        index_together = [
            ('deleted', 'published', 'entity_a', 'entity_b', 'connection_type', 'valid_from', 'valid_to',
             'transaction_amount', 'transaction_currency', 'transaction_date'),
            ('deleted', 'published', 'entity_b', 'entity_a', 'connection_type', 'valid_from', 'valid_to',
             'transaction_amount', 'transaction_currency', 'transaction_date'),
        ]
        unique_together = [
            (
                'entity_a', 'entity_b', 'connection_type', 'valid_from', 'valid_to', 'transaction_amount',
                'transaction_currency', 'transaction_date')
        ]
        verbose_name = 'Entity Connection'
        verbose_name_plural = 'Entities Connections'

    def __str__(self):
        return self.entity_a.public_id + ', ' + self.entity_b.public_id + ', ' + self.connection_type.name

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        changed_fields = self.changed_fields
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'id' in changed_fields or 'entity_a' in changed_fields or 'entity_b' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, ttl=-1)
        if not self._save_only_in_db:
            es = ElasticsearchDB.get_db()
            neo4j = Neo4jDB.get_db()
            if adding:
                es.q_add_connection(entity_entity=self, calculate_count=True, overwrite=False)
                neo4j.q_add_connection(entity_entity=self, overwrite=False)
            elif has_changed:
                es.q_update_connection(entity_entity=self, calculate_count=True)
                neo4j.q_update_connection(entity_entity=self)

    def delete(self, *args, **kwargs):
        attribute_value_changes = LogAttributeValueChange.objects.filter(entity_entity=self)
        len(attribute_value_changes)
        entity_entity_changes = LogEntityEntityChange.objects.filter(entity_entity=self)
        len(entity_entity_changes)
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        es.q_delete_connection(entity_entity=self, calculate_count=True, delete_all=True)
        neo4j.q_delete_connection(entity_entity=self)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_entity_entity_log_index, entity_entity_changes=entity_entity_changes, ttl=-1)

    def update_attribute_value_log_index(self):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in self.attribute_value_changes.all():
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_delete_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in self.entity_entity_changes.all():
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def delete_entity_entity_log_index(self, entity_entity_changes):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in entity_entity_changes:
            es.q_delete_entity_entity_change(entity_entity_change=entity_entity_change)


class StageAttributeValue(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    entity = models.ForeignKey(StageEntity, on_delete=models.CASCADE, related_name='attribute_values',
                               limit_choices_to=Q(deleted=False), null=True, blank=True)
    entity_entity = models.ForeignKey(StageEntityEntity, on_delete=models.CASCADE, related_name='attribute_values',
                                      limit_choices_to=Q(deleted=False, entity_a__deleted=False,
                                                         entity_b__deleted=False,
                                                         entity_entity_collections__deleted=False,
                                                         entity_entity_collections__collection__deleted=False,
                                                         entity_entity_collections__collection__source__deleted=False),
                                      null=True, blank=True)
    attribute = models.ForeignKey(StageAttribute, on_delete=models.CASCADE, related_name='attribute_values',
                                  limit_choices_to=Q(finally_deleted=False))
    value_boolean = models.NullBooleanField(null=True, blank=True)
    value_int = models.BigIntegerField(null=True, blank=True)
    value_fixed_point = models.BigIntegerField(null=True, blank=True)
    value_floating_point = models.FloatField(null=True, blank=True)
    value_string = models.CharField(max_length=512, null=True, blank=True, db_index=True)
    value_text = models.TextField(null=True, blank=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_geo_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True,
                                        validators=[MinValueValidator(-90), MaxValueValidator(90)])
    value_geo_lon = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True,
                                        validators=[MinValueValidator(-180), MaxValueValidator(180)])
    value_range_int_from = models.BigIntegerField(null=True, blank=True)
    value_range_int_to = models.BigIntegerField(null=True, blank=True)
    value_range_fixed_point_from = models.BigIntegerField(null=True, blank=True)
    value_range_fixed_point_to = models.BigIntegerField(null=True, blank=True)
    value_range_floating_point_from = models.FloatField(null=True, blank=True)
    value_range_floating_point_to = models.FloatField(null=True, blank=True)
    value_range_datetime_from = models.DateTimeField(null=True, blank=True)
    value_range_datetime_to = models.DateTimeField(null=True, blank=True)
    value_range_date_from = models.DateField(null=True, blank=True)
    value_range_date_to = models.DateField(null=True, blank=True)
    value_codebook_item = models.ForeignKey(StageCodebookValue, on_delete=models.PROTECT, null=True, blank=True,
                                            related_name='attribute_values',
                                            limit_choices_to=Q(deleted=False, codebook__deleted=False,
                                                               codebook__attribute_types__deleted=False))
    from_collections = models.ManyToManyField(StageCollection, through='StageAttributeValueCollection',
                                              related_name='attribute_values')
    currency = models.ForeignKey(StaticCurrency, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='attribute_values')
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    _save_only_in_db = True

    class Meta:
        db_table = 'mocbackend_stage_attribute_value'
        index_together = [
            ('attribute', 'entity', 'entity_entity', 'value_codebook_item'),
            ('attribute', 'entity', 'value_codebook_item'),
            ('attribute', 'entity_entity', 'value_codebook_item'),
            ('attribute', 'value_codebook_item'),
            ('attribute', 'value_string'),
        ]
        verbose_name = 'Attribute Value'
        verbose_name_plural = 'Attributes Values'

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not self._save_only_in_db:
            if adding or has_changed:
                es = ElasticsearchDB.get_db()
                neo4j = Neo4jDB.get_db()
                update_connections = self.attribute.string_id in ['person_first_name', 'person_last_name',
                                                                  'legal_entity_name', 'legal_entity_entity_type',
                                                                  'real_estate_name', 'movable_name', 'savings_name']
                if self.entity is not None:
                    es.q_update_entity(entity=self.entity, update_connections=update_connections)
                    if update_connections:
                        neo4j.q_update_entity(entity=self.entity, update_connections=False)
                elif self.entity_entity is not None:
                    es.q_update_connection(entity_entity=self.entity_entity, calculate_count=False)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        neo4j = Neo4jDB.get_db()
        update_connections = self.attribute.string_id in ['person_first_name', 'person_last_name', 'legal_entity_name',
                                                          'legal_entity_entity_type', 'real_estate_name',
                                                          'movable_name', 'savings_name']
        if self.entity is not None:
            es.q_update_entity(entity=self.entity, update_connections=update_connections)
            if update_connections:
                neo4j.q_update_entity(entity=self.entity, update_connections=False)
        elif self.entity_entity is not None:
            es.q_update_connection(entity_entity=self.entity_entity, calculate_count=False)

    def __str__(self):
        return str(self.get_value())

    def get_value(self, geo_values_separator=helpers.get_admin_geo_values_separator(),
                  range_values_separator=helpers.get_admin_range_values_separator(), format_value=True):
        ret = None
        attribute_type_instance = self.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret = self.value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret = self.value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                ret = self.value_fixed_point
                if ret is not None:
                    ret = ret / helpers.get_divider(attribute_type_instance)
                if format_value:
                    ret = number_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                ret = self.value_floating_point
                if format_value:
                    ret = number_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret = self.value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret = self.value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret = self.value_datetime
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                ret = self.value_date
                if ret is not None and format_value:
                    ret = date_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                if self.value_codebook_item is not None:
                    ret = self.value_codebook_item.value
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                geo_lat = self.value_geo_lat
                geo_lon = self.value_geo_lon
                if format_value:
                    geo_lat, geo_lon = number_format(geo_lat), number_format(geo_lon)
                ret = '%s%s%s' % (geo_lat, geo_values_separator, geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret = '%s%s%s' % (
                    self.value_range_int_from, range_values_separator, self.value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                value_from = self.value_range_fixed_point_from
                if value_from is not None:
                    value_from = value_from / divider
                value_to = self.value_range_fixed_point_to
                if value_to is not None:
                    value_to = value_to / divider
                if format_value:
                    value_from, value_to = number_format(value_from), number_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                value_from = self.value_range_floating_point_from
                value_to = self.value_range_floating_point_to
                if format_value:
                    value_from, value_to = number_format(value_from), number_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret = '%s%s%s' % (
                    date_format(localtime(self.value_range_datetime_from), 'DATETIME_FORMAT'),
                    range_values_separator,
                    date_format(localtime(self.value_range_datetime_to), 'DATETIME_FORMAT'))
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                value_from = self.value_range_date_from
                if value_from is not None and format_value:
                    value_from = date_format(value_from)
                value_to = self.value_range_date_to
                if value_to is not None and format_value:
                    value_to = date_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
        return ret

    def get_raw_value(self):
        ret = None
        data_type = self.attribute.attribute_type.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret = self.value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret = self.value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                ret = self.value_fixed_point
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                ret = self.value_floating_point
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret = self.value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret = self.value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret = self.value_datetime
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                ret = self.value_date
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                ret = self.value_codebook_item
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                ret = '%s%s%s' % (self.value_geo_lat, ',', self.value_geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret = '%s%s%s' % (self.value_range_int_from, ',', self.value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                ret = '%s%s%s' % (self.value_range_fixed_point_from, ',', self.value_range_fixed_point_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                ret = '%s%s%s' % (self.value_range_floating_point_from, ',', self.value_range_floating_point_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret = '%s%s%s' % (self.value_range_datetime_from, ',', self.value_range_datetime_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                ret = '%s%s%s' % (self.value_range_date_from, ',', self.value_range_date_to)
        return ret

    def get_raw_first_value(self):
        ret = None
        data_type = self.attribute.attribute_type.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret = self.value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret = self.value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                ret = self.value_fixed_point
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                ret = self.value_floating_point
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret = self.value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret = self.value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret = self.value_datetime
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                ret = self.value_date
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                ret = self.value_codebook_item
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                ret = self.value_geo_lat
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret = self.value_range_int_from
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                ret = self.value_range_fixed_point_from
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                ret = self.value_range_floating_point_from
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret = self.value_range_datetime_from
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                ret = self.value_range_date_from
        return ret

    def get_raw_second_value(self):
        ret = None
        data_type = self.attribute.attribute_type.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                ret = self.value_geo_lon
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret = self.value_range_int_to
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                ret = self.value_range_fixed_point_to
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                ret = self.value_range_floating_point_to
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret = self.value_range_datetime_to
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                ret = self.value_range_date_to
        return ret


class LogAttributeValueChange(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    changeset = models.ForeignKey(LogChangeset, on_delete=models.CASCADE, related_name='attribute_value_changes',
                                  limit_choices_to=Q(deleted=False, collection__deleted=False,
                                                     collection__source__deleted=False))
    change_type = models.ForeignKey(StaticChangeType, on_delete=models.PROTECT, related_name='attribute_value_changes')
    entity = models.ForeignKey(StageEntity, on_delete=models.CASCADE, related_name='attribute_value_changes',
                               limit_choices_to=Q(deleted=False), null=True, blank=True)
    entity_entity = models.ForeignKey(StageEntityEntity, on_delete=models.CASCADE,
                                      related_name='attribute_value_changes',
                                      limit_choices_to=Q(deleted=False, entity_a__deleted=False,
                                                         entity_b__deleted=False,
                                                         entity_entity_collections__deleted=False,
                                                         entity_entity_collections__collection__deleted=False,
                                                         entity_entity_collections__collection__source__deleted=False),
                                      null=True, blank=True)
    attribute = models.ForeignKey(StageAttribute, on_delete=models.CASCADE, related_name='attribute_value_changes',
                                  limit_choices_to=Q(finally_deleted=False))
    old_valid_from = models.DateField(null=True, blank=True)
    new_valid_from = models.DateField(null=True, blank=True)
    old_valid_to = models.DateField(null=True, blank=True)
    new_valid_to = models.DateField(null=True, blank=True)
    old_value_boolean = models.NullBooleanField(null=True, blank=True)
    new_value_boolean = models.NullBooleanField(null=True, blank=True)
    old_value_int = models.BigIntegerField(null=True, blank=True)
    new_value_int = models.BigIntegerField(null=True, blank=True)
    old_value_fixed_point = models.BigIntegerField(null=True, blank=True)
    new_value_fixed_point = models.BigIntegerField(null=True, blank=True)
    old_value_floating_point = models.FloatField(null=True, blank=True)
    new_value_floating_point = models.FloatField(null=True, blank=True)
    old_value_string = models.CharField(max_length=512, null=True, blank=True)
    new_value_string = models.CharField(max_length=512, null=True, blank=True)
    old_value_text = models.TextField(null=True, blank=True)
    new_value_text = models.TextField(null=True, blank=True)
    old_value_datetime = models.DateTimeField(null=True, blank=True)
    new_value_datetime = models.DateTimeField(null=True, blank=True)
    old_value_date = models.DateField(null=True, blank=True)
    new_value_date = models.DateField(null=True, blank=True)
    old_value_geo_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True,
                                            validators=[MinValueValidator(-90), MaxValueValidator(90)])
    new_value_geo_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True,
                                            validators=[MinValueValidator(-90), MaxValueValidator(90)])
    old_value_geo_lon = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True,
                                            validators=[MinValueValidator(-180), MaxValueValidator(180)])
    new_value_geo_lon = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True,
                                            validators=[MinValueValidator(-180), MaxValueValidator(180)])
    old_value_range_int_from = models.BigIntegerField(null=True, blank=True)
    new_value_range_int_from = models.BigIntegerField(null=True, blank=True)
    old_value_range_int_to = models.BigIntegerField(null=True, blank=True)
    new_value_range_int_to = models.BigIntegerField(null=True, blank=True)
    old_value_range_fixed_point_from = models.BigIntegerField(null=True, blank=True)
    new_value_range_fixed_point_from = models.BigIntegerField(null=True, blank=True)
    old_value_range_fixed_point_to = models.BigIntegerField(null=True, blank=True)
    new_value_range_fixed_point_to = models.BigIntegerField(null=True, blank=True)
    old_value_range_floating_point_from = models.FloatField(null=True, blank=True)
    new_value_range_floating_point_from = models.FloatField(null=True, blank=True)
    old_value_range_floating_point_to = models.FloatField(null=True, blank=True)
    new_value_range_floating_point_to = models.FloatField(null=True, blank=True)
    old_value_range_datetime_from = models.DateTimeField(null=True, blank=True)
    new_value_range_datetime_from = models.DateTimeField(null=True, blank=True)
    old_value_range_datetime_to = models.DateTimeField(null=True, blank=True)
    new_value_range_datetime_to = models.DateTimeField(null=True, blank=True)
    old_value_range_date_from = models.DateField(null=True, blank=True)
    new_value_range_date_from = models.DateField(null=True, blank=True)
    old_value_range_date_to = models.DateField(null=True, blank=True)
    new_value_range_date_to = models.DateField(null=True, blank=True)
    old_value_codebook_item = models.ForeignKey(StageCodebookValue, on_delete=models.PROTECT, null=True, blank=True,
                                                related_name='attribute_value_changes_codebook_item_old_values',
                                                limit_choices_to=Q(deleted=False, codebook__deleted=False,
                                                                   codebook__attribute_types__deleted=False))
    new_value_codebook_item = models.ForeignKey(StageCodebookValue, on_delete=models.PROTECT, null=True, blank=True,
                                                related_name='attribute_value_changes_codebook_item_new_values',
                                                limit_choices_to=Q(deleted=False, codebook__deleted=False,
                                                                   codebook__attribute_types__deleted=False))
    old_currency = models.ForeignKey(StaticCurrency, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='attribute_value_changes_old_currency')
    new_currency = models.ForeignKey(StaticCurrency, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name='attribute_value_changes_new_currency')
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_log_attribute_value_change'
        index_together = [
            ('deleted', 'published', 'id'),
            ('deleted', 'published', 'attribute', 'entity'),
            ('deleted', 'published', 'attribute', 'entity_entity'),
        ]
        verbose_name = 'Attribute Value Change'
        verbose_name_plural = 'Attributes Values Changes'

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding or has_changed:
            es = ElasticsearchDB.get_db()
            es.q_update_attribute_value_change(attribute_value_change=self)

    def delete(self, *args, **kwargs):
        other_attribute_values_changes_exists = self.changeset.attribute_value_changes.filter(~Q(pk=self.pk)).exists()
        other_entity_entity_changes_exists = self.changeset.entity_entity_changes.all().exists()
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        if not other_attribute_values_changes_exists and not other_entity_entity_changes_exists:
            self.changeset.delete()
        es.q_delete_attribute_value_change(attribute_value_change=self)

    def __str__(self):
        return str(self.get_value())

    def get_old_value(self, geo_values_separator=helpers.get_admin_geo_values_separator(),
                      range_values_separator=helpers.get_admin_range_values_separator(), format_value=True):
        ret = None
        attribute_type_instance = self.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret = self.old_value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret = self.old_value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                ret = self.old_value_fixed_point
                if ret is not None:
                    ret = ret / helpers.get_divider(attribute_type_instance)
                if format_value:
                    ret = number_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                ret = self.old_value_floating_point
                if format_value:
                    ret = number_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret = self.old_value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret = self.old_value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret = self.old_value_datetime
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                ret = self.old_value_date
                if ret is not None and format_value:
                    ret = date_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                if self.old_value_codebook_item is not None:
                    ret = self.old_value_codebook_item.value
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                geo_lat = self.old_value_geo_lat
                geo_lon = self.old_value_geo_lon
                if format_value:
                    geo_lat, geo_lon = number_format(geo_lat), number_format(geo_lon)
                ret = '%s%s%s' % (geo_lat, geo_values_separator, geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret = '%s%s%s' % (
                    self.old_value_range_int_from, range_values_separator, self.old_value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                value_from = self.old_value_range_fixed_point_from
                if value_from is not None:
                    value_from = value_from / divider
                value_to = self.old_value_range_fixed_point_to
                if value_to is not None:
                    value_to = value_to / divider
                if format_value:
                    value_from, value_to = number_format(value_from), number_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                value_from = self.old_value_range_floating_point_from
                value_to = self.old_value_range_floating_point_to
                if format_value:
                    value_from, value_to = number_format(value_from), number_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret = '%s%s%s' % (
                    date_format(localtime(self.old_value_range_datetime_from), 'DATETIME_FORMAT'),
                    range_values_separator,
                    date_format(localtime(self.old_value_range_datetime_to), 'DATETIME_FORMAT'))
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                value_from = self.old_value_range_date_from
                if value_from is not None and format_value:
                    value_from = date_format(value_from)
                value_to = self.old_value_range_date_to
                if value_to is not None and format_value:
                    value_to = date_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
        return ret

    def get_new_value(self, geo_values_separator=helpers.get_admin_geo_values_separator(),
                      range_values_separator=helpers.get_admin_range_values_separator(), format_value=True):
        ret = None
        attribute_type_instance = self.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret = self.new_value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret = self.new_value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                ret = self.new_value_fixed_point
                if ret is not None:
                    ret = ret / helpers.get_divider(attribute_type_instance)
                if format_value:
                    ret = number_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                ret = self.new_value_floating_point
                if format_value:
                    ret = number_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret = self.new_value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret = self.new_value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret = self.new_value_datetime
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                ret = self.new_value_date
                if ret is not None and format_value:
                    ret = date_format(ret)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                if self.new_value_codebook_item is not None:
                    ret = self.new_value_codebook_item.value
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                geo_lat = self.new_value_geo_lat
                geo_lon = self.new_value_geo_lon
                if format_value:
                    geo_lat, geo_lon = number_format(geo_lat), number_format(geo_lon)
                ret = '%s%s%s' % (geo_lat, geo_values_separator, geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret = '%s%s%s' % (
                    self.new_value_range_int_from, range_values_separator, self.new_value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                value_from = self.new_value_range_fixed_point_from
                if value_from is not None:
                    value_from = value_from / divider
                value_to = self.new_value_range_fixed_point_to
                if value_to is not None:
                    value_to = value_to / divider
                if format_value:
                    value_from, value_to = number_format(value_from), number_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                value_from = self.new_value_range_floating_point_from
                value_to = self.new_value_range_floating_point_to
                if format_value:
                    value_from, value_to = number_format(value_from), number_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret = '%s%s%s' % (
                    date_format(localtime(self.new_value_range_datetime_from), 'DATETIME_FORMAT'),
                    range_values_separator,
                    date_format(localtime(self.new_value_range_datetime_to), 'DATETIME_FORMAT'))
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                value_from = self.new_value_range_date_from
                if value_from is not None and format_value:
                    value_from = date_format(value_from)
                value_to = self.new_value_range_date_to
                if value_to is not None and format_value:
                    value_to = date_format(value_to)
                ret = '%s%s%s' % (value_from, range_values_separator, value_to)
        return ret

    def get_value(self, geo_values_separator=helpers.get_admin_geo_values_separator(),
                  range_values_separator=helpers.get_admin_range_values_separator(), format_value=True):
        ret = None
        attribute_type_instance = self.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        separator = ' \u2192 '
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret = '%s%s%s' % (self.old_value_boolean, separator, self.new_value_boolean)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret = '%s%s%s' % (self.old_value_int, separator, self.new_value_int)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                old_value = self.old_value_fixed_point
                if old_value is not None:
                    old_value = old_value / divider
                new_value = self.new_value_fixed_point
                if new_value is not None:
                    new_value = new_value / divider
                if format_value:
                    old_value, new_value = number_format(old_value), number_format(new_value)
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                old_value = self.old_value_floating_point
                new_value = self.new_value_floating_point
                if format_value:
                    old_value, new_value = number_format(old_value), number_format(new_value)
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret = '%s%s%s' % (self.old_value_string, separator, self.new_value_string)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret = '%s%s%s' % (self.old_value_text, separator, self.new_value_text)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret = '%s%s%s' % (date_format(localtime(self.old_value_datetime), 'DATETIME_FORMAT'), separator,
                                  date_format(localtime(self.new_value_datetime), 'DATETIME_FORMAT'))
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                old_value = self.old_value_date
                if old_value is not None and format_value:
                    old_value = date_format(old_value)
                new_value = self.new_value_date
                if new_value is not None and format_value:
                    new_value = date_format(new_value)
                ret = '%s%s%s' % (old_value, range_values_separator, new_value)
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                old_value = self.old_value_codebook_item
                if old_value is not None:
                    old_value = old_value.value
                new_value = self.new_value_codebook_item
                if new_value is not None:
                    new_value = new_value.value
                ret = '%s%s%s' % (old_value, separator, new_value)
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                old_value_geo_lat = self.old_value_geo_lat
                old_value_geo_lon = self.old_value_geo_lon
                if format_value:
                    old_value_geo_lat, old_value_geo_lon = number_format(old_value_geo_lat), number_format(
                        old_value_geo_lon)
                old_value = '%s%s%s' % (old_value_geo_lat, geo_values_separator, old_value_geo_lon)

                new_value_geo_lat = self.new_value_geo_lat
                new_value_geo_lon = self.new_value_geo_lon
                if format_value:
                    new_value_geo_lat, new_value_geo_lon = number_format(new_value_geo_lat), number_format(
                        new_value_geo_lon)
                new_value = '%s%s%s' % (new_value_geo_lat, geo_values_separator, new_value_geo_lon)
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                old_value = '%s%s%s' % (
                    self.old_value_range_int_from, range_values_separator, self.old_value_range_int_to)
                new_value = '%s%s%s' % (
                    self.new_value_range_int_from, range_values_separator, self.new_value_range_int_to)
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                old_value_from = self.old_value_range_fixed_point_from
                if old_value_from is not None:
                    old_value_from = old_value_from / divider
                old_value_to = self.old_value_range_fixed_point_to
                if old_value_to is not None:
                    old_value_to = old_value_to / divider
                if format_value:
                    old_value_from, old_value_to = number_format(old_value_from), number_format(old_value_to)
                old_value = '%s%s%s' % (old_value_from, range_values_separator, old_value_to)

                new_value_from = self.new_value_range_fixed_point_from
                if new_value_from is not None:
                    new_value_from = new_value_from / divider
                new_value_to = self.new_value_range_fixed_point_to
                if new_value_to is not None:
                    new_value_to = new_value_to / divider
                if format_value:
                    new_value_from, new_value_to = number_format(new_value_from), number_format(new_value_to)
                new_value = '%s%s%s' % (new_value_from, range_values_separator, new_value_to)
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                old_value_from = self.old_value_range_floating_point_from
                old_value_to = self.old_value_range_floating_point_to
                if format_value:
                    old_value_from, old_value_to = number_format(old_value_from), number_format(old_value_to)
                old_value = '%s%s%s' % (old_value_from, range_values_separator, old_value_to)

                new_value_from = self.new_value_range_floating_point_from
                new_value_to = self.new_value_range_floating_point_to
                if format_value:
                    new_value_from, new_value_to = number_format(new_value_from), number_format(new_value_to)
                new_value = '%s%s%s' % (new_value_from, range_values_separator, new_value_to)
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                old_value = '%s%s%s' % (
                    date_format(localtime(self.old_value_range_datetime_from), 'DATETIME_FORMAT'),
                    range_values_separator,
                    date_format(localtime(self.old_value_range_datetime_to), 'DATETIME_FORMAT'))
                new_value = '%s%s%s' % (
                    date_format(localtime(self.new_value_range_datetime_from), 'DATETIME_FORMAT'),
                    range_values_separator,
                    date_format(localtime(self.new_value_range_datetime_to), 'DATETIME_FORMAT'))
                ret = '%s%s%s' % (old_value, separator, new_value)
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                old_value_from = self.old_value_range_date_from
                if old_value_from is not None and format_value:
                    old_value_from = date_format(old_value_from)
                old_value_to = self.old_value_range_date_to
                if old_value_to is not None and format_value:
                    old_value_to = date_format(old_value_to)
                old_value = '%s%s%s' % (old_value_from, range_values_separator, old_value_to)

                new_value_from = self.new_value_range_date_from
                if new_value_from is not None and format_value:
                    new_value_from = date_format(new_value_from)
                new_value_to = self.new_value_range_date_to
                if new_value_to is not None and format_value:
                    new_value_to = date_format(new_value_to)
                new_value = '%s%s%s' % (new_value_from, range_values_separator, new_value_to)
                ret = '%s%s%s' % (old_value, separator, new_value)
        return ret


class LogEntityEntityChange(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    changeset = models.ForeignKey(LogChangeset, on_delete=models.CASCADE, related_name='entity_entity_changes',
                                  limit_choices_to=Q(deleted=False, collection__deleted=False,
                                                     collection__source__deleted=False))
    change_type = models.ForeignKey(StaticChangeType, on_delete=models.PROTECT, related_name='entity_entity_changes')
    entity_entity = models.ForeignKey(StageEntityEntity, on_delete=models.CASCADE, related_name='entity_entity_changes',
                                      limit_choices_to=Q(deleted=False, entity_a__deleted=False,
                                                         entity_b__deleted=True))
    old_valid_from = models.DateField(null=True, blank=True)
    new_valid_from = models.DateField(null=True, blank=True)
    old_valid_to = models.DateField(null=True, blank=True)
    new_valid_to = models.DateField(null=True, blank=True)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    class Meta:
        db_table = 'mocbackend_log_entity_entity_change'
        index_together = [
            ('deleted', 'published', 'id'),
        ]
        verbose_name = 'Entity Connection Change'
        verbose_name_plural = 'Entities Connections Changes'

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding or has_changed:
            es = ElasticsearchDB.get_db()
            es.q_update_entity_entity_change(entity_entity_change=self)

    def delete(self, *args, **kwargs):
        other_attribute_values_changes_exists = self.changeset.attribute_value_changes.all().exists()
        other_entity_entity_changes_exists = self.changeset.entity_entity_changes.filter(~Q(pk=self.pk)).exists()
        super().delete(*args, **kwargs)
        es = ElasticsearchDB.get_db()
        if not other_attribute_values_changes_exists and not other_entity_entity_changes_exists:
            self.changeset.delete()
        es.q_delete_entity_entity_change(entity_entity_change=self)


class StageAttributeValueCollection(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    attribute_value = models.ForeignKey(StageAttributeValue, on_delete=models.CASCADE,
                                        related_name='attribute_value_collections',
                                        limit_choices_to=Q(attribute__finally_deleted=False) & ((~Q(
                                            entity=None) & Q(entity__deleted=False)) | (~Q(entity_entity=None) & Q(
                                            entity_entity__deleted=False,
                                            entity_entity__entity_a__deleted=False,
                                            entity_entity__entity_b__deleted=False,
                                            entity_entity__entity_entity_collections__deleted=False,
                                            entity_entity__entity_entity_collections__collection__deleted=False,
                                            entity_entity__entity_entity_collections__collection__source__deleted=False))) & (
                                                                 Q(value_codebook_item=None) | Q(
                                                             value_codebook_item__deleted=False,
                                                             value_codebook_item__codebook__deleted=False)))
    collection = models.ForeignKey(StageCollection, on_delete=models.CASCADE,
                                   related_name='attribute_value_collections',
                                   limit_choices_to=Q(deleted=False, source__deleted=False))
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    _save_only_in_db = True

    class Meta:
        db_table = 'mocbackend_stage_attribute_value_collection'
        index_together = [
            ('deleted', 'published', 'collection'),
            ('deleted', 'published', 'attribute_value', 'collection'),
        ]
        unique_together = [
            ('attribute_value', 'collection')
        ]

    def save(self, *args, **kwargs):
        has_changed = self.has_changed
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not self._save_only_in_db:
            if adding or has_changed:
                es = ElasticsearchDB.get_db()
                neo4j = Neo4jDB.get_db()
                update_connections = self.attribute_value.attribute.string_id in ['person_first_name',
                                                                                  'person_last_name',
                                                                                  'legal_entity_name',
                                                                                  'legal_entity_entity_type',
                                                                                  'real_estate_name', 'movable_name',
                                                                                  'savings_name']
                if self.attribute_value.entity is not None:
                    es.q_update_entity(entity=self.attribute_value.entity, update_connections=update_connections)
                    if update_connections:
                        neo4j.q_update_entity(entity=self.attribute_value.entity, update_connections=False)
                elif self.attribute_value.entity_entity is not None:
                    es.q_update_connection(entity_entity=self.attribute_value.entity_entity, calculate_count=False)

    def delete(self, *args, **kwargs):
        other_attribute_value_collection_exists = self.attribute_value.attribute_value_collections.filter(
            ~Q(pk=self.pk)).exists()
        super().delete(*args, **kwargs)
        if not other_attribute_value_collection_exists:
            self.attribute_value.delete()
        else:
            es = ElasticsearchDB.get_db()
            neo4j = Neo4jDB.get_db()
            update_connections = self.attribute_value.attribute.string_id in ['person_first_name', 'person_last_name',
                                                                              'legal_entity_name',
                                                                              'legal_entity_entity_type',
                                                                              'real_estate_name', 'movable_name',
                                                                              'savings_name']
            if self.attribute_value.entity is not None:
                es.q_update_entity(entity=self.attribute_value.entity, update_connections=update_connections)
                if update_connections:
                    neo4j.q_update_entity(entity=self.attribute_value.entity, update_connections=False)
            elif self.attribute_value.entity_entity is not None:
                es.q_update_connection(entity_entity=self.attribute_value.entity_entity, calculate_count=False)


class StageEntityEntityCollection(ModelDiffMixin, models.Model):
    id = models.BigAutoField(primary_key=True)
    entity_entity = models.ForeignKey(StageEntityEntity, on_delete=models.CASCADE,
                                      related_name='entity_entity_collections',
                                      limit_choices_to=Q(deleted=False, entity_a__deleted=False,
                                                         entity_b__deleted=False))
    collection = models.ForeignKey(StageCollection, on_delete=models.CASCADE,
                                   related_name='entity_entity_collections',
                                   limit_choices_to=Q(deleted=False, source__deleted=False))
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False, verbose_name='Soft Deleted')

    _save_only_in_db = True

    class Meta:
        db_table = 'mocbackend_stage_entity_entity_collection'
        index_together = [
            ('deleted', 'published', 'entity_entity', 'collection'),
        ]
        unique_together = [
            ('entity_entity', 'collection')
        ]

    def save(self, *args, **kwargs):
        changed_fields = self.changed_fields
        has_changed = self.has_changed
        adding = self._state.adding
        old_entity_entity = None
        if not adding and 'entity_entity' in changed_fields:
            old_entity_entity = StageEntityEntityCollection.objects.get(pk=self.pk).entity_entity
        super().save(*args, **kwargs)
        if not adding and (
                'published' in changed_fields or 'deleted' in changed_fields or 'entity_entity' in changed_fields or 'collection' in changed_fields):
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_attribute_value_log_index, old_entity_entity=old_entity_entity, ttl=-1)
            queue = helpers.get_queue(queue='db', default_timeout='60m')
            queue.enqueue(self.update_entity_entity_log_index, old_entity_entity=old_entity_entity, ttl=-1)
        if not self._save_only_in_db:
            es = ElasticsearchDB.get_db()
            neo4j = Neo4jDB.get_db()
            if adding:
                es.q_add_connection(entity_entity=self.entity_entity, calculate_count=True, overwrite=False)
                neo4j.q_add_connection(entity_entity=self, overwrite=False)
            elif has_changed:
                es.q_update_connection(entity_entity=self.entity_entity, calculate_count=True)
                neo4j.q_update_connection(entity_entity=self.entity_entity)

    def delete(self, *args, **kwargs):
        other_entity_entity_collection_exists = self.entity_entity.entity_entity_collections.filter(
            ~Q(pk=self.pk)).exists()
        attribute_value_changes = LogAttributeValueChange.objects.filter(
            entity_entity__entity_entity_collections__pk=self.pk).distinct()
        len(attribute_value_changes)
        entity_entity_changes = LogEntityEntityChange.objects.filter(
            entity_entity__entity_entity_collections__pk=self.pk).distinct()
        len(entity_entity_changes)
        super().delete(*args, **kwargs)
        if not other_entity_entity_collection_exists:
            self.entity_entity.delete()
        else:
            es = ElasticsearchDB.get_db()
            neo4j = Neo4jDB.get_db()
            es.q_delete_connection(entity_entity=self.entity_entity, calculate_count=True, delete_all=True)
            neo4j.q_delete_connection(entity_entity=self)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_attribute_value_log_index, attribute_value_changes=attribute_value_changes, ttl=-1)
        queue = helpers.get_queue(queue='db', default_timeout='60m')
        queue.enqueue(self.delete_entity_entity_log_index, entity_entity_changes=entity_entity_changes, ttl=-1)

    def update_attribute_value_log_index(self, old_entity_entity):
        es = ElasticsearchDB.get_db()
        processed_attribute_value_changes = set()
        for attribute_value_change in old_entity_entity.attribute_value_changes.all():
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)
        for attribute_value_change in LogAttributeValueChange.objects.filter(
                entity_entity__entity_entity_collections__pk=self.pk).distinct():
            if attribute_value_change not in processed_attribute_value_changes:
                processed_attribute_value_changes.add(attribute_value_change)
                es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def delete_attribute_value_log_index(self, attribute_value_changes):
        es = ElasticsearchDB.get_db()
        for attribute_value_change in attribute_value_changes:
            es.q_update_attribute_value_change(attribute_value_change=attribute_value_change)

    def update_entity_entity_log_index(self, old_entity_entity):
        es = ElasticsearchDB.get_db()
        processed_entity_entity_changes = set()
        for entity_entity_change in old_entity_entity.entity_entity_changes.all():
            if entity_entity_change not in processed_entity_entity_changes:
                processed_entity_entity_changes.add(entity_entity_change)
                es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)
        for entity_entity_change in LogEntityEntityChange.objects.filter(
                entity_entity__entity_entity_collections__pk=self.pk).distinct():
            if entity_entity_change not in processed_entity_entity_changes:
                processed_entity_entity_changes.add(entity_entity_change)
                es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)

    def delete_entity_entity_log_index(self, entity_entity_changes):
        es = ElasticsearchDB.get_db()
        for entity_entity_change in entity_entity_changes:
            es.q_update_entity_entity_change(entity_entity_change=entity_entity_change)


class KeyValue(models.Model):
    key = models.CharField(max_length=512, primary_key=True)
    value = models.CharField(max_length=512, db_index=True)
    raw_data = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'mocbackend_key_value'


class Article(models.Model):
    id = models.AutoField(primary_key=True)
    slug = models.SlugField(max_length=128)
    title = models.CharField(max_length=128)
    content_short = fields.RichTextField(blank=True)
    content_long = fields.RichTextField(blank=True)

    class Meta:
        db_table = 'cms_article'


class UserInfo(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_info',
                                primary_key=True, limit_choices_to=Q(is_active=True))
    watched_entities = models.ManyToManyField(StageEntity, through='UserEntity', related_name='watchers')
    send_notification_on_change_watched_entity = models.BooleanField(default=False)

    class Meta:
        db_table = 'mocbackend_user_info'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.user.username


class UserEntity(models.Model):
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='user_entities',
                              limit_choices_to=Q(user__is_active=True))
    entity = models.ForeignKey(StageEntity, on_delete=models.CASCADE, related_name='user_entities',
                               limit_choices_to=Q(deleted=False, published=True))

    @property
    def entity__public_id(self):
        return self.entity.public_id

    class Meta:
        db_table = 'mocbackend_user_entity'
        unique_together = [
            ('owner', 'entity')
        ]


class UserSavedSearch(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    name = models.CharField(max_length=64)
    saved_url = models.TextField()
    owner = models.ForeignKey(UserInfo, on_delete=models.CASCADE, related_name='saved_searches',
                              limit_choices_to=Q(user__is_active=True))

    class Meta:
        db_table = 'mocbackend_user_saved_search'
        unique_together = [
            ('owner', 'name'),
            ('owner', 'saved_url')
        ]
        index_together = [
            ('owner', 'created_at')
        ]
        verbose_name = 'Saved Search'
        verbose_name_plural = 'Saved Searches'

    def __str__(self):
        return self.name


class SecurityExtensionUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='security_extension',
                                primary_key=True)
    password_change_token_hash = models.CharField(max_length=128, null=True, default=None)
    password_change_token_hash_salt = models.CharField(max_length=128, null=True, default=None)
    password_change_token_created_at = models.DateTimeField(null=True, default=None)
    unverified_email = models.EmailField(max_length=254)
    email_verification_token_hash = models.CharField(max_length=128, null=True, default=None)
    email_verification_token_hash_salt = models.CharField(max_length=128, null=True, default=None)
    email_verification_token_created_at = models.DateTimeField(null=True, default=None)

    _token_length = 64
    _salt_length = 128

    class Meta:
        db_table = 'security_extension_user'
        verbose_name = 'Security Extension'
        verbose_name_plural = 'Security Extensions'

    def __str__(self):
        return self.user.username

    def generate_password_change_token(self):
        token = get_random_string(length=self._token_length)
        self.password_change_token_hash_salt = get_random_string(length=self._salt_length)
        self.password_change_token_hash = helpers.hash(data=token, salt=self.password_change_token_hash_salt)
        self.password_change_token_created_at = timezone.now()
        return token

    def is_password_change_token(self, token):
        return self.password_change_token_hash is not None and self.password_change_token_hash_salt is not None and len(
            token) == self._token_length and helpers.hash(data=token,
                                                          salt=self.password_change_token_hash_salt) == self.password_change_token_hash

    def unset_password_change_token(self):
        self.password_change_token_hash = None
        self.password_change_token_hash_salt = None
        self.password_change_token_created_at = None

    def generate_email_verification_token(self):
        token = get_random_string(length=self._token_length)
        self.email_verification_token_hash_salt = get_random_string(length=self._salt_length)
        self.email_verification_token_hash = helpers.hash(data=token, salt=self.email_verification_token_hash_salt)
        self.email_verification_token_created_at = timezone.now()
        return token

    def is_email_verification_token(self, token):
        return self.email_verification_token_hash is not None and self.email_verification_token_hash_salt is not None and len(
            token) == self._token_length and helpers.hash(data=token,
                                                          salt=self.email_verification_token_hash_salt) == self.email_verification_token_hash

    def unset_email_verification_token(self):
        self.email_verification_token_hash = None
        self.email_verification_token_hash_salt = None
        self.email_verification_token_created_at = None


class AccessLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    remote_ip = models.GenericIPAddressField(db_index=True)
    method = models.CharField(max_length=7, db_index=True)
    path = models.TextField(db_index=True)
    query = models.TextField(db_index=True)
    post_data = models.TextField()
    response_status_code = models.CharField(max_length=3, db_index=True)
    request = models.TextField()
    response = models.TextField()

    class Meta:
        db_table = 'logging_access_log'
        index_together = [
            ('path', 'query')
        ]
        verbose_name = 'Access Log'
        verbose_name_plural = 'Access Log'

    def __str__(self):
        return str(self.timestamp) + ': ' + self.path
