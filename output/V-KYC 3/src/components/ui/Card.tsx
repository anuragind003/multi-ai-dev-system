import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  ariaLabel?: string;
}

const Card: React.FC<CardProps> = ({ children, className, ariaLabel }) => {
  return (
    <div
      className={`bg-white rounded-lg shadow-custom-light p-6 sm:p-8 ${className || ''}`}
      role="region"
      aria-label={ariaLabel}
    >
      {children}
    </div>
  );
};

export default Card;