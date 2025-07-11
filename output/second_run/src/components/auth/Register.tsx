import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { useForm } from '../../hooks/useForm';
import * as yup from 'yup';

const registerSchema = yup.object().shape({
  email: yup.string().email('Invalid email').required('Email is required'),
  password: yup.string().min(6, 'Password must be at least 6 characters').required('Password is required'),
  confirmPassword: yup.string().oneOf([yup.ref('password'), null], 'Passwords must match'),
});

export const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const { values, errors, handleChange, handleSubmit } = useForm({
    initialValues: { email: '', password: '', confirmPassword: '' },
    validationSchema: registerSchema,
    onSubmit: async (values: any) => {
      try {
        await register(values.email, values.password);
        navigate('/login');
      } catch (error: any) {
        console.error('Registration failed:', error);
        // Handle registration errors (e.g., display an error message)
      }
    },
  });

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="bg-white p-8 rounded shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6">Register</h2>
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
          <div className="mb-4">
            <Input
              type="password"
              name="confirmPassword"
              label="Confirm Password"
              value={values.confirmPassword}
              onChange={handleChange}
              error={errors.confirmPassword}
            />
          </div>
          <Button type="submit" className="w-full">
            Register
          </Button>
        </form>
      </div>
    </div>
  );
};