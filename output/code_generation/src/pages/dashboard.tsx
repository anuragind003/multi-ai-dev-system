// src/pages/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { useApp } from '../hooks/useApp';
import { Table, LoadingSpinner, Button, Modal, Input } from '../components/ui';
import { Recording, TableColumn } from '../types';
import { formatDate, formatDuration, formatSize } from '../utils';

const Dashboard: React.FC = () => {
  const { recordings, isLoading, error, fetchRecordings } = useApp();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedRecording, setSelectedRecording] = useState<Recording | null>(null);

  useEffect(() => {
    fetchRecordings();
  }, [fetchRecordings]);

  const handleViewDetails = (recording: Recording) => {
    setSelectedRecording(recording);
    setIsModalOpen(true);
  };

  const columns: TableColumn<Recording>[] = [
    { key: 'title', header: 'Title' },
    {
      key: 'duration',
      header: 'Duration',
      render: (recording) => formatDuration(recording.duration),
    },
    {
      key: 'date',
      header: 'Date',
      render: (recording) => formatDate(recording.date),
    },
    {
      key: 'size',
      header: 'Size',
      render: (recording) => formatSize(recording.size),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (recording) => (
        <Button
          onClick={() => handleViewDetails(recording)}
          variant="outline"
          size="sm"
          aria-label={`View details for ${recording.title}`}
        >
          View
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full min-h-[300px]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center p-8 bg-red-100 border border-error text-error rounded-md">
        <h2 className="text-xl font-semibold mb-2">Error Loading Recordings</h2>
        <p>{error}</p>
        <Button onClick={fetchRecordings} className="mt-4" variant="danger">
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <h1 className="text-3xl font-bold text-text mb-6">Recordings Dashboard</h1>
      <div className="bg-white p-4 rounded-lg shadow-md">
        <Table<Recording>
          data={recordings}
          columns={columns}
          emptyMessage="No recordings found. Try refreshing or check your API."
          aria-label="Recordings data table"
        />
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedRecording?.title || 'Recording Details'}
      >
        {selectedRecording ? (
          <div className="space-y-4 text-text">
            <p><strong>Title:</strong> {selectedRecording.title}</p>
            <p><strong>Duration:</strong> {formatDuration(selectedRecording.duration)}</p>
            <p><strong>Date:</strong> {formatDate(selectedRecording.date)}</p>
            <p><strong>Size:</strong> {formatSize(selectedRecording.size)}</p>
            <p>
              <strong>URL:</strong>{' '}
              <a href={selectedRecording.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                {selectedRecording.url}
              </a>
            </p>
            <Button onClick={() => setIsModalOpen(false)} className="mt-4 w-full" variant="secondary">
              Close
            </Button>
          </div>
        ) : (
          <p>No recording selected.</p>
        )}
      </Modal>
    </div>
  );
};

export default Dashboard;