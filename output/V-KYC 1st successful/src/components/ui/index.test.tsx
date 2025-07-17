import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Button, Input, Card, Modal } from './index'; // Import from the barrel file

describe('UI Components', () => {
  // --- Button Tests ---
  describe('Button', () => {
    it('renders with default variant and size', () => {
      render(<Button>Click Me</Button>);
      const button = screen.getByRole('button', { name: /click me/i });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('bg-primary'); // Default variant
      expect(button).toHaveClass('px-4 py-2'); // Default size
    });

    it('renders with specified variant and size', () => {
      render(<Button variant="secondary" size="large">Submit</Button>);
      const button = screen.getByRole('button', { name: /submit/i });
      expect(button).toHaveClass('bg-secondary');
      expect(button).toHaveClass('px-6 py-3');
    });

    it('handles click events', () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>Test Button</Button>);
      fireEvent.click(screen.getByRole('button', { name: /test button/i }));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('is disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled Button</Button>);
      const button = screen.getByRole('button', { name: /disabled button/i });
      expect(button).toBeDisabled();
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
      render(<Input label="Email" error="Invalid email" />);
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email/i)).toHaveClass('border-error');
    });

    it('updates value on change', () => {
      render(<Input label="Name" />);
      const input = screen.getByLabelText(/name/i) as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'John Doe' } });
      expect(input.value).toBe('John Doe');
    });
  });

  // --- Card Tests ---
  describe('Card', () => {
    it('renders children correctly', () => {
      render(<Card><div>Card Content</div></Card>);
      expect(screen.getByText(/card content/i)).toBeInTheDocument();
    });

    it('renders with a title', () => {
      render(<Card title="My Card Title">Content</Card>);
      expect(screen.getByRole('heading', { name: /my card title/i })).toBeInTheDocument();
    });

    it('applies custom class names', () => {
      render(<Card className="custom-card">Content</Card>);
      expect(screen.getByText(/content/i).closest('div')).toHaveClass('custom-card');
    });
  });

  // --- Modal Tests ---
  describe('Modal', () => {
    it('does not render when isOpen is false', () => {
      render(<Modal isOpen={false} onClose={() => {}}>Modal Content</Modal>);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('renders when isOpen is true', () => {
      render(<Modal isOpen={true} onClose={() => {}}>Modal Content</Modal>);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText(/modal content/i)).toBeInTheDocument();
    });

    it('calls onClose when the close button is clicked', () => {
      const handleClose = jest.fn();
      render(<Modal isOpen={true} onClose={handleClose}>Modal Content</Modal>);
      fireEvent.click(screen.getByLabelText(/close modal/i));
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when clicking outside the modal content', () => {
      const handleClose = jest.fn();
      render(<Modal isOpen={true} onClose={handleClose}>Modal Content</Modal>);
      fireEvent.click(screen.getByRole('dialog')); // Click on the overlay
      expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('does not call onClose when clicking inside the modal content', () => {
      const handleClose = jest.fn();
      render(<Modal isOpen={true} onClose={handleClose}><div>Inside Modal</div></Modal>);
      fireEvent.click(screen.getByText(/inside modal/i));
      expect(handleClose).not.toHaveBeenCalled();
    });

    it('renders with a title', () => {
      render(<Modal isOpen={true} onClose={() => {}} title="Modal Title">Content</Modal>);
      expect(screen.getByRole('heading', { name: /modal title/i })).toBeInTheDocument();
    });
  });
});