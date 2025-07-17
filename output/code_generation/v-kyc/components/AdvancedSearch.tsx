import React, { useState } from 'react';
import { SearchType } from '../types';

interface AdvancedSearchProps {
  onSearch: (params: any) => void;
  isLoading?: boolean;
}

const AdvancedSearch: React.FC<AdvancedSearchProps> = ({ onSearch, isLoading = false }) => {
  const [searchType, setSearchType] = useState<SearchType>(SearchType.SINGLE_ID);
  const [searchParams, setSearchParams] = useState({
    lanId: '',
    date: '',
    month: '',
    startDate: '',
    endDate: '',
    status: '',
    fileSize: ''
  });

  const handleSearch = () => {
    const params = { ...searchParams };
    
    // Clean up empty parameters
    Object.keys(params).forEach(key => {
      if (params[key as keyof typeof params] === '') {
        delete params[key as keyof typeof params];
      }
    });

    onSearch(params);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      const lanIds = content
        .split(/[\n,]/)
        .map(id => id.trim())
        .filter(id => id.length > 0)
        .slice(0, 50); // Limit to 50 IDs

      if (lanIds.length > 0) {
        onSearch({ lanIds });
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Advanced Search</h3>
      
      {/* Search Type Selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Search Type
        </label>
        <div className="flex space-x-4">
          {Object.values(SearchType).map((type) => (
            <label key={type} className="flex items-center">
              <input
                type="radio"
                name="searchType"
                value={type}
                checked={searchType === type}
                onChange={(e) => setSearchType(e.target.value as SearchType)}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">
                {type === SearchType.SINGLE_ID ? 'Single LAN ID' :
                 type === SearchType.DATE ? 'Date Range' :
                 'Bulk Upload'}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Search Fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
        {searchType === SearchType.SINGLE_ID && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              LAN ID
            </label>
            <input
              type="text"
              value={searchParams.lanId}
              onChange={(e) => setSearchParams({ ...searchParams, lanId: e.target.value })}
              placeholder="Enter LAN ID"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}

        {searchType === SearchType.DATE && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={searchParams.startDate}
                onChange={(e) => setSearchParams({ ...searchParams, startDate: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={searchParams.endDate}
                onChange={(e) => setSearchParams({ ...searchParams, endDate: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Month
          </label>
          <input
            type="month"
            value={searchParams.month}
            onChange={(e) => setSearchParams({ ...searchParams, month: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            value={searchParams.status}
            onChange={(e) => setSearchParams({ ...searchParams, status: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Status</option>
            <option value="APPROVED">Approved</option>
            <option value="PENDING">Pending</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            File Size
          </label>
          <select
            value={searchParams.fileSize}
            onChange={(e) => setSearchParams({ ...searchParams, fileSize: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Sizes</option>
            <option value="small">Small (&lt; 10MB)</option>
            <option value="medium">Medium (10-50MB)</option>
            <option value="large">Large (&gt; 50MB)</option>
          </select>
        </div>
      </div>

      {/* Bulk Upload */}
      {searchType === SearchType.BULK && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload File (CSV/TXT)
          </label>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <input
              type="file"
              accept=".csv,.txt"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="text-gray-600">
                <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                  <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <p className="mt-2">Click to upload or drag and drop</p>
                <p className="text-xs text-gray-500">CSV or TXT files with LAN IDs (max 50)</p>
              </div>
            </label>
          </div>
        </div>
      )}

      {/* Search Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>
    </div>
  );
};

export default AdvancedSearch; 