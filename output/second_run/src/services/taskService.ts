import { apiService } from './apiService';
import { Task } from '../types';

const TASKS_API_URL = '/tasks'; // Example endpoint

export const getTasks = async (): Promise<Task[]> => {
  try {
    const response = await apiService(TASKS_API_URL, { method: 'GET' });
    return response as Task[];
  } catch (error: any) {
    throw new Error(error.message || 'Failed to fetch tasks');
  }
};