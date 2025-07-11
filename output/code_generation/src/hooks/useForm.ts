import { useState, useCallback, ChangeEvent, FormEvent } from 'react';
import { FormValues, FormErrors, Validator } from '../types';

interface UseFormProps<T extends FormValues> {
  initialValues: T;
  validators?: Validator<T>;
  onSubmit: (values: T) => void;
}

const useForm = <T extends FormValues>({ initialValues, validators, onSubmit }: UseFormProps<T>) => {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<FormErrors<T>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let processedValue: string | number | boolean = value;

    if (type === 'number') {
      processedValue = parseFloat(value);
      if (isNaN(processedValue)) processedValue = ''; // Handle empty string for number inputs
    } else if (type === 'checkbox') {
      processedValue = (e.target as HTMLInputElement).checked;
    }

    setValues((prevValues) => ({
      ...prevValues,
      [name]: processedValue,
    }));

    // Clear error for the field as user types
    if (errors[name as keyof T]) {
      setErrors((prevErrors) => {
        const newErrors = { ...prevErrors };
        delete newErrors[name as keyof T];
        return newErrors;
      });
    }
  }, [errors]);

  const validate = useCallback((currentValues: T): FormErrors<T> => {
    const newErrors: FormErrors<T> = {};
    if (validators) {
      for (const key in validators) {
        if (Object.prototype.hasOwnProperty.call(validators, key)) {
          const validatorFn = validators[key];
          if (validatorFn) {
            const error = validatorFn(currentValues[key], currentValues);
            if (error) {
              newErrors[key] = error;
            }
          }
        }
      }
    }
    return newErrors;
  }, [validators]);

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const validationErrors = validate(values);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length === 0) {
      try {
        await onSubmit(values);
      } catch (submitError) {
        // Handle submission-specific errors if onSubmit throws
        console.error('Form submission error:', submitError);
        // Optionally set a global form error
        setErrors(prev => ({ ...prev, _form: 'An unexpected error occurred during submission.' }));
      }
    }
    setIsSubmitting(false);
  }, [values, validate, onSubmit]);

  const setFieldValue = useCallback((name: keyof T, value: T[keyof T]) => {
    setValues((prevValues) => ({
      ...prevValues,
      [name]: value,
    }));
    if (errors[name]) {
      setErrors((prevErrors) => {
        const newErrors = { ...prevErrors };
        delete newErrors[name];
        return newErrors;
      });
    }
  }, [errors]);

  return {
    values,
    errors,
    handleChange,
    handleSubmit,
    isSubmitting,
    setFieldValue,
    setErrors, // Allow external setting of errors
  };
};

export default useForm;