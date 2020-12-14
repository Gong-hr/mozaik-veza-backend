import logging
from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.db.models import Q
from elasticsearch import Elasticsearch, NotFoundError
from neo4j import GraphDatabase

from mocbackend import helpers, models, const, middleware
import django_rq

logger = logging.getLogger(__name__)


class BaseDatabase:
    __metaclass__ = ABCMeta

    @staticmethod
    @abstractmethod
    def get_db():
        pass

    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def put_entity_attribute_mapping(self, attribute):
        pass

    @abstractmethod
    def put_entity_connection_type_category_count_mapping(self, connection_type_category):
        pass

    @abstractmethod
    def delete_entity_attribute_mapping(self, attribute):
        pass

    @abstractmethod
    def add_entity(self, entity, overwrite, add_connections):
        pass

    @abstractmethod
    def update_entity(self, entity, update_connections):
        pass

    @abstractmethod
    def delete_entity(self, entity, delete_all):
        pass

    @abstractmethod
    def add_connection(self, entity_entity, calculate_count, overwrite):
        pass

    @abstractmethod
    def update_connection(self, entity_entity, calculate_count):
        pass

    @abstractmethod
    def delete_connection(self, entity_entity, calculate_count, delete_all):
        pass

    @staticmethod
    def _is_pep(entity):
        is_pep = None
        if entity.entity_type.string_id == 'person':
            is_pep = False
            if entity.force_pep:
                is_pep = True

            entity_type_legal_entity = models.StaticEntityType.objects.get(string_id='legal_entity')

            if not is_pep and entity.reverse_connections.filter(deleted=False, published=True,
                                                                entity_entity_collections__deleted=False,
                                                                entity_entity_collections__published=True,
                                                                entity_entity_collections__collection__deleted=False,
                                                                entity_entity_collections__collection__published=True,
                                                                entity_entity_collections__collection__source__deleted=False,
                                                                entity_entity_collections__collection__source__published=True,
                                                                connection_type__potentially_pep=True,
                                                                entity_b__deleted=False, entity_b__published=True,
                                                                entity_b__linked_potentially_pep=True,
                                                                entity_b__entity_type=entity_type_legal_entity).distinct().exists():
                is_pep = True
            if not is_pep and entity.connections.filter(deleted=False, published=True,
                                                        entity_entity_collections__deleted=False,
                                                        entity_entity_collections__published=True,
                                                        entity_entity_collections__collection__deleted=False,
                                                        entity_entity_collections__collection__published=True,
                                                        entity_entity_collections__collection__source__deleted=False,
                                                        entity_entity_collections__collection__source__published=True,
                                                        connection_type__potentially_pep=True,
                                                        entity_a__deleted=False, entity_a__published=True,
                                                        entity_a__linked_potentially_pep=True,
                                                        entity_a__entity_type=entity_type_legal_entity).distinct().exists():
                is_pep = True

            if not is_pep and entity.reverse_connections.filter(deleted=False, published=True,
                                                                entity_entity_collections__deleted=False,
                                                                entity_entity_collections__published=True,
                                                                entity_entity_collections__collection__deleted=False,
                                                                entity_entity_collections__collection__published=True,
                                                                entity_entity_collections__collection__source__deleted=False,
                                                                entity_entity_collections__collection__source__published=True,
                                                                entity_b__deleted=False, entity_b__published=True,
                                                                entity_b__force_pep=True).distinct().exists():
                is_pep = True
            if not is_pep and entity.connections.filter(deleted=False, published=True,
                                                        entity_entity_collections__deleted=False,
                                                        entity_entity_collections__published=True,
                                                        entity_entity_collections__collection__deleted=False,
                                                        entity_entity_collections__collection__published=True,
                                                        entity_entity_collections__collection__source__deleted=False,
                                                        entity_entity_collections__collection__source__published=True,
                                                        entity_a__deleted=False, entity_a__published=True,
                                                        entity_a__force_pep=True).distinct().exists():
                is_pep = True

            if not is_pep and entity.reverse_connections.filter(deleted=False, published=True,
                                                                entity_entity_collections__deleted=False,
                                                                entity_entity_collections__published=True,
                                                                entity_entity_collections__collection__deleted=False,
                                                                entity_entity_collections__collection__published=True,
                                                                entity_entity_collections__collection__source__deleted=False,
                                                                entity_entity_collections__collection__source__published=True,
                                                                entity_b__deleted=False, entity_b__published=True,
                                                                entity_b__reverse_connections__deleted=False,
                                                                entity_b__reverse_connections__published=True,
                                                                entity_b__reverse_connections__entity_entity_collections__deleted=False,
                                                                entity_b__reverse_connections__entity_entity_collections__published=True,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__deleted=False,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__published=True,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__source__deleted=False,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__source__published=True,
                                                                entity_b__reverse_connections__connection_type__potentially_pep=True,
                                                                entity_b__reverse_connections__entity_b__deleted=False,
                                                                entity_b__reverse_connections__entity_b__published=True,
                                                                entity_b__reverse_connections__entity_b__linked_potentially_pep=True,
                                                                entity_b__reverse_connections__entity_b__entity_type=entity_type_legal_entity).distinct().exists():
                is_pep = True
            if not is_pep and entity.reverse_connections.filter(deleted=False, published=True,
                                                                entity_entity_collections__deleted=False,
                                                                entity_entity_collections__published=True,
                                                                entity_entity_collections__collection__deleted=False,
                                                                entity_entity_collections__collection__published=True,
                                                                entity_entity_collections__collection__source__deleted=False,
                                                                entity_entity_collections__collection__source__published=True,
                                                                entity_b__deleted=False, entity_b__published=True,
                                                                entity_b__connections__deleted=False,
                                                                entity_b__connections__published=True,
                                                                entity_b__connections__entity_entity_collections__deleted=False,
                                                                entity_b__connections__entity_entity_collections__published=True,
                                                                entity_b__connections__entity_entity_collections__collection__deleted=False,
                                                                entity_b__connections__entity_entity_collections__collection__published=True,
                                                                entity_b__connections__entity_entity_collections__collection__source__deleted=False,
                                                                entity_b__connections__entity_entity_collections__collection__source__published=True,
                                                                entity_b__connections__connection_type__potentially_pep=True,
                                                                entity_b__connections__entity_a__deleted=False,
                                                                entity_b__connections__entity_a__published=True,
                                                                entity_b__connections__entity_a__linked_potentially_pep=True,
                                                                entity_b__connections__entity_a__entity_type=entity_type_legal_entity).distinct().exists():
                is_pep = True

            if not is_pep and entity.connections.filter(deleted=False, published=True,
                                                        entity_entity_collections__deleted=False,
                                                        entity_entity_collections__published=True,
                                                        entity_entity_collections__collection__deleted=False,
                                                        entity_entity_collections__collection__published=True,
                                                        entity_entity_collections__collection__source__deleted=False,
                                                        entity_entity_collections__collection__source__published=True,
                                                        entity_a__deleted=False, entity_a__published=True,
                                                        entity_a__reverse_connections__deleted=False,
                                                        entity_a__reverse_connections__published=True,
                                                        entity_a__reverse_connections__entity_entity_collections__deleted=False,
                                                        entity_a__reverse_connections__entity_entity_collections__published=True,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__deleted=False,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__published=True,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__source__deleted=False,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__source__published=True,
                                                        entity_a__reverse_connections__connection_type__potentially_pep=True,
                                                        entity_a__reverse_connections__entity_b__deleted=False,
                                                        entity_a__reverse_connections__entity_b__published=True,
                                                        entity_a__reverse_connections__entity_b__linked_potentially_pep=True,
                                                        entity_a__reverse_connections__entity_b__entity_type=entity_type_legal_entity).distinct().exists():
                is_pep = True
            if not is_pep and entity.connections.filter(deleted=False, published=True,
                                                        entity_entity_collections__deleted=False,
                                                        entity_entity_collections__published=True,
                                                        entity_entity_collections__collection__deleted=False,
                                                        entity_entity_collections__collection__published=True,
                                                        entity_entity_collections__collection__source__deleted=False,
                                                        entity_entity_collections__collection__source__published=True,
                                                        entity_a__deleted=False, entity_a__published=True,
                                                        entity_a__connections__deleted=False,
                                                        entity_a__connections__published=True,
                                                        entity_a__connections__entity_entity_collections__deleted=False,
                                                        entity_a__connections__entity_entity_collections__published=True,
                                                        entity_a__connections__entity_entity_collections__collection__deleted=False,
                                                        entity_a__connections__entity_entity_collections__collection__published=True,
                                                        entity_a__connections__entity_entity_collections__collection__source__deleted=False,
                                                        entity_a__connections__entity_entity_collections__collection__source__published=True,
                                                        entity_a__connections__connection_type__potentially_pep=True,
                                                        entity_a__connections__entity_a__deleted=False,
                                                        entity_a__connections__entity_a__published=True,
                                                        entity_a__connections__entity_a__linked_potentially_pep=True,
                                                        entity_a__connections__entity_a__entity_type=entity_type_legal_entity).distinct().exists():
                is_pep = True

            if not is_pep and entity.reverse_connections.filter(deleted=False, published=True,
                                                                entity_entity_collections__deleted=False,
                                                                entity_entity_collections__published=True,
                                                                entity_entity_collections__collection__deleted=False,
                                                                entity_entity_collections__collection__published=True,
                                                                entity_entity_collections__collection__source__deleted=False,
                                                                entity_entity_collections__collection__source__published=True,
                                                                entity_b__deleted=False, entity_b__published=True,
                                                                entity_b__reverse_connections__deleted=False,
                                                                entity_b__reverse_connections__published=True,
                                                                entity_b__reverse_connections__entity_entity_collections__deleted=False,
                                                                entity_b__reverse_connections__entity_entity_collections__published=True,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__deleted=False,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__published=True,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__source__deleted=False,
                                                                entity_b__reverse_connections__entity_entity_collections__collection__source__published=True,
                                                                entity_b__reverse_connections__entity_b__deleted=False,
                                                                entity_b__reverse_connections__entity_b__published=True,
                                                                entity_b__reverse_connections__entity_b__force_pep=True).distinct().exists():
                is_pep = True
            if not is_pep and entity.reverse_connections.filter(deleted=False, published=True,
                                                                entity_entity_collections__deleted=False,
                                                                entity_entity_collections__published=True,
                                                                entity_entity_collections__collection__deleted=False,
                                                                entity_entity_collections__collection__published=True,
                                                                entity_entity_collections__collection__source__deleted=False,
                                                                entity_entity_collections__collection__source__published=True,
                                                                entity_b__deleted=False, entity_b__published=True,
                                                                entity_b__connections__deleted=False,
                                                                entity_b__connections__published=True,
                                                                entity_b__connections__entity_entity_collections__deleted=False,
                                                                entity_b__connections__entity_entity_collections__published=True,
                                                                entity_b__connections__entity_entity_collections__collection__deleted=False,
                                                                entity_b__connections__entity_entity_collections__collection__published=True,
                                                                entity_b__connections__entity_entity_collections__collection__source__deleted=False,
                                                                entity_b__connections__entity_entity_collections__collection__source__published=True,
                                                                entity_b__connections__entity_a__deleted=False,
                                                                entity_b__connections__entity_a__published=True,
                                                                entity_b__connections__entity_a__force_pep=True).distinct().exists():
                is_pep = True

            if not is_pep and entity.connections.filter(deleted=False, published=True,
                                                        entity_entity_collections__deleted=False,
                                                        entity_entity_collections__published=True,
                                                        entity_entity_collections__collection__deleted=False,
                                                        entity_entity_collections__collection__published=True,
                                                        entity_entity_collections__collection__source__deleted=False,
                                                        entity_entity_collections__collection__source__published=True,
                                                        entity_a__deleted=False, entity_a__published=True,
                                                        entity_a__reverse_connections__deleted=False,
                                                        entity_a__reverse_connections__published=True,
                                                        entity_a__reverse_connections__entity_entity_collections__deleted=False,
                                                        entity_a__reverse_connections__entity_entity_collections__published=True,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__deleted=False,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__published=True,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__source__deleted=False,
                                                        entity_a__reverse_connections__entity_entity_collections__collection__source__published=True,
                                                        entity_a__reverse_connections__entity_b__deleted=False,
                                                        entity_a__reverse_connections__entity_b__published=True,
                                                        entity_a__reverse_connections__entity_b__force_pep=True).distinct().exists():
                is_pep = True

            if not is_pep and entity.connections.filter(deleted=False, published=True,
                                                        entity_entity_collections__deleted=False,
                                                        entity_entity_collections__published=True,
                                                        entity_entity_collections__collection__deleted=False,
                                                        entity_entity_collections__collection__published=True,
                                                        entity_entity_collections__collection__source__deleted=False,
                                                        entity_entity_collections__collection__source__published=True,
                                                        entity_a__deleted=False, entity_a__published=True,
                                                        entity_a__connections__deleted=False,
                                                        entity_a__connections__published=True,
                                                        entity_a__connections__entity_entity_collections__deleted=False,
                                                        entity_a__connections__entity_entity_collections__published=True,
                                                        entity_a__connections__entity_entity_collections__collection__deleted=False,
                                                        entity_a__connections__entity_entity_collections__collection__published=True,
                                                        entity_a__connections__entity_entity_collections__collection__source__deleted=False,
                                                        entity_a__connections__entity_entity_collections__collection__source__published=True,
                                                        entity_a__connections__entity_a__deleted=False,
                                                        entity_a__connections__entity_a__published=True,
                                                        entity_a__connections__entity_a__force_pep=True).distinct().exists():
                is_pep = True

        return is_pep


class ElasticsearchDB(BaseDatabase):
    const.ELASTICSEARCH_DEFAULTS = {
        'HOST': '127.0.0.1',
        'PORT': '9200',
        'USE_SSL': False,

        'INDICES_PREFIX': 'mocbackend',
        'DOC_TYPE_NAME': 'default'
    }

    const.DATA_TYPE_MAPPING_TO_ELASTIC = {
        const.DATA_TYPE_BOOLEAN: 'boolean',
        const.DATA_TYPE_INT: 'long',
        const.DATA_TYPE_FIXED_POINT: 'scaled_float',
        const.DATA_TYPE_FLOATING_POINT: 'double',
        const.DATA_TYPE_STRING: 'text',
        const.DATA_TYPE_TEXT: 'text',
        const.DATA_TYPE_DATETIME: 'date',
        const.DATA_TYPE_DATE: 'date',
        const.DATA_TYPE_CODEBOOK: 'text',
        const.DATA_TYPE_GEO: 'geo_point',
        const.DATA_TYPE_RANGE_INT: 'long_range',
        const.DATA_TYPE_RANGE_FIXED_POINT: 'scaled_float',
        const.DATA_TYPE_RANGE_FLOATING_POINT: 'double_range',
        const.DATA_TYPE_RANGE_DATETIME: 'date_range',
        const.DATA_TYPE_RANGE_DATE: 'date_range',
        const.DATA_TYPE_COMPLEX: None
    }

    const.DATA_TYPE_ELASTICSEARCH_KEYWORD = 'keyword'
    const.DATA_TYPE_ELASTICSEARCH_NESTED = 'nested'
    const.DATA_TYPE_ELASTICSEARCH_SHORT = 'short'  # 2 bytes (16 bit) postgres data type: smallint
    const.DATA_TYPE_ELASTICSEARCH_INTEGER = 'integer'  # 4 bytes (32 bit) postgres data type: integer

    const.ELASTICSEARCH_ENTITIES_INDEX_NAME = 'entity'  # not deleted & published
    const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME = 'entity-all'  # all

    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME = 'connection'  # not deleted & published
    const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME = 'connection-all'  # all

    const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME = 'attribute'

    const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME = 'connection-type'

    const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME = 'attribute-value-log'

    const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME = 'entity-entity-log'

    const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME = 'codebook'

    const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX = '_exact'
    const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX = '_id'
    const.ELASTICSEARCH_CONNECTION_TYPE_CATEGORY_COUNT_FIELD_PREFIX = 'count_'

    const.ELASTICSEARCH_SEARCH_FIELD_NAME = 'search'

    const.ELASTICSEARCH_VALUE_FIELD_NAME = 'value'

    const.ELASTICSEARCH_NESTED_FIELDS_LIMIT = 10000
    const.ELASTICSEARCH_TOTAL_FIELDS_LIMIT = 100000
    const.ELASTICSEARCH_MAX_RESULT_WINDOWS = 100000

    const.SEARCH_ATTRIBUTES = [
        'person_first_name',
        'person_last_name',
        'legal_entity_name',
        # 'person_vat_number',
        # 'legal_entity_vat_number',
        # 'legal_entity_entity_type'
    ]

    elasticsearch = None

    @staticmethod
    def get_db():
        ret = None
        request_loc_mem_cache = None
        try:
            request_loc_mem_cache = middleware.get_request_loc_mem_cache()
            ret = request_loc_mem_cache.get('elasticsearchdb')
        except AssertionError:
            pass
        if ret is None:
            ret = ElasticsearchDB()
            if request_loc_mem_cache is not None:
                request_loc_mem_cache.set('elasticsearchdb', ret)
        return ret

    @staticmethod
    def get_elasticsearch_index_name(name):
        indices_prefix = ElasticsearchDB._get_elasticsearch_setting('INDICES_PREFIX')
        return indices_prefix + '-' + name

    @staticmethod
    def get_elasticsearch_doc_type():
        ret = ElasticsearchDB._get_elasticsearch_setting('DOC_TYPE_NAME')
        return ret

    @staticmethod
    def _get_elasticsearch_setting(setting_name):
        ret = None
        addon_databases = getattr(settings, 'ADDON_DATABASES', None)
        if addon_databases is not None:
            for addon_database in addon_databases:
                if 'BACKEND' in addon_database and addon_database['BACKEND'] == 'mocbackend.databases.ElasticsearchDB':
                    if setting_name in addon_database:
                        ret = addon_database[setting_name]
                    elif setting_name in const.ELASTICSEARCH_DEFAULTS:
                        ret = const.ELASTICSEARCH_DEFAULTS[setting_name]
                    break
        return ret

    @staticmethod
    def is_elasticsearch_settings_exists():
        ret = False
        addon_databases = getattr(settings, 'ADDON_DATABASES', None)
        if addon_databases is not None:
            for addon_database in addon_databases:
                if 'BACKEND' in addon_database and addon_database['BACKEND'] == 'mocbackend.databases.ElasticsearchDB':
                    ret = True
        return ret

    @staticmethod
    def _get_elasticsearch_connection_strings():
        ret = []
        if ElasticsearchDB._get_elasticsearch_setting('USE_SSL'):
            connection_string = 'https://'
        else:
            connection_string = 'http://'
        user = ElasticsearchDB._get_elasticsearch_setting('USER')
        if user is not None:
            connection_string = connection_string + user
            password = ElasticsearchDB._get_elasticsearch_setting('PASSWORD')
            if password is not None:
                connection_string = connection_string + ':' + password
            connection_string = connection_string + '@'
        connection_string = connection_string + ElasticsearchDB._get_elasticsearch_setting(
            'HOST') + ':' + ElasticsearchDB._get_elasticsearch_setting('PORT')
        ret.append(connection_string)
        return ret

    @staticmethod
    def _get_elasticsearch_field_mapping_properties(attribute):
        field_name = attribute.string_id
        data_type = attribute.attribute_type.data_type.string_id

        internal_data_type = None

        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            internal_data_type = const.DATA_TYPE_MAPPING_SIMPLE[data_type]
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            internal_data_type = const.DATA_TYPE_MAPPING_COMPLEX[data_type]

        if internal_data_type is None or internal_data_type not in const.DATA_TYPE_MAPPING_TO_ELASTIC:
            raise Exception('Unknown data type')

        inner_field_name = const.ELASTICSEARCH_VALUE_FIELD_NAME
        value_field_properties = {
            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[internal_data_type]
        }
        if internal_data_type in [const.DATA_TYPE_STRING, const.DATA_TYPE_TEXT, const.DATA_TYPE_CODEBOOK]:
            value_field_properties.update({
                'analyzer': 'standard_hr_diacritics'
            })
        elif internal_data_type == const.DATA_TYPE_FIXED_POINT:
            value_field_properties.update({
                'scaling_factor': helpers.get_divider(attribute.attribute_type)
            })
        elif internal_data_type == const.DATA_TYPE_DATETIME or internal_data_type == const.DATA_TYPE_RANGE_DATETIME:
            value_field_properties.update({
                'format': 'date_time||date_time_no_millis||date'
            })
        elif internal_data_type == const.DATA_TYPE_DATE or internal_data_type == const.DATA_TYPE_RANGE_DATE:
            value_field_properties.update({
                'format': 'date'
            })
        elif internal_data_type == const.DATA_TYPE_RANGE_FIXED_POINT:
            inner_value_field_properties = {
                'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[internal_data_type],
                'scaling_factor': helpers.get_divider(attribute.attribute_type)
            }
            value_field_properties = {
                'properties': {
                    'gte': inner_value_field_properties,
                    'lte': inner_value_field_properties
                }
            }
        elif internal_data_type == const.DATA_TYPE_COMPLEX:
            value_field_properties = {}
            for inner_attribute in attribute.attributes.all():
                value_field_properties.update(
                    ElasticsearchDB._get_elasticsearch_field_mapping_properties(inner_attribute)[1])

        if internal_data_type != const.DATA_TYPE_COMPLEX:
            properties = {
                inner_field_name: value_field_properties
            }
        else:
            properties = value_field_properties

        if internal_data_type == const.DATA_TYPE_STRING:
            properties.update({
                inner_field_name + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                    'analyzer': 'keyword_lowercase_hr_diacritics'
                }
            })
        elif internal_data_type == const.DATA_TYPE_CODEBOOK:
            properties.update({
                inner_field_name + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                }
            })
        elif internal_data_type == const.DATA_TYPE_FIXED_POINT or internal_data_type == const.DATA_TYPE_RANGE_FIXED_POINT:
            properties.update({
                'currency': {
                    'properties': {
                        'code': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'sign': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'sign_before_value': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                        }
                    }
                }
            })

        properties.update({
            'collections': {
                'type': const.DATA_TYPE_ELASTICSEARCH_NESTED,
                'dynamic': 'false',
                'properties': {
                    'valid_from': {
                        'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE]
                    },
                    'valid_to': {
                        'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE]
                    },
                    'collection': {
                        'properties': {
                            'string_id': {
                                'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                            },
                            'name': {
                                'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                            },
                            'source': {
                                'properties': {
                                    'string_id': {
                                        'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                    },
                                    'name': {
                                        'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })

        if internal_data_type == const.DATA_TYPE_COMPLEX or internal_data_type == const.DATA_TYPE_FIXED_POINT or internal_data_type == const.DATA_TYPE_RANGE_FIXED_POINT:
            ret = {
                field_name: {
                    'type': const.DATA_TYPE_ELASTICSEARCH_NESTED,
                    'dynamic': 'false',
                    'properties': properties
                }
            }
        else:
            ret = {
                field_name: {
                    'properties': properties
                }
            }

        return field_name, ret

    @staticmethod
    def _get_elasticsearch_attribute_value_to_index(entity, entity_entity, attribute):
        ret = {}

        inner_field_name = const.ELASTICSEARCH_VALUE_FIELD_NAME
        field_name = attribute.string_id

        attribute_type = attribute.attribute_type
        data_type = attribute_type.data_type.string_id

        if data_type not in const.DATA_TYPE_MAPPING_COMPLEX or const.DATA_TYPE_MAPPING_COMPLEX[
            data_type] != const.DATA_TYPE_COMPLEX:
            attribute_values = []
            if entity is not None:
                attribute_values = attribute.attribute_values.filter(Q(entity=entity) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True)))
            elif entity_entity is not None:
                attribute_values = attribute.attribute_values.filter(Q(entity_entity=entity_entity) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True)))
            for attribute_value in attribute_values:
                attribute_value_collections = attribute_value.attribute_value_collections.filter(deleted=False,
                                                                                                 published=True,
                                                                                                 collection__deleted=False,
                                                                                                 collection__published=True,
                                                                                                 collection__source__deleted=False,
                                                                                                 collection__source__published=True)
                if attribute_value_collections.exists():
                    value = None
                    if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
                        if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                            value = {
                                inner_field_name: attribute_value.get_raw_first_value(),
                                inner_field_name + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: attribute_value.get_raw_first_value()
                            }

                        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                            raw_value = attribute_value.get_raw_first_value()
                            value = {}
                            if raw_value is not None:
                                value = {
                                    inner_field_name: raw_value / helpers.get_divider(
                                        attribute_type)}
                            if attribute_value.currency is not None:
                                currency = attribute_value.currency
                                value.update({
                                    'currency': {
                                        'code': currency.code,
                                        'sign': currency.sign,
                                        'sign_before_value': currency.sign_before_value
                                    }
                                })
                        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                            value = {
                                inner_field_name: attribute_value.get_raw_first_value().value,
                                inner_field_name + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: attribute_value.get_raw_first_value().id
                            }
                        else:
                            value = {inner_field_name: attribute_value.get_raw_first_value()}
                    elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
                        if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                            value = {inner_field_name: {
                                'lat': attribute_value.get_raw_first_value(),
                                'lon': attribute_value.get_raw_second_value()
                            }}
                        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                            divider = helpers.get_divider(attribute_type)
                            value_from = attribute_value.get_raw_first_value()
                            if value_from is not None:
                                value_from = value_from / divider
                            value_to = attribute_value.get_raw_second_value()
                            if value_to is not None:
                                value_to = value_to / divider
                            value = {}
                            inner_value = {}
                            if value_from is not None:
                                inner_value.update({'gte': value_from})
                            if value_to is not None:
                                inner_value.update({'lte': value_to})

                            if value_from is not None or value_to is not None:
                                value.update({inner_field_name: inner_value})

                            if attribute_value.currency is not None:
                                currency = attribute_value.currency
                                value.update({
                                    'currency': {
                                        'code': currency.code,
                                        'sign': currency.sign,
                                        'sign_before_value': currency.sign_before_value
                                    }
                                })
                        else:
                            value = {
                                inner_field_name: {
                                    'gte': attribute_value.get_raw_first_value(),
                                    'lte': attribute_value.get_raw_second_value(),
                                }
                            }

                    if value is not None:
                        collection_values = []
                        for attribute_value_collection in attribute_value_collections:
                            collection_values.append({
                                'valid_from': attribute_value_collection.valid_from,
                                'valid_to': attribute_value_collection.valid_to,
                                'collection': {
                                    'string_id': attribute_value_collection.collection.string_id,
                                    'name': attribute_value_collection.collection.name,
                                    'source': {
                                        'string_id': attribute_value_collection.collection.source.string_id,
                                        'name': attribute_value_collection.collection.source.name,
                                    }
                                }
                            })

                        value.update({
                            'collections': collection_values
                        })

                        if field_name in ret and ret[field_name] is not None:
                            values = ret[field_name] + [value]
                        else:
                            values = [value]

                        ret.update({
                            field_name: values
                        })
                    else:
                        if field_name not in ret:
                            ret.update({
                                field_name: None
                            })
                else:
                    if field_name not in ret:
                        ret.update({
                            field_name: None
                        })
        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_COMPLEX:
            value = {}
            for inner_attribute in attribute.attributes.filter(finally_deleted=False, finally_published=True):
                if entity is not None:
                    value.update(
                        ElasticsearchDB._get_elasticsearch_attribute_value_to_index(entity=entity, entity_entity=None,
                                                                                    attribute=inner_attribute))
                elif entity_entity is not None:
                    value.update(
                        ElasticsearchDB._get_elasticsearch_attribute_value_to_index(entity=None,
                                                                                    entity_entity=entity_entity,
                                                                                    attribute=inner_attribute))

            if value != {}:
                if field_name in ret and ret[field_name] is not None:
                    values = ret[field_name] + [value]
                else:
                    values = [value]

                ret.update({
                    field_name: values
                })

        return ret

    @staticmethod
    def _get_search_field_to_index(entity):
        ret = {}
        for attribute_value in entity.attribute_values.filter(Q(attribute_value_collections__deleted=False,
                                                                attribute_value_collections__published=True,
                                                                attribute_value_collections__collection__deleted=False,
                                                                attribute_value_collections__collection__published=True,
                                                                attribute_value_collections__collection__source__deleted=False,
                                                                attribute_value_collections__collection__source__published=True,
                                                                attribute__finally_deleted=False,
                                                                attribute__finally_published=True,
                                                                attribute__string_id__in=const.SEARCH_ATTRIBUTES
                                                                ) & (
                                                                      Q(value_codebook_item=None) | Q(
                                                                  value_codebook_item__deleted=False,
                                                                  value_codebook_item__published=True))).distinct():
            search_attribute_value = attribute_value.get_raw_value()
            if search_attribute_value is not None:
                if attribute_value.attribute.attribute_type.data_type.string_id == 'codebook':
                    search_attribute_value = search_attribute_value.value

                search_value = search_attribute_value

                if const.ELASTICSEARCH_SEARCH_FIELD_NAME in ret and ret[
                    const.ELASTICSEARCH_SEARCH_FIELD_NAME] is not None:
                    search_values = ret[const.ELASTICSEARCH_SEARCH_FIELD_NAME] + [search_value]
                else:
                    search_values = [search_value]

                ret.update({
                    const.ELASTICSEARCH_SEARCH_FIELD_NAME: search_values
                })
        return ret

    @staticmethod
    def _get_queue():
        return django_rq.get_queue('elasticsearch', default_timeout='300m')

    @staticmethod
    def _get_elasticsearch_entity_to_index(entity):
        ret = {
            'entity_type': {
                'string_id': entity.entity_type.string_id,
                'name': entity.entity_type.name
            },
            'published': entity.published,
            'deleted': entity.deleted,
        }
        is_pep = BaseDatabase._is_pep(entity)
        if entity.entity_type.string_id == 'person':
            ret.update({
                'is_pep': is_pep
            })

        processed_attributes = set()
        for attribute in models.StageAttribute.objects.filter(
                Q(attribute_values__entity=entity, finally_deleted=False, finally_published=True) & (
                        Q(attribute_values__value_codebook_item=None) | Q(
                    attribute_values__value_codebook_item__deleted=False,
                    attribute_values__value_codebook_item__published=True,
                    attribute_values__value_codebook_item__codebook__deleted=False,
                    attribute_values__value_codebook_item__codebook__published=True))).distinct():
            root_attribute = helpers.get_root_attribute(attribute)
            if root_attribute not in processed_attributes:
                processed_attributes.add(root_attribute)
                ret.update(
                    ElasticsearchDB._get_elasticsearch_attribute_value_to_index(entity=entity, entity_entity=None,
                                                                                attribute=root_attribute))

        ret.update(ElasticsearchDB._get_search_field_to_index(entity))
        return ret

    @staticmethod
    def _get_elasticsearch_attribute_to_index(attribute):
        ret = {
            'name': attribute.name,
            'order_number': attribute.order_number,
        }
        if attribute.attribute is None:
            if attribute.entity_type is not None:
                ret.update({
                    'entity_type': {
                        'string_id': attribute.entity_type.string_id,
                        'name': attribute.entity_type.name
                    }
                })
            elif attribute.collection is not None:
                ret.update({
                    'collection': {
                        'string_id': attribute.collection.string_id,
                        'name': attribute.collection.name,
                        'source': {
                            'string_id': attribute.collection.source.string_id,
                            'name': attribute.collection.source.name,
                        }
                    }
                })
            ret.update({
                'published': attribute.finally_published,
                'deleted': attribute.finally_deleted
            })
        else:
            ret.update({
                'string_id': attribute.string_id
            })

        attribute_type = {
            'string_id': attribute.attribute_type.string_id,
            'name': attribute.attribute_type.name,
            'data_type': {
                'string_id': attribute.attribute_type.data_type.string_id,
                'name': attribute.attribute_type.data_type.name,
            },
            'fixed_point_decimal_places': attribute.attribute_type.fixed_point_decimal_places,
            'range_floating_point_from_inclusive': attribute.attribute_type.range_floating_point_from_inclusive,
            'range_floating_point_to_inclusive': attribute.attribute_type.range_floating_point_to_inclusive,
            'values_separator': helpers.get_values_separator(attribute.attribute_type),
            'input_formats': helpers.get_input_formats(attribute.attribute_type),
        }
        codebook = None
        if attribute.attribute_type.codebook is not None:
            codebook = {
                'string_id': attribute.attribute_type.codebook.string_id,
                'name': attribute.attribute_type.codebook.name
            }
        attribute_type.update({
            'codebook': codebook
        })
        ret.update({
            'attribute_type': attribute_type
        })

        attributes = []
        for inner_attribute in attribute.attributes.filter(finally_deleted=False, finally_published=True):
            inner_attribute_mapping = ElasticsearchDB._get_elasticsearch_attribute_to_index(attribute=inner_attribute)
            attributes.append(inner_attribute_mapping)
        if len(attributes) > 0:
            ret.update({
                'attributes': attributes
            })
        return ret

    @staticmethod
    def _get_elasticsearch_connection_type_to_index(connection_type):
        ret = {
            'name': connection_type.name,
            'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: connection_type.name,
            'reverse_name': connection_type.reverse_name,
            'reverse_name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: connection_type.reverse_name,
            const.ELASTICSEARCH_SEARCH_FIELD_NAME: [
                connection_type.name,
                connection_type.reverse_name
            ],
            'connection_type_category': {
                'string_id': connection_type.category.string_id,
                'name': connection_type.category.name,
            }
        }
        return ret

    @staticmethod
    def _get_elasticsearch_attribute_value_change_to_index(attribute_value_change):
        deleted = attribute_value_change.deleted or \
                  attribute_value_change.attribute.finally_deleted or \
                  attribute_value_change.changeset.deleted or \
                  attribute_value_change.changeset.collection.deleted or \
                  attribute_value_change.changeset.collection.source.deleted or (
                          attribute_value_change.entity is not None and attribute_value_change.entity.deleted) or (
                          attribute_value_change.entity_entity is not None and (
                          attribute_value_change.entity_entity.deleted or
                          attribute_value_change.entity_entity.entity_a.deleted or
                          attribute_value_change.entity_entity.entity_b.deleted)) or (
                          attribute_value_change.old_value_codebook_item is not None and (
                          attribute_value_change.old_value_codebook_item.deleted or
                          attribute_value_change.old_value_codebook_item.codebook.deleted)) or (
                          attribute_value_change.new_value_codebook_item is not None and (
                          attribute_value_change.new_value_codebook_item.deleted or
                          attribute_value_change.new_value_codebook_item.codebook.deleted))
        if not deleted and attribute_value_change.entity_entity is not None:
            deleted = not attribute_value_change.entity_entity.entity_entity_collections.filter(deleted=False,
                                                                                                collection__deleted=False,
                                                                                                collection__source__deleted=False).exists()
        published = attribute_value_change.published and \
                    attribute_value_change.attribute.finally_published and \
                    attribute_value_change.changeset.published and \
                    attribute_value_change.changeset.collection.published and \
                    attribute_value_change.changeset.collection.source.published and (
                            attribute_value_change.entity is None or attribute_value_change.entity.published) and (
                            attribute_value_change.entity_entity is None or (
                            attribute_value_change.entity_entity.published and
                            attribute_value_change.entity_entity.entity_a.published and
                            attribute_value_change.entity_entity.entity_b.published)) and (
                            attribute_value_change.old_value_codebook_item is None or (
                            attribute_value_change.old_value_codebook_item.published and
                            attribute_value_change.old_value_codebook_item.codebook.published)) and (
                            attribute_value_change.new_value_codebook_item is None or (
                            attribute_value_change.new_value_codebook_item.published and
                            attribute_value_change.new_value_codebook_item.codebook.published))
        if published and attribute_value_change.entity_entity is not None:
            published = attribute_value_change.entity_entity.entity_entity_collections.filter(published=True,
                                                                                              collection__published=True,
                                                                                              collection__source__published=True).exists()
        ret = {
            'change_type': {
                'string_id': attribute_value_change.change_type.string_id,
                'name': attribute_value_change.change_type.name
            },
            'created_at': attribute_value_change.changeset.created_at,
            'collection': {
                'string_id': attribute_value_change.changeset.collection.string_id,
                'name': attribute_value_change.changeset.collection.name,
                'description': attribute_value_change.changeset.collection.description,
                'quality': attribute_value_change.changeset.collection.quality,
                'collection_type': {
                    'string_id': attribute_value_change.changeset.collection.collection_type.string_id,
                    'name': attribute_value_change.changeset.collection.collection_type.name
                },
                'source': {
                    'string_id': attribute_value_change.changeset.collection.source.string_id,
                    'name': attribute_value_change.changeset.collection.source.name,
                    'description': attribute_value_change.changeset.collection.source.description,
                    'quality': attribute_value_change.changeset.collection.source.quality,
                    'source_type': {
                        'string_id': attribute_value_change.changeset.collection.source.source_type.string_id,
                        'name': attribute_value_change.changeset.collection.source.source_type.name
                    }
                }
            },
            'published': published,
            'deleted': deleted
        }
        if attribute_value_change.entity is not None:
            ret.update({
                'entity_public_id-attribute_string_id': attribute_value_change.entity.public_id + '#' + attribute_value_change.attribute.string_id,
                'entity': {
                    'public_id': attribute_value_change.entity.public_id
                }
            })
        elif attribute_value_change.entity_entity is not None:
            ret.update({
                'connection_id-attribute_string_id': str(
                    attribute_value_change.entity_entity.id) + '#' + attribute_value_change.attribute.string_id,
                'connection': {
                    'id': attribute_value_change.entity_entity.id
                }
            })
        attribute = {
            'string_id': attribute_value_change.attribute.string_id,
            'name': attribute_value_change.attribute.name,
            'order_number': attribute_value_change.attribute.order_number,
        }
        attribute_type = {
            'string_id': attribute_value_change.attribute.attribute_type.string_id,
            'name': attribute_value_change.attribute.attribute_type.name,
            'fixed_point_decimal_places': attribute_value_change.attribute.attribute_type.fixed_point_decimal_places,
            'range_floating_point_from_inclusive': attribute_value_change.attribute.attribute_type.range_floating_point_from_inclusive,
            'range_floating_point_to_inclusive': attribute_value_change.attribute.attribute_type.range_floating_point_to_inclusive,
            'data_type': {
                'string_id': attribute_value_change.attribute.attribute_type.data_type.string_id,
                'name': attribute_value_change.attribute.attribute_type.data_type.name
            },
            'values_separator': helpers.get_values_separator(attribute_value_change.attribute.attribute_type),
            'input_formats': helpers.get_input_formats(attribute_value_change.attribute.attribute_type),
        }
        if attribute_value_change.attribute.attribute_type.codebook is not None:
            attribute_type.update({
                'codebook': {
                    'string_id': attribute_value_change.attribute.attribute_type.codebook.string_id,
                    'name': attribute_value_change.attribute.attribute_type.codebook.name
                }
            })
        attribute.update({
            'attribute_type': attribute_type
        })
        root_attribute = helpers.get_root_attribute(attribute_value_change.attribute)
        if root_attribute.entity_type is not None:
            attribute.update({
                'entity_type': {
                    'string_id': root_attribute.entity_type.string_id,
                    'name': root_attribute.entity_type.name
                }
            })
        elif root_attribute.collection is not None:
            attribute.update({
                'collection': {
                    'string_id': root_attribute.collection.string_id,
                    'name': root_attribute.collection.name,
                    'collection_type': {
                        'string_id': root_attribute.collection.collection_type.string_id,
                        'name': root_attribute.collection.collection_type.name
                    },
                    'source': {
                        'string_id': root_attribute.collection.source.string_id,
                        'name': root_attribute.collection.source.name,
                        'source_type': {
                            'string_id': root_attribute.collection.source.source_type.string_id,
                            'name': root_attribute.collection.source.source_type.name
                        }
                    }
                }
            })
        ret.update({
            'attribute': attribute
        })

        ret.update({
            'old_valid_from': attribute_value_change.old_valid_from,
            'old_valid_to': attribute_value_change.old_valid_to,
            'new_valid_from': attribute_value_change.new_valid_from,
            'new_valid_to': attribute_value_change.new_valid_to
        })
        if attribute_value_change.old_currency is not None:
            ret.update({
                'old_currency': {
                    'code': attribute_value_change.old_currency.code,
                    'sign': attribute_value_change.old_currency.sign,
                    'sign_before_value': attribute_value_change.old_currency.sign_before_value
                }
            })
        else:
            ret.update({
                'old_currency': None
            })
        if attribute_value_change.new_currency is not None:
            ret.update({
                'new_currency': {
                    'code': attribute_value_change.new_currency.code,
                    'sign': attribute_value_change.new_currency.sign,
                    'sign_before_value': attribute_value_change.new_currency.sign_before_value
                }
            })
        else:
            ret.update({
                'old_currency': None
            })
        data_type = attribute_value_change.attribute.attribute_type.data_type.string_id

        if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
            if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                ret.update({
                    'old_value_boolean': attribute_value_change.old_value_boolean,
                    'new_value_boolean': attribute_value_change.new_value_boolean
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                ret.update({
                    'old_value_int': attribute_value_change.old_value_int,
                    'new_value_int': attribute_value_change.new_value_int
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                ret.update({
                    'old_value_fixed_point': attribute_value_change.old_value_fixed_point,
                    'new_value_fixed_point': attribute_value_change.new_value_fixed_point
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                ret.update({
                    'old_value_floating_point': attribute_value_change.old_value_floating_point,
                    'new_value_floating_point': attribute_value_change.new_value_floating_point
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                ret.update({
                    'old_value_string': attribute_value_change.old_value_string,
                    'new_value_string': attribute_value_change.new_value_string
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                ret.update({
                    'old_value_text': attribute_value_change.old_value_text,
                    'new_value_text': attribute_value_change.new_value_text
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                ret.update({
                    'old_value_datetime': attribute_value_change.old_value_datetime,
                    'new_value_datetime': attribute_value_change.new_value_datetime
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                ret.update({
                    'old_value_date': attribute_value_change.old_value_date,
                    'new_value_date': attribute_value_change.new_value_date
                })
            elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                if attribute_value_change.old_value_codebook_item is not None:
                    ret.update({
                        'old_value_codebook_item': {
                            'id': attribute_value_change.old_value_codebook_item.id,
                            const.ELASTICSEARCH_VALUE_FIELD_NAME: attribute_value_change.old_value_codebook_item.value
                        }
                    })
                else:
                    ret.update({
                        'old_value_codebook_item': None
                    })
                if attribute_value_change.new_value_codebook_item is not None:
                    ret.update({
                        'new_value_codebook_item': {
                            'id': attribute_value_change.new_value_codebook_item.id,
                            const.ELASTICSEARCH_VALUE_FIELD_NAME: attribute_value_change.new_value_codebook_item.value
                        }
                    })
                else:
                    ret.update({
                        'new_value_codebook_item': None
                    })
        elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
            if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                if attribute_value_change.old_value_geo_lat is None or attribute_value_change.old_value_geo_lon is None:
                    ret.update({
                        'old_value_geo': None
                    })
                else:
                    ret.update({
                        'old_value_geo': {
                            'lat': attribute_value_change.old_value_geo_lat,
                            'lon': attribute_value_change.old_value_geo_lon
                        }
                    })
                ret.update({
                    'new_value_geo': {
                        'lat': attribute_value_change.new_value_geo_lat,
                        'lon': attribute_value_change.new_value_geo_lon
                    }
                })
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                ret.update({
                    'old_value_range_int': {
                        'gte': attribute_value_change.old_value_range_int_from,
                        'lte': attribute_value_change.old_value_range_int_to
                    },
                    'new_value_range_int': {
                        'gte': attribute_value_change.new_value_range_int_from,
                        'lte': attribute_value_change.new_value_range_int_to
                    }
                })
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                ret.update({
                    'old_value_range_fixed_point': {
                        'gte': attribute_value_change.old_value_range_fixed_point_from,
                        'lte': attribute_value_change.old_value_range_fixed_point_to
                    },
                    'new_value_range_fixed_point': {
                        'gte': attribute_value_change.new_value_range_fixed_point_from,
                        'lte': attribute_value_change.new_value_range_fixed_point_to
                    }
                })
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                ret.update({
                    'old_value_range_floating_point': {
                        'gte': attribute_value_change.old_value_range_floating_point_from,
                        'lte': attribute_value_change.old_value_range_floating_point_to
                    },
                    'new_value_range_floating_point': {
                        'gte': attribute_value_change.new_value_range_floating_point_from,
                        'lte': attribute_value_change.new_value_range_floating_point_to
                    }
                })
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                ret.update({
                    'old_value_range_datetime': {
                        'gte': attribute_value_change.old_value_range_datetime_from,
                        'lte': attribute_value_change.old_value_range_datetime_to
                    },
                    'new_value_range_datetime': {
                        'gte': attribute_value_change.new_value_range_datetime_from,
                        'lte': attribute_value_change.new_value_range_datetime_to
                    }
                })
            elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                ret.update({
                    'old_value_range_date': {
                        'gte': attribute_value_change.old_value_range_date_from,
                        'lte': attribute_value_change.old_value_range_date_to
                    },
                    'new_value_range_date': {
                        'gte': attribute_value_change.new_value_range_date_from,
                        'lte': attribute_value_change.new_value_range_date_to
                    }
                })

        return ret

    @staticmethod
    def _get_elasticsearch_entity_entity_change_to_index(entity_entity_change):
        deleted = entity_entity_change.deleted or \
                  entity_entity_change.changeset.deleted or \
                  entity_entity_change.changeset.collection.deleted or \
                  entity_entity_change.changeset.collection.source.deleted or \
                  entity_entity_change.entity_entity.deleted or \
                  entity_entity_change.entity_entity.entity_a.deleted or \
                  entity_entity_change.entity_entity.entity_b.deleted
        if not deleted:
            deleted = not entity_entity_change.entity_entity.entity_entity_collections.filter(deleted=False,
                                                                                              collection__deleted=False,
                                                                                              collection__source__deleted=False).exists()

        published = entity_entity_change.published and \
                    entity_entity_change.changeset.published and \
                    entity_entity_change.changeset.collection.published and \
                    entity_entity_change.changeset.collection.source.published and \
                    entity_entity_change.entity_entity.published and \
                    entity_entity_change.entity_entity.entity_a.published and \
                    entity_entity_change.entity_entity.entity_b.published
        if published:
            published = entity_entity_change.entity_entity.entity_entity_collections.filter(published=True,
                                                                                            collection__published=True,
                                                                                            collection__source__published=True).exists()

        ret = {
            'change_type': {
                'string_id': entity_entity_change.change_type.string_id,
                'name': entity_entity_change.change_type.name
            },
            'created_at': entity_entity_change.changeset.created_at,
            'collection': {
                'string_id': entity_entity_change.changeset.collection.string_id,
                'name': entity_entity_change.changeset.collection.name,
                'description': entity_entity_change.changeset.collection.description,
                'quality': entity_entity_change.changeset.collection.quality,
                'collection_type': {
                    'string_id': entity_entity_change.changeset.collection.collection_type.string_id,
                    'name': entity_entity_change.changeset.collection.collection_type.name
                },
                'source': {
                    'string_id': entity_entity_change.changeset.collection.source.string_id,
                    'name': entity_entity_change.changeset.collection.source.name,
                    'description': entity_entity_change.changeset.collection.source.description,
                    'quality': entity_entity_change.changeset.collection.source.quality,
                    'source_type': {
                        'string_id': entity_entity_change.changeset.collection.source.source_type.string_id,
                        'name': entity_entity_change.changeset.collection.source.source_type.name
                    }
                }
            },
            'connection': {
                'id': entity_entity_change.entity_entity.id
            },
            'published': published,
            'deleted': deleted,
            'old_valid_from': entity_entity_change.old_valid_from,
            'old_valid_to': entity_entity_change.old_valid_to,
            'new_valid_from': entity_entity_change.new_valid_from,
            'new_valid_to': entity_entity_change.new_valid_to
        }

        return ret

    @staticmethod
    def _get_elasticsearch_codebook_value_to_index(codebook_value):
        ret = {
            'name': codebook_value.value,
            'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: codebook_value.value,
            const.ELASTICSEARCH_SEARCH_FIELD_NAME: [
                codebook_value.value
            ],
            'deleted': codebook_value.deleted or codebook_value.codebook.deleted,
            'published': codebook_value.published and codebook_value.codebook.published,
            'codebook': {
                'string_id': codebook_value.codebook.string_id,
                'name': codebook_value.codebook.name,
            }
        }
        return ret

    @staticmethod
    def _get_elasticsearch_entity_connection_type_category_count_to_index(entity, count_deleted,
                                                                          entity_not_to_count=None,
                                                                          entity_entity_not_to_count=None):
        ret = {}
        for connection_type_category in models.StaticConnectionTypeCategory.objects.all():
            queryset = entity.reverse_connections.filter(
                connection_type__category=connection_type_category)
            if not count_deleted:
                queryset = queryset.filter(deleted=False, published=True, entity_a__deleted=False,
                                           entity_a__published=True, entity_b__deleted=False, entity_b__published=True,
                                           entity_entity_collections__deleted=False,
                                           entity_entity_collections__published=True,
                                           entity_entity_collections__collection__deleted=False,
                                           entity_entity_collections__collection__published=True,
                                           entity_entity_collections__collection__source__deleted=False,
                                           entity_entity_collections__collection__source__published=True)

            if entity_not_to_count is not None:
                queryset = queryset.filter(~Q(entity_b=entity_not_to_count))

            if entity_entity_not_to_count is not None:
                queryset = queryset.filter(~Q(pk=entity_entity_not_to_count.pk))

            queryset = queryset.distinct()

            count_1 = queryset.count()

            queryset = entity.connections.filter(
                connection_type__category=connection_type_category)
            if not count_deleted:
                queryset = queryset.filter(deleted=False, published=True, entity_a__deleted=False,
                                           entity_a__published=True, entity_b__deleted=False, entity_b__published=True,
                                           entity_entity_collections__deleted=False,
                                           entity_entity_collections__published=True,
                                           entity_entity_collections__collection__deleted=False,
                                           entity_entity_collections__collection__published=True,
                                           entity_entity_collections__collection__source__deleted=False,
                                           entity_entity_collections__collection__source__published=True)

            if entity_not_to_count is not None:
                queryset = queryset.filter(~Q(entity_a=entity_not_to_count))

            if entity_entity_not_to_count is not None:
                queryset = queryset.filter(~Q(pk=entity_entity_not_to_count.pk))

            queryset = queryset.distinct()

            count_2 = queryset.count()

            ret.update({
                const.ELASTICSEARCH_CONNECTION_TYPE_CATEGORY_COUNT_FIELD_PREFIX + connection_type_category.string_id: count_1 + count_2
            })

        return ret

    @staticmethod
    def _get_elasticsearch_connection_to_index(entity_entity):
        entity_a_first_name = ''
        entity_a_second_name = ''
        entity_a_name = ''
        entity_a_legal_entity_entity_type = None
        for attribute_value in entity_entity.entity_a.attribute_values.filter(
                Q(attribute__finally_deleted=False, attribute__finally_published=True,
                  attribute_value_collections__deleted=False,
                  attribute_value_collections__published=True,
                  attribute_value_collections__collection__deleted=False,
                  attribute_value_collections__collection__published=True,
                  attribute_value_collections__collection__source__deleted=False,
                  attribute_value_collections__collection__source__published=True
                  ) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True,
                                                        value_codebook_item__codebook__deleted=False,
                                                        value_codebook_item__codebook__published=True)) & (
                        Q(attribute__string_id='person_first_name') | Q(attribute__string_id='person_last_name') | Q(
                    attribute__string_id='legal_entity_name') | Q(attribute__string_id='legal_entity_entity_type') | Q(
                    attribute__string_id='real_estate_name') | Q(attribute__string_id='movable_name') | Q(
                    attribute__string_id='savings_name'))).distinct():
            if attribute_value.attribute.string_id == 'person_first_name':
                entity_a_first_name = entity_a_first_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'person_last_name':
                entity_a_second_name = entity_a_second_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'legal_entity_name':
                entity_a_name = entity_a_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'legal_entity_entity_type':
                value = {
                    const.ELASTICSEARCH_VALUE_FIELD_NAME: attribute_value.get_raw_first_value().value,
                    const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: attribute_value.get_raw_first_value().id
                }
                if entity_a_legal_entity_entity_type is not None:
                    entity_a_legal_entity_entity_type = entity_a_legal_entity_entity_type + [value]
                else:
                    entity_a_legal_entity_entity_type = [value]
            elif attribute_value.attribute.string_id == 'real_estate_name':
                entity_a_name = entity_a_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'movable_name':
                entity_a_name = entity_a_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'savings_name':
                entity_a_name = entity_a_name + ' ' + attribute_value.get_raw_first_value()
        if entity_a_name == '':
            entity_a_name = entity_a_first_name.strip() + ' ' + entity_a_second_name.strip()
        entity_a_name = entity_a_name.strip()

        entity_b_first_name = ''
        entity_b_second_name = ''
        entity_b_name = ''
        entity_b_legal_entity_entity_type = None
        for attribute_value in entity_entity.entity_b.attribute_values.filter(
                Q(attribute__finally_deleted=False, attribute__finally_published=True,
                  attribute_value_collections__deleted=False,
                  attribute_value_collections__published=True,
                  attribute_value_collections__collection__deleted=False,
                  attribute_value_collections__collection__published=True,
                  attribute_value_collections__collection__source__deleted=False,
                  attribute_value_collections__collection__source__published=True
                  ) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True,
                                                        value_codebook_item__codebook__deleted=False,
                                                        value_codebook_item__codebook__published=True)) & (
                        Q(attribute__string_id='person_first_name') | Q(attribute__string_id='person_last_name') | Q(
                    attribute__string_id='legal_entity_name') | Q(attribute__string_id='legal_entity_entity_type') | Q(
                    attribute__string_id='real_estate_name') | Q(attribute__string_id='movable_name') | Q(
                    attribute__string_id='savings_name'))).distinct():
            if attribute_value.attribute.string_id == 'person_first_name':
                entity_b_first_name = entity_b_first_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'person_last_name':
                entity_b_second_name = entity_b_second_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'legal_entity_name':
                entity_b_name = entity_b_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'legal_entity_entity_type':
                value = {
                    const.ELASTICSEARCH_VALUE_FIELD_NAME: attribute_value.get_raw_first_value().value,
                    const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: attribute_value.get_raw_first_value().id
                }
                if entity_b_legal_entity_entity_type is not None:
                    entity_b_legal_entity_entity_type = entity_b_legal_entity_entity_type + [value]
                else:
                    entity_b_legal_entity_entity_type = [value]
            elif attribute_value.attribute.string_id == 'real_estate_name':
                entity_b_name = entity_b_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'movable_name':
                entity_b_name = entity_b_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'savings_name':
                entity_b_name = entity_b_name + ' ' + attribute_value.get_raw_first_value()
        if entity_b_name == '':
            entity_b_name = entity_b_first_name.strip() + ' ' + entity_b_second_name.strip()
        entity_b_name = entity_b_name.strip()

        ret = {
            'entity_a': {
                'public_id': entity_entity.entity_a.public_id,
                'is_pep': BaseDatabase._is_pep(entity_entity.entity_a),
                'name': entity_a_name,
                'entity_type': {
                    'string_id': entity_entity.entity_a.entity_type.string_id,
                    'name': entity_entity.entity_a.entity_type.name,
                },
                'legal_entity_type': entity_a_legal_entity_entity_type
            },
            'entity_b': {
                'public_id': entity_entity.entity_b.public_id,
                'is_pep': BaseDatabase._is_pep(entity_entity.entity_b),
                'name': entity_b_name,
                'entity_type': {
                    'string_id': entity_entity.entity_b.entity_type.string_id,
                    'name': entity_entity.entity_b.entity_type.name,
                },
                'legal_entity_type': entity_b_legal_entity_entity_type
            },
            'connection_type_category': {
                'string_id': entity_entity.connection_type.category.string_id,
                'name': entity_entity.connection_type.category.name
            },
            'connection_type': {
                'string_id': entity_entity.connection_type.string_id,
                'name': entity_entity.connection_type.name,
                'reverse_name': entity_entity.connection_type.reverse_name
            },
            'valid_from': entity_entity.valid_from,
            'valid_to': entity_entity.valid_to,
            'transaction_amount': entity_entity.transaction_amount,
            'transaction_date': entity_entity.transaction_date,
            'published': entity_entity.published and entity_entity.entity_a.published and entity_entity.entity_b.published and entity_entity.entity_entity_collections.filter(
                published=True, collection__published=True, collection__source__published=True).exists(),
            'deleted': entity_entity.deleted or entity_entity.entity_a.deleted or entity_entity.entity_b.deleted or not entity_entity.entity_entity_collections.filter(
                deleted=False, collection__deleted=False, collection__source__deleted=False).exists(),
        }
        if entity_entity.transaction_currency is not None:
            ret.update({
                'transaction_currency': {
                    'code': entity_entity.transaction_currency.code,
                    'sign': entity_entity.transaction_currency.sign,
                    'sign_before_value': entity_entity.transaction_currency.sign_before_value
                }
            })

        processed_attributes = set()
        for attribute in models.StageAttribute.objects.filter(
                Q(attribute_values__entity_entity=entity_entity, finally_deleted=False, finally_published=True) & (
                        Q(attribute_values__value_codebook_item=None) | Q(
                    attribute_values__value_codebook_item__deleted=False,
                    attribute_values__value_codebook_item__published=True,
                    attribute_values__value_codebook_item__codebook__deleted=False,
                    attribute_values__value_codebook_item__codebook__published=True))).distinct():
            root_attribute = helpers.get_root_attribute(attribute)
            if root_attribute not in processed_attributes:
                processed_attributes.add(root_attribute)
                ret.update(
                    ElasticsearchDB._get_elasticsearch_attribute_value_to_index(entity=None,
                                                                                entity_entity=entity_entity,
                                                                                attribute=root_attribute))

        return ret

    def get_elasticsearch(self):
        if self.elasticsearch is None:
            self.elasticsearch = Elasticsearch(ElasticsearchDB._get_elasticsearch_connection_strings(), timeout=30)
        return self.elasticsearch

    def q_init(self, command=None):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.init, command=command, ttl=-1)

    def init(self, command=None):
        if not ElasticsearchDB.is_elasticsearch_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Elasticsearch not configured'))
            return

        es = self.get_elasticsearch()

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
            ignore=[404])
        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITIES_INDEX_NAME) + ' deleted'))
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME) + ' deleted'))

        index_settings = {
            'settings': {
                'index.mapping.total_fields.limit': const.ELASTICSEARCH_TOTAL_FIELDS_LIMIT,
                'index.mapping.nested_fields.limit': const.ELASTICSEARCH_NESTED_FIELDS_LIMIT,
                'index.max_result_window': const.ELASTICSEARCH_MAX_RESULT_WINDOWS,
                'analysis': {
                    'analyzer': {
                        'standard_hr_diacritics': {
                            'type': 'custom',
                            'tokenizer': 'standard',
                            'filter': [
                                'standard',
                                'lowercase',
                                # 'stop'
                            ],
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        },
                        'keyword_lowercase_hr_diacritics': {
                            'type': 'custom',
                            'tokenizer': 'keyword',
                            'filter': [
                                'lowercase',
                            ],
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        },
                        'letter_edge_ngram_hr_diacritics': {
                            'type': 'custom',
                            'tokenizer': 'letter_edge_ngram',
                            'filter': [
                                'lowercase'
                            ],
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        },
                        'letter_edge_ngram_hr_diacritics_search': {
                            'type': 'custom',
                            'tokenizer': 'lowercase',
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        }
                    },
                    'char_filter': {
                        'hr_diacritics': {
                            'type': 'mapping',
                            'mappings': [
                                'č => c',
                                'ć => c',
                                'ž => z',
                                'š => s',
                                'đ => d',
                                'Č => C',
                                'Ć => C',
                                'Ž => Z',
                                'Š => S',
                                'Đ => D',
                            ]
                        }
                    },
                    'tokenizer': {
                        'letter_edge_ngram': {
                            'type': 'edge_ngram',
                            'min_gram': 1,
                            'max_gram': 1024,
                            'token_chars': [
                                'letter'
                            ]
                        }
                    }
                }
            }
        }

        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
            body=index_settings)
        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
            body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITIES_INDEX_NAME) + ' created'))
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME) + ' created'))

        entity_mappings = {
            'properties': {
                'entity_type': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                },
                const.ELASTICSEARCH_SEARCH_FIELD_NAME: {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                    'analyzer': 'letter_edge_ngram_hr_diacritics',
                    'search_analyzer': 'letter_edge_ngram_hr_diacritics_search'
                },
                'is_pep': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'published': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'deleted': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=entity_mappings)
        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=entity_mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('entity_type:string_id\tkeyword\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('entity_type:name\ttext\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('published\tboolean\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('deleted\tboolean\ttype mapped'))

        for connection_type_category in models.StaticConnectionTypeCategory.objects.all():
            field_name, mapping_properties = self.put_entity_connection_type_category_count_mapping(
                connection_type_category)
            if mapping_properties is not None:
                if command is not None:
                    command.stdout.write(command.style.SUCCESS(
                        field_name + '\t' + '\ttype mapped'))
            else:
                if command is not None:
                    command.stdout.write(command.style.WARNING(field_name + '\ttype not mapped'))

        for attribute in models.StageAttribute.objects.filter(~Q(entity_type=None)):
            field_name, mapping_properties = self.put_entity_attribute_mapping(attribute=attribute)
            if mapping_properties is not None:
                if command is not None:
                    command.stdout.write(command.style.SUCCESS(
                        field_name + '\t' + '\ttype mapped'))
            else:
                if command is not None:
                    command.stdout.write(command.style.WARNING(field_name + '\ttype not mapped'))

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
            ignore=[404])
        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME) + ' deleted'))
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME) + ' deleted'))

        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
            body=index_settings)
        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
            body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME) + ' created'))
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME) + ' created'))

        connection_mappings = {
            'properties': {
                'entity_a': {
                    'properties': {
                        'public_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'is_pep': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'entity_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                }
                            }
                        },
                        'legal_entity_type': {
                            'properties': {
                                const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                                },
                                const.ELASTICSEARCH_VALUE_FIELD_NAME: {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                }
                            }
                        }
                    }
                },
                'entity_b': {
                    'properties': {
                        'public_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'is_pep': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'entity_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                }
                            }
                        },
                        'legal_entity_type': {
                            'properties': {
                                const.ELASTICSEARCH_VALUE_FIELD_NAME + const.ELASTICSEARCH_CODEBOOK_ITEM_ID_FIELD_SUFIX: {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                                },
                                const.ELASTICSEARCH_VALUE_FIELD_NAME: {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                }
                            }
                        }
                    }
                },
                'connection_type_category': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                },
                'connection_type': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'reverse_name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                },
                'valid_from': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME]
                },
                'valid_to': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME]
                },
                'transaction_amount': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_FIXED_POINT],
                    'scaling_factor': 4
                },
                'transaction_currency': {
                    'properties': {
                        'code': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'sign': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'sign_before_value': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                        }
                    }
                },
                'transaction_date': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME]
                },
                'published': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'deleted': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=connection_mappings)
        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=connection_mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('entity_a:public_id\tkeyword\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('entity_a:is_pep\tboolean\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('entity_b:public_id\tkeyword\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('entity_b:is_pep\tboolean\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('connection_type_category:string_id\tkeyword\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('connection_type_category:name\ttext\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('connection_type:string_id\tkeyword\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('connection_type:name\ttext\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('connection_type:reverse_name\ttext\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('valid_from\tdate\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('valid_to\tdate\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('transaction_amount\tscaled_float\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('transaction_currency:code\tkeyword\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('transaction_currency:sign\ttext\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('transaction_currency:sign_before_value\tboolean\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('transaction_date\tdate\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('published\tboolean\ttype mapped'))
            command.stdout.write(command.style.SUCCESS('deleted\tboolean\ttype mapped'))

        for attribute in models.StageAttribute.objects.filter(~Q(collection=None) & Q(attribute=None)):
            field_name, mapping_properties = self.put_connection_attribute_mapping(attribute=attribute)
            if mapping_properties is not None:
                if command is not None:
                    command.stdout.write(command.style.SUCCESS(
                        field_name + '\t' + '\ttype mapped'))
            else:
                if command is not None:
                    command.stdout.write(command.style.WARNING(field_name + '\ttype not mapped'))

    def q_init_attributes(self, command=None):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.init_attributes, command=command, ttl=-1)

    def init_attributes(self, command=None):
        if not ElasticsearchDB.is_elasticsearch_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Elasticsearch not configured'))
            return

        es = self.get_elasticsearch()

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME) + ' deleted'))

        index_settings = {
            'settings': {
                'index.max_result_window': const.ELASTICSEARCH_MAX_RESULT_WINDOWS,
            }
        }

        es.indices.create(index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
                          body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME) + ' created'))

        mappings = {
            'properties': {
                'name': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                },
                'entity_type': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                },
                'collection': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'source': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                }
                            }
                        }
                    }
                },
                'attribute_type': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'data_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                            }
                        },
                        'codebook': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                            }
                        },
                        'fixed_point_decimal_places': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_SHORT,
                            'index': False
                        },
                        'range_floating_point_from_inclusive': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN],
                            'index': False
                        },
                        'range_floating_point_to_inclusive': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN],
                            'index': False
                        },
                        'values_separator': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                            'index': False
                        },
                        'input_formats': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                            'index': False
                        }
                    },
                },
                'order_number': {
                    'type': const.DATA_TYPE_ELASTICSEARCH_INTEGER,
                },
                'published': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'deleted': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                }
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('Fields mapped'))

    def q_init_connection_types(self, command=None):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.init_connection_types, command=command, ttl=-1)

    def init_connection_types(self, command=None):
        if not ElasticsearchDB.is_elasticsearch_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Elasticsearch not configured'))
            return

        es = self.get_elasticsearch()

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME) + ' deleted'))

        index_settings = {
            'settings': {
                'index.max_result_window': const.ELASTICSEARCH_MAX_RESULT_WINDOWS,
                'analysis': {
                    'analyzer': {
                        'letter_ngram_hr_diacritics': {
                            'type': 'custom',
                            'tokenizer': 'letter_ngram',
                            'filter': [
                                'lowercase'
                            ],
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        },
                        'letter_ngram_hr_diacritics_search': {
                            'type': 'custom',
                            'tokenizer': 'lowercase',
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        }
                    },
                    'char_filter': {
                        'hr_diacritics': {
                            'type': 'mapping',
                            'mappings': [
                                'č => c',
                                'ć => c',
                                'ž => z',
                                'š => s',
                                'đ => d',
                                'Č => C',
                                'Ć => C',
                                'Ž => Z',
                                'Š => S',
                                'Đ => D',
                            ]
                        }
                    },
                    'tokenizer': {
                        'letter_ngram': {
                            'type': 'ngram',
                            'min_gram': 1,
                            'max_gram': 1024,
                            'token_chars': [
                                'letter'
                            ]
                        }
                    }
                }
            }
        }

        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
            body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME) + ' created'))

        mappings = {
            'properties': {
                'name': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                },
                'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD,
                },
                'reverse_name': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                },
                'reverse_name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD,
                },
                const.ELASTICSEARCH_SEARCH_FIELD_NAME: {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                    'analyzer': 'letter_ngram_hr_diacritics',
                    'search_analyzer': 'letter_ngram_hr_diacritics_search'
                },
                'connection_type_category': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                }
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('Fields mapped'))

    def q_init_attribute_values_log(self, command=None):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.init_attribute_values_log, command=command, ttl=-1)

    def init_attribute_values_log(self, command=None):
        if not ElasticsearchDB.is_elasticsearch_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Elasticsearch not configured'))
            return

        es = self.get_elasticsearch()

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME) + ' deleted'))

        index_settings = {
            'settings': {
                'index.max_result_window': const.ELASTICSEARCH_MAX_RESULT_WINDOWS,
            }
        }

        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
            body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME) + ' created'))

        mappings = {
            'properties': {
                'entity_public_id-attribute_string_id': {
                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                },
                'connection_id-attribute_string_id': {
                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                },
                'change_type': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                },
                'created_at': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME],
                    'format': 'date_time||date_time_no_millis'
                },
                'collection': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'description': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_TEXT]
                        },
                        'quality': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_SHORT
                        },
                        'collection_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                            }
                        },
                        'source': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                                'description': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_TEXT]
                                },
                                'quality': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_SHORT
                                },
                                'source_type': {
                                    'properties': {
                                        'string_id': {
                                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                        },
                                        'name': {
                                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                        },
                                    }
                                }
                            }
                        }
                    }
                },
                'attribute': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'entity_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                }
                            }
                        },
                        'collection': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                                'collection_type': {
                                    'properties': {
                                        'string_id': {
                                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                        },
                                        'name': {
                                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                        },
                                    }
                                },
                                'source': {
                                    'properties': {
                                        'string_id': {
                                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                        },
                                        'name': {
                                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                        },
                                        'source_type': {
                                            'properties': {
                                                'string_id': {
                                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                                },
                                                'name': {
                                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                                },
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        'attribute_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                                'data_type': {
                                    'properties': {
                                        'string_id': {
                                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                        },
                                        'name': {
                                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                        },
                                    }
                                },
                                'codebook': {
                                    'properties': {
                                        'string_id': {
                                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                        },
                                        'name': {
                                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                        },
                                    }
                                },
                                'fixed_point_decimal_places': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_SHORT,
                                    'index': False
                                },
                                'range_floating_point_from_inclusive': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN],
                                    'index': False
                                },
                                'range_floating_point_to_inclusive': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN],
                                    'index': False
                                },
                                'values_separator': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                                    'index': False
                                },
                                'input_formats': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                                    'index': False
                                }
                            },
                        },
                        'order_number': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_INTEGER,
                        }
                    }
                },
                'entity': {
                    'properties': {
                        'public_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        }
                    }
                },
                'connection': {
                    'properties': {
                        'id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        }
                    }
                },
                'published': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'deleted': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },

                'old_value_boolean': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'new_value_boolean': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'old_value_int': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                },
                'new_value_int': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                },
                'old_value_fixed_point': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                },
                'new_value_fixed_point': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                },
                'old_value_floating_point': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_FLOATING_POINT]
                },
                'new_value_floating_point': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_FLOATING_POINT]
                },
                'old_value_string': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                },
                'new_value_string': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                },
                'old_value_text': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_TEXT]
                },
                'new_value_text': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_TEXT]
                },
                'old_value_datetime': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME],
                    'format': 'date_time||date_time_no_millis||date'
                },
                'new_value_datetime': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME],
                    'format': 'date_time||date_time_no_millis||date'
                },
                'old_value_date': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'new_value_date': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'old_value_codebook_item': {
                    'properties': {
                        'id': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                        },
                        const.ELASTICSEARCH_VALUE_FIELD_NAME: {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_CODEBOOK]
                        }
                    }
                },
                'new_value_codebook_item': {
                    'properties': {
                        'id': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                        },
                        const.ELASTICSEARCH_VALUE_FIELD_NAME: {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_CODEBOOK]
                        }
                    }
                },
                'old_value_geo': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_GEO]
                },
                'new_value_geo': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_GEO]
                },
                'old_value_range_int': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_INT]
                },
                'new_value_range_int': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_INT]
                },
                'old_value_range_fixed_point': {
                    'properties': {
                        'gte': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                        },
                        'lte': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                        }
                    }
                },
                'new_value_range_fixed_point': {
                    'properties': {
                        'gte': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                        },
                        'lte': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                        }
                    }
                },
                'old_value_range_floating_point': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_FLOATING_POINT]
                },
                'new_value_range_floating_point': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_FLOATING_POINT]
                },
                'old_value_range_datetime': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_DATETIME],
                    'format': 'date_time||date_time_no_millis||date'
                },
                'new_value_range_datetime': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_DATETIME],
                    'format': 'date_time||date_time_no_millis||date'
                },
                'old_value_range_date': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_DATE],
                    'format': 'date'
                },
                'new_value_range_date': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_RANGE_DATE],
                    'format': 'date'
                },

                'old_valid_from': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'old_valid_to': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'new_valid_from': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'new_valid_to': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'old_currency': {
                    'properties': {
                        'code': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'sign': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'sign_before_value': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                        }
                    }
                },
                'new_currency': {
                    'properties': {
                        'code': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'sign': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'sign_before_value': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                        }
                    }
                }
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('Fields mapped'))

    def q_init_entity_entity_log(self, command=None):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.init_entity_entity_log, command=command, ttl=-1)

    def init_entity_entity_log(self, command=None):
        if not ElasticsearchDB.is_elasticsearch_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Elasticsearch not configured'))
            return

        es = self.get_elasticsearch()

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME) + ' deleted'))

        index_settings = {
            'settings': {
                'index.max_result_window': const.ELASTICSEARCH_MAX_RESULT_WINDOWS,
            }
        }

        es.indices.create(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
            body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME) + ' created'))

        mappings = {
            'properties': {
                'change_type': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        }
                    }
                },
                'created_at': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATETIME],
                    'format': 'date_time||date_time_no_millis'
                },
                'collection': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                        'description': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_TEXT]
                        },
                        'quality': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_SHORT
                        },
                        'collection_type': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                            }
                        },
                        'source': {
                            'properties': {
                                'string_id': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                },
                                'name': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                },
                                'description': {
                                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_TEXT]
                                },
                                'quality': {
                                    'type': const.DATA_TYPE_ELASTICSEARCH_SHORT
                                },
                                'source_type': {
                                    'properties': {
                                        'string_id': {
                                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                                        },
                                        'name': {
                                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                                        },
                                    }
                                }
                            }
                        }
                    }
                },
                'connection': {
                    'properties': {
                        'id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        }
                    }
                },
                'published': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'deleted': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'old_valid_from': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'old_valid_to': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'new_valid_from': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                },
                'new_valid_to': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_DATE],
                    'format': 'date'
                }
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('Fields mapped'))

    def q_init_codebook_values(self, command=None):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.init_codebook_values, command=command, ttl=-1)

    def init_codebook_values(self, command=None):
        if not ElasticsearchDB.is_elasticsearch_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Elasticsearch not configured'))
            return

        es = self.get_elasticsearch()

        es.indices.delete(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
            ignore=[404])

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME) + ' deleted'))

        index_settings = {
            'settings': {
                'index.max_result_window': const.ELASTICSEARCH_MAX_RESULT_WINDOWS,
                'analysis': {
                    'analyzer': {
                        'letter_ngram_hr_diacritics': {
                            'type': 'custom',
                            'tokenizer': 'letter_ngram',
                            'filter': [
                                'lowercase'
                            ],
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        },
                        'letter_ngram_hr_diacritics_search': {
                            'type': 'custom',
                            'tokenizer': 'lowercase',
                            'char_filter': [
                                'hr_diacritics'
                            ]
                        }
                    },
                    'char_filter': {
                        'hr_diacritics': {
                            'type': 'mapping',
                            'mappings': [
                                'č => c',
                                'ć => c',
                                'ž => z',
                                'š => s',
                                'đ => d',
                                'Č => C',
                                'Ć => C',
                                'Ž => Z',
                                'Š => S',
                                'Đ => D',
                            ]
                        }
                    },
                    'tokenizer': {
                        'letter_ngram': {
                            'type': 'ngram',
                            'min_gram': 1,
                            'max_gram': 1024,
                            'token_chars': [
                                'letter'
                            ]
                        }
                    }
                }
            }
        }

        es.indices.create(index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
                          body=index_settings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'Index ' + ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME) + ' created'))

        mappings = {
            'properties': {
                'name': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                },
                'name' + const.ELASTICSEARCH_EXACT_STRING_FIELD_SUFIX: {
                    'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD,
                },
                const.ELASTICSEARCH_SEARCH_FIELD_NAME: {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING],
                    'analyzer': 'letter_ngram_hr_diacritics',
                    'search_analyzer': 'letter_ngram_hr_diacritics_search'
                },
                'published': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'deleted': {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_BOOLEAN]
                },
                'codebook': {
                    'properties': {
                        'string_id': {
                            'type': const.DATA_TYPE_ELASTICSEARCH_KEYWORD
                        },
                        'name': {
                            'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_STRING]
                        },
                    }
                }
            }
        }

        es.indices.put_mapping(
            index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
            doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body=mappings)

        if command is not None:
            command.stdout.write(command.style.SUCCESS('Fields mapped'))

    def q_put_attribute_mapping(self, attribute):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.put_attribute_mapping, attribute=attribute, ttl=-1)

    def put_attribute_mapping(self, attribute):
        field_name = None
        mapping_properties = None
        if helpers.is_attribute_for_entity(attribute):
            field_name, mapping_properties = self.put_entity_attribute_mapping(attribute=attribute)
        elif helpers.is_attribute_for_connection(attribute):
            field_name, mapping_properties = self.put_connection_attribute_mapping(attribute=attribute)

        return field_name, mapping_properties

    def q_delete_attribute_mapping(self, attribute):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_attribute_mapping, attribute=attribute, ttl=-1)

    def delete_attribute_mapping(self, attribute):
        if helpers.is_attribute_for_entity(attribute):
            self.delete_entity_attribute_mapping(attribute=attribute)
        elif helpers.is_attribute_for_connection(attribute):
            self.delete_connection_attribute_mapping(attribute=attribute)

    def q_put_entity_attribute_mapping(self, attribute):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.put_entity_attribute_mapping, attribute=attribute, ttl=-1)

    def put_entity_attribute_mapping(self, attribute):
        field_name = None
        mapping_properties = None
        if ElasticsearchDB.is_elasticsearch_settings_exists() and helpers.is_attribute_for_entity(attribute):
            es = self.get_elasticsearch()
            attribute = helpers.get_root_attribute(attribute)
            field_name, mapping_properties = ElasticsearchDB._get_elasticsearch_field_mapping_properties(
                attribute=attribute)
            es.indices.put_mapping(
                index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body={'properties': mapping_properties})
            es.indices.put_mapping(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body={'properties': mapping_properties})
        return field_name, mapping_properties

    def q_delete_entity_attribute_mapping(self, attribute):
        pass

    def delete_entity_attribute_mapping(self, attribute):
        pass

    def q_put_connection_attribute_mapping(self, attribute):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.put_connection_attribute_mapping, attribute=attribute, ttl=-1)

    def put_connection_attribute_mapping(self, attribute):
        field_name = None
        mapping_properties = None
        if ElasticsearchDB.is_elasticsearch_settings_exists() and helpers.is_attribute_for_connection(attribute):
            es = self.get_elasticsearch()
            attribute = helpers.get_root_attribute(attribute)
            field_name, mapping_properties = ElasticsearchDB._get_elasticsearch_field_mapping_properties(
                attribute=attribute)
            es.indices.put_mapping(
                index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body={'properties': mapping_properties})
            es.indices.put_mapping(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body={'properties': mapping_properties})
        return field_name, mapping_properties

    def q_delete_connection_attribute_mapping(self, attribute):
        pass

    def delete_connection_attribute_mapping(self, attribute):
        pass

    def q_put_entity_connection_type_category_count_mapping(self, connection_type_category):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.put_entity_connection_type_category_count_mapping,
                      connection_type_category=connection_type_category, ttl=-1)

    def put_entity_connection_type_category_count_mapping(self, connection_type_category):
        mapping_properties = None
        if connection_type_category is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            mapping_properties = {
                const.ELASTICSEARCH_CONNECTION_TYPE_CATEGORY_COUNT_FIELD_PREFIX + connection_type_category.string_id: {
                    'type': const.DATA_TYPE_MAPPING_TO_ELASTIC[const.DATA_TYPE_INT]
                }
            }
            es.indices.put_mapping(
                index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body={'properties': mapping_properties})
            es.indices.put_mapping(
                index=ElasticsearchDB.get_elasticsearch_index_name(
                    const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), body={'properties': mapping_properties})
        return const.ELASTICSEARCH_CONNECTION_TYPE_CATEGORY_COUNT_FIELD_PREFIX + connection_type_category.string_id, mapping_properties

    def q_add_entity(self, entity, overwrite=False, add_connections=True):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_entity, entity=entity, overwrite=overwrite, add_connections=add_connections, ttl=-1)

    def add_entity(self, entity, overwrite=False, add_connections=True):
        if entity is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            body = None
            if entity.deleted or not entity.published:
                self.delete_entity(entity=entity, delete_all=False)
            else:
                if overwrite or not es.exists(
                        index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id):
                    body = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                    body.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                          count_deleted=False))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id,
                        body=body)

            if overwrite or not es.exists(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id):
                if body is None:
                    body = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                body.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                      count_deleted=True))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id,
                    body=body)

            if add_connections:
                for entity_entity in entity.reverse_connections.all():
                    self.add_connection(entity_entity=entity_entity, calculate_count=False, overwrite=overwrite)

                for entity_entity in entity.connections.all():
                    self.add_connection(entity_entity=entity_entity, calculate_count=False, overwrite=overwrite)

    def q_update_entity(self, entity, update_connections=True):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_entity, entity=entity, update_connections=update_connections, ttl=-1)

    def update_entity(self, entity, update_connections=True):
        self.add_entity(entity=entity, overwrite=True, add_connections=update_connections)

    def q_delete_entity(self, entity, delete_all=True):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_entity, entity=entity, delete_all=delete_all, ttl=-1)

    def delete_entity(self, entity, delete_all=True):
        if entity is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            try:
                es.delete(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id)
            except NotFoundError:
                pass

            if delete_all:
                try:
                    es.delete(index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id)
                except NotFoundError:
                    pass

            for entity_entity in entity.reverse_connections.all():
                entity_b = entity_entity.entity_b
                body = ElasticsearchDB._get_elasticsearch_entity_to_index(entity_b)
                body.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity_b,
                                                                                                      count_deleted=False,
                                                                                                      entity_not_to_count=entity))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_b.public_id,
                    body=body)

                if delete_all:
                    body.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity_b,
                                                                                                          count_deleted=True,
                                                                                                          entity_not_to_count=entity))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_b.public_id,
                        body=body)

                self.delete_connection(entity_entity=entity_entity, calculate_count=False, delete_all=delete_all)

            for entity_entity in entity.connections.all():
                entity_a = entity_entity.entity_a
                body = ElasticsearchDB._get_elasticsearch_entity_to_index(entity_a)
                body.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity_a,
                                                                                                      count_deleted=False,
                                                                                                      entity_not_to_count=entity))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_a.public_id,
                    body=body)

                if delete_all:
                    body.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity_a,
                                                                                                          count_deleted=True,
                                                                                                          entity_not_to_count=entity))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_a.public_id,
                        body=body)

                self.delete_connection(entity_entity=entity_entity, calculate_count=False, delete_all=delete_all)

    def q_add_connection(self, entity_entity, calculate_count=True, overwrite=False):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_connection, entity_entity=entity_entity, calculate_count=calculate_count,
                      overwrite=overwrite, ttl=-1)

    def add_connection(self, entity_entity, calculate_count=True, overwrite=False):
        if entity_entity is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            body_a = None
            body_b = None
            if entity_entity.deleted or not entity_entity.published or entity_entity.entity_a.deleted or not entity_entity.entity_a.published or entity_entity.entity_b.deleted or not entity_entity.entity_b.published or not entity_entity.entity_entity_collections.filter(
                    deleted=False, published=True, collection__deleted=False, collection__published=True,
                    collection__source__deleted=False, collection__source__published=True).exists():
                self.delete_connection(entity_entity=entity_entity, calculate_count=True, delete_all=False)
            else:
                if overwrite or not es.exists(
                        index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity.id):
                    body = ElasticsearchDB._get_elasticsearch_connection_to_index(entity_entity)
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity.id,
                        body=body)

                if calculate_count:
                    entity = entity_entity.entity_a
                    body_a = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                    body_a.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                          count_deleted=False))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id,
                        body=body_a)

                    entity = entity_entity.entity_b
                    body_b = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                    body_b.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                          count_deleted=False))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id,
                        body=body_b)

            if overwrite or not es.exists(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity.id):
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity.id,
                    body=ElasticsearchDB._get_elasticsearch_connection_to_index(entity_entity))

            if calculate_count:
                entity = entity_entity.entity_a
                if body_a is None:
                    body_a = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                body_a.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                      count_deleted=True))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id,
                    body=body_a)

                entity = entity_entity.entity_b
                if body_b is None:
                    body_b = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                body_b.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                      count_deleted=True))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id,
                    body=body_b)

    def q_update_connection(self, entity_entity, calculate_count=True):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_connection, entity_entity=entity_entity, calculate_count=calculate_count, ttl=-1)

    def update_connection(self, entity_entity, calculate_count=True):
        self.add_connection(entity_entity=entity_entity, calculate_count=calculate_count, overwrite=True)

    def q_delete_connection(self, entity_entity, calculate_count=True, delete_all=True):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_connection, entity_entity=entity_entity, calculate_count=calculate_count,
                      delete_all=delete_all, ttl=-1)

    def delete_connection(self, entity_entity, calculate_count=True, delete_all=True):
        if entity_entity is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            try:
                es.delete(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_CONNECTIONS_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity.id)
            except NotFoundError:
                pass

            if delete_all:
                try:
                    es.delete(index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ALL_CONNECTIONS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity.id)
                except NotFoundError:
                    pass

            if calculate_count:
                entity = entity_entity.entity_a
                body = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                body.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                      count_deleted=False,
                                                                                                      entity_entity_not_to_count=entity_entity))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id, body=body)

                if delete_all:
                    body.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                          count_deleted=True,
                                                                                                          entity_entity_not_to_count=entity_entity))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id, body=body)

                entity = entity_entity.entity_b
                body = ElasticsearchDB._get_elasticsearch_entity_to_index(entity)
                body.update(
                    ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                      count_deleted=False,
                                                                                                      entity_entity_not_to_count=entity_entity))
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ENTITIES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id, body=body)

                if delete_all:
                    body.update(
                        ElasticsearchDB._get_elasticsearch_entity_connection_type_category_count_to_index(entity=entity,
                                                                                                          count_deleted=True,
                                                                                                          entity_entity_not_to_count=entity_entity))
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ALL_ENTITIES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity.public_id, body=body)

    def q_add_attribute(self, attribute, overwrite=False):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_attribute, attribute=attribute, overwrite=overwrite, ttl=-1)

    def add_attribute(self, attribute, overwrite=False):
        if attribute is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            root_attribute = helpers.get_root_attribute(attribute)
            if root_attribute.finally_deleted or not root_attribute.finally_published:
                self.delete_attribute(attribute=root_attribute)
            elif overwrite or not es.exists(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=root_attribute.string_id):
                body = ElasticsearchDB._get_elasticsearch_attribute_to_index(attribute=root_attribute)
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=root_attribute.string_id,
                    body=body)

    def q_update_attribute(self, attribute):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_attribute, attribute=attribute, ttl=-1)

    def update_attribute(self, attribute):
        self.add_attribute(attribute=attribute, overwrite=True)

    def q_delete_attribute(self, attribute):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_attribute, attribute=attribute, ttl=-1)

    def delete_attribute(self, attribute):
        if attribute is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            if attribute.attribute is not None:
                self.update_attribute(attribute)
            else:
                es = self.get_elasticsearch()
                try:
                    es.delete(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ATTRIBUTES_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=attribute.string_id)
                except NotFoundError:
                    pass

    def q_add_connection_type(self, connection_type, overwrite=False):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_connection_type, connection_type=connection_type, overwrite=overwrite, ttl=-1)

    def add_connection_type(self, connection_type, overwrite=False):
        if connection_type is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            if overwrite or not es.exists(
                    index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=connection_type.string_id):
                body = ElasticsearchDB._get_elasticsearch_connection_type_to_index(connection_type=connection_type)
                es.index(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=connection_type.string_id,
                    body=body)

    def q_update_connection_type(self, connection_type):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_connection_type, connection_type=connection_type, ttl=-1)

    def update_connection_type(self, connection_type):
        self.add_connection_type(connection_type=connection_type, overwrite=True)

    def q_delete_connection_type(self, connection_type):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_connection_type, connection_type=connection_type, ttl=-1)

    def delete_connection_type(self, connection_type):
        if connection_type is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            try:
                es.delete(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_CONNECTION_TYPES_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=connection_type.string_id)
            except NotFoundError:
                pass

    def q_add_attribute_value_change(self, attribute_value_change, overwrite=False):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_attribute_value_change, attribute_value_change=attribute_value_change,
                      overwrite=overwrite, ttl=-1)

    def add_attribute_value_change(self, attribute_value_change, overwrite=False):
        if attribute_value_change is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            delete = attribute_value_change.deleted or not attribute_value_change.published or \
                     attribute_value_change.attribute.finally_deleted or not attribute_value_change.attribute.finally_published or \
                     attribute_value_change.changeset.deleted or not attribute_value_change.changeset.published or \
                     attribute_value_change.changeset.collection.deleted or not attribute_value_change.changeset.collection.published or \
                     attribute_value_change.changeset.collection.source.deleted or not attribute_value_change.changeset.collection.source.published or (
                             attribute_value_change.entity is not None and (
                             attribute_value_change.entity.deleted or not attribute_value_change.entity.published)) or (
                             attribute_value_change.entity_entity is not None and (
                             attribute_value_change.entity_entity.deleted or not attribute_value_change.entity_entity.published or
                             attribute_value_change.entity_entity.entity_a.deleted or not attribute_value_change.entity_entity.entity_a.published or
                             attribute_value_change.entity_entity.entity_b.deleted or not attribute_value_change.entity_entity.entity_b.published)) or (
                             attribute_value_change.old_value_codebook_item is not None and (
                             attribute_value_change.old_value_codebook_item.deleted or not attribute_value_change.old_value_codebook_item.published or
                             attribute_value_change.old_value_codebook_item.codebook.deleted or not attribute_value_change.old_value_codebook_item.codebook.published)) or (
                             attribute_value_change.new_value_codebook_item is not None and (
                             attribute_value_change.new_value_codebook_item.deleted or not attribute_value_change.new_value_codebook_item.published or
                             attribute_value_change.new_value_codebook_item.codebook.deleted or not attribute_value_change.new_value_codebook_item.codebook.published))
            if not delete and attribute_value_change.entity_entity is not None:
                delete = not attribute_value_change.entity_entity.entity_entity_collections.filter(deleted=False,
                                                                                                   published=True,
                                                                                                   collection__deleted=False,
                                                                                                   collection__published=True,
                                                                                                   collection__source__deleted=False,
                                                                                                   collection__source__published=True).exists()
            if delete:
                self.delete_attribute_value_change(attribute_value_change=attribute_value_change)
            else:
                if overwrite or not es.exists(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=attribute_value_change.id):
                    body = ElasticsearchDB._get_elasticsearch_attribute_value_change_to_index(
                        attribute_value_change=attribute_value_change)
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=attribute_value_change.id,
                        body=body)

    def q_update_attribute_value_change(self, attribute_value_change):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_attribute_value_change, attribute_value_change=attribute_value_change, ttl=-1)

    def update_attribute_value_change(self, attribute_value_change):
        self.add_attribute_value_change(attribute_value_change=attribute_value_change, overwrite=True)

    def q_delete_attribute_value_change(self, attribute_value_change):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_attribute_value_change, attribute_value_change=attribute_value_change, ttl=-1)

    def delete_attribute_value_change(self, attribute_value_change):
        if attribute_value_change is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            try:
                es.delete(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ATTRIBUTE_VALUES_LOG_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=attribute_value_change.id)
            except NotFoundError:
                pass

    def q_add_entity_entity_change(self, entity_entity_change, overwrite=False):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_entity_entity_change, entity_entity_change=entity_entity_change,
                      overwrite=overwrite, ttl=-1)

    def add_entity_entity_change(self, entity_entity_change, overwrite=False):
        if entity_entity_change is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            delete = entity_entity_change.deleted or not entity_entity_change.published or \
                     entity_entity_change.changeset.deleted or not entity_entity_change.changeset.published or \
                     entity_entity_change.changeset.collection.deleted or not entity_entity_change.changeset.collection.published or \
                     entity_entity_change.changeset.collection.source.deleted or not entity_entity_change.changeset.collection.source.published or \
                     (
                             entity_entity_change.entity_entity is not None and (
                             entity_entity_change.entity_entity.deleted or not entity_entity_change.entity_entity.published or
                             entity_entity_change.entity_entity.entity_a.deleted or not entity_entity_change.entity_entity.entity_a.published or
                             entity_entity_change.entity_entity.entity_b.deleted or not entity_entity_change.entity_entity.entity_b.published))
            if not delete:
                delete = not entity_entity_change.entity_entity.entity_entity_collections.filter(deleted=False,
                                                                                                 published=True,
                                                                                                 collection__deleted=False,
                                                                                                 collection__published=True,
                                                                                                 collection__source__deleted=False,
                                                                                                 collection__source__published=True).exists()
            if delete:
                self.delete_entity_entity_change(entity_entity_change=entity_entity_change)
            else:
                if overwrite or not es.exists(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity_change.id):
                    body = ElasticsearchDB._get_elasticsearch_entity_entity_change_to_index(
                        entity_entity_change=entity_entity_change)
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity_change.id,
                        body=body)

    def q_update_entity_entity_change(self, entity_entity_change):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_entity_entity_change, entity_entity_change=entity_entity_change, ttl=-1)

    def update_entity_entity_change(self, entity_entity_change):
        self.add_entity_entity_change(entity_entity_change=entity_entity_change, overwrite=True)

    def q_delete_entity_entity_change(self, entity_entity_change):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_entity_entity_change, entity_entity_change=entity_entity_change, ttl=-1)

    def delete_entity_entity_change(self, entity_entity_change):
        if entity_entity_change is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            try:
                es.delete(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_ENTITY_ENTITY_LOG_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=entity_entity_change.id)
            except NotFoundError:
                pass

    def q_add_codebook_value(self, codebook_value, overwrite=False):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.add_codebook_value, codebook_value=codebook_value, overwrite=overwrite, ttl=-1)

    def add_codebook_value(self, codebook_value, overwrite=False):
        if codebook_value is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            if codebook_value.deleted or not codebook_value.published or codebook_value.codebook.deleted or not codebook_value.codebook.published:
                self.delete_codebook_value(codebook_value=codebook_value)
            else:
                if overwrite or not es.exists(
                        index=ElasticsearchDB.get_elasticsearch_index_name(const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=codebook_value.id):
                    body = ElasticsearchDB._get_elasticsearch_codebook_value_to_index(codebook_value=codebook_value)
                    es.index(
                        index=ElasticsearchDB.get_elasticsearch_index_name(
                            const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
                        doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=codebook_value.id,
                        body=body)

    def q_update_codebook_value(self, codebook_value):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.update_codebook_value, codebook_value=codebook_value, ttl=-1)

    def update_codebook_value(self, codebook_value):
        self.add_codebook_value(codebook_value=codebook_value, overwrite=True)

    def q_delete_codebook_value(self, codebook_value):
        es_db = ElasticsearchDB.get_db()
        queue = ElasticsearchDB._get_queue()
        queue.enqueue(es_db.delete_codebook_value, codebook_value=codebook_value, ttl=-1)

    def delete_codebook_value(self, codebook_value):
        if codebook_value is not None and ElasticsearchDB.is_elasticsearch_settings_exists():
            es = self.get_elasticsearch()
            try:
                es.delete(
                    index=ElasticsearchDB.get_elasticsearch_index_name(
                        const.ELASTICSEARCH_CODEBOOKS_INDEX_NAME),
                    doc_type=ElasticsearchDB.get_elasticsearch_doc_type(), id=codebook_value.id)
            except NotFoundError:
                pass


class Neo4jDB(BaseDatabase):
    const.NEO4J_DEFAULTS = {
        'TYPE': 'bolt',
        'HOST': '127.0.0.1',
        'PORT': '7687',
    }

    neo4j = None

    @staticmethod
    def get_db():
        ret = None
        request_loc_mem_cache = None
        try:
            request_loc_mem_cache = middleware.get_request_loc_mem_cache()
            ret = request_loc_mem_cache.get('neo4jdb')
        except AssertionError:
            pass
        if ret is None:
            ret = Neo4jDB()
            if request_loc_mem_cache is not None:
                request_loc_mem_cache.set('neo4jdb', ret)
        return ret

    @staticmethod
    def _get_queue():
        return django_rq.get_queue('neo4j', default_timeout='300m')

    @staticmethod
    def is_neo4j_settings_exists():
        ret = False
        addon_databases = getattr(settings, 'ADDON_DATABASES', None)
        if addon_databases is not None:
            for addon_database in addon_databases:
                if 'BACKEND' in addon_database and addon_database['BACKEND'] == 'mocbackend.databases.Neo4jDB':
                    ret = True
        return ret

    @staticmethod
    def _get_neo4j_setting(setting_name):
        ret = None
        addon_databases = getattr(settings, 'ADDON_DATABASES', None)
        if addon_databases is not None:
            for addon_database in addon_databases:
                if 'BACKEND' in addon_database and addon_database['BACKEND'] == 'mocbackend.databases.Neo4jDB':
                    if setting_name in addon_database:
                        ret = addon_database[setting_name]
                    elif setting_name in const.NEO4J_DEFAULTS:
                        ret = const.NEO4J_DEFAULTS[setting_name]
                    break
        return ret

    @staticmethod
    def _get_neo4j_connection_strings():
        ret = 'bolt://'
        connection_type = Neo4jDB._get_neo4j_setting('TYPE')
        if connection_type == 'http':
            ret = 'http://'
        elif connection_type == 'https':
            ret = 'https://'
        ret = ret + Neo4jDB._get_neo4j_setting('HOST') + ':' + Neo4jDB._get_neo4j_setting('PORT')
        return ret

    def get_neo4j(self):
        if self.neo4j is None:
            self.neo4j = GraphDatabase.driver(Neo4jDB._get_neo4j_connection_strings(), auth=(
                Neo4jDB._get_neo4j_setting('USER'), Neo4jDB._get_neo4j_setting('PASSWORD')))
        return self.neo4j

    @staticmethod
    def _get_neo4j_entity_to_index(entity):
        ret = {
            'public_id': entity.public_id,
            'is_pep': BaseDatabase._is_pep(entity=entity),
            'entity_type_string_id': entity.entity_type.string_id,
            'entity_type_name': entity.entity_type.name,
            'published': entity.published,
            'deleted': entity.deleted
        }

        entity_first_name = ''
        entity_second_name = ''
        entity_name = ''
        entity_legal_entity_entity_type_ids = set()
        entity_legal_entity_entity_type_values = set()
        for attribute_value in entity.attribute_values.filter(
                Q(attribute__finally_deleted=False, attribute__finally_published=True,
                  attribute_value_collections__deleted=False,
                  attribute_value_collections__published=True,
                  attribute_value_collections__collection__deleted=False,
                  attribute_value_collections__collection__published=True,
                  attribute_value_collections__collection__source__deleted=False,
                  attribute_value_collections__collection__source__published=True
                  ) & (
                        Q(value_codebook_item=None) | Q(value_codebook_item__deleted=False,
                                                        value_codebook_item__published=True,
                                                        value_codebook_item__codebook__deleted=False,
                                                        value_codebook_item__codebook__published=True)) & (
                        Q(attribute__string_id='person_first_name') | Q(
                    attribute__string_id='person_last_name') | Q(
                    attribute__string_id='legal_entity_name') | Q(
                    attribute__string_id='legal_entity_entity_type') | Q(
                    attribute__string_id='real_estate_name') | Q(attribute__string_id='movable_name') | Q(
                    attribute__string_id='savings_name'))).distinct():
            if attribute_value.attribute.string_id == 'person_first_name':
                entity_first_name = entity_first_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'person_last_name':
                entity_second_name = entity_second_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'legal_entity_name':
                entity_name = entity_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'legal_entity_entity_type':
                entity_legal_entity_entity_type_ids.add(attribute_value.get_raw_first_value().id)
                entity_legal_entity_entity_type_values.add(attribute_value.get_raw_first_value().value)
            elif attribute_value.attribute.string_id == 'real_estate_name':
                entity_name = entity_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'movable_name':
                entity_name = entity_name + ' ' + attribute_value.get_raw_first_value()
            elif attribute_value.attribute.string_id == 'savings_name':
                entity_name = entity_name + ' ' + attribute_value.get_raw_first_value()
        if entity_name == '':
            entity_name = entity_first_name.strip() + ' ' + entity_second_name.strip()
        entity_name = entity_name.strip()

        ret.update({
            'name': entity_name
        })
        if entity.entity_type.string_id == 'legal_entity':
            ret.update({
                'legal_entity_type_id': list(entity_legal_entity_entity_type_ids),
                'legal_entity_type_value': list(entity_legal_entity_entity_type_values)
            })

        return ret

    @staticmethod
    def _get_neo4j_connection_to_index(entity_entity):
        currency_code = None
        currency_sign = None
        currency_sign_before_value = None
        if entity_entity.transaction_currency is not None:
            currency_code = entity_entity.transaction_currency.code
            currency_sign = entity_entity.transaction_currency.sign
            currency_sign_before_value = entity_entity.transaction_currency.sign_before_value
        ret = {
            'id': entity_entity.id,
            'connection_type_string_id': entity_entity.connection_type.string_id,
            'connection_type_name': entity_entity.connection_type.name,
            'connection_type_reverse_name': entity_entity.connection_type.reverse_name,
            'connection_type_category_string_id': entity_entity.connection_type.category.string_id,
            'connection_type_category_name': entity_entity.connection_type.category.name,
            'valid_from': None if entity_entity.valid_from is None else entity_entity.valid_from.isoformat(),
            'valid_to': None if entity_entity.valid_to is None else entity_entity.valid_to.isoformat(),
            'transaction_amount': None if entity_entity.transaction_amount is None else float(
                entity_entity.transaction_amount),
            'transaction_date': None if entity_entity.transaction_date is None else entity_entity.transaction_date.isoformat(),
            'transaction_currency_code': currency_code,
            'transaction_currency_sign': currency_sign,
            'transaction_currency_sign_before_value': currency_sign_before_value,
            'published': entity_entity.published and entity_entity.entity_a.published and entity_entity.entity_b.published and entity_entity.entity_entity_collections.filter(
                published=True, collection__published=True, collection__source__published=True).exists(),
            'deleted': entity_entity.deleted or entity_entity.entity_a.deleted or entity_entity.entity_b.deleted or not entity_entity.entity_entity_collections.filter(
                deleted=False, collection__deleted=False, collection__source__deleted=False).exists(),

            'entity_a_public_id': entity_entity.entity_a.public_id,
            'entity_a_is_pep': BaseDatabase._is_pep(entity=entity_entity.entity_a),
            'entity_a_entity_type_string_id': entity_entity.entity_a.entity_type.string_id,
            'entity_a_published': entity_entity.entity_a.published,
            'entity_a_deleted': entity_entity.entity_a.deleted,

            'entity_b_public_id': entity_entity.entity_b.public_id,
            'entity_b_is_pep': BaseDatabase._is_pep(entity=entity_entity.entity_b),
            'entity_b_entity_type_string_id': entity_entity.entity_b.entity_type.string_id,
            'entity_b_published': entity_entity.entity_b.published,
            'entity_b_deleted': entity_entity.entity_b.deleted,
        }

        if entity_entity.entity_a.entity_type.string_id == 'legal_entity':
            entity_legal_entity_entity_type_ids = set()
            for attribute_value in entity_entity.entity_a.attribute_values.filter(
                    Q(attribute__finally_deleted=False, attribute__finally_published=True,
                      attribute_value_collections__deleted=False,
                      attribute_value_collections__published=True,
                      attribute_value_collections__collection__deleted=False,
                      attribute_value_collections__collection__published=True,
                      attribute_value_collections__collection__source__deleted=False,
                      attribute_value_collections__collection__source__published=True,
                      attribute__string_id='legal_entity_entity_type'
                      ) & (
                            ~Q(value_codebook_item=None) & Q(value_codebook_item__deleted=False,
                                                            value_codebook_item__published=True,
                                                            value_codebook_item__codebook__deleted=False,
                                                            value_codebook_item__codebook__published=True))).distinct():
                entity_legal_entity_entity_type_ids.add(attribute_value.get_raw_first_value().id)

            ret.update({
                'entity_a_legal_entity_type_id': list(entity_legal_entity_entity_type_ids),
            })

        if entity_entity.entity_b.entity_type.string_id == 'legal_entity':
            entity_legal_entity_entity_type_ids = set()
            for attribute_value in entity_entity.entity_b.attribute_values.filter(
                    Q(attribute__finally_deleted=False, attribute__finally_published=True,
                      attribute_value_collections__deleted=False,
                      attribute_value_collections__published=True,
                      attribute_value_collections__collection__deleted=False,
                      attribute_value_collections__collection__published=True,
                      attribute_value_collections__collection__source__deleted=False,
                      attribute_value_collections__collection__source__published=True,
                      attribute__string_id='legal_entity_entity_type'
                      ) & (
                            ~Q(value_codebook_item=None) & Q(value_codebook_item__deleted=False,
                                                            value_codebook_item__published=True,
                                                            value_codebook_item__codebook__deleted=False,
                                                            value_codebook_item__codebook__published=True))).distinct():
                entity_legal_entity_entity_type_ids.add(attribute_value.get_raw_first_value().id)

            ret.update({
                'entity_b_legal_entity_type_id': list(entity_legal_entity_entity_type_ids),
            })

        return ret

    def q_init(self, command=None):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.init, command=command, ttl=-1)

    def init(self, command=None):
        if not Neo4jDB.is_neo4j_settings_exists():
            if command is not None:
                command.stdout.write(command.style.ERROR('Neo4j not configured'))
            return

        neo4j = self.get_neo4j()

        with neo4j.session() as session:
            with session.begin_transaction() as tx:
                tx.run('MATCH ()-[r:relationship]->() DELETE r')
                tx.run('MATCH (r:relationship) DELETE r')
                tx.run('MATCH (n:node) DELETE n')

        if command is not None:
            command.stdout.write(command.style.SUCCESS(
                'All relationships and nodes deleted!'))

        with neo4j.session() as session:
            results = session.run('CALL db.indexes')
            for result in results:
                label = result.value('label', None)
                if label in ['node', 'relationship']:
                    props = result.value('properties', None)
                    if props:
                        session.run('DROP INDEX ON :' + label + '(' + ','.join(p for p in props) + ')')

        if command is not None:
            command.stdout.write(command.style.SUCCESS('All indexes deleted!'))

        with neo4j.session() as session:
            session.run('CREATE INDEX ON :node(public_id)')
            session.run('CREATE INDEX ON :node(entity_type_string_id)')
            session.run('CREATE INDEX ON :node(legal_entity_type_id)')
            session.run('CREATE INDEX ON :node(is_pep)')
            session.run('CREATE INDEX ON :node(published)')
            session.run('CREATE INDEX ON :node(deleted)')

            session.run('CREATE INDEX ON :relationship(id)')
            session.run('CREATE INDEX ON :relationship(connection_type_string_id)')
            session.run('CREATE INDEX ON :relationship(connection_type_category_string_id)')
            session.run('CREATE INDEX ON :relationship(valid_from)')
            session.run('CREATE INDEX ON :relationship(valid_to)')
            session.run('CREATE INDEX ON :relationship(transaction_amount)')
            session.run('CREATE INDEX ON :relationship(transaction_date)')
            session.run('CREATE INDEX ON :relationship(transaction_currency_code)')
            session.run('CREATE INDEX ON :relationship(published)')
            session.run('CREATE INDEX ON :relationship(deleted)')

            session.run('CREATE INDEX ON :relationship(entity_a_public_id)')
            session.run('CREATE INDEX ON :relationship(entity_a_is_pep)')
            session.run('CREATE INDEX ON :relationship(entity_a_entity_type_string_id)')
            session.run('CREATE INDEX ON :relationship(entity_a_published)')
            session.run('CREATE INDEX ON :relationship(entity_a_deleted)')
            session.run('CREATE INDEX ON :relationship(entity_a_legal_entity_type_id)')

            session.run('CREATE INDEX ON :relationship(entity_b_public_id)')
            session.run('CREATE INDEX ON :relationship(entity_b_is_pep)')
            session.run('CREATE INDEX ON :relationship(entity_b_entity_type_string_id)')
            session.run('CREATE INDEX ON :relationship(entity_b_published)')
            session.run('CREATE INDEX ON :relationship(entity_b_deleted)')
            session.run('CREATE INDEX ON :relationship(entity_b_legal_entity_type_id)')

        if command is not None:
            command.stdout.write(command.style.SUCCESS('All indexes created!'))

    def q_add_entity(self, entity, overwrite=False, add_connections=True):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.add_entity, entity=entity, overwrite=overwrite, add_connections=add_connections, ttl=-1)

    def add_entity(self, entity, overwrite=False, add_connections=True):
        if entity is not None and Neo4jDB.is_neo4j_settings_exists():
            neo4j = self.get_neo4j()
            if entity.deleted or not entity.published:
                self.delete_entity(entity=entity)
            else:
                with neo4j.session() as session:
                    exists = session.run('MATCH (n:node { public_id: $public_id }) RETURN COUNT(*)',
                                         public_id=entity.public_id).single().value() > 0
                if overwrite and exists:
                    properties = Neo4jDB._get_neo4j_entity_to_index(entity)
                    with neo4j.session() as session:
                        session.run('MATCH (n:node { public_id: $public_id }) SET n = $properties',
                                    public_id=entity.public_id, properties=properties)

                if not exists:
                    properties = Neo4jDB._get_neo4j_entity_to_index(entity)
                    with neo4j.session() as session:
                        session.run('CREATE (n:node $properties)', properties=properties)

            if add_connections:
                for entity_entity in entity.reverse_connections.all():
                    self.add_connection(entity_entity=entity_entity, overwrite=overwrite)

                for entity_entity in entity.connections.all():
                    self.add_connection(entity_entity=entity_entity, overwrite=overwrite)

    def q_update_entity(self, entity, update_connections=True):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.update_entity, entity=entity, update_connections=update_connections, ttl=-1)

    def update_entity(self, entity, update_connections=True):
        self.add_entity(entity=entity, overwrite=True, add_connections=update_connections)

    def q_delete_entity(self, entity):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.delete_entity, entity=entity, ttl=-1)

    def delete_entity(self, entity):
        if entity is not None and Neo4jDB.is_neo4j_settings_exists():
            neo4j = self.get_neo4j()
            with neo4j.session() as session:
                with session.begin_transaction() as tx:
                    tx.run(
                        'MATCH (n:node { public_id: $public_id })-[r1:relationship]-(r:relationship)-[r2:relationship]-() DELETE r1, r2, r, n',
                        public_id=entity.public_id)

    def q_add_connection(self, entity_entity, overwrite=False):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.add_connection, entity_entity=entity_entity, overwrite=overwrite, ttl=-1)

    def add_connection(self, entity_entity, overwrite=False):
        if entity_entity is not None and Neo4jDB.is_neo4j_settings_exists():
            neo4j = self.get_neo4j()
            if entity_entity.deleted or not entity_entity.published or entity_entity.entity_a.deleted or not entity_entity.entity_a.published or entity_entity.entity_b.deleted or not entity_entity.entity_b.published or not entity_entity.entity_entity_collections.filter(
                    deleted=False, published=True, collection__deleted=False, collection__published=True,
                    collection__source__deleted=False, collection__source__published=True).exists():
                self.delete_connection(entity_entity=entity_entity)
            else:
                with neo4j.session() as session:
                    exists = session.run('MATCH (r:relationship { id: $entity_entity_id }) RETURN COUNT(*)',
                                         entity_entity_id=entity_entity.id).single().value() > 0
                if overwrite and exists:
                    properties = Neo4jDB._get_neo4j_connection_to_index(entity_entity)
                    with neo4j.session() as session:
                        session.run('MATCH (r:relationship { id: $entity_entity_id }) SET r = $properties',
                                    entity_entity_id=entity_entity.id, properties=properties)
                if not exists:
                    properties = Neo4jDB._get_neo4j_connection_to_index(entity_entity)
                    with neo4j.session() as session:
                        session.run(
                            'MATCH (a:node { public_id: $entity_a_public_id }), (b:node { public_id: $entity_b_public_id }) CREATE (a)-[r1:relationship]->(r:relationship $properties)-[r2:relationship]->(b)',
                            entity_a_public_id=entity_entity.entity_a.public_id,
                            entity_b_public_id=entity_entity.entity_b.public_id, properties=properties)

    def q_update_connection(self, entity_entity):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.update_connection, entity_entity=entity_entity, ttl=-1)

    def update_connection(self, entity_entity):
        self.add_connection(entity_entity=entity_entity, overwrite=True)

    def q_delete_connection(self, entity_entity):
        neo4j_db = Neo4jDB.get_db()
        queue = Neo4jDB._get_queue()
        queue.enqueue(neo4j_db.delete_connection, entity_entity=entity_entity, ttl=-1)

    def delete_connection(self, entity_entity):
        if entity_entity is not None and Neo4jDB.is_neo4j_settings_exists():
            neo4j = self.get_neo4j()
            with neo4j.session() as session:
                session.run('MATCH (r:relationship {id: $entity_entity_id})-[r1:relationship]-() DELETE r1, r', entity_entity_id=entity_entity.id)
