from sqlalchemy import Column, String, Boolean, DateTime, BigInteger, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))
    
    tokens = relationship('AuthToken', back_populates='user', cascade='all, delete-orphan')
    buckets = relationship('Bucket', back_populates='owner', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('char_length(username) >= 3', name='username_length'),
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", name='email_format'),
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
    )


class AuthToken(Base):
    __tablename__ = 'auth_tokens'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(512), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    user = relationship('User', back_populates='tokens')
    
    __table_args__ = (
        Index('idx_auth_tokens_token', 'token'),
        Index('idx_auth_tokens_user_id', 'user_id'),
        Index('idx_auth_tokens_expires_at', 'expires_at'),
    )


class Bucket(Base):
    __tablename__ = 'buckets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    storage_used = Column(BigInteger, default=0)
    max_storage = Column(BigInteger, default=10737418240)
    is_active = Column(Boolean, default=True)
    
    owner = relationship('User', back_populates='buckets')
    objects = relationship('Object', back_populates='bucket', cascade='all, delete-orphan')
    user_accesses = relationship('UserBucketAccess', back_populates='bucket', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('char_length(name) >= 3 AND char_length(name) <= 63', name='bucket_name_length'),
        Index('idx_buckets_user_id', 'user_id'),
        Index('idx_buckets_bucket_id', 'bucket_id'),
    )


class UserBucketAccess(Base):
    __tablename__ = 'user_bucket_access'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    bucket_id = Column(UUID(as_uuid=True), ForeignKey('buckets.id', ondelete='CASCADE'), nullable=False)
    permission_level = Column(String(50), nullable=False, default='read')
    granted_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    
    user = relationship('User', foreign_keys=[user_id])
    bucket = relationship('Bucket', back_populates='user_accesses')
    granter = relationship('User', foreign_keys=[granted_by])
    
    __table_args__ = (
        CheckConstraint("permission_level IN ('read', 'write', 'admin')", name='valid_permission'),
        Index('idx_user_bucket_access_user_id', 'user_id'),
        Index('idx_user_bucket_access_bucket_id', 'bucket_id'),
    )


class Object(Base):
    __tablename__ = 'objects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket_id = Column(UUID(as_uuid=True), ForeignKey('buckets.id', ondelete='CASCADE'), nullable=False)
    object_key = Column(String(1024), nullable=False)
    size = Column(BigInteger, nullable=False)
    content_type = Column(String(255))
    etag = Column(String(255))
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())
    object_metadata = Column('metadata', JSONB)
    is_deleted = Column(Boolean, default=False)
    
    bucket = relationship('Bucket', back_populates='objects')
    uploader = relationship('User', foreign_keys=[uploaded_by])
    
    __table_args__ = (
        Index('idx_objects_bucket_id', 'bucket_id'),
        Index('idx_objects_object_key', 'object_key'),
    )

