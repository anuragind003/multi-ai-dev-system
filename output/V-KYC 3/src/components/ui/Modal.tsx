import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import Button from './Button';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
}

const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);

    // Focus the modal content when it opens for accessibility
    modalRef.current?.focus();

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      tabIndex={-1} // Make the overlay focusable for initial focus
      onClick={(e) => {
        // Close modal if clicking outside the content
        if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
          onClose();
        }
      }}
    >
      <div
        ref={modalRef}
        className={`bg-white rounded-lg shadow-custom-medium max-w-lg w-full p-6 relative outline-none ${className || ''}`}
        tabIndex={0} // Make the modal content focusable
      >
        <div className="flex justify-between items-center mb-4 pb-4 border-b border-gray-200">
          <h2 id="modal-title" className="text-xl font-semibold text-gray-800">
            {title}
          </h2>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
            aria-label="Close modal"
            className="p-1 -mr-2 text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </Button>
        </div>
        <div className="text-gray-700">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default Modal;