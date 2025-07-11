import { z, ZodError } from 'zod';

// Define Zod schema for login form
export const loginFormSchema = z.object({
  usernameOrEmail: z.string()
    .min(1, { message: 'Username or Email is required' })
    .max(255, { message: 'Username or Email is too long' }),
  password: z.string()
    .min(1, { message: 'Password is required' })
    .min(6, { message: 'Password must be at least 6 characters long' })
    .max(100, { message: 'Password is too long' }),
});

// Infer the TypeScript type from the schema
export type LoginFormSchema = z.infer<typeof loginFormSchema>;

/**
 * Validates login form data against the schema.
 * @param data - The form data to validate.
 * @throws {ZodError} If validation fails.
 */
export const validateLoginForm = (data: LoginFormSchema): void => {
  loginFormSchema.parse(data);
};

// Example of a more generic validation function (can be extended)
export const validateFormData = <T extends z.ZodTypeAny>(schema: T, data: unknown): z.infer<T> => {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof ZodError) {
      console.error('Validation Error:', error.errors);
      // You might want to re-throw or return a structured error object
      throw error;
    }
    throw new Error('An unknown validation error occurred.');
  }
};

// Example of a registration form schema (for future use)
export const registrationFormSchema = z.object({
  username: z.string().min(3, { message: 'Username must be at least 3 characters' }),
  email: z.string().email({ message: 'Invalid email address' }),
  password: z.string().min(6, { message: 'Password must be at least 6 characters' }),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'], // Path of error
});

export type RegistrationFormSchema = z.infer<typeof registrationFormSchema>;