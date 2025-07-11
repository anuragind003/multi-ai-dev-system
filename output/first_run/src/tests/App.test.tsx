import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import App from '../App';
import { AppProvider } from '../context/AppContext';

test('renders App component and navigation links', () => {
  render(
    <AppProvider>
      <Router>
        <App />
      </Router>
    </AppProvider>
  );

  expect(screen.getByText(/My App/i)).toBeInTheDocument();
  expect(screen.getByText(/Home/i)).toBeInTheDocument();
  expect(screen.getByText(/About/i)).toBeInTheDocument();
  expect(screen.getByText(/Contact/i)).toBeInTheDocument();
});