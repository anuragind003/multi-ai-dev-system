import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AppContextProvider } from '../context/AppContext';
import { DashboardPage } from '../pages'; // Import DashboardPage from the consolidated pages file
import * as api from '../services/api'; // Import the API service

// Mock the API service
const mockFetchDashboardData = vi.spyOn(api, 'fetchDashboardData');

const mockData = [
  { id: '1', date: '2023-10-01', value: 100, description: 'Test data 1' },
  { id: '2', date: '2023-10-15', value: 200, description: 'Another test' },
  { id: '3', date: '2023-11-01', value: 50, description: 'November data' },
];

describe('DashboardPage', () => {
  beforeEach(() => {
    // Reset mocks before each test
    mockFetchDashboardData.mockClear();
    mockFetchDashboardData.mockResolvedValue(mockData);
    localStorage.clear(); // Clear local storage for auth state
  });

  const renderDashboard = () => {
    // Wrap with BrowserRouter and AppContextProvider for context and routing
    return render(
      <BrowserRouter>
        <AppContextProvider>
          <DashboardPage />
        </AppContextProvider>
      </BrowserRouter>
    );
  };

  it('renders DashboardPage with loading state initially', async () => {
    renderDashboard();
    expect(screen.getByLabelText('Loading')).toBeInTheDocument();
    await waitFor(() => expect(mockFetchDashboardData).toHaveBeenCalledTimes(1));
  });

  it('displays dashboard data after loading', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('Dashboard Overview')).toBeInTheDocument());
    expect(screen.getByText('Test data 1')).toBeInTheDocument();
    expect(screen.getByText('Another test')).toBeInTheDocument();
    expect(screen.getByText('November data')).toBeInTheDocument();
  });

  it('applies date filter correctly', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('Dashboard Overview')).toBeInTheDocument());

    const dateInput = screen.getByLabelText('Filter by date');
    userEvent.type(dateInput, '2023-10-01'); // Simulate typing a date

    // Wait for the API call with the new filter
    await waitFor(() => {
      expect(mockFetchDashboardData).toHaveBeenCalledWith(
        expect.objectContaining({ date: '2023-10-01' })
      );
    });

    // Mock the API response for the filtered data
    mockFetchDashboardData.mockResolvedValueOnce([mockData[0]]);
    userEvent.click(screen.getByRole('button', { name: /search/i })); // Trigger re-fetch (though not explicitly needed for date input)

    await waitFor(() => {
      expect(screen.getByText('Test data 1')).toBeInTheDocument();
      expect(screen.queryByText('Another test')).not.toBeInTheDocument();
    });
  });

  it('applies month filter correctly', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('Dashboard Overview')).toBeInTheDocument());

    const monthSelect = screen.getByLabelText('Filter by month');
    userEvent.selectOptions(monthSelect, '11'); // Select November (month 11)

    await waitFor(() => {
      expect(mockFetchDashboardData).toHaveBeenCalledWith(
        expect.objectContaining({ month: '11' })
      );
    });

    mockFetchDashboardData.mockResolvedValueOnce([mockData[2]]); // Mock response for November
    userEvent.click(screen.getByRole('button', { name: /search/i })); // Trigger re-fetch

    await waitFor(() => {
      expect(screen.getByText('November data')).toBeInTheDocument();
      expect(screen.queryByText('Test data 1')).not.toBeInTheDocument();
    });
  });

  it('applies search filter correctly', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('Dashboard Overview')).toBeInTheDocument());

    const searchInput = screen.getByLabelText('Search by description');
    userEvent.type(searchInput, 'another');

    await waitFor(() => {
      expect(mockFetchDashboardData).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'another' })
      );
    });

    mockFetchDashboardData.mockResolvedValueOnce([mockData[1]]); // Mock response for 'another'
    userEvent.click(screen.getByRole('button', { name: /search/i })); // Trigger re-fetch

    await waitFor(() => {
      expect(screen.getByText('Another test')).toBeInTheDocument();
      expect(screen.queryByText('Test data 1')).not.toBeInTheDocument();
    });
  });

  it('displays error message if data fetch fails', async () => {
    mockFetchDashboardData.mockRejectedValueOnce(new Error('Network error'));
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch dashboard data. Please try again.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Test data 1')).not.toBeInTheDocument();
  });

  it('opens and closes modal on calendar day click', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('Dashboard Overview')).toBeInTheDocument());

    // Find a day with data (e.g., Oct 1)
    const dayWithData = screen.getByLabelText('Day 1 of October 2023');
    userEvent.click(dayWithData);

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /data for 2023-10-01/i })).toBeInTheDocument();
    });
    expect(screen.getByText('Test data 1')).toBeInTheDocument();

    const closeButton = screen.getByLabelText('Close modal');
    userEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });
});