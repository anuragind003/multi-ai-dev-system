import React, { useState } from 'react';
import { IconType } from 'react-icons'; // Placeholder for actual icon library if used

// --- Button Component ---
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: IconType;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon: Icon,
  children,
  className,
  disabled,
  ...props
}) => {
  const baseStyles = 'font-semibold rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2';
  const variantStyles = {
    primary: 'bg-primary text-white hover:bg-primary-dark focus:ring-primary',
    secondary: 'bg-secondary text-white hover:bg-secondary-dark focus:ring-secondary',
    danger: 'bg-danger text-white hover:bg-red-600 focus:ring-danger',
    outline: 'bg-transparent border border-gray-300 text-text hover:bg-gray-100 focus:ring-gray-400',
    ghost: 'bg-transparent text-text hover:bg-gray-100 focus:ring-gray-400',
  };
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className || ''} ${
        (isLoading || disabled) ? 'opacity-60 cursor-not-allowed' : ''
      }`}
      disabled={isLoading || disabled}
      {...props}
    >
      {isLoading ? (
        <LoadingSpinner size="sm" className="inline-block mr-2" />
      ) : (
        Icon && <Icon className="inline-block mr-2" />
      )}
      {children}
    </button>
  );
};

// --- Input Component ---
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  type?: 'text' | 'password' | 'email' | 'number' | 'file';
}

export const Input: React.FC<InputProps> = ({ label, error, type = 'text', className, ...props }) => {
  const id = props.id || props.name || `input-${Math.random().toString(36).substr(2, 9)}`;

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
        className={`block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm ${
          error ? 'border-danger focus:ring-danger focus:border-danger' : ''
        } ${className || ''}`}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

// --- Card Component ---
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  title?: string;
}

export const Card: React.FC<CardProps> = ({ children, title, className, ...props }) => {
  return (
    <div className={`bg-white rounded-lg shadow-medium p-6 ${className || ''}`} {...props}>
      {title && <h2 className="text-xl font-semibold text-text mb-4">{title}</h2>}
      {children}
    </div>
  );
};

// --- Modal Component ---
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer }) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto my-8 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 id="modal-title" className="text-lg font-semibold text-text">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary rounded-md"
            aria-label="Close modal"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {children}
        </div>
        {footer && (
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

// --- LoadingSpinner Component ---
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', className }) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-3',
    lg: 'w-8 h-8 border-4',
  };
  return (
    <div
      className={`inline-block animate-spin rounded-full border-solid border-current border-r-transparent text-primary ${sizeClasses[size]} ${className || ''}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

// --- ErrorMessage Component ---
interface ErrorMessageProps {
  message: string;
  className?: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, className }) => {
  if (!message) return null;
  return (
    <div
      className={`bg-danger/10 border border-danger text-danger px-4 py-3 rounded-md relative ${className || ''}`}
      role="alert"
    >
      <strong className="font-bold mr-2">Error!</strong>
      <span className="block sm:inline">{message}</span>
    </div>
  );
};