import React from 'react';

const SkeletonRow = () => (
    <tr className="animate-pulse">
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-24"></div></td>
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-20"></div></td>
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-20"></div></td>
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-16"></div></td>
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-24"></div></td>
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-20"></div></td>
        <td className="px-6 py-4"><div className="h-4 bg-brand-gray-200 rounded w-16"></div></td>
        <td className="px-6 py-4 text-right">
            <div className="flex justify-end space-x-4">
                <div className="h-6 bg-brand-gray-200 rounded w-20"></div>
                <div className="h-6 bg-brand-gray-200 rounded w-24"></div>
            </div>
        </td>
    </tr>
);

const SkeletonLoader: React.FC = () => {
    
    const headers = ['LAN ID', 'Date', 'Time', 'Duration', 'Status', 'Upload Time', 'Size'];

    return (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="p-4 sm:p-6 border-b border-brand-gray-200 flex justify-between items-center animate-pulse">
                <div className="h-6 bg-brand-gray-200 rounded w-1/3"></div>
                <div className="h-10 bg-brand-gray-200 rounded w-36"></div>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-brand-gray-200">
                    <thead className="bg-brand-gray-50">
                        <tr>
                            {headers.map(h => (
                                <th key={h} scope="col" className="px-6 py-3 text-left text-xs font-medium text-brand-gray-500 uppercase tracking-wider">{h}</th>
                            ))}
                            <th scope="col" className="relative px-6 py-3">
                                <span className="sr-only">Actions</span>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-brand-gray-200">
                        {Array.from({ length: 10 }).map((_, i) => (
                            <SkeletonRow key={i} />
                        ))}
                    </tbody>
                </table>
            </div>

             <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-brand-gray-200 sm:px-6 rounded-b-lg animate-pulse">
                <div className="h-4 bg-brand-gray-200 rounded w-1/4"></div>
                <div className="flex space-x-2">
                    <div className="h-8 w-20 bg-brand-gray-200 rounded"></div>
                    <div className="h-8 w-20 bg-brand-gray-200 rounded"></div>
                </div>
            </div>
        </div>
    );
};

export default SkeletonLoader;
