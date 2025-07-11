import React from 'react';
import TaskItem from '../components/TaskItem';
import { useTasks } from '../context/TaskContext';
import TaskForm from '../components/TaskForm';

const TaskList: React.FC = () => {
  const { tasks } = useTasks();

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Task List</h1>
      <TaskForm />
      {tasks.length === 0 ? (
        <p className="text-gray-500">No tasks yet. Add one!</p>
      ) : (
        <ul className="space-y-2">
          {tasks.map((task) => (
            <TaskItem key={task.id} task={task} />
          ))}
        </ul>
      )}
    </div>
  );
};

export default TaskList;