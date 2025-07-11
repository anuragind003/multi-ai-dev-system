// src/types/index.ts

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  token: string | null;
  loading: boolean;
  error: string | null;
}

export interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export interface TableRecord {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'pending';
  createdAt: string;
  updatedAt: string;
  category: string;
  value: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  totalRecords: number;
  currentPage: number;
  totalPages: number;
  pageSize: number;
}

export interface UseTableDataOptions {
  initialPage?: number;
  initialPageSize?: number;
  debounceTime?: number;
}

export interface UseTableDataResult<T> {
  data: T[];
  loading: boolean;
  error: string | null;
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalRecords: number;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  goToPage: (page: number) => void;
  setPageSize: (size: number) => void;
  refreshData: () => void;
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  pageSize: number;
  onPageSizeChange: (size: number) => void;
  pageSizeOptions?: number[];
}

export interface FeedbackProps {
  message: string;
  type: 'loading' | 'error';
}