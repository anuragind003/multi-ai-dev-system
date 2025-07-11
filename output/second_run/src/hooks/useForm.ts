import { useState, useCallback } from 'react';

interface UseFormProps<T> {
  initialValues: T;
  onSubmit: (values: T) => void | Promise<void>;
  validate?: (values: T) => { [key: string]: string };
}

export const useForm = <T extends object>({ initialValues, onSubmit, validate }: UseFormProps<T>) => {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { name, value } = e.target;
      setValues((prevValues) => ({
        ...prevValues,
        [name]: value,
      }));
    },
    []
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setIsSubmitting(true);
      const validationErrors = validate ? validate(values) : {};
      setErrors(validationErrors);

      if (Object.keys(validationErrors).length === 0) {
        await onSubmit(values);
      }
      setIsSubmitting(false);
    },
    [values, onSubmit, validate]
  );

  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
  }, [initialValues]);

  return {
    values,
    handleChange,
    handleSubmit,
    errors,
    isSubmitting,
    resetForm,
  };
};