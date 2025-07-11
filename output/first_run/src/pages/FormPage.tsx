import React from 'react';
import { useForm } from '../hooks/useForm';
import InputField from '../components/InputField';
import { useAppContext } from '../context/AppContext';

function FormPage() {
  const { formData, setFormData } = useAppContext();
  const { values, errors, handleChange, handleSubmit } = useForm({
    initialValues: {
      name: '',
      email: '',
      password: '',
    },
    onSubmit: (values) => {
      console.log('Form submitted with values:', values);
      setFormData(values);
      alert('Form submitted successfully! Check console for data.');
    },
    validate: (values) => {
      const errors: { [key: string]: string } = {};
      if (!values.name) {
        errors.name = 'Name is required';
      }
      if (!values.email) {
        errors.email = 'Email is required';
      } else if (!/\S+@\S+\.\S+/.test(values.email)) {
        errors.email = 'Email is invalid';
      }
      if (!values.password) {
        errors.password = 'Password is required';
      } else if (values.password.length < 6) {
        errors.password = 'Password must be at least 6 characters';
      }
      return errors;
    },
  });

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white shadow-md rounded-md">
      <h2 className="text-2xl font-semibold mb-4">Form with Validation</h2>
      <form onSubmit={handleSubmit}>
        <InputField
          label="Name"
          type="text"
          id="name"
          name="name"
          value={values.name}
          onChange={handleChange}
          error={errors.name}
        />
        <InputField
          label="Email"
          type="email"
          id="email"
          name="email"
          value={values.email}
          onChange={handleChange}
          error={errors.email}
        />
        <InputField
          label="Password"
          type="password"
          id="password"
          name="password"
          value={values.password}
          onChange={handleChange}
          error={errors.password}
        />
        <button
          type="submit"
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
        >
          Submit
        </button>
      </form>
      {formData && (
        <div className="mt-4">
          <h3 className="font-semibold">Form Data:</h3>
          <pre>{JSON.stringify(formData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default FormPage;