import React, { createContext, useState, useContext, useEffect } from 'react';
import { API_URL } from '../config';
import { useAuth } from '../hooks/useAuth';

interface Task {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

interface TaskContextType {
  tasks: Task[];
  loading: boolean;
  error: string | null;
  addTask: (task: Omit<Task, 'id'>) => Promise<void>;
  // Add other task-related actions (e.g., updateTask, deleteTask)
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export const useTask = () => {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTask must be used within a TaskProvider');
  }
  return context;
};

interface TaskProviderProps {
  children: React.ReactNode;
}

export const TaskProvider: React.FC<TaskProviderProps> = ({ children }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    const fetchTasks = async () => {
      if (!user) {
        setLoading(false);
        return;
      }
      try {
        const response = await fetch(`${API_URL}/tasks`, {
          headers: {
            Authorization: `Bearer ${user.id}`, // Assuming user.id is a token
          },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch tasks');
        }
        const data = await response.json();
        setTasks(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, [user]);

  const addTask = async (newTask: Omit<Task, 'id'>) => {
    if (!user) {
      setError('Not authenticated');
      return;
    }
    try {
      const response = await fetch(`${API_URL}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.id}`,
        },
        body: JSON.stringify(newTask),
      });

      if (!response.ok) {
        throw new Error('Failed to create task');
      }

      const createdTask = await response.json();
      setTasks([...tasks, createdTask]);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const value: TaskContextType = {
    tasks,
    loading,
    error,
    addTask,
  };

  return (
    <TaskContext.Provider value={value}>{children}</TaskContext.Provider>
  );
};