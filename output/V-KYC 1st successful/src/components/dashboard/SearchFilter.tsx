// src/components/dashboard/SearchFilter.tsx
import React from 'react';
import { Input, Button } from '../ui/CommonUI';

interface SearchFilterProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const SearchFilter: React.FC<SearchFilterProps> = ({
  searchTerm,
  onSearchChange,
  onRefresh,
  isLoading,
}) => {
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSearchChange(e.target.value);
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-white rounded-t-lg border-b border-border">
      <div className="w-full sm:w-1/2">
        <Input
          type="text"
          placeholder="Search by name, status, or category..."
          value={searchTerm}
          onChange={handleInputChange}
          className="w-full"
          aria-label="Search records"
        />
      </div>
      <div className="w-full sm:w-auto flex justify-end">
        <Button onClick={onRefresh} isLoading={isLoading} variant="secondary" aria-label="Refresh data">
          Refresh Data
        </Button>
      </div>
    </div>
  );
};