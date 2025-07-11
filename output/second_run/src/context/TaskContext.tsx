import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

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
}

const TaskContext = createContext<TaskContextType>({
  tasks: [],
  loading: false,
  error: null,
});

interface TaskProviderProps {
  children: React.ReactNode;
}

export const TaskProvider: React.FC<TaskProviderProps> = ({ children }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoading(true);
        const response = await axios.get<Task[]>('https://jsonplaceholder.typicode.com/todos'); // Replace with your API endpoint
        const limitedTasks = response.data.slice(0, 10).map(task => ({
          id: String(task.id),
          title: task.title,
          description: "This is a sample description.",
          completed: task.completed,
        }));
        setTasks(limitedTasks);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch tasks');
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  const value = {
    tasks,
    loading,
    error,
  };

  return (
    <TaskContext.Provider value={value}>
      {children}
    </TaskContext.Provider>
  );
};

export const useTaskContext = () => {
  return useContext(TaskContext);
};