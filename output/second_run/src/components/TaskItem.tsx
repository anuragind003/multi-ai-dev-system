import React from 'react';
import { Task } from '../types';

interface TaskItemProps {
  task: Task;
  onDelete: (id: string) => void;
  onToggleComplete: (id: string) => void;
}

export const TaskItem: React.FC<TaskItemProps> = ({ task, onDelete, onToggleComplete }) => {
  return (
    <div className="bg-white dark:bg-gray-700 shadow-md rounded-lg p-4 mb-4 flex justify-between items-center">
      <div className="flex-grow">
        <h3 className={`text-lg font-semibold ${task.completed ? 'line-through text-gray-500' : 'text-gray-800 dark:text-white'}`}>
          {task.title}
        </h3>
        <p className="text-gray-600 dark:text-gray-300">{task.description}</p>
      </div>
      <div className="flex space-x-2">
        <button
          onClick={() => onToggleComplete(task.id)}
          className={`px-3 py-1 rounded-md text-white ${task.completed ? 'bg-green-500 hover:bg-green-700' : 'bg-yellow-500 hover:bg-yellow-700'}`}
        >
          {task.completed ? 'Mark Incomplete' : 'Mark Complete'}
        </button>
        <button
          onClick={() => onDelete(task.id)}
          className="px-3 py-1 rounded-md bg-red-500 hover:bg-red-700 text-white"
        >
          Delete
        </button>
      </div>
    </div>
  );
};