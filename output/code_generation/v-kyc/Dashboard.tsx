import React, { useState, useCallback, useEffect } from 'react';
import { User, Recording } from '../types';
import SearchForm from './SearchForm';
import ResultsTable from './ResultsTable';
import { searchRecordings, downloadBulkRecordings, getRecentRecordings, downloadSingleRecording } from '../services/api';
import Icon from './Icon';
import { useToast } from './ToastProvider';
import SkeletonLoader from './SkeletonLoader';
import ViewRecordingModal from './ViewRecordingModal';

interface DashboardProps {
  user: User;
  onLogout: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ user, onLogout }) => {
  const [results, setResults] = useState<Recording[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start loading on initial mount
  const [isBulkDownloading, setIsBulkDownloading] = useState<boolean>(false);
  const [searchPerformed, setSearchPerformed] = useState<boolean>(false);
  const [viewingRecording, setViewingRecording] = useState<Recording | null>(null);
  const addToast = useToast();

  useEffect(() => {
    const fetchRecent = async () => {
        try {
            const recentResults = await getRecentRecordings();
            setResults(recentResults);
        } catch (e) {
            addToast({ type: 'error', message: 'Failed to load recent recordings.' });
        } finally {
            setIsLoading(false);
        }
    };
    fetchRecent();
  }, [addToast]);

  const handleSearch = useCallback(async (params: any) => {
    setIsLoading(true);
    setSearchPerformed(true);
    setResults([]);
    try {
      const searchResult = await searchRecordings(params);
      setResults(searchResult);
      if (searchResult.length === 0) {
          addToast({ type: 'info', message: "No recordings found for the specified criteria." });
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : 'An error occurred while searching.';
      addToast({ type: 'error', message: errorMessage });
    } finally {
      setIsLoading(false);
    }
  }, [addToast]);

  const handleClearSearch = useCallback(() => {
    setResults([]);
    setSearchPerformed(false);
    // Fetch recent recordings again when clearing to return to the initial state
    setIsLoading(true);
     getRecentRecordings()
      .then(recentResults => setResults(recentResults))
      .catch(() => addToast({ type: 'error', message: 'Failed to load recent recordings.' }))
      .finally(() => setIsLoading(false));

    addToast({ type: 'info', message: 'Search has been cleared.' });
  }, [addToast]);

  const handleView = (recording: Recording) => {
    setViewingRecording(recording);
  };
  
  const handleDownload = useCallback(async (lanId: string) => {
      addToast({ type: 'success', message: `Preparing download for ${lanId}.`});
      try {
        await downloadSingleRecording(lanId);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to initiate download.';
        addToast({ type: 'error', message: errorMessage });
      }
  }, [addToast]);

  const handleBulkDownload = useCallback(async (lanIds: string[]) => {
    if (lanIds.length > 0 && !isBulkDownloading) {
      setIsBulkDownloading(true);
      addToast({ type: 'info', message: `Preparing ${lanIds.length} recordings for download. This may take a moment...`});
      try {
        await downloadBulkRecordings(lanIds);
        // Success is indicated by the browser's download prompt. A toast here might be redundant.
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to initiate bulk download.';
        addToast({ type: 'error', message: errorMessage });
      } finally {
        setIsBulkDownloading(false);
      }
    }
  }, [addToast, isBulkDownloading]);

  const renderContent = () => {
    // Show skeleton only when the page is blank and loading
    if (isLoading && results.length === 0) {
        return <SkeletonLoader />;
    }
    // If we have results, always show the table
    if (results.length > 0) {
        return <ResultsTable 
            results={results}
            onView={handleView}
            onDownload={handleDownload}
            onBulkDownload={handleBulkDownload}
            isBulkDownloading={isBulkDownloading}
        />;
    }
    // This shows "No records found" only after a search has been explicitly performed
    if (searchPerformed && results.length === 0) {
         return (
            <div className="text-center py-16 px-6 bg-white rounded-lg shadow-lg">
              <Icon name="document" className="mx-auto h-16 w-16 text-brand-gray-300" />
              <h3 className="mt-4 text-xl font-semibold text-brand-gray-700">No Recordings Found</h3>
              <p className="mt-2 text-brand-gray-500">Your search did not match any records. Please try different criteria.</p>
            </div>
        );
    }
    // Fallback for when there are no initial records and no search has been performed
    return (
      <div className="mt-8 text-center py-12 px-6 bg-white rounded-lg shadow-lg">
        <Icon name="search" className="mx-auto h-16 w-16 text-brand-gray-300" />
        <h3 className="mt-4 text-xl font-semibold text-brand-gray-700">Welcome to the V-KYC Portal</h3>
        <p className="mt-2 text-brand-gray-500">Use the search form above to find specific recordings.</p>
      </div>
    );
  };

  return (
    <>
      <div className="min-h-screen bg-brand-gray-100">
        <header className="bg-white shadow-md sticky top-0 z-20">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                   <div className="flex items-center space-x-4">
                      <h1 className="text-2xl font-bold text-brand-blue">L&T Finance</h1>
                      <div className="w-px h-8 bg-brand-gray-200"></div>
                      <h2 className="text-xl font-semibold text-brand-gray-800">V-KYC Portal</h2>
                  </div>
                  <div className="flex items-center">
                      <div className="text-right mr-4">
                          <p className="text-sm font-medium text-brand-gray-800">{user.name}</p>
                          <p className="text-xs text-brand-gray-500">{user.role}</p>
                      </div>
                      <button 
                          onClick={onLogout} 
                          className="flex items-center p-2 text-brand-gray-500 rounded-full hover:bg-brand-gray-100 hover:text-brand-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue"
                          aria-label="Logout"
                      >
                         <Icon name="logout" className="w-6 h-6" />
                      </button>
                  </div>
              </div>
          </div>
        </header>

        <main className="container mx-auto p-4 sm:p-6 lg:p-8">
          <SearchForm 
            onSearch={handleSearch} 
            isLoading={isLoading} 
            searchPerformed={searchPerformed || results.length > 0} // Pass true if there are initial results
            onClear={handleClearSearch}
          />
          <div className="mt-8">
            {renderContent()}
          </div>
        </main>
      </div>
      {viewingRecording && (
        <ViewRecordingModal 
          recording={viewingRecording}
          onClose={() => setViewingRecording(null)}
          onDownload={handleDownload}
        />
      )}
    </>
  );
};

export default Dashboard;
