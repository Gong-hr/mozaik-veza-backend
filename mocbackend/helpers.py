import datetime

import django_rq
from django.conf import settings
from django.utils import six, timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from pytz import InvalidTimeError
from rest_framework import ISO_8601
from rest_framework.compat import unicode_to_repr
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import humanize_datetime
from templated_email import send_templated_mail

from mocbackend import const

from Crypto.Hash import SHA3_512

const.MOCBACKEND_DEFAULTS = {
    'FIXED_POINT_DECIMAL_PLACES': 2,
    'RANGE_FLOATING_POINT_FROM_INCLUSIVE': True,
    'RANGE_FLOATING_POINT_TO_INCLUSIVE': True,

    'API_GEO_VALUES_SEPARATOR': ', ',
    'API_RANGE_VALUES_SEPARATOR': ' -> ',
    'ADMIN_GEO_VALUES_SEPARATOR': ', ',
    'ADMIN_RANGE_VALUES_SEPARATOR': ' -> ',
}

const.DATA_TYPE_BOOLEAN = 'boolean'
const.DATA_TYPE_INT = 'int'
const.DATA_TYPE_FIXED_POINT = 'fixed_point'
const.DATA_TYPE_FLOATING_POINT = 'floating_point'
const.DATA_TYPE_STRING = 'string'
const.DATA_TYPE_TEXT = 'text'
const.DATA_TYPE_DATETIME = 'datetime'
const.DATA_TYPE_DATE = 'date'
const.DATA_TYPE_CODEBOOK = 'codebook'
const.DATA_TYPE_GEO = 'geo'
const.DATA_TYPE_RANGE_INT = 'range_int'
const.DATA_TYPE_RANGE_FIXED_POINT = 'range_fixed_point'
const.DATA_TYPE_RANGE_FLOATING_POINT = 'range_floating_point'
const.DATA_TYPE_RANGE_DATETIME = 'range_datetime'
const.DATA_TYPE_RANGE_DATE = 'range_date'
const.DATA_TYPE_COMPLEX = 'complex'

# db to internal
const.DATA_TYPE_MAPPING_SIMPLE = {
    'boolean': const.DATA_TYPE_BOOLEAN,
    'int': const.DATA_TYPE_INT,
    'fixed_point': const.DATA_TYPE_FIXED_POINT,
    'floating_point': const.DATA_TYPE_FLOATING_POINT,
    'string': const.DATA_TYPE_STRING,
    'text': const.DATA_TYPE_TEXT,
    'datetime': const.DATA_TYPE_DATETIME,
    'date': const.DATA_TYPE_DATE,
    'codebook': const.DATA_TYPE_CODEBOOK
}
const.DATA_TYPE_MAPPING_COMPLEX = {
    'geo': const.DATA_TYPE_GEO,
    'range_int': const.DATA_TYPE_RANGE_INT,
    'range_fixed_point': const.DATA_TYPE_RANGE_FIXED_POINT,
    'range_floating_point': const.DATA_TYPE_RANGE_FLOATING_POINT,
    'range_datetime': const.DATA_TYPE_RANGE_DATETIME,
    'range_date': const.DATA_TYPE_RANGE_DATE,
    'complex': const.DATA_TYPE_COMPLEX
}

const.VAT_NUMBER_SALT = 'w1Ts3#Wn0Ne#bUEl_dMFLhB4xH8QuTWM'


def get_input_formats(attribute_type):
    ret = None
    data_type = attribute_type.data_type.string_id
    if (data_type in const.DATA_TYPE_MAPPING_SIMPLE and const.DATA_TYPE_MAPPING_SIMPLE[
        data_type] == const.DATA_TYPE_DATETIME) or (
            data_type in const.DATA_TYPE_MAPPING_COMPLEX and const.DATA_TYPE_MAPPING_COMPLEX[
        data_type] == const.DATA_TYPE_RANGE_DATETIME):
        ret = api_settings.DATETIME_INPUT_FORMATS
    elif (data_type in const.DATA_TYPE_MAPPING_SIMPLE and const.DATA_TYPE_MAPPING_SIMPLE[
        data_type] == const.DATA_TYPE_DATE) or (
            data_type in const.DATA_TYPE_MAPPING_COMPLEX and const.DATA_TYPE_MAPPING_COMPLEX[
        data_type] == const.DATA_TYPE_RANGE_DATE):
        ret = api_settings.DATE_INPUT_FORMATS
    return ret


def get_values_separator(attribute_type):
    ret = None
    data_type = attribute_type.data_type.string_id
    if data_type in const.DATA_TYPE_MAPPING_COMPLEX:
        if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
            ret = get_api_geo_values_separator()
        else:
            ret = get_api_range_values_separator()
    return ret


def get_mocbackend_default_setting(setting_name):
    mocbackend_settings = getattr(settings, 'MOCBACKEND_DEFAULTS', None)
    if mocbackend_settings is not None and setting_name in mocbackend_settings:
        ret = mocbackend_settings[setting_name]
    else:
        ret = const.MOCBACKEND_DEFAULTS[setting_name]
    return ret


def get_divider(attribute_type):
    decimal_places = attribute_type.fixed_point_decimal_places
    if decimal_places is None:
        decimal_places = get_mocbackend_default_setting('FIXED_POINT_DECIMAL_PLACES')
    return 10 ** decimal_places


def get_fixed_point_decimal_places(attribute_type):
    ret = None
    data_type = attribute_type.data_type.string_id
    if (data_type in const.DATA_TYPE_MAPPING_SIMPLE and const.DATA_TYPE_MAPPING_SIMPLE[
        data_type] == const.DATA_TYPE_FIXED_POINT) or (
            data_type in const.DATA_TYPE_MAPPING_COMPLEX and const.DATA_TYPE_MAPPING_COMPLEX[
        data_type] == const.DATA_TYPE_RANGE_FIXED_POINT):
        ret = attribute_type.fixed_point_decimal_places
        if ret is None:
            ret = get_mocbackend_default_setting('FIXED_POINT_DECIMAL_PLACES')
    return ret


def get_range_floating_point_from_inclusive(attribute_type):
    ret = None
    data_type = attribute_type.data_type.string_id
    if data_type in const.DATA_TYPE_MAPPING_COMPLEX and const.DATA_TYPE_MAPPING_COMPLEX[
        data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
        ret = attribute_type.range_floating_point_from_inclusive
        if ret is None:
            ret = get_mocbackend_default_setting('RANGE_FLOATING_POINT_FROM_INCLUSIVE')
    return ret


def get_range_floating_point_to_inclusive(attribute_type):
    ret = None
    data_type = attribute_type.data_type.string_id
    if data_type in const.DATA_TYPE_MAPPING_COMPLEX and const.DATA_TYPE_MAPPING_COMPLEX[
        data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
        ret = attribute_type.range_floating_point_to_inclusive
        if ret is None:
            ret = get_mocbackend_default_setting('RANGE_FLOATING_POINT_TO_INCLUSIVE')
    return ret


def get_api_geo_values_separator():
    return get_mocbackend_default_setting('API_GEO_VALUES_SEPARATOR')


def get_api_range_values_separator():
    return get_mocbackend_default_setting('API_RANGE_VALUES_SEPARATOR')


def get_admin_geo_values_separator():
    return get_mocbackend_default_setting('ADMIN_GEO_VALUES_SEPARATOR')


def get_admin_range_values_separator():
    return get_mocbackend_default_setting('ADMIN_RANGE_VALUES_SEPARATOR')


error_messages = {
    'datetime_invalid': _('Datetime has wrong format. Use one of these formats instead: {format}.'),
    'datetime_date': _('Expected a datetime but got a date.'),
    'datetime_make_aware': _('Invalid datetime for the timezone "{timezone}".')
}

MISSING_ERROR_MESSAGE = (
    'ValidationError raised by `{class_name}`, but error key `{key}` does '
    'not exist in the `error_messages` dictionary.'
)


def fail(instance, key, **kwargs):
    """
    A helper method that simply raises a validation error.
    """
    try:
        msg = error_messages[key]
    except KeyError:
        class_name = instance.__class__.__name__
        msg = MISSING_ERROR_MESSAGE.format(class_name=class_name, key=key)
        raise AssertionError(msg)
    message_string = msg.format(**kwargs)
    raise ValidationError(message_string, code=key)


def default_timezone():
    return timezone.get_current_timezone() if settings.USE_TZ else None


def datetime_enforce_timezone(instance, value, field_timezone=None):
    """
    When `self.default_timezone` is `None`, always return naive datetimes.
    When `self.default_timezone` is not `None`, always return aware datetimes.
    """
    if field_timezone is None:
        field_timezone = getattr(None, 'timezone', default_timezone())

    if field_timezone is not None:
        if timezone.is_aware(value):
            return value.astimezone(field_timezone)
        try:
            return timezone.make_aware(value, field_timezone)
        except InvalidTimeError:
            fail(instance, 'datetime_make_aware', timezone=field_timezone)
    elif (field_timezone is None) and timezone.is_aware(value):
        return timezone.make_naive(value, utc)
    return value


def datetime_to_internal_value(instance, value, field_timezone=None):
    input_formats = getattr(None, 'input_formats', api_settings.DATETIME_INPUT_FORMATS)

    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        fail(instance, 'date')

    if isinstance(value, datetime.datetime):
        return datetime_enforce_timezone(instance, value, field_timezone)

    for input_format in input_formats:
        if input_format.lower() == ISO_8601:
            try:
                parsed = parse_datetime(value)
                if parsed is not None:
                    return datetime_enforce_timezone(instance, parsed, field_timezone)
            except (ValueError, TypeError):
                pass
        else:
            try:
                parsed = datetime.datetime.strptime(value, input_format)
                return datetime_enforce_timezone(instance, parsed, field_timezone)
            except (ValueError, TypeError):
                pass

    humanized_format = humanize_datetime.datetime_formats(input_formats)
    fail(instance, 'invalid', format=humanized_format)


def datetime_to_representation(instance, value):
    if not value:
        return None

    output_format = getattr(None, 'format', api_settings.DATETIME_FORMAT)

    if output_format is None or isinstance(value, six.string_types):
        return value

    if output_format.lower() == ISO_8601:
        value = datetime_enforce_timezone(instance, value)
        value = value.isoformat()
        if value.endswith('+00:00'):
            value = value[:-6] + 'Z'
        return value
    return value.strftime(output_format)


def get_attribute_value_serializer_data(attribute_value_data):
    data_type = attribute_value_data['attribute'].attribute_type.data_type.string_id

    field_name_1 = None
    field_name_2 = None
    value_1 = None
    value_2 = None
    if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
        if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
            field_name_1 = 'value_boolean'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
            field_name_1 = 'value_int'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
            field_name_1 = 'value_fixed_point'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
            field_name_1 = 'value_floating_point'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
            field_name_1 = 'value_string'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
            field_name_1 = 'value_text'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
            field_name_1 = 'value_datetime'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
            field_name_1 = 'value_date'
            value_1 = attribute_value_data['value']
        elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
            field_name_1 = 'value_codebook_item'
            value_1 = attribute_value_data['value']
    elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
        if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
            field_name_1 = 'value_geo_lat'
            field_name_2 = 'value_geo_lon'
            value_1, value_2 = attribute_value_data['value'].split(
                get_api_geo_values_separator().strip())
        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
            field_name_1 = 'value_range_int_from'
            field_name_2 = 'value_range_int_to'
            value_1, value_2 = attribute_value_data['value'].split(
                get_api_range_values_separator().strip())
        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
            field_name_1 = 'value_range_fixed_point_from'
            field_name_2 = 'value_range_fixed_point_to'
            value_1, value_2 = attribute_value_data['value'].split(
                get_api_range_values_separator().strip())
        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
            field_name_1 = 'value_range_floating_point_from'
            field_name_2 = 'value_range_floating_point_to'
            value_1, value_2 = attribute_value_data['value'].split(
                get_api_range_values_separator().strip())
        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
            field_name_1 = 'value_range_datetime_from'
            field_name_2 = 'value_range_datetime_to'
            value_1, value_2 = attribute_value_data['value'].split(
                get_api_range_values_separator().strip())
        elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
            field_name_1 = 'value_range_date_from'
            field_name_2 = 'value_range_date_to'
            value_1, value_2 = attribute_value_data['value'].split(
                get_api_range_values_separator().strip())

    if value_1 is not None:
        value_1 = value_1.strip()
    if value_1 == '':
        value_1 = None
    if value_2 is not None:
        value_2 = value_2.strip()
    if value_2 == '':
        value_2 = None
    return value_1, value_2, field_name_1, field_name_2


def check_attribute_entity_type(attribute, entity_type):
    if attribute.entity_type is None and attribute.attribute is None:
        return False
    if attribute.entity_type is not None:
        return attribute.entity_type == entity_type
    return check_attribute_entity_type(attribute.attribute, entity_type)


def check_attribute_collection(attribute, entity_entity):
    if attribute.collection is None:
        return False

    return attribute.collection in entity_entity.from_collections.filter(deleted=False, published=True,
                                                                         source__deleted=False, source__published=True,
                                                                         entity_entity_collections__deleted=False,
                                                                         entity_entity_collections__published=True).distinct()


def is_attribute_for_entity(attribute):
    if attribute.entity_type is None and attribute.attribute is None:
        return False
    if attribute.entity_type is not None:
        return True
    return is_attribute_for_entity(attribute.attribute)


def is_attribute_for_connection(attribute):
    if attribute.collection is None and attribute.attribute is None:
        return False
    if attribute.collection is not None and attribute.attribute is None:
        return True
    return is_attribute_for_connection(attribute.attribute)


def get_root_attribute(attribute):
    ret = attribute
    if attribute.attribute is not None:
        ret = get_root_attribute(attribute.attribute)
    return ret


class CurrentUserInfoDefault(object):
    def set_context(self, serializer_field):
        self.user = serializer_field.context['request'].user

    def __call__(self):
        return self.user.user_info

    def __repr__(self):
        return unicode_to_repr('%s()' % self.__class__.__name__)


def lreplace(pattern, sub, string):
    """
    Replaces 'pattern' in 'string' with 'sub' if 'pattern' starts 'string'.
    """
    import re
    return re.sub('^%s' % pattern, sub, string)


def sha3_512_encode(data, salt):
    h_obj = SHA3_512.new()
    h_obj.update(data.encode() + salt.encode())
    return h_obj.hexdigest()


def hash(data, salt=''):
    return sha3_512_encode(data=data, salt=salt)


def send_mail_q(template_name, from_email, recipient_list, context, fail_silently=False, auth_user=None,
                auth_password=None,
                connection=None, html_message=None, queue_name='system_mails'):
    queue = django_rq.get_queue(queue_name, default_timeout='60m')
    queue.enqueue(send_templated_mail, template_name=template_name, from_email=from_email,
                  recipient_list=recipient_list, context=context, fail_silently=fail_silently, auth_user=auth_user,
                  auth_password=auth_password, connection=connection, html_message=html_message, ttl=-1)


def get_queue(queue, default_timeout='60m'):
    return django_rq.get_queue(queue, default_timeout=default_timeout)


class JSONChunkGenerator:
    _first = True
    _renderer = None
    _last_id = None
    _raw = False

    def __init__(self, renderer, last_id, raw=False):
        self._renderer = renderer
        self._last_id = last_id
        self._raw = raw

    def generate(self, data):
        ret = self._renderer.render(data=data).decode('utf-8')
        suffix = ''
        if self._first:
            self._first = False
            if self._raw:
                prefix = '['
            else:
                prefix = '{"results":['
        else:
            prefix = ','
        if data['id'] == self._last_id:
            if self._raw:
                suffix = ']'
            else:
                suffix = ']}'
        return prefix + ret + suffix
