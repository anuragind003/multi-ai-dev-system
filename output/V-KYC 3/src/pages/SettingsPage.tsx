import React, { useState } from 'react';
import { Card, Button, Input } from '../components/ui/CommonUI';
import { useFormValidation } from '../hooks/useFormValidation';

interface SettingsFormData {
  notifications: boolean;
  theme: 'light' | 'dark';
  language: string;
  timezone: string;
}

const SettingsPage: React.FC = () => {
  const [apiMessage, setApiMessage] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const {
    formData,
    errors,
    handleChange,
    handleSubmit,
    resetForm,
  } = useFormValidation<SettingsFormData>(
    {
      notifications: true,
      theme: 'light',
      language: 'en',
      timezone: 'UTC',
    },
    (values) => {
      const newErrors: { [key: string]: string } = {};
      if (!values.language) newErrors.language = 'Language is required.';
      if (!values.timezone) newErrors.timezone = 'Timezone is required.';
      return newErrors;
    },
    async (values) => {
      setIsSaving(true);
      setApiMessage(null);
      try {
        // Simulate API call to save settings
        console.log('Saving settings:', values);
        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network delay
        setApiMessage({ type: 'success', message: 'Settings saved successfully!' });
      } catch (error: any) {
        setApiMessage({ type: 'error', message: error.message || 'Failed to save settings.' });
      } finally {
        setIsSaving(false);
      }
    }
  );

  const handleToggleNotifications = () => {
    handleChange({ target: { name: 'notifications', value: !formData.notifications } as any });
  };

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-text">Settings</h1>

      {apiMessage && (
        <div className={`p-3 rounded-md mb-4 ${apiMessage.type === 'success' ? 'bg-green-100 text-success' : 'bg-red-100 text-error'}`} role="alert">
          {apiMessage.message}
        </div>
      )}

      <Card title="General Settings">
        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <label htmlFor="language" className="block text-sm font-medium text-text-light mb-1">Language</label>
            <select
              id="language"
              name="language"
              value={formData.language}
              onChange={handleChange}
              className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm border-border"
              aria-required="true"
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
            </select>
            {errors.language && <p className="mt-1 text-sm text-error" role="alert">{errors.language}</p>}
          </div>

          <div className="mb-4">
            <label htmlFor="timezone" className="block text-sm font-medium text-text-light mb-1">Timezone</label>
            <select
              id="timezone"
              name="timezone"
              value={formData.timezone}
              onChange={handleChange}
              className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm border-border"
              aria-required="true"
            >
              <option value="UTC">UTC</option>
              <option value="EST">EST</option>
              <option value="PST">PST</option>
            </select>
            {errors.timezone && <p className="mt-1 text-sm text-error" role="alert">{errors.timezone}</p>}
          </div>

          <div className="mt-6 flex justify-end">
            <Button type="submit" variant="primary" isLoading={isSaving} disabled={isSaving} aria-label="Save general settings">
              Save General Settings
            </Button>
          </div>
        </form>
      </Card>

      <Card title="Notification Preferences">
        <div className="flex items-center justify-between mb-4">
          <span className="text-text-light">Email Notifications</span>
          <label htmlFor="notifications-toggle" className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              id="notifications-toggle"
              name="notifications"
              checked={formData.notifications}
              onChange={handleToggleNotifications}
              className="sr-only peer"
              role="switch"
              aria-checked={formData.notifications}
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            <span className="ml-3 text-sm font-medium text-text-light">{formData.notifications ? 'On' : 'Off'}</span>
          </label>
        </div>
        <p className="text-sm text-text-light">Receive important updates and alerts via email.</p>
      </Card>

      <Card title="Account Management">
        <p className="text-text-light mb-4">Options to manage your account, including data export or deletion.</p>
        <Button variant="danger" aria-label="Delete account">Delete Account</Button>
      </Card>
    </div>
  );
};

export default SettingsPage;