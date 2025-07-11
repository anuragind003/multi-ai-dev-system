import React from 'react';
import TaskForm from '../components/TaskForm';

const AddTaskPage: React.FC = () => {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Add New Task</h1>
      <TaskForm />
    </div>
  );
};

export default AddTaskPage;