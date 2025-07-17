
import React, { useState, useEffect } from 'react';
import { User } from './types';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import { getUser, logout, verifyToken } from './services/auth';
import { ToastProvider } from './components/ToastProvider';

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Check for existing token on app load
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const savedUser = getUser();
        if (savedUser) {
          // Verify token with backend
          const isValid = await verifyToken();
          if (isValid) {
            setUser(savedUser);
          } else {
            // Token is invalid, clear storage
            logout();
          }
        }
      } catch (error) {
        console.error('Auth check error:', error);
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = (loggedInUser: User) => {
    setUser(loggedInUser);
  };

  const handleLogout = () => {
    logout();
    setUser(null);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <ToastProvider>
      <div className="min-h-screen font-sans">
        {user ? (
          <Dashboard user={user} onLogout={handleLogout} />
        ) : (
          <Login onLogin={handleLogin} />
        )}
      </div>
    </ToastProvider>
  );
};

export default App;
