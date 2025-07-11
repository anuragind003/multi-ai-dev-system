import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthContextProvider, useAuth } from '../context/AuthContext.tsx';
import { api } from '../services/api.ts';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import React from 'react';

// Mock the API service
vi.mock('../services/api.ts', () => ({
  api: {
    login: vi.fn(),
    register: vi.fn(),
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
    getDashboardData: vi.fn(),
  },
}));

// Helper component to consume the AuthContext
const TestComponent: React.FC = () => {
  const { isAuthenticated, user, isLoading, login, logout, register, checkAuthStatus } = useAuth();

  return (
    <div>
      <span data-testid="is-authenticated">{isAuthenticated ? 'true' : 'false'}</span>
      <span data-testid="user-email">{user?.email || 'N/A'}</span>
      <span data-testid="is-loading">{isLoading ? 'true' : 'false'}</span>
      <button onClick={() => login('test@example.com', 'password123')}>Login</button>
      <button onClick={logout}>Logout</button>
      <button onClick={() => register('testuser', 'test@example.com', 'password123')}>Register</button>
      <button onClick={checkAuthStatus}>Check Auth Status</button>
    </div>
  );
};

// Helper to render with AuthContextProvider and BrowserRouter
const renderWithAuth = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AuthContextProvider>{ui}</AuthContextProvider>} />
      </Routes>
    </BrowserRouter>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    localStorage.clear(); // Clear localStorage
    // Mock initial getProfile to simulate no token
    (api.getProfile as vi.Mock).mockRejectedValue(new Error('No token'));
  });

  it('should initialize as loading and then unauthenticated if no token', async () => {
    renderWithAuth(<TestComponent />);

    // Initially loading
    expect(screen.getByTestId('is-loading')).toHaveTextContent('true');

    // After initial check, should be unauthenticated
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('user-email')).toHaveTextContent('N/A');
    });
  });

  it('should log in a user successfully', async () => {
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', createdAt: '2023-01-01T00:00:00Z', updatedAt: '2023-01-01T00:00:00Z' };
    (api.login as vi.Mock).mockResolvedValue({ token: 'mock_token', user: mockUser });

    renderWithAuth(<TestComponent />);

    await waitFor(() => expect(screen.getByTestId('is-loading')).toHaveTextContent('false'));

    await userEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith('test@example.com', 'password123');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      expect(localStorage.getItem('authToken')).toBe('mock_token');
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });
  });

  it('should register a user successfully', async () => {
    const mockUser = { id: '2', username: 'newuser', email: 'new@example.com', createdAt: '2023-01-01T00:00:00Z', updatedAt: '2023-01-01T00:00:00Z' };
    (api.register as vi.Mock).mockResolvedValue({ token: 'new_token', user: mockUser });

    renderWithAuth(<TestComponent />);

    await waitFor(() => expect(screen.getByTestId('is-loading')).toHaveTextContent('false'));

    await userEvent.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => {
      expect(api.register).toHaveBeenCalledWith('testuser', 'test@example.com', 'password123');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user-email')).toHaveTextContent('new@example.com');
      expect(localStorage.getItem('authToken')).toBe('new_token');
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });
  });

  it('should log out a user', async () => {
    // Simulate already logged in
    localStorage.setItem('authToken', 'existing_token');
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', createdAt: '2023-01-01T00:00:00Z', updatedAt: '2023-01-01T00:00:00Z' };
    (api.getProfile as vi.Mock).mockResolvedValue(mockUser);

    renderWithAuth(<TestComponent />);

    // Wait for initial check to complete and user to be authenticated
    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    });

    await userEvent.click(screen.getByRole('button', { name: /logout/i }));

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('user-email')).toHaveTextContent('N/A');
      expect(localStorage.getItem('authToken')).toBeNull();
    });
  });

  it('should re-authenticate on load if token exists and is valid', async () => {
    localStorage.setItem('authToken', 'valid_token');
    const mockUser = { id: '1', username: 'testuser', email: 'test@example.com', createdAt: '2023-01-01T00:00:00Z', updatedAt: '2023-01-01T00:00:00Z' };
    (api.getProfile as vi.Mock).mockResolvedValue(mockUser);

    renderWithAuth(<TestComponent />);

    await waitFor(() => {
      expect(api.getProfile).toHaveBeenCalled();
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });
  });

  it('should clear auth if token exists but is invalid', async () => {
    localStorage.setItem('authToken', 'invalid_token');
    (api.getProfile as vi.Mock).mockRejectedValue(new Error('Invalid token'));

    renderWithAuth(<TestComponent />);

    await waitFor(() => {
      expect(api.getProfile).toHaveBeenCalled();
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('user-email')).toHaveTextContent('N/A');
      expect(localStorage.getItem('authToken')).toBeNull();
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });
  });
});