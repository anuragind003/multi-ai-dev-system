// middleware/errorMiddleware.js
const { logger } = require('../utils/logger');

const errorHandler = (err, req, res, next) => {
  const statusCode = res.statusCode === 200 ? 500 : res.statusCode; // Default to 500 if no status code is set
  res.status(statusCode);
  logger.error(
    `${statusCode} - ${err.message} - ${req.originalUrl} - ${req.method} - ${err.stack}`
  ); // Log the full error stack
  res.json({
    message: err.message,
    stack: process.env.NODE_ENV === 'production' ? '🥞' : err.stack, // Don't expose stack trace in production
  });
};

module.exports = { errorHandler };