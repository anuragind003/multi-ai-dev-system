import { useContext } from 'react';
import AuthContext from '@context/GlobalContext';
import { AuthContextType } from '@/types';

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within a GlobalProvider');
  }
  return context;
};