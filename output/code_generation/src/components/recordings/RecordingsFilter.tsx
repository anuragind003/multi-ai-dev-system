import React, { useState, useEffect, useRef } from 'react';
import { useRecordings } from '../../context/RecordingsContext';
import Input from '../ui/Input';
import Button from '../ui/Button';

const RecordingsFilter: React.FC = () => {
  const { searchTerm, setSearchTerm, fetchRecordings, loading } = useRecordings();
  const [localSearchTerm, setLocalSearchTerm] = useState(searchTerm);
  const debounceTimeoutRef = useRef<number | null>(null);

  // Update local state when global searchTerm changes (e.g., on initial load)
  useEffect(() => {
    setLocalSearchTerm(searchTerm);
  }, [searchTerm]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalSearchTerm(value);

    // Debounce the search term update to avoid excessive API calls
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    debounceTimeoutRef.current = window.setTimeout(() => {
      setSearchTerm(value);
    }, 300); // 300ms debounce
  };

  const handleClearSearch = () => {
    setLocalSearchTerm('');
    setSearchTerm('');
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-6 flex flex-col sm:flex-row items-center justify-between space-y-4 sm:space-y-0 sm:space-x-4">
      <div className="flex-grow w-full sm:w-auto">
        <Input
          id="search-recordings"
          type="search"
          placeholder="Search by title, artist, or genre..."
          value={localSearchTerm}
          onChange={handleInputChange}
          className="w-full"
          aria-label="Search recordings"
        />
      </div>
      <div className="flex space-x-2 w-full sm:w-auto">
        <Button onClick={handleClearSearch} variant="secondary" disabled={!localSearchTerm || loading}>
          Clear Search
        </Button>
        {/* The actual search is debounced, so a separate "Apply" button might not be needed
            unless there are other filters. For now, the search is live. */}
        {/* <Button onClick={() => setSearchTerm(localSearchTerm)} disabled={loading}>
          Apply Filters
        </Button> */}
      </div>
    </div>
  );
};

export default RecordingsFilter;