import React, { useEffect, useRef } from 'react';

export type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  type?: ToastType;
  onClose: () => void;
  duration?: number;
}

const typeStyles: Record<ToastType, string> = {
  success: 'bg-green-600 text-white',
  error: 'bg-red-600 text-white',
  info: 'bg-brand-green-dark text-white',
};

const Toast: React.FC<ToastProps> = ({ message, type = 'info', onClose, duration = 3000 }) => {
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    closeBtnRef.current?.focus();
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  // Trap focus inside the toast
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        closeBtnRef.current?.focus();
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 px-6 py-3 rounded shadow-lg flex items-center gap-2 ${typeStyles[type]}`}
      role="alert"
      aria-live="assertive"
      tabIndex={0}
    >
      <span>{message}</span>
      <button
        ref={closeBtnRef}
        onClick={onClose}
        className="ml-4 text-white font-bold focus:outline-none"
        aria-label="Close notification"
      >
        ✕
      </button>
    </div>
  );
};

export default Toast; 