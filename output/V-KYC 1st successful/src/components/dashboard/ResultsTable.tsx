// src/components/dashboard/ResultsTable.tsx
import React from 'react';
import { TableRecord } from '../../types';
import { Feedback } from '../ui/CommonUI';

interface ResultsTableProps {
  data: TableRecord[];
  loading: boolean;
  error: string | null;
}

export const ResultsTable: React.FC<ResultsTableProps> = ({ data, loading, error }) => {
  if (loading) {
    return <Feedback type="loading" message="Loading table data..." />;
  }

  if (error) {
    return <Feedback type="error" message={`Failed to load data: ${error}`} />;
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-text-light">
        <p className="text-lg">No records found.</p>
        <p className="text-sm">Try adjusting your search or filters.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto shadow-custom rounded-lg border border-border">
      <table className="min-w-full divide-y divide-border">
        <thead className="bg-gray-50">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider">
              ID
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider">
              Name
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider">
              Category
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider">
              Value
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider">
              Created At
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-border">
          {data.map((record) => (
            <tr key={record.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-text">
                {record.id}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-text-light">
                {record.name}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                  record.status === 'active' ? 'bg-green-100 text-green-800' :
                  record.status === 'inactive' ? 'bg-red-100 text-red-800' :
                  'bg-yellow-100 text-yellow-800'
                }`}>
                  {record.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-text-light">
                {record.category}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-text-light">
                ${record.value.toLocaleString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-text-light">
                {new Date(record.createdAt).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};