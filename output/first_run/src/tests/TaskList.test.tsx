import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TaskList from '../pages/TaskList';
import { TaskProvider } from '../context/TaskContext';

// Mock the useTasks hook to control the context values for testing
jest.mock('../context/TaskContext', () => ({
  useTasks: () => ({
    tasks: [
      { id: '1', title: 'Test Task', description: 'Test Description', completed: false },
      { id: '2', title: 'Completed Task', description: 'Completed Description', completed: true },
    ],
    addTask: jest.fn(),
    toggleTaskCompletion: jest.fn(),
    deleteTask: jest.fn(),
  }),
  TaskProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('TaskList Component', () => {
  it('renders the task list', () => {
    render(
      <TaskProvider>
        <TaskList />
      </TaskProvider>,
    );
    expect(screen.getByText('Test Task')).toBeInTheDocument();
    expect(screen.getByText('Completed Task')).toBeInTheDocument();
  });

  it('renders the "No tasks yet" message when there are no tasks', () => {
    // Mock useTasks to return an empty task list
    jest.mock('../context/TaskContext', () => ({
      useTasks: () => ({
        tasks: [],
        addTask: jest.fn(),
        toggleTaskCompletion: jest.fn(),
        deleteTask: jest.fn(),
      }),
      TaskProvider: ({ children }: { children: React.ReactNode }) => children,
    }));

    render(
      <TaskProvider>
        <TaskList />
      </TaskProvider>,
    );
    expect(screen.getByText('No tasks yet. Add one!')).toBeInTheDocument();
  });

  // Add more tests for interactions (e.g., clicking buttons) if needed
});