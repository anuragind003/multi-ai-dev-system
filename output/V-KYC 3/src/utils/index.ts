import { useState, useEffect, useCallback } from 'react';
import { useForm, FieldValues, UseFormProps } from 'react-hook-form';
import { ZodSchema } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

// --- Custom Hook for Form Handling with Zod Validation ---
interface UseFormValidationProps<TFieldValues extends FieldValues> extends UseFormProps<TFieldValues> {
  schema: ZodSchema<TFieldValues>;
}

export function useFormValidation<TFieldValues extends FieldValues>(
  props: UseFormValidationProps<TFieldValues>
) {
  const { schema, ...rest } = props;
  return useForm<TFieldValues>({
    resolver: zodResolver(schema),
    ...rest,
  });
}

// --- Utility Function: formatDate ---
export const formatDate = (dateString: string | Date, format: 'short' | 'long' = 'short'): string => {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    return 'Invalid Date';
  }

  const options: Intl.DateTimeFormatOptions = format === 'short'
    ? { year: 'numeric', month: 'short', day: 'numeric' }
    : { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };

  return new Intl.DateTimeFormat('en-US', options).format(date);
};

// --- Utility Function: debounce ---
// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
export const debounce = <T extends (...args: any[]) => void>(
  func: T,
  delay: number,
  immediate = false
): ((...args: Parameters<T>) => void) => {
  let timeout: ReturnType<typeof setTimeout> | null;
  let result: any;

  return function(this: any, ...args: Parameters<T>): void {
    const context = this;
    const later = function() {
      timeout = null;
      if (!immediate) {
        result = func.apply(context, args);
      }
    };

    const callNow = immediate && !timeout;
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, delay);
    if (callNow) {
      result = func.apply(context, args);
    }
  };
};

// --- Custom Hook: useDebounce ---
// A React-specific hook for debouncing a value.
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// --- Utility Function: capitalizeFirstLetter ---
export const capitalizeFirstLetter = (str: string): string => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
};