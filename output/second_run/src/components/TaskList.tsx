import React from 'react';

interface Task {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

interface TaskListProps {
  tasks: Task[];
}

const TaskList: React.FC<TaskListProps> = ({ tasks }) => {
  return (
    <ul className="space-y-4">
      {tasks.map((task) => (
        <li key={task.id} className="bg-white dark:bg-gray-700 shadow-md rounded-lg p-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white">{task.title}</h3>
          <p className="text-gray-600 dark:text-gray-300">{task.description}</p>
          <div className="mt-2">
            <span className={`inline-block py-1 px-2 rounded-full text-xs font-medium ${task.completed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              {task.completed ? 'Completed' : 'Pending'}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
};

export default TaskList;