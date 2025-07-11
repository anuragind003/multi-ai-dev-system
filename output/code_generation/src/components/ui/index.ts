import React, { useState, useEffect } from 'react';
import { ButtonProps, InputProps, ModalProps, CardProps, LoadingSpinnerProps, ErrorBoundaryProps, ErrorBoundaryState } from '../../types';

// --- Button Component ---
export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  className = '',
  children,
  ...props
}) => {
  const baseStyles = 'font-semibold py-2 px-4 rounded-md transition duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-400',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost: 'bg-transparent text-blue-600 hover:bg-blue-50 focus:ring-blue-500',
  };
  const sizes = {
    small: 'text-sm py-1 px-3',
    medium: 'text-base py-2 px-4',
    large: 'text-lg py-3 px-6',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className} ${props.disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      {...props}
    >
      {children}
    </button>
  );
};

// --- Input Component ---
export const Input: React.FC<InputProps> = ({ label, id, name, error, className = '', ...props }) => {
  const inputClasses = `block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm ${
    error ? 'border-red-500' : 'border-gray-300'
  } ${className}`;

  return (
    <div>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <input id={id} name={name} className={inputClasses} {...props} />
      {error && (
        <p className="mt-1 text-sm text-red-600" role="alert" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
};

// --- Modal Component ---
export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className = '', ariaLabel }) => {
  if (!isOpen) return null;

  // Close on Escape key press
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-label={ariaLabel || title}
    >
      <div
        className={`bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto relative ${className}`}
        onClick={(e) => e.stopPropagation()} // Prevent click from closing modal
      >
        <div className="flex justify-between items-center p-4 border-b border-gray-200">
          <h2 id="modal-title" className="text-xl font-semibold text-gray-900">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md"
            aria-label="Close modal"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
};

// --- Card Component ---
export const Card: React.FC<CardProps> = ({ children, className = '', ...props }) => {
  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`} {...props}>
      {children}
    </div>
  );
};

// --- LoadingSpinner Component ---
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'medium', className = '' }) => {
  const spinnerSizes = {
    small: 'w-4 h-4 border-2',
    medium: 'w-6 h-6 border-3',
    large: 'w-8 h-8 border-4',
  };
  return (
    <div
      className={`inline-block animate-spin rounded-full border-solid border-current border-r-transparent text-blue-600 ${spinnerSizes[size]} ${className}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

// --- ErrorBoundary Component ---
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-red-50 text-red-800 p-4">
          <h1 className="text-3xl font-bold mb-4">Something went wrong.</h1>
          <p className="text-lg mb-4">We're sorry for the inconvenience. Please try refreshing the page.</p>
          {this.state.error && (
            <details className="mt-4 p-2 bg-red-100 border border-red-200 rounded-md max-w-lg overflow-auto">
              <summary className="font-semibold cursor-pointer">Error Details</summary>
              <pre className="mt-2 text-sm whitespace-pre-wrap break-words">
                {this.state.error.toString()}
                <br />
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
          <Button onClick={() => window.location.reload()} variant="primary" className="mt-6">
            Refresh Page
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}