import { useState, useCallback } from 'react';
import { api } from '../services/api';

interface UseDownloadOptions {
  filename?: string;
  contentType?: string;
}

export const useDownload = (url: string, options?: UseDownloadOptions) => {
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const defaultFilename = options?.filename || 'downloaded_file';
  const defaultContentType = options?.contentType || 'application/octet-stream';

  const downloadFile = useCallback(async () => {
    setIsDownloading(true);
    setDownloadError(null);
    try {
      const response = await api.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: response.headers['content-type'] || defaultContentType });

      // Create a link element
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = defaultFilename + (response.headers['content-type'] === 'text/csv' ? '.csv' : '.bin'); // Add .csv extension if content type is csv

      document.body.appendChild(link); // Append to body to make it clickable
      link.click(); // Programmatically click the link to trigger download
      document.body.removeChild(link); // Clean up the link element
      URL.revokeObjectURL(link.href); // Release the object URL

    } catch (err) {
      console.error('Download failed:', err);
      setDownloadError('Failed to download file. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  }, [url, defaultFilename, defaultContentType]);

  return { downloadFile, isDownloading, downloadError };
};