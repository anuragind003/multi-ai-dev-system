import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
}

export const Button = ({ children, variant = 'primary', size = 'medium', disabled, ...props }: ButtonProps) => {
  const variantStyles = {
    primary: 'bg-blue-500 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-300 hover:bg-gray-400 text-gray-800',
    danger: 'bg-red-500 hover:bg-red-700 text-white',
  };

  const sizeStyles = {
    small: 'px-2 py-1 text-sm',
    medium: 'px-4 py-2 text-base',
    large: 'px-6 py-3 text-lg',
  };

  const disabledStyles = disabled ? 'opacity-50 cursor-not-allowed' : '';

  return (
    <button
      {...props}
      disabled={disabled}
      className={`rounded font-medium ${variantStyles[variant]} ${sizeStyles[size]} ${disabledStyles} focus:outline-none focus:ring-2 focus:ring-blue-500`}
    >
      {children}
    </button>
  );
};