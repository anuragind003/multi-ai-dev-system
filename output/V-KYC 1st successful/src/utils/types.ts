// --- User & Auth Types ---
export enum UserRole {
  User = 'user',
  Admin = 'admin',
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  userId: string;
  // Add any other user data returned on login
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

// --- Upload Types ---
export enum UploadStatus {
  Pending = 'PENDING',
  Processing = 'PROCESSING',
  Completed = 'COMPLETED',
  Failed = 'FAILED',
}

export interface UploadResponse {
  requestId: string;
  message: string;
}

export interface UploadResult {
  rowId: number;
  status: 'SUCCESS' | 'FAILED';
  message: string;
  data: Record<string, any>; // The actual data processed for this row
}

export interface BulkUploadRequest {
  id: string;
  filename: string;
  status: UploadStatus;
  uploadedAt: string; // ISO date string
  totalRows: number;
  processedRows: number;
  successCount: number;
  failureCount: number;
  results: UploadResult[]; // Detailed results for each row
  errorMessage?: string; // If the overall upload failed
}

// --- Generic Component Types ---
export type Variant = 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
export type Size = 'sm' | 'md' | 'lg';