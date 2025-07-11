// models/userModel.js
const { DataTypes } = require('sequelize');
const { getSequelize } = require('../config/database');

const User = getSequelize().define('User', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
  },
  username: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    validate: {
      len: [3, 20], // Example validation
    },
  },
  password: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  email: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    validate: {
      isEmail: true,
    },
  },
  // Add other user-related fields here
}, {
  // Model options
  // timestamps: true, // Enable timestamps (createdAt, updatedAt)
  // Other options like indexes, etc.
});

module.exports = { User };