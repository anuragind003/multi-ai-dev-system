import React from 'react';
import { render, screen } from '@testing-library/react';
import Button from '../components/ui/Button';
import '@testing-library/jest-dom';

describe('Button Component', () => {
  test('renders with default variant and size', () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
    expect(button).toHaveClass('px-4 py-2');
  });

  test('renders with specified variant', () => {
    render(<Button variant="secondary">Secondary Button</Button>);
    const button = screen.getByRole('button', { name: /secondary button/i });
    expect(button).toHaveClass('bg-secondary');
  });

  test('renders with specified size', () => {
    render(<Button size="lg">Large Button</Button>);
    const button = screen.getByRole('button', { name: /large button/i });
    expect(button).toHaveClass('px-6 py-3');
  });

  test('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    expect(button).toBeDisabled();
    expect(button).toHaveClass('opacity-50');
  });

  test('shows loading state when isLoading prop is true', () => {
    render(<Button isLoading>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading.../i });
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent('Loading...');
    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument(); // Check for spinner SVG
  });

  test('applies additional className', () => {
    render(<Button className="custom-class">Custom Button</Button>);
    const button = screen.getByRole('button', { name: /custom button/i });
    expect(button).toHaveClass('custom-class');
  });

  test('forwards other props to the button element', () => {
    render(<Button data-testid="test-button">Test Button</Button>);
    const button = screen.getByTestId('test-button');
    expect(button).toBeInTheDocument();
  });
});