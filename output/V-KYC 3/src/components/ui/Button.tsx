import React from 'react';

// Define button variants and sizes for consistent styling
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  children: React.ReactNode;
}

/**
 * Reusable Button component with customizable variants, sizes, and loading state.
 * Follows modern UI/UX best practices and accessibility.
 */
const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className = '',
  disabled,
  ...props
}) => {
  // Base styles for all buttons
  const baseStyles = 'font-semibold rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 ease-in-out';

  // Variant-specific styles
  const variantStyles: Record<ButtonVariant, string> = {
    primary: 'bg-primary text-white hover:bg-primary-dark focus:ring-primary-dark',
    secondary: 'bg-secondary text-white hover:bg-secondary-dark focus:ring-secondary-dark',
    danger: 'bg-danger text-white hover:bg-red-600 focus:ring-red-600',
    outline: 'bg-transparent border border-primary text-primary hover:bg-primary hover:text-white focus:ring-primary',
    ghost: 'bg-transparent text-text hover:bg-gray-100 focus:ring-gray-300',
  };

  // Size-specific styles
  const sizeStyles: Record<ButtonSize, string> = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  // Disabled styles
  const disabledStyles = 'opacity-50 cursor-not-allowed';

  // Loading spinner
  const spinner = (
    <svg
      className="animate-spin h-5 w-5 text-white inline-block mr-2"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      ></circle>
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      ></path>
    </svg>
  );

  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${
        (disabled || isLoading) ? disabledStyles : ''
      } ${className}`}
      disabled={disabled || isLoading}
      aria-busy={isLoading ? "true" : "false"}
      aria-live="polite"
      {...props}
    >
      {isLoading && spinner}
      {children}
    </button>
  );
};

export default React.memo(Button); // Memoize for performance