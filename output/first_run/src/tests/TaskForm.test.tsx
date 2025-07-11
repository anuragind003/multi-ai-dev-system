import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import TaskForm from '../components/TaskForm';
import { TaskProvider } from '../context/TaskContext';

describe('TaskForm Component', () => {
  it('renders the form with input fields and a submit button', () => {
    render(
      <TaskProvider>
        <TaskForm />
      </TaskProvider>
    );

    expect(screen.getByLabelText('Title')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Due Date')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add task/i })).toBeInTheDocument();
  });

  it('calls addTask with the correct values when the form is submitted', () => {
    const addTaskMock = jest.fn();
    jest.mock('../context/TaskContext', () => ({
      useTaskContext: () => ({
        addTask: addTaskMock,
      }),
    }));

    render(
      <TaskProvider>
        <TaskForm />
      </TaskProvider>
    );

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Test Title' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Test Description' } });
    fireEvent.change(screen.getByLabelText('Due Date'), { target: { value: '2024-12-31' } });
    fireEvent.click(screen.getByRole('button', { name: /add task/i }));

    expect(addTaskMock).toHaveBeenCalledWith({
      title: 'Test Title',
      description: 'Test Description',
      dueDate: '2024-12-31',
    });
  });

  it('displays error messages when required fields are missing', () => {
    render(
      <TaskProvider>
        <TaskForm />
      </TaskProvider>
    );

    fireEvent.click(screen.getByRole('button', { name: /add task/i }));

    expect(screen.getByText('Title is required')).toBeInTheDocument();
    expect(screen.getByText('Description is required')).toBeInTheDocument();
    expect(screen.getByText('Due date is required')).toBeInTheDocument();
  });
});