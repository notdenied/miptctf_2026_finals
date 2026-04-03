import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from .models import User, AuthToken, Bucket, UserBucketAccess, Object


class AuthManager:
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.secret_key = os.getenv('SECRET_KEY')
        if not self.secret_key:
            import secrets
            self.secret_key = secrets.token_urlsafe(64)
        self.token_expiry_hours = 24
        self.s3_url = os.getenv('S3_SERVICE_URL', 'http://s3service:8080')
    
    def hash_password(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password, password_hash):
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def register_user(self, username, email, password):
        password_hash = self.hash_password(password)
        user_id = None
        username_val = username
        email_val = email
        
        with self.db_pool.get_session() as session:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash
            )
            session.add(user)
            session.flush()
            user_id = user.id
            username_val = user.username
            email_val = user.email
        
        return {
            'id': str(user_id),
            'username': username_val,
            'email': email_val,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    def authenticate_user(self, username, password, ip_address=None, user_agent=None):
        with self.db_pool.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            
            if not user:
                return None
            
            if not user.is_active:
                return None
            
            if not self.verify_password(password, user.password_hash):
                return None
            
            token = self._create_token_in_session(session, user.id, user.username, ip_address, user_agent)
            
            user.last_login = datetime.now(timezone.utc)
            session.flush()
            
            return {
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email,
                'token': token
            }
    
    def _create_token_in_session(self, session, user_id, username, ip_address=None, user_agent=None):
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours)
        
        payload = {
            'user_id': str(user_id),
            'username': username,
            'exp': expires_at,
            'iat': datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        auth_token = AuthToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        session.add(auth_token)
        session.flush()
        
        return token
    
    def _create_token(self, user_id, username, ip_address=None, user_agent=None):
        with self.db_pool.get_session() as session:
            return self._create_token_in_session(session, user_id, username, ip_address, user_agent)
    
    def validate_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            with self.db_pool.get_session() as session:
                auth_token = session.query(AuthToken).filter(AuthToken.token == token).first()
                
                if not auth_token:
                    return None
                
                if auth_token.is_revoked:
                    return None
                
                if auth_token.expires_at < datetime.now(timezone.utc):
                    return None
                
                return {
                    'user_id': str(auth_token.user_id),
                    'username': payload.get('username')
                }
        
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
    
    def check_bucket_access(self, user_id, bucket_id):
        with self.db_pool.get_session() as session:
            bucket = session.query(Bucket).outerjoin(
                UserBucketAccess,
                and_(
                    Bucket.id == UserBucketAccess.bucket_id,
                    UserBucketAccess.user_id == user_id
                )
            ).filter(
                and_(
                    Bucket.bucket_id == bucket_id,
                    Bucket.is_active == True,
                    or_(
                        Bucket.user_id == user_id,
                        UserBucketAccess.user_id == user_id
                    )
                )
            ).first()
            
            if bucket:
                permission = None
                for access in bucket.user_accesses:
                    if str(access.user_id) == user_id:
                        permission = access.permission_level
                        break
                
                return {
                    'bucket_id': bucket.bucket_id,
                    'name': bucket.name,
                    'permission': permission or 'admin'
                }
            
            return None
    
    def get_user_buckets(self, user_id):
        with self.db_pool.get_session() as session:
            buckets = session.query(Bucket).outerjoin(
                UserBucketAccess,
                Bucket.id == UserBucketAccess.bucket_id
            ).filter(
                and_(
                    or_(
                        Bucket.user_id == user_id,
                        UserBucketAccess.user_id == user_id
                    ),
                    Bucket.is_active == True
                )
            ).order_by(Bucket.created_at.desc()).all()
            
            result = []
            seen_ids = set()
            for bucket in buckets:
                if bucket.id not in seen_ids:
                    seen_ids.add(bucket.id)
                    result.append({
                        'bucket_id': bucket.bucket_id,
                        'name': bucket.name,
                        'description': bucket.description,
                        'storage_used': bucket.storage_used,
                        'max_storage': bucket.max_storage,
                        'created_at': bucket.created_at.isoformat()
                    })
            
            return result
    
    def create_bucket(self, user_id, name, description=None):
        bucket_id = f"bucket-{uuid4().hex[:16]}"
        
        with self.db_pool.get_session() as session:
            bucket = Bucket(
                bucket_id=bucket_id,
                user_id=user_id,
                name=name,
                description=description
            )
            session.add(bucket)
            session.flush()
            
            access = UserBucketAccess(
                user_id=user_id,
                bucket_id=bucket.id,
                permission_level='admin',
                granted_by=user_id
            )
            session.add(access)
            session.flush()
            
            return {
                'bucket_id': bucket.bucket_id,
                'name': bucket.name,
                'created_at': bucket.created_at.isoformat()
            }
    
    def delete_bucket(self, user_id, bucket_id):
        import requests
        
        with self.db_pool.get_session() as session:
            bucket = session.query(Bucket).filter(
                and_(
                    Bucket.bucket_id == bucket_id,
                    Bucket.user_id == user_id
                )
            ).first()
            
            if not bucket:
                return False
            
            session.query(Object).filter(
                Object.bucket_id == bucket.id
            ).update({
                'is_deleted': True,
                'updated_at': datetime.now(timezone.utc)
            })
            
            session.query(UserBucketAccess).filter(
                UserBucketAccess.bucket_id == bucket.id
            ).delete()
            
            bucket.is_active = False
            bucket.updated_at = datetime.now(timezone.utc)
            
            session.flush()
        
        try:
            requests.delete(
                f"{self.s3_url}/bucket",
                headers={'s3-bucket-id': bucket_id},
                timeout=5
            )
        except:
            pass
        
        return True
