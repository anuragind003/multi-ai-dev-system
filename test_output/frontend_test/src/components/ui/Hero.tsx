import React from 'react';

export const Hero: React.FC = () => {
  return (
    <div className="bg-gradient-to-r from-blue-200 to-blue-500 py-12 text-center">
      <div className="container mx-auto">
        <h1 className="text-4xl font-bold text-white">Welcome to Our E-commerce Platform</h1>
        <p className="text-lg text-white mt-4">Discover amazing products at unbeatable prices.</p>
      </div>
    </div>
  );
};