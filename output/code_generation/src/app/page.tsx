import Link from 'next/link';
import { Button } from '@/components/ui';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-gradient-to-br from-primary to-primary-dark text-white">
      <div className="text-center max-w-2xl">
        <h1 className="text-5xl font-extrabold mb-6 leading-tight">
          Welcome to the Enterprise Dashboard
        </h1>
        <p className="text-xl mb-10 opacity-90">
          Your central hub for managing all critical business operations.
          Secure, efficient, and user-friendly.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/dashboard" passHref>
            <Button variant="secondary" size="large" className="w-full sm:w-auto">
              Go to Dashboard
            </Button>
          </Link>
          <Link href="/login" passHref>
            <Button variant="outline" size="large" className="w-full sm:w-auto border-white text-white hover:bg-white hover:text-primary">
              Login
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}