import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  id: string; // Enforce id for accessibility
}

/**
 * Reusable Input component with label, error display, and accessibility features.
 */
const Input: React.FC<InputProps> = ({
  label,
  error,
  id,
  className = '',
  type = 'text',
  ...props
}) => {
  const baseStyles = 'block w-full px-4 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 transition-colors duration-200 ease-in-out';
  const defaultBorder = 'border-border focus:border-primary focus:ring-primary';
  const errorBorder = 'border-danger focus:border-danger focus:ring-danger';

  return (
    <div className="mb-4">
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-text-light mb-1">
          {label}
        </label>
      )}
      <input
        id={id}
        type={type}
        className={`${baseStyles} ${error ? errorBorder : defaultBorder} ${className}`}
        aria-invalid={error ? "true" : "false"}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
};

export default React.memo(Input); // Memoize for performance