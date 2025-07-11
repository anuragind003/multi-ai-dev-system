import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-200 dark:bg-gray-700 py-4 px-6 text-center text-gray-700 dark:text-gray-300">
      &copy; {new Date().getFullYear()} Task Management App
    </footer>
  );
};

export default Footer;