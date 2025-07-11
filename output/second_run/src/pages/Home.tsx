import React from 'react';
import { Link } from 'react-router-dom';

export const Home = () => {
  return (
    <div className="container mx-auto py-12">
      <h1 className="text-3xl font-bold mb-4">Welcome to Task Manager</h1>
      <p className="mb-4">
        Manage your tasks efficiently.  Get started by <Link to="/login" className="text-blue-500 hover:underline">logging in</Link> or <Link to="/register" className="text-blue-500 hover:underline">registering</Link>.
      </p>
    </div>
  );
};