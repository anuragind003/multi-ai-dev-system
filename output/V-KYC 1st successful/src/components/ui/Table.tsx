import React from 'react';

interface Column<T> {
  header: string;
  accessor: keyof T | ((row: T) => any);
  render?: (row: T) => React.ReactNode; // Custom render function for complex cells
  className?: string; // Tailwind classes for the column header and cells
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyAccessor: keyof T | ((row: T) => string | number); // Unique key for each row
  emptyMessage?: string;
  className?: string;
}

export function Table<T>({ data, columns, keyAccessor, emptyMessage = 'No data available.', className = '' }: TableProps<T>) {
  const getKeyValue = (row: T, accessor: keyof T | ((row: T) => any)) => {
    if (typeof accessor === 'function') {
      return accessor(row);
    }
    return row[accessor];
  };

  return (
    <div className={`overflow-x-auto rounded-lg shadow-sm border border-gray-200 ${className}`}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                scope="col"
                className={`px-6 py-3 text-left text-xs font-medium text-text-light uppercase tracking-wider ${column.className || ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-6 py-4 whitespace-nowrap text-sm text-text-light text-center">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr key={typeof keyAccessor === 'function' ? keyAccessor(row) : String(row[keyAccessor]) || rowIndex} className="hover:bg-gray-50">
                {columns.map((column, colIndex) => (
                  <td
                    key={colIndex}
                    className={`px-6 py-4 whitespace-nowrap text-sm text-text ${column.className || ''}`}
                  >
                    {column.render ? column.render(row) : String(getKeyValue(row, column.accessor))}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}