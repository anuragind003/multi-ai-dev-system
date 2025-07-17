
import React, { useMemo } from 'react';
import Icon from './Icon';

interface PaginationProps {
    currentPage: number;
    totalCount: number;
    pageSize: number;
    onPageChange: (page: number) => void;
    siblingCount?: number;
}

const DOTS = '...';

const usePaginationRange = ({
  totalCount,
  pageSize,
  siblingCount = 1,
  currentPage,
}: Omit<PaginationProps, 'onPageChange'>) => {
  const paginationRange = useMemo(() => {
    const totalPageCount = Math.ceil(totalCount / pageSize);

    // Pages count is determined as siblingCount + firstPage + lastPage + currentPage + 2*DOTS
    const totalPageNumbers = siblingCount + 5;

    /*
      Case 1:
      If the number of pages is less than the page numbers we want to show in our
      paginationComponent, we return the range [1..totalPageCount]
    */
    if (totalPageNumbers >= totalPageCount) {
      return Array.from({ length: totalPageCount }, (_, i) => i + 1);
    }

    const leftSiblingIndex = Math.max(currentPage - siblingCount, 1);
    const rightSiblingIndex = Math.min(
      currentPage + siblingCount,
      totalPageCount
    );

    const shouldShowLeftDots = leftSiblingIndex > 2;
    const shouldShowRightDots = rightSiblingIndex < totalPageCount - 2;

    const firstPageIndex = 1;
    const lastPageIndex = totalPageCount;

    if (!shouldShowLeftDots && shouldShowRightDots) {
      let leftItemCount = 3 + 2 * siblingCount;
      let leftRange = Array.from({ length: leftItemCount }, (_, i) => i + 1);
      return [...leftRange, DOTS, totalPageCount];
    }
    
    if (shouldShowLeftDots && !shouldShowRightDots) {
      let rightItemCount = 3 + 2 * siblingCount;
      let rightRange = Array.from({ length: rightItemCount }, (_, i) => totalPageCount - rightItemCount + i + 1);
      return [firstPageIndex, DOTS, ...rightRange];
    }
     
    if (shouldShowLeftDots && shouldShowRightDots) {
      let middleRange = Array.from({ length: rightSiblingIndex - leftSiblingIndex + 1 }, (_, i) => leftSiblingIndex + i);
      return [firstPageIndex, DOTS, ...middleRange, DOTS, lastPageIndex];
    }

    return []; // Should not happen
  }, [totalCount, pageSize, siblingCount, currentPage]);

  return paginationRange;
};


const Pagination: React.FC<PaginationProps> = (props) => {
    const { currentPage, totalCount, pageSize, onPageChange } = props;
    const totalPages = Math.ceil(totalCount / pageSize);

    const paginationRange = usePaginationRange(props);

    if (currentPage === 0 || paginationRange.length < 2) {
        return null;
    }

    const onNext = () => onPageChange(currentPage + 1);
    const onPrevious = () => onPageChange(currentPage - 1);
    
    const startItem = (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalCount);

    return (
        <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-brand-gray-200 sm:px-6 rounded-b-lg">
             <div className="flex-1 flex justify-between sm:hidden">
                <button onClick={onPrevious} disabled={currentPage === 1} className="relative inline-flex items-center px-4 py-2 border border-brand-gray-300 text-sm font-medium rounded-md text-brand-gray-700 bg-white hover:bg-brand-gray-50 disabled:opacity-50">
                    Previous
                </button>
                <button onClick={onNext} disabled={currentPage === totalPages} className="ml-3 relative inline-flex items-center px-4 py-2 border border-brand-gray-300 text-sm font-medium rounded-md text-brand-gray-700 bg-white hover:bg-brand-gray-50 disabled:opacity-50">
                    Next
                </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                     <p className="text-sm text-brand-gray-700">
                        Showing <span className="font-medium">{startItem}</span> to <span className="font-medium">{endItem}</span> of{' '}
                        <span className="font-medium">{totalCount}</span> results
                    </p>
                </div>
                <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                         <button onClick={onPrevious} disabled={currentPage === 1} className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-brand-gray-300 bg-white text-sm font-medium text-brand-gray-500 hover:bg-brand-gray-50 disabled:opacity-50 transition-colors">
                            <span className="sr-only">Previous</span>
                            <Icon name="chevron-left" className="h-5 w-5" />
                        </button>
                        {paginationRange.map((pageNumber, index) => {
                            if (pageNumber === DOTS) {
                                return <span key={`${DOTS}-${index}`} className="relative inline-flex items-center px-4 py-2 border border-brand-gray-300 bg-white text-sm font-medium text-brand-gray-700">...</span>;
                            }

                            return (
                                <button
                                    key={pageNumber}
                                    onClick={() => onPageChange(pageNumber as number)}
                                    className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium transition-colors ${
                                        currentPage === pageNumber 
                                        ? 'z-10 bg-brand-blue/10 border-brand-blue text-brand-blue' 
                                        : 'bg-white border-brand-gray-300 text-brand-gray-500 hover:bg-brand-gray-50'
                                    }`}
                                >
                                    {pageNumber}
                                </button>
                            );
                        })}
                         <button onClick={onNext} disabled={currentPage === totalPages} className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-brand-gray-300 bg-white text-sm font-medium text-brand-gray-500 hover:bg-brand-gray-50 disabled:opacity-50 transition-colors">
                            <span className="sr-only">Next</span>
                            <Icon name="chevron-right" className="h-5 w-5" />
                        </button>
                    </nav>
                </div>
            </div>
        </div>
    );
};

export default Pagination;
