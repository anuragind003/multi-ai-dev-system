/**
 * @file General utility functions for the frontend application.
 * This file contains helpers for date formatting, input validation, and other common tasks.
 */

/**
 * Formats a date string into a human-readable format.
 * If the dateString is null, undefined, or invalid, it returns a default message.
 *
 * @param {string | null | undefined} dateString - The date string to format (e.g., "2023-10-27T10:00:00Z").
 * @returns {string} The formatted date string (e.g., "Oct 27, 2023") or "No due date" if invalid/missing.
 */
export const formatDate = (dateString) => {
  if (!dateString) {
    return "No due date";
  }

  const date = new Date(dateString);

  // Check if the date is valid after parsing. getTime() returns NaN for invalid dates.
  if (isNaN(date.getTime())) {
    return "Invalid Date";
  }

  // Options for formatting: e.g., "Oct 27, 2023"
  const options = { year: 'numeric', month: 'short', day: 'numeric' };
  // toLocaleDateString uses the user's default locale for formatting.
  return date.toLocaleDateString(undefined, options);
};

/**
 * Validates if a given string is a valid email format.
 * Uses a common regular expression for email validation. This regex is a balance
 * between strictness and allowing common valid email formats.
 *
 * @param {string} email - The email string to validate.
 * @returns {boolean} True if the email is valid, false otherwise.
 */
export const isValidEmail = (email) => {
  // Ensure the input is a string before attempting regex test.
  if (typeof email !== 'string') {
    return false;
  }
  // Regex explanation:
  // ^[^\s@]+ : Matches one or more characters that are not whitespace or '@' at the beginning.
  // @       : Matches the '@' symbol.
  // [^\s@]+ : Matches one or more characters that are not whitespace or '@' (domain name part).
  // \.      : Matches a literal dot.
  // [^\s@]{2,6}$ : Matches 2 to 6 characters that are not whitespace or '@' at the end (top-level domain).
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,6}$/;
  return emailRegex.test(email);
};

/**
 * Validates if a given password meets the minimum security requirements.
 * Current requirements:
 * - Minimum length of 8 characters.
 * - Contains at least one uppercase letter.
 * - Contains at least one lowercase letter.
 * - Contains at least one number.
 * - Contains at least one special character (from a predefined set).
 *
 * @param {string} password - The password string to validate.
 * @returns {boolean} True if the password is valid, false otherwise.
 */
export const isValidPassword = (password) => {
  // Ensure the input is a string.
  if (typeof password !== 'string') {
    return false;
  }

  // 1. Minimum length check
  if (password.length < 8) {
    return false;
  }

  // 2. Check for at least one uppercase letter using a regex.
  if (!/[A-Z]/.test(password)) {
    return false;
  }

  // 3. Check for at least one lowercase letter using a regex.
  if (!/[a-z]/.test(password)) {
    return false;
  }

  // 4. Check for at least one number using a regex.
  if (!/[0-9]/.test(password)) {
    return false;
  }

  // 5. Check for at least one special character.
  // The regex matches any character within the specified set.
  const specialCharRegex = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/;
  if (!specialCharRegex.test(password)) {
    return false;
  }

  // If all checks pass, the password is considered valid.
  return true;
};

/**
 * Checks if a given value is considered "empty".
 * A value is empty if it is:
 * - null
 * - undefined
 * - an empty string ("")
 * - a string containing only whitespace characters ("   ")
 *
 * @param {string | null | undefined} value - The value to check.
 * @returns {boolean} True if the value is empty, false otherwise.
 */
export const isEmpty = (value) => {
  // Handle null or undefined values directly.
  if (value === null || typeof value === 'undefined') {
    return true;
  }
  // If it's a string, trim whitespace and check if it's empty.
  if (typeof value === 'string') {
    return value.trim() === '';
  }
  // For other types (e.g., numbers, booleans, objects), they are generally not considered empty
  // by this helper unless explicitly handled.
  return false;
};

/**
 * Capitalizes the first letter of a given string.
 * Returns an empty string if the input is not a string or is empty.
 *
 * @param {string} str - The input string.
 * @returns {string} The string with its first letter capitalized, or an empty string.
 */
export const capitalizeFirstLetter = (str) => {
  // Ensure the input is a non-empty string.
  if (typeof str !== 'string' || str.length === 0) {
    return '';
  }
  // Get the first character and convert it to uppercase, then concatenate with the rest of the string.
  return str.charAt(0).toUpperCase() + str.slice(1);
};