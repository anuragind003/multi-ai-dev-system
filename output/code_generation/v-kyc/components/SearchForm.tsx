
import React, { useState, useMemo } from 'react';
import { SearchType } from '../types';
import Icon from './Icon';
import { useToast } from './ToastProvider';

interface SearchFormProps {
  onSearch: (params: any) => void;
  isLoading: boolean;
  searchPerformed: boolean;
  onClear: () => void;
}

const SearchForm: React.FC<SearchFormProps> = ({ onSearch, isLoading, searchPerformed, onClear }) => {
  const [searchType, setSearchType] = useState<SearchType>(SearchType.SINGLE_ID);
  const [lanId, setLanId] = useState('');
  const [date, setDate] = useState('');
  const [month, setMonth] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const addToast = useToast();

  const handleSearchTypeChange = (type: SearchType) => {
    setSearchType(type);
    setLanId('');
    setDate('');
    setMonth('');
    setFile(null);
  }

  const handleFileChange = (selectedFile: File | null) => {
    if (isLoading) return;
    if (selectedFile) {
        const allowedTypes = ['text/csv', 'text/plain', 'application/vnd.ms-excel'];
        if (allowedTypes.includes(selectedFile.type)) {
            setFile(selectedFile);
        } else {
            setFile(null);
            addToast({ type: 'error', message: 'Invalid file type. Please upload a .csv or .txt file.' });
        }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    let params = {};
    if (searchType === SearchType.SINGLE_ID) {
      if (!lanId) {
        addToast({ type: 'error', message: 'Please enter a LAN ID.' });
        return;
      };
      params = { lanId };
    } else if (searchType === SearchType.DATE) {
        if(date) params = { date };
        else if (month) params = { month };
        else {
          addToast({ type: 'error', message: 'Please select a date or month.' });
          return;
        }
    } else if (searchType === SearchType.BULK) {
        if (!file) {
            addToast({ type: 'error', message: 'Please select a file to upload.' });
            return;
        }
        try {
            const text = await file.text();
            const lanIds = text.split(/[\s,]+/).filter(id => id.trim() !== '').map(id => id.trim());
            if (lanIds.length < 2 || lanIds.length > 50) {
                addToast({ type: 'error', message: `File must contain between 2 and 50 LAN IDs. Found: ${lanIds.length}`});
                return;
            }
            params = { lanIds };
        } catch (err) {
            addToast({ type: 'error', message: 'Error reading file.' });
            return;
        }
    }
    onSearch(params);
  };
  
  const searchOptions = useMemo(() => [
    { id: SearchType.SINGLE_ID, label: 'Single LAN ID', icon: 'user' },
    { id: SearchType.DATE, label: 'Date/Month', icon: 'calendar' },
    { id: SearchType.BULK, label: 'Bulk Upload', icon: 'upload' },
  ], []);

  const dragProps = {
    onDragEnter: (e: React.DragEvent) => {
      if (isLoading) return;
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(true);
    },
    onDragLeave: (e: React.DragEvent) => {
      if (isLoading) return;
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
    },
    onDragOver: (e: React.DragEvent) => {
      if (isLoading) return;
      e.preventDefault();
      e.stopPropagation();
    },
    onDrop: (e: React.DragEvent<HTMLDivElement>) => {
      if (isLoading) return;
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files?.[0];
      if (droppedFile) {
        handleFileChange(droppedFile);
      }
    },
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <div className="flex border-b border-brand-gray-200">
        {searchOptions.map(opt => (
          <button 
            key={opt.id}
            onClick={() => handleSearchTypeChange(opt.id)}
            disabled={isLoading}
            className={`flex items-center px-4 py-3 -mb-px text-sm font-medium focus:outline-none transition-colors duration-200 disabled:cursor-not-allowed disabled:text-brand-gray-400 ${
              searchType === opt.id 
              ? 'border-b-2 border-brand-blue text-brand-blue' 
              : 'text-brand-gray-500 hover:text-brand-gray-700'
            }`}
          >
            <Icon name={opt.icon as any} className="w-5 h-5 mr-2" />
            {opt.label}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {searchType === SearchType.SINGLE_ID && (
          <div>
            <label htmlFor="lanId" className="block text-sm font-medium text-brand-gray-700">LAN ID</label>
            <input 
              type="text" 
              id="lanId" 
              value={lanId} 
              onChange={e => setLanId(e.target.value)} 
              placeholder="e.g., LTF12345" 
              className="mt-1 block w-full px-3 py-2 bg-white border border-brand-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-brand-blue focus:border-brand-blue sm:text-sm disabled:bg-brand-gray-100 disabled:cursor-not-allowed text-brand-gray-900" 
              disabled={isLoading} 
              autoComplete="off"
            />
          </div>
        )}
        {searchType === SearchType.DATE && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="date" className="block text-sm font-medium text-brand-gray-700">Specific Date</label>
              <input type="date" id="date" value={date} onChange={e => { setDate(e.target.value); setMonth(''); }} className="mt-1 block w-full px-3 py-2 bg-white border border-brand-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-brand-blue focus:border-brand-blue sm:text-sm disabled:bg-brand-gray-100 disabled:cursor-not-allowed text-brand-gray-900" disabled={isLoading}/>
            </div>
            <div>
              <label htmlFor="month" className="block text-sm font-medium text-brand-gray-700">Specific Month</label>
              <input type="month" id="month" value={month} onChange={e => { setMonth(e.target.value); setDate(''); }} className="mt-1 block w-full px-3 py-2 bg-white border border-brand-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-brand-blue focus:border-brand-blue sm:text-sm disabled:bg-brand-gray-100 disabled:cursor-not-allowed text-brand-gray-900" disabled={isLoading}/>
            </div>
          </div>
        )}
        {searchType === SearchType.BULK && (
          <div {...dragProps}>
            <label htmlFor="file-upload" className="block text-sm font-medium text-brand-gray-700">Upload LAN ID File</label>
            <div className={`mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-brand-gray-300 border-dashed rounded-md transition-colors ${isDragging ? 'bg-brand-blue/10 border-brand-blue' : ''} ${isLoading ? 'bg-brand-gray-100 cursor-not-allowed' : ''}`}>
                <div className="space-y-1 text-center">
                    <Icon name="document" className="mx-auto h-12 w-12 text-brand-gray-400" />
                    <div className="flex text-sm text-brand-gray-600">
                        <label htmlFor="file-upload" className={`relative bg-white rounded-md font-medium text-brand-blue hover:text-brand-blue focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-brand-blue ${isLoading ? 'cursor-not-allowed text-brand-gray-500' : 'cursor-pointer'}`}>
                            <span>Upload a file</span>
                            <input id="file-upload" name="file-upload" type="file" className="sr-only" onChange={e => handleFileChange(e.target.files?.[0] ?? null)} accept=".csv,.txt" disabled={isLoading} />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                    </div>
                    <p className="text-xs text-brand-gray-500">CSV or TXT, 2-50 LAN IDs</p>
                </div>
            </div>
            {file && <p className="mt-2 text-sm text-green-700 bg-green-100 p-2 rounded-md">File selected: <strong>{file.name}</strong></p>}
          </div>
        )}
        <div className="pt-2 flex items-center justify-end gap-x-3">
            {searchPerformed && !isLoading && (
                <button 
                    type="button" 
                    onClick={() => {
                        onClear();
                        // Also reset form state
                        setLanId('');
                        setDate('');
                        setMonth('');
                        setFile(null);
                    }}
                    className="inline-flex items-center justify-center px-4 py-2 border border-brand-gray-300 text-sm font-medium rounded-md shadow-sm text-brand-gray-700 bg-white hover:bg-brand-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue transition-all"
                >
                    <Icon name="x-mark" className="w-5 h-5 mr-2 text-brand-gray-500" />
                    Clear
                </button>
            )}
            <button type="submit" disabled={isLoading} className="inline-flex items-center justify-center px-6 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-brand-blue hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue disabled:bg-brand-gray-400 disabled:cursor-not-allowed transition-all">
                {isLoading ? (
                    <>
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Searching...
                    </>
                ) : (
                   <>
                    <Icon name="search" className="w-5 h-5 mr-2" />
                    Search
                   </>
                )}
            </button>
        </div>
      </form>
    </div>
  );
};

export default SearchForm;
