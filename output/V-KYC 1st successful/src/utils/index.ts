// --- Types ---
export interface User {
  id: string;
  username: string;
  email: string;
}

export interface AuthResponse {
  token: string;
  userId: string;
  username: string;
  email: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  email: string;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (userData: User, token: string) => void;
  logout: () => void;
}

export interface AppContextType {
  appLoading: boolean;
  showLoading: () => void;
  hideLoading: () => void;
  appError: string | null;
  showError: (message: string) => void;
  clearError: () => void;
  notification: string | null;
  showNotification: (message: string, duration?: number) => void;
  clearNotification: () => void;
}

// --- Validation Helpers ---
export const validateEmail = (email: string): string => {
  if (!email) return 'Email is required.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Invalid email format.';
  return '';
};

export const validatePassword = (password: string): string => {
  if (!password) return 'Password is required.';
  if (password.length < 6) return 'Password must be at least 6 characters.';
  return '';
};

export const validateUsername = (username: string): string => {
  if (!username) return 'Username is required.';
  if (username.length < 3) return 'Username must be at least 3 characters.';
  return '';
};

export const validateFile = (
  file: File | null,
  allowedExtensions: string[],
  maxSize: number
): string => {
  if (!file) return 'File is required.';

  const fileName = file.name;
  const fileExtension = fileName.split('.').pop()?.toLowerCase();

  if (!fileExtension || !allowedExtensions.includes(fileExtension)) {
    return `Invalid file type. Allowed: ${allowedExtensions.join(', ').toUpperCase()}.`;
  }

  if (file.size > maxSize) {
    return `File size exceeds limit. Max: ${formatBytes(maxSize)}.`;
  }

  return '';
};

// --- General Utilities ---
export const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};