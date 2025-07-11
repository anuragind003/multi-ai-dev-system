import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import LoginPage from '@pages/LoginPage';
import { AuthContext } from '@context/AuthContext';
import { BrowserRouter as Router } from 'react-router-dom';

// Mock the useAuth hook
const mockLogin = vi.fn();
const mockUseAuth = vi.fn(() => ({
  isAuthenticated: false,
  loading: false,
  login: mockLogin,
  logout: vi.fn(),
  user: null,
  token: null,
}));

// Helper to render LoginPage within necessary contexts
const renderLoginPage = (authContextValue?: any) => {
  return render(
    <Router>
      <AuthContext.Provider value={authContextValue || mockUseAuth()}>
        <LoginPage />
      </AuthContext.Provider>
    </Router>
  );
};

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset localStorage mock before each test
    window.localStorage.clear();
  });

  it('renders the login form correctly', () => {
    renderLoginPage();
    expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('displays validation errors for empty fields on submit', async () => {
    renderLoginPage();
    const signInButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.click(signInButton);

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('displays validation error for invalid email format', async () => {
    renderLoginPage();
    const emailInput = screen.getByLabelText(/email address/i);
    const signInButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(emailInput, 'invalid-email');
    await userEvent.click(signInButton);

    expect(await screen.findByText(/invalid email address/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('displays validation error for password less than 6 characters', async () => {
    renderLoginPage();
    const passwordInput = screen.getByLabelText(/password/i);
    const signInButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(passwordInput, 'short');
    await userEvent.click(signInButton);

    expect(await screen.findByText(/password must be at least 6 characters/i)).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login function with correct credentials on valid submission', async () => {
    mockLogin.mockResolvedValueOnce(undefined); // Simulate successful login

    renderLoginPage();
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const signInButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    await userEvent.click(signInButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledTimes(1);
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('displays API error message on login failure', async () => {
    const errorMessage = 'Invalid credentials provided.';
    mockLogin.mockRejectedValueOnce({
      response: {
        data: { message: errorMessage },
        status: 400,
      },
    });

    renderLoginPage();
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const signInButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'wrongpassword');
    await userEvent.click(signInButton);

    expect(await screen.findByText(errorMessage)).toBeInTheDocument();
    expect(mockLogin).toHaveBeenCalledTimes(1);
  });

  it('shows loading state on button during submission', async () => {
    mockLogin.mockReturnValueOnce(new Promise(() => {})); // Never resolve to keep loading state

    renderLoginPage();
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const signInButton = screen.getByRole('button', { name: /sign in/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    fireEvent.click(signInButton);

    // Check if button is disabled and spinner is present
    expect(signInButton).toBeDisabled();
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });

  it('redirects to dashboard if already authenticated', async () => {
    // Mock useNavigate to check if it's called
    const mockNavigate = vi.fn();
    vi.mock('react-router-dom', async (importOriginal) => {
      const actual = await importOriginal<typeof import('react-router-dom')>();
      return {
        ...actual,
        useNavigate: () => mockNavigate,
      };
    });

    render(
      <Router>
        <AuthContext.Provider value={{
          isAuthenticated: true,
          loading: false,
          login: mockLogin,
          logout: vi.fn(),
          user: { id: '1', email: 'test@example.com' },
          token: 'mock-token',
        }}>
          <LoginPage />
        </AuthContext.Provider>
      </Router>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
  });
});