// src/pages/login.tsx
import Head from 'next/head';
import LoginForm from '@/components/forms/LoginForm';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard'); // Redirect to dashboard if already authenticated
    }
  }, [isAuthenticated, isLoading, router]);

  // If loading or already authenticated, don't render the login form immediately
  if (isLoading || isAuthenticated) {
    return null; // Or a simple loading spinner if preferred
  }

  return (
    <>
      <Head>
        <title>Login | EnterpriseApp</title>
        <meta name="description" content="Login to your enterprise application" />
      </Head>
      <div className="flex items-center justify-center min-h-screen bg-background p-4">
        <LoginForm />
      </div>
    </>
  );
};

export default LoginPage;