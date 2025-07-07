import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchUsers } from '../services/api';
import { User } from '../types/User';

const HomePage: React.FC = () => {
  const { data: users, isLoading, isError, error } = useQuery<User[]>(
    ['users'],
    fetchUsers
  );

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (isError) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <div>
      <h1>Home Page</h1>
      <ul>
        {users?.map((user) => (
          <li key={user.id}>{user.name}</li>
        ))}
      </ul>
    </div>
  );
};

export default HomePage;