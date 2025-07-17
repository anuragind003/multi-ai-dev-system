import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../../../context/AuthContext';
import { Button, Input, Card } from '../../ui/CommonUI';
import { useNavigate } from 'react-router-dom';

const authSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters').max(50, 'Username cannot exceed 50 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters').max(100, 'Password cannot exceed 100 characters'),
});

type AuthFormInputs = z.infer<typeof authSchema>;

interface AuthFormProps {
  type: 'login' | 'register';
}

export const AuthForm: React.FC<AuthFormProps> = ({ type }) => {
  const { login, register, isLoading, error } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register: formRegister,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<AuthFormInputs>({
    resolver: zodResolver(authSchema),
  });

  const onSubmit = async (data: AuthFormInputs) => {
    setFormError(null);
    try {
      if (type === 'login') {
        await login(data);
      } else {
        await register(data);
      }
      reset();
      navigate('/dashboard'); // Redirect to dashboard on success
    } catch (err: any) {
      setFormError(err.message || `Failed to ${type}. Please try again.`);
    }
  };

  const title = type === 'login' ? 'Login to Your Account' : 'Create a New Account';
  const submitButtonText = type === 'login' ? 'Login' : 'Register';
  const toggleLinkText = type === 'login' ? 'Need an account? Register' : 'Already have an account? Login';
  const toggleLinkPath = type === 'login' ? '/register' : '/login';

  return (
    <div className="flex items-center justify-center min-h-screen bg-background p-4">
      <Card className="w-full max-w-md">
        <h2 className="text-2xl font-bold text-center text-text mb-6">{title}</h2>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <Input
            label="Username"
            type="text"
            placeholder="Your username"
            {...formRegister('username')}
            error={errors.username?.message}
            autoComplete="username"
          />
          <Input
            label="Password"
            type="password"
            placeholder="Your password"
            {...formRegister('password')}
            error={errors.password?.message}
            autoComplete={type === 'login' ? 'current-password' : 'new-password'}
          />

          {(formError || error) && (
            <p className="text-error text-sm mb-4" role="alert">
              {formError || error}
            </p>
          )}

          <Button type="submit" className="w-full mt-2" disabled={isLoading}>
            {isLoading ? 'Processing...' : submitButtonText}
          </Button>
        </form>
        <p className="text-center text-sm text-text-light mt-4">
          <a href={toggleLinkPath} className="text-primary hover:underline">
            {toggleLinkText}
          </a>
        </p>
      </Card>
    </div>
  );
};