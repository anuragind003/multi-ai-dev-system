const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Database file path
const dbPath = path.join(__dirname, 'vkyc.db');

// Create database connection
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        console.log('Connected to SQLite database');
    }
});

// Enable foreign keys
db.run('PRAGMA foreign_keys = ON');

// Helper function to run queries with promises
function runQuery(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => {
            if (err) {
                reject(err);
            } else {
                resolve(rows);
            }
        });
    });
}

// Helper function to run single row queries
function runQuerySingle(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.get(sql, params, (err, row) => {
            if (err) {
                reject(err);
            } else {
                resolve(row);
            }
        });
    });
}

// Helper function to run insert/update/delete queries
function runQueryExecute(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.run(sql, params, function(err) {
            if (err) {
                reject(err);
            } else {
                resolve({ id: this.lastID, changes: this.changes });
            }
        });
    });
}

// Audit logging function
async function logAuditAction(userId, action, details = null, ipAddress = null, userAgent = null) {
    try {
        await runQueryExecute(
            'INSERT INTO audit_logs (user_id, action, details, ip_address, user_agent) VALUES (?, ?, ?, ?, ?)',
            [userId, action, details ? JSON.stringify(details) : null, ipAddress, userAgent]
        );
    } catch (error) {
        console.error('Error logging audit action:', error);
    }
}

module.exports = {
    db,
    runQuery,
    runQuerySingle,
    runQueryExecute,
    logAuditAction
}; 