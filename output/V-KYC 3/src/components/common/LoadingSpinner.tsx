import React from 'react';

const LoadingSpinner: React.FC = () => {
  return (
    <div className="flex justify-center items-center h-full min-h-[200px]">
      <div
        className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-primary"
        role="status"
        aria-label="Loading"
      >
        <span className="sr-only">Loading...</span>
      </div>
    </div>
  );
};

export default LoadingSpinner;