const Joi = require('joi');

// Validation schemas
const loginSchema = Joi.object({
  username: Joi.string().alphanum().min(3).max(30).required(),
  password: Joi.string().min(6).required()
});

const searchSchema = Joi.object({
  lanId: Joi.string().pattern(/^[A-Z0-9]+$/).max(20),
  date: Joi.string().pattern(/^\d{4}-\d{2}-\d{2}$/),
  month: Joi.string().pattern(/^\d{4}-\d{2}$/),
  startDate: Joi.string().pattern(/^\d{4}-\d{2}-\d{2}$/),
  endDate: Joi.string().pattern(/^\d{4}-\d{2}-\d{2}$/),
  status: Joi.string().valid('APPROVED', 'PENDING', 'REJECTED'),
  fileSize: Joi.string().valid('small', 'medium', 'large')
});

const bulkSearchSchema = Joi.object({
  lanIds: Joi.array().items(
    Joi.string().pattern(/^[A-Z0-9]+$/).max(20)
  ).min(1).max(50).required()
});

const downloadSchema = Joi.object({
  lanIds: Joi.array().items(
    Joi.string().pattern(/^[A-Z0-9]+$/).max(20)
  ).min(1).max(50).required()
});

// Validation middleware
const validate = (schema) => {
  return (req, res, next) => {
    const { error } = schema.validate(req.body);
    if (error) {
      return res.status(400).json({
        message: 'Validation error',
        details: error.details.map(detail => detail.message)
      });
    }
    next();
  };
};

// Sanitize input
const sanitizeInput = (input) => {
  if (typeof input === 'string') {
    return input
      .trim()
      .replace(/[<>]/g, '') // Remove potential HTML tags
      .replace(/[&]/g, '&amp;') // Escape ampersands
      .replace(/["]/g, '&quot;') // Escape quotes
      .replace(/[']/g, '&#x27;'); // Escape apostrophes
  }
  return input;
};

// Validate LAN ID format
const isValidLanId = (lanId) => {
  const lanIdPattern = /^[A-Z0-9]+$/;
  return lanIdPattern.test(lanId) && lanId.length <= 20;
};

// Validate date format
const isValidDate = (dateString) => {
  const datePattern = /^\d{4}-\d{2}-\d{2}$/;
  if (!datePattern.test(dateString)) return false;
  
  const date = new Date(dateString);
  return date instanceof Date && !isNaN(date);
};

// Validate file size
const isValidFileSize = (size) => {
  const validSizes = ['small', 'medium', 'large'];
  return validSizes.includes(size);
};

// Validate status
const isValidStatus = (status) => {
  const validStatuses = ['APPROVED', 'PENDING', 'REJECTED'];
  return validStatuses.includes(status);
};

module.exports = {
  loginSchema,
  searchSchema,
  bulkSearchSchema,
  downloadSchema,
  validate,
  sanitizeInput,
  isValidLanId,
  isValidDate,
  isValidFileSize,
  isValidStatus
}; 