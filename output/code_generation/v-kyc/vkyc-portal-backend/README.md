# VKYC Portal Backend

A production-ready backend for the VKYC (Video Know Your Customer) portal that provides secure access to video recordings stored on an NFS server via SFTP.

## Features

- **Secure Authentication**: User login with role-based access control
- **Recording Search**: Search by LAN ID, date, month, or bulk search
- **File Downloads**: Single and bulk recording downloads via SFTP
- **Audit Logging**: Complete audit trail of all user activities
- **SQLite Database**: Local database for metadata storage
- **SFTP Integration**: Secure file access from NFS server

## Technology Stack

- **Backend**: Node.js with Express
- **Database**: SQLite (local development) / PostgreSQL (production)
- **File Access**: SFTP client for NFS server integration
- **Security**: CORS, input validation, audit logging

## Prerequisites

- Node.js 16+ 
- npm or yarn
- Access to NFS server via SFTP

## Installation

1. **Clone and navigate to backend directory**:
   ```bash
   cd vkyc-portal-backend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` with your actual configuration:
   ```env
   # Server Configuration
   PORT=3001
   
   # SFTP Configuration for NFS Server Access
   SFTP_HOST=your-nfs-server.com
   SFTP_PORT=22
   SFTP_USER=your-sftp-username
   SFTP_PASSWORD=your-sftp-password
   SFTP_BASE_PATH=/path/to/recordings/
   
   # Security Configuration
   JWT_SECRET=your-super-secret-jwt-key-here
   SESSION_SECRET=your-session-secret-key
   
   # CORS Configuration
   CORS_ORIGIN=http://localhost:3000
   
   # Logging Configuration
   LOG_LEVEL=info
   ```

4. **Initialize the database**:
   ```bash
   npm run init-db
   ```

5. **Start the development server**:
   ```bash
   npm run dev
   ```

## API Endpoints

### Authentication
- `POST /api/login` - User authentication

### Recordings
- `GET /api/recordings/search` - Search by LAN ID, date, or month
- `POST /api/recordings/search/bulk` - Bulk search by LAN IDs
- `GET /api/recordings/recent` - Get recent recordings
- `GET /api/recordings/download/:lanId` - Download single recording
- `POST /api/recordings/download-bulk` - Download multiple recordings as ZIP

## Database Schema

### Users Table
- `id` - Primary key
- `username` - Unique username
- `password` - Hashed password
- `name` - Full name
- `role` - Team Leader or Process Manager
- `created_at` - Account creation timestamp
- `last_login` - Last login timestamp

### Recordings Table
- `id` - Primary key
- `lanId` - Unique LAN ID
- `date` - Recording date (YYYY-MM-DD)
- `fileName` - File name on NFS server
- `size` - File size (e.g., "15.4 MB")
- `sizeInBytes` - File size in bytes
- `streamUrl` - Optional streaming URL
- `callDuration` - Call duration (HH:MM:SS)
- `status` - Recording status
- `time` - Recording time
- `uploadTime` - Upload timestamp

### Audit Logs Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `action` - Action performed
- `details` - JSON details of the action
- `ip_address` - User's IP address
- `user_agent` - User's browser info
- `created_at` - Timestamp

## Security Features

1. **Input Validation**: All inputs are validated and sanitized
2. **SQL Injection Prevention**: Parameterized queries
3. **Audit Logging**: Complete trail of user activities
4. **CORS Protection**: Configured for specific origins
5. **Error Handling**: Secure error messages without exposing internals

## Production Deployment

### 1. Environment Setup
```bash
# Set production environment variables
NODE_ENV=production
PORT=3001
SFTP_HOST=your-production-nfs-server.com
SFTP_USER=your-production-sftp-user
SFTP_PASSWORD=your-secure-password
SFTP_BASE_PATH=/production/recordings/
JWT_SECRET=your-very-secure-jwt-secret
CORS_ORIGIN=https://your-frontend-domain.com
```

### 2. Database Setup
For production, consider using PostgreSQL instead of SQLite:

```bash
# Install PostgreSQL dependencies
npm install pg

# Update database connection in database/db.js
```

### 3. Process Management
Use PM2 for process management:

```bash
# Install PM2
npm install -g pm2

# Start the application
pm2 start index.js --name "vkyc-backend"

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
```

### 4. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 5. SSL/TLS Setup
Use Let's Encrypt for free SSL certificates:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## Monitoring and Logging

### 1. Application Logs
```bash
# View PM2 logs
pm2 logs vkyc-backend

# View real-time logs
pm2 logs vkyc-backend --lines 100
```

### 2. Database Monitoring
```bash
# Check database size
ls -lh database/vkyc.db

# Backup database
cp database/vkyc.db database/backup/vkyc_$(date +%Y%m%d_%H%M%S).db
```

### 3. SFTP Connection Monitoring
The application logs all SFTP connection attempts and file operations. Monitor these logs for any connection issues.

## Troubleshooting

### Common Issues

1. **SFTP Connection Failed**
   - Verify SFTP credentials in `.env`
   - Check network connectivity to NFS server
   - Ensure SFTP port is open

2. **Database Errors**
   - Check database file permissions
   - Verify database schema is properly initialized
   - Check for disk space issues

3. **CORS Errors**
   - Verify CORS_ORIGIN setting matches frontend URL
   - Check if frontend is running on correct port

4. **File Download Issues**
   - Verify SFTP_BASE_PATH is correct
   - Check if files exist on NFS server
   - Monitor SFTP connection logs

### Performance Optimization

1. **Database Indexing**: Indexes are automatically created on frequently queried columns
2. **Connection Pooling**: SFTP connections are managed efficiently
3. **File Streaming**: Large files are streamed directly without loading into memory
4. **Caching**: Consider implementing Redis for session management in production

## Development

### Running Tests
```bash
npm test
```

### Code Quality
```bash
# Install ESLint
npm install -g eslint

# Run linting
eslint *.js database/*.js
```

### Database Migrations
For schema changes, create migration scripts in the `database/migrations/` directory.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Verify environment configuration
4. Contact the development team

## License

This project is proprietary to L&T Finance. All rights reserved. 