import React from 'react';
import { useAuth } from '@/context/AppProviders';
import { Button } from '@/components/ui';
import { Link } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <div className="flex flex-col min-h-screen">
      <Header isAuthenticated={isAuthenticated} user={user} onLogout={logout} />
      <main className="flex-grow container mx-auto px-4 py-8">
        {children}
      </main>
      <Footer />
    </div>
  );
};

interface HeaderProps {
  isAuthenticated: boolean;
  user: { username: string } | null;
  onLogout: () => void;
}

const Header: React.FC<HeaderProps> = ({ isAuthenticated, user, onLogout }) => {
  return (
    <header className="bg-primary text-white shadow-md py-4 px-6">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-2xl font-bold tracking-tight">
          FileUploader
        </Link>
        <nav>
          <ul className="flex space-x-6 items-center">
            {isAuthenticated ? (
              <>
                <li>
                  <Link to="/dashboard" className="hover:text-secondary transition-colors duration-200">Dashboard</Link>
                </li>
                <li>
                  <Link to="/profile" className="hover:text-secondary transition-colors duration-200">Profile</Link>
                </li>
                <li className="text-sm text-gray-200">
                  Welcome, {user?.username || 'User'}!
                </li>
                <li>
                  <Button onClick={onLogout} variant="ghost" size="sm" className="text-white hover:bg-primary/80">
                    Logout
                  </Button>
                </li>
              </>
            ) : (
              <li>
                <Link to="/login">
                  <Button variant="outline" size="sm" className="text-white border-white hover:bg-white hover:text-primary">
                    Login
                  </Button>
                </Link>
              </li>
            )}
          </ul>
        </nav>
      </div>
    </header>
  );
};

const Footer: React.FC = () => {
  return (
    <footer className="bg-dark text-gray-300 py-6 px-6 mt-auto">
      <div className="container mx-auto text-center text-sm">
        <p>&copy; {new Date().getFullYear()} FileUploader. All rights reserved.</p>
        <p className="mt-2">
          <a href="#" className="hover:text-white transition-colors duration-200">Privacy Policy</a> |{' '}
          <a href="#" className="hover:text-white transition-colors duration-200">Terms of Service</a>
        </p>
      </div>
    </footer>
  );
};