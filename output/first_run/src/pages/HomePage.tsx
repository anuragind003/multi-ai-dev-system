import React from 'react';
import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <div className="text-center">
      <h1 className="text-3xl font-bold mb-4">Welcome to UAT App</h1>
      <p className="mb-4">
        This application helps you manage and execute User Acceptance Testing.
      </p>
      <Link
        to="/test-cases"
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
      >
        View Test Cases
      </Link>
    </div>
  );
}

export default HomePage;