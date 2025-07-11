// src/components/forms/LoginForm.tsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Input, Button, Card } from '@/components/ui/CommonUI';
import { useAuth } from '@/context/AuthContext';
import { LoginFormInputs } from '@/types';
import { api } from '@/services/api';
import { toast } from 'react-toastify';
import { FaEnvelope, FaLock, FaSignInAlt } from 'react-icons/fa';

const loginSchema = z.object({
  email: z.string().email({ message: 'Invalid email address' }),
  password: z.string().min(6, { message: 'Password must be at least 6 characters' }),
});

const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormInputs>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormInputs) => {
    setIsLoading(true);
    try {
      const response = await api.login(data);
      if (response.success && response.data) {
        login(response.data.token, response.data.user);
        // AuthContext's useEffect will handle redirection to dashboard
      } else {
        toast.error(response.error || 'Login failed. Please check your credentials.');
      }
    } catch (error) {
      console.error('Login API call error:', error);
      toast.error('An unexpected error occurred during login.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card title="Login to Your Account" className="w-full max-w-md mx-auto animate-fadeIn">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Email Address"
          type="email"
          placeholder="your@example.com"
          {...register('email')}
          error={errors.email?.message}
          icon={<FaEnvelope className="text-gray-400" />}
          aria-invalid={errors.email ? "true" : "false"}
        />
        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          {...register('password')}
          error={errors.password?.message}
          icon={<FaLock className="text-gray-400" />}
          aria-invalid={errors.password ? "true" : "false"}
        />
        <Button
          type="submit"
          className="w-full"
          isLoading={isLoading}
          icon={<FaSignInAlt />}
          aria-label="Sign in"
        >
          Sign In
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-text-light">
        Don't have an account?{' '}
        <a href="#" className="text-primary hover:underline">
          Sign Up
        </a>
      </p>
    </Card>
  );
};

export default LoginForm;