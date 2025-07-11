import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Table } from '../components/ui/Table';
import { Spinner } from '../components/ui/Spinner';
import { apiService } from '../services/apiService';
import { UploadResult, UploadStatus, BulkUploadRequest } from '../utils/types';

const BulkUploadResultsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);

  const [results, setResults] = useState<UploadResult[]>([]);
  const [loadingResults, setLoadingResults] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [currentRequestId, setCurrentRequestId] = useState<string | null>(id || null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0]);
      setUploadError(null);
      setUploadSuccessMessage(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a file to upload.');
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadSuccessMessage(null);
    setResults([]); // Clear previous results

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      const response = await apiService.uploadFile(formData);
      setUploadSuccessMessage(`Upload initiated successfully! Request ID: ${response.requestId}`);
      setCurrentRequestId(response.requestId);
      setUploadFile(null); // Clear file input
    } catch (error: any) {
      setUploadError(error.message || 'Failed to initiate upload.');
    } finally {
      setUploading(false);
    }
  };

  const fetchUploadResults = useCallback(async (requestId: string) => {
    setLoadingResults(true);
    setResultsError(null);
    try {
      const response: BulkUploadRequest = await apiService.getUploadResults(requestId);
      setResults(response.results || []);
      if (response.status === UploadStatus.Completed || response.status === UploadStatus.Failed) {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      }
    } catch (error: any) {
      setResultsError(error.message || 'Failed to fetch upload results.');
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    } finally {
      setLoadingResults(false);
    }
  }, [pollingInterval]);

  useEffect(() => {
    if (currentRequestId) {
      // Clear any existing interval before setting a new one
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
      fetchUploadResults(currentRequestId); // Initial fetch
      const interval = setInterval(() => fetchUploadResults(currentRequestId), 5000); // Poll every 5 seconds
      setPollingInterval(interval);
    }

    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [currentRequestId, fetchUploadResults]);

  const tableColumns = [
    { header: 'Row ID', accessor: 'rowId' },
    { header: 'Status', accessor: 'status', render: (row: UploadResult) => (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
        row.status === 'SUCCESS' ? 'bg-green-100 text-success' : 'bg-red-100 text-error'
      }`}>
        {row.status}
      </span>
    )},
    { header: 'Message', accessor: 'message' },
    { header: 'Data', accessor: 'data', render: (row: UploadResult) => (
      <pre className="text-xs bg-gray-50 p-2 rounded-md overflow-auto max-h-20">
        {JSON.stringify(row.data, null, 2)}
      </pre>
    )},
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold text-text mb-6">Bulk Upload Results</h2>

      {/* File Upload Section */}
      <div className="bg-white p-6 rounded-lg shadow-soft mb-8">
        <h3 className="text-xl font-semibold text-text mb-4">Upload New File</h3>
        <form onSubmit={handleUploadSubmit} className="flex flex-col sm:flex-row items-center gap-4">
          <Input
            type="file"
            id="bulk-upload-file"
            accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/json"
            onChange={handleFileChange}
            className="flex-1"
            aria-label="Select file for bulk upload"
          />
          <Button type="submit" disabled={uploading || !uploadFile}>
            {uploading ? <Spinner size="sm" /> : 'Upload File'}
          </Button>
        </form>
        {uploadError && <p className="text-error mt-2 text-sm" role="alert">{uploadError}</p>}
        {uploadSuccessMessage && <p className="text-success mt-2 text-sm" role="status">{uploadSuccessMessage}</p>}
      </div>

      {/* Results Display Section */}
      <div className="bg-white p-6 rounded-lg shadow-soft">
        <h3 className="text-xl font-semibold text-text mb-4">Upload Request Results</h3>
        {currentRequestId ? (
          <p className="text-text-light mb-4">
            Displaying results for Request ID: <span className="font-mono text-primary">{currentRequestId}</span>
          </p>
        ) : (
          <p className="text-text-light mb-4">No upload request selected or initiated yet.</p>
        )}

        {loadingResults && (
          <div className="flex justify-center items-center py-8">
            <Spinner size="lg" />
            <p className="ml-4 text-text-light">Loading results...</p>
          </div>
        )}

        {resultsError && <p className="text-error mt-4" role="alert">{resultsError}</p>}

        {!loadingResults && !resultsError && results.length > 0 && (
          <Table<UploadResult>
            data={results}
            columns={tableColumns}
            keyAccessor="rowId"
            emptyMessage="No results found for this upload."
          />
        )}

        {!loadingResults && !resultsError && results.length === 0 && currentRequestId && (
          <p className="text-text-light text-center py-8">
            No results available yet, or upload is still processing. Please wait or try again later.
          </p>
        )}
      </div>
    </div>
  );
};

export default BulkUploadResultsPage;