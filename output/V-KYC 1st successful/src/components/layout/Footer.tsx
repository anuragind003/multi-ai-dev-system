import React from 'react';

export const Footer: React.FC = React.memo(() => {
  return (
    <footer className="bg-gray-800 text-white py-6 px-6 text-center text-sm">
      <div className="container mx-auto">
        <p>&copy; {new Date().getFullYear()} EnterpriseApp. All rights reserved.</p>
        <p className="mt-2">
          <a href="/privacy" className="text-gray-400 hover:text-white transition-colors">Privacy Policy</a> |{' '}
          <a href="/terms" className="text-gray-400 hover:text-white transition-colors">Terms of Service</a>
        </p>
      </div>
    </footer>
  );
});