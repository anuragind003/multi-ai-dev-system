import React, { useState } from 'react';
import { Card, Input, Button } from '../components/ui/CommonUI';
import { useAuth } from '../context/AuthContext';
import { useFormValidation } from '../hooks/useFormValidation';
import { updateUserProfile } from '../services/api'; // Assuming this function exists

interface ProfileFormData {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
}

const ProfilePage: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [apiMessage, setApiMessage] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const initialData: ProfileFormData = {
    username: user?.username || '',
    email: user?.email || '', // Assuming email is part of User type
    firstName: user?.firstName || '', // Assuming firstName is part of User type
    lastName: user?.lastName || '', // Assuming lastName is part of User type
  };

  const {
    formData,
    errors,
    handleChange,
    handleSubmit,
    resetForm,
    setFormData,
  } = useFormValidation<ProfileFormData>(
    initialData,
    (values) => {
      const newErrors: { [key: string]: string } = {};
      if (!values.username) newErrors.username = 'Username is required.';
      if (!values.email) {
        newErrors.email = 'Email is required.';
      } else if (!/\S+@\S+\.\S+/.test(values.email)) {
        newErrors.email = 'Email address is invalid.';
      }
      if (!values.firstName) newErrors.firstName = 'First Name is required.';
      if (!values.lastName) newErrors.lastName = 'Last Name is required.';
      return newErrors;
    },
    async (values) => {
      setIsSaving(true);
      setApiMessage(null);
      try {
        // Simulate API call to update profile
        await updateUserProfile(user?.id || '', values); // Pass user ID and updated data
        setApiMessage({ type: 'success', message: 'Profile updated successfully!' });
        setIsEditing(false); // Exit edit mode on success
        // In a real app, you'd update the user context here
      } catch (error: any) {
        setApiMessage({ type: 'error', message: error.message || 'Failed to update profile.' });
      } finally {
        setIsSaving(false);
      }
    }
  );

  // Update form data if user context changes (e.g., after initial load)
  React.useEffect(() => {
    if (user && !isEditing) { // Only update if not currently editing
      setFormData({
        username: user.username || '',
        email: user.email || '',
        firstName: user.firstName || '',
        lastName: user.lastName || '',
      });
    }
  }, [user, isEditing, setFormData]);

  const handleCancelEdit = () => {
    setIsEditing(false);
    resetForm(); // Reset form to initial user data
    setApiMessage(null);
  };

  if (authLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <p className="text-text-light">Loading profile data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-text">User Profile</h1>

      <Card title="Personal Information">
        {apiMessage && (
          <div className={`p-3 rounded-md mb-4 ${apiMessage.type === 'success' ? 'bg-green-100 text-success' : 'bg-red-100 text-error'}`} role="alert">
            {apiMessage.message}
          </div>
        )}
        <form onSubmit={handleSubmit} noValidate>
          <Input
            label="Username"
            name="username"
            value={formData.username}
            onChange={handleChange}
            error={errors.username}
            disabled={!isEditing}
            aria-readonly={!isEditing}
          />
          <Input
            label="Email"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            error={errors.email}
            disabled={!isEditing}
            aria-readonly={!isEditing}
          />
          <Input
            label="First Name"
            name="firstName"
            value={formData.firstName}
            onChange={handleChange}
            error={errors.firstName}
            disabled={!isEditing}
            aria-readonly={!isEditing}
          />
          <Input
            label="Last Name"
            name="lastName"
            value={formData.lastName}
            onChange={handleChange}
            error={errors.lastName}
            disabled={!isEditing}
            aria-readonly={!isEditing}
          />

          <div className="mt-6 flex justify-end space-x-4">
            {isEditing ? (
              <>
                <Button type="button" variant="secondary" onClick={handleCancelEdit} disabled={isSaving} aria-label="Cancel editing profile">
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSaving} disabled={isSaving} aria-label="Save profile changes">
                  Save Changes
                </Button>
              </>
            ) : (
              <Button type="button" variant="primary" onClick={() => setIsEditing(true)} aria-label="Edit profile">
                Edit Profile
              </Button>
            )}
          </div>
        </form>
      </Card>

      <Card title="Account Security">
        <p className="text-text-light mb-4">Manage your password and security settings.</p>
        <Button variant="outline" aria-label="Change password">Change Password</Button>
      </Card>
    </div>
  );
};

export default ProfilePage;