import React, { useEffect, useMemo } from 'react';
import { useFilters } from '../../../context/FilterContext';
import { Input, Button } from '../../ui/CommonUI';

interface DateMonthYearFilterProps {
  onApplyFilters: () => void;
  isLoading?: boolean;
}

export const DateMonthYearFilter: React.FC<DateMonthYearFilterProps> = ({ onApplyFilters, isLoading }) => {
  const { filters, updateSearchQuery, updateSelectedDate, updateSelectedMonth, updateSelectedYear, resetFilters } = useFilters();

  const currentYear = new Date().getFullYear();
  const years = useMemo(() => Array.from({ length: 10 }, (_, i) => String(currentYear - 5 + i)), [currentYear]);
  const months = useMemo(() => [
    { value: '', label: 'All Months' },
    { value: '01', label: 'January' }, { value: '02', label: 'February' }, { value: '03', label: 'March' },
    { value: '04', label: 'April' }, { value: '05', label: 'May' }, { value: '06', label: 'June' },
    { value: '07', label: 'July' }, { value: '08', label: 'August' }, { value: '09', label: 'September' },
    { value: '10', label: 'October' }, { value: '11', label: 'November' }, { value: '12', label: 'December' },
  ], []);

  const daysInMonth = useMemo(() => {
    if (!filters.selectedYear || !filters.selectedMonth) return 31;
    const year = parseInt(filters.selectedYear);
    const month = parseInt(filters.selectedMonth);
    return new Date(year, month, 0).getDate();
  }, [filters.selectedYear, filters.selectedMonth]);

  const dates = useMemo(() => {
    const dateOptions = [{ value: '', label: 'All Dates' }];
    for (let i = 1; i <= daysInMonth; i++) {
      dateOptions.push({ value: String(i).padStart(2, '0'), label: String(i) });
    }
    return dateOptions;
  }, [daysInMonth]);

  // Effect to trigger filter application when filters change
  useEffect(() => {
    const handler = setTimeout(() => {
      onApplyFilters();
    }, 500); // Debounce filter application
    return () => clearTimeout(handler);
  }, [filters, onApplyFilters]);

  return (
    <Card className="mb-6 p-4 md:p-6">
      <h3 className="text-xl font-semibold text-text mb-4">Filter Data</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search Input */}
        <Input
          label="Search"
          type="text"
          placeholder="Enter keyword..."
          value={filters.searchQuery}
          onChange={(e) => updateSearchQuery(e.target.value)}
          aria-label="Search keyword"
        />

        {/* Year Filter */}
        <div>
          <label htmlFor="year-filter" className="block text-sm font-medium text-text-light mb-1">Year</label>
          <select
            id="year-filter"
            className="block w-full px-3 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            value={filters.selectedYear}
            onChange={(e) => updateSelectedYear(e.target.value)}
            aria-label="Select year"
          >
            <option value="">All Years</option>
            {years.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>

        {/* Month Filter */}
        <div>
          <label htmlFor="month-filter" className="block text-sm font-medium text-text-light mb-1">Month</label>
          <select
            id="month-filter"
            className="block w-full px-3 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            value={filters.selectedMonth}
            onChange={(e) => updateSelectedMonth(e.target.value)}
            aria-label="Select month"
          >
            {months.map(month => (
              <option key={month.value} value={month.value}>{month.label}</option>
            ))}
          </select>
        </div>

        {/* Date Filter */}
        <div>
          <label htmlFor="date-filter" className="block text-sm font-medium text-text-light mb-1">Date</label>
          <select
            id="date-filter"
            className="block w-full px-3 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            value={filters.selectedDate}
            onChange={(e) => updateSelectedDate(e.target.value)}
            aria-label="Select date"
            disabled={!filters.selectedYear || !filters.selectedMonth}
          >
            {dates.map(date => (
              <option key={date.value} value={date.value}>{date.label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-6 flex justify-end gap-4">
        <Button onClick={resetFilters} variant="outline" disabled={isLoading} aria-label="Reset filters">
          Reset Filters
        </Button>
        {/* The onApplyFilters is debounced by useEffect, so no explicit apply button is strictly needed,
            but it's good for UX to have one if the debounce is long or for manual trigger.
            For this example, the useEffect handles it, so this button is illustrative. */}
        <Button onClick={onApplyFilters} disabled={isLoading} aria-label="Apply filters">
          {isLoading ? 'Applying...' : 'Apply Filters'}
        </Button>
      </div>
    </Card>
  );
};