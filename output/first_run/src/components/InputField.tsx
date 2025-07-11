import React from 'react';

interface InputFieldProps {
  label: string;
  type: string;
  id: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
}

function InputField({ label, type, id, name, value, onChange, error }: InputFieldProps) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="block text-gray-700 text-sm font-bold mb-2">
        {label}
      </label>
      <input
        className={`shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline ${
          error ? 'border-red-500' : ''
        }`}
        type={type}
        id={id}
        name={name}
        value={value}
        onChange={onChange}
        aria-describedby={`${id}-error`}
      />
      {error && (
        <p className="text-red-500 text-xs italic mt-1" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

export default InputField;