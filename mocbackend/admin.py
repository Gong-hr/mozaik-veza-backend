from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.utils import get_deleted_objects, model_ngettext
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import router
from django.db.models import Q
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _, ugettext_lazy
from jet import filters
from jet.admin import CompactInline
from rest_framework.authtoken.admin import TokenAdmin

from mocbackend import const
from mocbackend import models


# from builtins import super


def delete_selected(modeladmin, request, queryset):
    """
    Default action which deletes the selected objects.

    This action first displays a confirmation page which shows all the
    deletable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it deletes all selected objects and redirects back to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Check that the user has delete permission for the actual model
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    using = router.db_for_write(modeladmin.model)

    # Populate deletable_objects, a data structure of all related objects that
    # will also be deleted.
    deletable_objects, model_count, perms_needed, protected = get_deleted_objects(
        queryset, opts, request.user, modeladmin.admin_site, using)

    # The user has already confirmed the deletion.
    # Do the deletion and return a None to display the change list view again.
    if request.POST.get('post') and not protected:
        if perms_needed:
            raise PermissionDenied
        n = len(queryset)
        if n:
            for obj in queryset:
                obj_display = force_text(obj)
                modeladmin.log_deletion(request, obj, obj_display)
            for item in queryset:
                item.delete()
            modeladmin.message_user(request, _("Successfully deleted %(count)d %(items)s.") % {
                "count": n, "items": model_ngettext(modeladmin.opts, n)
            }, messages.SUCCESS)
        # Return None to display the change list page again.
        return None

    if len(queryset) == 1:
        objects_name = force_text(opts.verbose_name)
    else:
        objects_name = force_text(opts.verbose_name_plural)

    if perms_needed or protected:
        title = _("Cannot delete %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = dict(
        modeladmin.admin_site.each_context(request),
        title=title,
        objects_name=objects_name,
        deletable_objects=[deletable_objects],
        model_count=dict(model_count).items(),
        queryset=queryset,
        perms_lacking=perms_needed,
        protected=protected,
        opts=opts,
        action_checkbox_name=admin.helpers.ACTION_CHECKBOX_NAME,
        media=modeladmin.media,
    )

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(request, modeladmin.delete_selected_confirmation_template or [
        "admin/%s/%s/delete_selected_confirmation.html" % (app_label, opts.model_name),
        "admin/%s/delete_selected_confirmation.html" % app_label,
        "admin/delete_selected_confirmation.html"
    ], context)


delete_selected.short_description = ugettext_lazy("Delete selected %(verbose_name_plural)s")


def make_published(modeladmin, request, queryset):
    rows_updated = len(queryset)
    for item in queryset:
        item.published = True
        item.save()
    if rows_updated == 1:
        message_bit = '1 item was'
    else:
        message_bit = '%s items were' % rows_updated
    modeladmin.message_user(request, '%s successfully marked as published.' % message_bit)


make_published.short_description = ugettext_lazy("Mark selected %(verbose_name_plural)s as published")


def make_unpublished(modeladmin, request, queryset):
    rows_updated = len(queryset)
    for item in queryset:
        item.published = False
        item.save()
    if rows_updated == 1:
        message_bit = '1 item was'
    else:
        message_bit = '%s items were' % rows_updated
    modeladmin.message_user(request, '%s successfully marked as unpublished.' % message_bit)


make_unpublished.short_description = ugettext_lazy("Mark selected %(verbose_name_plural)s as unpublished")


def make_soft_deleted(modeladmin, request, queryset):
    rows_updated = len(queryset)
    for item in queryset:
        item.deleted = True
        item.save()
    if rows_updated == 1:
        message_bit = '1 item was'
    else:
        message_bit = '%s items were' % rows_updated
    modeladmin.message_user(request, '%s successfully soft deleted.' % message_bit)


make_soft_deleted.short_description = ugettext_lazy("Soft delete selected %(verbose_name_plural)s")


def make_soft_undeleted(modeladmin, request, queryset):
    rows_updated = len(queryset)
    for item in queryset:
        item.deleted = False
        item.save()
    if rows_updated == 1:
        message_bit = '1 item was'
    else:
        message_bit = '%s items were' % rows_updated
    modeladmin.message_user(request, '%s successfully soft undeleted.' % message_bit)


make_soft_undeleted.short_description = ugettext_lazy("Soft undelete selected %(verbose_name_plural)s")


# https://stackoverflow.com/questions/23070679/django-show-reverse-foreignkey-lookup-on-admin-page-as-read-only-list

class MocModelAdmin(admin.ModelAdmin):
    edit_readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.edit_readonly_fields + self.readonly_fields
        return self.readonly_fields
        # return ()


class StageEntityEntityCollectionInline(CompactInline):
    model = models.StageEntityEntity.from_collections.through
    readonly_fields = ('collection',
                       'created_at',
                       'updated_at')
    extra = 0
    # show_change_link = True
    verbose_name = 'Collection'
    verbose_name_plural = 'Collections'

    def has_add_permission(self, request):
        return False


class StageAttributeValueCollectionInline(CompactInline):
    model = models.StageAttributeValue.from_collections.through
    readonly_fields = ('collection',
                       'valid_from',
                       'valid_to',
                       'created_at',
                       'updated_at')
    extra = 0
    # show_change_link = True
    verbose_name = 'Collection'
    verbose_name_plural = 'Collections'

    def has_add_permission(self, request):
        return False


# todo: custom validation
class StageAttributeAdmin(MocModelAdmin):
    readonly_fields = ('created_at',
                       'updated_at')
    edit_readonly_fields = ('string_id',
                            'entity_type',
                            'collection',
                            'attribute',
                            'attribute_type')
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['string_id',
                    'name',
                    'entity_type__name',
                    'collection__name',
                    'attribute_type__name',
                    'created_at',
                    'updated_at',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['string_id',
                     'name']
    list_filter = [('entity_type', filters.RelatedFieldAjaxListFilter),
                   ('collection', filters.RelatedFieldAjaxListFilter),
                   ('attribute_type', filters.RelatedFieldAjaxListFilter),
                   ('created_at', filters.DateRangeFilter),
                   ('updated_at', filters.DateRangeFilter),
                   'published',
                   'deleted']
    exclude = ['is_required',
               'default_value',
               'is_unique']

    def entity_type__name(self, obj):
        ret = None
        if obj.entity_type is not None:
            ret = obj.entity_type.name
        return ret

    entity_type__name.admin_order_field = 'entity_type__name'

    def collection__name(self, obj):
        ret = None
        if obj.collection is not None:
            ret = obj.collection.name
        return ret

    collection__name.admin_order_field = 'collection__name'

    def attribute_type__name(self, obj):
        return obj.attribute_type.name

    attribute_type__name.admin_order_field = 'attribute_type__name'


# todo: custom validation
class StageAttributeTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',
                            'data_type',
                            'codebook',
                            'fixed_point_decimal_places')
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['string_id',
                    'name',
                    'data_type__name',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['string_id',
                     'name']
    list_filter = [('data_type', filters.RelatedFieldAjaxListFilter),
                   'published',
                   'deleted']
    exclude = ['is_multivalue',
               'permited_values']

    def data_type__name(self, obj):
        return obj.data_type.name

    data_type__name.admin_order_field = 'data_type__name'


# todo: custom validacija, vjerojatno i custom forma
class StageAttributeValueAdmin(MocModelAdmin):
    readonly_fields = ('created_at',
                       'updated_at')
    edit_readonly_fields = ('entity',
                            'entity_entity',
                            'attribute',
                            'currency')
    list_display = ['id',
                    'entity__public_id',
                    'entity_entity__entity_a__public_id',
                    'entity_entity__entity_b__public_id',
                    'entity_entity__connection_type__name',
                    'attribute__name',
                    'value',
                    'created_at',
                    'updated_at']
    search_fields = ['id',
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
                     'value_codebook_item__value']
    list_filter = [('entity', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__entity_a', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__entity_b', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__connection_type', filters.RelatedFieldAjaxListFilter),
                   ('attribute', filters.RelatedFieldAjaxListFilter),
                   ('created_at', filters.DateRangeFilter),
                   ('updated_at', filters.DateRangeFilter)]
    inlines = [StageAttributeValueCollectionInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'value_codebook_item':
            kwargs['queryset'] = models.StageCodebookValue.objects.filter(deleted=False, codebook__deleted=False,
                                                                          codebook__attribute_types__deleted=False).distinct()
        elif db_field.name == 'entity_entity':
            kwargs['queryset'] = models.StageEntityEntity.objects.filter(deleted=False, entity_a__deleted=False,
                                                                         entity_b__deleted=False,
                                                                         entity_entity_collections__deleted=False,
                                                                         entity_entity_collections__collection__deleted=False,
                                                                         entity_entity_collections__collection__source__deleted=False).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def entity__public_id(self, obj):
        ret = None
        if obj.entity is not None:
            ret = obj.entity.public_id
        return ret

    entity__public_id.admin_order_field = 'entity__public_id'

    def entity_entity__entity_a__public_id(self, obj):
        ret = None
        if obj.entity_entity is not None:
            ret = obj.entity_entity.entity_a.public_id
        return ret

    entity_entity__entity_a__public_id.admin_order_field = 'entity_entity__entity_a__public_id'

    def entity_entity__entity_b__public_id(self, obj):
        ret = None
        if obj.entity_entity is not None:
            ret = obj.entity_entity.entity_b.public_id
        return ret

    entity_entity__entity_b__public_id.admin_order_field = 'entity_entity__entity_b__public_id'

    def entity_entity__connection_type__name(self, obj):
        ret = None
        if obj.entity_entity is not None:
            ret = obj.entity_entity.connection_type.name
        return ret

    entity_entity__connection_type__name.admin_order_field = 'entity_entity__connection_type__name'

    def attribute__name(self, obj):
        return obj.attribute.name

    attribute__name.admin_order_field = 'attribute__name'

    def value(self, obj):
        return obj.get_value()

    def get_search_results_disabled(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        try:
            queryset |= self.model.objects.filter(value_boolean=search_term)
        except (ValueError, ValidationError):
            pass
        try:
            queryset |= self.model.objects.filter(value_int=search_term)
            queryset |= self.model.objects.filter(value_fixed_point=search_term)
            queryset |= self.model.objects.filter(value_range_int_from=search_term)
            queryset |= self.model.objects.filter(value_range_int_to=search_term)
            queryset |= self.model.objects.filter(value_range_fixed_point_from=search_term)
            queryset |= self.model.objects.filter(value_range_fixed_point_to=search_term)
        except ValueError:
            pass
        try:
            queryset |= self.model.objects.filter(value_floating_point=search_term)
            queryset |= self.model.objects.filter(value_range_floating_point_from=search_term)
            queryset |= self.model.objects.filter(value_range_floating_point_to=search_term)
        except ValueError:
            pass
        try:
            queryset |= self.model.objects.filter(value_datetime=search_term)
            queryset |= self.model.objects.filter(value_range_datetime_from=search_term)
            queryset |= self.model.objects.filter(value_range_datetime_to=search_term)
        except (ValueError, ValidationError):
            pass
        try:
            queryset |= self.model.objects.filter(value_date=search_term)
            queryset |= self.model.objects.filter(value_range_date_from=search_term)
            queryset |= self.model.objects.filter(value_range_date_to=search_term)
        except (ValueError, ValidationError):
            pass
        try:
            queryset |= self.model.objects.filter(value_geo_lat=search_term)
            queryset |= self.model.objects.filter(value_geo_lon=search_term)
        except (ValueError, ValidationError):
            pass
        queryset |= self.model.objects.filter(value_string=search_term)
        queryset |= self.model.objects.filter(value_text=search_term)
        queryset |= self.model.objects.filter(value_codebook_item__value=search_term)
        return queryset, use_distinct

    def get_exclude(self, request, obj=None):
        if obj:
            exclude = [
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
                'value_codebook_item']
            data_type = obj.attribute.attribute_type.data_type.string_id
            if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
                if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                    exclude.remove('value_boolean')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                    exclude.remove('value_int')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                    exclude.remove('value_fixed_point')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                    exclude.remove('value_floating_point')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                    exclude.remove('value_string')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                    exclude.remove('value_text')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                    exclude.remove('value_datetime')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                    exclude.remove('value_date')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                    exclude.remove('value_codebook_item')
            elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
                if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                    exclude.remove('value_geo_lat')
                    exclude.remove('value_geo_lon')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                    exclude.remove('value_range_int_from')
                    exclude.remove('value_range_int_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                    exclude.remove('value_range_fixed_point_from')
                    exclude.remove('value_range_fixed_point_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                    exclude.remove('value_range_floating_point_from')
                    exclude.remove('value_range_floating_point_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                    exclude.remove('value_range_datetime_from')
                    exclude.remove('value_range_datetime_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                    exclude.remove('value_range_date_from')
                    exclude.remove('value_range_date_to')
            if self.exclude is not None:
                return tuple(exclude) + self.exclude
            else:
                return exclude
        return self.exclude

    def has_add_permission(self, request):
        return False


class LogAttributeValueChangeAdmin(MocModelAdmin):
    edit_readonly_fields = ('changeset',
                            'change_type',
                            'old_valid_from',
                            'new_valid_from',
                            'old_valid_to',
                            'new_valid_to',
                            'entity',
                            'entity_entity',
                            'attribute',
                            'old_value_boolean',
                            'new_value_boolean',
                            'old_value_int',
                            'new_value_int',
                            'old_value_fixed_point',
                            'new_value_fixed_point',
                            'old_value_floating_point',
                            'new_value_floating_point',
                            'old_value_string',
                            'new_value_string',
                            'old_value_text',
                            'new_value_text',
                            'old_value_datetime',
                            'new_value_datetime',
                            'old_value_date',
                            'new_value_date',
                            'old_value_geo_lat',
                            'old_value_geo_lon',
                            'new_value_geo_lat',
                            'new_value_geo_lon',
                            'old_value_range_int_from',
                            'old_value_range_int_to',
                            'new_value_range_int_from',
                            'new_value_range_int_to',
                            'old_value_range_fixed_point_from',
                            'old_value_range_fixed_point_to',
                            'new_value_range_fixed_point_from',
                            'new_value_range_fixed_point_to',
                            'old_value_range_floating_point_from',
                            'old_value_range_floating_point_to',
                            'new_value_range_floating_point_from',
                            'new_value_range_floating_point_to',
                            'old_value_range_datetime_from',
                            'old_value_range_datetime_to',
                            'new_value_range_datetime_from',
                            'new_value_range_datetime_to',
                            'old_value_range_date_from',
                            'old_value_range_date_to',
                            'new_value_range_date_from',
                            'new_value_range_date_to',
                            'old_value_codebook_item',
                            'new_value_codebook_item',
                            'old_currency',
                            'new_currency')
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['id',
                    'changeset__collection__name',
                    'changeset__created_at',
                    'change_type__name',
                    'old_valid_from',
                    'new_valid_from',
                    'old_valid_to',
                    'new_valid_to',
                    'entity__public_id',
                    'entity_entity__entity_a__public_id',
                    'entity_entity__entity_b__public_id',
                    'entity_entity__connection_type__name',
                    'attribute__name',
                    'old_value',
                    'new_value',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['id',
                     'old_value_boolean',
                     'new_value_boolean',
                     'old_value_int',
                     'new_value_int',
                     'old_value_fixed_point',
                     'new_value_fixed_point',
                     'old_value_floating_point',
                     'new_value_floating_point',
                     'old_value_string',
                     'new_value_string',
                     'old_value_text',
                     'new_value_text',
                     'old_value_datetime',
                     'new_value_datetime',
                     'old_value_date',
                     'new_value_date',
                     'old_value_geo_lat',
                     'old_value_geo_lon',
                     'new_value_geo_lat',
                     'new_value_geo_lon',
                     'old_value_range_int_from',
                     'old_value_range_int_to',
                     'new_value_range_int_from',
                     'new_value_range_int_to',
                     'old_value_range_fixed_point_from',
                     'old_value_range_fixed_point_to',
                     'new_value_range_fixed_point_from',
                     'new_value_range_fixed_point_to',
                     'old_value_range_floating_point_from',
                     'old_value_range_floating_point_to',
                     'new_value_range_floating_point_from',
                     'new_value_range_floating_point_to',
                     'old_value_range_datetime_from',
                     'old_value_range_datetime_to',
                     'new_value_range_datetime_from',
                     'new_value_range_datetime_to',
                     'old_value_range_date_from',
                     'old_value_range_date_to',
                     'new_value_range_date_from',
                     'new_value_range_date_to',
                     'old_value_codebook_item__value',
                     'new_value_codebook_item__value']
    list_filter = [('changeset__collection', filters.RelatedFieldAjaxListFilter),
                   ('changeset__created_at', filters.DateRangeFilter),
                   ('change_type', filters.RelatedFieldAjaxListFilter),
                   ('old_valid_from', filters.DateRangeFilter),
                   ('new_valid_from', filters.DateRangeFilter),
                   ('old_valid_to', filters.DateRangeFilter),
                   ('new_valid_to', filters.DateRangeFilter),
                   ('entity', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__entity_a', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__entity_b', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__connection_type', filters.RelatedFieldAjaxListFilter),
                   ('attribute', filters.RelatedFieldAjaxListFilter),
                   'published',
                   'deleted']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'old_value_codebook_item' or db_field.name == 'new_value_codebook_item':
            kwargs['queryset'] = models.StageCodebookValue.objects.filter(deleted=False, codebook__deleted=False,
                                                                          codebook__attribute_types__deleted=False).distinct()
        elif db_field.name == 'entity_entity':
            kwargs['queryset'] = models.StageEntityEntity.objects.filter(deleted=False, entity_a__deleted=False,
                                                                         entity_b__deleted=False,
                                                                         entity_entity_collections__deleted=False,
                                                                         entity_entity_collections__collection__deleted=False,
                                                                         entity_entity_collections__collection__source__deleted=False).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changeset__collection__name(self, obj):
        return obj.changeset.collection.name

    changeset__collection__name.admin_order_field = 'changeset__collection__name'

    def changeset__created_at(self, obj):
        return obj.changeset.created_at

    changeset__created_at.admin_order_field = 'changeset__created_at'

    def change_type__name(self, obj):
        return obj.change_type.name

    change_type__name.admin_order_field = 'change_type__name'

    def entity__public_id(self, obj):
        ret = None
        if obj.entity is not None:
            ret = obj.entity.public_id
        return ret

    entity__public_id.admin_order_field = 'entity__public_id'

    def entity_entity__entity_a__public_id(self, obj):
        ret = None
        if obj.entity_entity is not None:
            ret = obj.entity_entity.entity_a.public_id
        return ret

    entity_entity__entity_a__public_id.admin_order_field = 'entity_entity__entity_a__public_id'

    def entity_entity__entity_b__public_id(self, obj):
        ret = None
        if obj.entity_entity is not None:
            ret = obj.entity_entity.entity_b.public_id
        return ret

    entity_entity__entity_b__public_id.admin_order_field = 'entity_entity__entity_b__public_id'

    def entity_entity__connection_type__name(self, obj):
        ret = None
        if obj.entity_entity is not None:
            ret = obj.entity_entity.connection_type.name
        return ret

    entity_entity__connection_type__name.admin_order_field = 'entity_entity__connection_type__name'

    def attribute__name(self, obj):
        return obj.attribute.name

    attribute__name.admin_order_field = 'attribute__name'

    def old_value(self, obj):
        return obj.get_old_value()

    def new_value(self, obj):
        return obj.get_new_value()

    def get_search_results_disabled(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        try:
            queryset |= self.model.objects.filter(
                Q(attribute_value__value_boolean=search_term) | Q(old_value_boolean=search_term) | Q(
                    new_value_boolean=search_term))
        except (ValueError, ValidationError):
            pass
        try:
            queryset |= self.model.objects.filter(
                Q(old_value_int=search_term) | Q(new_value_int=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_fixed_point=search_term) | Q(
                    new_value_fixed_point=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_int_from=search_term) | Q(
                    new_value_range_int_from=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_int_to=search_term) | Q(
                    new_value_range_int_to=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_fixed_point_from=search_term) | Q(new_value_range_fixed_point_from=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_fixed_point_to=search_term) | Q(new_value_range_fixed_point_to=search_term))
        except ValueError:
            pass
        try:
            queryset |= self.model.objects.filter(
                Q(old_value_floating_point=search_term) | Q(new_value_floating_point=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_floating_point_from=search_term) | Q(new_value_range_floating_point_from=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_floating_point_to=search_term) | Q(new_value_range_floating_point_to=search_term))
        except ValueError:
            pass
        try:
            queryset |= self.model.objects.filter(
                Q(old_value_datetime=search_term) | Q(new_value_datetime=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_datetime_from=search_term) | Q(new_value_range_datetime_from=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_datetime_to=search_term) | Q(new_value_range_datetime_to=search_term))
        except (ValueError, ValidationError):
            pass
        try:
            queryset |= self.model.objects.filter(
                Q(old_value_date=search_term) | Q(new_value_date=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_date_from=search_term) | Q(new_value_range_date_from=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_range_date_to=search_term) | Q(new_value_range_date_to=search_term))
        except (ValueError, ValidationError):
            pass
        try:
            queryset |= self.model.objects.filter(
                Q(old_value_geo_lat=search_term) | Q(new_value_geo_lat=search_term))
            queryset |= self.model.objects.filter(
                Q(old_value_geo_lon=search_term) | Q(new_value_geo_lon=search_term))
        except (ValueError, ValidationError):
            pass
        queryset |= self.model.objects.filter(
            Q(old_value_string=search_term) | Q(new_value_string=search_term))
        queryset |= self.model.objects.filter(
            Q(old_value_text=search_term) | Q(new_value_text=search_term))
        queryset |= self.model.objects.filter(
            Q(old_value_codebook_item__value=search_term) | Q(new_value_codebook_item__value=search_term))
        return queryset, use_distinct

    def get_fieldsets(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj:
            exclude = ['old_value_boolean',
                       'new_value_boolean',
                       'old_value_int',
                       'new_value_int',
                       'old_value_fixed_point',
                       'new_value_fixed_point',
                       'old_value_floating_point',
                       'new_value_floating_point',
                       'old_value_string',
                       'new_value_string',
                       'old_value_text',
                       'new_value_text',
                       'old_value_datetime',
                       'new_value_datetime',
                       'old_value_date',
                       'new_value_date',
                       'old_value_geo_lat',
                       'old_value_geo_lon',
                       'new_value_geo_lat',
                       'new_value_geo_lon',
                       'old_value_range_int_from',
                       'old_value_range_int_to',
                       'new_value_range_int_from',
                       'new_value_range_int_to',
                       'old_value_range_fixed_point_from',
                       'old_value_range_fixed_point_to',
                       'new_value_range_fixed_point_from',
                       'new_value_range_fixed_point_to',
                       'old_value_range_floating_point_from',
                       'old_value_range_floating_point_to',
                       'new_value_range_floating_point_from',
                       'new_value_range_floating_point_to',
                       'old_value_range_datetime_from',
                       'old_value_range_datetime_to',
                       'new_value_range_datetime_from',
                       'new_value_range_datetime_to',
                       'old_value_range_date_from',
                       'old_value_range_date_to',
                       'new_value_range_date_from',
                       'new_value_range_date_to',
                       'old_value_codebook_item',
                       'new_value_codebook_item']
            data_type = obj.attribute.attribute_type.data_type.string_id
            if data_type in const.DATA_TYPE_MAPPING_SIMPLE:
                if const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_BOOLEAN:
                    exclude.remove('old_value_boolean')
                    exclude.remove('new_value_boolean')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_INT:
                    exclude.remove('old_value_int')
                    exclude.remove('new_value_int')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FIXED_POINT:
                    exclude.remove('old_value_fixed_point')
                    exclude.remove('new_value_fixed_point')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_FLOATING_POINT:
                    exclude.remove('old_value_floating_point')
                    exclude.remove('new_value_floating_point')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_STRING:
                    exclude.remove('old_value_string')
                    exclude.remove('new_value_string')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_TEXT:
                    exclude.remove('old_value_text')
                    exclude.remove('new_value_text')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATETIME:
                    exclude.remove('old_value_datetime')
                    exclude.remove('new_value_datetime')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_DATE:
                    exclude.remove('old_value_date')
                    exclude.remove('new_value_date')
                elif const.DATA_TYPE_MAPPING_SIMPLE[data_type] == const.DATA_TYPE_CODEBOOK:
                    exclude.remove('old_value_codebook_item')
                    exclude.remove('new_value_codebook_item')
            elif data_type in const.DATA_TYPE_MAPPING_COMPLEX:
                if const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_GEO:
                    exclude.remove('old_value_geo_lat')
                    exclude.remove('old_value_geo_lon')
                    exclude.remove('new_value_geo_lat')
                    exclude.remove('new_value_geo_lon')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_INT:
                    exclude.remove('old_value_range_int_from')
                    exclude.remove('old_value_range_int_to')
                    exclude.remove('new_value_range_int_from')
                    exclude.remove('new_value_range_int_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FIXED_POINT:
                    exclude.remove('old_value_range_fixed_point_from')
                    exclude.remove('old_value_range_fixed_point_to')
                    exclude.remove('new_value_range_fixed_point_from')
                    exclude.remove('new_value_range_fixed_point_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_FLOATING_POINT:
                    exclude.remove('old_value_range_floating_point_from')
                    exclude.remove('old_value_range_floating_point_to')
                    exclude.remove('new_value_range_floating_point_from')
                    exclude.remove('new_value_range_floating_point_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATETIME:
                    exclude.remove('old_value_range_datetime_from')
                    exclude.remove('old_value_range_datetime_to')
                    exclude.remove('new_value_range_datetime_from')
                    exclude.remove('new_value_range_datetime_to')
                elif const.DATA_TYPE_MAPPING_COMPLEX[data_type] == const.DATA_TYPE_RANGE_DATE:
                    exclude.remove('old_value_range_date_from')
                    exclude.remove('old_value_range_date_to')
                    exclude.remove('new_value_range_date_from')
                    exclude.remove('new_value_range_date_to')
            fields = [field for field in fields if field not in exclude]
        return (
            (None, {
                'classes': ('wide',),
                'fields': fields}
             ),
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StaticChangeTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name']
    search_fields = ['string_id',
                     'name']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LogChangesetAdmin(MocModelAdmin):
    readonly_fields = ('created_at',)
    edit_readonly_fields = ('collection',)
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['collection__name',
                    'created_at',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    list_filter = [('collection',
                    filters.RelatedFieldAjaxListFilter),
                   ('created_at', filters.DateRangeFilter),
                   'published',
                   'deleted']

    def collection__name(self, obj):
        return obj.collection.name

    collection__name.admin_order_field = 'collection__name'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StageCodebookAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['string_id',
                    'name',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['string_id',
                     'name']
    list_filter = ['published',
                   'deleted']


class StageCodebookValueAdmin(MocModelAdmin):
    edit_readonly_fields = ('codebook',)
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['id',
                    'codebook__name',
                    'value',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['id',
                     'value']
    list_filter = [('codebook',
                    filters.RelatedFieldAjaxListFilter),
                   'published',
                   'deleted']

    def codebook__name(self, obj):
        return obj.codebook.name

    codebook__name.admin_order_field = 'codebook__name'


class StageCollectionAdmin(MocModelAdmin):
    readonly_fields = ('created_at',
                       'updated_at')
    edit_readonly_fields = ('string_id',
                            'source')
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['string_id',
                    'name',
                    'source__name',
                    'collection_type__name',
                    'quality',
                    'created_at',
                    'updated_at',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['string_id',
                     'name',
                     'description']
    list_filter = [('source', filters.RelatedFieldAjaxListFilter),
                   ('collection_type', filters.RelatedFieldAjaxListFilter),
                   'quality',
                   ('created_at', filters.DateRangeFilter),
                   ('updated_at', filters.DateRangeFilter),
                   'published',
                   'deleted']

    def source__name(self, obj):
        return obj.source.name

    source__name.admin_order_field = 'source__name'

    def collection_type__name(self, obj):
        return obj.collection_type.name

    collection_type__name.admin_order_field = 'collection_type__name'


class StaticCollectionTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name']
    search_fields = ['string_id',
                     'name']


class StaticConnectionTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name',
                    'reverse_name',
                    'potentially_pep',
                    'category__name']
    search_fields = ['string_id',
                     'name',
                     'reverse_name']
    list_filter = ['potentially_pep',
                   ('category', filters.RelatedFieldAjaxListFilter)]

    def category__name(self, obj):
        return obj.category.name

    category__name.admin_order_field = 'category__name'


class StaticConnectionTypeCategoryAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name']
    search_fields = ['string_id',
                     'name']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StaticCurrencyAmin(MocModelAdmin):
    list_display = ['code',
                    'sign',
                    'sign_before_value']
    search_fields = ['code',
                     'sign']
    list_filter = ['sign_before_value']


class StaticDataTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name']
    search_fields = ['string_id',
                     'name']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# todo: custom forma i validacija (gledati duplice EntityEntity)
class StageEntityAdmin(MocModelAdmin):
    readonly_fields = ('created_at',
                       'updated_at')
    edit_readonly_fields = ('public_id',
                            'entity_type',
                            'internal_slug',
                            'internal_slug_count')
    actions = [delete_selected, make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['public_id',
                    'entity_type__name',
                    'linked_potentially_pep',
                    'force_pep',
                    'created_at',
                    'updated_at',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['public_id']
    list_filter = [('entity_type',
                    filters.RelatedFieldAjaxListFilter),
                   'linked_potentially_pep',
                   'force_pep',
                   ('created_at', filters.DateRangeFilter),
                   ('updated_at', filters.DateRangeFilter),
                   'published',
                   'deleted']

    def entity_type__name(self, obj):
        return obj.entity_type.name

    entity_type__name.admin_order_field = 'entity_type__name'

    def has_add_permission(self, request):
        return False


class StageEntityEntityAdmin(MocModelAdmin):
    readonly_fields = ('created_at',
                       'updated_at')
    edit_readonly_fields = (
        'entity_a',
        'entity_b',
        'connection_type',
        'transaction_amount',
        'transaction_currency',
        'transaction_date',
        'valid_from',
        'valid_to')
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['entity_a__public_id',
                    'entity_b__public_id',
                    'connection_type__name',
                    'created_at',
                    'updated_at',
                    'published',
                    'deleted']
    list_filter = [('entity_a', filters.RelatedFieldAjaxListFilter),
                   ('entity_b', filters.RelatedFieldAjaxListFilter),
                   ('connection_type', filters.RelatedFieldAjaxListFilter),
                   'transaction_amount',
                   ('transaction_currency', filters.RelatedFieldAjaxListFilter),
                   ('transaction_date', filters.DateRangeFilter),
                   ('created_at', filters.DateRangeFilter),
                   ('updated_at', filters.DateRangeFilter),
                   'published',
                   'deleted']
    inlines = [StageEntityEntityCollectionInline]

    def entity_a__public_id(self, obj):
        return obj.entity_a.public_id

    entity_a__public_id.admin_order_field = 'entity_a__public_id'

    def entity_b__public_id(self, obj):
        return obj.entity_b.public_id

    entity_b__public_id.admin_order_field = 'entity_b__public_id'

    def connection_type__name(self, obj):
        return obj.connection_type.name

    connection_type__name.admin_order_field = 'connection_type__name'

    def has_add_permission(self, request):
        return False


class LogEntityEntityChangeAdmin(MocModelAdmin):
    edit_readonly_fields = (
        'changeset',
        'change_type',
        'old_valid_from',
        'new_valid_from',
        'old_valid_to',
        'new_valid_to',
        'entity_entity')
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['id',
                    'changeset__collection__name',
                    'changeset__created_at',
                    'change_type__name',
                    'old_valid_from',
                    'new_valid_from',
                    'old_valid_to',
                    'new_valid_to',
                    'entity_entity__entity_a__public_id',
                    'entity_entity__entity_b__public_id',
                    'entity_entity__connection_type__name',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['id']
    list_filter = [('changeset__collection', filters.RelatedFieldAjaxListFilter),
                   ('changeset__created_at', filters.DateRangeFilter),
                   ('change_type', filters.RelatedFieldAjaxListFilter),
                   ('old_valid_from', filters.DateRangeFilter),
                   ('new_valid_from', filters.DateRangeFilter),
                   ('old_valid_to', filters.DateRangeFilter),
                   ('new_valid_to', filters.DateRangeFilter),
                   ('entity_entity__entity_a', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__entity_b', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__connection_type', filters.RelatedFieldAjaxListFilter),
                   'entity_entity__transaction_amount',
                   ('entity_entity__transaction_currency', filters.RelatedFieldAjaxListFilter),
                   ('entity_entity__transaction_date', filters.DateRangeFilter),
                   'published',
                   'deleted']

    def changeset__collection__name(self, obj):
        return obj.changeset.collection.name

    changeset__collection__name.admin_order_field = 'changeset__collection__name'

    def changeset__created_at(self, obj):
        return obj.changeset.created_at

    changeset__created_at.admin_order_field = 'changeset__created_at'

    def change_type__name(self, obj):
        return obj.change_type.name

    change_type__name.admin_order_field = 'change_type__name'

    def entity_entity__entity_a__public_id(self, obj):
        return obj.entity_entity.entity_a.public_id

    entity_entity__entity_a__public_id.admin_order_field = 'entity_entity__entity_a__public_id'

    def entity_entity__entity_b__public_id(self, obj):
        return obj.entity_entity.entity_b.public_id

    entity_entity__entity_b__public_id.admin_order_field = 'entity_entity__entity_b__public_id'

    def entity_entity__connection_type__name(self, obj):
        return obj.entity_entity.connection_type.name

    entity_entity__connection_type__name.admin_order_field = 'entity_entity__connection_type__name'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StaticEntityTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name']
    search_fields = ['string_id',
                     'name']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StageSourceAdmin(MocModelAdmin):
    readonly_fields = ('created_at',
                       'updated_at')
    edit_readonly_fields = ('string_id',)
    actions = [make_published, make_unpublished, make_soft_deleted, make_soft_undeleted]
    list_display = ['string_id',
                    'name',
                    'source_type__name',
                    'quality',
                    'created_at',
                    'updated_at',
                    'published',
                    'deleted']
    list_editable = ['published',
                     'deleted']
    search_fields = ['string_id',
                     'name',
                     'description',
                     'address',
                     'contact',
                     'note']
    list_filter = [('source_type', filters.RelatedFieldAjaxListFilter),
                   'quality',
                   ('created_at', filters.DateRangeFilter),
                   ('updated_at', filters.DateRangeFilter),
                   'published',
                   'deleted']

    def source_type__name(self, obj):
        return obj.source_type.name

    source_type__name.admin_order_field = 'source_type__name'


class StaticSourceTypeAdmin(MocModelAdmin):
    edit_readonly_fields = ('string_id',)
    list_display = ['string_id',
                    'name']
    search_fields = ['string_id',
                     'name']


class KeyValueAdmin(admin.ModelAdmin):
    readonly_fields = ('key',
                       'raw_data',
                       'value')
    list_display = ['key',
                    'value']
    search_fields = ['value',
                     'raw_data']


class ArticleAdmin(admin.ModelAdmin):
    list_display = ['slug', 'title']
    search_fields = ['slug', 'title']


class UserInfoAdmin(admin.ModelAdmin):
    readonly_fields = ['user']
    list_display = ['user',
                    'send_notification_on_change_watched_entity']
    list_filter = ['send_notification_on_change_watched_entity']
    search_fields = ['user']

    def has_add_permission(self, request):
        return False


class SecurityExtensionUserAdmin(admin.ModelAdmin):
    readonly_fields = ['user',
                       'unverified_email',
                       'password_change_token_created_at',
                       'email_verification_token_created_at']
    exclude = ['password_change_token_hash',
               'password_change_token_hash_salt',
               'email_verification_token_hash',
               'email_verification_token_hash_salt']
    list_display = ['user']
    search_fields = ['user']


admin.site.register(models.StageAttribute, StageAttributeAdmin)
admin.site.register(models.StageAttributeType, StageAttributeTypeAdmin)
admin.site.register(models.StageAttributeValue, StageAttributeValueAdmin)
admin.site.register(models.LogAttributeValueChange, LogAttributeValueChangeAdmin)
admin.site.register(models.StaticChangeType, StaticChangeTypeAdmin)
admin.site.register(models.LogChangeset, LogChangesetAdmin)
admin.site.register(models.StageCodebook, StageCodebookAdmin)
admin.site.register(models.StageCodebookValue, StageCodebookValueAdmin)
admin.site.register(models.StageCollection, StageCollectionAdmin)
admin.site.register(models.StaticCollectionType, StaticCollectionTypeAdmin)
admin.site.register(models.StaticConnectionType, StaticConnectionTypeAdmin)
admin.site.register(models.StaticConnectionTypeCategory, StaticConnectionTypeCategoryAdmin)
admin.site.register(models.StaticCurrency, StaticCurrencyAmin)
admin.site.register(models.StaticDataType, StaticDataTypeAdmin)
admin.site.register(models.StageEntity, StageEntityAdmin)
admin.site.register(models.StageEntityEntity, StageEntityEntityAdmin)
admin.site.register(models.LogEntityEntityChange, LogEntityEntityChangeAdmin)
admin.site.register(models.StaticEntityType, StaticEntityTypeAdmin)
admin.site.register(models.StageSource, StageSourceAdmin)
admin.site.register(models.StaticSourceType, StaticSourceTypeAdmin)
admin.site.register(models.KeyValue, KeyValueAdmin)
admin.site.register(models.Article, ArticleAdmin)
admin.site.register(models.UserInfo, UserInfoAdmin)
admin.site.register(models.SecurityExtensionUser, SecurityExtensionUserAdmin)

TokenAdmin.raw_id_fields = ('user',)
