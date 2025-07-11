import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ResultsDisplay from './ResultsDisplay';
import { ResultsContext } from '../../context/ResultsContext';
import { ResultItem } from '../../services/api';

// Mock the useResults hook and its context value
const mockFetchResults = vi.fn();
const mockDownloadAllResults = vi.fn();

const mockResults: ResultItem[] = [
  { id: '1', name: 'Report A', status: 'completed', date: '2023-01-01', sizeKB: 100 },
  { id: '2', name: 'Report B', status: 'pending', date: '2023-01-02', sizeKB: 200 },
];

const renderWithResultsContext = (
  ui: React.ReactElement,
  {
    results = mockResults,
    loading = false,
    error = null,
    downloading = false,
    downloadProgress = 0,
    fetchResults = mockFetchResults,
    downloadAllResults = mockDownloadAllResults,
  } = {}
) => {
  return render(
    <ResultsContext.Provider
      value={{
        results,
        loading,
        error,
        downloading,
        downloadProgress,
        fetchResults,
        downloadAllResults,
      }}
    >
      {ui}
    </ResultsContext.Provider>
  );
};

describe('ResultsDisplay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.alert for download button
    vi.spyOn(window, 'alert').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the table with results', () => {
    renderWithResultsContext(<ResultsDisplay results={mockResults} />);

    expect(screen.getByText('Available Results')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Report A')).toBeInTheDocument();
    expect(screen.getByText('Report B')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('renders "No results to display." when results array is empty', () => {
    renderWithResultsContext(<ResultsDisplay results={[]} />);
    expect(screen.getByText('No results to display.')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('renders the Download All button with correct count', () => {
    renderWithResultsContext(<ResultsDisplay results={mockResults} />);
    const downloadButton = screen.getByRole('button', { name: /Download All \(2 records\)/i });
    expect(downloadButton).toBeInTheDocument();
    expect(downloadButton).not.toBeDisabled();
  });

  it('disables the Download All button when there are no results', () => {
    renderWithResultsContext(<ResultsDisplay results={[]} />);
    const downloadButton = screen.getByRole('button', { name: /Download All \(0 records\)/i });
    expect(downloadButton).toBeInTheDocument();
    expect(downloadButton).toBeDisabled();
  });

  it('calls downloadAllResults when the Download All button is clicked', async () => {
    renderWithResultsContext(<ResultsDisplay results={mockResults} />);
    const downloadButton = screen.getByRole('button', { name: /Download All \(2 records\)/i });

    await userEvent.click(downloadButton);

    expect(mockDownloadAllResults).toHaveBeenCalledTimes(1);
  });

  it('shows "Downloading..." state when downloading is true', () => {
    renderWithResultsContext(<ResultsDisplay results={mockResults} downloading={true} />);
    const downloadButton = screen.getByRole('button', { name: /Downloading.../i });
    expect(downloadButton).toBeInTheDocument();
    expect(downloadButton).toBeDisabled();
    expect(screen.getByRole('status', { name: /Loading/i })).toBeInTheDocument(); // Check for spinner
  });

  it('alerts if download is attempted with no results', async () => {
    renderWithResultsContext(<ResultsDisplay results={[]} />);
    const downloadButton = screen.getByRole('button', { name: /Download All \(0 records\)/i });

    await userEvent.click(downloadButton);

    expect(window.alert).toHaveBeenCalledWith('No results to download.');
    expect(mockDownloadAllResults).not.toHaveBeenCalled();
  });
});