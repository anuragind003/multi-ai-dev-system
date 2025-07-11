// middleware/authMiddleware.js
const jwt = require('jsonwebtoken');
const { config } = require('../config/config');
const { logger } = require('../utils/logger');

const authMiddleware = (req, res, next) => {
  // Get token from header
  const token = req.header('Authorization');

  // Check if not token
  if (!token) {
    return res.status(401).json({ message: 'No token, authorization denied' });
  }

  try {
    // Verify token
    const decoded = jwt.verify(token.replace('Bearer ', ''), config.jwtSecret); // Remove 'Bearer ' prefix
    req.user = decoded.user;
    next();
  } catch (err) {
    logger.error('Token is not valid', err);
    res.status(401).json({ message: 'Token is not valid' });
  }
};

module.exports = { authMiddleware };