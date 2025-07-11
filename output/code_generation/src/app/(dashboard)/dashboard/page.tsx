'use client';

import { useEffect, useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, Button } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { getDashboardData } from '@/lib/api';
import { LoadingSpinner } from '@/components/common/ErrorBoundary'; // Re-using the spinner

interface DashboardMetrics {
  users: number;
  sales: number;
  projects: number;
}

interface RecentActivity {
  id: number;
  description: string;
  timestamp: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      setError(null);
      try {
        // In a real app, you'd get the token from a secure place (e.g., AuthContext, cookies)
        const token = localStorage.getItem('authToken') || '';
        const response = await getDashboardData(token);
        if (response.success && response.data) {
          setMetrics(response.data.metrics);
          setRecentActivity(response.data.recentActivity);
        } else {
          setError(response.message || 'Failed to fetch dashboard data.');
        }
      } catch (err) {
        setError('An unexpected error occurred while fetching data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <DashboardLayout>
      <h1 className="text-3xl font-bold text-text mb-6">Welcome, {user?.name || 'User'}!</h1>

      {loading && <LoadingSpinner className="h-24" />}
      {error && (
        <Card className="bg-red-50 border border-error text-error p-4 mb-6">
          <p className="font-semibold">Error:</p>
          <p>{error}</p>
          <Button onClick={() => window.location.reload()} variant="outline" className="mt-4 border-error text-error hover:bg-error hover:text-white">
            Retry
          </Button>
        </Card>
      )}

      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <Card title="Total Users">
              <p className="text-4xl font-bold text-primary">{metrics?.users || 'N/A'}</p>
              <p className="text-text-light mt-2">Registered users across all platforms.</p>
            </Card>
            <Card title="Total Sales">
              <p className="text-4xl font-bold text-secondary">${metrics?.sales?.toLocaleString() || 'N/A'}</p>
              <p className="text-text-light mt-2">Revenue generated this quarter.</p>
            </Card>
            <Card title="Active Projects">
              <p className="text-4xl font-bold text-accent">{metrics?.projects || 'N/A'}</p>
              <p className="text-text-light mt-2">Currently ongoing projects.</p>
            </Card>
          </div>

          <Card title="Recent Activity">
            {recentActivity && recentActivity.length > 0 ? (
              <ul className="space-y-4">
                {recentActivity.map((activity) => (
                  <li key={activity.id} className="flex items-center justify-between border-b border-border pb-2 last:border-b-0 last:pb-0">
                    <p className="text-text">{activity.description}</p>
                    <span className="text-sm text-text-light">{activity.timestamp}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-text-light">No recent activity to display.</p>
            )}
          </Card>

          <div className="mt-8 text-center">
            <p className="text-text-light">
              This is a protected dashboard page. You can navigate to other sections using the sidebar.
            </p>
          </div>
        </>
      )}
    </DashboardLayout>
  );
}