import React from 'react';
import { FallbackProps } from 'react-error-boundary';

/**
 * A fallback UI component for React Error Boundaries.
 * Displays an error message and a button to reset the application state.
 */
const ErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center min-h-screen bg-red-50 text-red-800 p-4 text-center"
    >
      <h2 className="text-3xl font-bold mb-4">Something went wrong!</h2>
      <pre className="bg-red-100 p-4 rounded-md text-sm whitespace-pre-wrap break-words max-w-lg mb-6">
        {error.message}
      </pre>
      <button
        onClick={resetErrorBoundary}
        className="px-6 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
      >
        Try again
      </button>
      <p className="mt-4 text-sm text-red-700">
        If the problem persists, please contact support.
      </p>
    </div>
  );
};

export default ErrorFallback;