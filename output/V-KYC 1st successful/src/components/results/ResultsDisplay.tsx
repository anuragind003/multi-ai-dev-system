import React from 'react';
import { ResultItem } from '../../services/api';
import { Button, Card, LoadingSpinner } from '../ui';
import { useResults } from '../../context/ResultsContext';
import { DownloadIcon } from '@heroicons/react/outline'; // Example icon

// Mock DownloadIcon
const DownloadIconComponent = (props: React.SVGProps<SVGSVGElement>) => <svg {...props} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>;


interface ResultsDisplayProps {
  results: ResultItem[];
}

/**
 * ResultsTable component.
 * Displays a list of ResultItem in a responsive table.
 */
const ResultsTable: React.FC<{ results: ResultItem[] }> = ({ results }) => {
  if (results.length === 0) {
    return <p className="text-center text-gray-600">No results to display.</p>;
  }

  return (
    <div className="overflow-x-auto shadow-md rounded-lg">
      <table className="min-w-full divide-y divide-gray-200">
        <caption className="sr-only">List of bulk results records</caption>
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              ID
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Size (KB)
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {results.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {item.id}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {item.name}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                  item.status === 'completed' ? 'bg-green-100 text-green-800' :
                  item.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {item.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {item.date}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {item.sizeKB.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/**
 * DownloadAllButton component.
 * Triggers the bulk download functionality from ResultsContext.
 */
const DownloadAllButton: React.FC = () => {
  const { downloading, downloadAllResults, results } = useResults();

  const handleDownload = () => {
    if (results.length === 0) {
      alert('No results to download.');
      return;
    }
    downloadAllResults();
  };

  return (
    <Button
      onClick={handleDownload}
      variant="primary"
      size="large"
      className="w-full sm:w-auto flex items-center justify-center"
      disabled={downloading || results.length === 0}
      aria-label={downloading ? "Downloading results" : "Download all results"}
    >
      {downloading ? (
        <>
          <LoadingSpinner size="small" className="mr-2" /> Downloading...
        </>
      ) : (
        <>
          <DownloadIconComponent className="h-5 w-5 mr-2" /> Download All ({results.length} records)
        </>
      )}
    </Button>
  );
};

/**
 * ResultsDisplay component.
 * Combines the ResultsTable and DownloadAllButton, providing a unified view.
 */
const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ results }) => {
  return (
    <Card className="p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 space-y-4 sm:space-y-0">
        <h2 className="text-2xl font-semibold text-gray-800">Available Results</h2>
        <DownloadAllButton />
      </div>
      <ResultsTable results={results} />
    </Card>
  );
};

export default ResultsDisplay;