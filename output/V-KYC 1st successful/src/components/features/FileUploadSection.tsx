import React, { useState, useCallback, useRef } from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { FileUploadFormInputs, fileUploadSchema, BulkUploadResponse, FileUploadResult, formatBytes } from '@/types';
import { Button, Card, Input, Spinner, Modal } from '@/components/ui';
import { fileUploadService } from '@/services/api';
import { useAppContext } from '@/context/AppProviders';

export const FileUploadSection: React.FC = () => {
  const { addAlert, setLoading } = useAppContext();
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<BulkUploadResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
    setError,
    clearErrors,
  } = useForm<FileUploadFormInputs>({
    resolver: zodResolver(fileUploadSchema),
  });

  const selectedFiles = watch('files');

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      clearErrors('files'); // Clear previous file errors on new selection
    }
  };

  const onSubmit: SubmitHandler<FileUploadFormInputs> = useCallback(async (data) => {
    setIsUploading(true);
    setUploadProgress(0);
    setUploadResults(null);
    setLoading(true);

    try {
      const filesArray = Array.from(data.files);

      const response = await fileUploadService.uploadBulkFiles(filesArray, (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percentCompleted);
      });

      setUploadResults(response.data);
      setIsModalOpen(true); // Open modal to show results
      addAlert('Files uploaded successfully!', 'success');
      reset(); // Clear form after successful upload
      if (fileInputRef.current) {
        fileInputRef.current.value = ''; // Manually clear file input
      }
    } catch (error: any) {
      console.error('File upload failed:', error);
      const errorMessage = error.response?.data?.message || 'An unexpected error occurred during upload.';
      addAlert(errorMessage, 'error');
      setError('files', { type: 'manual', message: errorMessage });
    } finally {
      setIsUploading(false);
      setLoading(false);
      setUploadProgress(0); // Reset progress
    }
  }, [addAlert, reset, setError, setLoading]);

  const renderFileUploadProgress = () => {
    if (!isUploading) return null;

    return (
      <div className="mt-4">
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">Uploading...</span>
          <span className="text-sm font-medium text-primary">{uploadProgress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-primary h-2.5 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${uploadProgress}%` }}
          ></div>
        </div>
      </div>
    );
  };

  const renderSelectedFiles = () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      return <p className="text-sm text-gray-500 mt-2">No files selected.</p>;
    }
    return (
      <div className="mt-2 text-sm text-gray-700">
        <p className="font-medium">Selected Files:</p>
        <ul className="list-disc list-inside">
          {Array.from(selectedFiles).map((file, index) => (
            <li key={index} className="flex justify-between items-center">
              <span>{file.name} ({formatBytes(file.size)})</span>
              {errors.files?.message && errors.files.type === 'refine' && (
                <span className="text-danger text-xs ml-2">{errors.files.message}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderModalContent = () => {
    if (!uploadResults) return null;

    return (
      <div>
        <p className="mb-2">Total Files: <span className="font-semibold">{uploadResults.totalFiles}</span></p>
        <p className="mb-2">Successful Uploads: <span className="font-semibold text-success">{uploadResults.successfulUploads}</span></p>
        <p className="mb-4">Failed Uploads: <span className="font-semibold text-danger">{uploadResults.failedUploads}</span></p>

        {uploadResults.results.length > 0 && (
          <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md p-3">
            <h4 className="font-semibold mb-2">Detailed Results:</h4>
            <ul className="space-y-2">
              {uploadResults.results.map((result: FileUploadResult, index: number) => (
                <li key={index} className={`p-2 rounded-md ${result.status === 'SUCCESS' ? 'bg-success/5 text-success' : 'bg-danger/5 text-danger'}`}>
                  <span className="font-medium">{result.fileName}:</span> {result.message}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <Card title="Bulk File Upload" className="max-w-2xl mx-auto">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          type="file"
          label="Select Files (CSV/Excel, max 5MB each)"
          multiple
          accept=".csv, application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          {...register('files', { onChange: onFileChange })}
          error={errors.files?.message}
          ref={fileInputRef}
          aria-describedby={errors.files?.message ? 'file-upload-error' : undefined}
        />
        {errors.files && <p id="file-upload-error" className="mt-1 text-sm text-danger" role="alert">{errors.files.message}</p>}

        {renderSelectedFiles()}
        {renderFileUploadProgress()}

        <Button
          type="submit"
          isLoading={isUploading}
          disabled={isUploading || !selectedFiles || selectedFiles.length === 0}
          className="w-full"
        >
          {isUploading ? 'Uploading...' : 'Upload Files'}
        </Button>
      </form>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Upload Results"
        footer={
          <Button onClick={() => setIsModalOpen(false)} variant="secondary">
            Close
          </Button>
        }
      >
        {renderModalContent()}
      </Modal>
    </Card>
  );
};