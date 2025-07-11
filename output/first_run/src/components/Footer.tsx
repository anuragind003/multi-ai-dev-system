import React from 'react';

function Footer() {
  return (
    <footer className="bg-gray-200 py-4 mt-8">
      <div className="container mx-auto text-center">
        &copy; {new Date().getFullYear()} UAT App
      </div>
    </footer>
  );
}

export default Footer;