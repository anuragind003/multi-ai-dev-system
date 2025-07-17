import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  id: string;
  error?: string;
  className?: string;
}

const Input: React.FC<InputProps> = ({
  label,
  id,
  error,
  className = '',
  ...props
}) => {
  const baseStyles = 'block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none sm:text-sm';
  const defaultBorder = 'border-gray-300 focus:border-primary focus:ring-primary';
  const errorBorder = 'border-error focus:border-error focus:ring-error';

  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-text-light mb-1">
          {label}
        </label>
      )}
      <input
        id={id}
        className={`${baseStyles} ${error ? errorBorder : defaultBorder}`}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-error" role="alert" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
};

export default Input;