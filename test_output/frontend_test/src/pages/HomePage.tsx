import React from 'react';
import { Hero } from '../components/ui/Hero';
import { ProductGrid } from '../components/data-display/ProductGrid';
import { Product } from '../types';

const products: Product[] = [
  { id: 1, name: 'Product 1', description: 'Description 1', price: 19.99, imageUrl: 'https://via.placeholder.com/150' },
  { id: 2, name: 'Product 2', description: 'Description 2', price: 29.99, imageUrl: 'https://via.placeholder.com/150' },
  { id: 3, name: 'Product 3', description: 'Description 3', price: 39.99, imageUrl: 'https://via.placeholder.com/150' },
];

export const HomePage: React.FC = () => {
  return (
    <div>
      <Hero />
      <ProductGrid products={products} />
    </div>
  );
};