import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DateMonthYearFilter } from '../components/features/filters/DateMonthYearFilter';
import { FilterProvider, useFilters } from '../context/FilterContext';

// Mock the useFilters hook to control its state and functions
const mockUpdateSearchQuery = jest.fn();
const mockUpdateSelectedDate = jest.fn();
const mockUpdateSelectedMonth = jest.fn();
const mockUpdateSelectedYear = jest.fn();
const mockResetFilters = jest.fn();
const mockOnApplyFilters = jest.fn();

const MockFilterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const filters = {
    searchQuery: '',
    selectedDate: '',
    selectedMonth: '',
    selectedYear: String(new Date().getFullYear()),
  };
  return (
    <FilterProvider>
      {/* Override the context value for testing */}
      <useFilters.Provider value={{
        filters,
        updateSearchQuery: mockUpdateSearchQuery,
        updateSelectedDate: mockUpdateSelectedDate,
        updateSelectedMonth: mockUpdateSelectedMonth,
        updateSelectedYear: mockUpdateSelectedYear,
        resetFilters: mockResetFilters,
      }}>
        {children}
      </useFilters.Provider>
    </FilterProvider>
  );
};

describe('DateMonthYearFilter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers(); // Use fake timers for debouncing
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders search input and filter dropdowns', () => {
    render(
      <MockFilterProvider>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} />
      </MockFilterProvider>
    );

    expect(screen.getByLabelText(/search/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/year/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/month/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/date/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reset filters/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /apply filters/i })).toBeInTheDocument();
  });

  it('calls updateSearchQuery on search input change and debounces onApplyFilters', async () => {
    render(
      <MockFilterProvider>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} />
      </MockFilterProvider>
    );

    const searchInput = screen.getByLabelText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'test query' } });

    expect(mockUpdateSearchQuery).toHaveBeenCalledWith('test query');
    expect(mockOnApplyFilters).not.toHaveBeenCalled(); // Should be debounced

    jest.advanceTimersByTime(500); // Advance timer by debounce duration

    expect(mockOnApplyFilters).toHaveBeenCalledTimes(1);
  });

  it('calls updateSelectedYear on year select change and debounces onApplyFilters', async () => {
    render(
      <MockFilterProvider>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} />
      </MockFilterProvider>
    );

    const yearSelect = screen.getByLabelText(/year/i);
    fireEvent.change(yearSelect, { target: { value: '2022' } });

    expect(mockUpdateSelectedYear).toHaveBeenCalledWith('2022');
    expect(mockOnApplyFilters).not.toHaveBeenCalled();

    jest.advanceTimersByTime(500);

    expect(mockOnApplyFilters).toHaveBeenCalledTimes(1);
  });

  it('calls updateSelectedMonth on month select change and debounces onApplyFilters', async () => {
    render(
      <MockFilterProvider>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} />
      </MockFilterProvider>
    );

    const monthSelect = screen.getByLabelText(/month/i);
    fireEvent.change(monthSelect, { target: { value: '03' } }); // March

    expect(mockUpdateSelectedMonth).toHaveBeenCalledWith('03');
    expect(mockOnApplyFilters).not.toHaveBeenCalled();

    jest.advanceTimersByTime(500);

    expect(mockOnApplyFilters).toHaveBeenCalledTimes(1);
  });

  it('calls updateSelectedDate on date select change and debounces onApplyFilters', async () => {
    // To enable date selection, we need to mock the context state to have a year and month selected
    const MockFilterProviderWithDate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
      const filters = {
        searchQuery: '',
        selectedDate: '',
        selectedMonth: '01', // January
        selectedYear: '2023',
      };
      return (
        <FilterProvider>
          <useFilters.Provider value={{
            filters,
            updateSearchQuery: mockUpdateSearchQuery,
            updateSelectedDate: mockUpdateSelectedDate,
            updateSelectedMonth: mockUpdateSelectedMonth,
            updateSelectedYear: mockUpdateSelectedYear,
            resetFilters: mockResetFilters,
          }}>
            {children}
          </useFilters.Provider>
        </FilterProvider>
      );
    };

    render(
      <MockFilterProviderWithDate>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} />
      </MockFilterProviderWithDate>
    );

    const dateSelect = screen.getByLabelText(/date/i);
    fireEvent.change(dateSelect, { target: { value: '15' } });

    expect(mockUpdateSelectedDate).toHaveBeenCalledWith('15');
    expect(mockOnApplyFilters).not.toHaveBeenCalled();

    jest.advanceTimersByTime(500);

    expect(mockOnApplyFilters).toHaveBeenCalledTimes(1);
  });

  it('calls resetFilters on "Reset Filters" button click', () => {
    render(
      <MockFilterProvider>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} />
      </MockFilterProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: /reset filters/i }));
    expect(mockResetFilters).toHaveBeenCalledTimes(1);
    expect(mockOnApplyFilters).toHaveBeenCalledTimes(1); // Reset also triggers apply
  });

  it('disables buttons when isLoading is true', () => {
    render(
      <MockFilterProvider>
        <DateMonthYearFilter onApplyFilters={mockOnApplyFilters} isLoading={true} />
      </MockFilterProvider>
    );

    expect(screen.getByRole('button', { name: /reset filters/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /applying.../i })).toBeDisabled();
  });
});