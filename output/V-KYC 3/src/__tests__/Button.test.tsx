import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Button from '../components/ui/Button';

describe('Button Component', () => {
  test('renders with default variant and size', () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary'); // Default variant
    expect(button).toHaveClass('px-4 py-2'); // Default size
  });

  test('renders with specified variant and size', () => {
    render(<Button variant="secondary" size="lg">Submit</Button>);
    const button = screen.getByRole('button', { name: /submit/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-secondary');
    expect(button).toHaveClass('px-5 py-2.5');
  });

  test('calls onClick handler when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Test Button</Button>);
    const button = screen.getByRole('button', { name: /test button/i });
    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('disables button when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    expect(button).toBeDisabled();
    expect(button).toHaveClass('opacity-50');
    expect(button).toHaveClass('cursor-not-allowed');
  });

  test('shows loading state when isLoading is true', () => {
    render(<Button isLoading>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading.../i });
    expect(button).toBeInTheDocument();
    expect(button).toBeDisabled();
    expect(button).toHaveClass('opacity-50');
    expect(button).toHaveClass('cursor-not-allowed');
    expect(screen.getByLabelText('Loading')).toBeInTheDocument(); // Check for spinner's aria-label
  });

  test('does not call onClick when isLoading is true', () => {
    const handleClick = jest.fn();
    render(<Button isLoading onClick={handleClick}>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading.../i });
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  test('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole('button', { name: /custom/i });
    expect(button).toHaveClass('custom-class');
  });
});