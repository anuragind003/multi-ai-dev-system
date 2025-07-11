import { useState, useCallback, ChangeEvent } from 'react';

type ValidationRule = {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: string) => string | undefined;
};

type ValidationRules<T extends Record<string, string>> = {
  [K in keyof T]?: ValidationRule;
};

type FormErrors<T extends Record<string, string>> = {
  [K in keyof T]?: string;
};

const useFormValidation = <T extends Record<string, string>>(
  initialState: T,
  validationRules: ValidationRules<T>
) => {
  const [formData, setFormData] = useState<T>(initialState);
  const [errors, setErrors] = useState<FormErrors<T>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
    // Clear error for the field as user types
    if (errors[name as keyof T]) {
      setErrors((prevErrors) => ({
        ...prevErrors,
        [name]: undefined,
      }));
    }
  }, [errors]);

  const validateField = useCallback((name: keyof T, value: string): string | undefined => {
    const rules = validationRules[name];
    if (!rules) return undefined;

    if (rules.required && !value.trim()) {
      return 'This field is required.';
    }
    if (rules.minLength && value.length < rules.minLength) {
      return `Must be at least ${rules.minLength} characters.`;
    }
    if (rules.maxLength && value.length > rules.maxLength) {
      return `Must be no more than ${rules.maxLength} characters.`;
    }
    if (rules.pattern && !rules.pattern.test(value)) {
      return 'Invalid format.';
    }
    if (rules.custom) {
      return rules.custom(value);
    }
    return undefined;
  }, [validationRules]);

  const validateForm = useCallback((): boolean => {
    let newErrors: FormErrors<T> = {};
    let isValid = true;

    for (const key in formData) {
      const error = validateField(key, formData[key]);
      if (error) {
        newErrors = { ...newErrors, [key]: error };
        isValid = false;
      }
    }
    setErrors(newErrors);
    return isValid;
  }, [formData, validateField]);

  const handleSubmit = useCallback(async (callback: (data: T) => Promise<void>) => {
    setIsSubmitting(true);
    const isValid = validateForm();
    if (isValid) {
      try {
        await callback(formData);
      } catch (err) {
        // Handle submission-specific errors, e.g., API errors
        console.error('Form submission error:', err);
        setErrors((prevErrors) => ({
          ...prevErrors,
          _form: (err as Error).message || 'An unexpected error occurred.',
        }));
      }
    }
    setIsSubmitting(false);
  }, [formData, validateForm]);

  return {
    formData,
    errors,
    handleChange,
    handleSubmit,
    isSubmitting,
    setFormData, // Expose setFormData for external updates if needed
    setErrors, // Expose setErrors for external error setting (e.g., API errors)
  };
};

export default useFormValidation;