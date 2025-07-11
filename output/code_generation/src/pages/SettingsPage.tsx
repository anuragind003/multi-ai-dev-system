import React from 'react';
import { Card, Button } from '../components/ui';

const SettingsPage: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>
      <Card className="max-w-2xl mx-auto">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">General Settings</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2 border-b border-gray-200 last:border-b-0">
            <div>
              <p className="font-medium text-gray-700">Notification Preferences</p>
              <p className="text-sm text-gray-500">Manage how you receive alerts.</p>
            </div>
            <Button variant="outline" size="sm">Manage</Button>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-200 last:border-b-0">
            <div>
              <p className="font-medium text-gray-700">Data Export</p>
              <p className="text-sm text-gray-500">Export your processed data.</p>
            </div>
            <Button variant="primary" size="sm">Export Data</Button>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-200 last:border-b-0">
            <div>
              <p className="font-medium text-gray-700">API Keys</p>
              <p className="text-sm text-gray-500">Manage your API integration keys.</p>
            </div>
            <Button variant="outline" size="sm">View Keys</Button>
          </div>
        </div>

        <h2 className="text-xl font-semibold text-gray-800 mt-8 mb-4">Account Settings</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2 border-b border-gray-200 last:border-b-0">
            <div>
              <p className="font-medium text-gray-700">Change Password</p>
              <p className="text-sm text-gray-500">Update your account password.</p>
            </div>
            <Button variant="outline" size="sm">Change</Button>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-200 last:border-b-0">
            <div>
              <p className="font-medium text-gray-700">Delete Account</p>
              <p className="text-sm text-gray-500">Permanently delete your account and data.</p>
            </div>
            <Button variant="danger" size="sm">Delete</Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default SettingsPage;