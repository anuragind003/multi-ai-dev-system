import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import Button from './Button';

describe('Button', () => {
  it('renders with default variant and size', () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary'); // Default variant
    expect(button).toHaveClass('px-4 py-2'); // Default size
  });

  it('renders with specified variant and size', () => {
    render(<Button variant="secondary" size="lg">Submit</Button>);
    const button = screen.getByRole('button', { name: /submit/i });
    expect(button).toHaveClass('bg-secondary');
    expect(button).toHaveClass('px-6 py-3');
  });

  it('calls onClick handler when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Test Button</Button>);
    const button = screen.getByRole('button', { name: /test button/i });
    await userEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('disables the button when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    expect(button).toBeDisabled();
    expect(button).toHaveClass('opacity-50');
  });

  it('shows loading state when isLoading prop is true', () => {
    render(<Button isLoading>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading button/i });
    expect(button).toBeDisabled(); // Should be disabled when loading
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument(); // Check for spinner SVG
  });

  it('does not call onClick when isLoading is true', async () => {
    const handleClick = vi.fn();
    render(<Button isLoading onClick={handleClick}>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading button/i });
    await userEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies additional className', () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole('button', { name: /custom/i });
    expect(button).toHaveClass('custom-class');
  });
});