import React from 'react';

export const Footer = () => {
  return (
    <footer className="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 py-4 px-6 text-center mt-auto">
      &copy; {new Date().getFullYear()} Task Manager. All rights reserved.
    </footer>
  );
};