import React, { useState } from 'react';
import { useTask } from '../contexts/TaskContext';
import Input from './Input';
import Button from './Button';

const TaskForm: React.FC = () => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const { addTask, error } = useTask();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      return; // Prevent submission if fields are empty
    }

    await addTask({ title, description, completed: false });
    setTitle('');
    setDescription('');
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      {error && <p className="text-red-500 mb-2">{error}</p>}
      <Input
        type="text"
        label="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />
      <Input
        type="text"
        label="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        required
      />
      <Button type="submit" variant="primary">
        Add Task
      </Button>
    </form>
  );
};

export default TaskForm;