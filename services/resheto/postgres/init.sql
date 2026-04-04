-- Resheto: SCP Foundation Containment Database

CREATE TABLE IF NOT EXISTS staff (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(128) NOT NULL,
    clearance_level INT NOT NULL DEFAULT 1 CHECK (clearance_level BETWEEN 1 AND 5),
    department VARCHAR(64) DEFAULT 'General',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    scp_id VARCHAR(64) UNIQUE NOT NULL,
    object_class VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    containment_procedures TEXT NOT NULL,
    min_clearance INT NOT NULL DEFAULT 1,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    created_by INT REFERENCES staff(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    title VARCHAR(256) NOT NULL,
    content_markdown TEXT NOT NULL,
    pdf_path VARCHAR(512),
    author_id INT REFERENCES staff(id),
    anomaly_id INT REFERENCES anomalies(id),
    classification VARCHAR(32) DEFAULT 'CONFIDENTIAL',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS research_tasks (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    anomaly_id INT REFERENCES anomalies(id),
    researcher_id INT REFERENCES staff(id),
    status VARCHAR(16) DEFAULT 'PENDING',
    researcher_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_archive (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    task_id INT REFERENCES research_tasks(id),
    researcher_id INT REFERENCES staff(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS incident_logs (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    anomaly_id INT REFERENCES anomalies(id),
    reporter_id INT REFERENCES staff(id),
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    description TEXT NOT NULL,
    response_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_anomalies_clearance ON anomalies(min_clearance);
CREATE INDEX IF NOT EXISTS idx_anomalies_private ON anomalies(is_private);
CREATE INDEX IF NOT EXISTS idx_anomalies_created_by ON anomalies(created_by);
CREATE INDEX IF NOT EXISTS idx_reports_author ON reports(author_id);
CREATE INDEX IF NOT EXISTS idx_research_status ON research_tasks(status);
CREATE INDEX IF NOT EXISTS idx_research_researcher ON research_tasks(researcher_id);
CREATE INDEX IF NOT EXISTS idx_archive_researcher ON research_archive(researcher_id);
CREATE INDEX IF NOT EXISTS idx_incidents_anomaly ON incident_logs(anomaly_id);
