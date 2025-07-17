// src/pages/index.tsx
import Head from 'next/head';
import { Card, Button } from '@/components/ui/CommonUI';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { FaRocket, FaSignInAlt, FaUserCircle } from 'react-icons/fa';

const Home: React.FC = () => {
  const { isAuthenticated, user } = useAuth();

  return (
    <>
      <Head>
        <title>Home | EnterpriseApp</title>
        <meta name="description" content="Welcome to your enterprise application" />
      </Head>

      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-160px)] py-10 px-4 animate-fadeIn">
        <Card className="w-full max-w-3xl text-center p-8">
          <FaRocket className="text-primary mx-auto mb-6" size={64} />
          <h1 className="text-4xl font-bold text-text mb-4">
            Welcome to EnterpriseApp
          </h1>
          <p className="text-lg text-text-light mb-8">
            Your comprehensive solution for managing business operations efficiently.
            Get started by exploring your dashboard or logging in.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-4">
            {isAuthenticated ? (
              <>
                <Link href="/dashboard" passHref>
                  <Button size="lg" icon={<FaTachometerAlt />}>
                    Go to Dashboard
                  </Button>
                </Link>
                <Link href="/profile" passHref>
                  <Button variant="outline" size="lg" icon={<FaUserCircle />}>
                    View Profile
                  </Button>
                </Link>
              </>
            ) : (
              <Link href="/login" passHref>
                <Button size="lg" icon={<FaSignInAlt />}>
                  Login Now
                </Button>
              </Link>
            )}
          </div>

          {user && (
            <p className="mt-8 text-md text-text-light">
              You are logged in as <span className="font-semibold text-primary">{user.email}</span>.
            </p>
          )}
        </Card>
      </div>
    </>
  );
};

export default Home;