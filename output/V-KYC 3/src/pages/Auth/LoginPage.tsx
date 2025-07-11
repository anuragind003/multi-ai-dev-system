import React, { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth';
import Button from '@components/ui/Button';
import Input from '@components/ui/Input';
import { authService, ApiResponse, AuthResponseData } from '@api/index';

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [errors, setErrors] = useState<{ username?: string; password?: string; api?: string }>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const validateForm = () => {
    const newErrors: { username?: string; password?: string } = {};
    if (!username.trim()) {
      newErrors.username = 'Username is required.';
    }
    if (!password.trim()) {
      newErrors.password = 'Password is required.';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters long.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrors({}); // Clear previous errors
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    try {
      const response: ApiResponse<AuthResponseData> = await authService.login({ username, password });

      if (response.success && response.data) {
        login(response.data.token, response.data.user);
        navigate('/dashboard');
      } else {
        setErrors({ api: response.message || 'Login failed. Please try again.' });
      }
    } catch (error) {
      console.error('Login API call failed:', error);
      setErrors({ api: 'Network error. Please check your connection.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-120px)] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-lg shadow-card">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-text">
            Sign in to your account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
          <Input
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            required
            label="Username"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            error={errors.username}
            aria-label="Username input"
          />
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            label="Password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={errors.password}
            aria-label="Password input"
          />

          {errors.api && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
              <span className="block sm:inline">{errors.api}</span>
            </div>
          )}

          <div>
            <Button
              type="submit"
              isLoading={isLoading}
              className="w-full"
              aria-label="Sign in button"
            >
              Sign In
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;