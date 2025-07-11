import React, { useState, useEffect, useCallback } from 'react';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import StatusDisplay from '../components/ui/StatusDisplay';
import { useRecordings } from '../context/AppContext';
import { Recording } from '../types';
import { debounce } from '../utils';

const RecordingsPage: React.FC = () => {
  const { recordings, fetchRecordings, loading, error } = useRecordings();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterDate, setFilterDate] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1); // Assuming API returns total pages

  // Debounced search term update
  const debouncedSetSearchTerm = useCallback(
    debounce((value: string) => {
      setSearchTerm(value);
      setCurrentPage(1); // Reset page on new search
    }, 500),
    []
  );

  useEffect(() => {
    const fetchParams = {
      page: currentPage,
      limit: 10, // Example limit
      search: searchTerm,
      type: filterType,
      date: filterDate,
    };
    fetchRecordings(fetchParams).then((data) => {
      if (data?.totalPages) {
        setTotalPages(data.totalPages);
      }
    });
  }, [searchTerm, filterType, filterDate, currentPage, fetchRecordings]);

  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    debouncedSetSearchTerm(e.target.value);
  };

  const handleFilterTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterType(e.target.value);
    setCurrentPage(1);
  };

  const handleFilterDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterDate(e.target.value);
    setCurrentPage(1);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setFilterType('');
    setFilterDate('');
    setCurrentPage(1);
    // Clear the input fields directly if debounce prevents immediate update
    const searchInput = document.getElementById('search-input') as HTMLInputElement;
    if (searchInput) searchInput.value = '';
    const typeSelect = document.getElementById('filter-type') as HTMLSelectElement;
    if (typeSelect) typeSelect.value = '';
    const dateInput = document.getElementById('filter-date') as HTMLInputElement;
    if (dateInput) dateInput.value = '';
  };

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  return (
    <section className="recordings-page">
      <h1 className="text-3xl font-bold text-text mb-6">Recordings Dashboard</h1>

      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <h2 className="text-xl font-semibold text-text mb-4">Search & Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <Input
            id="search-input"
            label="Search by Title/Description"
            type="text"
            placeholder="e.g., meeting, interview"
            onChange={handleSearchInputChange}
            aria-label="Search recordings by title or description"
          />
          <div>
            <label htmlFor="filter-type" className="block text-sm font-medium text-text-light mb-1">
              Filter by Type
            </label>
            <select
              id="filter-type"
              className="w-full p-2 border border-border rounded-md focus:ring-primary focus:border-primary transition-all duration-200"
              onChange={handleFilterTypeChange}
              value={filterType}
              aria-label="Filter recordings by type"
            >
              <option value="">All Types</option>
              <option value="meeting">Meeting</option>
              <option value="interview">Interview</option>
              <option value="lecture">Lecture</option>
              <option value="other">Other</option>
            </select>
          </div>
          <Input
            id="filter-date"
            label="Filter by Date"
            type="date"
            onChange={handleFilterDateChange}
            value={filterDate}
            aria-label="Filter recordings by date"
          />
        </div>
        <Button onClick={handleClearFilters} variant="secondary" className="w-full md:w-auto">
          Clear Filters
        </Button>
      </div>

      {loading && <StatusDisplay type="loading" message="Loading recordings..." />}
      {error && <StatusDisplay type="error" message={error} />}

      {!loading && !error && recordings.length === 0 && (
        <StatusDisplay type="info" message="No recordings found matching your criteria." />
      )}

      {!loading && !error && recordings.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recordings.map((recording: Recording) => (
              <div key={recording.id} className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200">
                <h3 className="text-xl font-semibold text-primary mb-2">{recording.title}</h3>
                <p className="text-text-light text-sm mb-2">Type: <span className="capitalize">{recording.type}</span></p>
                <p className="text-text-light text-sm mb-4">Date: {new Date(recording.date).toLocaleDateString()}</p>
                <p className="text-text mb-4">{recording.description}</p>
                <Button variant="primary" size="sm" onClick={() => alert(`Playing recording: ${recording.title}`)}>
                  Play Recording
                </Button>
              </div>
            ))}
          </div>

          <div className="flex justify-center items-center mt-8 space-x-2">
            <Button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              variant="secondary"
              size="sm"
              aria-label="Previous page"
            >
              Previous
            </Button>
            <span className="text-text-light">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              variant="secondary"
              size="sm"
              aria-label="Next page"
            >
              Next
            </Button>
          </div>
        </>
      )}
    </section>
  );
};

export default RecordingsPage;