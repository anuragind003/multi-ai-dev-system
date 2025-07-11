import { afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

// runs a cleanup after each test case
afterEach(() => {
  cleanup();
});

// Add any global setup here, e.g., mocking modules
beforeAll(() => {
  // Example: Mock a module
  // jest.mock('../services/api', () => ({
  //   fetchData: jest.fn(() => Promise.resolve({ data: [] })),
  // }));
});