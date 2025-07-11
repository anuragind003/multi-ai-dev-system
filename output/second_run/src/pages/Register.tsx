import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useForm } from '../hooks/useForm';
import { Input } from '../components/Input';
import { Button } from '../components/Button';

export const Register = () => {
  const navigate = useNavigate();
  const { register, error: authError } = useAuth();

  const { values, handleChange, handleSubmit, errors } = useForm({
    initialValues: { email: '', password: '', confirmPassword: '' },
    onSubmit: async (values) => {
      if (values.password !== values.confirmPassword) {
        return; // Validation handled in useForm
      }
      const success = await register(values.email, values.password);
      if (success) {
        navigate('/login');
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
      if (values.password !== values.confirmPassword) {
        errors.confirmPassword = 'Passwords do not match';
      }
      return errors;
    },
  });

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="bg-white dark:bg-gray-800 shadow-md rounded px-8 pt-6 pb-8 mb-4 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6">Register</h2>
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
          <Input
            label="Confirm Password"
            type="password"
            id="confirmPassword"
            name="confirmPassword"
            value={values.confirmPassword}
            onChange={handleChange}
            error={errors.confirmPassword}
          />
          <Button type="submit" className="w-full">Register</Button>
        </form>
        <p className="text-sm mt-4">
          Already have an account? <Link to="/login" className="text-blue-500 hover:underline">Login</Link>
        </p>
      </div>
    </div>
  );
};