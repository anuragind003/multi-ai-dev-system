import React, { createContext, useState, ReactNode, useContext } from 'react';

interface Task {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

interface TaskContextType {
  tasks: Task[];
  addTask: (task: Omit<Task, 'id'>) => void;
  toggleTaskCompletion: (id: string) => void;
  deleteTask: (id: string) => void;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

interface TaskProviderProps {
  children: ReactNode;
}

export const TaskProvider: React.FC<TaskProviderProps> = ({ children }) => {
  const [tasks, setTasks] = useState<Task[]>([
    { id: '1', title: 'Grocery Shopping', description: 'Buy groceries for the week', completed: false },
    { id: '2', title: 'Book Doctor Appointment', description: 'Schedule a checkup', completed: true },
  ]);

  const addTask = (newTask: Omit<Task, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 15); // Simple ID generation
    setTasks([...tasks, { ...newTask, id }]);
  };

  const toggleTaskCompletion = (id: string) => {
    setTasks(
      tasks.map((task) =>
        task.id === id ? { ...task, completed: !task.completed } : task,
      ),
    );
  };

  const deleteTask = (id: string) => {
    setTasks(tasks.filter((task) => task.id !== id));
  };

  const value: TaskContextType = {
    tasks,
    addTask,
    toggleTaskCompletion,
    deleteTask,
  };

  return <TaskContext.Provider value={value}>{children}</TaskContext.Provider>;
};

export const useTasks = () => {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTasks must be used within a TaskProvider');
  }
  return context;
};