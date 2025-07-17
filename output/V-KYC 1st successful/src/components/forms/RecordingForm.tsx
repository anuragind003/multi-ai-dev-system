import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Input, Button } from '@/components/ui';
import { recordingSchema } from '@/utils';
import { useRecordings } from '@/context';
import { z } from 'zod';

// Infer the type from the Zod schema
type RecordingFormData = z.infer<typeof recordingSchema>;

interface Recording {
  id: string;
  title: string;
  description: string;
  duration: number; // in seconds
  date: string; // ISO string
  tags: string[];
}

interface RecordingFormProps {
  initialData?: Recording | null;
  onSuccess: () => void;
}

export const RecordingForm: React.FC<RecordingFormProps> = React.memo(({ initialData, onSuccess }) => {
  const { addRecording, updateRecording, isLoading: isContextLoading } = useRecordings();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<RecordingFormData>({
    resolver: zodResolver(recordingSchema),
    defaultValues: {
      title: '',
      description: '',
      duration: 0,
      date: new Date().toISOString().split('T')[0], // Default to today's date
      tags: '',
    },
  });

  useEffect(() => {
    if (initialData) {
      reset({
        title: initialData.title,
        description: initialData.description,
        duration: initialData.duration,
        date: initialData.date.split('T')[0], // Format date for input type="date"
        tags: initialData.tags.join(', '),
      });
    } else {
      reset({
        title: '',
        description: '',
        duration: 0,
        date: new Date().toISOString().split('T')[0],
        tags: '',
      });
    }
  }, [initialData, reset]);

  const onSubmit = async (data: RecordingFormData) => {
    try {
      const formattedData = {
        ...data,
        duration: Number(data.duration), // Ensure duration is a number
        tags: data.tags.split(',').map(tag => tag.trim()).filter(tag => tag !== ''),
        date: new Date(data.date).toISOString(), // Ensure date is ISO string
      };

      if (initialData) {
        await updateRecording(initialData.id, formattedData);
      } else {
        await addRecording(formattedData);
      }
      onSuccess(); // Close modal or navigate
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'An unexpected error occurred.';
      setError('root.serverError', { type: 'manual', message: errorMessage });
      console.error('Form submission error:', err);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="Title"
        type="text"
        id="title"
        {...register('title')}
        error={errors.title?.message}
        aria-required="true"
      />
      <Input
        label="Description"
        type="text"
        id="description"
        {...register('description')}
        error={errors.description?.message}
      />
      <Input
        label="Duration (seconds)"
        type="number"
        id="duration"
        {...register('duration', { valueAsNumber: true })}
        error={errors.duration?.message}
        min="0"
        aria-required="true"
      />
      <Input
        label="Date"
        type="date"
        id="date"
        {...register('date')}
        error={errors.date?.message}
        aria-required="true"
      />
      <Input
        label="Tags (comma-separated)"
        type="text"
        id="tags"
        {...register('tags')}
        error={errors.tags?.message}
        placeholder="e.g., meeting, project, important"
      />

      {errors.root?.serverError && (
        <p className="error-message text-center" role="alert">
          {errors.root.serverError.message}
        </p>
      )}

      <Button type="submit" className="w-full" isLoading={isSubmitting || isContextLoading}>
        {initialData ? 'Update Recording' : 'Add Recording'}
      </Button>
    </form>
  );
});