from threading import currentThread
from django.core.cache.backends.locmem import LocMemCache
from django.utils.deprecation import MiddlewareMixin

_request_loc_mem_caches = {}
_installed_request_loc_mem_cache_middleware = False


def get_request_loc_mem_cache():
    assert _installed_request_loc_mem_cache_middleware, 'RequestLocMemCacheMiddleware not loaded'
    return _request_loc_mem_caches[currentThread()]


# LocMemCache is a threadsafe local memory cache
class RequestLocMemCache(LocMemCache):
    def __init__(self):
        name = 'RequestLocMemCache@%i' % hash(currentThread())
        params = dict()
        super().__init__(name, params)


class RequestLocMemCacheMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        global _installed_request_loc_mem_cache_middleware
        _installed_request_loc_mem_cache_middleware = True
        super().__init__(get_response=get_response)

    def process_request(self, request):
        cache = _request_loc_mem_caches.get(currentThread()) or RequestLocMemCache()
        cache.clear()
        _request_loc_mem_caches[currentThread()] = cache

    def process_response(self, request, response):
        cache = _request_loc_mem_caches.get(currentThread())
        if cache is not None:
            cache.clear()
        try:
            del _request_loc_mem_caches[currentThread()]
        except KeyError:
            pass
        return response


class AccessLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        from mocbackend.models import AccessLog
        access_log = AccessLog()

        if 'HTTP_X_FORWARDED_FOR' in request.META:
            access_log.remote_ip = request.META['HTTP_X_FORWARDED_FOR']
        else:
            access_log.remote_ip = request.META['REMOTE_ADDR']

        access_log.method = request.method
        access_log.path = request.path_info
        access_log.query = request.META['QUERY_STRING']

        import jsonpickle
        jsonpickle.set_encoder_options('simplejson', sort_keys=True, indent=4)
        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
        jsonpickle.set_encoder_options('demjson', sort_keys=True, indent=4)

        if request.POST:
            access_log.post_data = jsonpickle.encode(request.POST)
        access_log.request = jsonpickle.encode(request)
        # access_log.response = jsonpickle.encode(response)

        access_log.response_status_code = response.status_code
        access_log.save()

        return response

