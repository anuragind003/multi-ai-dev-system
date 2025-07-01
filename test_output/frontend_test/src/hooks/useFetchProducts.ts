import { useQuery } from '@tanstack/react-query';
import { Product } from '../types';
import { API_BASE_URL } from '../constants';

const fetchProducts = async (): Promise<Product[]> => {
  const response = await fetch(`${API_BASE_URL}/products`);
  if (!response.ok) {
    throw new Error('Failed to fetch products');
  }
  return await response.json();
};

export const useFetchProducts = () => {
  return useQuery<Product[], Error>({
    queryKey: ['products'],
    queryFn: fetchProducts,
  });
};