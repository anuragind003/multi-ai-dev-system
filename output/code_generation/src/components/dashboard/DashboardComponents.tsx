import React, { useState, useMemo } from 'react';
import { useFilters } from '../../hooks/useAppHooks';
import { Input, Card, Button, Modal } from '../ui'; // Reusable UI components
import { getMonthName, getDaysInMonth } from '../../utils/helpers'; // Utility functions

// --- Types ---
interface DashboardData {
  id: string;
  date: string; // YYYY-MM-DD
  value: number;
  description: string;
}

interface FilterBarProps {}
interface CalendarViewProps {
  data: DashboardData[];
}
interface DataDisplayProps {
  data: DashboardData[];
}

// --- FilterBar Component ---
export const FilterBar: React.FC<FilterBarProps> = () => {
  const { dateFilter, monthFilter, yearFilter, searchFilter, setFilters } = useFilters();

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 10 }, (_, i) => (currentYear - i).toString()); // Last 10 years

  const handleFilterChange = (key: keyof Omit<typeof useFilters, 'setFilters'>, value: string) => {
    setFilters({ [key]: value });
  };

  return (
    <Card className="p-4 sm:p-6 mb-6">
      <h3 className="text-xl font-semibold text-text mb-4">Filter Data</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Input
          label="Date"
          type="date"
          value={dateFilter}
          onChange={(e) => handleFilterChange('dateFilter', e.target.value)}
          aria-label="Filter by date"
        />
        <div className="relative">
          <label htmlFor="month-filter" className="block text-sm font-medium text-text-light mb-1">Month</label>
          <select
            id="month-filter"
            value={monthFilter}
            onChange={(e) => handleFilterChange('monthFilter', e.target.value)}
            className="block w-full px-3 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            aria-label="Filter by month"
          >
            <option value="">All Months</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((monthNum) => (
              <option key={monthNum} value={String(monthNum).padStart(2, '0')}>
                {getMonthName(monthNum)}
              </option>
            ))}
          </select>
        </div>
        <div className="relative">
          <label htmlFor="year-filter" className="block text-sm font-medium text-text-light mb-1">Year</label>
          <select
            id="year-filter"
            value={yearFilter}
            onChange={(e) => handleFilterChange('yearFilter', e.target.value)}
            className="block w-full px-3 py-2 border border-border rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary sm:text-sm"
            aria-label="Filter by year"
          >
            <option value="">All Years</option>
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
        <Input
          label="Search"
          type="text"
          value={searchFilter}
          onChange={(e) => handleFilterChange('searchFilter', e.target.value)}
          placeholder="Search description..."
          aria-label="Search by description"
        />
      </div>
    </Card>
  );
};

// --- CalendarView Component ---
export const CalendarView: React.FC<CalendarViewProps> = React.memo(({ data }) => {
  const { monthFilter, yearFilter } = useFilters();
  const today = new Date();
  const currentMonth = parseInt(monthFilter) || today.getMonth() + 1;
  const currentYear = parseInt(yearFilter) || today.getFullYear();

  const daysInMonth = getDaysInMonth(currentYear, currentMonth);
  const firstDayOfMonth = new Date(currentYear, currentMonth - 1, 1).getDay(); // 0 for Sunday, 1 for Monday

  // Adjust firstDayOfMonth to be 0 for Monday, 6 for Sunday
  const startDayOffset = (firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1); // Monday is 0, Sunday is 6

  const calendarDays = useMemo(() => {
    const days = [];
    // Add empty cells for days before the 1st of the month
    for (let i = 0; i < startDayOffset; i++) {
      days.push(null);
    }
    // Add days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }
    return days;
  }, [daysInMonth, startDayOffset]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDateData, setSelectedDateData] = useState<DashboardData[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>('');

  const handleDayClick = (day: number) => {
    const dateString = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dataForDay = data.filter(item => item.date === dateString);
    setSelectedDateData(dataForDay);
    setSelectedDate(dateString);
    setIsModalOpen(true);
  };

  return (
    <Card className="p-4 sm:p-6">
      <h3 className="text-xl font-semibold text-text mb-4">
        Calendar View for {getMonthName(currentMonth)} {currentYear}
      </h3>
      <div className="grid grid-cols-7 text-center font-medium text-text-light mb-2">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
          <div key={day} className="py-2">{day}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map((day, index) => {
          const dateString = day ? `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}` : '';
          const hasData = day && data.some(item => item.date === dateString);
          const isToday = day && dateString === today.toISOString().slice(0, 10);

          return (
            <div
              key={index}
              className={`relative h-16 sm:h-20 flex flex-col items-center justify-center rounded-md transition-colors duration-150
                ${day ? 'bg-gray-50 hover:bg-gray-100 cursor-pointer' : 'bg-gray-100'}
                ${isToday ? 'border-2 border-primary' : ''}
                ${hasData ? 'bg-blue-100 hover:bg-blue-200' : ''}
              `}
              onClick={() => day && handleDayClick(day)}
              role="gridcell"
              aria-label={day ? `Day ${day} of ${getMonthName(currentMonth)} ${currentYear}` : undefined}
            >
              {day && (
                <>
                  <span className={`text-lg font-semibold ${isToday ? 'text-primary' : 'text-text'}`}>
                    {day}
                  </span>
                  {hasData && (
                    <span className="absolute bottom-1 right-1 w-2 h-2 bg-accent rounded-full" aria-hidden="true"></span>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={`Data for ${selectedDate}`}>
        {selectedDateData.length > 0 ? (
          <ul className="space-y-2 max-h-60 overflow-y-auto">
            {selectedDateData.map((item) => (
              <li key={item.id} className="p-3 bg-gray-50 rounded-md border border-border">
                <p className="font-medium text-text">{item.description}</p>
                <p className="text-sm text-text-light">Value: ${item.value.toFixed(2)}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-text-light">No data available for this date.</p>
        )}
      </Modal>
    </Card>
  );
});

// --- DataDisplay Component ---
export const DataDisplay: React.FC<DataDisplayProps> = React.memo(({ data }) => {
  const { dateFilter, monthFilter, yearFilter, searchFilter } = useFilters();

  const filteredData = useMemo(() => {
    return data.filter(item => {
      const itemDate = new Date(item.date);
      const itemMonth = String(itemDate.getMonth() + 1).padStart(2, '0');
      const itemYear = String(itemDate.getFullYear());

      const matchesDate = dateFilter ? item.date === dateFilter : true;
      const matchesMonth = monthFilter ? itemMonth === monthFilter : true;
      const matchesYear = yearFilter ? itemYear === yearFilter : true;
      const matchesSearch = searchFilter
        ? item.description.toLowerCase().includes(searchFilter.toLowerCase())
        : true;

      return matchesDate && matchesMonth && matchesYear && matchesSearch;
    });
  }, [data, dateFilter, monthFilter, yearFilter, searchFilter]);

  return (
    <Card className="p-4 sm:p-6">
      <h3 className="text-xl font-semibold text-text mb-4">Filtered Data ({filteredData.length} items)</h3>
      <div className="max-h-96 overflow-y-auto pr-2">
        {filteredData.length > 0 ? (
          <ul className="space-y-3">
            {filteredData.map((item) => (
              <li key={item.id} className="p-4 bg-gray-50 rounded-md border border-border shadow-sm">
                <p className="text-sm text-text-light">{item.date}</p>
                <p className="font-medium text-text">{item.description}</p>
                <p className="text-lg font-bold text-primary mt-1">${item.value.toFixed(2)}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-text-light text-center py-8">No data matches the current filters.</p>
        )}
      </div>
    </Card>
  );
});