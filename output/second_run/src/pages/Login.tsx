import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useForm } from '../hooks/useForm';
import { Input } from '../components/Input';
import { Button } from '../components/Button';

export const Login = () => {
  const navigate = useNavigate();
  const { login, error: authError } = useAuth();

  const { values, handleChange, handleSubmit, errors } = useForm({
    initialValues: { email: '', password: '' },
    onSubmit: async (values) => {
      const success = await login(values.email, values.password);
      if (success) {
        navigate('/dashboard');
      }
    },
    validate: (values) => {
      const errors: { [key: string]: string } = {};
      if (!values.email) {
        errors.email = 'Email is required';
      }
      if (!values.password) {
        errors.password = 'Password is required';
      }
      return errors;
    },
  });

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="bg-white dark:bg-gray-800 shadow-md rounded px-8 pt-6 pb-8 mb-4 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6">Login</h2>
        {authError && <p className="text-red-500 text-sm mb-4">{authError}</p>}
        <form onSubmit={handleSubmit}>
          <Input
            label="Email"
            type="email"
            id="email"
            name="email"
            value={values.email}
            onChange={handleChange}
            error={errors.email}
          />
          <Input
            label="Password"
            type="password"
            id="password"
            name="password"
            value={values.password}
            onChange={handleChange}
            error={errors.password}
          />
          <Button type="submit" className="w-full">Login</Button>
        </form>
        <p className="text-sm mt-4">
          Don't have an account? <Link to="/register" className="text-blue-500 hover:underline">Register</Link>
        </p>
      </div>
    </div>
  );
};