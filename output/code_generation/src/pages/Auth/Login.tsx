// src/pages/Auth/Login.tsx
import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../../hooks/useApp';
import { Input, Button, LoadingSpinner } from '../../components/ui';
import { loginSchema, LoginFormData } from '../../utils';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading, error } = useApp();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (data: LoginFormData) => {
    await login(data.username, data.password);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h1 className="text-3xl font-bold text-center text-text mb-6">Login</h1>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <Input
            id="username"
            label="Username"
            type="text"
            placeholder="Enter your username"
            {...register('username')}
            error={errors.username?.message}
            aria-invalid={errors.username ? "true" : "false"}
          />
          <Input
            id="password"
            label="Password"
            type="password"
            placeholder="Enter your password"
            {...register('password')}
            error={errors.password?.message}
            aria-invalid={errors.password ? "true" : "false"}
          />
          {error && (
            <p className="text-error text-sm text-center mb-4" role="alert">
              {error}
            </p>
          )}
          <Button
            type="submit"
            className="w-full mt-4"
            isLoading={isLoading}
            disabled={isLoading}
            aria-label={isLoading ? "Logging in..." : "Login"}
          >
            {isLoading ? <LoadingSpinner size="sm" color="border-white" /> : 'Login'}
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-text-light">
          Don't have an account? <a href="#" className="text-primary hover:underline">Sign up</a>
        </p>
      </div>
    </div>
  );
};

export default Login;