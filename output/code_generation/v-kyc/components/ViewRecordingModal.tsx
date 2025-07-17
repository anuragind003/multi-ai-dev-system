import React, { useEffect } from 'react';
import { Recording } from '../types';
import Icon from './Icon';

interface ViewRecordingModalProps {
  recording: Recording;
  onClose: () => void;
  onDownload: (lanId: string) => void;
}

const DetailItem: React.FC<{ label: string; value: string; className?: string }> = ({ label, value, className = ''}) => (
    <div className={`py-3 ${className}`}>
        <dt className="text-sm font-medium text-brand-gray-500">{label}</dt>
        <dd className="mt-1 text-sm text-brand-gray-900 font-mono">{value}</dd>
    </div>
);


const ViewRecordingModal: React.FC<ViewRecordingModalProps> = ({ recording, onClose, onDownload }) => {

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);


  return (
    <div 
        className="fixed inset-0 bg-brand-gray-800 bg-opacity-75 flex items-center justify-center z-30 p-4 transition-opacity"
        aria-labelledby="modal-title"
        role="dialog"
        aria-modal="true"
        onClick={onClose}
    >
        <div 
            className="bg-white rounded-lg shadow-xl w-full max-w-2xl transform transition-all"
            onClick={e => e.stopPropagation()}
        >
            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4 rounded-t-lg">
                 <div className="flex items-start justify-between">
                    <div>
                        <h3 className="text-lg leading-6 font-bold text-brand-blue" id="modal-title">
                            Recording Details
                        </h3>
                        <p className="mt-1 text-sm text-brand-gray-500 font-mono">{recording.lanId}</p>
                    </div>
                    <button onClick={onClose} className="p-1 rounded-full text-brand-gray-400 hover:bg-brand-gray-100 hover:text-brand-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue">
                        <Icon name="x-mark" className="w-6 h-6" />
                        <span className="sr-only">Close</span>
                    </button>
                </div>
            </div>

            <div className="px-4 sm:px-6 grid grid-cols-1 md:grid-cols-2 gap-x-8">
                {/* Left Side: Video Player */}
                <div className="py-4">
                    <video
                        key={recording.lanId}
                        className="w-full aspect-video bg-black rounded-lg"
                        src={recording.streamUrl}
                        controls
                        autoPlay
                        aria-label={`Video recording for LAN ID ${recording.lanId}`}
                    >
                        Your browser does not support the video tag.
                    </video>
                </div>

                {/* Right Side: Details */}
                <div className="py-4">
                     <dl className="divide-y divide-brand-gray-200">
                        <DetailItem label="File Name" value={recording.fileName} />
                        <DetailItem label="Date" value={recording.date} />
                        <DetailItem label="Time" value={recording.time} />
                        <DetailItem label="Call Duration" value={recording.callDuration} />
                        <DetailItem label="Size" value={recording.size} />
                        <DetailItem label="NFS Upload Time" value={recording.uploadTime} />
                        <div className="py-3">
                            <dt className="text-sm font-medium text-brand-gray-500">Status</dt>
                            <dd className="mt-1">
                               <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                 {recording.status}
                               </span>
                            </dd>
                        </div>
                    </dl>
                </div>
            </div>

            <div className="bg-brand-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse rounded-b-lg">
                <button
                    type="button"
                    onClick={() => onDownload(recording.lanId)}
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-brand-blue text-base font-medium text-white hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue sm:ml-3 sm:w-auto sm:text-sm"
                >
                    <Icon name="download" className="w-5 h-5 mr-2" />
                    Download
                </button>
                <button
                    type="button"
                    onClick={onClose}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-brand-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-brand-gray-700 hover:bg-brand-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-blue sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                    Close
                </button>
            </div>
        </div>
    </div>
  );
};

export default ViewRecordingModal;