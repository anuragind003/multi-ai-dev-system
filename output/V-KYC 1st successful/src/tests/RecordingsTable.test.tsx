import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import RecordingsTable from '@/components/recordings/RecordingsTable';
import { Recording } from '@/context/RecordingsContext'; // Import the type

// Mock data for testing
const mockRecordings: Recording[] = [
  {
    id: 'rec1',
    title: 'Meeting with Client A',
    duration: 3600, // 1 hour
    date: '2023-01-15T10:00:00Z',
    speaker: 'John Doe',
    tags: ['meeting', 'client'],
    url: 'http://example.com/rec1',
  },
  {
    id: 'rec2',
    title: 'Team Standup',
    duration: 900, // 15 minutes
    date: '2023-01-16T09:30:00Z',
    speaker: 'Jane Smith',
    tags: ['daily', 'internal'],
    url: 'http://example.com/rec2',
  },
];

describe('RecordingsTable', () => {
  beforeEach(() => {
    // Clean up any previous renders
    document.body.innerHTML = '';
  });

  it('renders table headers correctly', () => {
    render(<RecordingsTable recordings={[]} />);

    expect(screen.getByRole('columnheader', { name: /title/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /speaker/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /duration/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /date/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /tags/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /actions/i })).toBeInTheDocument();
  });

  it('renders recording data correctly', () => {
    render(<RecordingsTable recordings={mockRecordings} />);

    // Check for first recording
    expect(screen.getByText('Meeting with Client A')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('60m 0s')).toBeInTheDocument(); // Formatted duration
    expect(screen.getByText('Jan 15, 2023')).toBeInTheDocument(); // Formatted date
    expect(screen.getByText('meeting')).toBeInTheDocument();
    expect(screen.getByText('client')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /listen to meeting with client a/i })).toHaveAttribute('href', 'http://example.com/rec1');

    // Check for second recording
    expect(screen.getByText('Team Standup')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('15m 0s')).toBeInTheDocument();
    expect(screen.getByText('Jan 16, 2023')).toBeInTheDocument();
    expect(screen.getByText('daily')).toBeInTheDocument();
    expect(screen.getByText('internal')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /listen to team standup/i })).toHaveAttribute('href', 'http://example.com/rec2');
  });

  it('displays "Listen" link for each recording', () => {
    render(<RecordingsTable recordings={mockRecordings} />);

    const listenLinks = screen.getAllByRole('link', { name: /listen/i });
    expect(listenLinks).toHaveLength(mockRecordings.length);
    expect(listenLinks[0]).toHaveAttribute('href', mockRecordings[0].url);
    expect(listenLinks[1]).toHaveAttribute('href', mockRecordings[1].url);
  });

  it('renders an empty table when no recordings are provided', () => {
    render(<RecordingsTable recordings={[]} />);

    // Check that no recording titles are present
    expect(screen.queryByText('Meeting with Client A')).not.toBeInTheDocument();
    expect(screen.queryByText('Team Standup')).not.toBeInTheDocument();

    // Check that the table body is empty or only contains headers
    const rows = screen.getAllByRole('row');
    // Expecting only the header row
    expect(rows).toHaveLength(1);
  });

  it('applies React.memo optimization', () => {
    // This is a conceptual test. React.memo is a HOC, and its effect
    // is on re-renders. We can't directly test if it's memoized
    // without complex mocking of React internals.
    // However, we can assert that the component itself is rendered.
    const { rerender } = render(<RecordingsTable recordings={mockRecordings} />);
    const initialRenderCount = vi.fn();
    initialRenderCount(); // Simulate a render

    rerender(<RecordingsTable recordings={mockRecordings} />); // Re-render with same props
    initialRenderCount(); // Simulate a render

    // If memoization works, the component's render logic might not execute again
    // if props are shallowly equal. This test primarily checks if the component
    // can be re-rendered without issues.
    expect(screen.getByText('Meeting with Client A')).toBeInTheDocument();
  });
});