import React, { useState } from 'react';
import { useAuth } from '../routes';
import { useNavigate } from 'react-router-dom';
import { Card, Input, Button, LoadingSpinner } from '../components/ui';
import { z } from 'zod';

// Define Zod schema for login form validation
const loginSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters').max(50, 'Username cannot exceed 50 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters').max(100, 'Password cannot exceed 100 characters'),
});

type LoginFormInputs = z.infer<typeof loginSchema>;

/**
 * AuthPage component.
 * Handles user login with form validation and integrates with AuthContext.
 */
const AuthPage: React.FC = () => {
  const [formData, setFormData] = useState<LoginFormInputs>({ username: '', password: '' });
  const [errors, setErrors] = useState<Partial<Record<keyof LoginFormInputs, string>>>({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear specific error when user starts typing
    if (errors[name as keyof LoginFormInputs]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    setLoading(true);

    try {
      // Validate form data using Zod
      loginSchema.parse(formData);
      setErrors({}); // Clear all errors if validation passes

      // Attempt login via AuthContext
      await login(formData.username, formData.password);
      navigate('/dashboard'); // Redirect to dashboard on successful login
    } catch (err) {
      if (err instanceof z.ZodError) {
        // Handle Zod validation errors
        const newErrors: Partial<Record<keyof LoginFormInputs, string>> = {};
        err.errors.forEach((error) => {
          if (error.path.length > 0) {
            newErrors[error.path[0] as keyof LoginFormInputs] = error.message;
          }
        });
        setErrors(newErrors);
      } else if (err instanceof Error) {
        // Handle API or other runtime errors
        setApiError(err.message || 'An unexpected error occurred during login.');
      } else {
        setApiError('An unknown error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-80px)] p-4">
      <Card className="w-full max-w-md p-8 shadow-lg">
        <h1 className="text-3xl font-bold text-center text-gray-900 mb-6">Login</h1>
        <form onSubmit={handleSubmit} noValidate> {/* noValidate to allow custom validation */}
          <div className="mb-4">
            <Input
              label="Username"
              id="username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleChange}
              placeholder="Enter your username"
              error={errors.username}
              aria-invalid={!!errors.username}
              aria-describedby={errors.username ? 'username-error' : undefined}
            />
            {errors.username && (
              <p id="username-error" className="text-red-500 text-sm mt-1" role="alert">
                {errors.username}
              </p>
            )}
          </div>
          <div className="mb-6">
            <Input
              label="Password"
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              error={errors.password}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
            {errors.password && (
              <p id="password-error" className="text-red-500 text-sm mt-1" role="alert">
                {errors.password}
              </p>
            )}
          </div>
          {apiError && (
            <p className="text-red-600 text-center mb-4" role="alert">
              {apiError}
            </p>
          )}
          <Button type="submit" variant="primary" size="large" className="w-full" disabled={loading}>
            {loading ? <LoadingSpinner size="small" /> : 'Login'}
          </Button>
        </form>
        <p className="text-center text-gray-600 text-sm mt-6">
          Don't have an account? <a href="#" className="text-blue-600 hover:underline">Sign Up</a> (Not implemented in this demo)
        </p>
      </Card>
    </div>
  );
};

export default AuthPage;