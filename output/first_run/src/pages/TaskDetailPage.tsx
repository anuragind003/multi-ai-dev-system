import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTaskContext } from '../context/TaskContext';
import { Task } from '../context/TaskContext';

const TaskDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { getTaskById, deleteTask } = useTaskContext();
  const navigate = useNavigate();
  const task: Task | undefined = getTaskById(id!);

  if (!task) {
    return <p>Task not found.</p>;
  }

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      deleteTask(id!);
      navigate('/');
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">{task.title}</h1>
      <p className="mb-2">
        <span className="font-semibold">Due Date:</span> {task.dueDate}
      </p>
      <p className="mb-4">{task.description}</p>
      <p className="mb-2">
        <span className="font-semibold">Status:</span> {task.status}
      </p>
      <button
        onClick={handleDelete}
        className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
      >
        Delete Task
      </button>
    </div>
  );
};

export default TaskDetailPage;