// src/components/ui/Pagination.tsx
import React from 'react';
import { Button } from './CommonUI';
import { PaginationProps } from '../../types';

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50],
}) => {
  const pageNumbers = [];
  const maxPagesToShow = 5; // Number of page buttons to display directly

  // Determine the range of pages to show
  let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
  let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

  // Adjust startPage if endPage is at totalPages but we don't have enough pages
  if (endPage - startPage + 1 < maxPagesToShow) {
    startPage = Math.max(1, endPage - maxPagesToShow + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    pageNumbers.push(i);
  }

  return (
    <nav className="flex flex-col sm:flex-row justify-between items-center py-4 px-4 bg-white border-t border-border rounded-b-lg" aria-label="Pagination">
      <div className="flex items-center space-x-2 mb-4 sm:mb-0">
        <label htmlFor="pageSizeSelect" className="text-sm text-text-light mr-2">
          Items per page:
        </label>
        <select
          id="pageSizeSelect"
          className="block w-auto px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          aria-label="Select items per page"
        >
          {pageSizeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center space-x-2">
        <Button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          variant="outline"
          size="sm"
          aria-label="Previous page"
        >
          Previous
        </Button>

        <div className="hidden sm:flex space-x-1">
          {startPage > 1 && (
            <>
              <Button variant="ghost" size="sm" onClick={() => onPageChange(1)} aria-label="Go to page 1">1</Button>
              {startPage > 2 && <span className="text-text-light px-1">...</span>}
            </>
          )}

          {pageNumbers.map((page) => (
            <Button
              key={page}
              onClick={() => onPageChange(page)}
              variant={page === currentPage ? 'primary' : 'ghost'}
              size="sm"
              aria-current={page === currentPage ? 'page' : undefined}
              aria-label={`Go to page ${page}`}
            >
              {page}
            </Button>
          ))}

          {endPage < totalPages && (
            <>
              {endPage < totalPages - 1 && <span className="text-text-light px-1">...</span>}
              <Button variant="ghost" size="sm" onClick={() => onPageChange(totalPages)} aria-label={`Go to page ${totalPages}`}>{totalPages}</Button>
            </>
          )}
        </div>

        <span className="sm:hidden text-sm text-text-light">
          Page {currentPage} of {totalPages}
        </span>

        <Button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          variant="outline"
          size="sm"
          aria-label="Next page"
        >
          Next
        </Button>
      </div>
    </nav>
  );
};