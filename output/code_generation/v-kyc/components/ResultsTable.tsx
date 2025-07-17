import React, { useState, useMemo } from 'react';
import { Recording, SortConfig, SortDirection } from '../types';
import Pagination from './Pagination';
import Icon from './Icon';

interface ResultsTableProps {
  results: Recording[];
  onView: (recording: Recording) => void;
  onDownload: (lanId: string) => void;
  onBulkDownload: (lanIds: string[]) => void;
  isBulkDownloading: boolean;
}

const RECORDS_PER_PAGE = 10;

const ResultsTable: React.FC<ResultsTableProps> = ({ results, onView, onDownload, onBulkDownload, isBulkDownloading }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState<SortConfig | null>({ key: 'date', direction: 'descending' });

  const sortedResults = useMemo(() => {
    let sortableItems = [...results];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aValue: string | number = a[sortConfig.key];
        let bValue: string | number = b[sortConfig.key];

        if (sortConfig.key === 'sizeInBytes') {
            aValue = a.sizeInBytes;
            bValue = b.sizeInBytes;
        }

        if (aValue < bValue) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'ascending' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [results, sortConfig]);

  const paginatedResults = useMemo(() => {
    const startIndex = (currentPage - 1) * RECORDS_PER_PAGE;
    const endIndex = startIndex + RECORDS_PER_PAGE;
    return sortedResults.slice(startIndex, endIndex);
  }, [sortedResults, currentPage]);

  const requestSort = (key: keyof Recording) => {
    let direction: SortDirection = 'ascending';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(1); // Reset to first page after sorting
  };
  
  const getSortIcon = (key: keyof Recording) => {
      if (!sortConfig || sortConfig.key !== key) {
          return <Icon name="arrow-sort" className="w-4 h-4 text-brand-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />;
      }
      if (sortConfig.direction === 'ascending') {
          return <Icon name="arrow-up" className="w-4 h-4 text-brand-blue" />;
      }
      return <Icon name="arrow-down" className="w-4 h-4 text-brand-blue" />;
  };

  const handleBulkDownloadClick = () => {
    onBulkDownload(results.map(r => r.lanId));
  }

  if (results.length === 0) {
    return (
        <div className="text-center py-16 px-6 bg-white rounded-lg shadow-lg">
          <Icon name="document" className="mx-auto h-16 w-16 text-brand-gray-300" />
          <h3 className="mt-4 text-xl font-semibold text-brand-gray-700">No Recordings Found</h3>
          <p className="mt-2 text-brand-gray-500">Your search did not match any records. Please try different criteria.</p>
        </div>
    );
  }
  
  const isBulkDownloadable = results.length > 1;

  const headerConfig: { key: keyof Recording, label: string }[] = [
      { key: 'lanId', label: 'LAN ID'},
      { key: 'date', label: 'Date'},
      { key: 'time', label: 'Time'},
      { key: 'callDuration', label: 'Duration'},
      { key: 'status', label: 'Status'},
      { key: 'uploadTime', label: 'Upload Time'},
      { key: 'sizeInBytes', label: 'Size'},
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="p-4 sm:p-6 border-b border-brand-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-semibold leading-6 text-brand-gray-900">
          Search Results <span className="text-brand-gray-500 font-normal">({results.length} found)</span>
        </h3>
        {isBulkDownloadable && (
          <button 
            onClick={handleBulkDownloadClick}
            disabled={isBulkDownloading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-brand-red hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-red transition-all disabled:bg-red-300 disabled:cursor-wait"
          >
            {isBulkDownloading ? (
                <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                </>
            ) : (
                <>
                    <Icon name="download" className="w-5 h-5 mr-2" />
                    Download All ({results.length})
                </>
            )}
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-brand-gray-200">
          <thead className="bg-brand-gray-50">
            <tr>
                {headerConfig.map(({key, label}) => (
                    <th key={key} scope="col" className="px-6 py-3 text-left text-xs font-medium text-brand-gray-500 uppercase tracking-wider">
                         <button onClick={() => requestSort(key)} className="group flex items-center space-x-2 focus:outline-none">
                            <span>{label}</span>
                            {getSortIcon(key)}
                        </button>
                    </th>
                ))}
              <th scope="col" className="relative px-6 py-3">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-brand-gray-200">
            {paginatedResults.map((rec) => (
              <tr key={rec.lanId} className="hover:bg-brand-gray-50 transition-colors group">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-brand-gray-900">{rec.lanId}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-gray-500">{rec.date}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-gray-500">{rec.time}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-gray-500">{rec.callDuration}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {rec.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-gray-500">{rec.uploadTime}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-brand-gray-500">{rec.size}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center justify-end space-x-4">
                     <button 
                        onClick={() => onView(rec)} 
                        className="text-brand-gray-500 hover:text-brand-blue flex items-center gap-1 group"
                        aria-label={`View details for ${rec.lanId}`}
                      >
                        <Icon name="eye" className="w-5 h-5" />
                        View
                      </button>
                      <button 
                        onClick={() => onDownload(rec.lanId)} 
                        className="text-brand-blue hover:text-brand-blue/80 flex items-center gap-1 group"
                        aria-label={`Download recording for ${rec.lanId}`}
                      >
                        <Icon name="download" className="w-5 h-5 transition-transform group-hover:scale-110" />
                        Download
                      </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {results.length > RECORDS_PER_PAGE && (
        <Pagination
          currentPage={currentPage}
          totalCount={results.length}
          pageSize={RECORDS_PER_PAGE}
          onPageChange={page => setCurrentPage(page)}
        />
      )}
    </div>
  );
};

export default ResultsTable;