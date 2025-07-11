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
  // It receives the error that was thrown as a parameter.
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error, errorInfo: null };
  }

  // This method is called after an error has been thrown.
  // It receives two parameters: error and info.
  // error: The error that was thrown.
  // info: An object with a componentStack key containing information about which component threw the error.
  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in ErrorBoundary:', error, errorInfo);
    // You can also log the error to an error reporting service here
    this.setState({ errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-danger/10 text-danger p-4">
          <h1 className="text-3xl font-bold mb-4">Oops! Something went wrong.</h1>
          <p className="text-lg mb-6">We're sorry for the inconvenience. Please try refreshing the page.</p>
          {this.state.error && (
            <details className="bg-white p-4 rounded-md shadow-md text-sm text-text-light max-w-lg overflow-auto">
              <summary className="font-semibold cursor-pointer text-text">Error Details</summary>
              <pre className="mt-2 whitespace-pre-wrap break-words">
                {this.state.error.toString()}
                <br />
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
          <Button onClick={() => window.location.reload()} className="mt-8">
            Refresh Page
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary };