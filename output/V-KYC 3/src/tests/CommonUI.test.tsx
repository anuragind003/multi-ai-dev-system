import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button, Input, Card, LoadingSpinner } from '../components/ui/CommonUI';
import React from 'react';

// Mock React.memo to ensure components are rendered directly for testing
vi.mock('react', async (importOriginal) => {
  const actual = await importOriginal<typeof React>();
  return {
    ...actual,
    memo: (component: React.ComponentType) => component,
  };
});

describe('CommonUI Components', () => {
  // --- Button Tests ---
  describe('Button', () => {
    it('renders with default variant and size', () => {
      render(<Button>Click Me</Button>);
      const button = screen.getByRole('button', { name: /click me/i });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('bg-primary'); // Default variant is primary
      expect(button).toHaveClass('px-4 py-2'); // Default size is md
    });

    it('renders with specified variant and size', () => {
      render(<Button variant="secondary" size="lg">Submit</Button>);
      const button = screen.getByRole('button', { name: /submit/i });
      expect(button).toHaveClass('bg-secondary');
      expect(button).toHaveClass('px-5 py-2.5');
    });

    it('calls onClick handler when clicked', () => {
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Test Button</Button>);
      fireEvent.click(screen.getByRole('button', { name: /test button/i }));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('disables the button when disabled prop is true', () => {
      render(<Button disabled>Disabled Button</Button>);
      const button = screen.getByRole('button', { name: /disabled button/i });
      expect(button).toBeDisabled();
      expect(button).toHaveClass('opacity-50');
    });

    it('shows loading spinner and disables button when isLoading is true', () => {
      render(<Button isLoading>Loading Button</Button>);
      const button = screen.getByRole('button', { name: /loading button/i });
      expect(button).toBeDisabled();
      expect(screen.getByLabelText('Loading')).toBeInTheDocument();
    });
  });

  // --- Input Tests ---
  describe('Input', () => {
    it('renders with a label and placeholder', () => {
      render(<Input label="Username" placeholder="Enter username" />);
      expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/enter username/i)).toBeInTheDocument();
    });

    it('displays error message when error prop is provided', () => {
      render(<Input label="Email" error="Invalid email format" />);
      expect(screen.getByText(/invalid email format/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
    });

    it('updates value on change', () => {
      render(<Input label="Name" name="name" />);
      const input = screen.getByLabelText(/name/i) as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'John Doe' } });
      expect(input.value).toBe('John Doe');
    });

    it('uses provided id or generates one', () => {
      render(<Input label="Test Input" id="my-test-input" />);
      expect(screen.getByLabelText('Test Input')).toHaveAttribute('id', 'my-test-input');

      const { rerender } = render(<Input label="Another Input" name="another" />);
      expect(screen.getByLabelText('Another Input')).toHaveAttribute('id', 'another-input');

      rerender(<Input label="No ID or Name" />);
      expect(screen.getByLabelText('No ID or Name')).toHaveAttribute('id', 'no-id-or-name');
    });
  });

  // --- Card Tests ---
  describe('Card', () => {
    it('renders children content', () => {
      render(<Card><div>Card Content</div></Card>);
      expect(screen.getByText(/card content/i)).toBeInTheDocument();
    });

    it('renders with a title', () => {
      render(<Card title="My Card Title">Content</Card>);
      expect(screen.getByRole('heading', { name: /my card title/i })).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<Card className="custom-card">Content</Card>);
      expect(screen.getByText('Content').closest('div')).toHaveClass('custom-card');
    });
  });

  // --- LoadingSpinner Tests ---
  describe('LoadingSpinner', () => {
    it('renders with default size and role', () => {
      render(<LoadingSpinner />);
      const spinner = screen.getByRole('status', { name: /loading/i });
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveClass('w-6 h-6'); // Default size is md
    });

    it('renders with specified size', () => {
      render(<LoadingSpinner size="lg" />);
      const spinner = screen.getByRole('status', { name: /loading/i });
      expect(spinner).toHaveClass('w-8 h-8');
    });

    it('has screen reader text', () => {
      render(<LoadingSpinner />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });
});