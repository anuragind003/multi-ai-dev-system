import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAppContext } from '../../context/AppContext';
import { Button, Input, LoadingSpinner, ErrorMessage } from '../ui';

// Define schema for file upload
const fileSchema = z.object({
  file: z.instanceof(FileList)
    .refine(files => files.length > 0, 'File is required.')
    .refine(files => files[0]?.size <= 5 * 1024 * 1024, 'Max file size is 5MB.') // 5MB limit
    .refine(files => ['text/csv', 'application/vnd.ms-excel'].includes(files[0]?.type), 'Only CSV files are allowed.'),
});

type FileFormValues = z.infer<typeof fileSchema>;

const FileUploadForm: React.FC = () => {
  const { initiateUpload, uploadStatus, uploadProgress, currentUploadError, clearUploadState } = useAppContext();
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
    setError,
    clearErrors,
  } = useForm<FileFormValues>({
    resolver: zodResolver(fileSchema),
  });

  const onSubmit = async (data: FileFormValues) => {
    clearErrors();
    setCurrentUploadError(null); // Clear previous API errors
    try {
      await initiateUpload(data.file[0]);
      reset(); // Clear form after successful upload initiation
      setSelectedFileName(null);
    } catch (error: any) {
      // Error is already handled by AppContext and set to currentUploadError
      // We can optionally set a form-specific error here if needed
      setError('file', { type: 'manual', message: error.message || 'Upload failed.' });
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFileName(file.name);
      clearErrors('file'); // Clear file error when a new file is selected
    } else {
      setSelectedFileName(null);
    }
  };

  const isUploading = uploadStatus === 'uploading' || uploadStatus === 'processing';

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-semibold text-gray-800 mb-6">Upload New Data</h2>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div>
          <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700 mb-2">
            Select CSV File
          </label>
          <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
            <div className="space-y-1 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
                aria-hidden="true"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <div className="flex text-sm text-gray-600">
                <label
                  htmlFor="file-upload"
                  className="relative cursor-pointer bg-white rounded-md font-medium text-primary hover:text-secondary focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-primary"
                >
                  <span>Upload a file</span>
                  <input
                    id="file-upload"
                    type="file"
                    className="sr-only"
                    {...register('file', { onChange: handleFileChange })}
                    accept=".csv, application/vnd.ms-excel"
                    aria-describedby={errors.file ? 'file-error' : undefined}
                  />
                </label>
                <p className="pl-1">or drag and drop</p>
              </div>
              <p className="text-xs text-gray-500">CSV up to 5MB</p>
              {selectedFileName && (
                <p className="text-sm text-gray-700 mt-2">Selected: <span className="font-medium">{selectedFileName}</span></p>
              )}
            </div>
          </div>
          {errors.file && (
            <p id="file-error" className="mt-2 text-sm text-danger" role="alert">
              {errors.file.message}
            </p>
          )}
        </div>

        {isUploading && (
          <div className="mt-4">
            <div className="text-sm font-medium text-gray-700 mb-1">
              {uploadStatus === 'uploading' ? `Uploading: ${uploadProgress}%` : 'Processing...'}
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-primary h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <LoadingSpinner />
          </div>
        )}

        {currentUploadError && (
          <ErrorMessage message={currentUploadError} className="mt-4" />
        )}

        <div className="flex justify-end space-x-3">
          <Button
            type="button"
            variant="outline"
            onClick={clearUploadState}
            disabled={isUploading}
          >
            Clear
          </Button>
          <Button
            type="submit"
            disabled={isSubmitting || isUploading}
            aria-busy={isSubmitting || isUploading}
          >
            {isSubmitting ? 'Submitting...' : 'Upload File'}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default FileUploadForm;