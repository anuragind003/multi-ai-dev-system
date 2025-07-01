import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="bg-blue-500 text-white py-4">
      <div className="container mx-auto flex items-center justify-between">
        <a href="/" className="text-2xl font-bold">E-commerce Platform</a>
        <nav>
          <ul className="flex space-x-6">
            <li><a href="/" className="hover:underline">Home</a></li>
            <li><a href="/products" className="hover:underline">Products</a></li>
          </ul>
        </nav>
      </div>
    </header>
  );
};