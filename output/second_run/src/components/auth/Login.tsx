import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { useForm } from '../../hooks/useForm';
import * as yup from 'yup';

const loginSchema = yup.object().shape({
  email: yup.string().email('Invalid email').required('Email is required'),
  password: yup.string().required('Password is required'),
});

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { values, errors, handleChange, handleSubmit } = useForm({
    initialValues: { email: '', password: '' },
    validationSchema: loginSchema,
    onSubmit: async (values: any) => {
      try {
        await login(values.email, values.password);
        navigate('/');
      } catch (error: any) {
        console.error('Login failed:', error);
        // Handle login errors (e.g., display an error message)
      }
    },
  });

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="bg-white p-8 rounded shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6">Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <Input
              type="email"
              name="email"
              label="Email"
              value={values.email}
              onChange={handleChange}
              error={errors.email}
            />
          </div>
          <div className="mb-4">
            <Input
              type="password"
              name="password"
              label="Password"
              value={values.password}
              onChange={handleChange}
              error={errors.password}
            />
          </div>
          <Button type="submit" className="w-full">
            Login
          </Button>
        </form>
      </div>
    </div>
  );
};