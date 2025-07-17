import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Card from '@/components/ui/Card';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { updateUserProfile } from '@/services/api'; // Assuming an API service for profile updates
import { User } from '@/context/AuthContext'; // Re-using User type

const ProfilePage: React.FC = () => {
  const { user, isLoading: authLoading, error: authError, clearError } = useAuth();
  const [firstName, setFirstName] = useState<string>(user?.firstName || '');
  const [lastName, setLastName] = useState<string>(user?.lastName || '');
  const [email, setEmail] = useState<string>(user?.email || '');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [formErrors, setFormErrors] = useState<{ firstName?: string; lastName?: string; email?: string }>({});
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setFirstName(user.firstName || '');
      setLastName(user.lastName || '');
      setEmail(user.email || '');
    }
  }, [user]);

  useEffect(() => {
    clearError(); // Clear global auth errors when component mounts
    setSaveError(null); // Clear local save errors
    setSaveSuccess(false); // Clear success message
  }, [isEditing, clearError]);

  const validateForm = () => {
    const errors: { firstName?: string; lastName?: string; email?: string } = {};
    if (!firstName.trim()) {
      errors.firstName = 'First name is required.';
    }
    if (!lastName.trim()) {
      errors.lastName = 'Last name is required.';
    }
    if (!email.trim()) {
      errors.email = 'Email is required.';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      errors.email = 'Email address is invalid.';
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveError(null);
    setSaveSuccess(false);

    if (!validateForm()) {
      return;
    }

    setIsSaving(true);
    try {
      // Simulate API call
      const updatedUser: User = {
        ...user!, // Assuming user is not null here due to ProtectedRoute
        firstName,
        lastName,
        email,
      };
      await updateUserProfile(updatedUser); // Call your actual API service
      // In a real app, you'd update the user in AuthContext here
      // For this example, we'll just show success
      setSaveSuccess(true);
      setIsEditing(false);
    } catch (err: any) {
      console.error('Profile update failed:', err);
      setSaveError(err.message || 'Failed to update profile. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  if (authLoading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <p className="text-center text-error">User data not available.</p>;
  }

  return (
    <div className="p-6">
      <h2 className="text-3xl font-bold text-text mb-6">User Profile & Settings</h2>

      <Card title="Personal Information" className="bg-white shadow-md p-6 rounded-lg mb-8">
        <form onSubmit={handleSave}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <Input
                id="firstName"
                label="First Name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                disabled={!isEditing}
                error={formErrors.firstName}
                aria-invalid={!!formErrors.firstName}
                aria-describedby={formErrors.firstName ? 'firstName-error' : undefined}
              />
              {formErrors.firstName && (
                <p id="firstName-error" className="text-error text-sm mt-1">{formErrors.firstName}</p>
              )}
            </div>
            <div>
              <Input
                id="lastName"
                label="Last Name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                disabled={!isEditing}
                error={formErrors.lastName}
                aria-invalid={!!formErrors.lastName}
                aria-describedby={formErrors.lastName ? 'lastName-error' : undefined}
              />
              {formErrors.lastName && (
                <p id="lastName-error" className="text-error text-sm mt-1">{formErrors.lastName}</p>
              )}
            </div>
            <div className="md:col-span-2">
              <Input
                id="email"
                type="email"
                label="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={!isEditing}
                error={formErrors.email}
                aria-invalid={!!formErrors.email}
                aria-describedby={formErrors.email ? 'email-error' : undefined}
              />
              {formErrors.email && (
                <p id="email-error" className="text-error text-sm mt-1">{formErrors.email}</p>
              )}
            </div>
          </div>

          {saveSuccess && (
            <div className="bg-success/10 border border-success text-success px-4 py-3 rounded relative mb-4" role="alert">
              <strong className="font-bold">Success!</strong>
              <span className="block sm:inline ml-2">Profile updated successfully.</span>
            </div>
          )}
          {saveError && (
            <div className="bg-error/10 border border-error text-error px-4 py-3 rounded relative mb-4" role="alert">
              <strong className="font-bold">Error!</strong>
              <span className="block sm:inline ml-2">{saveError}</span>
            </div>
          )}
          {authError && (
            <div className="bg-error/10 border border-error text-error px-4 py-3 rounded relative mb-4" role="alert">
              <strong className="font-bold">Authentication Error!</strong>
              <span className="block sm:inline ml-2">{authError}</span>
            </div>
          )}

          <div className="flex justify-end space-x-4">
            {!isEditing ? (
              <Button onClick={() => setIsEditing(true)} variant="primary" aria-label="Edit profile">
                Edit Profile
              </Button>
            ) : (
              <>
                <Button type="button" onClick={() => { setIsEditing(false); setFormErrors({}); setSaveError(null); setSaveSuccess(false); }} variant="secondary" aria-label="Cancel editing">
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={isSaving} aria-label="Save profile changes">
                  {isSaving ? <LoadingSpinner size="sm" /> : 'Save Changes'}
                </Button>
              </>
            )}
          </div>
        </form>
      </Card>

      <Card title="Account Settings" className="bg-white shadow-md p-6 rounded-lg">
        <h3 className="text-xl font-semibold text-text mb-4">Password Management</h3>
        <p className="text-text-light mb-4">
          For security reasons, password changes are handled separately. Please contact support or use the dedicated password reset flow if available.
        </p>
        <Button variant="secondary" disabled aria-label="Change password (disabled)">
          Change Password (Disabled for Demo)
        </Button>

        <h3 className="text-xl font-semibold text-text mt-8 mb-4">Notifications</h3>
        <div className="flex items-center mb-4">
          <input type="checkbox" id="emailNotifications" className="h-4 w-4 text-primary rounded focus:ring-primary" defaultChecked disabled />
          <label htmlFor="emailNotifications" className="ml-2 text-text-light">Receive email notifications</label>
        </div>
        <div className="flex items-center">
          <input type="checkbox" id="smsNotifications" className="h-4 w-4 text-primary rounded focus:ring-primary" disabled />
          <label htmlFor="smsNotifications" className="ml-2 text-text-light">Receive SMS notifications</label>
        </div>
        <Button variant="secondary" className="mt-4" disabled aria-label="Save notification settings (disabled)">
          Save Notification Settings (Disabled for Demo)
        </Button>
      </Card>
    </div>
  );
};

export default ProfilePage;