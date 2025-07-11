import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@hooks/useAuth';
import { userService, ApiResponse } from '@api/index';
import Button from '@components/ui/Button';

interface DashboardData {
  stats: string;
  recentActivities: string[];
}

const DashboardPage: React.FC = () => {
  const { user, token, logout } = useAuth();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    if (!token) {
      setError("Authentication token not found.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response: ApiResponse<DashboardData> = await userService.getDashboardData(token);
      if (response.success && response.data) {
        setDashboardData(response.data);
      } else {
        setError(response.message || "Failed to fetch dashboard data.");
        if (response.statusCode === 401) { // Example: if token expired
          logout();
        }
      }
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
      setError("Network error or server unreachable.");
    } finally {
      setIsLoading(false);
    }
  }, [token, logout]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold text-text mb-6">Dashboard</h1>
      <p className="text-lg text-text-light mb-8">Welcome, <span className="font-semibold text-primary">{user?.username || 'Guest'}</span>!</p>

      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-primary"></div>
          <p className="ml-4 text-lg text-text-light">Loading dashboard data...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
          <Button onClick={fetchDashboardData} variant="outline" size="sm" className="ml-4 text-red-700 border-red-700 hover:bg-red-700 hover:text-white">
            Retry
          </Button>
        </div>
      )}

      {dashboardData && !isLoading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Stats Card */}
          <div className="bg-white p-6 rounded-lg shadow-card">
            <h2 className="text-2xl font-semibold text-text mb-4">Overview</h2>
            <p className="text-text-light">{dashboardData.stats}</p>
          </div>

          {/* Recent Activities Card */}
          <div className="bg-white p-6 rounded-lg shadow-card col-span-1 md:col-span-2">
            <h2 className="text-2xl font-semibold text-text mb-4">Recent Activities</h2>
            <ul className="list-disc list-inside space-y-2 text-text-light">
              {dashboardData.recentActivities.map((activity, index) => (
                <li key={index}>{activity}</li>
              ))}
            </ul>
          </div>

          {/* Example Action Card */}
          <div className="bg-white p-6 rounded-lg shadow-card flex flex-col justify-between">
            <h2 className="text-2xl font-semibold text-text mb-4">Quick Actions</h2>
            <p className="text-text-light mb-4">Perform common tasks quickly.</p>
            <div className="space-y-3">
              <Button variant="primary" className="w-full">Generate Report</Button>
              <Button variant="outline" className="w-full">Manage Users</Button>
            </div>
          </div>
        </div>
      )}

      <div className="mt-10 text-center">
        <p className="text-text-light">This is your personalized dashboard. More features coming soon!</p>
      </div>
    </div>
  );
};

export default DashboardPage;