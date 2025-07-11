import React, { useState, useEffect } from 'react';
import { useTasks } from '../hooks/useTasks';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Modal } from '../components/Modal';
import { Input } from '../components/Input';
import { useForm } from '../hooks/useForm';
import { Task } from '../types';

export const Dashboard = () => {
  const { tasks, loading, error, fetchTasks, createTask } = useTasks();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { values, handleChange, handleSubmit, errors, resetForm } = useForm({
    initialValues: { title: '', description: '' },
    onSubmit: async (values) => {
      await createTask(values);
      handleCloseModal();
      fetchTasks(); // Refresh tasks after creating a new one
    },
    validate: (values) => {
      const errors: { [key: string]: string } = {};
      if (!values.title) {
        errors.title = 'Title is required';
      }
      return errors;
    },
  });

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleOpenModal = () => setIsModalOpen(true);
  const handleCloseModal = () => {
    setIsModalOpen(false);
    resetForm();
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (error) {
    return <div className="flex items-center justify-center h-screen">Error: {error.message}</div>;
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Button onClick={handleOpenModal}>Add Task</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tasks.map((task) => (
          <Card key={task.id} title={task.title}>
            <p>{task.description}</p>
          </Card>
        ))}
      </div>

      <Modal isOpen={isModalOpen} onClose={handleCloseModal} title="Add New Task">
        <form onSubmit={handleSubmit}>
          <Input
            label="Title"
            type="text"
            id="title"
            name="title"
            value={values.title}
            onChange={handleChange}
            error={errors.title}
          />
          <Input
            label="Description"
            type="text"
            id="description"
            name="description"
            value={values.description}
            onChange={handleChange}
          />
          <Button type="submit">Create Task</Button>
        </form>
      </Modal>
    </div>
  );
};