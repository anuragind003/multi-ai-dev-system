import React from 'react';

interface StatusDisplayProps {
  type: 'loading' | 'error' | 'info';
  message: string;
}

const StatusDisplay: React.FC<StatusDisplayProps> = ({ type, message }) => {
  let icon: React.ReactNode;
  let bgColor: string;
  let textColor: string;

  switch (type) {
    case 'loading':
      icon = (
        <svg
          className="animate-spin h-5 w-5 text-primary mr-3"
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
      bgColor = 'bg-blue-100';
      textColor = 'text-blue-700';
      break;
    case 'error':
      icon = (
        <svg
          className="h-5 w-5 text-red-500 mr-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          ></path>
        </svg>
      );
      bgColor = 'bg-red-100';
      textColor = 'text-red-700';
      break;
    case 'info':
      icon = (
        <svg
          className="h-5 w-5 text-blue-500 mr-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          ></path>
        </svg>
      );
      bgColor = 'bg-blue-100';
      textColor = 'text-blue-700';
      break;
  }

  return (
    <div
      className={`flex items-center p-4 rounded-md ${bgColor} ${textColor} mb-4`}
      role={type === 'error' ? 'alert' : 'status'}
      aria-live={type === 'error' ? 'assertive' : 'polite'}
    >
      {icon}
      <p className="font-medium">{message}</p>
    </div>
  );
};

export default StatusDisplay;