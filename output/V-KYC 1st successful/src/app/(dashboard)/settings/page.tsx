'use client';

import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, Button, Input } from '@/components/ui';
import { useState } from 'react';

export default function SettingsPage() {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [theme, setTheme] = useState('light');
  const [apiKey, setApiKey] = useState('sk-xxxxxxxxxxxxxxxxxxxx'); // Placeholder
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSaveSettings = async () => {
    setSaveLoading(true);
    setSaveSuccess(false);
    setSaveError(null);
    try {
      // Simulate API call to save settings
      await new Promise(resolve => setTimeout(resolve, 1500));
      console.log('Saving settings:', { notificationsEnabled, theme, apiKey });
      setSaveSuccess(true);
    } catch (error) {
      setSaveError('Failed to save settings. Please try again.');
      console.error('Settings save error:', error);
    } finally {
      setSaveLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <h1 className="text-3xl font-bold text-text mb-6">Settings</h1>

      <Card title="General Settings" className="max-w-2xl mx-auto mb-8">
        <div className="flex items-center justify-between mb-4">
          <label htmlFor="notifications" className="text-text-light font-medium">
            Enable Notifications
          </label>
          <input
            type="checkbox"
            id="notifications"
            checked={notificationsEnabled}
            onChange={(e) => setNotificationsEnabled(e.target.checked)}
            className="h-5 w-5 text-primary rounded border-gray-300 focus:ring-primary"
            role="switch"
            aria-checked={notificationsEnabled}
          />
        </div>

        <div className="mb-6">
          <label htmlFor="theme-select" className="block text-sm font-medium text-text-light mb-1">
            Theme
          </label>
          <select
            id="theme-select"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            className="block w-full px-4 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-colors duration-200"
            aria-label="Select application theme"
          >
            <option value="light">Light</option>
            <option value="dark">Dark (Coming Soon)</option>
          </select>
        </div>

        <Button onClick={handleSaveSettings} disabled={saveLoading}>
          {saveLoading ? 'Saving...' : 'Save General Settings'}
        </Button>
        {saveSuccess && (
          <p className="mt-4 text-sm text-success text-center" role="status">
            Settings updated successfully!
          </p>
        )}
        {saveError && (
          <p className="mt-4 text-sm text-error text-center" role="alert">
            {saveError}
          </p>
        )}
      </Card>

      <Card title="API Key Management" className="max-w-2xl mx-auto">
        <Input
          label="Your API Key"
          type="text"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          readOnly
          className="mb-4"
          aria-label="API Key"
        />
        <p className="text-text-light text-sm mb-4">
          This key is used for programmatic access to your data. Keep it secure.
        </p>
        <Button variant="outline" className="mr-2">
          Generate New Key
        </Button>
        <Button variant="danger">
          Revoke Key
        </Button>
      </Card>
    </DashboardLayout>
  );
}