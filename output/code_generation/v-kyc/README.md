# VKYC Portal - Production Ready System

A secure, internal web portal for L&T Finance VKYC (Video Know Your Customer) team to efficiently search, find, and download V-KYC recordings from an NFS server.

## 🎯 Project Overview

This project replaces the manual process of requesting V-KYC video recordings from the IT team with a self-service portal, empowering authorized VKYC Team Leaders and Process Managers to instantly access necessary recordings for internal and external audit requirements.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   NFS Server    │
│   (React)       │◄──►│   (Node.js)     │◄──►│   (SFTP)        │
│   Port 3000     │    │   Port 3001     │    │   Port 22       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │   (Local)       │
                       └─────────────────┘
```

## 🚀 Features

### ✅ Core Functionality
- **Secure Authentication**: Role-based access control (Team Leader, Process Manager)
- **Recording Search**: Search by LAN ID, date, month, or bulk search via file upload
- **File Downloads**: Single and bulk recording downloads with ZIP compression
- **Audit Logging**: Complete audit trail of all user activities
- **Responsive UI**: Modern, intuitive interface with pagination and real-time feedback

### 🔒 Security Features
- **Input Validation**: All inputs validated and sanitized
- **SQL Injection Prevention**: Parameterized queries
- **CORS Protection**: Configured for specific origins
- **Audit Trail**: Complete logging of user actions
- **Secure File Access**: SFTP connection to NFS server

### 📊 User Stories Implemented
1. ✅ **Secure Login**: Corporate credential authentication
2. ✅ **Date/Month Search**: Search recordings by specific date or month
3. ✅ **Single LAN ID Search**: Quick retrieval of individual recordings
4. ✅ **Bulk Search**: Upload CSV/TXT file with 2-50 LAN IDs
5. ✅ **Results Navigation**: Paginated table with 10 records per page
6. ✅ **Individual Download**: Click-to-download single recordings
7. ✅ **Bulk Download**: Download multiple recordings as ZIP file

## 🛠️ Technology Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Custom hooks** for state management

### Backend
- **Node.js** with Express
- **SQLite** for local database (metadata storage)
- **SFTP Client** for NFS server integration
- **Archiver** for ZIP file creation
- **CORS** for cross-origin requests

### Infrastructure
- **Local SQLite Database** for metadata
- **SFTP Connection** to NFS server for file access
- **Environment-based Configuration**

## 📦 Installation & Setup

### Prerequisites
- Node.js 16+ 
- npm or yarn
- Access to NFS server via SFTP

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd v-kyc
   ```

2. **Setup Backend**:
   ```bash
   cd vkyc-portal-backend
   
   # On Windows
   setup.bat
   
   # On Linux/Mac
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure Environment**:
   ```bash
   # Edit .env file with your SFTP configuration
   nano .env
   ```

4. **Start Backend**:
   ```bash
   npm run dev
   ```

5. **Setup Frontend** (in new terminal):
   ```bash
   cd ..  # Back to project root
   npm install
   npm run dev
   ```

6. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:3001

### Default Users
- **Team Leader**: `leader1` / `password`
- **Process Manager**: `manager1` / `password`

## 🔧 Configuration

### Environment Variables

Create `.env` file in `vkyc-portal-backend/`:

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

## 📋 API Endpoints

### Authentication
- `POST /api/login` - User authentication

### Recordings
- `GET /api/recordings/search` - Search by LAN ID, date, or month
- `POST /api/recordings/search/bulk` - Bulk search by LAN IDs
- `GET /api/recordings/recent` - Get recent recordings
- `GET /api/recordings/download/:lanId` - Download single recording
- `POST /api/recordings/download-bulk` - Download multiple recordings as ZIP

## 🗄️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Team Leader', 'Process Manager')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);
```

### Recordings Table
```sql
CREATE TABLE recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lanId TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL,
    fileName TEXT NOT NULL,
    size TEXT NOT NULL,
    sizeInBytes INTEGER NOT NULL,
    streamUrl TEXT,
    callDuration TEXT NOT NULL,
    status TEXT DEFAULT 'APPROVED',
    time TEXT NOT NULL,
    uploadTime TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 🚀 Production Deployment

### 1. Environment Setup
```bash
NODE_ENV=production
PORT=3001
SFTP_HOST=your-production-nfs-server.com
SFTP_USER=your-production-sftp-user
SFTP_PASSWORD=your-secure-password
SFTP_BASE_PATH=/production/recordings/
JWT_SECRET=your-very-secure-jwt-secret
CORS_ORIGIN=https://your-frontend-domain.com
```

### 2. Process Management
```bash
# Install PM2
npm install -g pm2

# Start backend
cd vkyc-portal-backend
pm2 start index.js --name "vkyc-backend"

# Start frontend
cd ..
pm2 start "npm run dev" --name "vkyc-frontend"

# Save configuration
pm2 save
pm2 startup
```

### 3. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📊 Performance & Monitoring

### Performance Metrics
- **Search Response**: < 5 seconds
- **Download Initiation**: < 3 seconds
- **Concurrent Users**: Supports all authorized users
- **Uptime Target**: 99.5%

### Monitoring
- **Application Logs**: PM2 logs
- **Database Monitoring**: SQLite file size and backup
- **SFTP Connection**: Connection status and file operation logs
- **Audit Trail**: Complete user activity logging

## 🔍 Troubleshooting

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

## 🔐 Security Considerations

1. **Password Security**: In production, implement password hashing (bcrypt)
2. **JWT Tokens**: Implement JWT for session management
3. **HTTPS**: Use SSL/TLS in production
4. **Input Sanitization**: All inputs are validated
5. **Audit Logging**: Complete trail of user activities
6. **Network Security**: SFTP connection over secure channel

## 📈 Future Enhancements

1. **PostgreSQL Migration**: For production scalability
2. **Redis Caching**: For session management and performance
3. **File Streaming**: Direct video streaming capability
4. **Advanced Search**: Full-text search and filters
5. **User Management**: Admin panel for user management
6. **Reporting**: Analytics and usage reports

## 🤝 Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure security best practices

## 📄 License

This project is proprietary to L&T Finance. All rights reserved.

## 📞 Support

For technical support:
1. Check the troubleshooting section
2. Review application logs
3. Verify environment configuration
4. Contact the development team

---

**Built with ❤️ for L&T Finance VKYC Team**
