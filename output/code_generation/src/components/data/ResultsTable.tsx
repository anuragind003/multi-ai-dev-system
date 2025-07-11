import React from 'react';
import { TableDataItem } from '../../types';
import LoadingSpinner from '../ui/LoadingSpinner';
import Pagination from '../ui/Pagination';
import Input from '../ui/Input';
import Button from '../ui/Button';
import { useData } from '../../context/DataContext';

interface ResultsTableProps {
  // No direct props needed as data is consumed from DataContext
}

const ResultsTable: React.FC<ResultsTableProps> = () => {
  const {
    data,
    loading,
    error,
    currentPage,
    totalPages,
    totalRecords,
    searchTerm,
    setSearchTerm,
    goToPage,
    refreshData,
  } = useData();

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  if (error) {
    return (
      <div className="text-center p-6 bg-error/10 text-error rounded-lg shadow-soft" role="alert">
        <p className="text-lg font-semibold mb-2">Error loading data:</p>
        <p className="mb-4">{error}</p>
        <Button onClick={refreshData} variant="danger">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-medium">
      <div className="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
        <Input
          type="search"
          placeholder="Search by ID, Name, Category, Status..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="w-full sm:w-2/3 md:w-1/2"
          aria-label="Search table data"
        />
        <Button onClick={refreshData} variant="outline" disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </Button>
      </div>

      <div className="overflow-x-auto relative shadow-soft rounded-lg">
        <table className="w-full text-sm text-left text-text-light">
          <caption className="sr-only">Bulk Results Table</caption>
          <thead className="text-xs text-text uppercase bg-gray-50 border-b border-border">
            <tr>
              <th scope="col" className="py-3 px-6">ID</th>
              <th scope="col" className="py-3 px-6">Name</th>
              <th scope="col" className="py-3 px-6">Category</th>
              <th scope="col" className="py-3 px-6">Status</th>
              <th scope="col" className="py-3 px-6 text-right">Value</th>
              <th scope="col" className="py-3 px-6">Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-10">
                  <LoadingSpinner size="lg" />
                  <p className="mt-4 text-text-light">Loading results...</p>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-10 text-text-light">
                  No results found for "{searchTerm}".
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr key={item.id} className="bg-white border-b hover:bg-gray-50">
                  <th scope="row" className="py-4 px-6 font-medium text-text whitespace-nowrap">
                    {item.id}
                  </th>
                  <td className="py-4 px-6">{item.name}</td>
                  <td className="py-4 px-6">{item.category}</td>
                  <td className="py-4 px-6">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      item.status === 'Active' ? 'bg-success/20 text-success' :
                      item.status === 'Pending' ? 'bg-warning/20 text-warning' :
                      'bg-error/20 text-error'
                    }`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right">${item.value.toFixed(2)}</td>
                  <td className="py-4 px-6">{item.date}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={goToPage}
        isLoading={loading}
      />
      <div className="text-center text-sm text-text-light mt-4">
        Showing {data.length} of {totalRecords} records.
      </div>
    </div>
  );
};

export default React.memo(ResultsTable);