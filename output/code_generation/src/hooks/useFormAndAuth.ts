import { useState, useCallback, useContext } from 'react';
import { AuthAndAppContext } from '@/context/AuthAndAppContext';
import { loginUser, registerUser } from '@/services/api'; // Combined API service
import { User, LoginPayload, RegisterPayload } from '@/utils'; // Combined types

// --- useForm Hook ---
type FormValues = Record<string, any>;
type FormErrors<T extends FormValues> = {
  [K in keyof T]?: string;
};
type ValidationRules<T extends FormValues> = {
  [K in keyof T]?: (value: T[K]) => string;
};

export const useFormAndAuth = <T extends FormValues>(initialValues: T) => {
  const [formData, setFormData] = useState<T>(initialValues);
  const [errors, setErrors] = useState<FormErrors<T>>({});

  const handleChange = useCallback((name: keyof T, value: T[keyof T]) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[name]; // Clear error when user starts typing
      return newErrors;
    });
  }, []);

  const validateForm = useCallback((rules: ValidationRules<T>): FormErrors<T> => {
    const newErrors: FormErrors<T> = {};
    for (const key in rules) {
      if (rules[key]) {
        const error = rules[key]!(formData[key]);
        if (error) {
          newErrors[key] = error;
        }
      }
    }
    setErrors(newErrors);
    return newErrors;
  }, [formData]);

  const resetForm = useCallback(() => {
    setFormData(initialValues);
    setErrors({});
  }, [initialValues]);

  // --- useAuth Hook (integrated) ---
  const context = useContext(AuthAndAppContext);
  if (context === undefined) {
    throw new Error('useAuthAndApp must be used within an AuthAndAppProvider');
  }
  const { login: contextLogin, logout: contextLogout, showLoading, hideLoading, showError, clearError, ...restAuthContext } = context;

  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setAuthError(null);
    showLoading();
    try {
      const payload: LoginPayload = { username, password };
      const response = await loginUser(payload);
      const user: User = { id: response.userId, username: response.username, email: response.email };
      contextLogin(user, response.token);
      clearError(); // Clear global app error
    } catch (err: any) {
      const errorMessage = err.message || 'Login failed. Please check your credentials.';
      setAuthError(errorMessage);
      showError(errorMessage); // Set global app error
      throw err; // Re-throw to allow component to catch
    } finally {
      setIsLoading(false);
      hideLoading();
    }
  }, [contextLogin, showLoading, hideLoading, showError, clearError]);

  const register = useCallback(async (username: string, email: string, password: string) => {
    setIsLoading(true);
    setAuthError(null);
    showLoading();
    try {
      const payload: RegisterPayload = { username, email, password };
      const response = await registerUser(payload);
      const user: User = { id: response.userId, username: response.username, email: response.email };
      contextLogin(user, response.token);
      clearError(); // Clear global app error
    } catch (err: any) {
      const errorMessage = err.message || 'Registration failed. Please try again.';
      setAuthError(errorMessage);
      showError(errorMessage); // Set global app error
      throw err; // Re-throw to allow component to catch
    } finally {
      setIsLoading(false);
      hideLoading();
    }
  }, [contextLogin, showLoading, hideLoading, showError, clearError]);

  const logout = useCallback(() => {
    contextLogout();
    clearError(); // Clear global app error on logout
  }, [contextLogout, clearError]);

  return {
    formData,
    errors,
    handleChange,
    validateForm,
    resetForm,
    // Auth related exports
    login,
    register,
    logout,
    isLoading,
    error: authError || restAuthContext.appError, // Prioritize local auth error, then global app error
    user: restAuthContext.user,
    isAuthenticated: restAuthContext.isAuthenticated,
    appLoading: restAuthContext.appLoading,
    notification: restAuthContext.notification,
    showNotification: restAuthContext.showNotification,
    clearNotification: restAuthContext.clearNotification,
  };
};