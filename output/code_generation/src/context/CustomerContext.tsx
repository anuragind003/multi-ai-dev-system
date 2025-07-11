import React, { createContext, useState, useContext, ReactNode } from 'react';
import { Customer, CustomerContextType } from '@utils/types';
import { getCustomerById as apiGetCustomerById } from '@services/api';

const CustomerContext = createContext<CustomerContextType | undefined>(undefined);

export const CustomerProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [customerData, setCustomerData] = useState<Customer | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const searchCustomer = async (lanId: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    setCustomerData(null); // Clear previous data
    try {
      const data = await apiGetCustomerById(lanId);
      setCustomerData(data);
    } catch (err: any) {
      console.error('Failed to fetch customer:', err);
      setError(err.message || 'An unexpected error occurred while fetching customer data.');
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    customerData,
    isLoading,
    error,
    searchCustomer,
  };

  return <CustomerContext.Provider value={value}>{children}</CustomerContext.Provider>;
};

export const useCustomer = (): CustomerContextType => {
  const context = useContext(CustomerContext);
  if (context === undefined) {
    throw new Error('useCustomer must be used within a CustomerProvider');
  }
  return context;
};