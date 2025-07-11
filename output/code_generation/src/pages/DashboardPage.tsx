import React from 'react';
import Card from '@/components/ui/Card'; // Assuming Card is available
import { useAuth } from '@/context/AuthContext';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="p-6">
      <h2 className="text-3xl font-bold text-text mb-6">Dashboard Overview</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card title="Welcome Back!" className="bg-white shadow-md p-6 rounded-lg">
          <p className="text-text-light">Hello, {user?.firstName || user?.username || 'User'}!</p>
          <p className="text-text-light mt-2">Your role: <span className="font-semibold text-primary">{user?.role}</span></p>
        </Card>

        <Card title="Quick Stats" className="bg-white shadow-md p-6 rounded-lg">
          <ul className="list-disc list-inside text-text-light">
            <li>Projects Active: <span className="font-semibold text-primary">12</span></li>
            <li>Tasks Pending: <span className="font-semibold text-primary">34</span></li>
            <li>New Messages: <span className="font-semibold text-primary">5</span></li>
          </ul>
        </Card>

        <Card title="Recent Activity" className="bg-white shadow-md p-6 rounded-lg">
          <ul className="text-text-light">
            <li className="mb-2">User <span className="font-semibold">John Doe</span> updated project <span className="font-semibold">Alpha</span>.</li>
            <li className="mb-2">New task <span className="font-semibold">"Review Q1 Report"</span> assigned to you.</li>
            <li>System maintenance scheduled for <span className="font-semibold">tomorrow 2 AM</span>.</li>
          </ul>
        </Card>
      </div>

      <div className="mt-8">
        <h3 className="text-2xl font-bold text-text mb-4">Your Tasks</h3>
        <div className="bg-white shadow-md p-6 rounded-lg">
          <p className="text-text-light">No urgent tasks for today. Keep up the great work!</p>
          {/* Placeholder for a task list or chart */}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;