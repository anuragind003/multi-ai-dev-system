const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// Database file path
const dbPath = path.join(__dirname, 'vkyc.db');

// Remove existing database file if it exists
if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
    console.log('Removed existing database file');
}

// Create new database
const db = new sqlite3.Database(dbPath);

// Read and execute schema
const schema = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');

db.serialize(() => {
    console.log('Creating database tables...');
    
    // Execute schema
    db.exec(schema, (err) => {
        if (err) {
            console.error('Error creating tables:', err);
            return;
        }
        console.log('Database tables created successfully');
        
        // Insert sample recordings data
        insertSampleRecordings();
    });
});

function insertSampleRecordings() {
    console.log('Inserting sample recordings...');
    
    const recordings = [];
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 2); // Go back 2 months

    for (let i = 0; i < 50; i++) {
        const date = new Date(startDate.getTime() + (i * 24 * 3600 * 1000) / 2); // Advance half a day
        
        const pad = (num) => num.toString().padStart(2, '0');
        const dateStr = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
        const timeStr = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
        
        const lanId = `LTF100${pad(i)}`;
        const sizeInBytes = Math.floor(Math.random() * (50 * 1024 * 1024)) + (5 * 1024 * 1024); // 5MB to 50MB
        const size = `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`;
        const durationSeconds = Math.floor(Math.random() * 540) + 60; // 1 to 10 minutes
        const callDuration = new Date(durationSeconds * 1000).toISOString().substr(11, 8);
        
        recordings.push({
            lanId: lanId,
            date: dateStr,
            fileName: `${lanId}_${dateStr}.mp4`,
            size: size,
            sizeInBytes: sizeInBytes,
            streamUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
            callDuration: callDuration,
            status: 'APPROVED',
            time: timeStr,
            uploadTime: dateStr
        });
    }

    // Sort by date and time (newest first)
    recordings.sort((a, b) => new Date(b.date + ' ' + b.time).getTime() - new Date(a.date + ' ' + a.time).getTime());

    const stmt = db.prepare(`
        INSERT INTO recordings (lanId, date, fileName, size, sizeInBytes, streamUrl, callDuration, status, time, uploadTime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    recordings.forEach(recording => {
        stmt.run([
            recording.lanId,
            recording.date,
            recording.fileName,
            recording.size,
            recording.sizeInBytes,
            recording.streamUrl,
            recording.callDuration,
            recording.status,
            recording.time,
            recording.uploadTime
        ]);
    });

    stmt.finalize((err) => {
        if (err) {
            console.error('Error inserting sample recordings:', err);
        } else {
            console.log(`Successfully inserted ${recordings.length} sample recordings`);
            console.log('Database initialization completed successfully!');
        }
        db.close();
    });
} 