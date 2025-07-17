import React, { ButtonHTMLAttributes, InputHTMLAttributes, HTMLAttributes } from 'react';
import { FormErrors } from '@types';

// --- Button Component ---
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles = 'font-semibold rounded-md transition duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2';
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };
  const variantStyles = {
    primary: 'bg-primary text-white hover:bg-primary-dark focus:ring-primary',
    secondary: 'bg-secondary text-white hover:bg-secondary-dark focus:ring-secondary',
    danger: 'bg-danger text-white hover:bg-red-600 focus:ring-danger',
    outline: 'bg-transparent border border-primary text-primary hover:bg-primary hover:text-white focus:ring-primary',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${loading ? 'opacity-75 cursor-not-allowed' : ''} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <LoadingSpinner size="sm" className="inline-block mr-2" />
      ) : null}
      {children}
    </button>
  );
};

// --- Input Component ---
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  containerClassName?: string;
}

export const Input: React.FC<InputProps> = ({ label, error, containerClassName = '', className = '', id, ...props }) => {
  const inputId = id || props.name;
  return (
    <div className={`mb-4 ${containerClassName}`}>
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-text-light mb-1">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm
          ${error ? 'border-danger focus:border-danger focus:ring-danger' : 'border-border'} ${className}`}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-danger" role="alert">{error}</p>}
    </div>
  );
};

// --- Loading Spinner Component ---
interface LoadingSpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', color = 'currentColor', className = '', ...props }) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-3',
    lg: 'w-8 h-8 border-4',
  };
  return (
    <div
      className={`inline-block animate-spin rounded-full border-solid border-r-transparent ${sizeClasses[size]} ${className}`}
      style={{ borderColor: color }}
      role="status"
      aria-label="Loading"
      {...props}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

// --- Error Display Component ---
interface ErrorDisplayProps extends HTMLAttributes<HTMLDivElement> {
  message: string | null;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ message, className = '', ...props }) => {
  if (!message) return null;
  return (
    <div
      className={`bg-red-100 border border-danger text-danger px-4 py-3 rounded-md relative ${className}`}
      role="alert"
      {...props}
    >
      <strong className="font-bold">Error!</strong>
      <span className="block sm:inline ml-2">{message}</span>
    </div>
  );
};

// --- Card Component ---
interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
}

export const Card: React.FC<CardProps> = ({ children, title, className = '', ...props }) => {
  return (
    <div className={`bg-white rounded-lg shadow-custom-medium p-6 ${className}`} {...props}>
      {title && <h2 className="text-xl font-semibold text-text mb-4">{title}</h2>}
      {children}
    </div>
  );
};