import { useContext, useCallback, useState, useEffect } from 'react';
import { AuthContext } from '@context/AuthContext';
import { GlobalContext } from '@context/GlobalContext';
import { ZodSchema, ZodError } from 'zod';

// --- Types ---
interface FormErrors<T> {
  [key: string]: string | undefined;
}

interface UseFormValidationResult<T> {
  formData: T;
  errors: FormErrors<T>;
  handleChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void;
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  setFormData: React.Dispatch<React.SetStateAction<T>>;
  validateForm: () => boolean;
  resetForm: () => void;
}

// --- Custom Hooks ---

/**
 * Custom hook for authentication state and actions.
 * Provides access to `isAuthenticated`, `user`, `isLoading`, `login`, and `logout` from AuthContext.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * Custom hook for form state management and Zod validation.
 * @param initialData - The initial state of the form data.
 * @param schema - The Zod schema for validation.
 * @returns An object containing form data, errors, change handlers, and validation function.
 */
export const useFormValidation = <T extends Record<string, any>>(
  initialData: T,
  schema: ZodSchema<T>
): UseFormValidationResult<T> => {
  const [formData, setFormData] = useState<T>(initialData);
  const [errors, setErrors] = useState<FormErrors<T>>({});

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for the field as user types
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }, [errors]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, files } = e.target;
    setFormData((prev) => ({ ...prev, [name]: files && files.length > 0 ? files[0] : null }));
    // Clear error for the field
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }, [errors]);

  const validateForm = useCallback(() => {
    try {
      schema.parse(formData);
      setErrors({});
      return true;
    } catch (error) {
      if (error instanceof ZodError) {
        const newErrors: FormErrors<T> = {};
        error.errors.forEach((err) => {
          if (err.path.length > 0) {
            newErrors[err.path[0] as keyof T] = err.message;
          }
        });
        setErrors(newErrors);
      }
      return false;
    }
  }, [formData, schema]);

  const resetForm = useCallback(() => {
    setFormData(initialData);
    setErrors({});
  }, [initialData]);

  // Optional: Re-validate when formData changes (can be performance intensive for large forms)
  // useEffect(() => {
  //   validateForm();
  // }, [formData, validateForm]);

  return {
    formData,
    errors,
    handleChange,
    handleFileChange,
    setFormData,
    validateForm,
    resetForm,
  };
};