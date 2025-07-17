import React from 'react';
import Spinner from './Spinner'; // Assuming Spinner is a simple component

interface FeedbackProps {
  type: 'loading' | 'success' | 'error' | 'info';
  message?: string;
  className?: string;
}

const Feedback: React.FC<FeedbackProps> = ({ type, message, className }) => {
  const baseClasses = 'p-3 rounded-md flex items-center space-x-2';
  let typeClasses = '';
  let icon = null;

  switch (type) {
    case 'loading':
      typeClasses = 'bg-blue-100 text-blue-800';
      icon = <Spinner size="sm" />;
      break;
    case 'success':
      typeClasses = 'bg-green-100 text-green-800';
      icon = (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
      );
      break;
    case 'error':
      typeClasses = 'bg-red-100 text-red-800';
      icon = (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      );
      break;
    case 'info':
      typeClasses = 'bg-blue-100 text-blue-800';
      icon = (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
      );
      break;
  }

  return (
    <div className={`${baseClasses} ${typeClasses} ${className}`} role="alert">
      {icon}
      {message && <span className="text-sm font-medium">{message}</span>}
    </div>
  );
};

export default Feedback;