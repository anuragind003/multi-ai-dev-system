import { rest } from 'msw';
import { Product } from '../../types';

const products: Product[] = [
  { id: 1, name: 'Product 1', description: 'Description 1', price: 19.99, imageUrl: 'https://via.placeholder.com/150' },
  { id: 2, name: 'Product 2', description: 'Description 2', price: 29.99, imageUrl: 'https://via.placeholder.com/150' },
];

export const handlers = [
  rest.get('/api/products', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json(products));
  }),
];