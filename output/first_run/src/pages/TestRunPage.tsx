import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useUATContext } from '../context/UATContext';

function TestRunPage() {
  const { testRunId } = useParams<{ testRunId: string }>();
  const { addTestRun, testRuns } = useUATContext();
  const [testRunDetails, setTestRunDetails] = useState<any | null>(null); // Replace 'any' with a specific type

  useEffect(() => {
    // Simulate fetching test run details based on testRunId
    const fetchTestRunDetails = async () => {
      // Replace with actual API call or data fetching
      await new Promise((resolve) => setTimeout(resolve, 500)); // Simulate network delay

      const dummyDetails = {
        id: testRunId,
        name: `Test Run for ${testRunId}`,
        status: 'Running',
        steps: [
          { id: 1, description: 'Step 1: Navigate to login page', status: 'Pass' },
          { id: 2, description: 'Step 2: Enter username', status: 'Pass' },
          { id: 3, description: 'Step 3: Enter password', status: 'Pass' },
          { id: 4, description: 'Step 4: Click login', status: 'Fail' },
        ],
      };
      setTestRunDetails(dummyDetails);
      addTestRun(dummyDetails); // Add the test run to context
    };

    if (testRunId) {
      fetchTestRunDetails();
    }
  }, [testRunId, addTestRun]);

  if (!testRunDetails) {
    return <p>Loading test run details...</p>;
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">{testRunDetails.name}</h2>
      <p>Status: {testRunDetails.status}</p>
      <h3 className="text-xl font-semibold mt-4 mb-2">Test Steps</h3>
      <ul>
        {testRunDetails.steps.map((step: any) => (
          <li key={step.id} className="mb-2">
            {step.description} - <span className={step.status === 'Pass' ? 'text-green-500' : 'text-red-500'}>{step.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TestRunPage;