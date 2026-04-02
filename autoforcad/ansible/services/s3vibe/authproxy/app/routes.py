import json
import os
from twisted.web import resource, server
from twisted.internet import defer
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
import treq

from .auth import AuthManager


class RootResource(resource.Resource):
    
    def __init__(self, db_pool):
        resource.Resource.__init__(self)
        self.db_pool = db_pool
        self.auth_manager = AuthManager(db_pool)
        
        self.putChild(b'api', APIResource(self.auth_manager))
        self.putChild(b's3', S3ProxyResource(self.auth_manager))
        self.putChild(b'health', HealthResource())
    
    def render_GET(self, request):
        request.setHeader(b'content-type', b'application/json')
        return json.dumps({
            'service': 'Storage AuthProxy',
            'version': '1.0.0',
            'status': 'healthy'
        }).encode('utf-8')


class HealthResource(resource.Resource):
    
    isLeaf = True
    
    def render_GET(self, request):
        request.setHeader(b'content-type', b'application/json')
        return json.dumps({'status': 'healthy'}).encode('utf-8')


class APIResource(resource.Resource):
    
    def __init__(self, auth_manager):
        resource.Resource.__init__(self)
        self.auth_manager = auth_manager
        
        self.putChild(b'register', RegisterResource(auth_manager))
        self.putChild(b'login', LoginResource(auth_manager))
        self.putChild(b'buckets', BucketsResource(auth_manager))


class RegisterResource(resource.Resource):
    
    isLeaf = True
    
    def __init__(self, auth_manager):
        resource.Resource.__init__(self)
        self.auth_manager = auth_manager
    
    def render_POST(self, request):
        request.setHeader(b'content-type', b'application/json')
        
        try:
            data = json.loads(request.content.read().decode('utf-8'))
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            if not all([username, email, password]):
                request.setResponseCode(400)
                return json.dumps({
                    'error': 'Missing required fields: username, email, password'
                }).encode('utf-8')
            
            user = self.auth_manager.register_user(username, email, password)
            
            request.setResponseCode(201)
            return json.dumps({
                'success': True,
                'user': user
            }).encode('utf-8')
        
        except Exception:
            request.setResponseCode(400)
            return json.dumps({
                'error': 'User registration failed. Username or email may already exist.'
            }).encode('utf-8')


class LoginResource(resource.Resource):
    
    isLeaf = True
    
    def __init__(self, auth_manager):
        resource.Resource.__init__(self)
        self.auth_manager = auth_manager
    
    def render_POST(self, request):
        request.setHeader(b'content-type', b'application/json')
        
        try:
            data = json.loads(request.content.read().decode('utf-8'))
            username = data.get('username')
            password = data.get('password')
            
            if not all([username, password]):
                request.setResponseCode(400)
                return json.dumps({
                    'error': 'Missing required fields: username, password'
                }).encode('utf-8')
            
            ip_address = request.getClientAddress().host
            user_agent = request.getHeader(b'user-agent')
            
            try:
                auth_data = self.auth_manager.authenticate_user(
                    username, password, ip_address, user_agent
                )
                
                if auth_data:
                    buckets = self.auth_manager.get_user_buckets(auth_data['user_id'])
                    
                    request.setResponseCode(200)
                    return json.dumps({
                        'success': True,
                        'user': {
                            'id': auth_data['user_id'],
                            'username': auth_data['username'],
                            'email': auth_data['email']
                        },
                        'token': auth_data['token'],
                        'buckets': buckets
                    }).encode('utf-8')
                else:
                    request.setResponseCode(401)
                    return json.dumps({
                        'error': 'Invalid credentials'
                    }).encode('utf-8')
            except Exception:
                request.setResponseCode(401)
                return json.dumps({
                    'error': 'Invalid credentials'
                }).encode('utf-8')
        
        except Exception:
            request.setResponseCode(400)
            return json.dumps({'error': 'Missing required fields: username, password'}).encode('utf-8')


class BucketsResource(resource.Resource):
    
    def __init__(self, auth_manager):
        resource.Resource.__init__(self)
        self.auth_manager = auth_manager
    
    def getChild(self, path, request):
        if path and request.method == b'DELETE':
            return BucketDeleteResource(self.auth_manager, path.decode('utf-8'))
        return self
    
    def render_GET(self, request):
        request.setHeader(b'content-type', b'application/json')
        
        try:
            token = request.getHeader(b's3-auth-token')
            if not token:
                request.setResponseCode(401)
                return json.dumps({'error': 'Missing authentication token'}).encode('utf-8')
            
            user_info = self.auth_manager.validate_token(token.decode('utf-8'))
            if not user_info:
                request.setResponseCode(401)
                return json.dumps({'error': 'Invalid or expired token'}).encode('utf-8')
            
            buckets = self.auth_manager.get_user_buckets(user_info['user_id'])
            
            return json.dumps({
                'success': True,
                'buckets': buckets
            }).encode('utf-8')
        except Exception:
            request.setResponseCode(500)
            return json.dumps({'error': 'Internal server error'}).encode('utf-8')
    
    def render_POST(self, request):
        request.setHeader(b'content-type', b'application/json')
        
        try:
            token = request.getHeader(b's3-auth-token')
            if not token:
                request.setResponseCode(401)
                return json.dumps({'error': 'Missing authentication token'}).encode('utf-8')
            
            user_info = self.auth_manager.validate_token(token.decode('utf-8'))
            if not user_info:
                request.setResponseCode(401)
                return json.dumps({'error': 'Invalid or expired token'}).encode('utf-8')
            
            data = json.loads(request.content.read().decode('utf-8'))
            name = data.get('name')
            description = data.get('description')
            
            if not name:
                request.setResponseCode(400)
                return json.dumps({'error': 'Bucket name is required'}).encode('utf-8')
            
            bucket = self.auth_manager.create_bucket(
                user_info['user_id'],
                name,
                description
            )
            
            request.setResponseCode(201)
            return json.dumps({
                'success': True,
                'bucket': bucket
            }).encode('utf-8')
        
        except Exception:
            request.setResponseCode(400)
            return json.dumps({
                'error': 'Failed to create bucket. You may have reached the limit of 3 buckets.'
            }).encode('utf-8')


class BucketDeleteResource(resource.Resource):
    
    isLeaf = True
    
    def __init__(self, auth_manager, bucket_id):
        resource.Resource.__init__(self)
        self.auth_manager = auth_manager
        self.bucket_id = bucket_id
    
    def render_DELETE(self, request):
        request.setHeader(b'content-type', b'application/json')
        
        try:
            token = request.getHeader(b's3-auth-token')
            if not token:
                request.setResponseCode(401)
                return json.dumps({'error': 'Missing authentication token'}).encode('utf-8')
            
            user_info = self.auth_manager.validate_token(token.decode('utf-8'))
            if not user_info:
                request.setResponseCode(401)
                return json.dumps({'error': 'Invalid or expired token'}).encode('utf-8')
            
            bucket_access = self.auth_manager.check_bucket_access(user_info['user_id'], self.bucket_id)
            if not bucket_access:
                request.setResponseCode(403)
                return json.dumps({'error': 'Access denied'}).encode('utf-8')
            
            success = self.auth_manager.delete_bucket(user_info['user_id'], self.bucket_id)
            if success:
                return json.dumps({'success': True}).encode('utf-8')
            else:
                request.setResponseCode(404)
                return json.dumps({'error': 'Bucket not found'}).encode('utf-8')
        except Exception:
            request.setResponseCode(400)
            return json.dumps({'error': 'Failed to delete bucket'}).encode('utf-8')


class S3ProxyResource(resource.Resource):
    
    def __init__(self, auth_manager):
        resource.Resource.__init__(self)
        self.auth_manager = auth_manager
        self.s3_service_url = os.getenv('S3_SERVICE_URL', 'http://s3service:8080')
    
    def getChild(self, path, request):
        return self
    
    def render(self, request):
        token = request.getHeader(b's3-auth-token')
        if not token:
            request.setResponseCode(401)
            request.setHeader(b'content-type', b'application/json')
            return json.dumps({'error': 'Missing authentication token'}).encode('utf-8')
        
        user_info = self.auth_manager.validate_token(token.decode('utf-8'))
        if not user_info:
            request.setResponseCode(401)
            request.setHeader(b'content-type', b'application/json')
            return json.dumps({'error': 'Invalid or expired token'}).encode('utf-8')
        
        bucket_id = request.getHeader(b's3-bucket-id')
        if not bucket_id:
            request.setResponseCode(400)
            request.setHeader(b'content-type', b'application/json')
            return json.dumps({'error': 'Missing bucket ID'}).encode('utf-8')
        
        bucket_access = self.auth_manager.check_bucket_access(
            user_info['user_id'],
            bucket_id.decode('utf-8')
        )
        
        if not bucket_access:
            request.setResponseCode(403)
            request.setHeader(b'content-type', b'application/json')
            return json.dumps({'error': 'Access denied to this bucket'}).encode('utf-8')
        
        self._proxy_to_s3(request)
        return server.NOT_DONE_YET
    
    @defer.inlineCallbacks
    def _proxy_to_s3(self, request):
        try:
            path = request.uri.decode('utf-8')
            if path.startswith('/s3'):
                path = path[3:]
            
            target_url = f"{self.s3_service_url}{path}"
            
            headers = {}
            for key, values in request.requestHeaders.getAllRawHeaders():
                headers[key] = values
            
            response = yield treq.request(
                request.method.decode('utf-8'),
                target_url,
                data=request.content.read(),
                headers=headers
            )
            
            request.setResponseCode(response.code)
            for key, values in response.headers.getAllRawHeaders():
                for value in values:
                    request.setHeader(key, value)
            
            body = yield treq.content(response)
            request.write(body)
            request.finish()
        
        except Exception:
            request.setResponseCode(502)
            request.setHeader(b'content-type', b'application/json')
            request.write(json.dumps({
                'error': 'Failed to communicate with storage service'
            }).encode('utf-8'))
            request.finish()


