-- VKYC Portal Database Schema
-- SQLite Database for local development

-- Users table for authentication and role management
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL, -- In production, this should be hashed
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Team Leader', 'Project Manager')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- Recordings table to store metadata about VKYC recordings
CREATE TABLE IF NOT EXISTS recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lanId TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL, -- YYYY-MM-DD format
    fileName TEXT NOT NULL,
    size TEXT NOT NULL, -- e.g., "15.4 MB"
    sizeInBytes INTEGER NOT NULL,
    streamUrl TEXT, -- URL for video streaming (optional)
    callDuration TEXT NOT NULL, -- e.g., "0:05:54"
    status TEXT DEFAULT 'APPROVED',
    time TEXT NOT NULL, -- e.g., "9:54:45 PM"
    uploadTime TEXT NOT NULL, -- YYYY-MM-DD format
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Audit trail table for logging user activities
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL, -- 'LOGIN', 'SEARCH', 'DOWNLOAD_SINGLE', 'DOWNLOAD_BULK'
    details TEXT, -- JSON string with additional details
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_recordings_lanid ON recordings(lanId);
CREATE INDEX IF NOT EXISTS idx_recordings_date ON recordings(date);
CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Insert default users (for development)
INSERT OR IGNORE INTO users (username, password, name, role) VALUES
('leader', 'password1', 'Anurag Kumar', 'Team Leader'),
('manager', 'password2', 'Anil Tyagi', 'Project Manager'); 