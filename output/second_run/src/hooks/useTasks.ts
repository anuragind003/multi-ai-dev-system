import { useState, useEffect, useCallback } from 'react';
import { API } from '../services/api';
import { Task } from '../types';

export const useTasks = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await API.get<Task[]>('/tasks');
      setTasks(response.data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createTask = async (taskData: { title: string; description: string }) => {
    try {
      await API.post('/tasks', taskData);
    } catch (err: any) {
      setError(err);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  return { tasks, loading, error, fetchTasks, createTask };
};