import React from 'react';
import { Recording } from '../../types';
import Button from '../ui/Button';

interface RecordingsTableProps {
  recordings: Recording[];
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const RecordingsTable: React.FC<RecordingsTableProps> = React.memo(
  ({ recordings, currentPage, totalPages, onPageChange }) => {
    const formatDuration = (seconds: number) => {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
    };

    const getPageNumbers = () => {
      const pages: (number | string)[] = [];
      const maxPagesToShow = 5; // e.g., 1 ... 4 5 6 ... 10

      if (totalPages <= maxPagesToShow) {
        for (let i = 1; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        pages.push(1);
        if (currentPage > 2) pages.push('...');
        if (currentPage > 1) pages.push(currentPage - 1);
        pages.push(currentPage);
        if (currentPage < totalPages) pages.push(currentPage + 1);
        if (currentPage < totalPages - 1) pages.push('...');
        pages.push(totalPages);

        // Filter out duplicates and sort
        const uniquePages = Array.from(new Set(pages)).sort((a, b) => {
          if (typeof a === 'string') return 1; // '...' comes after numbers
          if (typeof b === 'string') return -1;
          return (a as number) - (b as number);
        });

        return uniquePages;
      }
      return pages;
    };

    return (
      <div className="bg-white shadow-md rounded-lg overflow-hidden mt-6">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Title
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Artist
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Duration
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Genre
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Upload Date
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Status
                </th>
                <th scope="col" className="relative px-6 py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recordings.map((recording) => (
                <tr key={recording.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {recording.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {recording.artist}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDuration(recording.duration)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {recording.genre}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {recording.uploadDate}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        recording.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : recording.status === 'archived'
                          ? 'bg-gray-100 text-gray-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {recording.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <a href={recording.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-900 mr-4" aria-label={`Listen to ${recording.title}`}>
                      Listen
                    </a>
                    <button className="text-indigo-600 hover:text-indigo-900" aria-label={`Edit ${recording.title}`}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <nav
            className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6"
            aria-label="Pagination"
          >
            <div className="flex-1 flex justify-between sm:hidden">
              <Button
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
                variant="secondary"
                size="sm"
                aria-label="Previous page"
              >
                Previous
              </Button>
              <Button
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                variant="secondary"
                size="sm"
                aria-label="Next page"
              >
                Next
              </Button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Page <span className="font-medium">{currentPage}</span> of{' '}
                  <span className="font-medium">{totalPages}</span>
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <Button
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    variant="ghost"
                    className="rounded-l-md"
                    aria-label="Go to previous page"
                  >
                    <span className="sr-only">Previous</span>
                    <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </Button>
                  {getPageNumbers().map((page, index) =>
                    typeof page === 'number' ? (
                      <Button
                        key={index}
                        onClick={() => onPageChange(page)}
                        variant={currentPage === page ? 'primary' : 'ghost'}
                        className={currentPage === page ? 'z-10' : ''}
                        aria-current={currentPage === page ? 'page' : undefined}
                        aria-label={`Go to page ${page}`}
                      >
                        {page}
                      </Button>
                    ) : (
                      <span
                        key={index}
                        className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700"
                      >
                        {page}
                      </span>
                    )
                  )}
                  <Button
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    variant="ghost"
                    className="rounded-r-md"
                    aria-label="Go to next page"
                  >
                    <span className="sr-only">Next</span>
                    <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                  </Button>
                </nav>
              </div>
            </div>
          </nav>
        )}
      </div>
    );
  }
);

export default RecordingsTable;