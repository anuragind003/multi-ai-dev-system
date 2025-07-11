import React from 'react';
import { Link } from 'react-router-dom';

function TestCasesPage() {
  // Dummy test cases data
  const testCases = [
    { id: 'TC-001', name: 'Login Functionality', status: 'Pass' },
    { id: 'TC-002', name: 'Create Account', status: 'Fail' },
    { id: 'TC-003', name: 'Search Feature', status: 'In Progress' },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Test Cases</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {testCases.map((testCase) => (
          <div
            key={testCase.id}
            className="bg-white rounded-lg shadow-md p-4"
          >
            <h3 className="text-lg font-semibold mb-2">{testCase.name}</h3>
            <p>ID: {testCase.id}</p>
            <p>Status: {testCase.status}</p>
            <Link
              to={`/test-run/${testCase.id}`}
              className="mt-2 inline-block bg-green-500 hover:bg-green-700 text-white font-bold py-1 px-2 rounded"
            >
              Run Test
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}

export default TestCasesPage;