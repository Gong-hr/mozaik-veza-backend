import datetime
import hashlib

import coreapi
import coreschema
import django
from django.db.models import Q, Prefetch
from django.http import Http404, StreamingHttpResponse
from django.utils import timezone
from django.utils.six import BytesIO
from elasticsearch import NotFoundError
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema
from rest_framework.views import APIView

from mocbackend import models, serializers, const, helpers, permissions
from mocbackend.databases import ElasticsearchDB, Neo4jDB
from mocbackend.schemas import KeyValueSchema


class ListSerializerClass:
    action = None
    serializer_class = None
    list_serializer_class = None
    create_serializer_class = None
    update_serializer_class = None

    def get_serializer_class(self):
        try:
            if self.action == 'list' and self.list_serializer_class is not None:
                return self.list_serializer_class
            if self.action == 'create' and self.create_serializer_class is not None:
                return self.create_serializer_class
            if (
                    self.action == 'update' or self.action == 'partial_update') and self.update_serializer_class is not None:
                return self.update_serializer_class
            return self.serializer_class
        except NameError:
            pass


class AttributeViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    queryset = models.StageAttribute.objects.filter(finally_deleted=False, finally_published=True)
    serializer_class = serializers.StageAttributeSerializer
    list_serializer_class = serializers.StageAttributeFlatSerializer
    create_serializer_class = serializers.StageAttributeCreateSerializer
    # update_serializer_class = serializers.StageAttributeUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class AttributeValueCollectionViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = models.StageAttributeValueCollection.objects.filter(Q(deleted=False,
                                                                     published=True,
                                                                     collection__deleted=False,
                                                                     collection__published=True,
                                                                     collection__source__deleted=False,
                                                                     collection__source__published=True,
                                                                     attribute_value__attribute__finally_deleted=False,
                                                                     attribute_value__attribute__finally_published=True) & (
                                                                           (~Q(attribute_value__entity=None) & Q(
                                                                               attribute_value__entity__deleted=False,
                                                                               attribute_value__entity__published=True)) | (
                                                                                   ~Q(
                                                                                       attribute_value__entity_entity=None) & Q(
                                                                               attribute_value__entity_entity__deleted=False,
                                                                               attribute_value__entity_entity__published=True,
                                                                               attribute_value__entity_entity__entity_a__deleted=False,
                                                                               attribute_value__entity_entity__entity_a__published=True,
                                                                               attribute_value__entity_entity__entity_b__deleted=False,
                                                                               attribute_value__entity_entity__entity_b__published=True,
                                                                               attribute_value__entity_entity__entity_entity_collections__deleted=False,
                                                                               attribute_value__entity_entity__entity_entity_collections__published=True,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__deleted=False,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__published=True,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__source__deleted=False,
                                                                               attribute_value__entity_entity__entity_entity_collections__collection__source__published=True))) & (
                                                                           Q(
                                                                               attribute_value__value_codebook_item=None) | Q(
                                                                       attribute_value__value_codebook_item__deleted=False,
                                                                       attribute_value__value_codebook_item__published=True,
                                                                       attribute_value__value_codebook_item__codebook__deleted=False,
                                                                       attribute_value__value_codebook_item__codebook__published=True))).distinct()
    serializer_class = serializers.StageAttributeValueCollectionCreateUpdateSerializer
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class AttributeTypeViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                           mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.StageAttributeType.objects.filter(
        Q(deleted=False, published=True) & (Q(codebook=None) | Q(codebook__deleted=False, codebook__published=True)))
    serializer_class = serializers.StageAttributeTypeSerializer
    list_serializer_class = serializers.StageAttributeTypeFlatSerializer
    create_serializer_class = serializers.StageAttributeTypeCreateSerializer
    # update_serializer_class = serializers.StageAttributeTypeUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class CodebookViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = models.StageCodebook.objects.filter(deleted=False, published=True)
    serializer_class = serializers.StageCodebookSerializer
    list_serializer_class = serializers.StageCodebookFlatSerializer
    create_serializer_class = serializers.StageCodebookCreateSerializer
    # update_serializer_class = serializers.StageCodebookUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)


class CodebookValueViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                           mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.StageCodebookValue.objects.filter(deleted=False, published=True, codebook__deleted=False,
                                                        codebook__published=True)
    serializer_class = serializers.StageCodebookValueSerializer
    list_serializer_class = serializers.StageCodebookValueFlatSerializer
    create_serializer_class = serializers.StageCodebookValueCreateSerializer
    # update_serializer_class = serializers.StageCodebookValueUpdateSerializer
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class CollectionViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    queryset = models.StageCollection.objects.filter(deleted=False, published=True, source__deleted=False,
                                                     source__published=True)
    serializer_class = serializers.StageCollectionSerializer
    list_serializer_class = serializers.StageCollectionFlatSerializer
    create_serializer_class = serializers.StageCollectionCreateSerializer
    # update_serializer_class = serializers.StageCollectionUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)
    allowed_actions = ('retrieve',)


class CollectionTypeViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                            mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.StaticCollectionType.objects.all()
    serializer_class = serializers.StaticCollectionTypeFlatSerializer
    list_serializer_class = serializers.StaticCollectionTypeFlatSerializer
    create_serializer_class = serializers.StaticCollectionTypeCreateSerializer
    # update_serializer_class = serializers.StaticCollectionTypeUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class ConnectionTypeViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                            mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = models.StaticConnectionType.objects.all()
    serializer_class = serializers.StaticConnectionTypeSerializer
    list_serializer_class = serializers.StaticConnectionTypeFlatSerializer
    create_serializer_class = serializers.StaticConnectionTypeCreateSerializer
    # update_serializer_class = serializers.StaticConnectionTypeUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class ConnectionTypeCategoryViewSet(ListSerializerClass, viewsets.ReadOnlyModelViewSet):
    queryset = models.StaticConnectionTypeCategory.objects.all()
    serializer_class = serializers.StaticConnectionTypeCategorySerializer
    list_serializer_class = serializers.StaticConnectionTypeCategoryFlatSerializer
    # create_serializer_class = serializers.StaticConnectionTypeCategoryCreateSerializer
    # update_serializer_class = serializers.StaticConnectionTypeCategoryUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)
    allowed_actions = ('list',)


class CurrencyViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = models.StaticCurrency.objects.all()
    serializer_class = serializers.StaticCurrencyFlatSerializer
    list_serializer_class = serializers.StaticCurrencyFlatSerializer
    create_serializer_class = serializers.StaticCurrencyCreateSerializer
    # update_serializer_class = serializers.StaticCurrencyUpdateSerializer
    lookup_field = 'code'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class DataTypeViewSet(ListSerializerClass, viewsets.ReadOnlyModelViewSet):
    queryset = models.StaticDataType.objects.all()
    serializer_class = serializers.StaticDataTypeFlatSerializer
    list_serializer_class = serializers.StaticDataTypeFlatSerializer
    lookup_field = 'string_id'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class EntityViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = models.StageEntity.objects.select_related('entity_type').filter(deleted=False, published=True)
    serializer_class = serializers.StageEntitySerializer
    list_serializer_class = serializers.StageEntityFlatSerializer
    create_serializer_class = serializers.StageEntityCreateWrapperSerializer
    # update_serializer_class = serializers.StageEntityUpdateSerializer
    lookup_field = 'public_id'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)


class EntityEntityCollectionViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = models.StageEntityEntityCollection.objects.filter(deleted=False, published=True,
                                                                 collection__deleted=False,
                                                                 collection__published=True,
                                                                 collection__source__deleted=False,
                                                                 collection__source__published=True,
                                                                 entity_entity__deleted=False,
                                                                 entity_entity__published=True,
                                                                 entity_entity__entity_a__deleted=False,
                                                                 entity_entity__entity_a__published=True,
                                                                 entity_entity__entity_b__deleted=False,
                                                                 entity_entity__entity_b__published=True)
    serializer_class = serializers.StageEntityEntityCollectionCreateUpdateSerializer
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class EntityTypeViewSet(ListSerializerClass, viewsets.ReadOnlyModelViewSet):
    queryset = models.StaticEntityType.objects.all()
    serializer_class = serializers.StaticEntityTypeSerializer
    list_serializer_class = serializers.StaticEntityTypeFlatSerializer
    lookup_field = 'string_id'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)
    allowed_actions = ('list',)


class SourceViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = models.StageSource.objects.select_related('source_type').prefetch_related(
        Prefetch('collections',
                 queryset=models.StageCollection.objects.select_related('collection_type').filter(deleted=False,
                                                                                                  published=True))).filter(
        deleted=False, published=True)
    serializer_class = serializers.StageSourceSerializer
    list_serializer_class = serializers.StageSourceSerializer
    create_serializer_class = serializers.StageSourceCreateSerializer
    # update_serializer_class = serializers.StageSourceUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)
    allowed_actions = ('list',)


class SourceTypeViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    queryset = models.StaticSourceType.objects.all()
    serializer_class = serializers.StaticSourceTypeFlatSerializer
    list_serializer_class = serializers.StaticSourceTypeFlatSerializer
    create_serializer_class = serializers.StaticSourceTypeCreateSerializer
    # update_serializer_class = serializers.StaticSourceTypeUpdateSerializer
    lookup_field = 'string_id'
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)


class KeyValueViewCreate(APIView):
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="key_data",
                    required=True,
                    location='form',
                    schema=coreschema.Array(
                        title="Key data"
                    ),
                ),
                coreapi.Field(
                    name="value",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Value",
                    ),
                ),
            ],
        )

    def post(self, request, format=None):
        serializer = serializers.KeyValueRawDataWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class KeyValueView(APIView):
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)
    if coreapi is not None and coreschema is not None:
        schema = KeyValueSchema()

    def get_object(self, pk):
        try:
            stream = BytesIO(pk.encode('utf-8'))
            data = JSONParser().parse(stream)
            serializer = serializers.KeyValueRawDataReadSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            key = hashlib.sha512((''.join(serializer.data['key_data'])).encode('utf-8')).hexdigest()
            return models.KeyValue.objects.get(pk=key)
        except (models.KeyValue.DoesNotExist, AttributeError):
            raise Http404

    def get(self, request, pk, format=None):
        key_value = self.get_object(pk)
        key_value_read_serializer = serializers.KeyValueReadSerializer(key_value)
        return Response(key_value_read_serializer.data)

    def put(self, request, pk, format=None):
        key_value = self.get_object(pk)
        stream = BytesIO(pk.encode('utf-8'))
        key_data = JSONParser().parse(stream)['key_data']
        key = hashlib.sha512((''.join(key_data)).encode('utf-8')).hexdigest()
        raw_data = {'key_data': key_data, 'value': request.data['value']}
        serializer = serializers.KeyValueRawDataWriteSerializer(data=raw_data)
        serializer.is_valid(raise_exception=True)
        data = {'key': key, 'value': request.data['value'], 'raw_data': JSONRenderer().render(raw_data).decode('utf-8')}
        key_value_write_serializer = serializers.KeyValueWriteSerializer(key_value, data=data)
        key_value_write_serializer.is_valid(raise_exception=True)
        key_value_write_serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, format=None):
        key_value = self.get_object(pk)
        key_value.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutocompleteEntitiesView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="full",
                    required=False,
                    location='query',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def get(self, request, term, offset, limit, format=None):
        limit = limit if int(limit) <= 100 else '100'
        body = {
            'from': offset,
            'size': limit,
            'query': {
                'function_score': {
                    'query': {
                        'match': {
                            const.ELASTICSEARCH_SEARCH_FIELD_NAME: {
                                'query': term,
                                'operator': 'and'
                            }
                        }
                    },
                    'script_score': {
                        'script': {
                            'source': "(doc['is_pep'].value ? _score * 100 : _score)"
                        }
                    }
                }
            }
        }

        full = request.GET.get('full') == 'true'
        if not full:
            _source = ['person_first_name.value', 'person_last_name.value', 'legal_entity_name.value',
                       'real_estate_name.value', 'movable_name.value', 'savings_name.value', 'is_pep', 'entity_type']
            for connection_type_category in models.StaticConnectionTypeCategory.objects.all():
                _source.append('count_' + connection_type_category.string_id)

            body.update({
                '_source': _source
            })

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'public_id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class EntityView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="full",
                    required=False,
                    location='query',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def get(self, request, pk, format=None):
        result = None
        source = None
        full = request.GET.get('full') == 'true'
        if not full:
            source = ['person_first_name.value', 'person_last_name.value', 'legal_entity_name.value',
                      'real_estate_name.value', 'movable_name.value', 'savings_name.value', 'is_pep', 'entity_type']
            for connection_type_category in models.StaticConnectionTypeCategory.objects.all():
                source.append('count_' + connection_type_category.string_id)
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            try:
                result_raw = es.get(index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=pk, _source=source)
            except NotFoundError:
                raise Http404
            result = result_raw['_source']
            result.update({
                'public_id': result_raw['_id']
            })
        if request.GET.get('as_file') == 'true':
            response = Response(result)
            response['Content-Disposition'] = 'attachment; filename="entity_%s.json"' % pk
        else:
            response = Response({'result': result})
        return response


class EntitiesByAttributesValuesView(
    APIView):  # todo kompleksni tipovi podataka nisu napravljeni (geo, range, complex), treba dodati i limit
    permission_classes = [permissions.IsStaffOrInAnyAllowedGroups]
    allowed_groups = ('importer',)
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="entity_type",
                    required=True,
                    location='form',
                    schema=coreschema.String(
                        title="Entity type"
                    ),
                ),
                coreapi.Field(
                    name="full",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def post(self, request, offset, limit, format=None):
        entity_type = request.POST.get('entity_type')
        if entity_type is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not models.StaticEntityType.objects.filter(string_id=entity_type).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        query = []
        for key, value in request.POST.items():
            if key not in ['entity_type']:
                try:
                    attribute = models.StageAttribute.objects.get(string_id=key, finally_deleted=False,
                                                                  finally_published=True,
                                                                  entity_type__string_id=entity_type)
                except models.StageAttribute.DoesNotExist:
                    return Response(status=status.HTTP_400_BAD_REQUEST)

                data_type = attribute.attribute_type.data_type.string_id

                if data_type not in const.DATA_TYPE_MAPPING_SIMPLE:
                    return Response(status=status.HTTP_400_BAD_REQUEST)

                field_name = key + '.' + const.ELASTICSEARCH_VALUE_FIELD_NAME

                query_tmp = []
                for item in request.POST.getlist(key):
                    filter_type = 'term'
                    if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                        field_name = field_name + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX
                        filter_type = 'match'
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                        field_name = field_name + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX

                    if key == 'person_vat_number':
                        item = hashlib.sha512((item + const.VAT_NUMBER_SALT).encode('utf-8')).hexdigest()
                        filter_type = 'term'

                    query_tmp.append({
                        filter_type: {
                            field_name: item
                        }
                    })

                if query_tmp:
                    if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                        path = key
                        query.append({
                            'nested': {
                                'path': path,
                                'query': {
                                    'bool': {
                                        'should': query_tmp
                                    }
                                }
                            }
                        })
                    else:
                        query.append({
                            'bool': {
                                'should': query_tmp
                            }
                        })
        if not query:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        query.append({
            'term': {
                'entity_type.string_id': entity_type
            }
        })

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'bool': {
                    'must': query
                }
            }
        }

        full = request.POST.get('full') == 'true'
        if not full:
            _source = ['person_first_name.value', 'person_last_name.value', 'legal_entity_name.value',
                       'real_estate_name.value', 'movable_name.value', 'savings_name.value', 'is_pep', 'entity_type']
            for connection_type_category in models.StaticConnectionTypeCategory.objects.all():
                _source.append('count_' + connection_type_category.string_id)
            body.update({
                '_source': _source
            })

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'public_id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class LegalEntitiesByVatNumberView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            '''
            manual_fields=[
                coreapi.Field(
                    name="full",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
            '''
        )

        def get(self, request, vat_number, format=None):
            entity_type = 'legal_entity'
            key = 'legal_entity_vat_number'
            field_name = key + '.' + const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX

            query = []
            query.append({
                'term': {
                    field_name: vat_number
                },
            })
            query.append({
                'term': {
                    'entity_type.string_id': entity_type
                }
            })

            body = {
                # 'from': 0,
                # 'size': 1,
                'query': {
                    'bool': {
                        'must': query
                    }
                }
            }

            # full = request.GET.get('full') == 'true'
            full = False
            if not full:
                _source = ['legal_entity_name.value', 'entity_type']
                body.update({
                    '_source': _source
                })

            results = []
            total = 0
            if ElasticsearchDB.is_elasticsearch_settings_exists():
                es = ElasticsearchDB.get_db().get_elasticsearch()
                results_raw = es.search(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
                hits = results_raw['hits']
                total = hits['total']
                for hit in hits['hits']:
                    source = hit['_source']
                    source.update({
                        'public_id': hit['_id']
                    })
                    results.append(source)

            return Response({'total': total, 'results': results})


class EntitiesByConnectionCountView(APIView):
    def get(self, request, pk, offset, limit, format=None):
        results = []
        body_1 = {
            'size': 0,
            'query': {
                'bool': {
                    'filter': [
                        {
                            'term': {
                                'entity_a.public_id': pk
                            }
                        }
                    ]
                }
            },
            'aggs': {
                'entities': {
                    'terms': {
                        'field': 'entity_b.public_id',
                        'size': const.ELASTICSEARCH_MAX_RESULT_WINDOWS
                    }
                }
            }
        }

        body_2 = {
            'size': 0,
            'query': {
                'bool': {
                    'filter': [
                        {
                            'term': {
                                'entity_b.public_id': pk
                            }
                        }
                    ]
                }
            },
            'aggs': {
                'entities': {
                    'terms': {
                        'field': 'entity_a.public_id',
                        'size': const.ELASTICSEARCH_MAX_RESULT_WINDOWS
                    }
                }
            }
        }

        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw_1 = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body_1)

            results_raw_2 = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body_2)

            buckets_1 = results_raw_1['aggregations']['entities']['buckets']
            buckets_2 = results_raw_2['aggregations']['entities']['buckets']

            buckets_1_fast = {}
            buckets_2_fast = {}

            for bucket_1 in buckets_1:
                buckets_1_fast.update({
                    bucket_1['key']: bucket_1['doc_count']
                })

            for bucket_2 in buckets_2:
                buckets_2_fast.update({
                    bucket_2['key']: bucket_2['doc_count']
                })

            for key, value in buckets_1_fast.items():
                if key in buckets_2_fast:
                    value = value + buckets_2_fast[key]
                results.append({
                    'key': key,
                    'doc_count': value
                })

            for key, value in buckets_2_fast.items():
                if key not in buckets_1_fast:
                    results.append({
                        'key': key,
                        'doc_count': value
                    })

            import operator
            results = sorted(results, key=operator.itemgetter('doc_count'), reverse=True)
            limit = limit if int(limit) <= 100 else '100'
            results = results[int(offset):int(offset) + int(limit)]

        return Response({'results': results})


class ConnectionView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="full",
                    required=False,
                    location='query',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def get(self, request, pk, format=None):
        result = None
        source = None
        full = request.GET.get('full') == 'true'
        if not full:
            source = ['entity_a', 'entity_b', 'connection_type', 'connection_type_category', 'valid_from', 'valid_to',
                      'transaction_amount', 'transaction_date', 'transaction_currency']
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            try:
                result_raw = es.get(index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=pk, _source=source)
            except NotFoundError:
                raise Http404
            result = result_raw['_source']
            result.update({
                'id': result_raw['_id']
            })
        if request.GET.get('as_file') == 'true':
            response = Response(result)
            response['Content-Disposition'] = 'attachment; filename="connection_%s.json"' % pk
        else:
            response = Response({'result': result})
        return response


class ConnectionsByAttributesValuesView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="entity",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Entity"
                    ),
                ),
                coreapi.Field(
                    name="connection_type_category",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type category"
                    ),
                ),
                coreapi.Field(
                    name="connection_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (to)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (to)"
                    ),
                ),
                coreapi.Field(
                    name="entity_type",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Entity type"
                    ),
                ),
                coreapi.Field(
                    name="legal_entity_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Legal entity type"
                    ),
                ),
                coreapi.Field(
                    name="is_pep",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Is PEP"
                    ),
                ),
                coreapi.Field(
                    name="valid_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid from"
                    ),
                ),
                coreapi.Field(
                    name="valid_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid to"
                    ),
                ),
                coreapi.Field(
                    name="order_by",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order by"
                    ),
                ),
                coreapi.Field(
                    name="order_direction",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order direction"
                    ),
                ),
                coreapi.Field(
                    name="count",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Count"
                    ),
                ),
                coreapi.Field(
                    name="full",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def post(self, request, offset, limit, format=None):
        query = []
        query_entity_a = []
        query_entity_b = []
        pk = None

        order_by = None
        order_direction = 'asc'

        connection_type = []

        for key, value in request.POST.items():
            if key == 'entity':
                pk = value
                query_entity_a.append({
                    'term': {
                        'entity_a.public_id': value
                    }
                })
                query_entity_b.append({
                    'term': {
                        'entity_b.public_id': value
                    }
                })
            elif key == 'connection_type_category':
                for item in request.POST.getlist('connection_type_category'):
                    connection_type.append({
                        'term': {
                            'connection_type_category.string_id': item
                        }
                    })
            elif key == 'connection_type':
                for item in request.POST.getlist('connection_type'):
                    connection_type.append({
                        'term': {
                            'connection_type.string_id': item
                        }
                    })
            elif key == 'transaction_date_from':
                query.append({
                    "range": {
                        "transaction_date": {
                            "gte": value,
                        }
                    }
                })
            elif key == 'transaction_date_to':
                query.append({
                    "range": {
                        "transaction_date": {
                            "lte": value,
                        }
                    }
                })
            elif key == 'transaction_amount_from':
                query.append({
                    "range": {
                        "transaction_amount": {
                            "gte": value,
                        }
                    }
                })
            elif key == 'transaction_amount_to':
                query.append({
                    "range": {
                        "transaction_amount": {
                            "lte": value,
                        }
                    }
                })
            elif key == 'entity_type':
                entity_type_a = []
                entity_type_b = []
                for item in request.POST.getlist('entity_type'):
                    entity_type_a.append({
                        'term': {
                            'entity_a.entity_type.string_id': item
                        }
                    })
                    entity_type_b.append({
                        'term': {
                            'entity_b.entity_type.string_id': item
                        }
                    })

                if entity_type_a:
                    query_entity_b.append({
                        'bool': {
                            'should': entity_type_a
                        }
                    })
                if entity_type_b:
                    query_entity_a.append({
                        'bool': {
                            'should': entity_type_b
                        }
                    })
            elif key == 'legal_entity_type':
                legal_entity_type_a = []
                legal_entity_type_b = []
                for item in request.POST.getlist('legal_entity_type'):
                    legal_entity_type_a.append({
                        'term': {
                            'entity_a.legal_entity_type.' + const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: item
                        }
                    })
                    legal_entity_type_b.append({
                        'term': {
                            'entity_b.legal_entity_type.' + const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: item
                        }
                    })

                if legal_entity_type_a:
                    query_entity_b.append({
                        'bool': {
                            'should': legal_entity_type_a
                        }
                    })
                if legal_entity_type_b:
                    query_entity_a.append({
                        'bool': {
                            'should': legal_entity_type_b
                        }
                    })
            elif key == 'is_pep' and (value == 'true' or value == 'false'):
                is_pep = True if value == 'true' else False
                query_entity_b.append({
                    'term': {
                        'entity_a.is_pep': is_pep
                    }
                })
                query_entity_a.append({
                    'term': {
                        'entity_b.is_pep': is_pep
                    }
                })
            elif key == 'valid_from':
                query.append({
                    "range": {
                        "valid_from": {
                            "gte": value,
                        }
                    }
                })
            elif key == 'valid_to':
                query.append({
                    "range": {
                        "valid_to": {
                            "lte": value,
                        }
                    }
                })
            elif key == 'order_by':
                if value == 'valid_from' or value == 'valid_to' or value == 'transaction_amount':
                    order_by = value
            elif key == 'order_direction':
                if value == 'asc' or value == 'desc':
                    order_direction = value

        if connection_type:
            query.append({
                'bool': {
                    'should': connection_type
                }
            })

        entity_a_b = []
        if query_entity_a:
            entity_a_b.append({
                'bool': {
                    'filter': query_entity_a
                }
            })
        if query_entity_b:
            entity_a_b.append({
                'bool': {
                    'filter': query_entity_b
                }
            })

        if entity_a_b:
            query.append({
                'bool': {
                    'should': entity_a_b
                }
            })

        aggs = {
            'min_valid_from': {
                'min': {
                    'field': 'valid_from'
                }
            },
            'min_valid_to': {
                'min': {
                    'field': 'valid_to'
                }
            },
            'max_valid_from': {
                'max': {
                    'field': 'valid_from'
                }
            },
            'max_valid_to': {
                'max': {
                    'field': 'valid_to'
                }
            },
        }

        count = request.POST.get('count') == 'true'
        if count:
            aggs.update({
                'entities_a': {
                    'terms': {
                        'field': 'entity_a.public_id',
                        'size': const.ELASTICSEARCH_MAX_RESULT_WINDOWS
                    }
                }
            })
            aggs.update({
                'entities_b': {
                    'terms': {
                        'field': 'entity_b.public_id',
                        'size': const.ELASTICSEARCH_MAX_RESULT_WINDOWS
                    }
                }
            })

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'bool': {
                    'filter': query
                }
            },
            'aggs': aggs,
        }

        full = request.POST.get('full') == 'true'
        if not full:
            body.update({
                '_source': ['entity_a', 'entity_b', 'connection_type', 'connection_type_category', 'valid_from',
                            'valid_to', 'transaction_amount', 'transaction_date', 'transaction_currency']
            })

        if order_by is not None:
            missing = '_last'
            if order_by == 'valid_from' and order_direction == 'asc':
                missing = '_first'
            if order_by == 'valid_to' and order_direction == 'desc':
                missing = '_first'
            body.update({
                'sort': [
                    {
                        order_by: {
                            'order': order_direction,
                            'missing': missing
                        }
                    }
                ]
            })

        results = []
        buckets = {}
        total = 0
        min_valid = None
        max_valid = None
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)

            min_valid_from = results_raw['aggregations']['min_valid_from']['value']
            min_valid_to = results_raw['aggregations']['min_valid_to']['value']

            max_valid_from = results_raw['aggregations']['max_valid_from']['value']
            max_valid_to = results_raw['aggregations']['max_valid_to']['value']

            minimums = set()
            if min_valid_from is not None:
                minimums.add(min_valid_from)
            if min_valid_to is not None:
                minimums.add(min_valid_to)

            maximums = set()
            if max_valid_from is not None:
                maximums.add(max_valid_from)
            if max_valid_to is not None:
                maximums.add(max_valid_to)

            if minimums:
                min_valid = datetime.datetime.fromtimestamp(min(minimums) / 1000.0)
            if maximums:
                max_valid = datetime.datetime.fromtimestamp(max(maximums) / 1000.0)

            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'id': hit['_id']
                })
                results.append(source)

            if pk is not None and count:
                buckets_1 = results_raw['aggregations']['entities_a']['buckets']
                buckets_2 = results_raw['aggregations']['entities_b']['buckets']

                buckets_2_fast = {}

                for bucket_2 in buckets_2:
                    key = bucket_2['key']
                    if key != pk:
                        buckets_2_fast.update({
                            key: bucket_2['doc_count']
                        })

                for bucket_1 in buckets_1:
                    key = bucket_1['key']
                    if key != pk:
                        value = bucket_1['doc_count']
                        if key in buckets_2_fast:
                            value = value + buckets_2_fast[key]
                        buckets.update({
                            key: value
                        })

                for key, value in buckets_2_fast.items():
                    if key != pk:
                        if key not in buckets:
                            buckets.update({
                                key: value
                            })

        ret = {'total': total, 'results': results, 'min_valid': min_valid, 'max_valid': max_valid}
        if pk is not None and count:
            ret.update({
                'buckets': buckets
            })

        return Response(ret)


class NeighboursByAttributesValuesView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="entity",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Entity"
                    ),
                ),
                coreapi.Field(
                    name="connection_type_category",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type category"
                    ),
                ),
                coreapi.Field(
                    name="connection_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (to)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (to)"
                    ),
                ),
                coreapi.Field(
                    name="entity_type",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Entity type"
                    ),
                ),
                coreapi.Field(
                    name="legal_entity_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Legal entity type"
                    ),
                ),
                coreapi.Field(
                    name="is_pep",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Is PEP"
                    ),
                ),
                coreapi.Field(
                    name="valid_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid from"
                    ),
                ),
                coreapi.Field(
                    name="valid_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid to"
                    ),
                ),
                coreapi.Field(
                    name="count",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Count"
                    ),
                ),
            ],
        )

    def post(self, request, offset, limit, format=None):
        entity_public_id = None
        connection_type_categories = None
        connection_types = None
        transaction_date_from = None
        transaction_date_to = None
        transaction_amount_from = None
        transaction_amount_to = None
        entity_types = None
        legal_entity_types = None
        valid_from = None
        valid_to = None

        query_a = ''
        query_b = ''
        query_r_connection_type = ''
        query_r = ''

        for key, value in request.POST.items():
            if key == 'entity':
                entity_public_id = value
                if query_a:
                    query_a += ' AND '
                query_a += 'r.entity_a_public_id = $entity_public_id'
                if query_b:
                    query_b += ' AND '
                query_b += 'r.entity_b_public_id = $entity_public_id'
            elif key == 'connection_type_category':
                connection_type_categories = request.POST.getlist('connection_type_category')
                if query_r_connection_type:
                    query_r_connection_type += ' OR '
                query_r_connection_type += 'r.connection_type_category_string_id IN $connection_type_categories'
            elif key == 'connection_type':
                connection_types = request.POST.getlist('connection_type')
                if query_r_connection_type:
                    query_r_connection_type += ' OR '
                query_r_connection_type += 'r.connection_type_string_id IN $connection_types'
            elif key == 'transaction_date_from':
                transaction_date_from = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_date >= $transaction_date_from'
            elif key == 'transaction_date_to':
                transaction_date_to = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_date <= $transaction_date_to'
            elif key == 'transaction_amount_from':
                transaction_amount_from = float(value)
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_amount >= $transaction_amount_from'
            elif key == 'transaction_amount_to':
                transaction_amount_to = float(value)
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_amount <= $transaction_amount_to'
            elif key == 'entity_type':
                entity_types = request.POST.getlist('entity_type')
                if query_a:
                    query_a += ' AND '
                query_a += 'r.entity_b_entity_type_string_id IN $entity_types'
                if query_b:
                    query_b += ' AND '
                query_b += 'r.entity_a_entity_type_string_id IN $entity_types'
            elif key == 'legal_entity_type':
                legal_entity_types = request.POST.getlist('legal_entity_type')
                if query_a:
                    query_a += ' AND '
                query_a += 'ANY(legal_entity_type IN r.entity_b_legal_entity_type_id WHERE legal_entity_type IN $legal_entity_types)'
                if query_b:
                    query_b += ' AND '
                query_b += 'ANY(legal_entity_type IN r.entity_a_legal_entity_type_id WHERE legal_entity_type IN $legal_entity_types)'
            elif key == 'is_pep' and (value == 'true' or value == 'false'):
                if query_a:
                    query_a += ' AND '
                query_a += 'r.entity_b_is_pep = ' + value
                if query_b:
                    query_b += ' AND '
                query_b += 'r.entity_a_is_pep = ' + value
            elif key == 'valid_from':
                valid_from = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.valid_from >= $valid_from'
            elif key == 'valid_to':
                valid_to = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.valid_to <= $valid_to'

        if query_r_connection_type:
            query_r_exists = False
            if query_r:
                query_r_exists = True
                query_r += ' AND '
            query_r += '(' + query_r_connection_type + ')'
            if query_r_exists:
                query_r = '(' + query_r + ')'

        query_a_b = ''
        if query_a or query_b:
            query_a_b = '((' + query_a + ') OR (' + query_b + '))'

        query = 'MATCH (entity_a:node)-[r1:relationship]-(r:relationship)-[r2:relationship]-(entity_b:node)'
        query += ' WHERE (ID(entity_a) < ID(entity_b))'
        if query_a_b or query_r:
            query += ' AND '
            if query_a_b and query_r:
                query += query_a_b + ' AND ' + query_r
            elif query_a_b:
                query += query_a_b
            elif query_r:
                query += query_r
        query += ' WITH DISTINCT entity_a, entity_b'
        limit = limit if int(limit) <= 100 else '100'
        query_total = query + ' WITH DISTINCT entity_a, entity_b'
        query += ' SKIP $offset LIMIT $limit'
        query += ' WITH COLLECT(DISTINCT entity_a) + COLLECT(DISTINCT entity_b) as union'
        query += ' UNWIND union as nodes'
        query += ' WITH COLLECT(DISTINCT nodes) as distinct_union'
        query += ' MATCH (entity_a_final:node)-[r1_final:relationship]-(r_final:relationship)-[r2_final:relationship]-(entity_b_final:node)'
        query += ' WHERE ID(entity_a_final) < ID(entity_b_final) AND (entity_a_final IN distinct_union AND entity_b_final IN distinct_union)'
        query += ' RETURN DISTINCT entity_a_final, entity_b_final, COLLECT(DISTINCT r_final.connection_type_category_string_id)'
        count = request.POST.get('count') == 'true'
        if count:
            query += ', COUNT(DISTINCT r_final)'

        query_total += ' WITH COLLECT(DISTINCT entity_a) + COLLECT(DISTINCT entity_b) as distinct_union'
        query_total += ' UNWIND distinct_union as nodes'
        query_total += ' RETURN COUNT(DISTINCT nodes) as total'

        results = []
        total = 0
        if Neo4jDB.is_neo4j_settings_exists():
            neo4j = Neo4jDB.get_db().get_neo4j()
            with neo4j.session() as session:
                results = session.run(query, entity_public_id=entity_public_id, connection_types=connection_types,
                                      connection_type_categories=connection_type_categories,
                                      transaction_date_from=transaction_date_from,
                                      transaction_date_to=transaction_date_to,
                                      transaction_amount_from=transaction_amount_from,
                                      transaction_amount_to=transaction_amount_to, entity_types=entity_types,
                                      legal_entity_types=legal_entity_types, valid_from=valid_from, valid_to=valid_to,
                                      offset=int(offset), limit=int(limit))
                total = session.run(query_total, entity_public_id=entity_public_id, connection_types=connection_types,
                                    connection_type_categories=connection_type_categories,
                                    transaction_date_from=transaction_date_from,
                                    transaction_date_to=transaction_date_to,
                                    transaction_amount_from=transaction_amount_from,
                                    transaction_amount_to=transaction_amount_to, entity_types=entity_types,
                                    legal_entity_types=legal_entity_types, valid_from=valid_from, valid_to=valid_to,
                                    offset=int(offset), limit=int(limit)).single().value()

        return Response({'total': total, 'results': results})


class ConnectionsByAttributesValuesGraphView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="entity",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Entity"
                    ),
                ),
                coreapi.Field(
                    name="connection_type_category",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type category"
                    ),
                ),
                coreapi.Field(
                    name="connection_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (to)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (to)"
                    ),
                ),
                coreapi.Field(
                    name="entity_type",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Entity type"
                    ),
                ),
                coreapi.Field(
                    name="legal_entity_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Legal entity type"
                    ),
                ),
                coreapi.Field(
                    name="is_pep",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Is PEP"
                    ),
                ),
                coreapi.Field(
                    name="valid_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid from"
                    ),
                ),
                coreapi.Field(
                    name="valid_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid to"
                    ),
                ),
                coreapi.Field(
                    name="order_by",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order by"
                    ),
                ),
                coreapi.Field(
                    name="order_direction",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order direction"
                    ),
                ),
            ],
        )

    def post(self, request, offset, limit, format=None):
        entity_public_id = None
        connection_type_categories = None
        connection_types = None
        transaction_date_from = None
        transaction_date_to = None
        transaction_amount_from = None
        transaction_amount_to = None
        entity_types = None
        legal_entity_types = None
        valid_from = None
        valid_to = None

        query_a = ''
        query_b = ''
        query_r_connection_type = ''
        query_r = ''

        order_by = None
        order_direction = 'ASC'

        for key, value in request.POST.items():
            if key == 'entity':
                entity_public_id = value
                if query_a:
                    query_a += ' AND '
                query_a += 'r.entity_a_public_id = $entity_public_id'
                if query_b:
                    query_b += ' AND '
                query_b += 'r.entity_b_public_id = $entity_public_id'
            elif key == 'connection_type_category':
                connection_type_categories = request.POST.getlist('connection_type_category')
                if query_r_connection_type:
                    query_r_connection_type += ' OR '
                query_r_connection_type += 'r.connection_type_category_string_id IN $connection_type_categories'
            elif key == 'connection_type':
                connection_types = request.POST.getlist('connection_type')
                if query_r_connection_type:
                    query_r_connection_type += ' OR '
                query_r_connection_type += 'r.connection_type_string_id IN $connection_types'
            elif key == 'transaction_date_from':
                transaction_date_from = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_date >= $transaction_date_from'
            elif key == 'transaction_date_to':
                transaction_date_to = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_date <= $transaction_date_to'
            elif key == 'transaction_amount_from':
                transaction_amount_from = float(value)
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_amount >= $transaction_amount_from'
            elif key == 'transaction_amount_to':
                transaction_amount_to = float(value)
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_amount <= $transaction_amount_to'
            elif key == 'entity_type':
                entity_types = request.POST.getlist('entity_type')
                if query_a:
                    query_a += ' AND '
                query_a += 'r.entity_b_entity_type_string_id IN $entity_types'
                if query_b:
                    query_b += ' AND '
                query_b += 'r.entity_a_entity_type_string_id IN $entity_types'
            elif key == 'legal_entity_type':
                legal_entity_types = request.POST.getlist('legal_entity_type')
                if query_a:
                    query_a += ' AND '
                query_a += 'ANY(legal_entity_type IN r.entity_b_legal_entity_type_id WHERE legal_entity_type IN $legal_entity_types)'
                if query_b:
                    query_b += ' AND '
                query_b += 'ANY(legal_entity_type IN r.entity_a_legal_entity_type_id WHERE legal_entity_type IN $legal_entity_types)'
            elif key == 'is_pep' and (value == 'true' or value == 'false'):
                if query_a:
                    query_a += ' AND '
                query_a += 'r.entity_b_is_pep = ' + value
                if query_b:
                    query_b += ' AND '
                query_b += 'r.entity_a_is_pep = ' + value
            elif key == 'valid_from':
                valid_from = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.valid_from >= $valid_from'
            elif key == 'valid_to':
                valid_to = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.valid_to <= $valid_to'
            elif key == 'order_by':
                if value == 'valid_from' or value == 'valid_to' or value == 'transaction_amount':
                    order_by = value
            elif key == 'order_direction':
                if value == 'asc' or value == 'desc':
                    order_direction = value.upper()

        if query_r_connection_type:
            query_r_exists = False
            if query_r:
                query_r_exists = True
                query_r += ' AND '
            query_r += '(' + query_r_connection_type + ')'
            if query_r_exists:
                query_r = '(' + query_r + ')'

        query_a_b = ''
        if query_a or query_b:
            query_a_b = '((' + query_a + ') OR (' + query_b + '))'

        query = 'MATCH (entity_a:node)-[r1:relationship]->(r:relationship)-[r2:relationship]->(entity_b:node)'
        if query_a_b or query_r:
            query += ' WHERE '
            if query_a_b and query_r:
                query += query_a_b + ' AND ' + query_r
            elif query_a_b:
                query += query_a_b
            elif query_r:
                query += query_r

        query_total_min_max = query + ' RETURN COUNT(DISTINCT r) AS TOTAL, MIN(r.valid_from), MIN(r.valid_to), MAX(r.valid_from), MAX(r.valid_to)'
        query += ' RETURN DISTINCT entity_a, entity_b, r'

        if order_by is not None:
            query += ' ORDER BY r.' + order_by + ' ' + order_direction

        limit = limit if int(limit) <= 100 else '100'

        query += ' SKIP $offset LIMIT $limit'

        results = []
        total = 0
        min_valid = None
        max_valid = None
        if Neo4jDB.is_neo4j_settings_exists():
            neo4j = Neo4jDB.get_db().get_neo4j()
            with neo4j.session() as session:
                results = session.run(query, entity_public_id=entity_public_id, connection_types=connection_types,
                                      connection_type_categories=connection_type_categories,
                                      transaction_date_from=transaction_date_from,
                                      transaction_date_to=transaction_date_to,
                                      transaction_amount_from=transaction_amount_from,
                                      transaction_amount_to=transaction_amount_to, entity_types=entity_types,
                                      legal_entity_types=legal_entity_types, valid_from=valid_from, valid_to=valid_to,
                                      offset=int(offset), limit=int(limit))
                total_min_max = session.run(query_total_min_max, entity_public_id=entity_public_id,
                                            connection_types=connection_types,
                                            connection_type_categories=connection_type_categories,
                                            transaction_date_from=transaction_date_from,
                                            transaction_date_to=transaction_date_to,
                                            transaction_amount_from=transaction_amount_from,
                                            transaction_amount_to=transaction_amount_to, entity_types=entity_types,
                                            legal_entity_types=legal_entity_types, valid_from=valid_from,
                                            valid_to=valid_to).single()
                total = total_min_max.value(0, 0)
                min_valid_from = total_min_max.value(1)
                min_valid_to = total_min_max.value(2)
                max_valid_from = total_min_max.value(3)
                max_valid_to = total_min_max.value(4)

                minimums = set()
                if min_valid_from is not None:
                    minimums.add(datetime.datetime.strptime(min_valid_from, "%Y-%m-%d").date())
                if min_valid_to is not None:
                    minimums.add(datetime.datetime.strptime(min_valid_to, "%Y-%m-%d").date())

                maximums = set()
                if max_valid_from is not None:
                    maximums.add(datetime.datetime.strptime(max_valid_from, "%Y-%m-%d").date())
                if max_valid_to is not None:
                    maximums.add(datetime.datetime.strptime(max_valid_to, "%Y-%m-%d").date())

                if minimums:
                    min_valid = min(minimums)
                if maximums:
                    max_valid = max(maximums)

        return Response({'total': total, 'results': results, 'min_valid': min_valid, 'max_valid': max_valid})


class ConnectionsByEndsView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="connection_type_category",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type category"
                    ),
                ),
                coreapi.Field(
                    name="connection_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (to)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (to)"
                    ),
                ),
                coreapi.Field(
                    name="valid_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid from"
                    ),
                ),
                coreapi.Field(
                    name="valid_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid to"
                    ),
                ),
                coreapi.Field(
                    name="order_by",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order by"
                    ),
                ),
                coreapi.Field(
                    name="order_direction",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order direction"
                    ),
                ),
                coreapi.Field(
                    name="full",
                    required=False,
                    location='form',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def post(self, request, pk1, pk2, offset, limit, format=None):
        query = []

        order_by = None
        order_direction = 'asc'

        connection_type = []

        for key, value in request.POST.items():
            if key == 'connection_type_category':
                for item in request.POST.getlist('connection_type_category'):
                    connection_type.append({
                        'term': {
                            'connection_type_category.string_id': item
                        }
                    })
            elif key == 'connection_type':
                for item in request.POST.getlist('connection_type'):
                    connection_type.append({
                        'term': {
                            'connection_type.string_id': item
                        }
                    })
            elif key == 'transaction_date_from':
                query.append({
                    "range": {
                        "transaction_date": {
                            "gte": value,
                        }
                    }
                })
            elif key == 'transaction_date_to':
                query.append({
                    "range": {
                        "transaction_date": {
                            "lte": value,
                        }
                    }
                })
            elif key == 'transaction_amount_from':
                query.append({
                    "range": {
                        "transaction_amount": {
                            "gte": value,
                        }
                    }
                })
            elif key == 'transaction_amount_to':
                query.append({
                    "range": {
                        "transaction_amount": {
                            "lte": value,
                        }
                    }
                })
            elif key == 'valid_from':
                query.append({
                    "range": {
                        "valid_from": {
                            "gte": value,
                        }
                    }
                })
            elif key == 'valid_to':
                query.append({
                    "range": {
                        "valid_to": {
                            "lte": value,
                        }
                    }
                })
            elif key == 'order_by':
                if value == 'valid_from' or value == 'valid_to' or value == 'transaction_amount':
                    order_by = value
            elif key == 'order_direction':
                if value == 'asc' or value == 'desc':
                    order_direction = value

        if connection_type:
            query.append({
                'bool': {
                    'should': connection_type
                }
            })

        query.append({
            'bool': {
                'should': [
                    {
                        'bool': {
                            'filter': [
                                {
                                    'term': {
                                        'entity_a.public_id': pk1
                                    }
                                },
                                {
                                    'term': {
                                        'entity_b.public_id': pk2
                                    }
                                }
                            ]
                        }
                    },
                    {
                        'bool': {
                            'filter': [
                                {
                                    'term': {
                                        'entity_a.public_id': pk2
                                    }
                                },
                                {
                                    'term': {
                                        'entity_b.public_id': pk1
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        })

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'bool': {
                    'filter': query
                }
            },
        }

        if order_by is not None:
            missing = '_last'
            if order_by == 'valid_from' and order_direction == 'asc':
                missing = '_first'
            if order_by == 'valid_to' and order_direction == 'desc':
                missing = '_first'
            body.update({
                'sort': [
                    {
                        order_by: {
                            'order': order_direction,
                            'missing': missing
                        }
                    }
                ]
            })

        full = request.POST.get('full') == 'true'
        if not full:
            body.update({
                '_source': ['entity_a', 'entity_b', 'connection_type', 'connection_type_category', 'valid_from',
                            'valid_to', 'transaction_amount', 'transaction_date', 'transaction_currency']
            })

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class ConnectionsByEndsGraphView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="connection_type_category",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type category"
                    ),
                ),
                coreapi.Field(
                    name="connection_type",
                    required=False,
                    location='form',
                    schema=coreschema.Array(
                        title="Connection type"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_date_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction date (to)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (from)"
                    ),
                ),
                coreapi.Field(
                    name="transaction_amount_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Transaction amount (to)"
                    ),
                ),
                coreapi.Field(
                    name="valid_from",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid from"
                    ),
                ),
                coreapi.Field(
                    name="valid_to",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Valid to"
                    ),
                ),
                coreapi.Field(
                    name="order_by",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order by"
                    ),
                ),
                coreapi.Field(
                    name="order_direction",
                    required=False,
                    location='form',
                    schema=coreschema.String(
                        title="Order direction"
                    ),
                ),
            ],
        )

    def post(self, request, pk1, pk2, offset, limit, format=None):
        connection_type_categories = None
        connection_types = None
        transaction_date_from = None
        transaction_date_to = None
        transaction_amount_from = None
        transaction_amount_to = None
        valid_from = None
        valid_to = None

        query_r_connection_type = ''
        query_r = ''

        order_by = None
        order_direction = 'ASC'

        for key, value in request.POST.items():
            if key == 'connection_type_category':
                connection_type_categories = request.POST.getlist('connection_type_category')
                if query_r_connection_type:
                    query_r_connection_type += ' OR '
                query_r_connection_type += 'r.connection_type_category_string_id IN $connection_type_categories'
            elif key == 'connection_type':
                connection_types = request.POST.getlist('connection_type')
                if query_r_connection_type:
                    query_r_connection_type += ' OR '
                query_r_connection_type += 'r.connection_type_string_id IN $connection_types'
            elif key == 'transaction_date_from':
                transaction_date_from = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_date >= $transaction_date_from'
            elif key == 'transaction_date_to':
                transaction_date_to = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_date <= $transaction_date_to'
            elif key == 'transaction_amount_from':
                transaction_amount_from = float(value)
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_amount >= $transaction_amount_from'
            elif key == 'transaction_amount_to':
                transaction_amount_to = float(value)
                if query_r:
                    query_r += ' AND '
                query_r += 'r.transaction_amount <= $transaction_amount_to'
            elif key == 'valid_from':
                valid_from = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.valid_from >= $valid_from'
            elif key == 'valid_to':
                valid_to = value
                if query_r:
                    query_r += ' AND '
                query_r += 'r.valid_to <= $valid_to'
            elif key == 'order_by':
                if value == 'valid_from' or value == 'valid_to' or value == 'transaction_amount':
                    order_by = value
            elif key == 'order_direction':
                if value == 'asc' or value == 'desc':
                    order_direction = value.upper()

        if query_r_connection_type:
            query_r_exists = False
            if query_r:
                query_r_exists = True
                query_r += ' AND '
            query_r += '(' + query_r_connection_type + ')'
            if query_r_exists:
                query_r = '(' + query_r + ')'

        query = 'MATCH (entity_a:node)-[r1:relationship]->(r:relationship)-[r2:relationship]->(entity_b:node)'
        query += ' WHERE ((entity_a.public_id = $pk1 AND entity_b.public_id = $pk2) OR (entity_a.public_id = $pk2 AND entity_b.public_id = $pk1))'
        if query_r:
            query += ' AND ' + query_r
        query_total = query + ' RETURN COUNT(DISTINCT r) AS TOTAL'
        query += ' RETURN DISTINCT entity_a, entity_b, r'

        if order_by is not None:
            query += ' ORDER BY r.' + order_by + ' ' + order_direction

        limit = limit if int(limit) <= 100 else '100'

        query += ' SKIP $offset LIMIT $limit'

        results = []
        total = 0
        if Neo4jDB.is_neo4j_settings_exists():
            neo4j = Neo4jDB.get_db().get_neo4j()
            with neo4j.session() as session:
                results = session.run(query, pk1=pk1, pk2=pk2, connection_types=connection_types,
                                      connection_type_categories=connection_type_categories,
                                      transaction_date_from=transaction_date_from,
                                      transaction_date_to=transaction_date_to,
                                      transaction_amount_from=transaction_amount_from,
                                      transaction_amount_to=transaction_amount_to, valid_from=valid_from,
                                      valid_to=valid_to, offset=int(offset), limit=int(limit))
                total = session.run(query_total, pk1=pk1, pk2=pk2, connection_types=connection_types,
                                    connection_type_categories=connection_type_categories,
                                    transaction_date_from=transaction_date_from,
                                    transaction_date_to=transaction_date_to,
                                    transaction_amount_from=transaction_amount_from,
                                    transaction_amount_to=transaction_amount_to, valid_from=valid_from,
                                    valid_to=valid_to).single()

        return Response({'total': total, 'results': results})


class ConnectionsCountPerYearByEndView(APIView):
    def get(self, request, pk, format=None):
        body = {
            'size': 0,
            'query': {
                'bool': {
                    'should': [
                        {
                            'term': {
                                'entity_a.public_id': pk
                            }
                        },
                        {
                            'term': {
                                'entity_b.public_id': pk
                            }
                        }
                    ]
                }
            },
            'aggs': {
                'min_valid_from': {
                    'min': {
                        'field': 'valid_from'
                    }
                },
                'min_valid_to': {
                    'min': {
                        'field': 'valid_to'
                    }
                },
                'max_valid_from': {
                    'max': {
                        'field': 'valid_from'
                    }
                },
                'max_valid_to': {
                    'max': {
                        'field': 'valid_to'
                    }
                },
            },
        }

        ret = {}

        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)

            min_valid_from = results_raw['aggregations']['min_valid_from']['value']
            min_valid_to = results_raw['aggregations']['min_valid_to']['value']

            max_valid_from = results_raw['aggregations']['max_valid_from']['value']
            max_valid_to = results_raw['aggregations']['max_valid_to']['value']

            if min_valid_from is not None or min_valid_to is not None:
                minimums = set()
                if min_valid_from is not None:
                    minimums.add(min_valid_from)
                if min_valid_to is not None:
                    minimums.add(min_valid_to)

                maximums = set()
                if max_valid_from is not None:
                    maximums.add(max_valid_from)
                if max_valid_to is not None:
                    maximums.add(max_valid_to)

                if maximums:
                    max_year = datetime.datetime.fromtimestamp(max(maximums) / 1000.0).year
                    current_year = timezone.now().year
                    if current_year > max_year:
                        max_year = current_year
                else:
                    max_year = timezone.now().year

                if minimums:
                    min_year = datetime.datetime.fromtimestamp(min(minimums) / 1000.0).year
                else:
                    min_year = max_year

                results = {}
                for year in range(min_year, max_year + 1):
                    from_datetime = datetime.datetime(year, 1, 1, 0, 0, 0)
                    to_datetime = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
                    body = {
                        'size': 0,
                        'query': {
                            'bool': {
                                'filter': [
                                    {
                                        'bool': {
                                            'should': [
                                                {
                                                    'term': {
                                                        'entity_a.public_id': pk
                                                    }
                                                },
                                                {
                                                    'term': {
                                                        'entity_b.public_id': pk
                                                    }
                                                }
                                            ]
                                        }
                                    },
                                    {
                                        'bool': {
                                            'should': [
                                                {
                                                    'bool': {
                                                        'filter': [
                                                            {
                                                                'range': {
                                                                    'valid_from': {
                                                                        'lt': to_datetime
                                                                    }
                                                                }
                                                            },
                                                            {
                                                                'range': {
                                                                    'valid_to': {
                                                                        'gte': from_datetime
                                                                    }
                                                                }
                                                            }
                                                        ]
                                                    }
                                                },
                                                {
                                                    'bool': {
                                                        'filter': [
                                                            {
                                                                'range': {
                                                                    'valid_from': {
                                                                        'lt': to_datetime
                                                                    }
                                                                }
                                                            }
                                                        ],
                                                        'must_not': {
                                                            'exists': {
                                                                'field': 'valid_to'
                                                            }
                                                        }
                                                    }
                                                },
                                                {
                                                    'bool': {
                                                        'filter': {
                                                            'range': {
                                                                'valid_to': {
                                                                    'gte': from_datetime,
                                                                    'lt': to_datetime
                                                                }
                                                            }
                                                        },
                                                        'must_not': {
                                                            'exists': {
                                                                'field': 'valid_from'
                                                            }
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        'aggs': {
                            'connection_type_category': {
                                'terms': {
                                    'field': 'connection_type_category.string_id',
                                    'size': const.ELASTICSEARCH_MAX_RESULT_WINDOWS
                                }
                            }
                        }
                    }
                    results_raw = es.search(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
                    results.update({
                        year: {
                            'total': results_raw['hits']['total'],
                            'per_connection_type_category': results_raw['aggregations']['connection_type_category'][
                                'buckets']
                        }
                    })
                ret.update({
                    'min_year': min_year,
                    'max_year': max_year,
                    'results': results
                })

        return Response(ret)


class ConnectionsByEnd(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="full",
                    required=False,
                    location='query',
                    schema=coreschema.Boolean(
                        title="Full"
                    ),
                ),
            ],
        )

    def get(self, request, pk, format=None):
        body = {
            'query': {
                'bool': {
                    'should': [
                        {
                            'term': {
                                'entity_a.public_id': pk
                            }
                        },
                        {
                            'term': {
                                'entity_b.public_id': pk
                            }
                        }
                    ]
                }
            }
        }

        full = request.GET.get('full') == 'true'
        if not full:
            body.update({
                '_source': ['entity_a', 'entity_b', 'connection_type', 'connection_type_category', 'valid_from',
                            'valid_to', 'transaction_amount', 'transaction_date', 'transaction_currency']
            })

        results = []
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'id': hit['_id']
                })
                results.append(source)

        if len(results) > 0:
            if request.GET.get('as_file') == 'true':
                json_chunk_generator = helpers.JSONChunkGenerator(renderer=JSONRenderer(), last_id=results[-1]['id'],
                                                                  raw=True)
            else:
                json_chunk_generator = helpers.JSONChunkGenerator(renderer=JSONRenderer(), last_id=results[-1]['id'])
            response = StreamingHttpResponse(
                (json_chunk_generator.generate(data=result) for result in results), content_type='application/json')
        else:
            if request.GET.get('as_file') == 'true':
                response = Response(results)
            else:
                response = Response({'results': results})

        if request.GET.get('as_file') == 'true':
            response['Content-Disposition'] = 'attachment; filename="connections_%s.json"' % pk

        return response


class AttributesByEntityTypeView(APIView):
    def get(self, request, entity_type, offset, limit, format=None):
        if not models.StaticEntityType.objects.filter(string_id=entity_type).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        body = {
            'from': offset,
            'size': limit,
            'query': {
                'term': {
                    'entity_type.string_id': entity_type
                }
            },
            'sort': [
                {
                    'order_number': {
                        'order': 'asc'
                    }
                },
            ],
        }

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'string_id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class AttributesConnectionsView(APIView):
    def get(self, request, offset, limit, format=None):
        body = {
            'from': offset,
            'size': limit,
            'query': {
                'exists': {
                    'field': 'collection.string_id'
                }
            },
            'sort': [
                {
                    'order_number': {
                        'order': 'asc'
                    }
                },
            ],
        }

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'string_id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class AutocompleteConnectionTypesView(APIView):
    def get(self, request, connection_type_category, term, offset, limit, format=None):
        if not models.StaticConnectionTypeCategory.objects.filter(string_id=connection_type_category).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'bool': {
                    'must': [
                        {
                            'term': {
                                'connection_type_category.string_id': connection_type_category
                            }
                        },
                        {
                            'match': {
                                const.ELASTICSEARCH_SEARCH_FIELD_NAME: {
                                    'query': term,
                                    'operator': 'and'
                                }
                            }
                        }
                    ]
                }
            },
            'sort': [
                {
                    'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                        'order': 'asc'
                    }
                },
            ],
        }

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'string_id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class ConnectionTypesByConnectionTypeCategoryView(APIView):
    if coreapi is not None and coreschema is not None:
        schema = AutoSchema(
            manual_fields=[
                coreapi.Field(
                    name="only_count",
                    required=False,
                    location='query',
                    schema=coreschema.Array(
                        title="Only count"
                    ),
                ),
            ],
        )

    def get(self, request, connection_type_category, offset, limit, format=None):
        if not models.StaticConnectionTypeCategory.objects.filter(string_id=connection_type_category).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        limit = limit if int(limit) <= 100 else '100'

        size = limit
        from_ = offset
        only_count = request.GET.get('only_count') == 'true'
        if only_count:
            size = 0
            from_ = 0

        body = {
            'size': size,
            'from': from_,
            'query': {
                'term': {
                    'connection_type_category.string_id': connection_type_category
                }
            },
        }

        if not only_count:
            body.update({
                'sort': [
                    {
                        'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                            'order': 'asc'
                        }
                    },
                ],
            })

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            if not only_count:
                for hit in hits['hits']:
                    source = hit['_source']
                    source.update({
                        'string_id': hit['_id']
                    })
                    results.append(source)

        result_for_response = {
            'total': total
        }
        if not only_count:
            result_for_response.update({
                'results': results
            })

        return Response(result_for_response)


class LogAttributeValueChangeView(APIView):
    def get(self, request, type, pk, attribute, offset, limit, format=None):
        if type != 'entity' and type != 'connection':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not models.StageAttribute.objects.filter(string_id=attribute).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        field = 'entity_public_id-attribute_string_id'
        if type == 'connection':
            field = 'connection_id-attribute_string_id'

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'term': {
                    field: pk + '#' + attribute
                }
            },
            'sort': [
                {
                    'created_at': {
                        'order': 'desc'
                    }
                }
            ]
        }

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'id': hit['_id']
                })
                data_type = source['attribute']['attribute_type']['data_type']['string_id']
                if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
                    if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                        source['old_value'] = source.pop('old_value_boolean')
                        source['new_value'] = source.pop('new_value_boolean')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                        source['old_value'] = source.pop('old_value_int')
                        source['new_value'] = source.pop('new_value_int')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                        decimal_places = source['attribute']['attribute_type']['fixed_point_decimal_places']
                        if decimal_places is None:
                            decimal_places = helpers.get_mocbackend_default_setting('FIXED_POINT_DECIMAL_PLACES')
                        decimal_places = 10 ** decimal_places

                        old_value_fixed_point = source.pop('old_value_fixed_point')
                        source[
                            'old_value'] = old_value_fixed_point if old_value_fixed_point is None else old_value_fixed_point / decimal_places

                        new_value_fixed_point = source.pop('new_value_fixed_point')
                        source[
                            'new_value'] = new_value_fixed_point if new_value_fixed_point is None else new_value_fixed_point / decimal_places
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                        source['old_value'] = source.pop('old_value_floating_point')
                        source['new_value'] = source.pop('new_value_floating_point')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                        source['old_value'] = source.pop('old_value_string')
                        source['new_value'] = source.pop('new_value_string')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                        source['old_value'] = source.pop('old_value_text')
                        source['new_value'] = source.pop('new_value_text')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                        source['old_value'] = source.pop('old_value_datetime')
                        source['new_value'] = source.pop('new_value_datetime')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                        source['old_value'] = source.pop('old_value_date')
                        source['new_value'] = source.pop('new_value_date')
                    elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                        source['old_value'] = source.pop('old_value_codebook_item')
                        source['new_value'] = source.pop('new_value_codebook_item')
                elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
                    if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                        try:
                            source['old_value'] = source.pop('old_value_geo')
                        except KeyError:
                            source['old_value'] = {
                                'lat': None,
                                'lon': None
                            }
                        try:
                            source['new_value'] = source.pop('new_value_geo')
                        except KeyError:
                            source['new_value'] = {
                                'lat': None,
                                'lon': None
                            }
                    elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                        source['old_value'] = source.pop('old_value_range_int')
                        source['new_value'] = source.pop('new_value_range_int')
                    elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                        decimal_places = source['attribute']['attribute_type']['fixed_point_decimal_places']
                        if decimal_places is None:
                            decimal_places = helpers.get_mocbackend_default_setting('FIXED_POINT_DECIMAL_PLACES')
                        decimal_places = 10 ** decimal_places

                        old_value_range_fixed_point = source.pop('old_value_range_fixed_point')
                        old_value_range_fixed_point_gte = old_value_range_fixed_point['gte']
                        old_value_range_fixed_point_lte = old_value_range_fixed_point['lte']
                        source['old_value'] = {
                            'gte': old_value_range_fixed_point_gte if old_value_range_fixed_point_gte is None else old_value_range_fixed_point_gte / decimal_places,
                            'lte': old_value_range_fixed_point_lte if old_value_range_fixed_point_lte is None else old_value_range_fixed_point_lte / decimal_places
                        }

                        new_value_range_fixed_point = source.pop('new_value_range_fixed_point')
                        new_value_range_fixed_point_gte = new_value_range_fixed_point['gte']
                        new_value_range_fixed_point_lte = new_value_range_fixed_point['lte']
                        source['new_value'] = {
                            'gte': new_value_range_fixed_point_gte if new_value_range_fixed_point_gte is None else new_value_range_fixed_point_gte / decimal_places,
                            'lte': new_value_range_fixed_point_lte if new_value_range_fixed_point_lte is None else new_value_range_fixed_point_lte / decimal_places
                        }
                    elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                        source['old_value'] = source.pop('old_value_range_floating_point')
                        source['new_value'] = source.pop('new_value_range_floating_point')
                    elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                        source['old_value'] = source.pop('old_value_range_datetime')
                        source['new_value'] = source.pop('new_value_range_datetime')
                    elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                        source['old_value'] = source.pop('old_value_range_date')
                        source['new_value'] = source.pop('new_value_range_date')
                results.append(source)

        return Response({'total': total, 'results': results})


class LogEntityEntityChangeView(APIView):
    def get(self, request, pk, offset, limit, format=None):

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'term': {
                    'connection.id': pk
                }
            },
            'sort': [
                {
                    'created_at': {
                        'order': 'desc'
                    }
                }
            ]
        }

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class CodebookValuesView(APIView):
    def get(self, request, codebook, offset, limit, format=None):
        if not models.StageCodebook.objects.filter(string_id=codebook).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        limit = limit if int(limit) <= 100 else '100'

        body = {
            'from': offset,
            'size': limit,
            'query': {
                'term': {
                    'codebook.string_id': codebook
                }
            },
            'sort': [
                {
                    'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                        'order': 'asc'
                    }
                },
            ],
        }

        results = []
        total = 0
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            results_raw = es.search(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)
            hits = results_raw['hits']
            total = hits['total']
            for hit in hits['hits']:
                source = hit['_source']
                source.update({
                    'string_id': hit['_id']
                })
                results.append(source)

        return Response({'total': total, 'results': results})


class ObjectsCountView(APIView):
    def get(self, request, format=None):
        body = {
            'size': 0,
            'aggs': {
                'entities_count': {
                    'terms': {
                        'field': 'entity_type.string_id',
                        'size': const.ELASTICSEARCH_MAX_RESULT_WINDOWS
                    }
                }
            }
        }

        body2 = {
            'size': 0
        }

        result = {
            'entities_count': {},
            'connections_count': 0
        }
        if ElasticsearchDB.is_elasticsearch_settings_exists():
            es = ElasticsearchDB.get_db().get_elasticsearch()
            result_raw = es.search(index=ElasticsearchDB.get_elasticsearch_index_name(
                const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body)

            buckets = result_raw['aggregations']['entities_count']['buckets']
            entities_count = {}
            for bucket in buckets:
                entities_count.update({
                    bucket['key']: bucket['doc_count']
                })

            result.update({
                'entities_count': entities_count
            })

            result_raw = es.search(index=ElasticsearchDB.get_elasticsearch_index_name(
                const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=body2)

            connections_count = result_raw['hits']['total']

            result.update({
                'connections_count': connections_count
            })

        return Response({'result': result})


class ArticleViewSet(ListSerializerClass, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.Article.objects.all()
    serializer_class = serializers.ArticleSerializer
    list_serializer_class = serializers.ArticleListSerializer
    lookup_field = 'slug'
    permission_classes = [
        permissions.IsStaffOrInAnyAllowedGroups | permissions.IsSafeMethod | permissions.IsAllowedActions]
    allowed_groups = ('importer',)


class ArticleContentShortViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.Article.objects.all()
    serializer_class = serializers.ArticleContentShortSerializer
    lookup_field = 'slug'


class ArticleContentLongViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = models.Article.objects.all()
    serializer_class = serializers.ArticleContentLongSerializer
    lookup_field = 'slug'


class UserViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                  mixins.DestroyModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = django.contrib.auth.models.User.objects.all()
    serializer_class = serializers.UserRetrieveSerializer
    create_serializer_class = serializers.UserCreateSerializer
    update_serializer_class = serializers.UserUpdateSerializer
    lookup_field = 'username'
    permission_classes = [permissions.IsSafeMethod | permissions.IsSelfOrIsAllowedActions]
    allowed_actions = ('create',)

    def perform_create(self, serializer):
        instance = serializer.save()
        if hasattr(serializer, '_email_verification_token'):
            # print(serializer._email_verification_token)
            helpers.send_mail_q(
                template_name='create_user',
                from_email='kontakt@mozaikveza.hr',
                recipient_list=[serializer.validated_data['email']],
                context={
                    'username': instance.username,
                    'token': serializer._email_verification_token
                },
                fail_silently=False
            )

    def perform_update(self, serializer):
        instance = serializer.save()
        if hasattr(serializer, '_email_verification_token'):
            # print(serializer._email_verification_token)
            helpers.send_mail_q(
                template_name='update_user',
                from_email='kontakt@mozaikveza.hr',
                recipient_list=[serializer.validated_data['email']],
                context={
                    'username': instance.username,
                    'token': serializer._email_verification_token
                },
                fail_silently=False,
            )


class UserPasswordViewSet(ListSerializerClass, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = django.contrib.auth.models.User.objects.all()
    serializer_class = serializers.UserPasswordSerializer
    lookup_field = 'username'
    permission_classes = [permissions.IsSelfOrIsAllowedActions]


class VerifyEmailViewSet(ListSerializerClass, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = django.contrib.auth.models.User.objects.all()
    serializer_class = serializers.VerifyEmailSerializer


class GeneratePasswordChangeTokenViewSet(ListSerializerClass, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = django.contrib.auth.models.User.objects.all()
    serializer_class = serializers.GeneratePasswordChangeTokenSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        # print(serializer._password_change_token)
        helpers.send_mail_q(
            template_name='change_password',
            from_email='kontakt@mozaikveza.hr',
            recipient_list=[serializer.validated_data['email']],
            context={
                'username': instance.username,
                'token': serializer._password_change_token
            },
            fail_silently=False,
        )


class UserPasswordWithoutAuthViewSet(ListSerializerClass, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = django.contrib.auth.models.User.objects.all()
    serializer_class = serializers.UserPasswordWithoutAuthSerializer
    lookup_field = 'username'


class UserEntityViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = models.UserEntity.objects.all()
    serializer_class = serializers.UserEntitySerializer
    create_serializer_class = serializers.UserEntityCreateSerializer
    permission_classes = [IsAuthenticated, permissions.IsOwner]
    lookup_field = 'entity__public_id'

    def get_queryset(self):
        return models.UserEntity.objects.filter(owner__user=self.request.user)


class UserSavedSearchViewSet(ListSerializerClass, mixins.CreateModelMixin, mixins.ListModelMixin,
                             mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                             viewsets.GenericViewSet):
    queryset = models.UserSavedSearch.objects.all()
    serializer_class = serializers.UserSavedSearchSerializer
    create_serializer_class = serializers.UserSavedSearchCreateSerializer
    update_serializer_class = serializers.UserSavedSearchUpdateSerializer
    permission_classes = [IsAuthenticated, permissions.IsOwner]

    def get_queryset(self):
        return models.UserSavedSearch.objects.filter(owner__user=self.request.user)
