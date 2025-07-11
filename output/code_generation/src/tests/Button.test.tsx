import { render, screen } from '@testing-library/react';
import { Button } from '../components/ui';
import { describe, it, expect, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

describe('Button', () => {
  it('renders with default variant and size', () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-indigo-600'); // primary variant default
    expect(button).toHaveClass('px-4 py-2'); // md size default
  });

  it('renders with specified variant and size', () => {
    render(<Button variant="secondary" size="lg">Submit</Button>);
    const button = screen.getByRole('button', { name: /submit/i });
    expect(button).toHaveClass('bg-gray-200'); // secondary variant
    expect(button).toHaveClass('px-6 py-3'); // lg size
  });

  it('calls onClick handler when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Test Button</Button>);
    const button = screen.getByRole('button', { name: /test button/i });
    await userEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    expect(button).toBeDisabled();
  });

  it('shows loading spinner when isLoading is true', () => {
    render(<Button isLoading>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading button/i });
    expect(button).toBeDisabled(); // Should be disabled when loading
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
    expect(button).not.toHaveTextContent(/loading button/i); // Text content should be replaced by spinner
  });

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole('button', { name: /custom/i });
    expect(button).toHaveClass('custom-class');
  });
});