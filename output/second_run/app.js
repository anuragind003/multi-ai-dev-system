// app.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { initializeDatabase } = require('./config/database');
const { authMiddleware } = require('./middleware/authMiddleware');
const { errorHandler } = require('./middleware/errorHandler');
const { logger } = require('./utils/logger');
const { taskRoutes } = require('./routes/taskRoutes');
const { userRoutes } = require('./routes/userRoutes');
const { config } = require('./config/config');

const app = express();
const port = config.port || 3000;

// Middleware
app.use(cors()); // Enable CORS for all origins (consider more restrictive settings in production)
app.use(helmet()); // Set security HTTP headers
app.use(express.json()); // Parse JSON request bodies

// Rate limiting - prevent brute-force attacks
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again after 15 minutes',
});
app.use(limiter);

// Initialize database connection
initializeDatabase()
  .then(() => {
    logger.info('Database connected successfully.');
  })
  .catch((err) => {
    logger.error('Database connection failed:', err);
    process.exit(1); // Exit the process if database connection fails
  });

// Routes - Apply authMiddleware to protected routes
app.use('/api/users', userRoutes);
app.use('/api/tasks', authMiddleware, taskRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', message: 'Server is healthy' });
});

// Error handling middleware - MUST be after routes
app.use(errorHandler);

// Start the server
const server = app.listen(port, () => {
  logger.info(`Server listening on port ${port}`);
});

// Handle graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  server.close(() => {
    logger.info('HTTP server closed');
    // Close database connection here if needed
  });
});

module.exports = { app };