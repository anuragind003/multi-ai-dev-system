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
  // It receives the error that was thrown as a parameter and should return a value to update state.
  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error: error, errorInfo: null };
  }

  // This method is called after an error has been thrown.
  // It receives the error and information about the component stack.
  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ errorInfo: errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-error/10 text-error p-4">
          <h1 className="text-4xl font-bold mb-4">Oops! Something went wrong.</h1>
          <p className="text-lg mb-6">We're sorry for the inconvenience. Please try again later.</p>
          <details className="w-full max-w-xl bg-white p-4 rounded-lg shadow-md text-sm text-text-light">
            <summary className="cursor-pointer font-semibold text-text">Error Details</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words">
              {this.state.error && this.state.error.toString()}
              <br />
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            className="mt-8 px-6 py-3 bg-primary text-white rounded-md hover:bg-indigo-700 transition duration-200"
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