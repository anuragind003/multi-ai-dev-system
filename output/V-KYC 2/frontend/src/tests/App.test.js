import { render, screen } from '@testing-library/react';
import App from '../App'; // Assuming App.js is the main component

// Mock fetch API to prevent actual network requests during tests
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ message: 'Hello from Backend!' }),
  })
);

describe('App Component', () => {
  test('renders learn react link', () => {
    render(<App />);
    const linkElement = screen.getByText(/learn react/i);
    expect(linkElement).toBeInTheDocument();
  });

  test('renders "Hello from Backend!" after fetching data', async () => {
    render(<App />);
    // Wait for the asynchronous fetch to complete and the component to update
    const backendMessage = await screen.findByText(/Hello from Backend!/i);
    expect(backendMessage).toBeInTheDocument();
  });

  test('displays "Loading..." initially', () => {
    render(<App />);
    const loadingText = screen.getByText(/Loading.../i);
    expect(loadingText).toBeInTheDocument();
  });

  test('calls fetch on component mount', () => {
    render(<App />);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith('/api'); // Assuming /api is the backend endpoint
  });
});