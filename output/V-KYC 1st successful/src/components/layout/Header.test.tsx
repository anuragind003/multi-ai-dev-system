import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Header from './Header';
import { useAuth } from '@hooks/useAuth'; // Import the hook to mock it

// Mock the useAuth hook
vi.mock('@hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Header', () => {
  const mockLogout = vi.fn();

  beforeEach(() => {
    // Reset mocks before each test
    mockLogout.mockReset();
    mockNavigate.mockReset();

    // Default mock implementation for useAuth (unauthenticated)
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: mockLogout,
      user: null,
      setError: vi.fn(),
    });
  });

  const renderHeader = () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
  };

  it('renders the app title and Home/Login links when unauthenticated', () => {
    renderHeader();
    expect(screen.getByRole('link', { name: /enterpriseapp/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /home/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /dashboard/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument();
  });

  it('renders Dashboard and Logout links when authenticated', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: mockLogout,
      user: { id: '1', email: 'test@example.com', name: 'Test User' },
      setError: vi.fn(),
    });
    renderHeader();
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    expect(screen.getByText(/welcome, test user!/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /login/i })).not.toBeInTheDocument();
  });

  it('calls logout and navigates to login page on logout button click', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: mockLogout.mockResolvedValue(undefined), // Simulate successful logout
      user: { id: '1', email: 'test@example.com', name: 'Test User' },
      setError: vi.fn(),
    });
    renderHeader();

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await userEvent.click(logoutButton);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('disables logout button when authentication is loading', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: true,
      isLoading: true, // Simulate loading state
      error: null,
      login: vi.fn(),
      logout: mockLogout,
      user: { id: '1', email: 'test@example.com', name: 'Test User' },
      setError: vi.fn(),
    });
    renderHeader();

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    expect(logoutButton).toBeDisabled();
  });

  it('navigates to home page when EnterpriseApp title is clicked', async () => {
    renderHeader();
    const homeLink = screen.getByRole('link', { name: /enterpriseapp/i });
    await userEvent.click(homeLink);
    // In a real browser, this would change the URL. For testing, we just check if it's a link.
    // Since we are using BrowserRouter, the link itself handles navigation.
    // We can't directly assert `mockNavigate` for Link components unless we mock Link itself.
    // A more robust test would involve testing the router setup or E2E.
    // For unit test, checking the `href` is sufficient.
    expect(homeLink).toHaveAttribute('href', '/');
  });
});