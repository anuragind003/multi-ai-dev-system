import { render, screen } from '@testing-library/react';
import HomePage from '../pages/HomePage';
import { server } from '../test/mocks/server';
import { rest } from 'msw';

test('renders home page', async () => {
  render(<HomePage />);
  expect(await screen.findByText('Home Page')).toBeInTheDocument();
});

test('renders users', async () => {
  server.use(
    rest.get('/api/users', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json([
          { id: 1, name: 'John Doe' },
          { id: 2, name: 'Jane Doe' }
        ])
      );
    })
  );
  render(<HomePage />);
  expect(await screen.findByText('John Doe')).toBeInTheDocument();
  expect(await screen.findByText('Jane Doe')).toBeInTheDocument();
});

test('renders loading state', async () => {
  server.use(
    rest.get('/api/users', (req, res, ctx) => {
      return res(ctx.delay(1000), ctx.status(200), ctx.json([]));
    })
  );
  render(<HomePage />);
  expect(screen.getByText('Loading...')).toBeInTheDocument();
});

test('renders error state', async () => {
  server.use(
    rest.get('/api/users', (req, res, ctx) => {
      return res(ctx.status(500));
    })
  );
  render(<HomePage />);
  expect(await screen.findByText(/Error/i)).toBeInTheDocument();
});