'use client';

import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, Input, Button } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { useState } from 'react';

export default function ProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [isEditing, setIsEditing] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaveLoading(true);
    setSaveSuccess(false);
    setSaveError(null);
    try {
      // Simulate API call to update profile
      await new Promise(resolve => setTimeout(resolve, 1500));
      // In a real app, you'd send name, email to backend and update context
      console.log('Saving profile:', { name, email });
      setSaveSuccess(true);
      setIsEditing(false);
    } catch (error) {
      setSaveError('Failed to save profile. Please try again.');
      console.error('Profile save error:', error);
    } finally {
      setSaveLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <DashboardLayout>
      <h1 className="text-3xl font-bold text-text mb-6">Your Profile</h1>
      <Card title="Personal Information" className="max-w-2xl mx-auto">
        <Input
          label="Full Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={!isEditing}
          aria-label="Full Name"
        />
        <Input
          label="Email Address"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={!isEditing}
          aria-label="Email Address"
        />
        <Input
          label="Role"
          value={user?.role || 'N/A'}
          disabled
          className="mb-6"
          aria-label="User Role"
        />

        <div className="flex justify-end gap-4">
          {isEditing ? (
            <>
              <Button variant="outline" onClick={() => { setIsEditing(false); setName(user?.name || ''); setEmail(user?.email || ''); setSaveError(null); setSaveSuccess(false); }} disabled={saveLoading}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saveLoading}>
                {saveLoading ? 'Saving...' : 'Save Changes'}
              </Button>
            </>
          ) : (
            <Button onClick={() => setIsEditing(true)} variant="secondary">
              Edit Profile
            </Button>
          )}
        </div>
        {saveSuccess && (
          <p className="mt-4 text-sm text-success text-center" role="status">
            Profile updated successfully!
          </p>
        )}
        {saveError && (
          <p className="mt-4 text-sm text-error text-center" role="alert">
            {saveError}
          </p>
        )}
      </Card>

      <Card title="Password Settings" className="max-w-2xl mx-auto mt-8">
        <p className="text-text-light mb-4">
          For security reasons, password changes are handled separately.
        </p>
        <Button variant="outline" className="w-full sm:w-auto">
          Change Password
        </Button>
      </Card>
    </DashboardLayout>
  );
}