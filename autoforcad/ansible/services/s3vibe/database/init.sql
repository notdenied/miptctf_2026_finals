CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    CONSTRAINT username_length CHECK (char_length(username) >= 3),
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(512) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    ip_address INET,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS buckets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bucket_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    storage_used BIGINT DEFAULT 0,
    max_storage BIGINT DEFAULT 10737418240,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT bucket_name_length CHECK (char_length(name) >= 3 AND char_length(name) <= 63)
);

CREATE TABLE IF NOT EXISTS user_bucket_access (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bucket_id UUID NOT NULL REFERENCES buckets(id) ON DELETE CASCADE,
    permission_level VARCHAR(50) NOT NULL DEFAULT 'read',
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    UNIQUE(user_id, bucket_id),
    CONSTRAINT valid_permission CHECK (permission_level IN ('read', 'write', 'admin'))
);

CREATE TABLE IF NOT EXISTS objects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bucket_id UUID NOT NULL REFERENCES buckets(id) ON DELETE CASCADE,
    object_key VARCHAR(1024) NOT NULL,
    size BIGINT NOT NULL,
    content_type VARCHAR(255),
    etag VARCHAR(255),
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(bucket_id, object_key)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_auth_tokens_token ON auth_tokens(token);
CREATE INDEX idx_auth_tokens_user_id ON auth_tokens(user_id);
CREATE INDEX idx_auth_tokens_expires_at ON auth_tokens(expires_at);
CREATE INDEX idx_buckets_user_id ON buckets(user_id);
CREATE INDEX idx_buckets_bucket_id ON buckets(bucket_id);
CREATE INDEX idx_user_bucket_access_user_id ON user_bucket_access(user_id);
CREATE INDEX idx_user_bucket_access_bucket_id ON user_bucket_access(bucket_id);
CREATE INDEX idx_objects_bucket_id ON objects(bucket_id);
CREATE INDEX idx_objects_object_key ON objects(object_key);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_buckets_updated_at BEFORE UPDATE ON buckets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_objects_updated_at BEFORE UPDATE ON objects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION check_bucket_limit()
RETURNS TRIGGER AS $$
DECLARE
    bucket_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO bucket_count
    FROM buckets
    WHERE user_id = NEW.user_id AND is_active = TRUE;
    
    IF bucket_count >= 3 THEN
        RAISE EXCEPTION 'Maximum 3 buckets per user';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_bucket_limit BEFORE INSERT ON buckets
    FOR EACH ROW EXECUTE FUNCTION check_bucket_limit();

CREATE OR REPLACE FUNCTION update_bucket_storage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE buckets
        SET storage_used = storage_used + NEW.size
        WHERE id = NEW.bucket_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE buckets
        SET storage_used = storage_used - OLD.size
        WHERE id = OLD.bucket_id;
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE buckets
        SET storage_used = storage_used - OLD.size + NEW.size
        WHERE id = NEW.bucket_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_bucket_storage_on_object_change
AFTER INSERT OR UPDATE OR DELETE ON objects
    FOR EACH ROW EXECUTE FUNCTION update_bucket_storage();
