import React from 'react';

const ProductSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
      <div className="w-full h-48 bg-gray-200"></div>
      <div className="p-4">
        <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
        <div className="flex flex-wrap gap-1 mb-4">
          <div className="h-6 w-16 bg-gray-200 rounded-full"></div>
          <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
        </div>
        <div className="flex justify-between items-center">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-10 w-28 bg-gray-200 rounded-full"></div>
        </div>
      </div>
    </div>
  );
};

export default ProductSkeleton;