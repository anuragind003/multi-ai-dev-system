import React, { useState, useEffect } from 'react';
import { useAuth } from '@context/AuthContext';
import { useNavigate } from 'react-router-dom';
import Input from '@components/ui/Input';
import Button from '@components/ui/Button';
import Card from '@components/ui/Card';
import { validateLoginForm, LoginFormSchema } from '@utils/validation';
import { ZodError } from 'zod';

const LoginPage: React.FC = () => {
  const [formData, setFormData] = useState<LoginFormSchema>({
    usernameOrEmail: '',
    password: '',
  });
  const [formErrors, setFormErrors] = useState<Partial<LoginFormSchema>>({});
  const { login, isAuthenticated, isLoading, error: authError } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for the field as user types
    if (formErrors[name as keyof LoginFormSchema]) {
      setFormErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormErrors({}); // Clear previous form errors
    try {
      validateLoginForm(formData); // Validate using Zod
      await login({
        username: formData.usernameOrEmail,
        email: formData.usernameOrEmail, // Backend should handle either username or email
        password: formData.password,
      });
    } catch (err) {
      if (err instanceof ZodError) {
        const newErrors: Partial<LoginFormSchema> = {};
        err.errors.forEach((validationError) => {
          if (validationError.path[0]) {
            newErrors[validationError.path[0] as keyof LoginFormSchema] = validationError.message;
          }
        });
        setFormErrors(newErrors);
      } else {
        // AuthContext already sets a general error for API failures
        console.error('Login submission error:', err);
      }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <Card className="w-full max-w-md" ariaLabel="Login Form">
        <h1 className="text-3xl font-bold text-center text-gray-900 mb-8">
          Welcome Back!
        </h1>
        <form onSubmit={handleSubmit} noValidate>
          <Input
            id="usernameOrEmail"
            name="usernameOrEmail"
            label="Username or Email"
            type="text"
            value={formData.usernameOrEmail}
            onChange={handleChange}
            placeholder="Enter your username or email"
            error={formErrors.usernameOrEmail}
            required
            autoComplete="username"
          />
          <Input
            id="password"
            name="password"
            label="Password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            placeholder="Enter your password"
            error={formErrors.password}
            required
            autoComplete="current-password"
          />

          {authError && (
            <div className="bg-danger-light text-danger border border-danger rounded-md p-3 mb-4 text-sm" role="alert">
              {authError}
            </div>
          )}

          <Button
            type="submit"
            className="w-full mt-6"
            isLoading={isLoading}
            disabled={isLoading}
            aria-label="Login to your account"
          >
            {isLoading ? 'Logging In...' : 'Login'}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <a href="#" className="font-medium text-primary hover:text-primary-dark">
            Sign Up
          </a>
        </div>
        <div className="mt-4 text-center text-sm text-gray-600">
          <a href="#" className="font-medium text-primary hover:text-primary-dark">
            Forgot Password?
          </a>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;