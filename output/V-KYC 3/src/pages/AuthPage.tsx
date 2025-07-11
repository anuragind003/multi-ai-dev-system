import React, { useState } from 'react';
import Input from '../components/ui/Input.tsx';
import Button from '../components/ui/Button.tsx';
import useFormValidation from '../hooks/useFormValidation.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useNavigate } from 'react-router-dom';

const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const { login, register, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const initialFormState = {
    username: '',
    password: '',
  };

  const validationRules = {
    username: {
      required: true,
      minLength: 3,
      maxLength: 20,
      pattern: /^[a-zA-Z0-9_]+$/,
      custom: (value: string) => {
        if (value.includes(' ')) return 'Username cannot contain spaces.';
        return undefined;
      },
    },
    password: {
      required: true,
      minLength: 6,
    },
  };

  const { formData, errors, handleChange, handleSubmit, isSubmitting, setErrors } =
    useFormValidation(initialFormState, validationRules);

  const handleAuthSubmit = async () => {
    try {
      if (isLogin) {
        await login(formData);
      } else {
        await register(formData);
      }
      navigate('/dashboard'); // Redirect to dashboard on successful auth
    } catch (error) {
      setErrors({ _form: (error as Error).message || 'Authentication failed.' });
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white p-8 rounded-lg shadow-md mt-10">
      <h2 className="text-3xl font-bold text-center text-gray-800 mb-6">
        {isLogin ? 'Login' : 'Register'}
      </h2>
      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(handleAuthSubmit); }}>
        <Input
          id="username"
          name="username"
          label="Username"
          type="text"
          value={formData.username}
          onChange={handleChange}
          error={errors.username}
          placeholder="Enter your username"
          autoComplete="username"
        />
        <Input
          id="password"
          name="password"
          label="Password"
          type="password"
          value={formData.password}
          onChange={handleChange}
          error={errors.password}
          placeholder="Enter your password"
          autoComplete={isLogin ? "current-password" : "new-password"}
        />

        {errors._form && (
          <p className="text-danger text-sm mb-4" role="alert">
            {errors._form}
          </p>
        )}

        <Button
          type="submit"
          className="w-full mt-4"
          isLoading={isSubmitting || authLoading}
          disabled={isSubmitting || authLoading}
        >
          {isLogin ? 'Login' : 'Register'}
        </Button>
      </form>

      <p className="text-center text-sm text-gray-600 mt-6">
        {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
        <button
          onClick={() => {
            setIsLogin(!isLogin);
            setErrors({}); // Clear errors when switching form type
            setFormData(initialFormState); // Reset form data
          }}
          className="text-primary hover:underline font-medium"
          type="button"
        >
          {isLogin ? 'Register here' : 'Login here'}
        </button>
      </p>
    </div>
  );
};

export default AuthPage;