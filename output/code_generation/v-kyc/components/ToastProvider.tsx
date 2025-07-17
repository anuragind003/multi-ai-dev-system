
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { ToastMessage, ToastType } from '../types';
import Icon from './Icon';

interface ToastContextType {
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context.addToast;
};

const Toast: React.FC<{ message: ToastMessage; onRemove: (id: number) => void }> = ({ message, onRemove }) => {
    const [isExiting, setIsExiting] = useState(false);

    const handleRemove = useCallback(() => {
        setIsExiting(true);
        setTimeout(() => onRemove(message.id), 300);
    }, [onRemove, message.id]);

    React.useEffect(() => {
        const timer = setTimeout(handleRemove, 5000);
        return () => clearTimeout(timer);
    }, [handleRemove]);
    
    const toastStyles: Record<ToastType, { bg: string, text: string, icon: React.ReactNode }> = {
        success: { 
            bg: 'bg-green-100 border-green-500', 
            text: 'text-green-800', 
            icon: <Icon name="check-circle" className="w-6 h-6 text-green-500" />
        },
        error: { 
            bg: 'bg-red-100 border-red-500', 
            text: 'text-red-800',
            icon: <Icon name="x-circle" className="w-6 h-6 text-red-500" />
        },
        info: { 
            bg: 'bg-blue-100 border-brand-blue', 
            text: 'text-brand-blue',
            icon: <Icon name="info" className="w-6 h-6 text-brand-blue" />
        },
    };

    const style = toastStyles[message.type];

  return (
    <div 
        className={`flex items-start w-full max-w-sm p-4 my-2 text-gray-500 bg-white rounded-lg shadow-xl border-l-4 ${style.bg} transform transition-all duration-300 ${isExiting ? 'opacity-0 translate-x-full' : 'opacity-100 translate-x-0'}`}
        role="alert"
    >
        <div className="flex-shrink-0">{style.icon}</div>
        <div className={`ml-3 text-sm font-medium ${style.text}`}>{message.message}</div>
        <button 
            type="button" 
            className="ml-auto -mx-1.5 -my-1.5 bg-white text-gray-400 hover:text-gray-900 rounded-lg focus:ring-2 focus:ring-gray-300 p-1.5 hover:bg-gray-100 inline-flex h-8 w-8 items-center justify-center" 
            aria-label="Close"
            onClick={handleRemove}
        >
            <span className="sr-only">Close</span>
            <Icon name="x-mark" className="w-5 h-5" />
        </button>
    </div>
  );
};

const ToastContainer: React.FC<{ messages: ToastMessage[]; onRemove: (id: number) => void }> = ({ messages, onRemove }) => (
  <div className="fixed top-4 right-4 z-50">
    {messages.map(message => (
      <Toast key={message.id} message={message} onRemove={onRemove} />
    ))}
  </div>
);

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    setToasts(prevToasts => [...prevToasts, { ...toast, id: Date.now() }]);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts(prevToasts => prevToasts.filter(toast => toast.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <ToastContainer messages={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};
