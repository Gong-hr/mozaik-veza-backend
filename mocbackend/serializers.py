import datetime
import hashlib
from collections import OrderedDict
from decimal import *

import django
from django.db.models import Q
from django.utils import timezone
from django.utils.timezone import utc
from slugify import slugify
from rest_framework import serializers
from rest_framework.fields import SkipField, DateField
from rest_framework.relations import PKOnlyObject
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from django.utils.translation import ugettext_lazy as _

from mocbackend import helpers, const, models


# - depth: 0

class StageAttributeCreateSerializer(serializers.ModelSerializer):
    attribute_type = serializers.SlugRelatedField(slug_field='string_id',
                                                  queryset=models.StageAttributeType.objects.filter(
                                                      Q(deleted=False, published=True) & (
                                                              Q(codebook=None) | Q(codebook__deleted=False,
                                                                                   codebook__published=True))),
                                                  required=True, allow_null=False)
    entity_type = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StaticEntityType.objects.all(),
                                               required=False, allow_null=True)
    collection = serializers.SlugRelatedField(slug_field='string_id',
                                              queryset=models.StageCollection.objects.filter(deleted=False,
                                                                                             published=True,
                                                                                             source__deleted=False,
                                                                                             source__published=True),
                                              required=False, allow_null=True)
    attribute = serializers.SlugRelatedField(slug_field='string_id',
                                             queryset=models.StageAttribute.objects.filter(finally_deleted=False,
                                                                                           finally_published=True,
                                                                                           attribute_type__data_type__string_id='complex'),
                                             required=False, allow_null=True)

    class Meta:
        model = models.StageAttribute
        fields = ('string_id', 'name', 'attribute_type', 'entity_type', 'collection', 'attribute')

    def validate(self, data):
        if data.get('entity_type') is None and data.get('collection') is None and data.get('attribute') is None:
            raise serializers.ValidationError(
                {'entity_type': 'Entity type or Collection or Attribute must be specified.'})
        elif (data.get('entity_type') is not None and (
                data.get('collection') is not None or data.get('attribute') is not None)) or (
                data.get('collection') is not None and data.get('attribute') is not None):
            raise serializers.ValidationError(
                {'entity_type': 'Only Entity type or Collection or Attribute can be specified.'})
        return data

    def create(self, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            if validated_data.get('attribute') is not None:
                attribute = validated_data.get('attribute')
                validated_data.update({
                    'collection': attribute.collection
                })
            instance = ModelClass._default_manager.create(**validated_data)
        except TypeError:
            import traceback
            tb = traceback.format_exc()
            msg = (
                    'Got a `TypeError` when calling `%s.%s.create()`. '
                    'This may be because you have a writable field on the '
                    'serializer class that is not a valid argument to '
                    '`%s.%s.create()`. You may need to make the field '
                    'read-only, or override the %s.create() method to handle '
                    'this correctly.\nOriginal exception was:\n %s' %
                    (
                        ModelClass.__name__,
                        ModelClass._default_manager.name,
                        ModelClass.__name__,
                        ModelClass._default_manager.name,
                        self.__class__.__name__,
                        tb
                    )
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                field.set(value)

        return instance


class StageAttributeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageAttribute
        fields = ()


class StageAttributeTypeCreateSerializer(serializers.ModelSerializer):
    data_type = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StaticDataType.objects.all(),
                                             required=True, allow_null=False)
    codebook = serializers.SlugRelatedField(slug_field='string_id',
                                            queryset=models.StageCodebook.objects.filter(deleted=False, published=True),
                                            required=False, allow_null=True)

    class Meta:
        model = models.StageAttributeType
        fields = (
            'string_id', 'name', 'data_type', 'codebook', 'fixed_point_decimal_places',
            'range_floating_point_from_inclusive', 'range_floating_point_to_inclusive')

    def validate(self, data):
        data_type = data.get('data_type').string_id
        field_name = None
        message = 'Must be none for the specified data type.'
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) in [const.DATA_TYPE_BOOLEAN, const.DATA_TYPE_INT,
                                                                 const.DATA_TYPE_FLOATING_POINT,
                                                                 const.DATA_TYPE_STRING, const.DATA_TYPE_TEXT,
                                                                 const.DATA_TYPE_DATETIME, const.DATA_TYPE_DATE]:
                if data.get('codebook') is not None:
                    field_name = 'codebook'
                elif data.get('fixed_point_decimal_places') is not None:
                    field_name = 'fixed_point_decimal_places'
                elif data.get('range_floating_point_from_inclusive') is not None:
                    field_name = 'range_floating_point_from_inclusive'
                elif data.get('range_floating_point_to_inclusive') is not None:
                    field_name = 'range_floating_point_to_inclusive'
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) in [const.DATA_TYPE_FIXED_POINT]:
                if data.get('codebook') is not None:
                    field_name = 'codebook'
                elif data.get('range_floating_point_from_inclusive') is not None:
                    field_name = 'range_floating_point_from_inclusive'
                elif data.get('range_floating_point_to_inclusive') is not None:
                    field_name = 'range_floating_point_to_inclusive'
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) in [const.DATA_TYPE_CODEBOOK]:
                if data.get('codebook') is None:
                    field_name = 'codebook'
                    message = 'Must be not none for the specified data type.'
                elif data.get('fixed_point_decimal_places') is not None:
                    field_name = 'fixed_point_decimal_places'
                elif data.get('range_floating_point_from_inclusive') is not None:
                    field_name = 'range_floating_point_from_inclusive'
                elif data.get('range_floating_point_to_inclusive') is not None:
                    field_name = 'range_floating_point_to_inclusive'
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) in [const.DATA_TYPE_GEO, const.DATA_TYPE_RANGE_INT,
                                                                  const.DATA_TYPE_RANGE_DATETIME,
                                                                  const.DATA_TYPE_RANGE_DATE]:
                if data.get('codebook') is not None:
                    field_name = 'codebook'
                elif data.get('fixed_point_decimal_places') is not None:
                    field_name = 'fixed_point_decimal_places'
                elif data.get('range_floating_point_from_inclusive') is not None:
                    field_name = 'range_floating_point_from_inclusive'
                elif data.get('range_floating_point_to_inclusive') is not None:
                    field_name = 'range_floating_point_to_inclusive'
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) in [const.DATA_TYPE_RANGE_FIXED_POINT]:
                if data.get('codebook') is not None:
                    field_name = 'codebook'
                elif data.get('range_floating_point_from_inclusive') is not None:
                    field_name = 'range_floating_point_from_inclusive'
                elif data.get('range_floating_point_to_inclusive') is not None:
                    field_name = 'range_floating_point_to_inclusive'
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) in [const.DATA_TYPE_RANGE_FLOATING_POINT]:
                if data.get('codebook') is not None:
                    field_name = 'codebook'
                elif data.get('fixed_point_decimal_places') is not None:
                    field_name = 'fixed_point_decimal_places'
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) in [const.DATA_TYPE_COMPLEX]:
                if data.get('codebook') is not None:
                    field_name = 'codebook'
                elif data.get('fixed_point_decimal_places') is not None:
                    field_name = 'fixed_point_decimal_places'
                elif data.get('range_floating_point_from_inclusive') is not None:
                    field_name = 'range_floating_point_from_inclusive'
                elif data.get('range_floating_point_to_inclusive') is not None:
                    field_name = 'range_floating_point_to_inclusive'
        else:
            field_name = 'data_type'
            message = 'Invalid.'
        if field_name is not None:
            raise serializers.ValidationError({field_name: message})
        return data


class StageAttributeTypeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageAttributeType
        fields = ()


class StageAttributeValueCreateUpdateSerializer(serializers.ModelSerializer):
    entity = serializers.SlugRelatedField(slug_field='public_id',
                                          queryset=models.StageEntity.objects.filter(deleted=False, published=True),
                                          required=False, allow_null=True)
    entity_entity = serializers.PrimaryKeyRelatedField(
        queryset=models.StageEntityEntity.objects.filter(deleted=False, published=True, entity_a__deleted=False,
                                                         entity_a__published=True, entity_b__deleted=False,
                                                         entity_b__published=True,
                                                         entity_entity_collections__deleted=False,
                                                         entity_entity_collections__published=True,
                                                         entity_entity_collections__collection__deleted=False,
                                                         entity_entity_collections__collection__published=True,
                                                         entity_entity_collections__collection__source__deleted=False,
                                                         entity_entity_collections__collection__source__published=True).distinct(),
        required=False, allow_null=True)
    attribute = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StageAttribute.objects.filter(
        Q(finally_deleted=False, finally_published=True) & ~Q(attribute_type__data_type__string_id='complex')),
                                             required=True, allow_null=False)
    value_codebook_item = serializers.PrimaryKeyRelatedField(
        queryset=models.StageCodebookValue.objects.filter(deleted=False, published=True, codebook__deleted=False,
                                                          codebook__published=True,
                                                          codebook__attribute_types__deleted=False,
                                                          codebook__attribute_types__published=True).distinct(),
        required=False, allow_null=True)
    currency = serializers.SlugRelatedField(slug_field='code', queryset=models.StaticCurrency.objects.all(),
                                            required=False, allow_null=True)

    def create(self, validated_data):
        """
        We have a bit of extra checking around this in order to provide
        descriptive messages when something goes wrong, but this method is
        essentially just:
            return ExampleModel.objects.create(**validated_data)
        If there are many to many fields present on the instance then they
        cannot be set until the model is instantiated, in which case the
        implementation is like so:
            example_relationship = validated_data.pop('example_relationship')
            instance = ExampleModel.objects.create(**validated_data)
            instance.example_relationship = example_relationship
            return instance
        The default implementation also does not handle nested relationships.
        If you want to support writable nested relationships you'll need
        to write an explicit `.create()` method.
        """
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            # instance = ModelClass._default_manager.create(**validated_data)
            instance = ModelClass(**validated_data)
            instance.save()
        except TypeError:
            import traceback
            tb = traceback.format_exc()
            msg = (
                    'Got a `TypeError` when calling `%s.%s.create()`. '
                    'This may be because you have a writable field on the '
                    'serializer class that is not a valid argument to '
                    '`%s.%s.create()`. You may need to make the field '
                    'read-only, or override the %s.create() method to handle '
                    'this correctly.\nOriginal exception was:\n %s' %
                    (
                        ModelClass.__name__,
                        ModelClass._default_manager.name,
                        ModelClass.__name__,
                        ModelClass._default_manager.name,
                        self.__class__.__name__,
                        tb
                    )
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                field.set(value)

        return instance

    def update(self, instance, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('update', self, validated_data)
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        return instance

    class Meta:
        model = models.StageAttributeValue
        fields = ('entity',
                  'entity_entity',
                  'attribute',
                  'value_boolean',
                  'value_int',
                  'value_fixed_point',
                  'value_floating_point',
                  'value_string',
                  'value_text',
                  'value_datetime',
                  'value_date',
                  'value_geo_lat',
                  'value_geo_lon',
                  'value_range_int_from',
                  'value_range_int_to',
                  'value_range_fixed_point_from',
                  'value_range_fixed_point_to',
                  'value_range_floating_point_from',
                  'value_range_floating_point_to',
                  'value_range_datetime_from',
                  'value_range_datetime_to',
                  'value_range_date_from',
                  'value_range_date_to',
                  'value_codebook_item',
                  'currency',
                  )


class StageAttributeValueCreateUpdateWrapperSerializer(serializers.Serializer):
    entity = serializers.SlugRelatedField(slug_field='public_id',
                                          queryset=models.StageEntity.objects.filter(deleted=False, published=True),
                                          required=False, allow_null=True)
    entity_entity = serializers.PrimaryKeyRelatedField(
        queryset=models.StageEntityEntity.objects.filter(deleted=False, published=True, entity_a__deleted=False,
                                                         entity_a__published=True, entity_b__deleted=False,
                                                         entity_b__published=True,
                                                         entity_entity_collections__deleted=False,
                                                         entity_entity_collections__published=True,
                                                         entity_entity_collections__collection__deleted=False,
                                                         entity_entity_collections__collection__published=True,
                                                         entity_entity_collections__collection__source__deleted=False,
                                                         entity_entity_collections__collection__source__published=True).distinct(),
        required=False, allow_null=True)
    attribute = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StageAttribute.objects.filter(
        Q(finally_deleted=False, finally_published=True) & ~Q(attribute_type__data_type__string_id='complex')),
                                             required=True, allow_null=False)
    value = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    currency = serializers.SlugRelatedField(slug_field='code', queryset=models.StaticCurrency.objects.all(),
                                            required=False, allow_null=True)

    class Meta:
        fields = ('entity', 'entity_entity', 'attribute', 'value', 'currency')

    def create(self, validated_data):
        return super().create(validated_data=validated_data)

    def update(self, instance, validated_data):
        return super().update(instance=instance, validated_data=validated_data)

    def validate(self, data):
        """
        Check that the start is before the stop.
        """
        if data.get('entity') is None and data.get('entity_entity') is None:
            raise serializers.ValidationError({'entity': 'Entity or Entity Connection must be specified.'})
        elif data.get('entity') is not None and data.get('entity_entity') is not None:
            raise serializers.ValidationError({'entity': 'Only Entity or Entity Connection can be specified.'})

        if data.get('entity') is not None and not helpers.check_attribute_entity_type(data.get('attribute'),
                                                                                      data.get('entity').entity_type):
            raise serializers.ValidationError({'attribute': 'Given attribute does not belong to given entity.'})
        elif data.get('entity_entity') is not None and not helpers.check_attribute_collection(data.get('attribute'),
                                                                                              data.get(
                                                                                                  'entity_entity')):
            raise serializers.ValidationError(
                {'attribute': 'Given attribute does not belong to given Entity Connection.'})

        data_type = data.get('attribute').attribute_type.data_type.string_id

        if data_type not in const.DATA_TYPE_MAPPING_SIMPLE and data_type not in const.DATA_TYPE_MAPPING_COMPLEX:
            raise serializers.ValidationError({'attribute': 'Invalid data type.'})

        if data.get('currency') is not None:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) is not None and const.DATA_TYPE_MAPPING_SIMPLE.get(
                    data_type) != const.DATA_TYPE_FIXED_POINT:
                raise serializers.ValidationError({'attribute': 'Currency is set to invalid data type.'})
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) is not None and const.DATA_TYPE_MAPPING_COMPLEX.get(
                    data_type) != const.DATA_TYPE_RANGE_FIXED_POINT:
                raise serializers.ValidationError({'attribute': 'Currency is set to invalid data type.'})

        try:
            value_1, value_2, field_name_1, field_name_2 = helpers.get_attribute_value_serializer_data(data)
        except ValueError as e:
            raise serializers.ValidationError({'value': e})  # "not enough values to unpack (expected 2, got 1)"

        if value_1 is None and value_2 is None:
            raise serializers.ValidationError({'value': 'This field may not be blank.'})

        if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_GEO and (
                value_1 is None or value_2 is None):
            raise serializers.ValidationError({'value': 'Both fields may not be blank.'})

        try:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FIXED_POINT:
                value_1 = int(Decimal(value_1) * helpers.get_divider(data.get('attribute').attribute_type))
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FIXED_POINT:
                if value_1 is not None:
                    value_1 = int(Decimal(value_1) * helpers.get_divider(data.get('attribute').attribute_type))
                if value_2 is not None:
                    value_2 = int(Decimal(value_2) * helpers.get_divider(data.get('attribute').attribute_type))
        except InvalidOperation:
            raise serializers.ValidationError({'value': 'A valid number is required.'})

        if data.get('entity') is not None:
            tmp_data = {
                'entity': data.get('entity').public_id
            }
        else:
            tmp_data = {
                'entity_entity': data.get('entity_entity').id
            }
        tmp_data.update({
            'attribute': data.get('attribute').string_id,
        })
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            tmp_data.update({
                field_name_1: value_1
            })
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            tmp_data.update({
                field_name_1: value_1,
                field_name_2: value_2
            })
        if data.get('currency') is not None:
            tmp_data.update({
                'currency': data.get('currency').code
            })

        attribute_value_create_serializer = StageAttributeValueCreateUpdateSerializer(data=tmp_data)

        try:
            attribute_value_create_serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            errors = []
            error_data = {}
            for field, value in e.detail.items():
                if field.startswith('value_'):
                    if isinstance(value, list):
                        errors = errors + value
                    else:
                        errors.append(value)
                else:
                    error_data.update({
                        field: value
                    })
            if len(errors) > 0:
                error_data.update({
                    'value': errors
                })
            raise serializers.ValidationError(error_data)

        if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
            try:
                codebook_value_instance = models.StageCodebookValue.objects.get(pk=value_1, deleted=False,
                                                                                published=True, codebook__deleted=False,
                                                                                codebook__published=True,
                                                                                codebook__attribute_types__deleted=False,
                                                                                codebook__attribute_types__published=True)
            except models.StageCodebookValue.DoesNotExist:
                raise serializers.ValidationError({'value': 'Invalid value.'})
            if data.get('attribute').attribute_type.codebook != codebook_value_instance.codebook:
                raise serializers.ValidationError({'value': 'Value is from wrong codebook.'})
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            tmp_value_1 = None
            tmp_value_2 = None
            if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_INT:
                tmp_value_1 = attribute_value_create_serializer.validated_data.get('value_range_int_from')
                tmp_value_2 = attribute_value_create_serializer.validated_data.get('value_range_int_to')
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FIXED_POINT:
                tmp_value_1 = attribute_value_create_serializer.validated_data.get('value_range_fixed_point_from')
                tmp_value_2 = attribute_value_create_serializer.validated_data.get('value_range_fixed_point_to')
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FLOATING_POINT:
                tmp_value_1 = attribute_value_create_serializer.validated_data.get('value_range_floating_point_from')
                tmp_value_2 = attribute_value_create_serializer.validated_data.get('value_range_floating_point_to')
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATETIME:
                tmp_value_1 = attribute_value_create_serializer.validated_data.get('value_range_datetime_from')
                tmp_value_2 = attribute_value_create_serializer.validated_data.get('value_range_datetime_to')
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATE:
                tmp_value_1 = attribute_value_create_serializer.validated_data.get('value_range_date_from')
                tmp_value_2 = attribute_value_create_serializer.validated_data.get('value_range_date_to')
            if tmp_value_1 is not None and tmp_value_2 is not None and tmp_value_1 > tmp_value_2:
                raise serializers.ValidationError({'value': 'First value must be lower then second value.'})

        return data

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self._readable_fields

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except (SkipField, AttributeError) as e:
                if isinstance(e, AttributeError):
                    if field.field_name == 'value':
                        data_type = instance.attribute.attribute_type.data_type.string_id
                        if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
                            ret[field.field_name] = instance.value_codebook_item.id
                        else:
                            ret[field.field_name] = StageAttributeValueHelperSerializer().get_attribute_value(instance)
                    else:
                        raise e
                continue

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret


class StaticChangeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticChangeType
        fields = ('string_id', 'name')


class StageCodebookFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StageCodebook
        fields = ('url', 'string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageCodebookCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageCodebook
        fields = ('string_id', 'name')


class StageCodebookUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageCodebook
        fields = ()


class StageCodebookValueFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StageCodebookValue
        fields = ('url', 'id', 'value')


class StageCodebookValueCreateSerializer(serializers.ModelSerializer):
    codebook = serializers.SlugRelatedField(slug_field='string_id',
                                            queryset=models.StageCodebook.objects.filter(deleted=False, published=True,
                                                                                         is_closed=False),
                                            required=True, allow_null=False)

    class Meta:
        model = models.StageCodebookValue
        fields = ('id', 'codebook', 'value')


class StageCodebookValueUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageCodebookValue
        fields = ()


class StageCollectionFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StageCollection
        fields = ('url', 'string_id', 'name', 'quality')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageCollectionCreateSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(slug_field='string_id',
                                          queryset=models.StageSource.objects.filter(deleted=False, published=True),
                                          required=True, allow_null=False)
    collection_type = serializers.SlugRelatedField(slug_field='string_id',
                                                   queryset=models.StaticCollectionType.objects.all(), required=True,
                                                   allow_null=False)

    class Meta:
        model = models.StageCollection
        fields = ('string_id', 'name', 'source', 'collection_type', 'quality')


class StageCollectionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageCollection
        fields = ()


class StaticCollectionTypeFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticCollectionType
        fields = ('url', 'string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticCollectionTypeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticCollectionType
        fields = ('string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticCollectionTypeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticCollectionType
        fields = ()


class StaticConnectionTypeFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticConnectionType
        fields = ('url', 'string_id', 'name', 'reverse_name', 'potentially_pep')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticConnectionTypeCreateSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field='string_id',
                                            queryset=models.StaticConnectionTypeCategory.objects.all(), required=True,
                                            allow_null=False)

    class Meta:
        model = models.StaticConnectionType
        fields = ('string_id', 'name', 'reverse_name', 'potentially_pep', 'category')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticConnectionTypeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticConnectionType
        fields = ()


class StaticConnectionTypeCategoryFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticConnectionTypeCategory
        fields = ('url', 'string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticConnectionTypeCategorySerializer(serializers.HyperlinkedModelSerializer):
    connection_types = serializers.SerializerMethodField()

    def get_connection_types(self, obj):
        return StaticConnectionTypeFlatSerializer(obj.connection_types.all(), many=True,
                                                  context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StaticConnectionTypeCategory
        fields = ('url', 'string_id', 'name', 'connection_types')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticConnectionTypeCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticConnectionTypeCategory
        fields = ('string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticConnectionTypeCategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticConnectionTypeCategory
        fields = ()


class StaticCurrencyFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticCurrency
        fields = ('url', 'code', 'sign', 'sign_before_value')
        extra_kwargs = {
            'url': {'lookup_field': 'code'}
        }


class StaticCurrencyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticCurrency
        fields = ('code', 'sign', 'sign_before_value')


class StaticCurrencyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticCurrency
        fields = ()


class StaticDataTypeFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticDataType
        fields = ('url', 'string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageEntityCreateSerializer(serializers.ModelSerializer):
    entity_type = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StaticEntityType.objects.all(),
                                               required=True, allow_null=False)

    class Meta:
        model = models.StageEntity
        fields = ('public_id', 'entity_type', 'linked_potentially_pep')


class StageEntityCreateExtendedSerializer(serializers.ModelSerializer):
    entity_type = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StaticEntityType.objects.all(),
                                               required=True, allow_null=False)

    class Meta:
        model = models.StageEntity
        fields = ('public_id', 'entity_type', 'linked_potentially_pep', 'internal_slug', 'internal_slug_count')


class StageEntityCreateWrapperSerializer(serializers.Serializer):
    entity_type = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StaticEntityType.objects.all(),
                                               required=True, allow_null=False)
    linked_potentially_pep = serializers.BooleanField(default=False)
    vat_number = serializers.CharField(max_length=512, required=False, allow_null=True)
    name = serializers.CharField(max_length=512)
    last_name = serializers.CharField(max_length=512, required=False, allow_null=True)
    force_creation = serializers.BooleanField(default=False)

    class Meta:
        fields = ('entity_type', 'linked_potentially_pep', 'vat_number', 'name', 'last_name', 'force_creation')

    def create(self, validated_data):
        entity_type = validated_data.get('entity_type')

        internal_slug = validated_data.get('name')
        if entity_type.string_id == 'person':
            internal_slug = internal_slug + ' ' + validated_data.get('last_name')
        internal_slug = slugify(internal_slug.strip())

        if len(internal_slug) > 128:
            internal_slug = internal_slug[0:128]

        latest_entity = None

        try:
            latest_entity = models.StageEntity.objects.filter(internal_slug=internal_slug).latest('internal_slug_count')
        except models.StageEntity.DoesNotExist:
            pass

        if latest_entity is None:
            internal_slug_count = 1
        elif latest_entity.internal_slug_count is None:
            internal_slug_count = 2
        else:
            internal_slug_count = latest_entity.internal_slug_count + 1

        internal_slug_count_str = ''
        if internal_slug_count > 1:
            internal_slug_count_str = '-' + str(internal_slug_count)

        if len(internal_slug) > 128 - len(internal_slug_count_str):
            internal_slug_striped = internal_slug[0:(128 - len(internal_slug_count_str))]
        else:
            internal_slug_striped = internal_slug

        public_id = slugify(internal_slug_striped + internal_slug_count_str)

        data = {
            'public_id': public_id,
            'entity_type': validated_data.get('entity_type').string_id,
            'linked_potentially_pep': validated_data.get('linked_potentially_pep'),
            'internal_slug': internal_slug,
            'internal_slug_count': internal_slug_count
        }
        entity_create_serializer = StageEntityCreateExtendedSerializer(data=data)
        entity_create_serializer.is_valid(raise_exception=True)
        return entity_create_serializer.save()

    def update(self, instance, validated_data):
        return super().update(instance=instance, validated_data=validated_data)

    def validate(self, data):
        entity_type = data.get('entity_type')
        if (entity_type.string_id == 'person' or entity_type.string_id == 'legal_entity') and data.get(
                'vat_number') is not None:
            vat_number = data.get('vat_number')
            vat_number_hashed = hashlib.sha512((vat_number + const.VAT_NUMBER_SALT).encode('utf-8')).hexdigest()

            similar_entities = models.StageEntity.objects.filter((Q(attribute_values__value_string=vat_number,
                                                                    attribute_values__attribute__string_id='legal_entity_vat_number') |
                                                                  Q(attribute_values__value_string=vat_number_hashed,
                                                                    attribute_values__attribute__string_id='person_vat_number')) &
                                                                 Q(
                                                                     attribute_values__attribute__attribute=None)).distinct()

            if len(similar_entities) > 0:
                serializer = StageEntityFlatSerializer(similar_entities, many=True,
                                                       context={'request': self.context.get('request')})
                raise serializers.ValidationError({
                    'vat_number': 'Entity with VAT number Exists',
                    'entities': serializer.data,
                })

        if entity_type.string_id == 'person':
            if 'last_name' not in data:
                raise serializers.ValidationError({'last_name': 'This field is required.'})
            elif data.get('last_name') is None:
                raise serializers.ValidationError({'last_name': 'This field may not be null.'})
            elif data.get('last_name').strip() == '':
                raise serializers.ValidationError({'last_name': 'This field may not be blank.'})
        elif data.get('last_name') is not None:
            raise serializers.ValidationError({'last_name': 'This field must be not set for given entity type.'})

        if not data.get('force_creation'):
            internal_slug = data.get('name')
            if entity_type.string_id == 'person':
                internal_slug = internal_slug + ' ' + data.get('last_name')
            internal_slug = slugify(internal_slug.strip())

            if len(internal_slug) > 128:
                internal_slug = internal_slug[0:128]

            potential_similar_entities = models.StageEntity.objects.filter(internal_slug=internal_slug)

            if len(potential_similar_entities) > 0:
                serializer = StageEntityFlatSerializer(potential_similar_entities, many=True,
                                                       context={'request': self.context.get('request')})
                raise serializers.ValidationError({
                    'name': 'Similar entity exists.',
                    'entities': serializer.data,
                })

        return data

    def to_representation(self, instance):
        serializer = StageEntityCreateSerializer()
        return serializer.to_representation(instance)


class StageEntityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageEntity
        fields = ()


class StageEntityEntityCreateUpdateSerializer(serializers.ModelSerializer):
    entity_a = serializers.SlugRelatedField(slug_field='public_id',
                                            queryset=models.StageEntity.objects.filter(deleted=False, published=True),
                                            required=True, allow_null=False, label='Entity')
    connection_type = serializers.SlugRelatedField(slug_field='string_id',
                                                   queryset=models.StaticConnectionType.objects.all(), required=True,
                                                   allow_null=False, label='Is (Connection type)')
    entity_b = serializers.SlugRelatedField(slug_field='public_id',
                                            queryset=models.StageEntity.objects.filter(deleted=False, published=True),
                                            required=True, allow_null=False, label='For/in/of (Entity)')
    transaction_currency = serializers.SlugRelatedField(slug_field='code', queryset=models.StaticCurrency.objects.all(),
                                                        required=False, allow_null=True)

    class Meta:
        model = models.StageEntityEntity
        fields = ('id', 'entity_a', 'connection_type', 'entity_b', 'valid_from', 'valid_to', 'transaction_amount',
                  'transaction_currency', 'transaction_date')

    def create(self, validated_data):
        """
        We have a bit of extra checking around this in order to provide
        descriptive messages when something goes wrong, but this method is
        essentially just:
            return ExampleModel.objects.create(**validated_data)
        If there are many to many fields present on the instance then they
        cannot be set until the model is instantiated, in which case the
        implementation is like so:
            example_relationship = validated_data.pop('example_relationship')
            instance = ExampleModel.objects.create(**validated_data)
            instance.example_relationship = example_relationship
            return instance
        The default implementation also does not handle nested relationships.
        If you want to support writable nested relationships you'll need
        to write an explicit `.create()` method.
        """
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            # instance = ModelClass._default_manager.create(**validated_data)
            instance = ModelClass(**validated_data)
            instance.save()
        except TypeError:
            import traceback
            tb = traceback.format_exc()
            msg = (
                    'Got a `TypeError` when calling `%s.%s.create()`. '
                    'This may be because you have a writable field on the '
                    'serializer class that is not a valid argument to '
                    '`%s.%s.create()`. You may need to make the field '
                    'read-only, or override the %s.create() method to handle '
                    'this correctly.\nOriginal exception was:\n %s' %
                    (
                        ModelClass.__name__,
                        ModelClass._default_manager.name,
                        ModelClass.__name__,
                        ModelClass._default_manager.name,
                        self.__class__.__name__,
                        tb
                    )
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                field.set(value)

        return instance

    def update(self, instance, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('update', self, validated_data)
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(instance)

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)
        instance.save()

        return instance


class StageEntityEntityCreateUpdateWrapperSerializer(serializers.Serializer):
    entity_a = serializers.SlugRelatedField(slug_field='public_id',
                                            queryset=models.StageEntity.objects.filter(deleted=False, published=True),
                                            required=False, allow_null=True, label='Entity')
    connection_type = serializers.SlugRelatedField(slug_field='string_id',
                                                   queryset=models.StaticConnectionType.objects.all(), required=False,
                                                   allow_null=True, label='Is (Connection type)')
    entity_b = serializers.SlugRelatedField(slug_field='public_id',
                                            queryset=models.StageEntity.objects.filter(deleted=False, published=True),
                                            required=False, allow_null=True, label='For/in/of (Entity)')
    valid_from = serializers.DateField(required=False, allow_null=True)
    valid_to = serializers.DateField(required=False, allow_null=True)
    transaction_amount = serializers.DecimalField(required=False, allow_null=True, max_digits=22, decimal_places=4)
    transaction_currency = serializers.SlugRelatedField(slug_field='code', queryset=models.StaticCurrency.objects.all(),
                                                        required=False, allow_null=True)
    transaction_date = serializers.DateField(required=False, allow_null=True)
    update_connection = serializers.PrimaryKeyRelatedField(
        queryset=models.StageEntityEntity.objects.filter(entity_a__deleted=False,
                                                         entity_a__published=True, entity_b__deleted=False,
                                                         entity_b__published=True,
                                                         entity_entity_collections__deleted=False,
                                                         entity_entity_collections__published=True,
                                                         entity_entity_collections__collection__deleted=False,
                                                         entity_entity_collections__collection__published=True,
                                                         entity_entity_collections__collection__source__deleted=False,
                                                         entity_entity_collections__collection__source__published=True).distinct(),
        required=False, allow_null=True)
    force_creation = serializers.BooleanField(default=False)

    class Meta:
        fields = ('entity_a', 'connection_type', 'entity_b', 'valid_from', 'valid_to', 'transaction_amount',
                  'transaction_currency', 'transaction_date', 'update_connection', 'force_creation')

    def validate(self, data):
        errors = {}
        if data.get('update_connection') is None:
            if 'entity_a' not in data:
                errors.update({
                    'entity_a': _('This field is required.')
                })
            elif data.get('entity_a') is None:
                errors.update({
                    'entity_a': _('This field may not be null.')
                })
            if 'connection_type' not in data:
                errors.update({
                    'connection_type': _('This field is required.')
                })
            elif data.get('connection_type') is None:
                errors.update({
                    'connection_type': _('This field may not be null.')
                })
            if 'entity_b' not in data:
                errors.update({
                    'entity_b': _('This field is required.')
                })
            elif data.get('entity_b') is None:
                errors.update({
                    'entity_b': _('This field may not be null.')
                })
        else:
            if data.get('entity_a') is not None:
                errors.update({
                    'entity_a': _('This field must not be specified or must be null.')
                })
            if data.get('connection_type') is not None:
                errors.update({
                    'connection_type': _('This field must not be specified or must be null.')
                })
            if data.get('entity_b') is not None:
                errors.update({
                    'entity_b': _('This field must not be specified or must be null.')
                })
            if data.get('transaction_amount') is not None:
                errors.update({
                    'transaction_amount': _('This field must not be specified or must be null.')
                })
            if data.get('transaction_currency') is not None:
                errors.update({
                    'transaction_currency': _('This field must not be specified or must be null.')
                })
            if data.get('transaction_date') is not None:
                errors.update({
                    'transaction_date': _('This field must not be specified or must be null.')
                })
            if data.get('force_creation'):
                errors.update({
                    'force_creation': _('This field must not be specified or must be false.')
                })
        if errors:
            raise serializers.ValidationError(errors)

        if data.get('update_connection') is None and data.get('entity_a') == data.get('entity_b'):
            raise serializers.ValidationError({'entity_b': 'Must be different from entity_a.'})

        if data.get('valid_from') is not None and data.get('valid_to') is not None and data.get(
                'valid_from') > data.get('valid_to'):
            raise serializers.ValidationError({'valid_from': 'Must be lower then valid_to.'})

        if data.get('transaction_amount') is not None or data.get('transaction_currency') is not None or data.get(
                'transaction_date') is not None:
            if data.get('transaction_amount') is None:
                raise serializers.ValidationError({'transaction_amount': 'This field may not be blank.'})
            elif data.get('transaction_currency') is None:
                raise serializers.ValidationError({'transaction_currency': 'This field may not be blank.'})
            elif data.get('transaction_date') is None:
                raise serializers.ValidationError({'transaction_date': 'This field may not be blank.'})

        entity_a = data.get('entity_a')
        entity_b = data.get('entity_b')
        connection_type = data.get('connection_type')
        valid_from = data.get('valid_from')
        valid_to = data.get('valid_to')
        transaction_amount = data.get('transaction_amount')
        transaction_currency = data.get('transaction_currency')
        transaction_date = data.get('transaction_date')

        if data.get('update_connection') is None:
            exact_connections = models.StageEntityEntity.objects.filter(
                (Q(entity_a=entity_a, entity_b=entity_b) | Q(entity_a=entity_b, entity_b=entity_a)) & Q(
                    connection_type=connection_type, valid_from=valid_from, valid_to=valid_to,
                    transaction_amount=transaction_amount, transaction_currency=transaction_currency,
                    transaction_date=transaction_date))

            if (not data.get('force_creation') and len(exact_connections) > 0) or len(exact_connections) > 1:
                serializer = StageEntityEntityHelper2Serializer(exact_connections, many=True,
                                                                context={'request': self.context.get('request')})
                raise serializers.ValidationError({
                    api_settings.NON_FIELD_ERRORS_KEY: 'Exact connections exists.',
                    'connections': serializer.data,
                })

            if not data.get('force_creation'):
                if valid_from is not None and valid_to is not None:
                    similar_connections = models.StageEntityEntity.objects.filter(
                        (Q(entity_a=entity_a, entity_b=entity_b) | Q(entity_a=entity_b, entity_b=entity_a)) & Q(
                            deleted=False, published=True,
                            connection_type=connection_type, transaction_amount=transaction_amount,
                            transaction_currency=transaction_currency, transaction_date=transaction_date) & (
                                Q(valid_from__gt=valid_from, valid_to__lt=valid_to) | Q(valid_from__lt=valid_from,
                                                                                        valid_to__gt=valid_from) | Q(
                            valid_from__lt=valid_to, valid_to__gt=valid_to) | Q(valid_from__gt=valid_from,
                                                                                valid_from__lt=valid_to,
                                                                                valid_to=None) | Q(
                            valid_from=None, valid_to__gt=valid_from, valid_to__lt=valid_to) | Q(valid_from=None,
                                                                                                 valid_to=None)))
                elif valid_from is not None and valid_to is None:
                    similar_connections = models.StageEntityEntity.objects.filter(
                        (Q(entity_a=entity_a, entity_b=entity_b) | Q(entity_a=entity_b, entity_b=entity_a)) & Q(
                            deleted=False, published=True,
                            connection_type=connection_type,
                            transaction_amount=transaction_amount, transaction_currency=transaction_currency,
                            transaction_date=transaction_date) & (
                                Q(valid_from__lt=valid_from, valid_to__gt=valid_from) | Q(valid_from=None,
                                                                                          valid_to=None)))
                elif valid_from is None and valid_to is not None:
                    similar_connections = models.StageEntityEntity.objects.filter(
                        (Q(entity_a=entity_a, entity_b=entity_b) | Q(entity_a=entity_b, entity_b=entity_a)) & Q(
                            deleted=False, published=True,
                            connection_type=connection_type, transaction_amount=transaction_amount,
                            transaction_currency=transaction_currency, transaction_date=transaction_date) & (
                                Q(valid_from__lt=valid_to, valid_to__gt=valid_to) | Q(valid_from=None,
                                                                                      valid_to=None)))
                else:
                    similar_connections = models.StageEntityEntity.objects.filter(
                        (Q(entity_a=entity_a, entity_b=entity_b) | Q(entity_a=entity_b, entity_b=entity_a)) & Q(
                            deleted=False, published=True,
                            connection_type=connection_type, transaction_amount=transaction_amount,
                            transaction_currency=transaction_currency, transaction_date=transaction_date))
                if len(similar_connections) > 0:
                    serializer = StageEntityEntityHelper2Serializer(similar_connections, many=True,
                                                                    context={'request': self.context.get('request')})
                    raise serializers.ValidationError({
                        api_settings.NON_FIELD_ERRORS_KEY: 'Similar connections exists.',
                        'connections': serializer.data,
                    })
        else:
            update_connection = data.get('update_connection')
            if update_connection.valid_from != valid_from or update_connection.valid_to != valid_to:
                exact_connections = models.StageEntityEntity.objects.filter(
                    (Q(entity_a=update_connection.entity_a, entity_b=update_connection.entity_b) | Q(
                        entity_a=update_connection.entity_b, entity_b=update_connection.entity_a)) & Q(
                        connection_type=update_connection.connection_type, valid_from=valid_from, valid_to=valid_to,
                        transaction_amount=update_connection.transaction_amount,
                        transaction_currency=update_connection.transaction_currency,
                        transaction_date=update_connection.transaction_date))
                if len(exact_connections) > 1:
                    serializer = StageEntityEntityHelper2Serializer(exact_connections, many=True,
                                                                    context={'request': self.context.get('request')})
                    raise serializers.ValidationError({
                        api_settings.NON_FIELD_ERRORS_KEY: 'Exact connections exists.',
                        'connections': serializer.data,
                    })

        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = instance.id
        return ret


class StaticEntityTypeFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticEntityType
        fields = ('url', 'string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageEntityFlatSerializer(serializers.HyperlinkedModelSerializer):
    entity_type = StaticEntityTypeFlatSerializer()

    class Meta:
        model = models.StageEntity
        fields = ('url', 'public_id', 'entity_type', 'linked_potentially_pep', 'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'public_id'}
        }


# todo - ne koristi se
class StageSourceFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StageSource
        fields = ('url', 'string_id', 'name', 'quality')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageSourceCreateSerializer(serializers.ModelSerializer):
    source_type = serializers.SlugRelatedField(slug_field='string_id', queryset=models.StaticSourceType.objects.all(),
                                               required=True, allow_null=False)

    class Meta:
        model = models.StageSource
        fields = ('string_id', 'name', 'source_type', 'address', 'quality', 'contact', 'note')


class StageSourceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StageSource
        fields = ()


class StaticSourceTypeFlatSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.StaticSourceType
        fields = ('url', 'string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticSourceTypeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticSourceType
        fields = ('string_id', 'name')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StaticSourceTypeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StaticSourceType
        fields = ()


# - depth: 1

class StageAttributeFlatSerializer(serializers.HyperlinkedModelSerializer):
    entity_type = StaticEntityTypeFlatSerializer()
    collection = StageCollectionFlatSerializer()
    attribute = serializers.SerializerMethodField()

    def get_attribute(self, obj):
        if obj.attribute is None:
            return None
        return StageAttributeFlatSerializer(obj.attribute, context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttribute
        fields = ('url', 'string_id', 'name', 'entity_type', 'collection', 'attribute')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeTypeFlatSerializer(serializers.HyperlinkedModelSerializer):
    data_type = StaticDataTypeFlatSerializer()
    codebook = StageCodebookFlatSerializer()

    class Meta:
        model = models.StageAttributeType
        fields = ('url', 'string_id', 'name', 'data_type', 'codebook')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeTypeHelper1Serializer(serializers.ModelSerializer):
    data_type = StaticDataTypeFlatSerializer()
    codebook = StageCodebookFlatSerializer()
    fixed_point_decimal_places = serializers.SerializerMethodField()
    range_floating_point_from_inclusive = serializers.SerializerMethodField()
    range_floating_point_to_inclusive = serializers.SerializerMethodField()
    values_separator = serializers.SerializerMethodField()
    input_formats = serializers.SerializerMethodField()

    def get_fixed_point_decimal_places(self, obj):
        return helpers.get_fixed_point_decimal_places(obj)

    def get_range_floating_point_from_inclusive(self, obj):
        return helpers.get_range_floating_point_from_inclusive(obj)

    def get_range_floating_point_to_inclusive(self, obj):
        return helpers.get_range_floating_point_to_inclusive(obj)

    def get_values_separator(self, obj):
        return helpers.get_values_separator(obj)

    def get_input_formats(self, obj):
        return helpers.get_input_formats(obj)

    class Meta:
        model = models.StageAttributeType
        fields = ('string_id', 'name', 'data_type', 'codebook', 'fixed_point_decimal_places',
                  'range_floating_point_from_inclusive', 'range_floating_point_to_inclusive', 'values_separator',
                  'input_formats')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeValueCollectionCreateUpdateSerializer(serializers.ModelSerializer):
    collection = serializers.SlugRelatedField(slug_field='string_id',
                                              queryset=models.StageCollection.objects.filter(deleted=False,
                                                                                             published=True,
                                                                                             source__deleted=False,
                                                                                             source__published=True),
                                              required=True, allow_null=False)
    attribute_value = StageAttributeValueCreateUpdateWrapperSerializer()

    class Meta:
        model = models.StageAttributeValueCollection
        fields = ('collection', 'valid_from', 'valid_to', 'attribute_value')

    def validate(self, data):
        if data.get('valid_from') is not None and data.get('valid_to') is not None and data.get(
                'valid_from') > data.get('valid_to'):
            raise serializers.ValidationError({'valid_from': 'Must be lower then valid_to.'})
        return data

    def create(self, validated_data):
        attribute_value_data = validated_data.pop('attribute_value')
        data_type = attribute_value_data.get('attribute').attribute_type.data_type.string_id

        value_1, value_2, field_name_1, field_name_2 = helpers.get_attribute_value_serializer_data(attribute_value_data)

        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_BOOLEAN:
                value_1 = value_1[0].upper() + value_1[1:].lower()
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_INT:
                value_1 = int(value_1)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FIXED_POINT:
                value_1 = int(
                    Decimal(value_1) * helpers.get_divider(attribute_value_data.get('attribute').attribute_type))
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FLOATING_POINT:
                value_1 = float(value_1)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATETIME:
                value_1 = helpers.datetime_to_internal_value(self, value_1, utc)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATE:
                value_1 = DateField.to_internal_value(None, value_1)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
                value_1 = int(value_1)
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_GEO:
                value_1 = float(value_1)
                value_2 = float(value_2)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FIXED_POINT:
                if value_1 is not None:
                    value_1 = int(
                        Decimal(value_1) * helpers.get_divider(attribute_value_data.get('attribute').attribute_type))
                if value_2 is not None:
                    value_2 = int(
                        Decimal(value_2) * helpers.get_divider(attribute_value_data.get('attribute').attribute_type))
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FLOATING_POINT:
                if value_1 is not None:
                    value_1 = float(value_1)
                if value_2 is not None:
                    value_2 = float(value_2)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATETIME:
                if value_1 is not None:
                    value_1 = helpers.datetime_to_internal_value(self, value_1, utc)
                if value_2 is not None:
                    value_2 = helpers.datetime_to_internal_value(self, value_2, utc)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATE:
                if value_1 is not None:
                    value_1 = DateField.to_internal_value(None, value_1)
                if value_2 is not None:
                    value_2 = DateField.to_internal_value(None, value_2)

        if attribute_value_data.get('attribute').string_id == 'person_vat_number':
            value_1 = hashlib.sha512((value_1 + const.VAT_NUMBER_SALT).encode('utf-8')).hexdigest()

        data = {}
        data2 = {}
        if attribute_value_data.get('entity') is not None:
            data.update({
                'entity': attribute_value_data.get('entity').public_id
            })
            data2.update({
                'entity': attribute_value_data.get('entity')
            })
        if attribute_value_data.get('entity_entity') is not None:
            data.update({
                'entity_entity': attribute_value_data.get('entity_entity').id
            })
            data2.update({
                'entity_entity': attribute_value_data.get('entity_entity')
            })
        data.update({
            'attribute': attribute_value_data.get('attribute').string_id,
            field_name_1: value_1
        })
        data2.update({
            'attribute': attribute_value_data.get('attribute'),
            field_name_1: value_1
        })
        if attribute_value_data.get('currency') is not None:
            data.update({
                'currency': attribute_value_data.get('currency').code
            })
            data2.update({
                'currency': attribute_value_data.get('currency')
            })
        codebook_value_instance = None
        if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
            codebook_value_instance = models.StageCodebookValue.objects.get(pk=value_1, deleted=False, published=True,
                                                                            codebook__deleted=False,
                                                                            codebook__published=True,
                                                                            codebook__attribute_types__deleted=False,
                                                                            codebook__attribute_types__published=True)
            data2.update({
                field_name_1: codebook_value_instance
            })
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            data.update({
                field_name_2: value_2
            })
            data2.update({
                field_name_2: value_2
            })

        tmp_attribute_value_instances = models.StageAttributeValue(**data2)
        try:
            if attribute_value_data.get('entity') is not None:
                instance = self.Meta.model.objects.get(collection=validated_data.get('collection'),
                                                       attribute_value__entity=attribute_value_data.get('entity'),
                                                       attribute_value__attribute=attribute_value_data.get('attribute'))
            else:
                instance = self.Meta.model.objects.get(collection=validated_data.get('collection'),
                                                       attribute_value__entity_entity=attribute_value_data.get(
                                                           'entity_entity'),
                                                       attribute_value__attribute=attribute_value_data.get('attribute'))

            old_currency = instance.attribute_value.currency
            old_value_1 = instance.attribute_value.get_raw_first_value()
            old_value_2 = instance.attribute_value.get_raw_second_value()
            old_valid_from = instance.valid_from
            old_valid_to = instance.valid_to

            attribute_value_instance = instance.attribute_value
            attribute_value_instance_to_delete = None

            if str(tmp_attribute_value_instances.get_raw_value()) != str(attribute_value_instance.get_raw_value()):
                found = False
                if attribute_value_data.get('entity') is not None:
                    for item in models.StageAttributeValue.objects.filter(
                            ~Q(attribute_value_collections__collection=validated_data.get('collection')) & Q(
                                entity=attribute_value_data.get('entity'),
                                attribute=attribute_value_data.get('attribute'))).distinct():
                        if str(tmp_attribute_value_instances.get_raw_value()) == str(
                                item.get_raw_value()):
                            found = True
                            if not attribute_value_instance.attribute_value_collections.filter(
                                    ~Q(collection=validated_data.get('collection'))).exists():
                                attribute_value_instance_to_delete = attribute_value_instance
                            attribute_value_instance = item
                            break
                else:
                    for item in models.StageAttributeValue.objects.filter(
                            ~Q(attribute_value_collections__collection=validated_data.get('collection')) & Q(
                                entity_entity=attribute_value_data.get('entity_entity'),
                                attribute=attribute_value_data.get('attribute'))).distinct():
                        if str(tmp_attribute_value_instances.get_raw_value()) == str(
                                item.get_raw_value()):
                            found = True
                            if not attribute_value_instance.attribute_value_collections.filter(
                                    ~Q(collection=validated_data.get('collection'))).exists():
                                attribute_value_instance_to_delete = attribute_value_instance
                            attribute_value_instance = item
                            break
                if not found:
                    if attribute_value_instance.attribute_value_collections.filter(
                            ~Q(collection=validated_data.get('collection'))).exists():
                        attribute_value_instance = None
                    attribute_value_create_serializer = StageAttributeValueCreateUpdateSerializer(
                        attribute_value_instance, data=data)
                    attribute_value_create_serializer.is_valid(raise_exception=True)
                    attribute_value_instance = attribute_value_create_serializer.save()

            attribute_value_instance.save()
            instance.attribute_value = attribute_value_instance
            instance.valid_from = validated_data.get('valid_from')
            instance.valid_to = validated_data.get('valid_to')
            instance.deleted = False
            instance.published = True
            instance.save()

            if attribute_value_instance_to_delete is not None:
                attribute_value_instance_to_delete.delete()

            change_type_instance = models.StaticChangeType.objects.get(string_id='update')
            changeset_instance = models.LogChangeset.objects.create(collection=validated_data.get('collection'))
            if attribute_value_data.get('entity') is not None:
                change_data = {
                    'entity': attribute_value_data.get('entity')
                }
            else:
                change_data = {
                    'entity_entity': attribute_value_data.get('entity_entity')
                }
            change_data.update({
                'changeset': changeset_instance,
                'attribute': attribute_value_data.get('attribute'),
                'change_type': change_type_instance,
                'old_valid_from': old_valid_from,
                'new_valid_from': validated_data.get('valid_from'),
                'old_valid_to': old_valid_to,
                'new_valid_to': validated_data.get('valid_to'),
                'old_' + field_name_1: old_value_1,
                'new_' + field_name_1: value_1,
            })
            if old_currency is not None:
                change_data.update({
                    'old_currency': old_currency,
                })
            if codebook_value_instance is not None:
                change_data.update({
                    'new_' + field_name_1: codebook_value_instance,
                })
            elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
                change_data.update({
                    'old_' + field_name_2: old_value_2,
                    'new_' + field_name_2: value_2,
                })
            if attribute_value_data.get('currency') is not None:
                change_data.update({
                    'new_currency': attribute_value_data.get('currency'),
                })
            models.LogAttributeValueChange.objects.create(**change_data)
        except self.Meta.model.DoesNotExist:
            attribute_value_instance = None
            if attribute_value_data.get('entity') is not None:
                for item in models.StageAttributeValue.objects.filter(entity=attribute_value_data.get('entity'),
                                                                      attribute=attribute_value_data.get('attribute')):
                    if str(tmp_attribute_value_instances.get_raw_value()) == str(item.get_raw_value()):
                        attribute_value_instance = item
                        break
            else:
                for item in models.StageAttributeValue.objects.filter(
                        entity_entity=attribute_value_data.get('entity_entity'),
                        attribute=attribute_value_data.get('attribute')):
                    if str(tmp_attribute_value_instances.get_raw_value()) == str(item.get_raw_value()):
                        attribute_value_instance = item
                        break
            if attribute_value_instance is None:
                attribute_value_create_serializer = StageAttributeValueCreateUpdateSerializer(data=data)
                attribute_value_create_serializer.is_valid(raise_exception=True)
                attribute_value_instance = attribute_value_create_serializer.save()
                change_type_instance = models.StaticChangeType.objects.get(string_id='create')
            else:
                change_type_instance = models.StaticChangeType.objects.get(string_id='update')

            attribute_value_instance.save()
            ModelClass = self.Meta.model
            instance = ModelClass(**validated_data)
            instance.attribute_value = attribute_value_instance
            instance.save()

            changeset_instance = models.LogChangeset.objects.create(collection=validated_data.get('collection'))
            if attribute_value_data.get('entity') is not None:
                change_data = {
                    'entity': attribute_value_data.get('entity'),
                }
            else:
                change_data = {
                    'entity_entity': attribute_value_data.get('entity_entity'),
                }
            change_data.update({
                'changeset': changeset_instance,
                'attribute': attribute_value_data.get('attribute'),
                'change_type': change_type_instance,
                'new_valid_from': instance.valid_from,
                'new_valid_to': instance.valid_to,
                'new_' + field_name_1: value_1,
            })
            if codebook_value_instance is not None:
                change_data.update({
                    'new_' + field_name_1: codebook_value_instance,
                })
            elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
                change_data.update({
                    'new_' + field_name_2: value_2,
                })
            if attribute_value_data.get('currency') is not None:
                change_data.update({
                    'new_currency': attribute_value_data.get('currency')
                })
            models.LogAttributeValueChange.objects.create(**change_data)

        return instance


class StageCodebookValueSerializer(serializers.ModelSerializer):
    codebook = StageCodebookFlatSerializer()

    class Meta:
        model = models.StageCodebookValue
        fields = ('id', 'value', 'codebook')


class StaticConnectionTypeSerializer(serializers.HyperlinkedModelSerializer):
    category = StaticConnectionTypeCategoryFlatSerializer()

    class Meta:
        model = models.StaticConnectionType
        fields = ('url', 'string_id', 'name', 'reverse_name', 'potentially_pep', 'category')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageEntityEntityCollectionCreateUpdateSerializer(serializers.ModelSerializer):
    collection = serializers.SlugRelatedField(slug_field='string_id',
                                              queryset=models.StageCollection.objects.filter(deleted=False,
                                                                                             published=True,
                                                                                             source__deleted=False,
                                                                                             source__published=True),
                                              required=True, allow_null=False)
    entity_entity = StageEntityEntityCreateUpdateWrapperSerializer()

    class Meta:
        model = models.StageEntityEntityCollection
        fields = ('collection', 'entity_entity')

    def validate(self, data):
        entity_entity_data = data.get('entity_entity')
        valid_from = entity_entity_data.get('valid_from')
        valid_to = entity_entity_data.get('valid_to')
        update_connection = entity_entity_data.get('update_connection')
        collection = data.get('collection')

        if update_connection is not None:
            if update_connection.valid_from != valid_from or update_connection.valid_to != valid_to:
                if models.StageEntityEntity.objects.filter(
                        (Q(entity_a=update_connection.entity_a, entity_b=update_connection.entity_b) | Q(
                            entity_a=update_connection.entity_b, entity_b=update_connection.entity_a)) & Q(
                            connection_type=update_connection.connection_type, valid_from=valid_from, valid_to=valid_to,
                            transaction_amount=update_connection.transaction_amount,
                            transaction_currency=update_connection.transaction_currency,
                            transaction_date=update_connection.transaction_date)).exists():
                    if update_connection.entity_entity_collections.filter(~Q(collection=collection)).exists():
                        raise serializers.ValidationError({
                            'entity_entity': 'Can\'t update connection.'
                        })
        return data

    def create(self, validated_data):
        entity_entity_data = validated_data.pop('entity_entity')

        entity_a = entity_entity_data.get('entity_a')
        entity_b = entity_entity_data.get('entity_b')
        connection_type = entity_entity_data.get('connection_type')
        valid_from = entity_entity_data.get('valid_from')
        valid_to = entity_entity_data.get('valid_to')
        transaction_amount = entity_entity_data.get('transaction_amount')
        transaction_currency = entity_entity_data.get('transaction_currency')
        transaction_currency_code = None if transaction_currency is None else transaction_currency.code
        transaction_date = entity_entity_data.get('transaction_date')

        entity_entity_instance = entity_entity_data.get('update_connection')

        if entity_entity_instance is not None:
            if entity_entity_instance.valid_from == valid_from or entity_entity_instance.valid_to == valid_to:
                old_valid_from = entity_entity_instance.valid_from
                old_valid_to = entity_entity_instance.valid_to

                entity_entity_instance.deleted = False
                entity_entity_instance.published = True
                entity_entity_instance.save()

                try:
                    instance = models.StageEntityEntityCollection.objects.get(
                        collection=validated_data.get('collection'),
                        entity_entity=entity_entity_instance)
                    instance.deleted = False
                    instance.published = True
                    instance.save()
                except models.StageEntityEntityCollection.DoesNotExist:
                    ModelClass = self.Meta.model
                    instance = ModelClass(**validated_data)
                    instance.entity_entity = entity_entity_instance
                    instance.save()
            else:
                exact_connections = models.StageEntityEntity.objects.filter(
                    (Q(entity_a=entity_entity_instance.entity_a, entity_b=entity_entity_instance.entity_b) | Q(
                        entity_a=entity_entity_instance.entity_b, entity_b=entity_entity_instance.entity_a)) & Q(
                        connection_type=entity_entity_instance.connection_type, valid_from=valid_from,
                        valid_to=valid_to,
                        transaction_amount=entity_entity_instance.transaction_amount,
                        transaction_currency=entity_entity_instance.transaction_currency,
                        transaction_date=entity_entity_instance.transaction_date))

                if len(exact_connections) == 0:
                    old_valid_from = entity_entity_instance.valid_from
                    old_valid_to = entity_entity_instance.valid_to

                    entity_entity_instance.valid_from = valid_from
                    entity_entity_instance.valid_to = valid_to
                    entity_entity_instance.deleted = False
                    entity_entity_instance.published = True
                    entity_entity_instance.save()

                    try:
                        instance = models.StageEntityEntityCollection.objects.get(
                            collection=validated_data.get('collection'),
                            entity_entity=entity_entity_instance)
                        instance.deleted = False
                        instance.published = True
                        instance.save()
                    except models.StageEntityEntityCollection.DoesNotExist:
                        ModelClass = self.Meta.model
                        instance = ModelClass(**validated_data)
                        instance.entity_entity = entity_entity_instance
                        instance.save()
                else:
                    old_entity_entity_instance = entity_entity_instance
                    entity_entity_instance = exact_connections.first()

                    old_valid_from = old_entity_entity_instance.valid_from
                    old_valid_to = old_entity_entity_instance.valid_to

                    try:
                        instance = models.StageEntityEntityCollection.objects.get(
                            collection=validated_data.get('collection'),
                            entity_entity=entity_entity_instance)
                        try:
                            entity_entity_collection_instance2 = models.StageEntityEntityCollection.objects.get(
                                collection=validated_data.get('collection'),
                                entity_entity=old_entity_entity_instance)
                            entity_entity_collection_instance2.delete()
                        except models.StageEntityEntityCollection.DoesNotExist:
                            pass
                        instance.save()
                    except models.StageEntityEntityCollection.DoesNotExist:
                        try:
                            instance = models.StageEntityEntityCollection.objects.get(
                                collection=validated_data.get('collection'),
                                entity_entity=old_entity_entity_instance)
                            instance.entity_entity = entity_entity_instance
                            instance.save()
                        except models.StageEntityEntityCollection.DoesNotExist:
                            ModelClass = self.Meta.model
                            instance = ModelClass(**validated_data)
                            instance.entity_entity = entity_entity_instance
                            instance.save()

                    entity_entity_instance.save()

                    for old_attribute_value_collection in models.StageAttributeValueCollection.objects.filter(
                            attribute_value__entity_entity=old_entity_entity_instance):
                        try:
                            attribute_value_collection_instance = models.StageAttributeValueCollection.objects.get(
                                collection=old_attribute_value_collection.collection,
                                attribute_value__entity_entity=entity_entity_instance,
                                attribute_value__attribute=old_attribute_value_collection.attribute_value.attribute)

                            if str(old_attribute_value_collection.attribute_vale.get_raw_value()) == str(
                                    attribute_value_collection_instance.attribute_value.get_raw_value()):
                                changed = False
                                if old_attribute_value_collection.created_at < attribute_value_collection_instance.created_at:
                                    attribute_value_collection_instance.created_at = old_attribute_value_collection.created_at
                                    changed = True
                                if old_attribute_value_collection.updated_at > attribute_value_collection_instance.updated_at:
                                    attribute_value_collection_instance.updated_at = old_attribute_value_collection.updated_at
                                    attribute_value_collection_instance.valid_from = old_attribute_value_collection.valid_from
                                    attribute_value_collection_instance.valid_to = old_attribute_value_collection.valid_to
                                    changed = True
                                if changed:
                                    attribute_value_collection_instance.save()

                                old_attribute_value_instance = old_attribute_value_collection.attribute_value
                                old_collection = old_attribute_value_collection.collection
                                old_attribute_value_collection.delete()

                                if not old_attribute_value_instance.attribute_value_collections.filter(
                                        ~Q(collection=old_collection)).exists():
                                    old_attribute_value_instance.delete()
                            else:
                                if old_attribute_value_collection.updated_at > attribute_value_collection_instance.updated_at:
                                    attribute_value_instance = attribute_value_collection_instance.attribute_value

                                    changeset_instance = models.LogChangeset.objects.create(
                                        collection=validated_data.get('collection'))

                                    attribute_value_change = models.LogAttributeValueChange()
                                    attribute_value_change.changeset = changeset_instance
                                    attribute_value_change.change_type = models.StaticChangeType.objects.get(
                                        string_id='update')
                                    attribute_value_change.entity_entity = entity_entity_instance
                                    attribute_value_change.attribute = attribute_value_instance.attribute

                                    attribute_value_change.old_valid_from = attribute_value_collection_instance.valid_from
                                    attribute_value_change.old_valid_to = attribute_value_collection_instance.valid_to
                                    attribute_value_change.old_value_boolean = attribute_value_instance.value_boolean
                                    attribute_value_change.old_value_int = attribute_value_instance.value_int
                                    attribute_value_change.old_value_fixed_point = attribute_value_instance.value_fixed_point
                                    attribute_value_change.old_value_floating_point = attribute_value_instance.value_floating_point
                                    attribute_value_change.old_value_string = attribute_value_instance.value_string
                                    attribute_value_change.old_value_text = attribute_value_instance.value_text
                                    attribute_value_change.old_value_datetime = attribute_value_instance.value_datetime
                                    attribute_value_change.old_value_date = attribute_value_instance.value_date
                                    attribute_value_change.old_value_geo_lat = attribute_value_instance.value_geo_lat
                                    attribute_value_change.old_value_geo_lon = attribute_value_instance.value_geo_lon
                                    attribute_value_change.old_value_range_int_from = attribute_value_instance.value_range_int_from
                                    attribute_value_change.old_value_range_int_to = attribute_value_instance.value_range_int_to
                                    attribute_value_change.old_value_range_fixed_point_from = attribute_value_instance.value_range_fixed_point_from
                                    attribute_value_change.old_value_range_fixed_point_to = attribute_value_instance.value_range_fixed_point_to
                                    attribute_value_change.old_value_range_floating_point_from = attribute_value_instance.value_range_floating_point_from
                                    attribute_value_change.old_value_range_floating_point_to = attribute_value_instance.value_range_floating_point_to
                                    attribute_value_change.old_value_range_datetime_from = attribute_value_instance.value_range_datetime_from
                                    attribute_value_change.old_value_range_datetime_to = attribute_value_instance.value_range_datetime_to
                                    attribute_value_change.old_value_range_date_from = attribute_value_instance.value_range_date_from
                                    attribute_value_change.old_value_range_date_to = attribute_value_instance.value_range_date_to
                                    attribute_value_change.old_value_codebook_item = attribute_value_instance.value_codebook_item
                                    attribute_value_change.old_currency = attribute_value_instance.currency

                                    attribute_value_instance.value_boolean = old_attribute_value_collection.attribute_value.value_boolean
                                    attribute_value_instance.value_int = old_attribute_value_collection.attribute_value.value_int
                                    attribute_value_instance.value_fixed_point = old_attribute_value_collection.attribute_value.value_fixed_point
                                    attribute_value_instance.value_floating_point = old_attribute_value_collection.attribute_value.value_floating_point
                                    attribute_value_instance.value_string = old_attribute_value_collection.attribute_value.value_string
                                    attribute_value_instance.value_text = old_attribute_value_collection.attribute_value.value_text
                                    attribute_value_instance.value_datetime = old_attribute_value_collection.attribute_value.value_datetime
                                    attribute_value_instance.value_date = old_attribute_value_collection.attribute_value.value_date
                                    attribute_value_instance.value_geo_lat = old_attribute_value_collection.attribute_value.value_geo_lat
                                    attribute_value_instance.value_geo_lon = old_attribute_value_collection.attribute_value.value_geo_lon
                                    attribute_value_instance.value_range_int_from = old_attribute_value_collection.attribute_value.value_range_int_from
                                    attribute_value_instance.value_range_int_to = old_attribute_value_collection.attribute_value.value_range_int_to
                                    attribute_value_instance.value_range_fixed_point_from = old_attribute_value_collection.attribute_value.value_range_fixed_point_from
                                    attribute_value_instance.value_range_fixed_point_to = old_attribute_value_collection.attribute_value.value_range_fixed_point_to
                                    attribute_value_instance.value_range_floating_point_from = old_attribute_value_collection.attribute_value.value_range_floating_point_from
                                    attribute_value_instance.value_range_floating_point_to = old_attribute_value_collection.attribute_value.value_range_floating_point_to
                                    attribute_value_instance.value_range_datetime_from = old_attribute_value_collection.attribute_value.value_range_datetime_from
                                    attribute_value_instance.value_range_datetime_to = old_attribute_value_collection.attribute_value.value_range_datetime_to
                                    attribute_value_instance.value_range_date_from = old_attribute_value_collection.attribute_value.value_range_date_from
                                    attribute_value_instance.value_range_date_to = old_attribute_value_collection.attribute_value.value_range_date_to
                                    attribute_value_instance.value_codebook_item = old_attribute_value_collection.attribute_value.value_codebook_item
                                    attribute_value_instance.currency = old_attribute_value_collection.attribute_value.currency

                                    attribute_value_instance.save()

                                    attribute_value_collection_instance.updated_at = old_attribute_value_collection.updated_at
                                    attribute_value_collection_instance.valid_from = old_attribute_value_collection.valid_from
                                    attribute_value_collection_instance.valid_to = old_attribute_value_collection.valid_to
                                    if old_attribute_value_collection.created_at < attribute_value_collection_instance.created_at:
                                        attribute_value_collection_instance.created_at = old_attribute_value_collection.created_at
                                    attribute_value_collection_instance.save()

                                    attribute_value_change.new_valid_from = old_attribute_value_collection.valid_from
                                    attribute_value_change.new_valid_to = old_attribute_value_collection.valid_to
                                    attribute_value_change.new_value_boolean = old_attribute_value_collection.attribute_value.value_boolean
                                    attribute_value_change.new_value_int = old_attribute_value_collection.attribute_value.value_int
                                    attribute_value_change.new_value_fixed_point = old_attribute_value_collection.attribute_value.value_fixed_point
                                    attribute_value_change.new_value_floating_point = old_attribute_value_collection.attribute_value.value_floating_point
                                    attribute_value_change.new_value_string = old_attribute_value_collection.attribute_value.value_string
                                    attribute_value_change.new_value_text = old_attribute_value_collection.attribute_value.value_text
                                    attribute_value_change.new_value_datetime = old_attribute_value_collection.attribute_value.value_datetime
                                    attribute_value_change.new_value_date = old_attribute_value_collection.attribute_value.value_date
                                    attribute_value_change.new_value_geo_lat = old_attribute_value_collection.attribute_value.value_geo_lat
                                    attribute_value_change.new_value_geo_lon = old_attribute_value_collection.attribute_value.value_geo_lon
                                    attribute_value_change.new_value_range_int_from = old_attribute_value_collection.attribute_value.value_range_int_from
                                    attribute_value_change.new_value_range_int_to = old_attribute_value_collection.attribute_value.value_range_int_to
                                    attribute_value_change.new_value_range_fixed_point_from = old_attribute_value_collection.attribute_value.value_range_fixed_point_from
                                    attribute_value_change.new_value_range_fixed_point_to = old_attribute_value_collection.attribute_value.value_range_fixed_point_to
                                    attribute_value_change.new_value_range_floating_point_from = old_attribute_value_collection.attribute_value.value_range_floating_point_from
                                    attribute_value_change.new_value_range_floating_point_to = old_attribute_value_collection.attribute_value.value_range_floating_point_to
                                    attribute_value_change.new_value_range_datetime_from = old_attribute_value_collection.attribute_value.value_range_datetime_from
                                    attribute_value_change.new_value_range_datetime_to = old_attribute_value_collection.attribute_value.value_range_datetime_to
                                    attribute_value_change.new_value_range_date_from = old_attribute_value_collection.attribute_value.value_range_date_from
                                    attribute_value_change.new_value_range_date_to = old_attribute_value_collection.attribute_value.value_range_date_to
                                    attribute_value_change.new_value_codebook_item = old_attribute_value_collection.attribute_value.value_codebook_item
                                    attribute_value_change.new_currency = old_attribute_value_collection.attribute_value.currency

                                    attribute_value_change.save()
                                elif old_attribute_value_collection.created_at < attribute_value_collection_instance.created_at:
                                    attribute_value_collection_instance.created_at = old_attribute_value_collection.created_at
                                    attribute_value_collection_instance.save()

                                old_attribute_value_instance = old_attribute_value_collection.attribute_value
                                old_collection = old_attribute_value_collection.collection
                                old_attribute_value_collection.delete()

                                if not old_attribute_value_instance.attribute_value_collections.filter(
                                        ~Q(collection=old_collection)).exists():
                                    old_attribute_value_instance.delete()
                        except models.StageAttributeValueCollection.DoesNotExist:
                            attribute_value_instance = None
                            for attribute_value in models.StageAttributeValue.objects.filter(
                                    entity_entity=entity_entity_instance,
                                    attribute=old_attribute_value_collection.attribute_value.attribute):
                                if str(old_attribute_value_collection.attribute_vale.get_raw_value()) == str(
                                        attribute_value.get_raw_value()):
                                    attribute_value_instance = attribute_value
                                    break

                            if attribute_value_instance is None:
                                attribute_value_instance = old_attribute_value_collection.attribute_value
                                attribute_value_instance.entity_entity = entity_entity_instance
                                attribute_value_instance.save()
                            else:
                                old_attribute_value_instance = old_attribute_value_collection.attribute_value
                                old_attribute_value_collection.attribute_value = attribute_value_instance
                                old_attribute_value_collection.save()
                                if not old_attribute_value_instance.attribute_value_collections.filter(
                                        ~Q(collection=old_attribute_value_collection.collection)).exists():
                                    old_attribute_value_instance.delete()

                    models.LogEntityEntityChange.objects.filter(entity_entity=old_entity_entity_instance).update(
                        entity_entity=entity_entity_instance)

                    models.LogAttributeValueChange.objects.filter(entity_entity=old_entity_entity_instance).update(
                        entity_entity=entity_entity_instance)

                    old_entity_entity_instance.delete()

            change_type_instance = models.StaticChangeType.objects.get(string_id='update')
        else:
            exact_connections = models.StageEntityEntity.objects.filter(
                (Q(entity_a=entity_a, entity_b=entity_b) | Q(entity_a=entity_b, entity_b=entity_a)) & Q(
                    connection_type=connection_type, valid_from=valid_from, valid_to=valid_to,
                    transaction_amount=transaction_amount, transaction_currency=transaction_currency,
                    transaction_date=transaction_date))
            if len(exact_connections) > 0:
                entity_entity_instance = exact_connections.first()

                changed = False
                if entity_entity_instance.deleted:
                    entity_entity_instance.deleted = False
                    changed = True
                if not entity_entity_instance.published:
                    entity_entity_instance.published = True
                    changed = True
                if changed:
                    entity_entity_instance.save()

                change_type_instance = models.StaticChangeType.objects.get(string_id='update')
                old_valid_from = entity_entity_instance.valid_from
                old_valid_to = entity_entity_instance.valid_to

                try:
                    instance = models.StageEntityEntityCollection.objects.get(
                        collection=validated_data.get('collection'), entity_entity=entity_entity_instance)

                    changed = False
                    if instance.deleted:
                        instance.deleted = False
                        changed = True
                    if not instance.published:
                        instance.published = True
                        changed = True
                    if changed:
                        instance.save()

                except models.StageEntityEntityCollection.DoesNotExist:
                    ModelClass = self.Meta.model
                    instance = ModelClass(**validated_data)
                    instance.entity_entity = entity_entity_instance
                    instance.save()
            else:
                data = {
                    'entity_a': entity_a.public_id,
                    'connection_type': connection_type.string_id,
                    'entity_b': entity_b.public_id,
                    'transaction_amount': transaction_amount,
                    'transaction_currency': transaction_currency_code,
                    'transaction_date': transaction_date,
                    'valid_from': valid_from,
                    'valid_to': valid_to,
                }

                entity_entity_create_serializer = StageEntityEntityCreateUpdateSerializer(data=data)
                entity_entity_create_serializer.is_valid(raise_exception=True)
                entity_entity_instance = entity_entity_create_serializer.save()
                change_type_instance = models.StaticChangeType.objects.get(string_id='create')
                old_valid_from = None
                old_valid_to = None

                ModelClass = self.Meta.model
                instance = ModelClass(**validated_data)
                instance.entity_entity = entity_entity_instance
                instance.save()

        changeset_instance = models.LogChangeset.objects.create(collection=validated_data.get('collection'))
        change_data = {
            'changeset': changeset_instance,
            'change_type': change_type_instance,
            'old_valid_from': old_valid_from,
            'new_valid_from': valid_from,
            'old_valid_to': old_valid_to,
            'new_valid_to': valid_to,
            'entity_entity': entity_entity_instance
        }
        models.LogEntityEntityChange.objects.create(**change_data)

        return instance


class StageSourceSerializer(serializers.HyperlinkedModelSerializer):
    source_type = StaticSourceTypeFlatSerializer()
    collections = serializers.SerializerMethodField()

    def get_collections(self, obj):
        # we use prefetch_related
        '''
        return StageCollectionHelper2Serializer(
            obj.collections.select_related('collection_type').filter(deleted=False, published=True), many=True,
            context={'request': self.context.get('request')}).data
        '''
        return StageCollectionHelper2Serializer(obj.collections.all(), many=True,
                                                context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageSource
        fields = (
            'url', 'string_id', 'name', 'description', 'source_type', 'address', 'quality', 'collections', 'created_at',
            'updated_at', 'last_in_log')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageSourceHelperSerializer(serializers.HyperlinkedModelSerializer):
    source_type = StaticSourceTypeFlatSerializer()

    class Meta:
        model = models.StageSource
        fields = (
            'url', 'string_id', 'name', 'description', 'source_type', 'address', 'quality', 'created_at', 'updated_at',
            'last_in_log')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


# - depth: 2


class StageAttributeSerializer(serializers.HyperlinkedModelSerializer):
    attribute_type = StageAttributeTypeFlatSerializer()
    entity_type = StaticEntityTypeFlatSerializer()
    collection = StageCollectionFlatSerializer()
    attribute = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    def get_attribute(self, obj):
        if obj.attribute is None:
            return None
        return StageAttributeHelper1Serializer(obj.attribute, context={'request': self.context.get('request')}).data

    def get_attributes(self, obj):
        return StageAttributeHelper4Serializer(
            obj.attributes.filter(finally_deleted=False, finally_published=True).order_by('order_number'),
            many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttribute
        fields = ('url', 'string_id', 'name', 'attribute_type', 'entity_type', 'collection', 'attribute', 'attributes',
                  'order_number', 'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeHelper4Serializer(serializers.HyperlinkedModelSerializer):
    attribute_type = StageAttributeTypeFlatSerializer()
    entity_type = StaticEntityTypeFlatSerializer()
    collection = StageCollectionFlatSerializer()
    attributes = serializers.SerializerMethodField()

    def get_attributes(self, obj):
        return StageAttributeHelper4Serializer(
            obj.attributes.filter(finally_deleted=False, finally_published=True).order_by('order_number'),
            many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttribute
        fields = ('url', 'string_id', 'name', 'attribute_type', 'entity_type', 'collection', 'attributes',
                  'order_number', 'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeHelper2Serializer(serializers.HyperlinkedModelSerializer):
    attribute_type = StageAttributeTypeHelper1Serializer()
    attributes = serializers.SerializerMethodField()

    def get_attributes(self, obj):
        return StageAttributeHelper2Serializer(
            obj.attributes.select_related('attribute_type__data_type').select_related(
                'attribute_type__codebook').filter(finally_deleted=False, finally_published=True).order_by(
                'order_number'), many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttribute
        fields = (
            'url', 'string_id', 'name', 'attribute_type', 'order_number', 'attributes', 'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeTypeSerializer(serializers.HyperlinkedModelSerializer):
    data_type = StaticDataTypeFlatSerializer()
    codebook = StageCodebookFlatSerializer()
    fixed_point_decimal_places = serializers.SerializerMethodField()
    range_floating_point_from_inclusive = serializers.SerializerMethodField()
    range_floating_point_to_inclusive = serializers.SerializerMethodField()
    values_separator = serializers.SerializerMethodField()
    input_formats = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    def get_fixed_point_decimal_places(self, obj):
        return helpers.get_fixed_point_decimal_places(obj)

    def get_range_floating_point_from_inclusive(self, obj):
        return helpers.get_range_floating_point_from_inclusive(obj)

    def get_range_floating_point_to_inclusive(self, obj):
        return helpers.get_range_floating_point_to_inclusive(obj)

    def get_values_separator(self, obj):
        return helpers.get_values_separator(obj)

    def get_input_formats(self, obj):
        return helpers.get_input_formats(obj)

    def get_attributes(self, obj):
        return StageAttributeHelper1Serializer(
            obj.attributes.filter(finally_deleted=False, finally_published=True).order_by('order_number'),
            many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttributeType
        fields = ('url', 'string_id', 'name', 'data_type', 'codebook', 'fixed_point_decimal_places',
                  'range_floating_point_from_inclusive', 'range_floating_point_to_inclusive', 'values_separator',
                  'input_formats', 'attributes')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeTypeHelper2Serializer(serializers.ModelSerializer):
    data_type = StaticDataTypeFlatSerializer()
    fixed_point_decimal_places = serializers.SerializerMethodField()
    range_floating_point_from_inclusive = serializers.SerializerMethodField()
    range_floating_point_to_inclusive = serializers.SerializerMethodField()
    values_separator = serializers.SerializerMethodField()
    input_formats = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    def get_fixed_point_decimal_places(self, obj):
        return helpers.get_fixed_point_decimal_places(obj)

    def get_range_floating_point_from_inclusive(self, obj):
        return helpers.get_range_floating_point_from_inclusive(obj)

    def get_range_floating_point_to_inclusive(self, obj):
        return helpers.get_range_floating_point_to_inclusive(obj)

    def get_values_separator(self, obj):
        return helpers.get_values_separator(obj)

    def get_input_formats(self, obj):
        return helpers.get_input_formats(obj)

    def get_attributes(self, obj):
        return StageAttributeHelper1Serializer(
            obj.attributes.filter(finally_deleted=False, finally_published=True).order_by('order_number'),
            many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttributeType
        fields = ('string_id', 'name', 'data_type', 'fixed_point_decimal_places',
                  'range_floating_point_from_inclusive', 'range_floating_point_to_inclusive', 'values_separator',
                  'input_formats', 'attributes')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageCollectionHelperSerializer(serializers.HyperlinkedModelSerializer):
    source = StageSourceHelperSerializer()
    collection_type = StaticCollectionTypeFlatSerializer()

    class Meta:
        model = models.StageCollection
        fields = (
            'url', 'string_id', 'name', 'description', 'source', 'collection_type', 'quality', 'created_at',
            'updated_at', 'last_in_log')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageCollectionHelper2Serializer(serializers.HyperlinkedModelSerializer):
    collection_type = StaticCollectionTypeFlatSerializer()

    class Meta:
        model = models.StageCollection
        fields = (
            'url', 'string_id', 'name', 'description', 'collection_type', 'quality', 'created_at', 'updated_at',
            'last_in_log')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


# - depth: 3

class StageAttributeHelper1Serializer(serializers.HyperlinkedModelSerializer):
    attribute_type = StageAttributeTypeFlatSerializer()
    entity_type = StaticEntityTypeFlatSerializer()
    collection = StageCollectionFlatSerializer()
    attribute = serializers.SerializerMethodField()

    def get_attribute(self, obj):
        if obj.attribute is None:
            return None
        return StageAttributeHelper1Serializer(obj.attribute, context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttribute
        fields = ('url', 'string_id', 'name', 'attribute_type', 'entity_type', 'collection', 'attribute', 'created_at',
                  'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class LogAttributeValueChangeHelperSerializer(serializers.ModelSerializer):
    old_value = serializers.SerializerMethodField()
    new_value = serializers.SerializerMethodField()
    change_type = StaticChangeTypeSerializer()
    collection = serializers.SerializerMethodField()
    old_currency = StaticCurrencyFlatSerializer()
    new_currency = StaticCurrencyFlatSerializer()
    created_at = serializers.SerializerMethodField()
    data_type = serializers.SerializerMethodField()

    def get_old_value(self, obj):
        ret = None
        attribute_type_instance = obj.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_BOOLEAN:
                ret = obj.old_value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_INT:
                ret = obj.old_value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FIXED_POINT:
                ret = obj.old_value_fixed_point
                if ret is not None:
                    ret = ret / helpers.get_divider(attribute_type_instance)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FLOATING_POINT:
                ret = obj.old_value_floating_point
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_STRING:
                ret = obj.old_value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_TEXT:
                ret = obj.old_value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATETIME:
                ret = helpers.datetime_to_representation(self, obj.old_value_datetime)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATE:
                ret = DateField.to_representation(None, obj.old_value_date)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
                if obj.old_value_codebook_item is not None:
                    ret = StageCodebookValueFlatSerializer(obj.old_value_codebook_item,
                                                           context={'request': self.context.get('request')}).data
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_GEO:
                old_value_geo_lat = obj.old_value_geo_lat if obj.old_value_geo_lat is not None else 'null'
                old_value_geo_lon = obj.old_value_geo_lon if obj.old_value_geo_lon is not None else 'null'
                ret = '%s%s%s' % (old_value_geo_lat, helpers.get_api_geo_values_separator(), old_value_geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_INT:
                old_value_range_int_from = obj.old_value_range_int_from if obj.old_value_range_int_from is not None else 'null'
                old_value_range_int_to = obj.old_value_range_int_to if obj.old_value_range_int_to is not None else 'null'
                ret = '%s%s%s' % (
                    old_value_range_int_from, helpers.get_api_range_values_separator(), old_value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                old_value_from = obj.old_value_range_fixed_point_from
                if old_value_from is not None:
                    old_value_from = old_value_from / divider
                else:
                    old_value_from = 'null'
                old_value_to = obj.old_value_range_fixed_point_to
                if old_value_to is not None:
                    old_value_to = old_value_to / divider
                else:
                    old_value_to = 'null'
                ret = '%s%s%s' % (old_value_from, helpers.get_api_range_values_separator(), old_value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FLOATING_POINT:
                old_value_range_floating_point_from = obj.old_value_range_floating_point_from if obj.old_value_range_floating_point_from is not None else 'null'
                old_value_range_floating_point_to = obj.old_value_range_floating_point_to if obj.old_value_range_floating_point_to is not None else 'null'
                ret = '%s%s%s' % (
                    old_value_range_floating_point_from, helpers.get_api_range_values_separator(),
                    old_value_range_floating_point_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATETIME:
                old_value_range_datetime_from = helpers.datetime_to_representation(self,
                                                                                   obj.old_value_range_datetime_from) if obj.old_value_range_datetime_from is not None else 'null'
                old_value_range_datetime_to = helpers.datetime_to_representation(self,
                                                                                 obj.old_value_range_datetime_to) if obj.old_value_range_datetime_to is not None else 'null'
                ret = '%s%s%s' % (
                    old_value_range_datetime_from, helpers.get_api_range_values_separator(),
                    old_value_range_datetime_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATE:
                old_value_range_date_from = DateField.to_representation(None,
                                                                        obj.old_value_range_date_from) if obj.old_value_range_date_from is not None else 'null'
                old_value_range_date_to = DateField.to_representation(None,
                                                                      obj.old_value_range_date_to) if obj.old_value_range_date_to is not None else 'null'
                ret = '%s%s%s' % (
                    old_value_range_date_from, helpers.get_api_range_values_separator(), old_value_range_date_to)
        return ret

    def get_new_value(self, obj):
        ret = None
        attribute_type_instance = obj.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_BOOLEAN:
                ret = obj.new_value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_INT:
                ret = obj.new_value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FIXED_POINT:
                ret = obj.new_value_fixed_point
                if ret is not None:
                    ret = ret / helpers.get_divider(attribute_type_instance)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FLOATING_POINT:
                ret = obj.new_value_floating_point
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_STRING:
                ret = obj.new_value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_TEXT:
                ret = obj.new_value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATETIME:
                ret = helpers.datetime_to_representation(self, obj.new_value_datetime)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATE:
                ret = DateField.to_representation(None, obj.new_value_date)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
                if obj.new_value_codebook_item is not None:
                    ret = StageCodebookValueFlatSerializer(obj.new_value_codebook_item,
                                                           context={'request': self.context.get('request')}).data
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_GEO:
                new_value_geo_lat = obj.new_value_geo_lat if obj.new_value_geo_lat is not None else 'null'
                new_value_geo_lon = obj.new_value_geo_lon if obj.new_value_geo_lon is not None else 'null'
                ret = '%s%s%s' % (new_value_geo_lat, helpers.get_api_geo_values_separator(), new_value_geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_INT:
                new_value_range_int_from = obj.new_value_range_int_from if obj.new_value_range_int_from is not None else 'null'
                new_value_range_int_to = obj.new_value_range_int_to if obj.new_value_range_int_to is not None else 'null'
                ret = '%s%s%s' % (
                    new_value_range_int_from, helpers.get_api_range_values_separator(), new_value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                new_value_from = obj.new_value_range_fixed_point_from
                if new_value_from is not None:
                    new_value_from = new_value_from / divider
                else:
                    new_value_from = 'null'
                new_value_to = obj.new_value_range_fixed_point_to
                if new_value_to is not None:
                    new_value_to = new_value_to / divider
                else:
                    new_value_to = 'null'
                ret = '%s%s%s' % (new_value_from, helpers.get_api_range_values_separator(), new_value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FLOATING_POINT:
                new_value_range_floating_point_from = obj.new_value_range_floating_point_from if obj.new_value_range_floating_point_from is not None else 'null'
                new_value_range_floating_point_to = obj.new_value_range_floating_point_to if obj.new_value_range_floating_point_to is not None else 'null'
                ret = '%s%s%s' % (
                    new_value_range_floating_point_from, helpers.get_api_range_values_separator(),
                    new_value_range_floating_point_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATETIME:
                new_value_range_datetime_from = helpers.datetime_to_representation(self,
                                                                                   obj.new_value_range_datetime_from) if obj.new_value_range_datetime_from is not None else 'null'
                new_value_range_datetime_to = helpers.datetime_to_representation(self,
                                                                                 obj.new_value_range_datetime_to) if obj.new_value_range_datetime_to is not None else 'null'
                ret = '%s%s%s' % (
                    new_value_range_datetime_from, helpers.get_api_range_values_separator(),
                    new_value_range_datetime_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATE:
                new_value_range_date_from = DateField.to_representation(None,
                                                                        obj.new_value_range_date_from) if obj.new_value_range_date_from is not None else 'null'
                new_value_range_date_to = DateField.to_representation(None,
                                                                      obj.new_value_range_date_to) if obj.new_value_range_date_to is not None else 'null'
                ret = '%s%s%s' % (
                    new_value_range_date_from, helpers.get_api_range_values_separator(), new_value_range_date_to)
        return ret

    def get_collection(self, obj):
        return StageCollectionHelperSerializer(obj.changeset.collection,
                                               context={'request': self.context.get('request')}).data

    def get_created_at(self, obj):
        return obj.changeset.created_at

    def get_data_type(self, obj):
        return StaticDataTypeFlatSerializer(obj.attribute.attribute_type.data_type,
                                            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.LogAttributeValueChange
        fields = (
            'old_value', 'new_value', 'old_currency', 'new_currency', 'old_valid_from', 'new_valid_from',
            'old_valid_to', 'new_valid_to', 'change_type', 'data_type', 'collection', 'created_at')


class StageAttributeValueCollectionSerializer(serializers.ModelSerializer):
    collection = StageCollectionHelperSerializer()

    class Meta:
        model = models.StageAttributeValueCollection
        fields = ('collection', 'valid_from', 'valid_to', 'created_at', 'updated_at')


class StageCodebookSerializer(serializers.HyperlinkedModelSerializer):
    codebook_values = serializers.SerializerMethodField()
    attribute_types = serializers.SerializerMethodField()

    def get_codebook_values(self, obj):
        return StageCodebookValueFlatSerializer(
            obj.codebook_values.filter(deleted=False, published=True), many=True,
            context={'request': self.context.get('request')}).data

    def get_attribute_types(self, obj):
        return StageAttributeTypeHelper2Serializer(obj.attribute_types.filter(deleted=False, published=True), many=True,
                                                   context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageCodebook
        fields = ('url', 'string_id', 'name', 'is_closed', 'codebook_values', 'attribute_types')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageCollectionSerializer(serializers.HyperlinkedModelSerializer):
    source = StageSourceHelperSerializer()
    collection_type = StaticCollectionTypeFlatSerializer()

    # attributes = serializers.SerializerMethodField()

    def get_attributes(self, obj):
        return StageAttributeHelper2Serializer(
            obj.attributes.select_related('attribute_type__data_type').select_related(
                'attribute_type__codebook').filter(finally_deleted=False, finally_published=True).order_by(
                'order_number'), many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageCollection
        fields = (
            'url', 'string_id', 'name', 'source', 'collection_type', 'quality', 'description',  # 'attributes',
            'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class LogEntityEntityChangeHelperSerializer(serializers.ModelSerializer):
    change_type = StaticChangeTypeSerializer()
    collection = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    def get_collection(self, obj):
        return StageCollectionHelperSerializer(obj.changeset.collection,
                                               context={'request': self.context.get('request')}).data

    def get_created_at(self, obj):
        return obj.changeset.created_at

    class Meta:
        model = models.LogEntityEntityChange
        fields = (
            'old_valid_from', 'new_valid_from', 'old_valid_to', 'new_valid_to', 'change_type', 'collection',
            'created_at')


class StageEntityEntityCollectionSerializer(serializers.ModelSerializer):
    collection = StageCollectionHelperSerializer()

    class Meta:
        model = models.StageEntityEntityCollection
        fields = ('collection', 'created_at', 'updated_at')


class StaticEntityTypeSerializer(serializers.HyperlinkedModelSerializer):
    attributes = serializers.SerializerMethodField()

    def get_attributes(self, obj):
        return StageAttributeHelper2Serializer(
            obj.attributes.select_related('attribute_type__data_type').select_related(
                'attribute_type__codebook').filter(finally_deleted=False, finally_published=True).order_by(
                'order_number'),
            many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StaticEntityType
        fields = ('url', 'string_id', 'name', 'attributes')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


# - depth: 4


class StageAttributeValueHelperSerializer(serializers.ModelSerializer):
    attribute_value = serializers.SerializerMethodField()
    attribute_value_collections = serializers.SerializerMethodField()
    currency = StaticCurrencyFlatSerializer()

    def get_attribute_value(self, obj):
        ret = None
        attribute_type_instance = obj.attribute.attribute_type
        data_type = attribute_type_instance.data_type.string_id
        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_BOOLEAN:
                ret = obj.value_boolean
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_INT:
                ret = obj.value_int
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FIXED_POINT:
                ret = obj.value_fixed_point
                if ret is not None:
                    ret = ret / helpers.get_divider(attribute_type_instance)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_FLOATING_POINT:
                ret = obj.value_floating_point
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_STRING:
                ret = obj.value_string
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_TEXT:
                ret = obj.value_text
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATETIME:
                ret = helpers.datetime_to_representation(self, obj.value_datetime)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_DATE:
                ret = DateField.to_representation(None, obj.value_date)
            elif const.DATA_TYPE_MAPPING_SIMPLE.get(data_type) == const.DATA_TYPE_CODEBOOK:
                if obj.value_codebook_item is not None:
                    ret = StageCodebookValueFlatSerializer(obj.value_codebook_item,
                                                           context={'request': self.context.get('request')}).data
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_GEO:
                value_geo_lat = obj.value_geo_lat if obj.value_geo_lat is not None else 'null'
                value_geo_lon = obj.value_geo_lon if obj.value_geo_lon is not None else 'null'
                ret = '%s%s%s' % (value_geo_lat, helpers.get_api_geo_values_separator(), value_geo_lon)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_INT:
                value_range_int_from = obj.value_range_int_from if obj.value_range_int_from is not None else 'null'
                value_range_int_to = obj.value_range_int_to if obj.value_range_int_to is not None else 'null'
                ret = '%s%s%s' % (value_range_int_from, helpers.get_api_range_values_separator(), value_range_int_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FIXED_POINT:
                divider = helpers.get_divider(attribute_type_instance)
                value_from = obj.value_range_fixed_point_from
                if value_from is not None:
                    value_from = value_from / divider
                else:
                    value_from = 'null'
                value_to = obj.value_range_fixed_point_to
                if value_to is not None:
                    value_to = value_to / divider
                else:
                    value_to = 'null'
                ret = '%s%s%s' % (value_from, helpers.get_api_range_values_separator(), value_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_FLOATING_POINT:
                value_range_floating_point_from = obj.value_range_floating_point_from if obj.value_range_floating_point_from is not None else 'null'
                value_range_floating_point_to = obj.value_range_floating_point_to if obj.value_range_floating_point_to is not None else 'null'
                ret = '%s%s%s' % (value_range_floating_point_from, helpers.get_api_range_values_separator(),
                                  value_range_floating_point_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATETIME:
                value_range_datetime_from = helpers.datetime_to_representation(self,
                                                                               obj.value_range_datetime_from) if obj.value_range_datetime_from is not None else 'null'
                value_range_datetime_to = helpers.datetime_to_representation(self,
                                                                             obj.value_range_datetime_to) if obj.value_range_datetime_to is not None else 'null'
                ret = '%s%s%s' % (
                    value_range_datetime_from, helpers.get_api_range_values_separator(), value_range_datetime_to)
            elif const.DATA_TYPE_MAPPING_COMPLEX.get(data_type) == const.DATA_TYPE_RANGE_DATE:
                value_range_date_from = DateField.to_representation(None,
                                                                    obj.value_range_date_from) if obj.value_range_date_from is not None else 'null'
                value_range_date_to = DateField.to_representation(None,
                                                                  obj.value_range_date_to) if obj.value_range_date_to is not None else 'null'
                ret = '%s%s%s' % (value_range_date_from, helpers.get_api_range_values_separator(), value_range_date_to)
        return ret

    def get_attribute_value_collections(self, obj):
        return StageAttributeValueCollectionSerializer(
            obj.attribute_value_collections.filter(deleted=False, published=True, collection__deleted=False,
                                                   collection__published=True, collection__source__deleted=False,
                                                   collection__source__published=True), many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageAttributeValue
        fields = ('attribute_value', 'currency', 'attribute_value_collections', 'created_at', 'updated_at')


# - depth: 5


class StageAttributeHelper3Serializer(serializers.HyperlinkedModelSerializer):
    attribute_type = StageAttributeTypeHelper1Serializer()
    attribute_values = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    def get_attribute_values(self, obj):
        return StageAttributeValueHelperSerializer(
            obj.attribute_values.filter(
                Q(entity=self.context.get('entity'), entity_entity=self.context.get('entity_entity'),
                  attribute_value_collections__deleted=False,
                  attribute_value_collections__published=True,
                  attribute_value_collections__collection__deleted=False,
                  attribute_value_collections__collection__published=True,
                  attribute_value_collections__collection__source__deleted=False,
                  attribute_value_collections__collection__source__published=True) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True,
                                                        value_codebook_item__codebook__deleted=False,
                                                        value_codebook_item__codebook__published=True))).distinct(),
            many=True, context={'request': self.context.get('request')}).data

    def get_changes(self, obj):
        return LogAttributeValueChangeHelperSerializer(
            obj.attribute_value_changes.filter(
                Q(entity=self.context.get('entity'), entity_entity=self.context.get('entity_entity'),
                  deleted=False, published=True,
                  changeset__deleted=False, changeset__published=True,
                  changeset__collection__deleted=False,
                  changeset__collection__published=True,
                  changeset__collection__source__deleted=False,
                  changeset__collection__source__published=True) & (
                        Q(old_value_codebook_item=None) | (
                    Q(old_value_codebook_item__deleted=False,
                      old_value_codebook_item__published=True,
                      old_value_codebook_item__codebook__deleted=False,
                      old_value_codebook_item__codebook__published=True))) & (
                        Q(new_value_codebook_item=None) | (
                    Q(new_value_codebook_item__deleted=False,
                      new_value_codebook_item__published=True,
                      new_value_codebook_item__codebook__deleted=False,
                      new_value_codebook_item__codebook__published=True)))),
            many=True,
            context={'request': self.context.get('request')}).data

    def get_attributes(self, obj):
        return StageAttributeHelper3Serializer(
            obj.attributes.filter(finally_deleted=False, finally_published=True).order_by('order_number'),
            many=True,
            context={'request': self.context.get('request'), 'entity': self.context.get('entity'),
                     'entity_entity': self.context.get('entity_entity')}).data

    class Meta:
        model = models.StageAttribute
        fields = (
            'url', 'string_id', 'name', 'attribute_type', 'attribute_values', 'changes', 'attributes', 'created_at',
            'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


class StageAttributeHelper5Serializer(serializers.HyperlinkedModelSerializer):
    attribute_type = StageAttributeTypeHelper1Serializer()
    attribute_values = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()

    def get_attribute_values(self, obj):
        return StageAttributeValueHelperSerializer(
            obj.attribute_values.filter(
                Q(entity=self.context.get('entity'), entity_entity=self.context.get('entity_entity'),
                  attribute_value_collections__deleted=False,
                  attribute_value_collections__published=True,
                  attribute_value_collections__collection__deleted=False,
                  attribute_value_collections__collection__published=True,
                  attribute_value_collections__collection__source__deleted=False,
                  attribute_value_collections__collection__source__published=True) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True,
                                                        value_codebook_item__codebook__deleted=False,
                                                        value_codebook_item__codebook__published=True))).distinct(),
            many=True, context={'request': self.context.get('request')}).data

    def get_attributes(self, obj):
        return StageAttributeHelper5Serializer(
            obj.attributes.filter(finally_deleted=False, finally_published=True).order_by('order_number'), many=True,
            context={'request': self.context.get('request'),
                     'entity': self.context.get('entity'),
                     'entity_entity': self.context.get('entity_entity')}).data

    class Meta:
        model = models.StageAttribute
        fields = (
            'url', 'string_id', 'name', 'attribute_type', 'attribute_values', 'attributes', 'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'string_id'}
        }


# - depth: 6


class StageEntityEntityHelperSerializer(serializers.ModelSerializer):
    entity = serializers.SerializerMethodField()
    connection_type = StaticConnectionTypeSerializer()
    transaction_currency = StaticCurrencyFlatSerializer()
    entity_entity_collections = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    connection_changes = serializers.SerializerMethodField()

    def get_entity(self, obj):
        return StageEntityFlatSerializer(obj.entity_b, context={'request': self.context.get('request')}).data

    def get_entity_entity_collections(self, obj):
        return StageEntityEntityCollectionSerializer(
            obj.entity_entity_collections.filter(deleted=False, published=True, collection__deleted=False,
                                                 collection__published=True, collection__source__deleted=False,
                                                 collection__source__published=True), many=True,
            context={'request': self.context.get('request')}).data

    def get_attributes(self, obj):
        return StageAttributeHelper3Serializer(
            models.StageAttribute.objects.filter(
                attribute=None,
                collection__in=models.StageCollection.objects.filter(deleted=False, published=True,
                                                                     source__deleted=False,
                                                                     source__published=True,
                                                                     entity_entity_collections__entity_entity=obj,
                                                                     entity_entity_collections__deleted=False,
                                                                     entity_entity_collections__published=True,
                                                                     entity_entity_collections__entity_entity__deleted=False,
                                                                     entity_entity_collections__entity_entity__published=True,
                                                                     entity_entity_collections__entity_entity__entity_a__deleted=False,
                                                                     entity_entity_collections__entity_entity__entity_a__published=True,
                                                                     entity_entity_collections__entity_entity__entity_b__deleted=False,
                                                                     entity_entity_collections__entity_entity__entity_b__published=True).distinct(),
                finally_deleted=False, finally_published=True), many=True,
            context={'request': self.context.get('request'), 'entity': None, 'entity_entity': obj}).data

    def get_connection_changes(self, obj):
        return LogEntityEntityChangeHelperSerializer(
            obj.entity_entity_changes.filter(deleted=False, published=True, changeset__deleted=False,
                                             changeset__published=True, changeset__collection__deleted=False,
                                             changeset__collection__published=True,
                                             changeset__collection__source__deleted=False,
                                             changeset__collection__source__published=True), many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageEntityEntity
        fields = ('entity', 'connection_type', 'valid_from', 'valid_to', 'transaction_amount', 'transaction_currency',
                  'transaction_date', 'entity_entity_collections', 'attributes', 'created_at', 'updated_at',
                  'connection_changes')


class StageEntityEntityHelper2Serializer(serializers.ModelSerializer):
    entity_a = StageEntityFlatSerializer()
    connection_type = StaticConnectionTypeSerializer()
    entity_b = StageEntityFlatSerializer()
    transaction_currency = StaticCurrencyFlatSerializer()

    class Meta:
        model = models.StageEntityEntity
        fields = ('id', 'entity_a', 'connection_type', 'entity_b', 'valid_from', 'valid_to', 'transaction_amount',
                  'transaction_currency', 'transaction_date', 'created_at', 'updated_at')


class StageEntityEntityReverseHelperSerializer(serializers.ModelSerializer):
    entity = serializers.SerializerMethodField()
    connection_type = StaticConnectionTypeSerializer()
    transaction_currency = StaticCurrencyFlatSerializer()
    entity_entity_collections = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    connection_changes = serializers.SerializerMethodField()

    def get_entity(self, obj):
        return StageEntityFlatSerializer(obj.entity_a, context={'request': self.context.get('request')}).data

    def get_entity_entity_collections(self, obj):
        return StageEntityEntityCollectionSerializer(
            obj.entity_entity_collections.filter(deleted=False, published=True, collection__deleted=False,
                                                 collection__published=True, collection__source__deleted=False,
                                                 collection__source__published=True), many=True,
            context={'request': self.context.get('request')}).data

    def get_attributes(self, obj):
        return StageAttributeHelper3Serializer(
            models.StageAttribute.objects.filter(
                attribute=None,
                collection__in=models.StageCollection.objects.filter(deleted=False, published=True,
                                                                     source__deleted=False,
                                                                     source__published=True,
                                                                     entity_entity_collections__entity_entity=obj,
                                                                     entity_entity_collections__deleted=False,
                                                                     entity_entity_collections__published=True,
                                                                     entity_entity_collections__entity_entity__deleted=False,
                                                                     entity_entity_collections__entity_entity__published=True,
                                                                     entity_entity_collections__entity_entity__entity_a__deleted=False,
                                                                     entity_entity_collections__entity_entity__entity_a__published=True,
                                                                     entity_entity_collections__entity_entity__entity_b__deleted=False,
                                                                     entity_entity_collections__entity_entity__entity_b__published=True).distinct(),
                finally_deleted=False, finally_published=True), many=True,
            context={'request': self.context.get('request'), 'entity': None, 'entity_entity': obj}).data

    def get_connection_changes(self, obj):
        return LogEntityEntityChangeHelperSerializer(
            obj.entity_entity_changes.filter(deleted=False, published=True, changeset__deleted=False,
                                             changeset__published=True, changeset__collection__deleted=False,
                                             changeset__collection__published=True,
                                             changeset__collection__source__deleted=False,
                                             changeset__collection__source__published=True), many=True,
            context={'request': self.context.get('request')}).data

    class Meta:
        model = models.StageEntityEntity
        fields = ('entity', 'connection_type', 'valid_from', 'valid_to', 'transaction_amount', 'transaction_currency',
                  'transaction_date', 'entity_entity_collections', 'attributes', 'created_at', 'updated_at',
                  'connection_changes')


# - depth: 7


class StageEntitySerializer(serializers.HyperlinkedModelSerializer):
    entity_type = StaticEntityTypeFlatSerializer()
    # attributes = serializers.SerializerMethodField()
    # connections = serializers.SerializerMethodField()
    # reverse_connections = serializers.SerializerMethodField()

    '''
    def get_attributes(self, obj):
        return StageAttributeHelper3Serializer(
            models.StageAttribute.objects.filter(
                entity_type=obj.entity_type, finally_deleted=False, finally_published=True), many=True,
            context={'request': self.context.get('request'), 'entity': obj, 'entity_entity': None}).data
    '''

    '''
    def get_connections(self, obj):
        return StageEntityEntityHelperSerializer(
            obj.reverse_connections.filter(deleted=False, published=True, entity_b__deleted=False,
                                           entity_b__published=True, entity_entity_collections__deleted=False,
                                           entity_entity_collections__published=True,
                                           entity_entity_collections__collection__deleted=False,
                                           entity_entity_collections__collection__published=True,
                                           entity_entity_collections__collection__source__deleted=False,
                                           entity_entity_collections__collection__source__published=True).distinct(),
            many=True, context={'request': self.context.get('request')}).data
    '''

    '''
    def get_reverse_connections(self, obj):
        return StageEntityEntityReverseHelperSerializer(
            obj.connections.filter(deleted=False, published=True, entity_a__deleted=False, entity_a__published=True,
                                   entity_entity_collections__deleted=False,
                                   entity_entity_collections__published=True,
                                   entity_entity_collections__collection__deleted=False,
                                   entity_entity_collections__collection__published=True,
                                   entity_entity_collections__collection__source__deleted=False,
                                   entity_entity_collections__collection__source__published=True).distinct(),
            many=True, context={'request': self.context.get('request')}).data
    '''

    class Meta:
        model = models.StageEntity
        fields = (
            # 'url', 'public_id', 'entity_type', 'linked_potentially_pep', 'attributes', 'connections',
            # 'reverse_connections', 'created_at', 'updated_at')
            'url', 'public_id', 'entity_type', 'linked_potentially_pep', 'created_at', 'updated_at')
        extra_kwargs = {
            'url': {'lookup_field': 'public_id'}
        }


class KeyValueWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.KeyValue
        fields = ('key', 'value', 'raw_data')


class KeyValueReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.KeyValue
        fields = ('value',)


class KeyValueRawDataReadSerializer(serializers.Serializer):
    key_data = serializers.ListField(child=serializers.CharField(max_length=512, allow_null=False, allow_blank=False),
                                     required=True, allow_empty=False, allow_null=False)

    def create(self, validated_data):
        return super().create(validated_data=validated_data)

    def update(self, instance, validated_data):
        return super().update(instance=instance, validated_data=validated_data)


class KeyValueRawDataWriteSerializer(serializers.Serializer):
    key_data = serializers.ListField(child=serializers.CharField(max_length=512, allow_null=False, allow_blank=False),
                                     required=True, allow_empty=False, allow_null=False)
    value = serializers.CharField(max_length=512, required=True, allow_null=False, allow_blank=False)

    def create(self, validated_data):
        key = hashlib.sha512((''.join(validated_data.get('key_data'))).encode('utf-8')).hexdigest()
        data = {'key': key, 'value': validated_data.get('value'),
                'raw_data': JSONRenderer().render(validated_data).decode('utf-8')}
        key_value_write_serializer = KeyValueWriteSerializer(data=data)
        key_value_write_serializer.is_valid(raise_exception=True)
        self.data  # fill self.data before self.instance is set
        return key_value_write_serializer.save()

    def update(self, instance, validated_data):
        return super().update(instance=instance, validated_data=validated_data)


class ArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Article
        fields = ('url', 'slug', 'title')
        extra_kwargs = {
            'url': {'lookup_field': 'slug'}
        }


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Article
        fields = ('slug', 'title', 'content_short', 'content_long')
        extra_kwargs = {
            'url': {'lookup_field': 'slug'}
        }


class ArticleContentShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Article
        fields = ('slug', 'title', 'content_short')
        extra_kwargs = {
            'url': {'lookup_field': 'slug'}
        }


class ArticleContentLongSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Article
        fields = ('slug', 'title', 'content_long')
        extra_kwargs = {
            'url': {'lookup_field': 'slug'}
        }


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = django.contrib.auth.models.User
        fields = ('username', 'first_name', 'last_name', 'email', 'password')
        extra_kwargs = {
            'url': {'lookup_field': 'username'}
        }

    def validate(self, data):
        if data.get('email') is not None and data.get('email').strip() != '':
            if django.contrib.auth.models.User.objects.filter(
                    email=data.get('email')).exists():  # todo - možda is_active:
                raise serializers.ValidationError({'email': 'A user with that e-mail already exists.'})
        return data

    def create(self, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        try:
            password = validated_data.pop('password')
            email = None
            if 'email' in validated_data:
                email = validated_data.pop('email').strip()
            instance = ModelClass(**validated_data)
            instance.is_active = True
            instance.is_staff = False
            instance.is_superuser = False
            instance.set_password(password)
            instance.save()

            # instance = ModelClass.objects.create(**validated_data)

            models.UserInfo.objects.create(user=instance, send_notification_on_change_watched_entity=False)
            security_extension_user_instance = models.SecurityExtensionUser(user=instance)
            if email is not None and email != '':
                security_extension_user_instance.unverified_email = email
                self._email_verification_token = security_extension_user_instance.generate_email_verification_token()
            else:
                security_extension_user_instance.unverified_email = ''
            security_extension_user_instance.save()

            if 'email' in validated_data:
                instance.email = validated_data.get('email')

            instance.password = ''
        except TypeError:
            import traceback
            tb = traceback.format_exc()
            msg = (
                    'Got a `TypeError` when calling `%s.objects.create()`. '
                    'This may be because you have a writable field on the '
                    'serializer class that is not a valid argument to '
                    '`%s.objects.create()`. You may need to make the field '
                    'read-only, or override the %s.create() method to handle '
                    'this correctly.\nOriginal exception was:\n %s' %
                    (
                        ModelClass.__name__,
                        ModelClass.__name__,
                        self.__class__.__name__,
                        tb
                    )
            )
            raise TypeError(msg)

        # Save many-to-many relationships after the instance is created.
        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                field.set(value)

        return instance


class UserRetrieveSerializer(serializers.ModelSerializer):
    send_notification_on_change_watched_entity = serializers.BooleanField(
        source='user_info.send_notification_on_change_watched_entity')

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('username', 'first_name', 'last_name', 'email', 'send_notification_on_change_watched_entity')
        extra_kwargs = {
            'url': {'lookup_field': 'username'}
        }


class UserUpdateSerializer(serializers.ModelSerializer):
    send_notification_on_change_watched_entity = serializers.BooleanField(
        source='user_info.send_notification_on_change_watched_entity')

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('first_name', 'last_name', 'email', 'send_notification_on_change_watched_entity')
        related_fields = ['user_info']
        extra_kwargs = {
            'url': {'lookup_field': 'username'}
        }

    def validate(self, data):
        if 'email' in data:
            email = data.get('email').strip()
            if email is not None and email != '' and self.instance.email != email:
                if django.contrib.auth.models.User.objects.filter(
                        email=email).exists():  # todo - možda is_active:
                    raise serializers.ValidationError({'email': 'A user with that e-mail already exists.'})
        return data

    def update(self, instance, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('update', self, validated_data)
        from rest_framework.utils import model_meta
        info = model_meta.get_field_info(instance)

        email = None
        if 'email' in validated_data:
            email = validated_data.pop('email').strip()

        # Simply set each attribute on the instance, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an instance pk for the relationships to be associated with.
        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            elif attr not in info.relations:
                setattr(instance, attr, value)
        instance.save()

        for attr, value in validated_data.items():
            if attr in info.relations and not info.relations[attr].to_many:
                field = getattr(instance, attr)
                for attr2, value2 in value.items():
                    setattr(field, attr2, value2)
                field.save()

        if email is not None and email != '' and instance.email != email:
            security_extension_user_instance = instance.security_extension
            security_extension_user_instance.unverified_email = email
            self._email_verification_token = security_extension_user_instance.generate_email_verification_token()
            security_extension_user_instance.save()

        if 'email' in validated_data:
            instance.email = validated_data.get('email')

        return instance


class UserPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = django.contrib.auth.models.User
        fields = ('password',)
        extra_kwargs = {
            'url': {'lookup_field': 'username'}
        }

    def update(self, instance, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('update', self, validated_data)

        instance.set_password(validated_data.get('password'))
        instance.save()
        instance.password = ''

        return instance


class VerifyEmailSerializer(serializers.Serializer):
    username = serializers.CharField()
    verification_token = serializers.CharField()

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('username', 'verification_token',)
        extra_kwargs = {
            'url': {'lookup_field': 'username'}
        }

    def validate(self, attrs):
        ModelClass = self.Meta.model
        try:
            self._instance = ModelClass.objects.get(username=attrs.get('username'), is_active=True)
        except ModelClass.DoesNotExist:
            raise serializers.ValidationError({'username': 'Invalid username.'})
        security_extension_instance = self._instance.security_extension
        if not security_extension_instance.unverified_email:
            raise serializers.ValidationError({'verification_token': 'Invalid e-mail to verify.'})
        if not security_extension_instance.is_email_verification_token(token=attrs.get('verification_token')):
            raise serializers.ValidationError({'verification_token': 'Invalid verification token.'})
        elif timezone.now() > security_extension_instance.email_verification_token_created_at + datetime.timedelta(
                days=1):
            raise serializers.ValidationError({'verification_token': 'Verification token expired.'})

        return attrs

    def create(self, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        security_extension_instance = self._instance.security_extension
        self._instance.email = security_extension_instance.unverified_email
        self._instance.save()
        security_extension_instance.unverified_email = ''
        security_extension_instance.unset_email_verification_token()
        security_extension_instance.save()
        return self._instance

    def to_representation(self, instance):
        ret = OrderedDict()
        ret['username'] = instance.username
        return ret


class GeneratePasswordChangeTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('verification_token',)

    def validate(self, attrs):
        ModelClass = self.Meta.model
        try:
            self._instance = ModelClass.objects.get(email=attrs.get('email'), is_active=True)
        except ModelClass.DoesNotExist:
            raise serializers.ValidationError({'email': 'A user with that e-mail does not exists.'})
        return attrs

    def create(self, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        security_extension_user_instance = self._instance.security_extension
        self._password_change_token = security_extension_user_instance.generate_password_change_token()
        security_extension_user_instance.save()

        return self._instance


class UserPasswordWithoutAuthSerializer(serializers.Serializer):
    username = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField()

    class Meta:
        model = django.contrib.auth.models.User
        fields = ('username', 'token', 'password')
        extra_kwargs = {
            'url': {'lookup_field': 'username'}
        }

    def validate(self, attrs):
        ModelClass = self.Meta.model
        try:
            self._instance = ModelClass.objects.get(username=attrs.get('username'), is_active=True)
        except ModelClass.DoesNotExist:
            raise serializers.ValidationError({'username': 'Invalid username.'})
        security_extension_instance = self._instance.security_extension
        if not security_extension_instance.is_password_change_token(token=attrs.get('token')):
            raise serializers.ValidationError({'token': 'Invalid token.'})
        elif timezone.now() > security_extension_instance.password_change_token_created_at + datetime.timedelta(days=1):
            raise serializers.ValidationError({'token': 'Token expired.'})

        return attrs

    def create(self, validated_data):
        from rest_framework.serializers import raise_errors_on_nested_writes
        raise_errors_on_nested_writes('create', self, validated_data)

        self._instance.set_password(validated_data.get('password'))
        self._instance.save()
        self._instance.password = ''

        security_extension_instance = self._instance.security_extension
        security_extension_instance.unset_password_change_token()
        security_extension_instance.save()

        return self._instance

    def to_representation(self, instance):
        ret = OrderedDict()
        ret['username'] = instance.username
        return ret


class UserEntitySerializer(serializers.ModelSerializer):
    entity = StageEntityFlatSerializer()

    class Meta:
        model = models.UserEntity
        fields = ('url', 'entity')
        extra_kwargs = {
            'url': {'lookup_field': 'entity__public_id'}
        }


class UserEntityCreateSerializer(serializers.ModelSerializer):
    entity = serializers.SlugRelatedField(slug_field='public_id',
                                          queryset=models.StageEntity.objects.filter(deleted=False, published=True))
    owner = serializers.HiddenField(default=serializers.CreateOnlyDefault(helpers.CurrentUserInfoDefault()))

    class Meta:
        model = models.UserEntity
        fields = ('entity', 'owner')


class UserSavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserSavedSearch
        fields = ('url', 'id', 'name', 'saved_url')


class UserSavedSearchCreateSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CreateOnlyDefault(helpers.CurrentUserInfoDefault()))

    class Meta:
        model = models.UserSavedSearch
        fields = ('name', 'saved_url', 'owner')


class UserSavedSearchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserSavedSearch
        fields = ('name',)
