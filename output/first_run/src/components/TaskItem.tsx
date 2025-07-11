import React from 'react';
import { useTasks } from '../context/TaskContext';

interface TaskItemProps {
  task: {
    id: string;
    title: string;
    description: string;
    completed: boolean;
  };
}

const TaskItem: React.FC<TaskItemProps> = ({ task }) => {
  const { toggleTaskCompletion, deleteTask } = useTasks();

  return (
    <li className="bg-white shadow rounded-md p-4 flex items-center justify-between">
      <div className="flex-grow">
        <h3 className={`text-lg font-medium ${task.completed ? 'line-through text-gray-500' : ''}`}>
          {task.title}
        </h3>
        <p className="text-gray-600">{task.description}</p>
      </div>
      <div className="flex space-x-2">
        <button
          onClick={() => toggleTaskCompletion(task.id)}
          className={`px-3 py-1 rounded-md text-white ${
            task.completed ? 'bg-green-500 hover:bg-green-700' : 'bg-blue-500 hover:bg-blue-700'
          }`}
          aria-label={task.completed ? 'Mark as incomplete' : 'Mark as complete'}
        >
          {task.completed ? 'Incomplete' : 'Complete'}
        </button>
        <button
          onClick={() => deleteTask(task.id)}
          className="px-3 py-1 rounded-md bg-red-500 hover:bg-red-700 text-white"
          aria-label="Delete task"
        >
          Delete
        </button>
      </div>
    </li>
  );
};

export default TaskItem;