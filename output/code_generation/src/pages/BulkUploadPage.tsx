import React, { useState, useRef } from 'react';
import { Card, Button, Input, Modal, LoadingSpinner, ErrorMessage } from '@/components/ui/CoreUI';
import { useFormAndAuth } from '@/hooks/useFormAndAuth';
import { uploadFile } from '@/services/api'; // Combined API service
import { formatBytes, validateFile } from '@/utils'; // Combined utilities

const BulkUploadPage: React.FC = () => {
  const { formData, errors, handleChange, validateForm, resetForm } = useFormAndAuth({
    file: null as File | null,
    description: '',
  });
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files ? e.target.files[0] : null;
    handleChange('file', file);
    setUploadError(null); // Clear previous errors on new file selection
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError(null);
    setUploadSuccess(false);

    const formErrors = validateForm({
      file: (value: File | null) => validateFile(value, ['csv', 'xlsx', 'json'], 10 * 1024 * 1024), // 10MB limit
    });

    if (Object.keys(formErrors).length > 0) {
      return;
    }

    if (!formData.file) {
      setUploadError('Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const response = await uploadFile(formData.file, formData.description, (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });
      console.log('Upload successful:', response);
      setUploadSuccess(true);
      setIsModalOpen(true);
      resetForm();
      if (fileInputRef.current) {
        fileInputRef.current.value = ''; // Clear file input
      }
    } catch (error: any) {
      console.error('Upload failed:', error);
      setUploadError(error.message || 'An unexpected error occurred during upload.');
      setIsModalOpen(true);
    } finally {
      setIsUploading(false);
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setUploadError(null);
    setUploadSuccess(false);
  };

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold text-text mb-8">Bulk File Upload</h1>

      <Card title="Upload New File" className="max-w-2xl mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Select File"
            type="file"
            name="file"
            onChange={handleFileChange}
            error={errors.file}
            accept=".csv,.xlsx,.json"
            ref={fileInputRef}
            aria-describedby="file-upload-info"
          />
          <p id="file-upload-info" className="text-sm text-text-light -mt-4">
            Supported formats: CSV, XLSX, JSON. Max size: 10MB.
          </p>

          {formData.file && (
            <div className="mt-4 p-3 bg-gray-50 rounded-md border border-gray-200">
              <p className="text-sm font-medium text-text">Selected File:</p>
              <p className="text-sm text-text-light">{formData.file.name} ({formatBytes(formData.file.size)})</p>
            </div>
          )}

          <Input
            label="Description (Optional)"
            type="text"
            name="description"
            value={formData.description || ''}
            onChange={(e) => handleChange('description', e.target.value)}
            placeholder="e.g., Q4 Sales Data, User Migration List"
            maxLength={255}
          />

          {isUploading && (
            <div className="mt-4">
              <div className="text-sm font-medium text-text-light mb-2">Uploading: {uploadProgress}%</div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-primary h-2.5 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                  role="progressbar"
                  aria-valuenow={uploadProgress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                ></div>
              </div>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isUploading}
            disabled={isUploading || !formData.file}
            className="w-full"
            aria-label="Upload file"
          >
            {isUploading ? 'Uploading...' : 'Upload File'}
          </Button>
        </form>
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={uploadSuccess ? 'Upload Successful!' : 'Upload Failed'}
        footer={
          <Button onClick={closeModal} variant="primary">
            Close
          </Button>
        }
      >
        {uploadSuccess ? (
          <div className="text-center text-secondary-dark">
            <svg className="mx-auto h-16 w-16 text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-4 text-lg font-medium">Your file has been successfully uploaded and is being processed.</p>
            <p className="text-sm text-text-light mt-2">You will be notified once the processing is complete.</p>
          </div>
        ) : (
          <div className="text-center text-danger">
            <svg className="mx-auto h-16 w-16 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-4 text-lg font-medium">Upload failed. Please try again.</p>
            {uploadError && <ErrorMessage message={uploadError} className="mt-4" />}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default BulkUploadPage;