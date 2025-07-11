import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { TaskProvider } from '../context/TaskContext';
import TaskList from '../components/TaskList';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('https://api.example.com/tasks', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        { id: '1', title: 'Task 1', description: 'Description 1', status: 'open' },
        { id: '2', title: 'Task 2', description: 'Description 2', status: 'in progress' },
      ])
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('renders task list with tasks', async () => {
  render(
    <TaskProvider>
      <TaskList />
    </TaskProvider>
  );

  await waitFor(() => {
    expect(screen.getByText('Task 1')).toBeInTheDocument();
    expect(screen.getByText('Task 2')).toBeInTheDocument();
  });
});

test('renders loading state', async () => {
  server.use(
    rest.get('https://api.example.com/tasks', (req, res, ctx) => {
      return res(ctx.status(200), ctx.json([]));
    })
  );
  render(
    <TaskProvider>
      <TaskList />
    </TaskProvider>
  );

  expect(screen.getByText('Loading tasks...')).toBeInTheDocument();
});

test('renders error state', async () => {
  server.use(
    rest.get('https://api.example.com/tasks', (req, res, ctx) => {
      return res(ctx.status(500), ctx.json({ message: 'Failed to fetch tasks' }));
    })
  );
  render(
    <TaskProvider>
      <TaskList />
    </TaskProvider>
  );

  await waitFor(() => {
    expect(screen.getByText('Error: Failed to fetch tasks')).toBeInTheDocument();
  });
});