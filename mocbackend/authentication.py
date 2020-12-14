from rest_framework.authentication import TokenAuthentication


class QueryStringTokenAuthentication(TokenAuthentication):
    '''
    Extend the TokenAuthentication class to support querystring authentication
    in the form of "http://www.example.com/?auth_token=<token_key>"
    '''


    def authenticate(self, request):
        # Check if 'auth_token' is in the request query params.
        # Give precedence to 'Authorization' header.
        if 'auth_token' in request.query_params:
            return self.authenticate_credentials(request.query_params.get('auth_token'))

        #return super(QueryStringTokenAuthentication, self).authenticate(request)
        return super().authenticate(request)
