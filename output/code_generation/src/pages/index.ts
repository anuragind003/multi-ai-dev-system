import React, { useState, FormEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, useFilters } from '../hooks/useAppHooks';
import { Button, Input, Card } from '../components/ui'; // Reusable UI components
import { FilterBar, CalendarView, DataDisplay } from '../components/dashboard/DashboardComponents'; // Dashboard specific components
import { fetchDashboardData } from '../services/api'; // API service
import { LoadingSpinner } from '../components/ui'; // Loading spinner

// --- LoginPage ---
export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (!username || !password) {
      setError('Please enter both username and password.');
      setIsLoading(false);
      return;
    }

    const success = await login(username, password);
    setIsLoading(false);

    if (success) {
      navigate('/dashboard', { replace: true });
    } else {
      setError('Invalid username or password.');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-md p-8">
        <h2 className="text-3xl font-bold text-center text-primary mb-6">Login</h2>
        <form onSubmit={handleSubmit}>
          <Input
            label="Username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            aria-label="Username"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            aria-label="Password"
            required
          />
          {error && <p className="text-red-500 text-sm mb-4" role="alert">{error}</p>}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? <LoadingSpinner /> : 'Login'}
          </Button>
        </form>
      </Card>
    </div>
  );
};

// --- DashboardPage ---
export const DashboardPage: React.FC = () => {
  const { dateFilter, monthFilter, yearFilter, searchFilter } = useFilters();
  const [dashboardData, setDashboardData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const getData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchDashboardData({ date: dateFilter, month: monthFilter, year: yearFilter, search: searchFilter });
        setDashboardData(data);
      } catch (err) {
        setError('Failed to fetch dashboard data. Please try again.');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    getData();
  }, [dateFilter, monthFilter, yearFilter, searchFilter]);

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-text">Dashboard Overview</h2>
      <FilterBar />
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <Card className="bg-red-100 border-red-400 text-red-700 p-4" role="alert">
          <p>{error}</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <CalendarView data={dashboardData} />
          </div>
          <div className="lg:col-span-1">
            <DataDisplay data={dashboardData} />
          </div>
        </div>
      )}
    </div>
  );
};

// --- ProfilePage ---
export const ProfilePage: React.FC = () => {
  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-text">User Profile</h2>
      <Card>
        <h3 className="text-xl font-semibold text-text mb-4">Account Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-text-light">Username:</p>
            <p className="font-medium text-text">user@example.com</p>
          </div>
          <div>
            <p className="text-text-light">Role:</p>
            <p className="font-medium text-text">Administrator</p>
          </div>
          <div>
            <p className="text-text-light">Last Login:</p>
            <p className="font-medium text-text">2023-10-26 10:30 AM</p>
          </div>
        </div>
        <Button className="mt-6" variant="outline">Edit Profile</Button>
      </Card>
    </div>
  );
};

// --- SettingsPage ---
export const SettingsPage: React.FC = () => {
  const [notificationEnabled, setNotificationEnabled] = useState(true);
  const [theme, setTheme] = useState('light');

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-text">Settings</h2>
      <Card>
        <h3 className="text-xl font-semibold text-text mb-4">General Settings</h3>
        <div className="flex items-center justify-between mb-4">
          <label htmlFor="notifications" className="text-text-light cursor-pointer">Enable Notifications</label>
          <input
            type="checkbox"
            id="notifications"
            checked={notificationEnabled}
            onChange={(e) => setNotificationEnabled(e.target.checked)}
            className="h-5 w-5 text-primary rounded border-gray-300 focus:ring-primary"
            role="switch"
            aria-checked={notificationEnabled}
          />
        </div>
        <div className="mb-4">
          <label htmlFor="theme-select" className="block text-text-light mb-2">Theme</label>
          <select
            id="theme-select"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            className="block w-full px-3 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            aria-label="Select theme"
          >
            <option value="light">Light</option>
            <option value="dark">Dark (Coming Soon)</option>
          </select>
        </div>
        <Button className="mt-4">Save Settings</Button>
      </Card>
    </div>
  );
};