import React from 'react';
import { ProductGrid } from '../components/data-display/ProductGrid';
import { Product } from '../types';

const products: Product[] = [
  { id: 1, name: 'Product 1', description: 'Description 1', price: 19.99, imageUrl: 'https://via.placeholder.com/150' },
  { id: 2, name: 'Product 2', description: 'Description 2', price: 29.99, imageUrl: 'https://via.placeholder.com/150' },
  { id: 3, name: 'Product 3', description: 'Description 3', price: 39.99, imageUrl: 'https://via.placeholder.com/150' },
];

export const ProductsPage: React.FC = () => {
  return (
    <div>
      <ProductGrid products={products} />
    </div>
  );
};