import React, { createContext, useState, ReactNode, useContext } from 'react';

interface UATContextType {
  testRuns: any[]; // Replace 'any' with a more specific type for your test run data
  addTestRun: (testRun: any) => void;
  // Add other context values and functions as needed
}

const UATContext = createContext<UATContextType | undefined>(undefined);

interface UATProviderProps {
  children: ReactNode;
}

export const UATProvider = ({ children }: UATProviderProps) => {
  const [testRuns, setTestRuns] = useState<any[]>([]); // Initialize with an empty array

  const addTestRun = (testRun: any) => {
    setTestRuns([...testRuns, testRun]);
  };

  const value: UATContextType = {
    testRuns,
    addTestRun,
    // Add other context values and functions
  };

  return <UATContext.Provider value={value}>{children}</UATContext.Provider>;
};

export const useUATContext = () => {
  const context = useContext(UATContext);
  if (!context) {
    throw new Error('useUATContext must be used within a UATProvider');
  }
  return context;
};