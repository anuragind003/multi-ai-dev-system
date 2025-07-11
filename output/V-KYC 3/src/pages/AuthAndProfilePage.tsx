import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Routes, Route, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../context/AuthContext.tsx';
import { Input, Button, Card, LoadingSpinner } from '../components/ui/CommonUI.tsx';
import { api } from '../services/api.ts';

// --- Schemas ---
const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

const registerSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

const profileSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
});

const passwordSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string().min(6, 'New password must be at least 6 characters'),
  confirmNewPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmNewPassword, {
  message: "New passwords don't match",
  path: ["confirmNewPassword"],
});

type LoginFormInputs = z.infer<typeof loginSchema>;
type RegisterFormInputs = z.infer<typeof registerSchema>;
type ProfileFormInputs = z.infer<typeof profileSchema>;
type PasswordFormInputs = z.infer<typeof passwordSchema>;

// --- Login Form Component ---
const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormInputs>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormInputs) => {
    setError(null);
    setIsLoading(true);
    try {
      await login(data.email, data.password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="p-8 max-w-md mx-auto">
      <h2 className="text-3xl font-bold text-text mb-6 text-center">Login</h2>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <Input
          label="Email"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          aria-invalid={errors.email ? "true" : "false"}
        />
        <Input
          label="Password"
          type="password"
          {...register('password')}
          error={errors.password?.message}
          aria-invalid={errors.password ? "true" : "false"}
        />
        {error && <p className="text-red-500 text-sm text-center" role="alert">{error}</p>}
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? <LoadingSpinner size="sm" /> : 'Login'}
        </Button>
      </form>
      <p className="mt-6 text-center text-text-light">
        Don't have an account? <Link to="/auth/register" className="text-primary hover:underline">Register</Link>
      </p>
    </Card>
  );
};

// --- Register Form Component ---
const RegisterForm: React.FC = () => {
  const { register: authRegister } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterFormInputs>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormInputs) => {
    setError(null);
    setIsLoading(true);
    try {
      await authRegister(data.username, data.email, data.password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="p-8 max-w-md mx-auto">
      <h2 className="text-3xl font-bold text-text mb-6 text-center">Register</h2>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <Input
          label="Username"
          type="text"
          {...register('username')}
          error={errors.username?.message}
          aria-invalid={errors.username ? "true" : "false"}
        />
        <Input
          label="Email"
          type="email"
          {...register('email')}
          error={errors.email?.message}
          aria-invalid={errors.email ? "true" : "false"}
        />
        <Input
          label="Password"
          type="password"
          {...register('password')}
          error={errors.password?.message}
          aria-invalid={errors.password ? "true" : "false"}
        />
        <Input
          label="Confirm Password"
          type="password"
          {...register('confirmPassword')}
          error={errors.confirmPassword?.message}
          aria-invalid={errors.confirmPassword ? "true" : "false"}
        />
        {error && <p className="text-red-500 text-sm text-center" role="alert">{error}</p>}
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? <LoadingSpinner size="sm" /> : 'Register'}
        </Button>
      </form>
      <p className="mt-6 text-center text-text-light">
        Already have an account? <Link to="/auth/login" className="text-primary hover:underline">Login</Link>
      </p>
    </Card>
  );
};

// --- Profile Settings Component ---
const ProfileSettings: React.FC = () => {
  const { user, setUser } = useAuth();
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm<ProfileFormInputs>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      username: user?.username || '',
      email: user?.email || '',
      firstName: user?.firstName || '',
      lastName: user?.lastName || '',
    },
  });

  useEffect(() => {
    reset({
      username: user?.username || '',
      email: user?.email || '',
      firstName: user?.firstName || '',
      lastName: user?.lastName || '',
    });
  }, [user, reset]);

  const onProfileSubmit = async (data: ProfileFormInputs) => {
    setMessage(null);
    setIsLoading(true);
    try {
      const updatedUser = await api.updateProfile(data);
      setUser(updatedUser); // Update user in context
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
      reset(updatedUser); // Reset form with new data
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update profile.' });
    } finally {
      setIsLoading(false);
    }
  };

  const { register: registerPassword, handleSubmit: handlePasswordSubmit, reset: resetPassword, formState: { errors: passwordErrors, isDirty: isPasswordDirty } } = useForm<PasswordFormInputs>({
    resolver: zodResolver(passwordSchema),
  });

  const onChangePasswordSubmit = async (data: PasswordFormInputs) => {
    setMessage(null);
    setIsLoading(true);
    try {
      await api.changePassword(data.currentPassword, data.newPassword);
      setMessage({ type: 'success', text: 'Password changed successfully!' });
      resetPassword();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to change password.' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md-soft border border-border">
      <h1 className="text-3xl font-bold text-text mb-6">User Profile & Settings</h1>

      {message && (
        <div className={`p-3 mb-4 rounded-md text-sm ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`} role="alert">
          {message.text}
        </div>
      )}

      {/* Profile Information */}
      <Card className="p-6 mb-8">
        <h2 className="text-xl font-semibold text-text mb-4">Personal Information</h2>
        <form onSubmit={handleSubmit(onProfileSubmit)} className="space-y-5">
          <Input
            label="Username"
            type="text"
            {...register('username')}
            error={errors.username?.message}
            aria-invalid={errors.username ? "true" : "false"}
          />
          <Input
            label="Email"
            type="email"
            {...register('email')}
            error={errors.email?.message}
            aria-invalid={errors.email ? "true" : "false"}
          />
          <Input
            label="First Name"
            type="text"
            {...register('firstName')}
            error={errors.firstName?.message}
            aria-invalid={errors.firstName ? "true" : "false"}
          />
          <Input
            label="Last Name"
            type="text"
            {...register('lastName')}
            error={errors.lastName?.message}
            aria-invalid={errors.lastName ? "true" : "false"}
          />
          <Button type="submit" disabled={!isDirty || isLoading}>
            {isLoading ? <LoadingSpinner size="sm" /> : 'Save Profile'}
          </Button>
        </form>
      </Card>

      {/* Change Password */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold text-text mb-4">Change Password</h2>
        <form onSubmit={handlePasswordSubmit(onChangePasswordSubmit)} className="space-y-5">
          <Input
            label="Current Password"
            type="password"
            {...registerPassword('currentPassword')}
            error={passwordErrors.currentPassword?.message}
            aria-invalid={passwordErrors.currentPassword ? "true" : "false"}
          />
          <Input
            label="New Password"
            type="password"
            {...registerPassword('newPassword')}
            error={passwordErrors.newPassword?.message}
            aria-invalid={passwordErrors.newPassword ? "true" : "false"}
          />
          <Input
            label="Confirm New Password"
            type="password"
            {...registerPassword('confirmNewPassword')}
            error={passwordErrors.confirmNewPassword?.message}
            aria-invalid={passwordErrors.confirmNewPassword ? "true" : "false"}
          />
          <Button type="submit" disabled={!isPasswordDirty || isLoading}>
            {isLoading ? <LoadingSpinner size="sm" /> : 'Change Password'}
          </Button>
        </form>
      </Card>
    </div>
  );
};

// --- Main AuthAndProfilePage Component ---
const AuthAndProfilePage: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect authenticated users from auth forms to profile
    if (isAuthenticated && (location.pathname === '/auth/login' || location.pathname === '/auth/register')) {
      navigate('/profile', { replace: true });
    }
    // Redirect unauthenticated users from profile to login
    if (!isAuthenticated && location.pathname.startsWith('/profile')) {
      navigate('/auth/login', { replace: true });
    }
  }, [isAuthenticated, location.pathname, navigate]);

  return (
    <div className="py-8">
      <Routes>
        <Route path="login" element={<LoginForm />} />
        <Route path="register" element={<RegisterForm />} />
        <Route path="/" element={isAuthenticated ? <ProfileSettings /> : <LoginForm />} /> {/* Default for /auth or /profile */}
      </Routes>
    </div>
  );
};

export default AuthAndProfilePage;