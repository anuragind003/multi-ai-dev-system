import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button, Input } from '@/components/ui/CoreUI'; // Import from CoreUI
import { describe, it, expect, vi } from 'vitest';

describe('Button Component', () => {
  it('renders with default variant and size', () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
    expect(button).toHaveClass('px-4 py-2');
  });

  it('renders with a different variant', () => {
    render(<Button variant="secondary">Submit</Button>);
    const button = screen.getByRole('button', { name: /submit/i });
    expect(button).toHaveClass('bg-secondary');
  });

  it('calls onClick handler when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Test Button</Button>);
    const button = screen.getByRole('button', { name: /test button/i });
    await userEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('shows loading state when isLoading is true', () => {
    render(<Button isLoading>Loading...</Button>);
    const button = screen.getByRole('button', { name: /loading/i });
    expect(button).toBeDisabled();
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    expect(button).toBeDisabled();
  });
});

describe('Input Component', () => {
  it('renders with a label and placeholder', () => {
    render(<Input label="Username" placeholder="Enter username" />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/enter username/i)).toBeInTheDocument();
  });

  it('displays an error message', () => {
    render(<Input label="Email" error="Invalid email" />);
    expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
  });

  it('updates value on change', async () => {
    render(<Input label="Name" />);
    const input = screen.getByLabelText(/name/i);
    await userEvent.type(input, 'John Doe');
    expect(input).toHaveValue('John Doe');
  });

  it('renders file input correctly', () => {
    render(<Input label="Upload File" type="file" />);
    const fileInput = screen.getByLabelText(/upload file/i);
    expect(fileInput).toBeInTheDocument();
    expect(fileInput).toHaveAttribute('type', 'file');
  });
});