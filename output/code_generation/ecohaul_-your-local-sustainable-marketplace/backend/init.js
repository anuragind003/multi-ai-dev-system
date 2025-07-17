const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const dbPath = path.resolve(__dirname, 'ecohaul.db');
const schemaPath = path.resolve(__dirname, 'schema.sql');

// Remove existing database file if it exists
if (fs.existsSync(dbPath)) {
  fs.unlinkSync(dbPath);
  console.log('Existing database removed.');
}

const db = new sqlite3.Database(dbPath);
const schema = fs.readFileSync(schemaPath, 'utf8');

db.exec(schema, (err) => {
  if (err) {
    console.error('Error initializing database:', err.message);
    process.exit(1);
  } else {
    console.log('Database initialized successfully.');
    process.exit(0);
  }
}); 