import React, { ReactNode } from 'react';
import { reportError } from '../../utils/errorReporting';

interface ErrorBoundaryProps {
  fallback: ReactNode;
  children: ReactNode;
}

export const ErrorBoundary: React.FC<ErrorBoundaryProps> = ({ fallback, children }) => {
  const [hasError, setHasError] = React.useState(false);

  React.useEffect(() => {
    return () => {
      if (hasError) {
        reportError(new Error("ErrorBoundary triggered"));
      }
    };
  }, [hasError]);

  if (hasError) {
    return fallback;
  }

  return children;
};