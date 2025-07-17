import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
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

describe('LoginPage', () => {
  const mockLogin = vi.fn();
  const mockSetError = vi.fn();

  beforeEach(() => {
    // Reset mocks before each test
    mockLogin.mockReset();
    mockSetError.mockReset();
    mockNavigate.mockReset();

    // Default mock implementation for useAuth
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: mockLogin,
      logout: vi.fn(),
      user: null,
      setError: mockSetError,
    });
  });

  const renderLoginPage = () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
  };

  it('renders the login form', () => {
    renderLoginPage();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('displays validation errors for empty fields', async () => {
    renderLoginPage();
    const loginButton = screen.getByRole('button', { name: /login/i });

    await userEvent.click(loginButton);

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('displays validation error for invalid email format', async () => {
    renderLoginPage();
    const emailInput = screen.getByLabelText(/email/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await userEvent.type(emailInput, 'invalid-email');
    await userEvent.click(loginButton);

    expect(await screen.findByText(/invalid email address/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login function with correct credentials on submit', async () => {
    mockLogin.mockResolvedValue(true); // Simulate successful login

    renderLoginPage();
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    await userEvent.click(loginButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });

  it('displays error message from context on failed login', async () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      error: 'Invalid credentials provided.',
      login: mockLogin,
      logout: vi.fn(),
      user: null,
      setError: mockSetError,
    });

    renderLoginPage();
    expect(screen.getByRole('alert')).toHaveTextContent(/invalid credentials provided/i);
  });

  it('shows loading state during login', async () => {
    mockLogin.mockReturnValue(new Promise(() => {})); // Never resolve to keep loading state

    renderLoginPage();
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    await userEvent.click(loginButton);

    // Re-mock useAuth to simulate isLoading state after form submission
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: false,
      isLoading: true, // Simulate loading after submission
      error: null,
      login: mockLogin,
      logout: vi.fn(),
      user: null,
      setError: mockSetError,
    });
    renderLoginPage(); // Re-render to pick up the new mock state

    expect(loginButton).toBeDisabled();
    expect(screen.getByLabelText('Loading')).toBeInTheDocument(); // Check for spinner
  });

  it('redirects to dashboard if already authenticated', () => {
    (useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: mockLogin,
      logout: vi.fn(),
      user: { id: '1', email: 'authenticated@example.com', name: 'Auth User' },
      setError: mockSetError,
    });

    renderLoginPage();
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });
});