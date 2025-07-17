import React from 'react';
import { UploadResultItem } from '../../types';
import { formatDate } from '../../utils/helpers';
import { Card, ErrorMessage, LoadingSpinner } from '../ui';

interface UploadResultsTableProps {
  results: UploadResultItem[];
  isLoading: boolean;
  error: string | null;
}

const UploadResultsTable: React.FC<UploadResultsTableProps> = ({ results, isLoading, error }) => {
  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message={`Failed to load upload results: ${error}`} className="mt-4" />;
  }

  if (!results || results.length === 0) {
    return (
      <Card className="mt-8 text-center py-10">
        <p className="text-gray-600 text-lg">No upload results to display yet.</p>
        <p className="text-gray-500 text-sm mt-2">Upload a file to see results here.</p>
      </Card>
    );
  }

  return (
    <Card className="mt-8 overflow-x-auto">
      <h2 className="text-2xl font-semibold text-gray-800 mb-6">Recent Upload Results</h2>
      <div className="min-w-full inline-block align-middle">
        <div className="overflow-hidden border border-gray-200 rounded-lg shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  File Name
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Status
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Processed At
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Records (S/F/T)
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {results.map((result) => (
                <tr key={result.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {result.originalFileName}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        result.status === 'SUCCESS'
                          ? 'bg-success/10 text-success'
                          : result.status === 'FAILED'
                          ? 'bg-danger/10 text-danger'
                          : 'bg-warning/10 text-warning'
                      }`}
                    >
                      {result.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(result.processedAt)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {result.successfulRecords}/{result.failedRecords}/{result.totalRecords}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {result.errorMessage && (
                      <p className="text-danger text-xs italic">{result.errorMessage}</p>
                    )}
                    {result.details && result.details.length > 0 && (
                      <ul className="list-disc list-inside text-xs text-gray-600 mt-1">
                        {result.details.slice(0, 2).map((detail, index) => ( // Show first 2 details
                          <li key={index}>Row {detail.rowNumber}: {detail.error}</li>
                        ))}
                        {result.details.length > 2 && (
                          <li>...and {result.details.length - 2} more errors.</li>
                        )}
                      </ul>
                    )}
                    {!result.errorMessage && (!result.details || result.details.length === 0) && (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
};

export default UploadResultsTable;