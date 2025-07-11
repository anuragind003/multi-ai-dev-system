// controllers/userController.js
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { User } = require('../models/userModel');
const { config } = require('../config/config');
const { logger } = require('../utils/logger');
const { validationResult } = require('express-validator');

// User registration
const registerUser = async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    const { username, password, email } = req.body;

    // Hash the password
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    const newUser = await User.create({
      username,
      password: hashedPassword,
      email,
    });

    logger.info('User registered successfully', { userId: newUser.id });
    res.status(201).json({ message: 'User registered successfully' });
  } catch (error) {
    logger.error('Error registering user:', error);
    next(error);
  }
};

// User login
const loginUser = async (req, res, next) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    const { username, password } = req.body;

    const user = await User.findOne({ where: { username } });

    if (!user) {
      return res.status(400).json({ message: 'Invalid credentials' });
    }

    const isMatch = await bcrypt.compare(password, user.password);

    if (!isMatch) {
      return res.status(400).json({ message: 'Invalid credentials' });
    }

    // Create and sign a JWT
    const payload = {
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
      },
    };

    jwt.sign(
      payload,
      config.jwtSecret,
      { expiresIn: '1h' }, // Token expiration
      (err, token) => {
        if (err) throw err;
        logger.info('User logged in successfully', { userId: user.id });
        res.json({ token });
      }
    );
  } catch (error) {
    logger.error('Error logging in user:', error);
    next(error);
  }
};

// Get user profile
const getUserProfile = async (req, res, next) => {
  try {
    // req.user is set by authMiddleware
    const user = await User.findByPk(req.user.id, {
      attributes: { exclude: ['password'] }, // Exclude password from the response
    });

    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    res.json(user);
  } catch (error) {
    logger.error('Error getting user profile:', error);
    next(error);
  }
};

module.exports = { registerUser, loginUser, getUserProfile };