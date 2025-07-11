import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AppContextProvider, useRecordings } from '@context/AppContext';
import DashboardPage from '@pages/DashboardPage';
import { vi } from 'vitest';
import { Recording } from '@types';

// Mock the useRecordings hook to control its behavior in tests
vi.mock('@context/AppContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@context/AppContext')>();
  return {
    ...actual,
    useRecordings: vi.fn(),
  };
});

const mockRecordings: Recording[] = [
  {
    id: 'rec1',
    title: 'Meeting Notes',
    description: 'Important discussion points from the team meeting.',
    duration: 3600,
    uploadDate: '2023-01-15T10:00:00Z',
    url: 'http://example.com/rec1.mp3',
    status: 'ready',
  },
  {
    id: 'rec2',
    title: 'Product Demo',
    description: 'Demonstration of new product features.',
    duration: 1200,
    uploadDate: '2023-02-20T14:30:00Z',
    url: 'http://example.com/rec2.mp4',
    status: 'processing',
  },
];

describe('DashboardPage', () => {
  const mockFetchRecordings = vi.fn();
  const mockAddRecording = vi.fn();
  const mockUpdateRecording = vi.fn();
  const mockDeleteRecording = vi.fn();

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    (useRecordings as vi.Mock).mockReturnValue({
      recordings: mockRecordings,
      loading: false,
      error: null,
      fetchRecordings: mockFetchRecordings,
      addRecording: mockAddRecording,
      updateRecording: mockUpdateRecording,
      deleteRecording: mockDeleteRecording,
    });
  });

  const renderDashboard = () => {
    return render(
      <BrowserRouter>
        <AppContextProvider> {/* AppContextProvider is needed for useAuth in AppLayout, even if useRecordings is mocked */}
          <DashboardPage />
        </AppContextProvider>
      </BrowserRouter>
    );
  };

  test('renders dashboard title and "Add New Recording" button', async () => {
    renderDashboard();
    expect(screen.getByRole('heading', { name: /Recordings Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add New Recording/i })).toBeInTheDocument();
  });

  test('fetches recordings on initial render', async () => {
    renderDashboard();
    await waitFor(() => expect(mockFetchRecordings).toHaveBeenCalledTimes(1));
  });

  test('displays recordings in the table', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('Meeting Notes')).toBeInTheDocument();
      expect(screen.getByText('Product Demo')).toBeInTheDocument();
      expect(screen.getByText('3600s')).toBeInTheDocument();
      expect(screen.getByText('1200s')).toBeInTheDocument();
      expect(screen.getByText('ready')).toBeInTheDocument();
      expect(screen.getByText('processing')).toBeInTheDocument();
    });
  });

  test('shows loading spinner when recordings are loading', async () => {
    (useRecordings as vi.Mock).mockReturnValueOnce({
      recordings: [],
      loading: true,
      error: null,
      fetchRecordings: mockFetchRecordings,
      addRecording: mockAddRecording,
      updateRecording: mockUpdateRecording,
      deleteRecording: mockDeleteRecording,
    });
    renderDashboard();
    expect(screen.getByText(/Loading recordings.../i)).toBeInTheDocument();
    expect(screen.getByRole('status', { name: /Loading/i })).toBeInTheDocument();
  });

  test('displays error message if fetching recordings fails', async () => {
    (useRecordings as vi.Mock).mockReturnValueOnce({
      recordings: [],
      loading: false,
      error: 'Failed to load recordings',
      fetchRecordings: mockFetchRecordings,
      addRecording: mockAddRecording,
      updateRecording: mockUpdateRecording,
      deleteRecording: mockDeleteRecording,
    });
    renderDashboard();
    expect(screen.getByRole('alert', { name: /Error! Failed to load recordings/i })).toBeInTheDocument();
  });

  test('opens "Add New Recording" modal when button is clicked', async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: /Add New Recording/i }));
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Add New Recording/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/Title/i)).toHaveValue('');
      expect(screen.getByLabelText(/Description/i)).toHaveValue('');
      expect(screen.getByLabelText(/Duration \(seconds\)/i)).toHaveValue(0);
      expect(screen.getByLabelText(/URL/i)).toHaveValue('');
    });
  });

  test('opens "Edit Recording" modal with pre-filled data when edit button is clicked', async () => {
    renderDashboard();
    fireEvent.click(screen.getAllByRole('button', { name: /Edit/i })[0]); // Click edit for 'Meeting Notes'
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Edit Recording/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/Title/i)).toHaveValue('Meeting Notes');
      expect(screen.getByLabelText(/Description/i)).toHaveValue('Important discussion points from the team meeting.');
      expect(screen.getByLabelText(/Duration \(seconds\)/i)).toHaveValue(3600);
      expect(screen.getByLabelText(/URL/i)).toHaveValue('http://example.com/rec1.mp3');
    });
  });

  test('calls addRecording when new recording form is submitted successfully', async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: /Add New Recording/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Add New Recording/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: 'New Recording' } });
    fireEvent.change(screen.getByLabelText(/Description/i), { target: { value: 'A brand new recording for testing.' } });
    fireEvent.change(screen.getByLabelText(/Duration \(seconds\)/i), { target: { value: '600' } });
    fireEvent.change(screen.getByLabelText(/URL/i), { target: { value: 'http://example.com/new.mp3' } });

    fireEvent.click(screen.getByRole('button', { name: /Add Recording/i }));

    await waitFor(() => {
      expect(mockAddRecording).toHaveBeenCalledTimes(1);
      expect(mockAddRecording).toHaveBeenCalledWith({
        title: 'New Recording',
        description: 'A brand new recording for testing.',
        duration: 600,
        url: 'http://example.com/new.mp3',
      });
      expect(screen.queryByRole('dialog', { name: /Add New Recording/i })).not.toBeInTheDocument(); // Modal closes
    });
  });

  test('calls updateRecording when edit recording form is submitted successfully', async () => {
    renderDashboard();
    fireEvent.click(screen.getAllByRole('button', { name: /Edit/i })[0]); // Click edit for 'Meeting Notes'

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Edit Recording/i })).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: 'Updated Meeting Notes' } });
    fireEvent.click(screen.getByRole('button', { name: /Update Recording/i }));

    await waitFor(() => {
      expect(mockUpdateRecording).toHaveBeenCalledTimes(1);
      expect(mockUpdateRecording).toHaveBeenCalledWith('rec1', {
        title: 'Updated Meeting Notes',
        description: 'Important discussion points from the team meeting.',
        duration: 3600,
        url: 'http://example.com/rec1.mp3',
      });
      expect(screen.queryByRole('dialog', { name: /Edit Recording/i })).not.toBeInTheDocument(); // Modal closes
    });
  });

  test('calls deleteRecording when delete button is clicked', async () => {
    renderDashboard();
    fireEvent.click(screen.getAllByRole('button', { name: /Delete/i })[0]); // Click delete for 'Meeting Notes'

    await waitFor(() => {
      expect(mockDeleteRecording).toHaveBeenCalledTimes(1);
      expect(mockDeleteRecording).toHaveBeenCalledWith('rec1');
    });
  });

  test('displays "No recordings found" message if recordings array is empty', async () => {
    (useRecordings as vi.Mock).mockReturnValueOnce({
      recordings: [],
      loading: false,
      error: null,
      fetchRecordings: mockFetchRecordings,
      addRecording: mockAddRecording,
      updateRecording: mockUpdateRecording,
      deleteRecording: mockDeleteRecording,
    });
    renderDashboard();
    expect(screen.getByText(/No recordings found./i)).toBeInTheDocument();
    expect(screen.getByText(/Click "Add New Recording" to get started!/i)).toBeInTheDocument();
  });
});