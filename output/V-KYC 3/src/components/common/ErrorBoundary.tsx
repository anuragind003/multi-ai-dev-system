import React, { Component, ErrorInfo, ReactNode } from 'react';
import Button from '../ui/Button.tsx';

interface ErrorBoundaryProps {
  children: ReactNode;
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

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 text-gray-800 p-4">
          <h1 className="text-4xl font-bold text-danger mb-4">Oops! Something went wrong.</h1>
          <p className="text-lg text-gray-700 mb-6 text-center">
            We're sorry, but an unexpected error occurred. Please try reloading the page.
          </p>
          <Button onClick={this.handleReload} variant="primary" size="lg">
            Reload Page
          </Button>
          {this.state.error && (
            <details className="mt-8 p-4 bg-gray-200 rounded-md max-w-xl w-full overflow-auto text-sm">
              <summary className="font-semibold cursor-pointer">Error Details</summary>
              <pre className="mt-2 whitespace-pre-wrap break-words">
                {this.state.error.toString()}
                <br />
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;