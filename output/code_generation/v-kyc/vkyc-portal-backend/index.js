require('dotenv').config();
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const SftpClient = require('ssh2-sftp-client');
const archiver = require('archiver');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const helmet = require('helmet');
const compression = require('compression');
const { runQuery, runQuerySingle, runQueryExecute, logAuditAction } = require('./database/db');
const { authenticateToken, requireRole, loginLimiter, searchLimiter, downloadLimiter } = require('./middleware/auth');
const { validate, loginSchema, searchSchema, bulkSearchSchema, downloadSchema } = require('./utils/validation');
const https = require('https');

const app = express();

// Security middleware
app.use(helmet());
app.use(compression());
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3002',
  credentials: true
}));
app.use(bodyParser.json());

// --- SFTP Configuration ---
const sftpConfig = {
  host: process.env.SFTP_HOST || 'localhost',
  port: process.env.SFTP_PORT || 22,
  username: process.env.SFTP_USER || 'sftpuser',
  password: process.env.SFTP_PASSWORD || 'password',
};

// --- JWT Configuration ---
const JWT_SECRET = process.env.JWT_SECRET || 'your-super-secret-jwt-key-here';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';

// --- API Endpoints ---
app.post('/api/login', loginLimiter, validate(loginSchema), async (req, res) => {
  const { username, password } = req.body;

  try {
    // Get user from database
    const user = await runQuerySingle(
      'SELECT id, username, name, role, password FROM users WHERE username = ?',
      [username]
    );

    if (!user) {
      return res.status(401).json({ message: 'Invalid credentials.' });
    }

    // In production, compare hashed passwords
    // For now, we'll use plain text comparison (update this in production)
    const isValidPassword = password === user.password; // Replace with bcrypt.compare(password, user.password)

    if (!isValidPassword) {
      return res.status(401).json({ message: 'Invalid credentials.' });
    }

    // Generate JWT token
    const token = jwt.sign(
      { 
        userId: user.id, 
        username: user.username, 
        role: user.role 
      },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES_IN }
    );

    // Update last login time
    await runQueryExecute(
      'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
      [user.id]
    );

    // Log the login action
    await logAuditAction(user.id, 'LOGIN', { username }, req.ip, req.get('User-Agent'));

    // Return user data and token (without password)
    res.json({
      user: {
        id: user.id,
        name: user.name,
        role: user.role
      },
      token,
      expiresIn: JWT_EXPIRES_IN
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Protected route example - verify token
app.get('/api/verify-token', authenticateToken, (req, res) => {
  res.json({ 
    message: 'Token is valid', 
    user: req.user 
  });
});

// GET for single LAN ID, date, or month (with authentication)
app.get('/api/recordings/search', authenticateToken, searchLimiter, async (req, res) => {
    const { lanId, date, month } = req.query;
    let query = 'SELECT * FROM recordings';
    const params = [];

    if (lanId) {
        query += ' WHERE lanId LIKE ?';
        params.push(`%${lanId}%`);
    } else if (date) {
        query += ' WHERE date = ?';
        params.push(date);
    } else if (month) {
        query += " WHERE strftime('%Y-%m', date) = ?";
        params.push(month);
    } else {
        return res.json([]);
    }
    
    query += ' ORDER BY date DESC, time DESC';

    try {
        const rows = await runQuery(query, params);
        
        // Log search action
        await logAuditAction(req.user.id, 'SEARCH', { 
          query: req.query, 
          resultsCount: rows.length 
        }, req.ip, req.get('User-Agent'));
        
        res.json(rows);
    } catch (error) {
        console.error('Search error:', error);
        res.status(500).json({ message: 'Error searching recordings' });
    }
});

// POST for bulk search (with authentication)
app.post('/api/recordings/search/bulk', authenticateToken, searchLimiter, validate(bulkSearchSchema), async (req, res) => {
    const { lanIds } = req.body;

    try {
        // Create placeholders for the IN clause
        const placeholders = lanIds.map(() => '?').join(',');
        const query = `SELECT * FROM recordings WHERE lanId IN (${placeholders}) ORDER BY date DESC, time DESC`;
        
        const rows = await runQuery(query, lanIds);
        
        // Log bulk search action
        await logAuditAction(req.user.id, 'BULK_SEARCH', { 
          lanIdsCount: lanIds.length, 
          resultsCount: rows.length 
        }, req.ip, req.get('User-Agent'));
        
        res.json(rows);
    } catch (error) {
        console.error('Bulk search error:', error);
        res.status(500).json({ message: 'Error performing bulk search' });
    }
});

// GET for recent recordings (with authentication)
app.get('/api/recordings/recent', authenticateToken, async (req, res) => {
    try {
        const rows = await runQuery(
          'SELECT * FROM recordings ORDER BY date DESC, time DESC'
        );
        res.json(rows);
    } catch (error) {
        console.error('Recent recordings error:', error);
        res.status(500).json({ message: 'Error fetching recent recordings' });
    }
});

const fetchWithTimeout = (url, timeoutMs = 10000) => {
  const https = require('https');
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Request timed out'));
    }, timeoutMs);
    const req = https.get(url, (res) => {
      clearTimeout(timer);
      resolve(res);
    });
    req.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
};

// Download single recording (with authentication)
app.get('/api/recordings/download/:lanId', authenticateToken, downloadLimiter, async (req, res) => {
  const { lanId } = req.params;
  try {
    // 1. Get file metadata from the database
    const recording = await runQuerySingle('SELECT fileName, streamUrl FROM recordings WHERE lanId = ?', [lanId]);
    if (!recording) {
      return res.status(404).send('Recording not found.');
    }
    const { fileName, streamUrl } = recording;

    // 2. Proxy the mock video with timeout
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.setHeader('Content-Type', 'video/mp4');
    try {
      const videoRes = await fetchWithTimeout(streamUrl, 10000);
      videoRes.pipe(res);
    } catch (err) {
      console.error('Mock video proxy error:', err);
      res.status(504).send('Failed to download mock video (timeout or error).');
    }

    // Log download action
    await logAuditAction(req.user.id, 'DOWNLOAD_SINGLE', { 
      lanId, 
      fileName, 
      mock: true 
    }, req.ip, req.get('User-Agent'));

  } catch (error) {
    console.error('Download error:', error);
    res.status(500).send('Failed to download file.');
  }
});

// Bulk download (with authentication)
app.post('/api/recordings/download-bulk', authenticateToken, downloadLimiter, validate(downloadSchema), async (req, res) => {
  const { lanIds } = req.body;
  const archiver = require('archiver');

  try {
    // Get file metadata for all requested LAN IDs
    const placeholders = lanIds.map(() => '?').join(',');
    const query = `SELECT fileName, streamUrl FROM recordings WHERE lanId IN (${placeholders})`;
    const rows = await runQuery(query, lanIds);

    if (rows.length === 0) {
      return res.status(404).send('No recordings found for the given IDs.');
    }

    const zipFileName = `VKYC_Recordings_${new Date().toISOString().split('T')[0]}.zip`;
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="${zipFileName}"`);

    const archive = archiver('zip', { zlib: { level: 9 } });
    archive.pipe(res);

    // Fetch all mock videos in parallel with timeout
    const fetchPromises = rows.map(({ fileName, streamUrl }) => {
      return fetchWithTimeout(streamUrl, 10000)
        .then((videoRes) => ({ fileName, videoRes }))
        .catch((err) => ({ fileName, error: err }));
    });
    const results = await Promise.all(fetchPromises);

    for (const result of results) {
      if (result.videoRes) {
        archive.append(result.videoRes, { name: result.fileName });
      } else {
        archive.append(`Failed to fetch mock video for ${result.fileName}: ${result.error && result.error.message}`, { name: `ERROR_${result.fileName}.txt` });
      }
    }

    await archive.finalize();

    // Log bulk download action
    await logAuditAction(req.user.id, 'DOWNLOAD_BULK', { 
      lanIdsCount: lanIds.length, 
      filesCount: rows.length, 
      mock: true 
    }, req.ip, req.get('User-Agent'));

  } catch (error) {
    console.error('Bulk download error:', error);
    res.status(500).send('Failed to create ZIP archive.');
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Backend server running on http://localhost:${PORT}`);
  console.log('JWT authentication enabled');
}); 