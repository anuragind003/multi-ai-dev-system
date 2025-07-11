import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import DashboardPage from './DashboardPage';
import * as api from '../services/api';
import { vi } from 'vitest';

// Mock the uploadFiles API call
const mockUploadFiles = vi.spyOn(api, 'uploadFiles');

// Helper to create a mock file
const createMockFile = (name: string, size: number, type: string) => {
  const file = new File(['hello'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

describe('DashboardPage', () => {
  beforeEach(() => {
    // Reset mocks before each test
    mockUploadFiles.mockClear();
    // Simulate a logged-in user for protected route
    localStorage.setItem('user', JSON.stringify({ username: 'testuser' }));
  });

  afterEach(() => {
    localStorage.clear();
  });

  const renderDashboard = () => {
    return render(
      <Router>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </Router>
    );
  };

  it('renders the file upload form', () => {
    renderDashboard();
    expect(screen.getByText(/Bulk File Upload/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag & Drop your files here, or/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload All Files/i })).toBeInTheDocument();
  });

  it('allows selecting files via input and displays them', async () => {
    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;

    const file1 = createMockFile('test1.csv', 1024, 'text/csv');
    const file2 = createMockFile('test2.xlsx', 2048, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');

    await user.upload(fileInput, [file1, file2]);

    expect(screen.getByText('Selected Files (2)')).toBeInTheDocument();
    expect(screen.getByText('test1.csv')).toBeInTheDocument();
    expect(screen.getByText('test2.xlsx')).toBeInTheDocument();
    expect(screen.getByText('1 KB')).toBeInTheDocument();
    expect(screen.getByText('2 KB')).toBeInTheDocument();
  });

  it('allows removing a selected file', async () => {
    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;

    const file1 = createMockFile('test1.csv', 1024, 'text/csv');
    await user.upload(fileInput, file1);

    expect(screen.getByText('test1.csv')).toBeInTheDocument();

    const removeButton = screen.getByRole('button', { name: /Remove test1.csv/i });
    await user.click(removeButton);

    expect(screen.queryByText('test1.csv')).not.toBeInTheDocument();
    expect(screen.queryByText('Selected Files (0)')).toBeInTheDocument();
  });

  it('displays an error for invalid file type', async () => {
    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;

    const invalidFile = createMockFile('image.png', 100, 'image/png');
    await user.upload(fileInput, invalidFile);

    expect(screen.getByText('Only CSV and Excel files are allowed.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload All Files/i })).toBeDisabled();
  });

  it('displays an error for file exceeding max size', async () => {
    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;

    const largeFile = createMockFile('large.csv', 6 * 1024 * 1024, 'text/csv'); // 6MB
    await user.upload(fileInput, largeFile);

    expect(screen.getByText(/Max file size is 5 MB./i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload All Files/i })).toBeDisabled();
  });

  it('handles successful file upload', async () => {
    mockUploadFiles.mockResolvedValue({
      message: 'Files uploaded successfully!',
      files: [{ name: 'upload.csv', status: 'success', url: '/uploads/upload.csv' }],
    });

    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;
    const uploadButton = screen.getByRole('button', { name: /Upload All Files/i });

    const file = createMockFile('upload.csv', 1024, 'text/csv');
    await user.upload(fileInput, file);

    expect(uploadButton).not.toBeDisabled();
    await user.click(uploadButton);

    expect(screen.getByText('Uploading...')).toBeInTheDocument(); // Loading state
    expect(mockUploadFiles).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText('Files uploaded successfully!')).toBeInTheDocument();
      expect(screen.getByText('Uploaded')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Download upload.csv/i })).toBeInTheDocument();
    }, { timeout: 3000 }); // Increased timeout for simulated API call
  });

  it('handles failed file upload', async () => {
    mockUploadFiles.mockRejectedValue({
      message: 'Failed to upload some files.',
      files: [{ name: 'fail.csv', status: 'failed' }],
    });

    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;
    const uploadButton = screen.getByRole('button', { name: /Upload All Files/i });

    const file = createMockFile('fail.csv', 1024, 'text/csv');
    await user.upload(fileInput, file);

    await user.click(uploadButton);

    expect(screen.getByText('Uploading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Failed to upload some files.')).toBeInTheDocument();
      expect(screen.getByText('Failed')).toBeInTheDocument();
      expect(screen.getByText('Upload failed for this file.')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('resets form and messages after upload attempt', async () => {
    mockUploadFiles.mockResolvedValue({
      message: 'Files uploaded successfully!',
      files: [{ name: 'upload.csv', status: 'success', url: '/uploads/upload.csv' }],
    });

    renderDashboard();
    const user = userEvent.setup();
    const fileInput = screen.getByLabelText(/Drag and drop files or click to select/i).closest('div')?.querySelector('input[type="file"]') as HTMLInputElement;
    const uploadButton = screen.getByRole('button', { name: /Upload All Files/i });

    const file = createMockFile('upload.csv', 1024, 'text/csv');
    await user.upload(fileInput, file);
    await user.click(uploadButton);

    await waitFor(() => {
      expect(screen.getByText('Files uploaded successfully!')).toBeInTheDocument();
    }, { timeout: 3000 });

    // After successful upload, the selected files list should be empty
    expect(screen.queryByText('Selected Files (1)')).not.toBeInTheDocument();
    expect(screen.queryByText('upload.csv')).not.toBeInTheDocument();
    expect(uploadButton).toBeDisabled(); // Because no files are selected
  });
});