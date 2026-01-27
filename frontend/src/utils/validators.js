/**
 * Validate email format
 */
export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(String(email).toLowerCase());
};

/**
 * Validate password strength
 */
export const validatePassword = (password) => {
  const errors = [];
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters');
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }
  
  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

/**
 * Validate required field
 */
export const validateRequired = (value, fieldName = 'Field') => {
  if (value === null || value === undefined || value === '') {
    return { isValid: false, error: `${fieldName} is required` };
  }
  return { isValid: true };
};

/**
 * Validate number
 */
export const validateNumber = (value, min = null, max = null) => {
  const num = Number(value);
  
  if (isNaN(num)) {
    return { isValid: false, error: 'Must be a valid number' };
  }
  
  if (min !== null && num < min) {
    return { isValid: false, error: `Must be at least ${min}` };
  }
  
  if (max !== null && num > max) {
    return { isValid: false, error: `Must be at most ${max}` };
  }
  
  return { isValid: true };
};

/**
 * Validate string length
 */
export const validateLength = (value, min = 0, max = Infinity) => {
  const length = String(value).length;
  
  if (length < min) {
    return { isValid: false, error: `Must be at least ${min} characters` };
  }
  
  if (length > max) {
    return { isValid: false, error: `Must be at most ${max} characters` };
  }
  
  return { isValid: true };
};

/**
 * Validate URL format
 */
export const validateURL = (url) => {
  try {
    new URL(url);
    return { isValid: true };
  } catch (error) {
    return { isValid: false, error: 'Must be a valid URL' };
  }
};

/**
 * Validate JSON string
 */
export const validateJSON = (str) => {
  try {
    JSON.parse(str);
    return { isValid: true };
  } catch (error) {
    return { isValid: false, error: 'Must be valid JSON' };
  }
};

/**
 * Validate API key format
 */
export const validateAPIKey = (key) => {
  if (!key) {
    return { isValid: false, error: 'API key is required' };
  }
  
  if (!key.startsWith('ep_live_')) {
    return { isValid: false, error: 'Invalid API key format' };
  }
  
  if (key.length < 32) {
    return { isValid: false, error: 'API key is too short' };
  }
  
  return { isValid: true };
};

/**
 * Validate form data
 */
export const validateForm = (data, rules) => {
  const errors = {};
  let isValid = true;
  
  Object.keys(rules).forEach((field) => {
    const value = data[field];
    const fieldRules = rules[field];
    
    fieldRules.forEach((rule) => {
      const result = rule.validator(value);
      if (!result.isValid) {
        errors[field] = result.error;
        isValid = false;
      }
    });
  });
  
  return { isValid, errors };
};

export default {
  validateEmail,
  validatePassword,
  validateRequired,
  validateNumber,
  validateLength,
  validateURL,
  validateJSON,
  validateAPIKey,
  validateForm,
};