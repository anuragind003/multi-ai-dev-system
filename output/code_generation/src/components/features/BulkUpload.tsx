import React, { useState, useRef, useCallback, useContext } from 'react';
import { Input, Button, Modal, LoadingSpinner } from '@components/ui';
import { useFormValidation } from '@hooks';
import { bulkUploadSchema, formatBytes } from '@utils';
import { uploadFile, UploadResult } from '@services/api';
import { GlobalContext } from '@context/GlobalContext';

// --- Types ---
interface BulkUploadFormState {
  file: File | null;
}

// --- Component ---
export const BulkUpload: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { setIsLoading, handleError, showNotification } = useContext(GlobalContext)!;

  const {
    formData,
    errors,
    handleFileChange,
    setFormData,
    validateForm,
    resetForm,
  } = useFormValidation<BulkUploadFormState>(
    { file: null },
    bulkUploadSchema
  );

  const [uploadSummary, setUploadSummary] = useState<UploadResult | null>(null);
  const [isSummaryModalOpen, setIsSummaryModalOpen] = useState(false);

  const handleFileDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setFormData((prev) => ({ ...prev, file: files[0] }));
    }
  }, [setFormData]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleRemoveFile = useCallback(() => {
    setFormData((prev) => ({ ...prev, file: null }));
    if (fileInputRef.current) {
      fileInputRef.current.value = ''; // Clear the file input
    }
  }, [setFormData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      showNotification('Please correct the errors in the form.', 'error');
      return;
    }

    if (!formData.file) {
      showNotification('No file selected for upload.', 'warning');
      return;
    }

    setIsLoading(true);
    try {
      const result = await uploadFile(formData.file);
      setUploadSummary(result);
      setIsSummaryModalOpen(true);
      showNotification(`File "${result.fileName}" uploaded successfully!`, 'success');
      resetForm(); // Clear form after successful upload
    } catch (error) {
      handleError(error, 'File upload failed');
      setUploadSummary(null); // Clear any previous summary
    } finally {
      setIsLoading(false);
    }
  };

  const closeSummaryModal = useCallback(() => {
    setIsSummaryModalOpen(false);
    setUploadSummary(null);
  }, []);

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Input Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors duration-200 ${
            errors.file ? 'border-danger bg-red-50' : 'border-gray-300 hover:border-primary hover:bg-gray-50'
          }`}
          onDrop={handleFileDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Drag and drop or click to select file"
        >
          <input
            type="file"
            ref={fileInputRef}
            name="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
            aria-describedby={errors.file ? "file-error" : undefined}
            aria-invalid={!!errors.file}
          />
          {formData.file ? (
            <div className="flex flex-col items-center">
              <p className="text-lg font-medium text-gray-800">Selected File:</p>
              <p className="text-primary font-semibold text-xl mt-1">{formData.file.name}</p>
              <p className="text-gray-600 text-sm mt-1">{formatBytes(formData.file.size)}</p>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); handleRemoveFile(); }}
                className="mt-3 text-danger hover:bg-red-100"
                aria-label="Remove selected file"
              >
                Remove File
              </Button>
            </div>
          ) : (
            <div className="text-gray-600">
              <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="mt-2 text-sm">
                <span className="font-semibold text-primary">Drag and drop</span> or{' '}
                <span className="font-semibold text-primary">click to upload</span>
              </p>
              <p className="mt-1 text-xs text-gray-500">CSV files only (max 10MB)</p>
            </div>
          )}
        </div>
        {errors.file && (
          <p id="file-error" className="mt-2 text-sm text-danger" role="alert">
            {errors.file}
          </p>
        )}

        <Button
          type="submit"
          variant="primary"
          className="w-full py-3"
          isLoading={setIsLoading}
          disabled={!formData.file || setIsLoading}
          aria-label={setIsLoading ? "Uploading..." : "Upload File"}
        >
          {setIsLoading ? (
            <>
              <LoadingSpinner size="sm" color="text-white" /> Uploading...
            </>
          ) : (
            'Upload File'
          )}
        </Button>
      </form>

      {/* Upload Summary Modal */}
      <Modal
        isOpen={isSummaryModalOpen}
        onClose={closeSummaryModal}
        title="Upload Summary"
        size="md"
        footer={
          <Button onClick={closeSummaryModal} variant="primary">
            Close
          </Button>
        }
      >
        {uploadSummary ? (
          <div className="space-y-4 text-gray-700">
            <p><strong>File Name:</strong> {uploadSummary.fileName}</p>
            <p>
              <strong>Status:</strong>{' '}
              <span className={`font-semibold ${
                uploadSummary.status === 'success' ? 'text-secondary' :
                uploadSummary.status === 'partial' ? 'text-warning' : 'text-danger'
              }`}>
                {uploadSummary.status.toUpperCase()}
              </span>
            </p>
            <p><strong>Processed Records:</strong> {uploadSummary.processedRecords}</p>
            <p><strong>Failed Records:</strong> {uploadSummary.failedRecords}</p>

            {uploadSummary.errors && uploadSummary.errors.length > 0 && (
              <div>
                <h4 className="font-semibold text-danger mt-4 mb-2">Errors:</h4>
                <ul className="list-disc list-inside text-sm text-danger bg-red-50 p-3 rounded-md max-h-40 overflow-y-auto">
                  {uploadSummary.errors.map((err, index) => (
                    <li key={index}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {uploadSummary.warnings && uploadSummary.warnings.length > 0 && (
              <div>
                <h4 className="font-semibold text-warning mt-4 mb-2">Warnings:</h4>
                <ul className="list-disc list-inside text-sm text-warning bg-yellow-50 p-3 rounded-md max-h-40 overflow-y-auto">
                  {uploadSummary.warnings.map((warn, index) => (
                    <li key={index}>{warn}</li>
                  ))}
                </ul>
              </div>
            )}

            {uploadSummary.status === 'success' && (
              <p className="text-secondary font-medium mt-4">All records processed successfully!</p>
            )}
          </div>
        ) : (
          <p className="text-gray-600">No upload summary available.</p>
        )}
      </Modal>
    </div>
  );
};