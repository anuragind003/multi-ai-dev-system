// src/tests/Dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import Dashboard from '../pages/Dashboard';
import { GlobalContextProvider } from '../context/GlobalContext';
import * as apiService from '../api/apiService';
import { Recording } from '../types';

// Mock the API service
const mockRecordings: Recording[] = [
  { id: '1', title: 'Meeting 1', duration: 3600, date: '2023-01-15T10:00:00Z', size: 10.5, url: 'http://example.com/rec1' },
  { id: '2', title: 'Lecture 2', duration: 2700, date: '2023-02-20T14:30:00Z', size: 8.2, url: 'http://example.com/rec2' },
];

vi.mock('../api/apiService', async (importOriginal) => {
  const actual = await importOriginal<typeof apiService>();
  return {
    ...actual,
    getRecordings: vi.fn(() => Promise.resolve({ success: true, data: mockRecordings })),
    loginUser: vi.fn(), // Mock loginUser as well if it's used in context setup
  };
});

// Mock useApp hook to control authentication state for tests
vi.mock('../hooks/useApp', () => ({
  useApp: vi.fn(() => ({
    user: { id: 'test', username: 'testuser', email: 'test@example.com', token: 'fake-token' },
    isAuthenticated: true,
    recordings: mockRecordings,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    fetchRecordings: vi.fn(),
  })),
}));

describe('Dashboard', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    // Ensure useApp mock is correctly set for each test
    const { useApp } = vi.mocked(import('../hooks/useApp'));
    useApp.mockReturnValue({
      user: { id: 'test', username: 'testuser', email: 'test@example.com', token: 'fake-token' },
      isAuthenticated: true,
      recordings: mockRecordings,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      fetchRecordings: vi.fn(() => Promise.resolve()), // Mock fetchRecordings to resolve
    });
  });

  it('renders dashboard title', async () => {
    render(
      <BrowserRouter>
        <GlobalContextProvider>
          <Dashboard />
        </GlobalContextProvider>
      </BrowserRouter>
    );

    expect(screen.getByText(/Recordings Dashboard/i)).toBeInTheDocument();
  });

  it('displays recordings in the table', async () => {
    render(
      <BrowserRouter>
        <GlobalContextProvider>
          <Dashboard />
        </GlobalContextProvider>
      </BrowserRouter>
    );

    // Wait for the table data to appear
    await waitFor(() => {
      expect(screen.getByText('Meeting 1')).toBeInTheDocument();
      expect(screen.getByText('Lecture 2')).toBeInTheDocument();
      expect(screen.getByText('01:00:00')).toBeInTheDocument(); // Formatted duration
      expect(screen.getByText('10.5 MB')).toBeInTheDocument(); // Formatted size
    });
  });

  it('shows loading spinner when data is loading', () => {
    // Temporarily override useApp mock for this test case
    const { useApp } = vi.mocked(import('../hooks/useApp'));
    useApp.mockReturnValue({
      user: null,
      isAuthenticated: false,
      recordings: [],
      isLoading: true, // Set isLoading to true
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      fetchRecordings: vi.fn(),
    });

    render(
      <BrowserRouter>
        <GlobalContextProvider>
          <Dashboard />
        </GlobalContextProvider>
      </BrowserRouter>
    );

    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });

  it('displays error message when fetching recordings fails', async () => {
    const errorMessage = 'Failed to fetch recordings from server.';
    // Temporarily override useApp mock for this test case
    const { useApp } = vi.mocked(import('../hooks/useApp'));
    useApp.mockReturnValue({
      user: null,
      isAuthenticated: false,
      recordings: [],
      isLoading: false,
      error: errorMessage, // Set error message
      login: vi.fn(),
      logout: vi.fn(),
      fetchRecordings: vi.fn(),
    });

    render(
      <BrowserRouter>
        <GlobalContextProvider>
          <Dashboard />
        </GlobalContextProvider>
      </BrowserRouter>
    );

    expect(screen.getByText(/Error Loading Recordings/i)).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });
});