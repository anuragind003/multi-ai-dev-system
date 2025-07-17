import React, { createContext, useState, useContext, useCallback } from 'react';
import { fetchBulkResults, downloadBulkResults, ResultItem } from '../services/api'; // Assuming ResultItem type is exported from api.ts
import { Modal, Button } from '../components/ui'; // For download confirmation/progress

// Define the shape of the results context
interface ResultsContextType {
  results: ResultItem[];
  loading: boolean;
  error: string | null;
  downloading: boolean;
  downloadProgress: number; // 0-100
  fetchResults: () => Promise<void>;
  downloadAllResults: () => Promise<void>;
}

// Create the ResultsContext
export const ResultsContext = createContext<ResultsContextType | undefined>(undefined);

/**
 * ResultsContextProvider component.
 * Manages the state for bulk results, including fetching and downloading.
 */
export const ResultsContextProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [results, setResults] = useState<ResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);

  // Memoized function to fetch results
  const fetchResults = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBulkResults();
      setResults(data);
    } catch (err: any) {
      console.error('Failed to fetch results:', err);
      setError(err.message || 'Failed to load results. Please try again.');
      setResults([]); // Clear results on error
    } finally {
      setLoading(false);
    }
  }, []);

  // Memoized function to download all results
  const downloadAllResults = useCallback(async () => {
    if (downloading) return; // Prevent multiple simultaneous downloads

    setIsDownloadModalOpen(true); // Open modal to show progress
    setDownloading(true);
    setDownloadProgress(0);
    setError(null);

    try {
      // Simulate progress updates for a large download
      const totalSteps = 10;
      for (let i = 1; i <= totalSteps; i++) {
        await new Promise(resolve => setTimeout(resolve, 300)); // Simulate network delay
        setDownloadProgress(Math.round((i / totalSteps) * 100));
      }

      // Actual download call
      await downloadBulkResults();
      alert('Download completed successfully!');
    } catch (err: any) {
      console.error('Download failed:', err);
      setError(err.message || 'Failed to download results. Please try again.');
      alert(`Download failed: ${err.message || 'Unknown error'}`);
    } finally {
      setDownloading(false);
      setDownloadProgress(0);
      setIsDownloadModalOpen(false); // Close modal after completion/error
    }
  }, [downloading]);

  const contextValue = {
    results,
    loading,
    error,
    downloading,
    downloadProgress,
    fetchResults,
    downloadAllResults,
  };

  return (
    <ResultsContext.Provider value={contextValue}>
      {children}
      {/* Download Progress Modal */}
      <Modal
        isOpen={isDownloadModalOpen}
        onClose={() => {
          // Only allow closing if not actively downloading
          if (!downloading) {
            setIsDownloadModalOpen(false);
          }
        }}
        title="Downloading Results"
        aria-label="Download progress"
      >
        <div className="p-4 text-center">
          {downloading ? (
            <>
              <p className="text-lg mb-4">Downloading your bulk results...</p>
              <div className="w-full bg-gray-200 rounded-full h-4 mb-4" role="progressbar" aria-valuenow={downloadProgress} aria-valuemin={0} aria-valuemax={100}>
                <div
                  className="bg-blue-600 h-4 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${downloadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600">{downloadProgress}% Complete</p>
              {error && <p className="text-red-500 mt-2">{error}</p>}
            </>
          ) : (
            <>
              <p className="text-lg mb-4">Download finished!</p>
              <Button onClick={() => setIsDownloadModalOpen(false)} variant="primary">Close</Button>
            </>
          )}
        </div>
      </Modal>
    </ResultsContext.Provider>
  );
};

/**
 * Custom hook to consume the ResultsContext.
 * Throws an error if used outside of a ResultsContextProvider.
 */
export const useResults = () => {
  const context = useContext(ResultsContext);
  if (context === undefined) {
    throw new Error('useResults must be used within a ResultsContextProvider');
  }
  return context;
};