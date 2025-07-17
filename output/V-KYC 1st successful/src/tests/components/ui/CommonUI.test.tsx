// src/tests/components/ui/CommonUI.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Button, Input, Card } from '@/components/ui/CommonUI';
import { FaUser } from 'react-icons/fa';

// Mocking Next.js Link for components that might use it indirectly (e.g., Card footer)
jest.mock('next/link', () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

describe('CommonUI Components', () => {
  // --- Button Tests ---
  describe('Button', () => {
    it('renders with default variant and size', () => {
      render(<Button>Click Me</Button>);
      const button = screen.getByRole('button', { name: /click me/i });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('bg-primary');
      expect(button).toHaveClass('px-4 py-2');
    });

    it('renders with a different variant and size', () => {
      render(<Button variant="secondary" size="lg">Submit</Button>);
      const button = screen.getByRole('button', { name: /submit/i });
      expect(button).toHaveClass('bg-secondary');
      expect(button).toHaveClass('px-6 py-3');
    });

    it('displays loading state correctly', () => {
      render(<Button isLoading>Loading...</Button>);
      const button = screen.getByRole('button', { name: /loading.../i });
      expect(button).toBeDisabled();
      expect(button).toHaveClass('opacity-70');
      expect(screen.getByTestId('fa-spinner')).toBeInTheDocument(); // Assuming FaSpinner has data-testid="fa-spinner"
    });

    it('calls onClick handler when clicked', () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>Test Button</Button>);
      fireEvent.click(screen.getByRole('button', { name: /test button/i }));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders with an icon', () => {
      render(<Button icon={<FaUser data-testid="user-icon" />}>Profile</Button>);
      expect(screen.getByTestId('user-icon')).toBeInTheDocument();
    });
  });

  // --- Input Tests ---
  describe('Input', () => {
    it('renders with a label and placeholder', () => {
      render(<Input label="Username" placeholder="Enter username" />);
      expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/enter username/i)).toBeInTheDocument();
    });

    it('displays error message', () => {
      render(<Input label="Email" error="Invalid email" />);
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email/i)).toHaveClass('border-red-500');
    });

    it('updates value on change', () => {
      render(<Input label="Search" />);
      const input = screen.getByLabelText(/search/i) as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'test query' } });
      expect(input.value).toBe('test query');
    });

    it('renders with an icon', () => {
      render(<Input label="User" icon={<FaUser data-testid="input-user-icon" />} />);
      expect(screen.getByTestId('input-user-icon')).toBeInTheDocument();
      expect(screen.getByLabelText(/user/i)).toHaveClass('pl-10');
    });
  });

  // --- Card Tests ---
  describe('Card', () => {
    it('renders with children', () => {
      render(<Card><div>Card Content</div></Card>);
      expect(screen.getByText(/card content/i)).toBeInTheDocument();
      expect(screen.getByText(/card content/i).closest('div')).toHaveClass('bg-white');
    });

    it('renders with a title', () => {
      render(<Card title="My Card Title">Content</Card>);
      expect(screen.getByRole('heading', { name: /my card title/i })).toBeInTheDocument();
    });

    it('renders with a footer', () => {
      render(<Card footer={<span>Card Footer</span>}>Content</Card>);
      expect(screen.getByText(/card footer/i)).toBeInTheDocument();
    });

    it('applies custom class names', () => {
      render(<Card className="custom-card-style">Content</Card>);
      expect(screen.getByText(/content/i).closest('div')).toHaveClass('custom-card-style');
    });
  });
});