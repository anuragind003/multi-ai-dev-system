const jwt = require('jsonwebtoken');
const { runQuerySingle } = require('../database/db');

// Middleware to verify JWT token
const authenticateToken = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({ message: 'Access token required' });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    
    // Get user from database to ensure they still exist
    const user = await runQuerySingle(
      'SELECT id, username, name, role FROM users WHERE id = ?',
      [decoded.userId]
    );

    if (!user) {
      return res.status(401).json({ message: 'User not found' });
    }

    req.user = user;
    next();
  } catch (error) {
    return res.status(403).json({ message: 'Invalid or expired token' });
  }
};

// Middleware to check role permissions
const requireRole = (roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ message: 'Authentication required' });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ message: 'Insufficient permissions' });
    }

    next();
  };
};

// Rate limiting middleware
const rateLimit = require('express-rate-limit');

const createRateLimiter = (windowMs, max, message) => {
  return rateLimit({
    windowMs,
    max,
    message: { message },
    standardHeaders: true,
    legacyHeaders: false,
  });
};

// Apply different rate limits for different endpoints
const loginLimiter = createRateLimiter(
  15 * 60 * 1000, // 15 minutes
  5, // 5 attempts
  'Too many login attempts, please try again later'
);

const searchLimiter = createRateLimiter(
  60 * 1000, // 1 minute
  30, // 30 requests
  'Too many search requests, please slow down'
);

const downloadLimiter = createRateLimiter(
  60 * 1000, // 1 minute
  10, // 10 downloads
  'Too many download requests, please slow down'
);

module.exports = {
  authenticateToken,
  requireRole,
  loginLimiter,
  searchLimiter,
  downloadLimiter
}; 