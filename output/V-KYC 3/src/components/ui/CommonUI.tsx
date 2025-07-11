import React, { InputHTMLAttributes, ButtonHTMLAttributes, HTMLAttributes } from 'react';

// --- Button Component ---
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

export const Button = React.memo(({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) => {
  const baseStyles = 'font-semibold rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';
  const disabledStyles = 'opacity-50 cursor-not-allowed';

  const variantStyles = {
    primary: 'bg-primary text-white hover:bg-indigo-700 focus:ring-primary',
    secondary: 'bg-secondary text-white hover:bg-gray-600 focus:ring-secondary',
    danger: 'bg-error text-white hover:bg-red-600 focus:ring-error',
    outline: 'bg-transparent border border-primary text-primary hover:bg-primary hover:text-white focus:ring-primary',
    ghost: 'bg-transparent text-primary hover:bg-primary-50 focus:ring-primary',
  };

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-5 py-2.5 text-lg',
  };

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${isLoading ? disabledStyles : ''} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner size="sm" className="inline-block mr-2" />
      ) : null}
      {children}
    </button>
  );
});

// --- Input Component ---
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.memo(({ label, error, className = '', id, ...props }: InputProps) => {
  const inputId = id || props.name || label?.toLowerCase().replace(/\s/g, '-');
  return (
    <div className="mb-4">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-text-light mb-1">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm
          ${error ? 'border-error focus:border-error focus:ring-error' : 'border-border'} ${className}`}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${inputId}-error`} className="mt-1 text-sm text-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
});

// --- Card Component ---
interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  title?: string;
}

export const Card = React.memo(({ children, title, className = '', ...props }: CardProps) => {
  return (
    <div className={`bg-white rounded-lg shadow-md-light p-6 ${className}`} {...props}>
      {title && <h2 className="text-xl font-semibold text-text mb-4">{title}</h2>}
      {children}
    </div>
  );
});

// --- LoadingSpinner Component ---
interface LoadingSpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner = React.memo(({ size = 'md', className = '', ...props }: LoadingSpinnerProps) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-3',
    lg: 'w-8 h-8 border-4',
  };

  return (
    <div
      className={`inline-block animate-spin rounded-full border-solid border-current border-r-transparent text-primary ${sizeClasses[size]} ${className}`}
      role="status"
      aria-label="Loading"
      {...props}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
});