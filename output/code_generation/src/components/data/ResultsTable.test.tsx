import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ResultsTable from './ResultsTable';
import { DataProvider } from '../../context/DataContext';
import { fetchTableData } from '../../services/api'; // Mock this API call

// Mock the API service
vi.mock('../../services/api', () => ({
  fetchTableData: vi.fn(),
}));

const mockData = Array.from({ length: 25 }, (_, i) => ({
  id: `REC-${i + 1}`,
  name: `Item ${i + 1}`,
  category: `Cat ${Math.ceil((i + 1) / 5)}`,
  status: i % 2 === 0 ? 'Active' : 'Inactive',
  value: parseFloat((100 + i).toFixed(2)),
  date: `2023-01-${String(i + 1).padStart(2, '0')}`,
}));

describe('ResultsTable', () => {
  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    // Default mock implementation for fetchTableData
    (fetchTableData as vi.Mock).mockImplementation((page, limit, searchTerm) => {
      const filteredData = mockData.filter(item =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.status.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.id.toLowerCase().includes(searchTerm.toLowerCase())
      );
      const startIndex = (page - 1) * limit;
      const endIndex = startIndex + limit;
      return Promise.resolve({
        data: filteredData.slice(startIndex, endIndex),
        totalRecords: filteredData.length,
      });
    });
  });

  const renderWithProvider = () => {
    return render(
      <DataProvider>
        <ResultsTable />
      </DataProvider>
    );
  };

  it('renders loading spinner initially', () => {
    renderWithProvider();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.getByText('Loading results...')).toBeInTheDocument();
  });

  it('displays table data after loading', async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
    });

    // Check for some data from the first page (10 items per page)
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 10')).toBeInTheDocument();
    expect(screen.queryByText('Item 11')).not.toBeInTheDocument(); // Should not be on first page
    expect(screen.getByText('Showing 10 of 25 records.')).toBeInTheDocument();
  });

  it('handles pagination correctly', async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });

    const nextPageButton = screen.getByRole('button', { name: /next page/i });
    await userEvent.click(nextPageButton);

    await waitFor(() => {
      expect(screen.getByText('Item 11')).toBeInTheDocument();
      expect(screen.getByText('Item 20')).toBeInTheDocument();
      expect(screen.queryByText('Item 1')).not.toBeInTheDocument();
      expect(screen.getByText('Showing 10 of 25 records.')).toBeInTheDocument(); // Still 10 per page
    });

    const page3Button = screen.getByRole('button', { name: /page 3/i });
    await userEvent.click(page3Button);

    await waitFor(() => {
      expect(screen.getByText('Item 21')).toBeInTheDocument();
      expect(screen.getByText('Item 25')).toBeInTheDocument();
      expect(screen.getByText('Showing 5 of 25 records.')).toBeInTheDocument(); // Last page has 5 items
    });
  });

  it('handles search filtering', async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText('Search table data');
    await userEvent.type(searchInput, 'Item 5'); // Search for a specific item

    await waitFor(() => {
      expect(screen.getByText('Item 5')).toBeInTheDocument();
      expect(screen.queryByText('Item 1')).not.toBeInTheDocument(); // Item 1 should be filtered out
      expect(screen.getByText('Showing 1 of 1 records.')).toBeInTheDocument();
    }, { timeout: 1000 }); // Give time for debounce

    await userEvent.clear(searchInput);
    await userEvent.type(searchInput, 'Cat 1'); // Search for a category

    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 5')).toBeInTheDocument();
      expect(screen.queryByText('Item 6')).not.toBeInTheDocument(); // Item 6 is in Cat 2
      expect(screen.getByText('Showing 5 of 5 records.')).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('displays error message on API failure', async () => {
    (fetchTableData as vi.Mock).mockRejectedValueOnce(new Error('Network error'));
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByText(/error loading data/i)).toBeInTheDocument();
      expect(screen.getByText(/failed to load data\. please try again\./i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });

  it('shows "No results found" when search yields no data', async () => {
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByText('Item 1')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText('Search table data');
    await userEvent.type(searchInput, 'nonexistent item');

    await waitFor(() => {
      expect(screen.queryByText('Item 1')).not.toBeInTheDocument();
      expect(screen.getByText(/no results found for "nonexistent item"/i)).toBeInTheDocument();
    }, { timeout: 1000 });
  });
});