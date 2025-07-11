import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode; // Optional custom fallback UI
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  // This static method is called after an error has been thrown by a descendant component.
  // It receives the error that was thrown as a parameter and should return a value to update the state.
  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error, errorInfo: null }; // errorInfo will be set in componentDidCatch
  }

  // This method is called after an error has been thrown by a descendant component.
  // It receives two parameters: error and info.
  // error: The error that was thrown.
  // info: An object with a componentStack key containing information about which component threw the error.
  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error('Uncaught error in ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
    // Example of logging to a service:
    // logErrorToMyService(error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-error/10 text-error p-4 text-center">
          <h1 className="text-4xl font-bold mb-4">Oops! Something went wrong.</h1>
          <p className="text-lg mb-6">We're sorry, but an unexpected error occurred.</p>
          <details className="text-sm text-text-light bg-white p-4 rounded-md shadow-md max-w-lg overflow-auto">
            <summary className="cursor-pointer text-primary font-semibold">Error Details</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words text-left">
              {this.state.error && this.state.error.toString()}
              <br />
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            className="mt-8 px-6 py-3 bg-primary text-white rounded-md hover:bg-indigo-700 transition-colors duration-200"
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary };