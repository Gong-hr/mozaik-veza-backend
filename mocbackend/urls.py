from django.conf.urls import url, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.documentation import include_docs_urls
from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view
from rest_framework.urlpatterns import format_suffix_patterns

import mocbackend
from mocbackend import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
# router.register(r'key-value', views.KeyValueView)
router.register(r'attributes', views.AttributeViewSet)
router.register(r'attribute-value', views.AttributeValueCollectionViewSet)
router.register(r'attribute-types', views.AttributeTypeViewSet)
router.register(r'codebooks', views.CodebookViewSet)
router.register(r'codebook-values', views.CodebookValueViewSet)
router.register(r'collections', views.CollectionViewSet)
router.register(r'collection-types', views.CollectionTypeViewSet)
router.register(r'connection-types', views.ConnectionTypeViewSet)
router.register(r'connection-type-categories', views.ConnectionTypeCategoryViewSet)
router.register(r'currencies', views.CurrencyViewSet)
router.register(r'data-types', views.DataTypeViewSet)
router.register(r'entities', views.EntityViewSet)
router.register(r'entity-connection', views.EntityEntityCollectionViewSet)
router.register(r'entity-types', views.EntityTypeViewSet)
router.register(r'sources', views.SourceViewSet)
router.register(r'source-types', views.SourceTypeViewSet)
router.register(r'article-content-short', views.ArticleContentShortViewSet, 'article-content-short')
router.register(r'article-content-long', views.ArticleContentLongViewSet, 'article-content-long')
router.register(r'article', views.ArticleViewSet)
router.register(r'user', views.UserViewSet)
router.register(r'user-password', views.UserPasswordViewSet, 'user-password')
router.register(r'verify-email', views.VerifyEmailViewSet, 'verify-email')
router.register(r'password-change-token', views.GeneratePasswordChangeTokenViewSet, 'password-change-token')
router.register(r'user-password-token', views.UserPasswordWithoutAuthViewSet, 'user-password-token')
router.register(r'user-entity', views.UserEntityViewSet)
router.register(r'saved-search', views.UserSavedSearchViewSet)

# The API URLs are now determined automatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
                  url(r'^', include(router.urls)),
              ] + format_suffix_patterns([
    url(r'^key-value/$', views.KeyValueViewCreate.as_view()),
    url(r'^key-value/(?P<pk>[^/.]+)/$', views.KeyValueView.as_view(), name="test1234"),
    url(r'^search/entities/autocomplete/(?P<term>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.AutocompleteEntitiesView.as_view()),
    url(r'^search/entities/by-public_id/(?P<pk>[^/.]+)/$', views.EntityView.as_view()),
    url(r'^search/entities/by-attributes-values/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.EntitiesByAttributesValuesView.as_view()),
    url(r'^search/entities/by-vat_number/(?P<vat_number>\d+)/$',
        views.LegalEntitiesByVatNumberView.as_view()),
    url(r'^search/entities/by-connection-count/(?P<pk>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.EntitiesByConnectionCountView.as_view()),
    url(r'^search/connections/by-id/(?P<pk>\d+)/$', views.ConnectionView.as_view()),
    url(r'^search/connections/by-attributes-values/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.ConnectionsByAttributesValuesView.as_view()),
    url(r'^graph/neighbours/by-attributes-values/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.NeighboursByAttributesValuesView.as_view()),
    url(r'^graph/connections/by-attributes-values/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.ConnectionsByAttributesValuesGraphView.as_view()),
    url(r'^search/connections/by-ends/(?P<pk1>[^/.]+)/(?P<pk2>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.ConnectionsByEndsView.as_view()),
    url(r'^graph/connections/by-ends/(?P<pk1>[^/.]+)/(?P<pk2>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.ConnectionsByEndsGraphView.as_view()),
    url(r'^search/connections/count-per-year-by-end/(?P<pk>[^/.]+)/$',
        views.ConnectionsCountPerYearByEndView.as_view()),
    url(r'^search/connections/by-end/(?P<pk>[^/.]+)/$', views.ConnectionsByEnd.as_view()),
    url(r'^search/attributes/by-entity-type/(?P<entity_type>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.AttributesByEntityTypeView.as_view()),
    url(r'^search/attributes/connections/(?P<offset>\d+)/(?P<limit>\d+)/$', views.AttributesConnectionsView.as_view()),
    url(
        r'^search/connection-types/autocomplete/(?P<connection_type_category>[^/.]+)/(?P<term>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.AutocompleteConnectionTypesView.as_view()),
    url(
        r'^search/connection-types/by-connection-type-category/(?P<connection_type_category>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.ConnectionTypesByConnectionTypeCategoryView.as_view()),
    url(
        r'^search/attribute-value-changes/(?P<type>[^/.]+)/(?P<pk>[^/.]+)/(?P<attribute>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.LogAttributeValueChangeView.as_view()),
    url(r'^search/entity-entity-changes/(?P<pk>\d+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.LogEntityEntityChangeView.as_view()),
    url(r'^search/codebook-values/(?P<codebook>[^/.]+)/(?P<offset>\d+)/(?P<limit>\d+)/$',
        views.CodebookValuesView.as_view()),
    url(r'^search/objects-count/$', views.ObjectsCountView.as_view()),
    url(r'^schema/$', get_schema_view(title='MOC API')),
    url(r'^docs/', include_docs_urls(title='MOC API')),
    url(r'^api-token-auth/$', obtain_auth_token)
])
