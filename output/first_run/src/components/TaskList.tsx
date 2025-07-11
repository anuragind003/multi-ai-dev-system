import React from 'react';
import { Link } from 'react-router-dom';
import { Task } from '../context/TaskContext';

interface TaskListProps {
  tasks: Task[];
}

const TaskList: React.FC<TaskListProps> = ({ tasks }) => {
  return (
    <ul className="space-y-4">
      {tasks.map((task) => (
        <li key={task.id} className="bg-white shadow-md rounded-md p-4">
          <Link to={`/task/${task.id}`} className="block hover:text-blue-600">
            <h3 className="text-lg font-semibold">{task.title}</h3>
            <p className="text-gray-600">{task.description}</p>
            <p className="text-sm text-gray-500">Due: {task.dueDate}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
};

export default TaskList;