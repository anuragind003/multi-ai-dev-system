import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { Card } from '../components/Card';

export const Profile = () => {
  const { user } = useAuth();

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-4">Profile</h1>
      <Card>
        <p><strong>Email:</strong> {user?.email}</p>
        {/* Add more profile details here */}
      </Card>
    </div>
  );
};