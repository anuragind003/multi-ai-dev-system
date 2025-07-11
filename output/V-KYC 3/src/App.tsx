import React, { Suspense } from 'react';
import AppRouter from '@routes/AppRouter';
import Header from '@components/layout/Header';
import { useAuth } from '@hooks/useAuth';

// A simple loading spinner component
const LoadingSpinner: React.FC = () => (
  <div className="flex items-center justify-center h-screen">
    <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-primary"></div>
    <p className="ml-4 text-lg text-text-light">Loading...</p>
  </div>
);

// Basic Error Boundary component
interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // You can also log the error to an error reporting service
    console.error("Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div className="flex flex-col items-center justify-center h-screen bg-red-50 text-red-800 p-4 rounded-lg shadow-md">
          <h1 className="text-3xl font-bold mb-4">Oops! Something went wrong.</h1>
          <p className="text-lg mb-2">We're sorry, an unexpected error occurred.</p>
          {this.state.error && (
            <details className="text-sm text-red-600 bg-red-100 p-2 rounded-md mt-4 max-w-lg overflow-auto">
              <summary className="cursor-pointer">Error Details</summary>
              <pre className="whitespace-pre-wrap break-words mt-2">{this.state.error.message}</pre>
              {/* <pre className="whitespace-pre-wrap break-words mt-2">{this.state.error.stack}</pre> */}
            </details>
          )}
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-3 bg-primary text-white rounded-md hover:bg-primary-dark transition-colors"
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

const App: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <ErrorBoundary>
      <div className="flex flex-col min-h-screen bg-background">
        <Header />
        <main className="flex-grow container mx-auto px-4 py-8">
          <Suspense fallback={<LoadingSpinner />}>
            <AppRouter />
          </Suspense>
        </main>
        {/* Simple Footer */}
        <footer className="bg-gray-800 text-white py-4 text-center text-sm">
          <div className="container mx-auto">
            <p>&copy; {new Date().getFullYear()} Enterprise App. All rights reserved.</p>
            <p className="mt-1">Built with React & Tailwind CSS.</p>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
};

export default App;